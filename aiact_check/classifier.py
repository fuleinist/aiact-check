"""Classification: detections + config -> risk tier and findings (F2)."""

from __future__ import annotations

from dataclasses import dataclass, field

from aiact_check.config import ProjectConfig
from aiact_check.knowledge import (
    CAPABILITY_TRANSPARENCY,
    HIGH_RISK_DOMAINS,
    PROHIBITED_ARTICLES,
    RISK_HIGH,
    RISK_LIMITED,
    RISK_NONE,
    RISK_ORDER,
    RISK_PROHIBITED,
    RISK_TRANSPARENCY,
    SIGNAL_TO_DOMAIN,
    Finding,
)
from aiact_check.scanner import ScanResult

# Capability categories that inherently produce synthetic content
GENERATIVE_CAPABILITIES = {"image-generation", "speech"}

# Prohibited-candidate signal ids requiring context review vs outright flags
PROHIBITED_SIGNALS = {
    "social-scoring", "subliminal-manipulation", "scraped-facial-db", "rbi-public-space",
}


@dataclass
class Classification:
    tier: str  # prohibited | high-risk | transparency | limited | none
    tier_reasons: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    high_risk_domains: list[str] = field(default_factory=list)
    ai_detected: bool = False
    eu_market: bool | None = None  # None = undeclared

    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "tierReasons": list(self.tier_reasons),
            "aiDetected": self.ai_detected,
            "euMarket": self.eu_market,
            "highRiskDomains": list(self.high_risk_domains),
            "findings": [f.to_dict() for f in self.findings],
        }


def classify(scan: ScanResult, cfg: ProjectConfig) -> Classification:
    result = Classification(tier=RISK_NONE, ai_detected=bool(scan.detections))

    if cfg.market == "eu":
        result.eu_market = True
    elif cfg.market == "none":
        result.eu_market = False

    tier_candidates: list[tuple[str, str]] = []  # (tier, reason)

    # --- Prohibited-practice signals ---------------------------------------
    prohibited_hits = [d for d in scan.detections if d.name in PROHIBITED_SIGNALS]
    for det in prohibited_hits:
        article = PROHIBITED_ARTICLES.get(det.name, "Art. 5")
        result.findings.append(Finding(
            id=f"prohibited:{det.name}",
            severity=RISK_PROHIBITED,
            title=f"Possible prohibited practice: {det.name}",
            article=article,
            why=(f"Heuristic signal '{det.note}' matched. If confirmed in context, this practice is "
                 f"PROHIBITED under the EU AI Act and the system must not be placed on the market. "
                 f"Review the matched locations and remove or redesign the feature."),
            locations=list(det.locations),
        ))
        tier_candidates.append((RISK_PROHIBITED, f"prohibited-practice signal '{det.name}' ({article})"))

    # Emotion recognition / biometric categorisation: context-dependent
    for det in scan.detections:
        if det.name in ("emotion-recognition", "biometric-categorisation"):
            article = PROHIBITED_ARTICLES[det.name]
            result.findings.append(Finding(
                id=f"prohibited-context:{det.name}",
                severity=RISK_HIGH,
                title=f"Context-dependent prohibition check: {det.name}",
                article=article,
                why=(f"Signal '{det.note}' matched. This is PROHIBITED in workplace/education settings "
                     f"(emotion recognition) or for sensitive attributes (biometric categorisation), and "
                     f"otherwise typically high-risk biometrics (Annex III(1)). Verify your usage context."),
                locations=list(det.locations),
            ))
            tier_candidates.append((RISK_HIGH, f"context-dependent Art. 5 signal '{det.name}'"))

    # --- High-risk domains (Annex III) --------------------------------------
    domains: set[str] = set()
    for det in scan.detections:
        domain = SIGNAL_TO_DOMAIN.get(det.name)
        if domain:
            domains.add(domain)
            result.findings.append(Finding(
                id=f"high-risk-signal:{det.name}",
                severity=RISK_HIGH,
                title=f"Possible high-risk use: {HIGH_RISK_DOMAINS[domain]}",
                article=HIGH_RISK_DOMAINS[domain],
                why=(f"Heuristic signal '{det.note}' matched. Systems in this domain are presumed "
                     f"high-risk under Annex III and carry the full Art. 8-15 obligation set "
                     f"(risk management, data governance, technical documentation, logging, human "
                     f"oversight, accuracy/robustness). Review locations to confirm applicability."),
                locations=list(det.locations),
            ))
            tier_candidates.append((RISK_HIGH, f"Annex III domain '{domain}' signal ({det.name})"))

    if cfg.high_risk_domain:
        key = cfg.high_risk_domain
        if key in HIGH_RISK_DOMAINS:
            domains.add(key)
            result.findings.append(Finding(
                id=f"high-risk-declared:{key}",
                severity=RISK_HIGH,
                title=f"Declared high-risk domain: {HIGH_RISK_DOMAINS[key]}",
                article=HIGH_RISK_DOMAINS[key],
                why="aiact-check.toml declares this system operates in an Annex III high-risk domain.",
            ))
            tier_candidates.append((RISK_HIGH, f"declared high-risk domain '{key}'"))
        else:
            result.findings.append(Finding(
                id=f"config-unknown-domain:{key}",
                severity="info",
                title=f"Unknown high_risk_domain in config: {key}",
                article="—",
                why=f"Valid domains: {', '.join(sorted(HIGH_RISK_DOMAINS))}. Value ignored.",
            ))
    result.high_risk_domains = sorted(domains)

    # --- Transparency risk (Art. 50) ----------------------------------------
    transparency_reasons: list[str] = []
    if cfg.chatbot:
        transparency_reasons.append("config declares chatbot=true (Art. 50(1))")
        result.findings.append(Finding(
            id="transparency:chatbot-declared", severity=RISK_TRANSPARENCY,
            title="Declared conversational AI system", article="Art. 50(1)",
            why=("aiact-check.toml declares chatbot=true. Users must be informed they are interacting "
                 "with an AI system, unless obvious to a reasonably well-informed person."),
        ))
    if cfg.generates_content:
        kinds = ", ".join(cfg.generates_content)
        transparency_reasons.append(f"config declares generated content: {kinds} (Art. 50(2))")
        result.findings.append(Finding(
            id="transparency:synthetic-declared", severity=RISK_TRANSPARENCY,
            title=f"Declared synthetic content generation ({kinds})", article="Art. 50(2)",
            why=("aiact-check.toml declares generated content. Output must be marked as artificially "
                 "generated or manipulated in a machine-readable format, detectable at least as such."),
        ))
    if cfg.deepfake:
        transparency_reasons.append("config declares deepfake=true (Art. 50(4))")
        result.findings.append(Finding(
            id="transparency:deepfake-declared", severity=RISK_TRANSPARENCY,
            title="Declared deepfake generation", article="Art. 50(4)",
            why="aiact-check.toml declares deepfake generation. Deepfakes must be disclosed as artificially generated or manipulated.",
        ))

    generative_caps = scan.capabilities() & GENERATIVE_CAPABILITIES
    for cap in sorted(generative_caps):
        article, obligation = CAPABILITY_TRANSPARENCY[cap]
        transparency_reasons.append(f"capability '{cap}' can generate synthetic content ({article})")
        result.findings.append(Finding(
            id=f"transparency:capability:{cap}", severity=RISK_TRANSPARENCY,
            title=f"Synthetic-content capability detected: {cap}", article=article,
            why=(f"{obligation} Detections: " +
                 "; ".join(d.name for d in scan.detections if d.capability == cap)),
            locations=[loc for d in scan.detections if d.capability == cap for loc in d.locations[:3]],
        ))

    for det in scan.detections:
        if det.name == "deepfake-signals":
            transparency_reasons.append("deepfake/video-generation code signal (Art. 50(4))")
            result.findings.append(Finding(
                id="transparency:deepfake-signal", severity=RISK_TRANSPARENCY,
                title="Deepfake / synthetic video signal detected", article="Art. 50(4)",
                why=(f"{det.note}. If deployed, generated content must be marked machine-readably and "
                     f"deepfakes disclosed. Review locations to confirm."),
                locations=list(det.locations),
            ))
    if transparency_reasons:
        tier_candidates.append((RISK_TRANSPARENCY, "; ".join(transparency_reasons)))

    # --- AI detected at all -> limited risk floor ----------------------------
    if scan.detections and not tier_candidates:
        result.tier = RISK_LIMITED
        result.tier_reasons.append(
            "AI/ML usage detected without banned, high-risk, or transparency signals — "
            "minimal/limited risk tier. Art. 4 AI literacy still applies to staff."
        )
        result.findings.append(Finding(
            id="limited:ai-detected", severity="info",
            title="AI usage detected — limited/minimal risk",
            article="Art. 4",
            why=("No prohibited, high-risk, or Art. 50 signals matched. Note Art. 4 requires providers "
                 "and deployers to ensure a sufficient level of AI literacy in staff operating AI systems."),
            locations=[loc for d in scan.detections for loc in d.locations[:2]][:10],
        ))
    elif not scan.detections:
        result.tier = RISK_NONE
        result.tier_reasons.append("No AI/ML usage signals detected in the scanned project.")

    # --- Apply override / pick highest tier -----------------------------------
    if cfg.override:
        result.tier = cfg.override
        result.tier_reasons.insert(0, f"tier forced by aiact-check.toml override='{cfg.override}'")
        if cfg.override in (RISK_HIGH, RISK_PROHIBITED, RISK_TRANSPARENCY) and not result.findings:
            result.findings.append(Finding(
                id=f"override:{cfg.override}", severity=cfg.override,
                title=f"Risk tier forced to '{cfg.override}' by config", article="—",
                why="classification.override set in aiact-check.toml; no scanner findings contributed.",
            ))
    elif tier_candidates:
        best = max(tier_candidates, key=lambda t: RISK_ORDER[t[0]])
        result.tier = best[0]
        seen = set()
        for tier, reason in tier_candidates:
            if tier == best[0] and reason not in seen:
                result.tier_reasons.append(reason)
                seen.add(reason)
    return result
