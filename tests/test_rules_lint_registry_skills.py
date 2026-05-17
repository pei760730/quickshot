"""Tests for registry/disk skill completeness severity behavior."""

from path_bootstrap import load_rules_lint_module


def test_registry_has_skill_but_stub_missing_reports_error(tmp_path, monkeypatch):
    module = load_rules_lint_module("rules_lint_registry_skills")
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    errors = []
    module.check_registry_completeness({"valid_skills": ["flow-operator"]}, errors)

    assert any(
        e["check"] == "disk_missing_skill"
        and e["severity"] == "ERROR"
        and "flow-operator" in e["message"]
        for e in errors
    )


def test_stub_has_skill_but_registry_missing_reports_warn(tmp_path, monkeypatch):
    module = load_rules_lint_module("rules_lint_registry_skills")
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "flow-operator.md").write_text("# stub\n", encoding="utf-8")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    errors = []
    module.check_registry_completeness({"valid_skills": []}, errors)

    assert any(
        e["check"] == "registry_missing_skill"
        and e["severity"] == "WARN"
        and "flow-operator" in e["message"]
        for e in errors
    )


def test_vnext_registry_skill_without_stub_is_temporarily_allowed(tmp_path, monkeypatch):
    module = load_rules_lint_module("rules_lint_registry_skills")
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    errors = []
    module.check_registry_completeness({"valid_skills": ["orientation"]}, errors)

    assert not any(e["check"] == "disk_missing_skill" for e in errors)
