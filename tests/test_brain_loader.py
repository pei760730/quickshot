import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "libs"))
import brain_loader
from brain_loader import _active_lessons, load_for_skill


@pytest.fixture
def brain_repo(tmp_path, monkeypatch):
    brain_dir = tmp_path / "01-data-brain"
    personas_dir = brain_dir / "personas"
    personas_dir.mkdir(parents=True)
    (brain_dir / "brand.md").write_text("# Brand\n", encoding="utf-8")
    (brain_dir / "cases.md").write_text("# Cases\n", encoding="utf-8")
    (personas_dir / "kai.md").write_text(
        "# Kai\nKai persona fixture.\n", encoding="utf-8"
    )
    (personas_dir / "an.md").write_text("# An\nAn persona fixture.\n", encoding="utf-8")

    data_dir = tmp_path / "data" / "kai"
    data_dir.mkdir(parents=True)
    (data_dir / "lessons.json").write_text(
        '{"lessons": [{"id": "L-01", "stage": "soft", "scope": ["generation"]}]}',
        encoding="utf-8",
    )

    monkeypatch.setattr(brain_loader, "_repo_root", lambda: tmp_path)
    return tmp_path


def test_active_lessons_filters_soft_only():
    rows = [
        {"id": "L-01", "stage": "soft"},
        {"id": "L-02", "stage": "hardened"},
        {"id": "L-03", "stage": "archived"},
    ]
    result = _active_lessons(rows)
    assert len(result) == 1
    assert result[0]["id"] == "L-01"


def test_active_lessons_rejects_legacy_stages():
    """Regression guard: PR #365 used candidate/active (4-tier), should reject."""
    rows = [
        {"id": "L-01", "stage": "candidate"},
        {"id": "L-02", "stage": "active"},
        {"id": "L-03", "stage": "observation"},
    ]
    assert _active_lessons(rows) == []


def test_active_lessons_empty_input():
    assert _active_lessons([]) == []


def test_load_for_skill_returns_soft_lessons_for_kai_generation(brain_repo):
    """Smoke test: lessons.json + generation skill should return soft lessons."""
    bundle = load_for_skill("kai", "generation", mode="dual-track")
    assert isinstance(bundle.lessons, list)
    assert [lesson["id"] for lesson in bundle.lessons] == ["L-01"]


def test_load_for_skill_returns_kai_md(brain_repo):
    bundle = load_for_skill("kai", "generation", mode="dual-track")
    assert bundle.kai_md.strip()
    assert "Kai persona fixture" in bundle.kai_md


def test_load_for_skill_returns_an_md_when_present(brain_repo):
    bundle = load_for_skill("kai", "generation", mode="dual-track")
    assert "An persona fixture" in bundle.an_md


def test_missing_kai_md_returns_empty_string(brain_repo):
    (brain_repo / "01-data-brain" / "personas" / "kai.md").unlink()

    bundle = load_for_skill("kai", "generation", mode="dual-track")
    assert bundle.kai_md == ""


def test_missing_an_md_returns_empty_string(brain_repo):
    (brain_repo / "01-data-brain" / "personas" / "an.md").unlink()

    bundle = load_for_skill("kai", "generation", mode="dual-track")
    assert bundle.an_md == ""
