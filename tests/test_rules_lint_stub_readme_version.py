"""Tests for check_skill_stub_readme_version_sync.

Catches drift between SKILL.md frontmatter version and
(1) .claude/skills/<name>.md stub description
(2) 02-skill-factory/README.md skill table

Background: PR #12/#13 follow-up found stub & README versions drifting
independently of SKILL.md frontmatter (generation README v1.3 vs SKILL v1.4,
orientation stub v2.0 vs SKILL v2.1, harden stub v2.0 vs SKILL v2.1).
The existing check_skill_description_version_sync only validates SKILL.md's
own description, missing this cross-file drift.
"""

from pathlib import Path

from path_bootstrap import load_rules_lint_module


def _write_skill(skill_root: Path, name: str, version: str, desc: str = ""):
    d = skill_root / name
    d.mkdir(parents=True, exist_ok=True)
    desc_line = desc or f"{name} 工具說明"
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {desc_line}\nversion: {version}\n---\n\n# Body\n",
        encoding="utf-8",
    )


def _write_stub(stub_root: Path, name: str, desc: str):
    stub_root.mkdir(parents=True, exist_ok=True)
    (stub_root / f"{name}.md").write_text(
        f"---\nname: {name}\ndescription: {desc}\n---\n\nRead and follow 02-skill-factory/{name}/SKILL.md\n",
        encoding="utf-8",
    )


def _write_readme(skill_root: Path, rows: list[tuple[str, str]]):
    body = "# Skill list\n\n| tier | skill | ver | desc |\n|---|---|---|---|\n"
    for name, ver in rows:
        body += f"| Core | `{name}` | v{ver} | sample |\n"
    (skill_root / "README.md").write_text(body, encoding="utf-8")


def test_stub_drift_reports_error(tmp_path, monkeypatch):
    module = load_rules_lint_module("rules_lint_stub_readme_v1")
    _write_skill(tmp_path / "02-skill-factory", "alpha", "1.4")
    _write_stub(tmp_path / ".claude" / "skills", "alpha", "alpha 工具 v1.3 — stub")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_skill_stub_readme_version_sync(errors)
    assert any(
        e["check"] == "skill_stub_version_drift"
        and "v1.3" in e["message"]
        and "1.4" in e["message"]
        for e in errors
    )


def test_readme_drift_reports_error(tmp_path, monkeypatch):
    module = load_rules_lint_module("rules_lint_stub_readme_v2")
    _write_skill(tmp_path / "02-skill-factory", "alpha", "1.4")
    _write_readme(tmp_path / "02-skill-factory", [("alpha", "1.3")])
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_skill_stub_readme_version_sync(errors)
    assert any(
        e["check"] == "skill_readme_version_drift"
        and "v1.3" in e["message"]
        and "1.4" in e["message"]
        for e in errors
    )


def test_aligned_no_error(tmp_path, monkeypatch):
    module = load_rules_lint_module("rules_lint_stub_readme_v3")
    _write_skill(tmp_path / "02-skill-factory", "alpha", "2.1")
    _write_stub(tmp_path / ".claude" / "skills", "alpha", "alpha 第二輪退役 stub v2.1")
    _write_readme(tmp_path / "02-skill-factory", [("alpha", "2.1")])
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_skill_stub_readme_version_sync(errors)
    assert errors == []


def test_stub_without_inline_version_no_error(tmp_path, monkeypatch):
    """Stub description that doesn't mention vX.Y should be allowed."""
    module = load_rules_lint_module("rules_lint_stub_readme_v4")
    _write_skill(tmp_path / "02-skill-factory", "alpha", "1.4")
    _write_stub(tmp_path / ".claude" / "skills", "alpha", "alpha 短說明、無版本")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_skill_stub_readme_version_sync(errors)
    assert errors == []


def test_skill_creator_is_skipped(tmp_path, monkeypatch):
    """skill-creator is locked official MCP, not maintained here."""
    module = load_rules_lint_module("rules_lint_stub_readme_v5")
    _write_skill(tmp_path / "02-skill-factory", "skill-creator", "9.9")
    _write_stub(
        tmp_path / ".claude" / "skills", "skill-creator", "skill-creator v0.1 stub"
    )
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_skill_stub_readme_version_sync(errors)
    assert errors == []


def test_readme_without_skill_row_no_error(tmp_path, monkeypatch):
    """If README doesn't list the skill in its table, that's fine (not drift)."""
    module = load_rules_lint_module("rules_lint_stub_readme_v6")
    _write_skill(tmp_path / "02-skill-factory", "alpha", "1.4")
    _write_readme(tmp_path / "02-skill-factory", [("beta", "2.0")])
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    errors = []
    module.check_skill_stub_readme_version_sync(errors)
    assert errors == []
