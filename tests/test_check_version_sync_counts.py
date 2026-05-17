"""Tests for skill count drift detection in check-version-sync."""

from pathlib import Path

from path_bootstrap import load_module_from_repo


EXPECTED = 7


def _setup_tree(tmp_path: Path, *, registry_count: int = EXPECTED, factory_count: int = EXPECTED):
    (tmp_path / "scripts" / "lint").mkdir(parents=True)
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    (tmp_path / "02-skill-factory").mkdir(parents=True)

    valid_skills = [f"skill-{i}" for i in range(registry_count)]
    registry_body = '{\n  "valid_skills": [\n' + ",\n".join(
        f'    "{s}"' for s in valid_skills
    ) + "\n  ]\n}\n"
    (tmp_path / "scripts" / "lint" / "canonical-registry.json").write_text(registry_body, encoding="utf-8")

    for i in range(factory_count):
        d = tmp_path / "02-skill-factory" / f"skill-{i}"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("# skill v1.0\n", encoding="utf-8")

    # README and stubs intentionally remain out-of-sync during migration window.
    (tmp_path / ".claude" / "skills" / "skill-0.md").write_text("# stub\n", encoding="utf-8")
    (tmp_path / "02-skill-factory" / "README.md").write_text("# 14 個專業 Skills\n", encoding="utf-8")


def test_all_consistent_passes(tmp_path, monkeypatch):
    module = load_module_from_repo("scripts/utils/check-version-sync.py", "check_version_sync_counts")
    _setup_tree(tmp_path)

    monkeypatch.setattr(module, "CANONICAL_REGISTRY", tmp_path / "scripts" / "lint" / "canonical-registry.json")
    monkeypatch.setattr(module, "STUB_DIR", tmp_path / ".claude" / "skills")
    monkeypatch.setattr(module, "README", tmp_path / "02-skill-factory" / "README.md")
    monkeypatch.setattr(module, "SKILL_FACTORY", tmp_path / "02-skill-factory")

    assert module.check_skill_counts() == []


def test_registry_mismatch_fails(tmp_path, monkeypatch):
    module = load_module_from_repo("scripts/utils/check-version-sync.py", "check_version_sync_counts")
    _setup_tree(tmp_path, registry_count=14)

    monkeypatch.setattr(module, "CANONICAL_REGISTRY", tmp_path / "scripts" / "lint" / "canonical-registry.json")
    monkeypatch.setattr(module, "SKILL_FACTORY", tmp_path / "02-skill-factory")

    issues = "\n".join(module.check_skill_counts())
    assert "valid_skills=14" in issues


def test_factory_mismatch_fails(tmp_path, monkeypatch):
    module = load_module_from_repo("scripts/utils/check-version-sync.py", "check_version_sync_counts")
    _setup_tree(tmp_path, factory_count=14)

    monkeypatch.setattr(module, "CANONICAL_REGISTRY", tmp_path / "scripts" / "lint" / "canonical-registry.json")
    monkeypatch.setattr(module, "SKILL_FACTORY", tmp_path / "02-skill-factory")

    issues = "\n".join(module.check_skill_counts())
    assert "子目錄=14" in issues
