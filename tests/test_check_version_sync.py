from path_bootstrap import load_module_from_repo


def test_detects_version_mismatch_when_skill_heading_has_leading_spaces(tmp_path, monkeypatch, capsys):
    mod = load_module_from_repo("scripts/utils/check-version-sync.py", "check_version_sync")

    skill_dir = tmp_path / "02-skill-factory" / "flow-operator"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "  # flow-operator v1.40\nversion: 1.40\n",
        encoding="utf-8",
    )

    claude_skills = tmp_path / ".claude" / "skills"
    claude_skills.mkdir(parents=True)
    (claude_skills / "flow-operator.md").write_text(
        "Flow Operator skill v1.39\n",
        encoding="utf-8",
    )

    (tmp_path / "02-skill-factory" / "README.md").write_text("", encoding="utf-8")

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "SKILL_FACTORY", tmp_path / "02-skill-factory")
    monkeypatch.setattr(mod, "STUB_DIR", tmp_path / ".claude" / "skills")
    monkeypatch.setattr(mod, "README", tmp_path / "02-skill-factory" / "README.md")

    rc = mod.main()
    out = capsys.readouterr().out

    assert rc == 1
    assert "stub v1.39 ≠ heading v1.40" in out
