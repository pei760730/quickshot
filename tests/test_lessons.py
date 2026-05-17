"""Tests for unified lessons storage (v2.0 schema)."""

import pytest

from lib.lessons import (
    add_lesson,
    archive_lesson,
    load_lessons,
    promote_stage,
    query,
    stats,
    propose_hardening,
)


def test_add_and_load_lessons(patch_paths):
    lesson_id = add_lesson(
        "kai",
        origin="mistake",
        pattern="avoid fabricated numbers",
        counter_pattern="double check source",
        evidence=["VID-001"],
        scope=[],
    )
    rows = load_lessons("kai")
    assert len(rows) == 1
    assert rows[0]["id"] == lesson_id
    assert lesson_id == "L-0001"
    assert rows[0]["stage"] == "soft"
    # v2.0 assertions: legacy v1.x fields absent
    assert "hit_count" not in rows[0]
    assert "hardening_status" not in rows[0]
    assert "confidence" not in rows[0]


def test_dedup_and_evidence_merge(patch_paths):
    first = add_lesson("kai", "verifier", "ai residue", evidence=["VID-001"])
    second = add_lesson("kai", "verifier", "ai residue", evidence=["VID-002"])
    assert first == second
    rows = query("kai", origin="verifier")
    assert len(rows) == 1
    assert set(rows[0]["evidence"]) == {"VID-001", "VID-002"}


def test_stage_transitions_v2(patch_paths):
    """v2.0: soft → hardened/archived, terminal states locked."""
    lesson_id = add_lesson("kai", "mistake", "bad claim", evidence=["VID-001"])
    assert query("kai", origin="mistake")[0]["stage"] == "soft"

    # soft → hardened OK
    promote_stage("kai", lesson_id, "hardened")
    assert query("kai", origin="mistake")[0]["stage"] == "hardened"

    # hardened terminal: can't go back
    with pytest.raises(ValueError):
        promote_stage("kai", lesson_id, "soft")
    with pytest.raises(ValueError):
        promote_stage("kai", lesson_id, "archived")


def test_soft_to_archived_path(patch_paths):
    lesson_id = add_lesson("kai", "manual", "x", evidence=[])
    promote_stage("kai", lesson_id, "archived")
    assert query("kai", origin="manual")[0]["stage"] == "archived"
    # archived terminal
    with pytest.raises(ValueError):
        promote_stage("kai", lesson_id, "soft")


def test_query_filters(patch_paths):
    add_lesson("kai", "mistake", "m1", scope=[])
    add_lesson("kai", "deviation", "VID-001", scope=["script"], evidence=["VID-001"])
    assert len(query("kai", origin="mistake")) == 1
    assert len(query("kai", scope=["script"])) == 1
    assert len(query("kai", stage="soft")) == 2


def test_stats_v2_grouping(patch_paths):
    add_lesson("kai", "manual", "m1")
    l2 = add_lesson("kai", "manual", "m2")
    promote_stage("kai", l2, "hardened")
    l3 = add_lesson("kai", "manual", "m3")
    promote_stage("kai", l3, "archived")

    s = stats("kai")
    assert s["total"] == 3
    assert s["by_stage"]["soft"] == 1
    assert s["by_stage"]["hardened"] == 1
    assert s["by_stage"]["archived"] == 1


def test_archive_lesson_stamps_reason(patch_paths):
    lesson_id = add_lesson("kai", "manual", "dup-target", evidence=["VID-001"])
    assert archive_lesson("kai", lesson_id, reason="重複於 L-9999") is True
    row = query("kai", origin="manual")[0]
    assert row["stage"] == "archived"
    assert "重複於 L-9999" in (row.get("source_note") or "")
    # idempotent: second call on already-archived returns False
    assert archive_lesson("kai", lesson_id, reason="again") is False
    # unknown id returns False, not raise
    assert archive_lesson("kai", "L-9999", reason="x") is False


def test_propose_hardening_requires_counter_pattern(patch_paths):
    # lesson without counter_pattern → not proposed
    add_lesson("kai", "manual", "just-observation", evidence=["VID-001"])
    assert propose_hardening("kai") == []

    # lesson with counter_pattern → proposed
    l2 = add_lesson(
        "kai",
        "manual",
        "with-cp",
        counter_pattern="do X instead",
        evidence=["VID-002"],
    )
    proposals = propose_hardening("kai")
    assert [p["id"] for p in proposals] == [l2]

    # hardened lesson → not proposed
    promote_stage("kai", l2, "hardened")
    assert propose_hardening("kai") == []


def test_legacy_v1_stage_auto_migrates_on_load(patch_paths, tmp_path, monkeypatch):
    """load_lessons() transparently maps v1.x stages (candidate/active/graduated) to v2.0."""
    from lib.lessons import _lessons_json
    import json

    path = _lessons_json("kai")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.1",
                "next_id": 4,
                "lessons": [
                    {"id": "L-0001", "origin": "mistake", "pattern": "a", "stage": "observation", "evidence": [], "scope": [], "created_at": "2026-01-01", "updated_at": "2026-01-01", "hit_count": 5},
                    {"id": "L-0002", "origin": "mistake", "pattern": "b", "stage": "active", "evidence": [], "scope": [], "created_at": "2026-01-01", "updated_at": "2026-01-01", "confidence": 0.9},
                    {"id": "L-0003", "origin": "mistake", "pattern": "c", "stage": "graduated", "evidence": [], "scope": [], "created_at": "2026-01-01", "updated_at": "2026-01-01", "hardening_status": "hardened"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    rows = load_lessons("kai")
    stages = {r["id"]: r["stage"] for r in rows}
    assert stages == {"L-0001": "soft", "L-0002": "soft", "L-0003": "hardened"}
    # v1.x fields stripped from returned payload
    for r in rows:
        assert "hit_count" not in r
        assert "confidence" not in r
        assert "hardening_status" not in r
