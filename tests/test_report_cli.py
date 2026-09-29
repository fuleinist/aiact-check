"""Report renderer + CLI end-to-end tests (F5, F6, AC1-AC5, AC8)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aiact_check.classifier import classify
from aiact_check.cli import main
from aiact_check.config import ProjectConfig, load_config
from aiact_check.docs import init_docs
from aiact_check.obligations import build_obligations, deadline_awareness
from aiact_check.report import build_report, exit_code_for, render_json, render_markdown, render_terminal, render_yaml
from aiact_check.scanner import scan_project


def _make_report(project: Path, cfg: ProjectConfig | None = None) -> dict:
    cfg = cfg or ProjectConfig()
    scan = scan_project(project)
    cls = classify(scan, cfg)
    obligations = build_obligations(cls, cfg)
    return build_report(scan, cls, cfg, obligations, deadline_awareness())


def test_report_json_schema(chatbot_project):
    report = _make_report(chatbot_project)
    parsed = json.loads(render_json(report))  # AC3
    for key in ("schemaVersion", "tool", "generatedAt", "disclaimer", "project",
                "detections", "classification", "obligations", "deadlines", "exitCode"):
        assert key in parsed
    assert parsed["schemaVersion"] == "1.0"


def test_report_markdown_renders(chatbot_project):
    md = render_markdown(_make_report(chatbot_project))
    assert "# EU AI Act Compliance Report" in md
    assert "Risk classification" in md


def test_report_terminal_renders(plain_project):
    text = render_terminal(_make_report(plain_project))
    assert "aiact-check" in text
    assert "LIMITED" in text


def test_report_yaml_without_pyyaml_or_with(chatbot_project):
    report = _make_report(chatbot_project)
    try:
        import yaml  # noqa: F401
        text = render_yaml(report)
        assert "classification" in text
    except ImportError:
        with pytest.raises(RuntimeError, match="pyyaml"):
            render_yaml(report)


def test_exit_codes():
    assert exit_code_for("prohibited") == 2
    assert exit_code_for("high-risk") == 1
    assert exit_code_for("transparency") == 1
    assert exit_code_for("limited") == 0
    assert exit_code_for("none") == 0


# ---------------------------------------------------------------------------
# CLI end-to-end (AC1, AC2, AC5, AC8)
# ---------------------------------------------------------------------------

def test_cli_scan_chatbot_exit_1(chatbot_project, capsys):
    code = main(["scan", str(chatbot_project)])  # AC1
    out = capsys.readouterr().out
    assert code == 1
    assert "TRANSPARENCY" in out or "HIGH-RISK" in out


def test_cli_scan_prohibited_exit_2(prohibited_project, capsys):
    code = main(["scan", str(prohibited_project)])  # AC2
    out = capsys.readouterr().out
    assert code == 2
    assert "PROHIBITED" in out


def test_cli_scan_plain_exit_0(plain_project):
    assert main(["scan", str(plain_project)]) == 0


def test_cli_scan_no_ai_exit_0(no_ai_project):
    assert main(["scan", str(no_ai_project)]) == 0


def test_cli_scan_json_to_file(chatbot_project, tmp_path):
    out_file = tmp_path / "report.json"
    code = main(["scan", str(chatbot_project), "--format", "json", "--output", str(out_file), "--quiet"])
    assert code == 1
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["classification"]["aiDetected"] is True


def test_cli_scan_markdown(chatbot_project, capsys):
    code = main(["scan", str(chatbot_project), "--format", "markdown"])
    out = capsys.readouterr().out
    assert code == 1
    assert "# EU AI Act Compliance Report" in out


def test_cli_deadlines(capsys):
    code = main(["deadlines"])  # AC4
    out = capsys.readouterr().out
    assert code == 0
    assert "2025-02-02" in out and "2027-12-02" in out
    assert "PASSED" in out and "UPCOMING" in out


def test_cli_init_docs_creates_files(tmp_path):
    code = main(["init-docs", str(tmp_path)])  # AC5
    assert code == 0
    docs = tmp_path / "aiact-compliance"
    for name in ("AI_POLICY.md", "TECHNICAL_DOCUMENTATION.md", "TRANSPARENCY_NOTICE.md", "CHECKLIST.md"):
        assert (docs / name).is_file()


def test_cli_init_docs_second_run_skips(tmp_path):
    assert main(["init-docs", str(tmp_path)]) == 0
    code = main(["init-docs", str(tmp_path)])  # AC5: graceful skip
    assert code == 1


def test_cli_init_docs_force(tmp_path):
    main(["init-docs", str(tmp_path)])
    marker = tmp_path / "aiact-compliance" / "AI_POLICY.md"
    marker.write_text("modified", encoding="utf-8")
    code = main(["init-docs", str(tmp_path), "--force"])
    assert code == 0
    assert "modified" not in marker.read_text(encoding="utf-8")


def test_cli_init_docs_with_report(chatbot_project, tmp_path):
    report_file = tmp_path / "report.json"
    report = _make_report(chatbot_project)
    report_file.write_text(render_json(report), encoding="utf-8")
    code = main(["init-docs", str(tmp_path), "--report", str(report_file)])
    assert code == 0
    checklist = (tmp_path / "aiact-compliance" / "CHECKLIST.md").read_text(encoding="utf-8")
    assert "Risk classification" in checklist
    assert "Art. 4" in checklist


def test_cli_init_docs_bad_report(tmp_path):
    code = main(["init-docs", str(tmp_path), "--report", str(tmp_path / "missing.json")])
    assert code == 3


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "0.1.0" in capsys.readouterr().out


def test_cli_scan_with_config_override(plain_project, tmp_path):  # AC6
    cfg_file = tmp_path / "aiact-check.toml"
    cfg_file.write_text('[classification]\noverride = "high-risk"\n', encoding="utf-8")
    code = main(["scan", str(plain_project), "--config", str(cfg_file)])
    assert code == 1


def test_docs_module_directly(tmp_path):
    created, skipped, errors = init_docs(tmp_path)
    assert len(created) == 4 and not skipped and not errors
    created2, skipped2, errors2 = init_docs(tmp_path)
    assert not created2 and len(skipped2) == 4 and not errors2
