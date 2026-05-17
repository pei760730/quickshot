"""Test for check_manifest_files_exist lint rule (Wave 11 hardening).

Prevents regression of the orphan workflow-analytics.md entry pattern
(lived in manifest as version 3.0 for ~2 months after commit 8bd298f
deleted the file).
"""

import json
from pathlib import Path

from path_bootstrap import load_rules_lint_module


def test_orphan_contract_entry_reports_error(tmp_path, monkeypatch):
    module = load_rules_lint_module("rules_lint_manifest_exist")
    fake_manifest = {
        "_meta": {"engine_version": "9.99"},
        "contract_files": {"docs/phantom.md": "1.0"},
        "internal_files": {},
    }
    (tmp_path / "engine-manifest.json").write_text(
        json.dumps(fake_manifest, ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_manifest_files_exist(errors)
    assert any(e["check"] == "manifest_file_missing" and "docs/phantom.md" in e["message"] for e in errors)


def test_orphan_internal_entry_reports_error(tmp_path, monkeypatch):
    module = load_rules_lint_module("rules_lint_manifest_exist")
    fake_manifest = {
        "_meta": {"engine_version": "9.99"},
        "contract_files": {},
        "internal_files": {"scripts/gone.py": None},
    }
    (tmp_path / "engine-manifest.json").write_text(
        json.dumps(fake_manifest, ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_manifest_files_exist(errors)
    assert any(e["check"] == "manifest_file_missing" and "scripts/gone.py" in e["message"] for e in errors)


def test_existing_files_no_error(tmp_path, monkeypatch):
    module = load_rules_lint_module("rules_lint_manifest_exist")
    (tmp_path / "real.md").write_text("hi", encoding="utf-8")
    fake_manifest = {
        "_meta": {"engine_version": "9.99"},
        "contract_files": {"real.md": "1.0"},
        "internal_files": {},
    }
    (tmp_path / "engine-manifest.json").write_text(
        json.dumps(fake_manifest, ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_manifest_files_exist(errors)
    assert errors == []
