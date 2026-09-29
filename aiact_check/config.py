"""aiact-check.toml loading and merging (F7)."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    tomllib = None


@dataclass
class ProjectConfig:
    role: str = ""  # provider | deployer | both | ""
    market: str = ""  # eu | none | ""
    users: str = ""  # consumers | business | internal | ""
    override: str = ""  # forced risk tier
    chatbot: bool | None = None
    generates_content: list[str] = field(default_factory=list)
    deepfake: bool | None = None
    high_risk_domain: str = ""
    exclude: list[str] = field(default_factory=list)
    source_path: str | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def declared(self) -> bool:
        return bool(
            self.role or self.market or self.users or self.override
            or self.chatbot is not None or self.generates_content
            or self.deepfake is not None or self.high_risk_domain
        )


def load_config(path: str | Path | None, project_root: str | Path) -> ProjectConfig:
    """Load config from explicit path or <project_root>/aiact-check.toml. Missing file = empty config."""
    cfg = ProjectConfig()
    candidate = Path(path) if path else Path(project_root) / "aiact-check.toml"
    if not candidate.is_file():
        if path:
            cfg.errors.append(f"config file not found: {candidate}")
        return cfg

    if tomllib is None:
        cfg.errors.append(
            "tomllib unavailable (Python <3.11); config ignored. "
            "Install Python 3.11+ or remove aiact-check.toml."
        )
        cfg.source_path = str(candidate)
        return cfg

    try:
        data = tomllib.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        cfg.errors.append(f"failed to parse {candidate}: {exc}")
        return cfg

    cfg.source_path = str(candidate)
    project = data.get("project", {})
    if isinstance(project, dict):
        cfg.role = str(project.get("role", "")).strip().lower()
        cfg.market = str(project.get("market", "")).strip().lower()
        cfg.users = str(project.get("users", "")).strip().lower()

    classification = data.get("classification", {})
    if isinstance(classification, dict):
        cfg.override = str(classification.get("override", "")).strip().lower()
        if "chatbot" in classification:
            cfg.chatbot = bool(classification.get("chatbot"))
        if "deepfake" in classification:
            cfg.deepfake = bool(classification.get("deepfake"))
        gc = classification.get("generates_content", [])
        if isinstance(gc, list):
            cfg.generates_content = [str(x).strip().lower() for x in gc if str(x).strip()]
        cfg.high_risk_domain = str(classification.get("high_risk_domain", "")).strip().lower()

    scan_section = data.get("scan", {})
    if isinstance(scan_section, dict):
        ex = scan_section.get("exclude", [])
        if isinstance(ex, list):
            cfg.exclude = [str(x) for x in ex if str(x).strip()]

    # Validation warnings (non-fatal)
    if cfg.role and cfg.role not in ("provider", "deployer", "both"):
        cfg.errors.append(f"unknown project.role '{cfg.role}' (expected provider|deployer|both)")
    if cfg.market and cfg.market not in ("eu", "none"):
        cfg.errors.append(f"unknown project.market '{cfg.market}' (expected eu|none)")
    valid_overrides = ("prohibited", "high-risk", "transparency", "limited", "none")
    if cfg.override and cfg.override not in valid_overrides:
        cfg.errors.append(f"unknown classification.override '{cfg.override}' (expected one of {valid_overrides})")
    return cfg
