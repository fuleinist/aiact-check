"""Classifier + config tests (F2, F7)."""

from __future__ import annotations

from aiact_check.classifier import classify
from aiact_check.config import ProjectConfig, load_config
from aiact_check.knowledge import RISK_HIGH, RISK_LIMITED, RISK_NONE, RISK_PROHIBITED, RISK_TRANSPARENCY
from aiact_check.scanner import scan_project


def test_chatbot_tier_transparency(chatbot_project):
    cls = classify(scan_project(chatbot_project), ProjectConfig())
    assert cls.tier in (RISK_TRANSPARENCY, RISK_HIGH, RISK_PROHIBITED)
    assert cls.ai_detected


def test_plain_tier_limited(plain_project):
    cls = classify(scan_project(plain_project), ProjectConfig())
    assert cls.tier == RISK_LIMITED


def test_no_ai_tier_none(no_ai_project):
    cls = classify(scan_project(no_ai_project), ProjectConfig())
    assert cls.tier == RISK_NONE
    assert not cls.ai_detected


def test_prohibited_tier(prohibited_project):
    cls = classify(scan_project(prohibited_project), ProjectConfig())
    assert cls.tier == RISK_PROHIBITED
    assert any(f.severity == RISK_PROHIBITED for f in cls.findings)
    assert any("Art. 5" in f.article for f in cls.findings)


def test_hr_high_risk(hr_project):
    cls = classify(scan_project(hr_project), ProjectConfig())
    assert cls.tier == RISK_HIGH
    assert "employment" in cls.high_risk_domains


def test_deepfake_transparency(deepfake_project):
    cls = classify(scan_project(deepfake_project), ProjectConfig())
    assert cls.tier in (RISK_TRANSPARENCY, RISK_HIGH)
    assert any("Art. 50" in f.article for f in cls.findings)


def test_findings_explain_why(prohibited_project):
    cls = classify(scan_project(prohibited_project), ProjectConfig())
    for f in cls.findings:
        assert f.why and len(f.why) > 20
        assert f.article


def test_override_forces_tier(plain_project):
    cfg = ProjectConfig(override=RISK_HIGH)
    cls = classify(scan_project(plain_project), cfg)
    assert cls.tier == RISK_HIGH
    assert any("override" in r for r in cls.tier_reasons)


def test_override_none_forces_none(chatbot_project):
    cfg = ProjectConfig(override=RISK_NONE)
    cls = classify(scan_project(chatbot_project), cfg)
    assert cls.tier == RISK_NONE


def test_config_chatbot_flag(tmp_path, plain_project):
    cfg = ProjectConfig(chatbot=True)
    cls = classify(scan_project(plain_project), cfg)
    assert cls.tier in (RISK_TRANSPARENCY, RISK_HIGH)
    assert any(f.id == "transparency:chatbot-declared" for f in cls.findings)


def test_config_market_eu(plain_project):
    cls = classify(scan_project(plain_project), ProjectConfig(market="eu"))
    assert cls.eu_market is True


def test_config_market_none(plain_project):
    cls = classify(scan_project(plain_project), ProjectConfig(market="none"))
    assert cls.eu_market is False


def test_load_config_missing_file(tmp_path):
    cfg = load_config(None, tmp_path)
    assert not cfg.declared
    assert cfg.errors == []


def test_load_config_explicit_missing(tmp_path):
    cfg = load_config(tmp_path / "nope.toml", tmp_path)
    assert cfg.errors


def test_load_config_full(tmp_path):
    (tmp_path / "aiact-check.toml").write_text(
        '[project]\nrole = "provider"\nmarket = "eu"\nusers = "consumers"\n\n'
        '[classification]\nchatbot = true\ngenerates_content = ["text", "audio"]\n',
        encoding="utf-8",
    )
    cfg = load_config(None, tmp_path)
    assert cfg.role == "provider" and cfg.market == "eu" and cfg.users == "consumers"
    assert cfg.chatbot is True
    assert cfg.generates_content == ["text", "audio"]
    assert cfg.declared


def test_load_config_invalid_values(tmp_path):
    (tmp_path / "aiact-check.toml").write_text(
        '[project]\nrole = "wizard"\nmarket = "mars"\n\n[classification]\noverride = "banana"\n',
        encoding="utf-8",
    )
    cfg = load_config(None, tmp_path)
    assert len(cfg.errors) == 3


def test_load_config_broken_toml(tmp_path):
    (tmp_path / "aiact-check.toml").write_text("[[[broken", encoding="utf-8")
    cfg = load_config(None, tmp_path)
    assert cfg.errors


def test_config_generates_content_transparency(tmp_path, plain_project):
    cfg = ProjectConfig(generates_content=["text"])
    cls = classify(scan_project(plain_project), cfg)
    assert any(f.id == "transparency:synthetic-declared" for f in cls.findings)


def test_config_high_risk_domain(plain_project):
    cfg = ProjectConfig(high_risk_domain="employment")
    cls = classify(scan_project(plain_project), cfg)
    assert cls.tier == RISK_HIGH
    assert "employment" in cls.high_risk_domains


def test_config_unknown_domain_info_finding(plain_project):
    cfg = ProjectConfig(high_risk_domain="astrology")
    cls = classify(scan_project(plain_project), cfg)
    assert any(f.id.startswith("config-unknown-domain") for f in cls.findings)


def test_classification_serialization(plain_project):
    cls = classify(scan_project(plain_project), ProjectConfig())
    d = cls.to_dict()
    assert set(d.keys()) == {"tier", "tierReasons", "aiDetected", "euMarket", "highRiskDomains", "findings"}
