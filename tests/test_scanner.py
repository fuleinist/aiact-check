"""Scanner tests (F1)."""

from __future__ import annotations

from pathlib import Path

from aiact_check.scanner import (
    parse_manifest,
    scan_project,
    _parse_cargo,
    _parse_go_mod,
    _parse_package_json,
    _parse_pyproject,
    _parse_requirements,
)


def test_scan_chatbot_detects_openai(chatbot_project):
    result = scan_project(chatbot_project)
    deps = {d.name.lower() for d in result.detections if d.kind == "dependency"}
    assert "openai" in deps
    caps = result.capabilities()
    assert "llm-provider-sdk" in caps


def test_scan_chatbot_code_signals(chatbot_project):
    result = scan_project(chatbot_project)
    ids = {d.name for d in result.detections if d.kind == "code-signal"}
    assert "llm-api-openai" in ids
    assert "prompt-construction" in ids


def test_scan_records_locations(chatbot_project):
    result = scan_project(chatbot_project)
    openai_dep = next(d for d in result.detections if d.name.lower() == "openai")
    assert "requirements.txt" in openai_dep.locations


def test_scan_plain_project_limited(plain_project):
    result = scan_project(plain_project)
    caps = result.capabilities()
    assert "ml-framework" in caps
    ids = {d.name for d in result.detections if d.kind == "code-signal"}
    assert "social-scoring" not in ids


def test_scan_no_ai_project(no_ai_project):
    result = scan_project(no_ai_project)
    assert result.detections == []
    assert result.files_scanned > 0


def test_scan_prohibited_signal(prohibited_project):
    result = scan_project(prohibited_project)
    ids = {d.name for d in result.detections if d.kind == "code-signal"}
    assert "social-scoring" in ids


def test_scan_hr_signal(hr_project):
    result = scan_project(hr_project)
    ids = {d.name for d in result.detections if d.kind == "code-signal"}
    assert "hr-screening" in ids
    caps = result.capabilities()
    assert "local-model-runtime" in caps or "llm-provider-sdk" in caps or "agent-framework" in caps


def test_scan_node_package_json(node_project):
    result = scan_project(node_project)
    deps = {d.name.lower() for d in result.detections if d.kind == "dependency"}
    assert "@anthropic-ai/sdk" in deps


def test_scan_deepfake_signals(deepfake_project):
    result = scan_project(deepfake_project)
    ids = {d.name for d in result.detections if d.kind == "code-signal"}
    assert "deepfake-signals" in ids or "image-generation" in ids or "face-recognition" in ids


def test_scan_missing_dir(tmp_path):
    result = scan_project(tmp_path / "does-not-exist")
    assert result.errors


def test_scan_skips_venv_and_node_modules(tmp_path):
    root = tmp_path / "proj"
    (root / "node_modules" / "openai").mkdir(parents=True)
    (root / "node_modules" / "openai" / "index.js").write_text("import openai", encoding="utf-8")
    (root / ".venv").mkdir()
    (root / ".venv" / "x.py").write_text("import anthropic", encoding="utf-8")
    result = scan_project(root)
    assert result.detections == []


def test_parse_requirements_variants():
    text = """
    flask>=3.0
    openai==1.2.3
    # comment
    -r other.txt
    requests[socks]~=2.0
    """
    pkgs = _parse_requirements(text)
    assert "flask" in pkgs and "openai" in pkgs and "requests" in pkgs
    assert "-r" not in pkgs


def test_parse_package_json_sections():
    text = '{"dependencies": {"openai": "^1"}, "devDependencies": {"langchain": "^0.1"}, "scripts": {}}'
    pkgs = _parse_package_json(text)
    assert "openai" in pkgs and "langchain" in pkgs


def test_parse_package_json_invalid():
    assert _parse_package_json("{not json") == []


def test_parse_pyproject_dependencies():
    text = '[project]\ndependencies = [\n  "openai>=1",\n  "flask",\n]\n'
    assert set(_parse_pyproject(text)) == {"openai", "flask"}


def test_parse_cargo_dependencies():
    text = '[package]\nname = "x"\n\n[dependencies]\nollama-rs = "0.2"\nserde = "1"\n'
    pkgs = _parse_cargo(text)
    assert "ollama-rs" in pkgs and "serde" in pkgs


def test_parse_go_mod_require_block():
    text = 'module x\n\ngo 1.22\n\nrequire (\n\tgithub.com/ollama/ollama v0.1.0\n)\n'
    pkgs = _parse_go_mod(text)
    assert any("ollama" in p for p in pkgs)


def test_parse_manifest_dispatch(tmp_path):
    p = tmp_path / "requirements.txt"
    assert parse_manifest(p, "openai\n") == ["openai"]


def test_scan_result_serialization(chatbot_project):
    result = scan_project(chatbot_project)
    d = result.detections[0].to_dict()
    assert set(d.keys()) == {"kind", "name", "capability", "note", "locations"}
