"""Test for check_template_schema_alignment lint rule (Wave 14 hardening).

Prevents regression of template/pipeline/_meta.json lag behind operator pipeline
(wave 13 found 11 missing keys including stale_days, shelf_life_*, valid_verifier_predictions).
"""

import json
from pathlib import Path

from path_bootstrap import load_rules_lint_module


def _write_pipeline(data_dir: Path, meta: dict):
    (data_dir / "pipeline" / "items").mkdir(parents=True, exist_ok=True)
    (data_dir / "pipeline" / "_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False),
        encoding="utf-8",
    )


def test_template_missing_key_reports_warn(tmp_path, monkeypatch):
    module = load_rules_lint_module("rules_lint_template_align")
    _write_pipeline(
        tmp_path / "data" / "template",
        {"thresholds": {"performance": {"low": {"v": 1}}}},
    )
    _write_pipeline(
        tmp_path / "data" / "opA",
        {"thresholds": {"performance": {"low": {"v": 1}}, "stale_days": {"inbox": 7}}},
    )
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_template_schema_alignment(errors)
    assert any(
        e["check"] == "template_schema_drift" and "opA" in e["message"] for e in errors
    )


def test_template_equal_no_warn(tmp_path, monkeypatch):
    module = load_rules_lint_module("rules_lint_template_align")
    meta = {"thresholds": {"stale_days": {"inbox": 7}}, "valid_verifier_predictions": ["high"]}
    _write_pipeline(tmp_path / "data" / "template", meta)
    _write_pipeline(tmp_path / "data" / "opA", meta)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_template_schema_alignment(errors)
    assert errors == []


def test_template_superset_no_warn(tmp_path, monkeypatch):
    """Template 多出 description 類自描述欄位 OK。"""
    module = load_rules_lint_module("rules_lint_template_align")
    _write_pipeline(
        tmp_path / "data" / "template",
        {"description": "template file", "thresholds": {"stale_days": {"inbox": 7}}},
    )
    _write_pipeline(
        tmp_path / "data" / "opA",
        {"thresholds": {"stale_days": {"inbox": 7}}},
    )
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_template_schema_alignment(errors)
    assert errors == []


def test_skips_missing_template(tmp_path, monkeypatch):
    module = load_rules_lint_module("rules_lint_template_align")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_template_schema_alignment(errors)
    assert errors == []


def test_skips_cache_and_template_dirs(tmp_path, monkeypatch):
    """不應把 template / .cache 自己當 operator 比對。"""
    module = load_rules_lint_module("rules_lint_template_align")
    _write_pipeline(
        tmp_path / "data" / "template",
        {"thresholds": {"stale_days": {"inbox": 7}}},
    )
    (tmp_path / "data" / ".cache").mkdir(parents=True)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_template_schema_alignment(errors)
    assert errors == []
