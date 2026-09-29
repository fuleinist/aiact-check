"""Obligation + deadline tests (F3, F4)."""

from __future__ import annotations

from datetime import date

from aiact_check.classifier import classify
from aiact_check.config import ProjectConfig
from aiact_check.knowledge import DEADLINES
from aiact_check.obligations import (
    build_obligations,
    deadline_awareness,
    deadline_status,
    deadlines_report,
    gpai_obligations,
)
from aiact_check.scanner import scan_project


def test_deadlines_report_has_five_milestones():
    report = deadlines_report()
    assert len(report) == len(DEADLINES) == 5


def test_deadline_status_passed():
    status = deadline_status(DEADLINES[0], today=date(2026, 9, 29))
    assert status["state"] == "passed"
    assert status["daysSince"] > 0


def test_deadline_status_upcoming():
    status = deadline_status(DEADLINES[-1], today=date(2026, 9, 29))
    assert status["state"] == "upcoming"
    assert status["daysRemaining"] > 0


def test_deadline_status_due_today():
    status = deadline_status(DEADLINES[0], today=date(2025, 2, 2))
    assert status["state"] == "due-today"


def test_deadline_awareness_next_is_first_upcoming():
    awareness = deadline_awareness(today=date(2026, 9, 29))
    assert awareness.next_deadline is not None
    assert awareness.next_deadline["date"] == "2027-08-02"
    assert len(awareness.passed) == 3
    assert len(awareness.upcoming) == 2


def test_deadline_awareness_all_passed():
    awareness = deadline_awareness(today=date(2030, 1, 1))
    assert awareness.next_deadline is None
    assert len(awareness.passed) == 5


def test_no_obligations_when_no_ai(no_ai_project):
    cls = classify(scan_project(no_ai_project), ProjectConfig())
    obligations = build_obligations(cls, ProjectConfig())
    assert obligations == []


def test_limited_tier_gets_ai_literacy(plain_project):
    cls = classify(scan_project(plain_project), ProjectConfig())
    obligations = build_obligations(cls, ProjectConfig())
    ids = {o.id for o in obligations}
    assert "ai-literacy" in ids


def test_transparency_obligations(chatbot_project):
    cfg = ProjectConfig(chatbot=True, generates_content=["text"])
    cls = classify(scan_project(chatbot_project), cfg)
    obligations = build_obligations(cls, cfg)
    ids = {o.id for o in obligations}
    assert "art50-1-disclose" in ids
    assert "art50-2-mark" in ids
    assert all(o.article for o in obligations)


def test_high_risk_obligation_set(hr_project):
    cls = classify(scan_project(hr_project), ProjectConfig())
    obligations = build_obligations(cls, ProjectConfig())
    ids = {o.id for o in obligations}
    expected = {"hr-1-risk-mgmt", "hr-2-data-gov", "hr-3-tech-docs", "hr-4-logging",
                "hr-5-transparency", "hr-6-human-oversight", "hr-7-robustness",
                "hr-8-qms", "hr-9-conformity", "hr-10-registration"}
    assert expected <= ids


def test_prohibited_gets_stop_obligation(prohibited_project):
    cls = classify(scan_project(prohibited_project), ProjectConfig())
    obligations = build_obligations(cls, ProjectConfig())
    ids = {o.id for o in obligations}
    assert "prohibited-stop" in ids


def test_passed_deadline_severity_action_required(chatbot_project):
    cfg = ProjectConfig(chatbot=True)
    cls = classify(scan_project(chatbot_project), cfg)
    obligations = build_obligations(cls, cfg, today=date(2026, 9, 29))
    art50 = next(o for o in obligations if o.id == "art50-1-disclose")
    assert art50.severity == "action-required"  # Art. 50 deadline 2026-08-02 passed


def test_future_deadline_severity_info(hr_project):
    cls = classify(scan_project(hr_project), ProjectConfig())
    obligations = build_obligations(cls, ProjectConfig(), today=date(2026, 9, 29))
    hr_docs = next(o for o in obligations if o.id == "hr-3-tech-docs")
    assert hr_docs.severity == "info"  # 2027-12-02 far off


def test_market_none_adds_note(hr_project):
    cfg = ProjectConfig(market="none")
    cls = classify(scan_project(hr_project), cfg)
    obligations = build_obligations(cls, cfg)
    hr_items = [o for o in obligations if o.id.startswith("hr-")]
    assert hr_items and all(any("market='none'" in n for n in o.notes) for o in hr_items)


def test_gpai_obligations_when_training():
    obligations = gpai_obligations(ProjectConfig(), trains_model=True)
    ids = {o.id for o in obligations}
    assert {"gpai-docs", "gpai-copyright", "gpai-training-summary"} <= ids


def test_gpai_obligations_empty_when_not_training():
    assert gpai_obligations(ProjectConfig(), trains_model=False) == []


def test_obligation_serialization(plain_project):
    cls = classify(scan_project(plain_project), ProjectConfig())
    obligations = build_obligations(cls, ProjectConfig())
    d = obligations[0].to_dict()
    assert set(d.keys()) == {"id", "article", "appliesTo", "text", "deadline", "status", "severity", "notes"}
