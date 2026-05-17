"""Stage D (v4.64) — Dialog hardening API tests.

Verifies `scripts/ops/lib/hardening.harden_from_dialog()` behavior:
- executes artifact write + validator
- promotes lesson stage soft → hardened
- writes archive with source="dialog"
- preserves lesson stage on failure
"""

import json
from pathlib import Path

import pytest

from lib.hardening import harden_from_dialog, _load_archive_payload
from lib.lessons import add_lesson, load_lessons


def _read_lessons_raw(op_paths):
    return json.loads((op_paths["data_dir"] / "lessons.json").read_text(encoding="utf-8"))


@pytest.fixture
def soft_lesson(patch_paths):
    lid = add_lesson(
        "kai",
        origin="manual",
        pattern="test-harden",
        counter_pattern="use resolve_operator()",
        evidence=["VID-001"],
        scope=["scripts"],
    )
    return lid


def test_harden_test_path_promotes_and_archives(soft_lesson, patch_paths, tmp_path):
    """path=test → writes tests/test_lesson_<id>.py, validates, promotes."""
    # Build a trivial always-passing test file content
    draft = (
        f'"""Regression test for {soft_lesson}."""\n'
        f"def test_always_passes():\n"
        f"    assert True\n"
    )

    result = harden_from_dialog(
        operator="kai",
        lesson_id=soft_lesson,
        path="test",
        draft_content=draft,
    )

    assert result["status"] == "executed", result
    assert "test_lesson_" in result["target"]
    assert Path(result["target"]).exists()
    assert result["lesson_stage_after"] == "hardened"

    # Lesson promoted
    rows = load_lessons("kai")
    assert rows[0]["stage"] == "hardened"

    # Archive has entry with source=dialog
    archive = _load_archive_payload("kai")
    dialog_entries = [r for r in archive["items"] if r.get("source") == "dialog"]
    assert len(dialog_entries) == 1
    assert dialog_entries[0]["lesson_id"] == soft_lesson
    assert dialog_entries[0]["dialog_path"] == "test"

    # Cleanup artifact so it doesn't pollute repo state
    Path(result["target"]).unlink(missing_ok=True)


def test_harden_rejects_non_soft_lesson(patch_paths):
    lid = add_lesson("kai", "manual", "already-hardened", evidence=["VID-001"])
    # Simulate hardened state
    from lib.lessons import promote_stage
    promote_stage("kai", lid, "hardened")

    result = harden_from_dialog(
        operator="kai",
        lesson_id=lid,
        path="test",
        draft_content="def test_noop(): assert True",
    )
    assert result["status"] == "invalid_state"
    assert "soft" in result["message"]


def test_harden_rejects_unknown_lesson(patch_paths):
    result = harden_from_dialog(
        operator="kai",
        lesson_id="L-9999",
        path="test",
        draft_content="",
    )
    assert result["status"] == "not_found"


def test_harden_rejects_invalid_path(soft_lesson, patch_paths):
    result = harden_from_dialog(
        operator="kai",
        lesson_id=soft_lesson,
        path="unknown_path",
        draft_content="whatever",
    )
    assert result["status"] == "invalid_path"


def test_harden_failure_preserves_soft_stage(soft_lesson, patch_paths):
    """If validator fails, lesson stays soft and no archive entry is added."""
    # A syntactically broken test file → pytest fails → validator fails
    broken = "def test_broken(:\n    assert True\n"

    result = harden_from_dialog(
        operator="kai",
        lesson_id=soft_lesson,
        path="test",
        draft_content=broken,
    )
    assert result["status"] == "failed"

    rows = load_lessons("kai")
    assert rows[0]["stage"] == "soft"  # unchanged

    archive = _load_archive_payload("kai")
    dialog_entries = [r for r in archive["items"] if r.get("source") == "dialog"]
    assert dialog_entries == []

    # Cleanup partial artifact
    if result.get("target"):
        Path(result["target"]).unlink(missing_ok=True)
