"""Test for check_skill_description_version_sync lint rule (Wave 26 hardening).

Wave 25 found 6 SKILL description strings with stale vX.YY drift from frontmatter
version (topic-researcher v1.5 vs v1.05, trend-adapter v2.0 vs v1.20, etc).
This rule catches future drift of the same class.
"""

from pathlib import Path

from path_bootstrap import load_rules_lint_module


def _write_skill(dir_: Path, description: str, version: str):
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / "SKILL.md").write_text(
        f"---\nname: test-skill\ndescription: {description}\nversion: {version}\n---\n\n# Body\n",
        encoding="utf-8",
    )


def test_drift_reports_error(tmp_path, monkeypatch):
    module = load_rules_lint_module("rules_lint_desc_version")
    _write_skill(tmp_path / "02-skill-factory" / "test-skill", "工具 v1.5 — desc", "1.05")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_skill_description_version_sync(errors)
    assert any(
        e["check"] == "skill_description_version_drift"
        and "v1.5" in e["message"]
        and "1.05" in e["message"]
        for e in errors
    )


def test_aligned_no_error(tmp_path, monkeypatch):
    module = load_rules_lint_module("rules_lint_desc_version")
    _write_skill(tmp_path / "02-skill-factory" / "test-skill", "工具 v1.05 — desc", "1.05")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_skill_description_version_sync(errors)
    assert errors == []


def test_no_version_in_desc_no_error(tmp_path, monkeypatch):
    """Description without vX.YY inline 允許（短 description）。"""
    module = load_rules_lint_module("rules_lint_desc_version")
    _write_skill(tmp_path / "02-skill-factory" / "test-skill", "簡短工具說明", "1.05")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_skill_description_version_sync(errors)
    assert errors == []


def test_uppercase_V_also_caught(tmp_path, monkeypatch):
    module = load_rules_lint_module("rules_lint_desc_version")
    _write_skill(tmp_path / "02-skill-factory" / "test-skill", "工具 V2.0 — desc", "1.20")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_skill_description_version_sync(errors)
    assert any(e["check"] == "skill_description_version_drift" for e in errors)


def test_skips_shared_references(tmp_path, monkeypatch):
    """shared-references/ 不是 skill、不該掃。"""
    module = load_rules_lint_module("rules_lint_desc_version")
    _write_skill(tmp_path / "02-skill-factory" / "shared-references", "v1.0 — wrong", "2.0")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_skill_description_version_sync(errors)
    assert errors == []
