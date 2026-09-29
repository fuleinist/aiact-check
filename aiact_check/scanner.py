"""Project scanning: file discovery, manifest parsing, code heuristics (F1)."""

from __future__ import annotations

import fnmatch
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from aiact_check.knowledge import CODE_SIGNALS, package_capability

MAX_FILE_BYTES = 2_000_000
SOURCE_SUFFIXES = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".rs", ".go", ".rb",
    ".php", ".java", ".kt", ".cs", ".c", ".h", ".cpp", ".hpp", ".ipynb",
    ".svelte", ".vue", ".swift", ".scala", ".r", ".jl", ".ex", ".exs",
}
MANIFEST_NAMES = {
    "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "pipfile",
    "package.json", "cargo.toml", "go.mod", "gemfile", "build.gradle",
    "pom.xml", "composer.json", "environment.yml", "poetry.lock",
}
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    "env", ".tox", ".nox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "dist", "build", ".eggs", "target", "vendor", ".next", ".nuxt",
    "site-packages", ".idea", ".vscode", "coverage", "htmlcov",
}


@dataclass
class Detection:
    """One detected AI usage signal."""
    kind: str  # dependency | code-signal
    name: str  # package name or signal id
    capability: str
    note: str
    locations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "name": self.name,
            "capability": self.capability,
            "note": self.note,
            "locations": list(self.locations),
        }


@dataclass
class ScanResult:
    project_path: str
    files_scanned: int
    detections: list[Detection] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def capabilities(self) -> set[str]:
        return {d.capability for d in self.detections}


def _walk(root: Path):
    """Yield candidate files under root, skipping ignored directories."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS and not d.endswith(".egg-info")]
        for fn in filenames:
            yield Path(dirpath) / fn


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Manifest parsing
# ---------------------------------------------------------------------------

_REQ_LINE = re.compile(r"^\s*([A-Za-z0-9_.\-/@]+)\s*(?:[<>=!~\[;(]|$)")


def _parse_requirements(text: str) -> list[str]:
    pkgs = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = _REQ_LINE.match(line)
        if m:
            pkgs.append(m.group(1))
    return pkgs


def _parse_package_json(text: str) -> list[str]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    pkgs = []
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        section = data.get(key)
        if isinstance(section, dict):
            pkgs.extend(section.keys())
    return pkgs


def _parse_cargo(text: str) -> list[str]:
    pkgs = []
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_deps = "dependencies" in stripped
            continue
        if in_deps:
            m = re.match(r"^([A-Za-z0-9_\-]+)\s*=", stripped)
            if m:
                pkgs.append(m.group(1))
    return pkgs


def _parse_go_mod(text: str) -> list[str]:
    pkgs = []
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_block = True
            continue
        if in_block and stripped == ")":
            in_block = False
            continue
        if in_block:
            parts = stripped.split()
            if parts and not parts[0].startswith("//"):
                pkgs.append(parts[0])
        elif stripped.startswith("require "):
            parts = stripped.split()
            if len(parts) >= 2:
                pkgs.append(parts[1])
    return pkgs


def _parse_pyproject(text: str) -> list[str]:
    """Light regex-based dep extraction from pyproject.toml (avoid hard toml dep here)."""
    pkgs = []
    m = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.S)
    if m:
        for item in re.findall(r"[\"']([^\"']+)[\"']", m.group(1)):
            name = re.split(r"[<>=!~\[;( ]", item, 1)[0].strip()
            if name:
                pkgs.append(name)
    return pkgs


def _parse_composer(text: str) -> list[str]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    pkgs = []
    for key in ("require", "require-dev"):
        section = data.get(key)
        if isinstance(section, dict):
            pkgs.extend(k for k in section.keys() if k != "php")
    return pkgs


def parse_manifest(path: Path, text: str) -> list[str]:
    name = path.name.lower()
    if name in ("requirements.txt", "environment.yml"):
        return _parse_requirements(text)
    if name == "package.json":
        return _parse_package_json(text)
    if name == "cargo.toml":
        return _parse_cargo(text)
    if name == "go.mod":
        return _parse_go_mod(text)
    if name == "pyproject.toml":
        return _parse_pyproject(text)
    if name == "composer.json":
        return _parse_composer(text)
    if name == "gemfile":
        return [w.strip("'\"") for w in re.findall(r"gem\s+[\"']([^\"']+)[\"']", text)]
    if name == "pipfile":
        return _parse_requirements(text)
    if name == "setup.py":
        return re.findall(r"[\"']([A-Za-z0-9_.\-]+)[\"']\s*(?:,|>)", re.search(r"install_requires\s*=\s*\[(.*?)\]", text, re.S).group(1)) if re.search(r"install_requires\s*=\s*\[(.*?)\]", text, re.S) else []
    return []


def _normalize_pkg(pkg: str) -> str:
    """Normalize package names: strip scope punctuation differences, lowercase."""
    p = pkg.strip().lower()
    p = p.replace("_", "-") if not p.startswith("@") else p.replace("_", "-")
    return p


# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------

def scan_project(root: str | Path, exclude: list[str] | None = None) -> ScanResult:
    root = Path(root).resolve()
    result = ScanResult(project_path=str(root), files_scanned=0)
    exclude = exclude or []
    if not root.is_dir():
        result.errors.append(f"not a directory: {root}")
        return result

    compiled = [(s, re.compile(s.pattern, re.IGNORECASE)) for s in CODE_SIGNALS]
    dep_hits: dict[tuple[str, str], Detection] = {}
    sig_hits: dict[str, Detection] = {}

    for path in _walk(root):
        name = path.name.lower()
        suffix = path.suffix.lower()
        is_manifest = name in MANIFEST_NAMES
        is_source = suffix in SOURCE_SUFFIXES
        if not (is_manifest or is_source):
            continue
        text = _read_text(path)
        if text is None:
            continue
        rel = _rel(path, root)
        if exclude and any(fnmatch.fnmatch(rel, pat) for pat in exclude):
            continue
        result.files_scanned += 1

        if is_manifest:
            for pkg in parse_manifest(path, text):
                norm = _normalize_pkg(pkg)
                cap = package_capability(norm) or package_capability(pkg.strip().lower())
                if cap:
                    key = (norm, cap)
                    det = dep_hits.get(key)
                    if det is None:
                        det = Detection(kind="dependency", name=pkg, capability=cap,
                                        note=f"AI/ML package '{pkg}' declared in manifest ({cap})")
                        dep_hits[key] = det
                    if rel not in det.locations:
                        det.locations.append(rel)

        if is_source or is_manifest:
            for signal, rx in compiled:
                if rx.search(text):
                    det = sig_hits.get(signal.id)
                    if det is None:
                        det = Detection(kind="code-signal", name=signal.id,
                                        capability=signal.capability, note=signal.note)
                        sig_hits[signal.id] = det
                    if rel not in det.locations and len(det.locations) < 20:
                        det.locations.append(rel)

    result.detections.extend(dep_hits.values())
    result.detections.extend(sig_hits.values())
    return result
