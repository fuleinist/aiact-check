"""Report renderers: JSON / YAML / markdown / terminal (F5)."""

from __future__ import annotations

import json
from datetime import datetime

from aiact_check import DISCLAIMER, __version__
from aiact_check.classifier import Classification
from aiact_check.config import ProjectConfig
from aiact_check.knowledge import RISK_HIGH, RISK_PROHIBITED, RISK_TRANSPARENCY
from aiact_check.obligations import DeadlineAwareness
from aiact_check.scanner import ScanResult

SCHEMA_VERSION = "1.0"

TIER_LABELS = {
    RISK_PROHIBITED: ("PROHIBITED", "🚫"),
    RISK_HIGH: ("HIGH-RISK", "⚠️ "),
    RISK_TRANSPARENCY: ("TRANSPARENCY RISK", "📢"),
    "limited": ("LIMITED / MINIMAL RISK", "✅"),
    "none": ("NO AI DETECTED", "ℹ️ "),
}


def exit_code_for(tier: str) -> int:
    if tier == RISK_PROHIBITED:
        return 2
    if tier in (RISK_HIGH, RISK_TRANSPARENCY):
        return 1
    return 0


def build_report(
    scan: ScanResult,
    cls: Classification,
    cfg: ProjectConfig,
    obligations: list,
    deadlines: DeadlineAwareness,
) -> dict:
    """Stable-schema machine-readable report."""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "tool": {"name": "aiact-check", "version": __version__},
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "disclaimer": DISCLAIMER,
        "project": {
            "path": scan.project_path,
            "filesScanned": scan.files_scanned,
            "role": cfg.role or "undeclared",
            "market": cfg.market or "undeclared",
            "users": cfg.users or "undeclared",
            "configFile": cfg.source_path,
            "configErrors": list(cfg.errors),
        },
        "scanErrors": list(scan.errors),
        "detections": [d.to_dict() for d in scan.detections],
        "classification": cls.to_dict(),
        "obligations": [o.to_dict() for o in obligations],
        "deadlines": deadlines.to_dict(),
        "exitCode": exit_code_for(cls.tier),
    }


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def render_json(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)


def render_yaml(report: dict) -> str:
    try:
        import yaml  # optional extra
    except ImportError:
        raise RuntimeError(
            "YAML output requires pyyaml. Install with: pip install aiact-check[yaml]"
        ) from None
    return yaml.safe_dump(report, sort_keys=False, allow_unicode=True)


def render_markdown(report: dict) -> str:
    lines: list[str] = []
    tier = report["classification"]["tier"]
    label, icon = TIER_LABELS.get(tier, (tier.upper(), "❓"))
    lines.append("# EU AI Act Compliance Report")
    lines.append("")
    lines.append(f"> ⚠️ **{DISCLAIMER}**")
    lines.append("")
    lines.append(f"- **Project:** `{report['project']['path']}`")
    lines.append(f"- **Generated:** {report['generatedAt']} (aiact-check v{report['tool']['version']})")
    lines.append(f"- **Files scanned:** {report['project']['filesScanned']}")
    lines.append(f"- **Role:** {report['project']['role']} | **EU market:** {report['project']['market']}")
    lines.append("")
    lines.append(f"## Risk classification: {icon} {label}")
    for reason in report["classification"]["tierReasons"]:
        lines.append(f"- {reason}")
    lines.append("")

    detections = report["detections"]
    lines.append(f"## Detections ({len(detections)})")
    if not detections:
        lines.append("- No AI/ML usage signals detected.")
    else:
        lines.append("")
        lines.append("| Kind | Name | Capability | Locations |")
        lines.append("|------|------|------------|-----------|")
        for d in detections:
            locs = ", ".join(f"`{l}`" for l in d["locations"][:3])
            if len(d["locations"]) > 3:
                locs += f" (+{len(d['locations']) - 3})"
            lines.append(f"| {d['kind']} | {d['name']} | {d['capability']} | {locs or '—'} |")
    lines.append("")

    findings = report["classification"]["findings"]
    lines.append(f"## Findings ({len(findings)})")
    if not findings:
        lines.append("- None.")
    for f in findings:
        lines.append("")
        lines.append(f"### [{f['severity'].upper()}] {f['title']}")
        lines.append(f"- **Article:** {f['article']}")
        lines.append(f"- **Why:** {f['why']}")
        if f["locations"]:
            lines.append(f"- **Where:** {', '.join('`' + l + '`' for l in f['locations'][:5])}")
    lines.append("")

    obligations = report["obligations"]
    lines.append(f"## Obligation checklist ({len(obligations)})")
    if not obligations:
        lines.append("- No obligations triggered.")
    else:
        for o in obligations:
            sev = f" **[{o['severity'].upper()}]**" if o["severity"] == "action-required" else ""
            lines.append(f"- [ ] **{o['article']}** ({o['appliesTo']}, deadline {o['deadline']}){sev}: {o['text']}")
            for n in o["notes"]:
                lines.append(f"  - {n}")
    lines.append("")

    lines.append("## Deadline timeline")
    for entry in report["deadlines"]["passed"][-3:]:
        lines.append(f"- ✅ **{entry['date']}** — {entry['title']} (passed {entry['daysSince']} days ago)")
    for entry in report["deadlines"]["upcoming"]:
        lines.append(f"- ⏳ **{entry['date']}** — {entry['title']} ({entry['daysRemaining']} days remaining)")
    lines.append("")
    return "\n".join(lines)


def render_terminal(report: dict) -> str:
    lines: list[str] = []
    tier = report["classification"]["tier"]
    label, icon = TIER_LABELS.get(tier, (tier.upper(), "?"))
    lines.append("")
    lines.append("=" * 64)
    lines.append("  aiact-check — EU AI Act compliance scan")
    lines.append("=" * 64)
    lines.append(f"  Project:  {report['project']['path']}")
    lines.append(f"  Files:    {report['project']['filesScanned']} scanned")
    lines.append(f"  Result:   {icon} {label}")
    lines.append("")
    for reason in report["classification"]["tierReasons"]:
        lines.append(f"    • {reason}")
    findings = report["classification"]["findings"]
    if findings:
        lines.append("")
        lines.append(f"  Findings ({len(findings)}):")
        for f in findings:
            lines.append(f"    [{f['severity'].upper()}] {f['title']} — {f['article']}")
    obligations = report["obligations"]
    if obligations:
        lines.append("")
        lines.append(f"  Obligations ({len(obligations)}):")
        for o in obligations:
            mark = "!!" if o["severity"] == "action-required" else "  "
            lines.append(f"   {mark} [ ] {o['article']}: {o['text'][:90]}")
    nd = report["deadlines"]["nextDeadline"]
    if nd:
        lines.append("")
        lines.append(f"  Next deadline: {nd['date']} — {nd['title']} ({nd['daysRemaining']} days)")
    lines.append("")
    lines.append(f"  Exit code: {report['exitCode']}")
    lines.append(f"  ⚠️  {DISCLAIMER}")
    lines.append("=" * 64)
    return "\n".join(lines)


RENDERERS = {
    "json": render_json,
    "yaml": render_yaml,
    "markdown": render_markdown,
    "terminal": render_terminal,
}
