"""Obligation checklist generation + deadline tracking (F3, F4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from aiact_check.classifier import Classification
from aiact_check.config import ProjectConfig
from aiact_check.knowledge import (
    DEADLINES,
    RISK_HIGH,
    RISK_NONE,
    RISK_PROHIBITED,
    RISK_TRANSPARENCY,
    Deadline,
    Obligation,
)


def _today() -> date:
    return datetime.now().astimezone().date()


def _parse(iso: str) -> date:
    return date.fromisoformat(iso)


def deadline_status(deadline: Deadline, today: date | None = None) -> dict:
    """Status of one deadline milestone relative to today."""
    today = today or _today()
    d = _parse(deadline.date)
    if d < today:
        state = "passed"
        days = (today - d).days
    elif d == today:
        state = "due-today"
        days = 0
    else:
        state = "upcoming"
        days = (d - today).days
    return {
        "date": deadline.date,
        "title": deadline.title,
        "detail": deadline.detail,
        "state": state,
        "daysRemaining": max(days, 0) if state == "upcoming" else 0,
        "daysSince": days if state == "passed" else 0,
    }


def deadlines_report(today: date | None = None) -> list[dict]:
    return [deadline_status(dl, today) for dl in DEADLINES]


# ---------------------------------------------------------------------------
# Obligation checklist (F3)
# ---------------------------------------------------------------------------

def _severity_for(deadline_iso: str, today: date) -> str:
    d = _parse(deadline_iso)
    if d < today:
        return "action-required"
    if (d - today).days <= 90:
        return "due-soon"
    return "info"


def build_obligations(cls: Classification, cfg: ProjectConfig, today: date | None = None) -> list[Obligation]:
    """Map classification + config to a concrete obligation checklist."""
    today = today or _today()
    role = cfg.role or "both"
    obligations: list[Obligation] = []

    def add(oid: str, article: str, applies: str, text: str, deadline: str, notes: list[str] | None = None):
        applies_to = applies if role in ("", "both") else (role if role == applies or applies == "both" else applies)
        obligations.append(Obligation(
            id=oid, article=article, applies_to=applies_to, text=text, deadline=deadline,
            severity=_severity_for(deadline, today), notes=notes or [],
        ))

    if cls.tier == RISK_NONE:
        return obligations

    # Art. 4 AI literacy — applies to essentially every AI system
    add("ai-literacy", "Art. 4", "both",
        "Ensure staff and operators have a sufficient level of AI literacy (training, documentation, onboarding).",
        "2025-02-02",
        ["Applies to providers and deployers of all AI systems regardless of risk tier."])

    if cls.tier == RISK_PROHIBITED:
        add("prohibited-stop", "Art. 5", "both",
            "STOP: review prohibited-practice findings immediately. If confirmed, the system must not be "
            "placed on the EU market or put into service. Redesign or remove the feature.",
            "2025-02-02",
            ["Prohibitions have been in force since 2025-02-02; penalties up to EUR 35M or 7% of global turnover."])

    if cls.tier in (RISK_TRANSPARENCY, RISK_HIGH, RISK_PROHIBITED):
        finding_ids = {f.id for f in cls.findings}
        if cfg.chatbot or any(i.startswith("transparency:chatbot") for i in finding_ids):
            add("art50-1-disclose", "Art. 50(1)", "provider",
                "Inform natural persons that they are interacting with an AI system, unless obvious to a "
                "reasonably well-informed, observant person. Add a visible disclosure at first interaction.",
                "2026-08-02")
        if cfg.generates_content or any("synthetic" in i or "capability" in i for i in finding_ids):
            add("art50-2-mark", "Art. 50(2)", "provider",
                "Mark synthetic output (text/audio/image/video) as artificially generated in a "
                "machine-readable format, detectable at least as such (e.g. metadata, watermarking).",
                "2026-08-02")
        if cfg.deepfake or any("deepfake" in i for i in finding_ids):
            add("art50-4-deepfake", "Art. 50(4)", "deployer",
                "Disclose deepfakes as artificially generated or manipulated. For AI-generated text on "
                "matters of public interest, disclose unless human editorial review with responsibility applies.",
                "2026-08-02")

    if cls.tier in (RISK_HIGH, RISK_PROHIBITED):
        domains = ", ".join(cls.high_risk_domains) or "declared domain"
        notes = [f"Triggered by: {domains}."]
        add("hr-1-risk-mgmt", "Art. 9", "provider",
            "Establish and maintain a risk management system across the lifecycle of the high-risk system.",
            "2027-12-02", notes)
        add("hr-2-data-gov", "Art. 10", "provider",
            "Implement data governance: training/validation/testing data quality, bias examination, gap analysis.",
            "2027-12-02", notes)
        add("hr-3-tech-docs", "Art. 11 + Annex IV", "provider",
            "Draw up technical documentation per Annex IV before placing on market; keep it updated. "
            "Run `aiact-check init-docs` for a skeleton.",
            "2027-12-02", notes)
        add("hr-4-logging", "Art. 12", "provider",
            "Enable automatic logging of events (traceability) appropriate to the system's purpose.",
            "2027-12-02", notes)
        add("hr-5-transparency", "Art. 13", "provider",
            "Provide deployers with instructions for use: capabilities, limitations, accuracy, oversight measures.",
            "2027-12-02", notes)
        add("hr-6-human-oversight", "Art. 14", "provider",
            "Design for effective human oversight: understand, interpret, intervene, override or stop the system.",
            "2027-12-02", notes)
        add("hr-7-robustness", "Art. 15", "provider",
            "Achieve appropriate accuracy, robustness and cybersecurity; document metrics and failure modes.",
            "2027-12-02", notes)
        add("hr-8-qms", "Art. 17", "provider",
            "Put in place a quality management system (QMS) covering compliance strategy, design, testing, "
            "post-market monitoring.",
            "2027-12-02", notes)
        add("hr-9-conformity", "Art. 43 + 47", "provider",
            "Complete conformity assessment, draw up EU declaration of conformity, affix CE marking before launch.",
            "2027-12-02", notes)
        add("hr-10-registration", "Art. 49", "provider",
            "Register the system in the EU database before placing on market.",
            "2027-12-02", notes)
        if cls.eu_market is False:
            for o in obligations:
                o.notes.append("project.market='none' declared — obligations apply only if the system's output "
                               "is used in the EU (Art. 2). Confirm before relying on this.")
    return obligations


def gpai_obligations(cfg: ProjectConfig, trains_model: bool, today: date | None = None) -> list[Obligation]:
    """Art. 53 GPAI obligations when the project trains/fine-tunes a general-purpose model."""
    today = today or _today()
    if not trains_model:
        return []
    obligations = [
        Obligation(id="gpai-docs", article="Art. 53(1)(a)", applies_to="provider",
                   text="Maintain technical documentation of the GPAI model (training process, evaluation).",
                   deadline="2025-08-02", severity=_severity_for("2025-08-02", today)),
        Obligation(id="gpai-downstream", article="Art. 53(1)(b)", applies_to="provider",
                   text="Provide information/documentation to downstream providers integrating the model.",
                   deadline="2025-08-02", severity=_severity_for("2025-08-02", today)),
        Obligation(id="gpai-copyright", article="Art. 53(1)(c)", applies_to="provider",
                   text="Put in place a policy to comply with EU copyright law (incl. TDM opt-out reservations).",
                   deadline="2025-08-02", severity=_severity_for("2025-08-02", today)),
        Obligation(id="gpai-training-summary", article="Art. 53(1)(d)", applies_to="provider",
                   text="Publish a sufficiently detailed summary of training content using the AI Office template.",
                   deadline="2025-08-02", severity=_severity_for("2025-08-02", today)),
    ]
    return obligations


@dataclass
class DeadlineAwareness:
    """Aggregated timeline state for reports."""
    passed: list[dict]
    upcoming: list[dict]
    next_deadline: dict | None

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "upcoming": self.upcoming,
            "nextDeadline": self.next_deadline,
        }


def deadline_awareness(today: date | None = None) -> DeadlineAwareness:
    report = deadlines_report(today)
    passed = [r for r in report if r["state"] == "passed"]
    upcoming = [r for r in report if r["state"] in ("upcoming", "due-today")]
    return DeadlineAwareness(passed=passed, upcoming=upcoming,
                             next_deadline=upcoming[0] if upcoming else None)
