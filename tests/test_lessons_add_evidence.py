"""Tests for lessons add-evidence CLI behavior."""

import pytest

from lib.config import today_str
from lib.lessons import add_lesson, load_lessons
from path_bootstrap import load_video_ops_module


def test_lessons_add_evidence_happy_path(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"op_paths": {"operator": "kai"}}
    lesson_id = add_lesson("kai", "manual", "seed", evidence=[])

    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        ["video-ops.py", "lessons", "add-evidence", lesson_id, "--vid", "VID-001"],
    )
    video_ops._cmd_lessons(ctx)
    out = capsys.readouterr().out
    assert f"✅ lessons add-evidence: {lesson_id} += VID-001 (now 1 evidence)" in out

    row = load_lessons("kai")[0]
    assert row["evidence"] == ["VID-001"]
    assert row["updated_at"] == today_str()


def test_lessons_add_evidence_idempotent(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"op_paths": {"operator": "kai"}}
    lesson_id = add_lesson("kai", "manual", "seed", evidence=["VID-001"])
    before = load_lessons("kai")[0]["evidence"][:]

    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        ["video-ops.py", "lessons", "add-evidence", lesson_id, "--vid", "VID-001"],
    )
    video_ops._cmd_lessons(ctx)
    out = capsys.readouterr().out
    assert f"✅ already in evidence: {lesson_id} has VID-001" in out
    assert load_lessons("kai")[0]["evidence"] == before


def test_lessons_add_evidence_not_found(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"op_paths": {"operator": "kai"}}
    add_lesson("kai", "manual", "seed", evidence=[])

    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        ["video-ops.py", "lessons", "add-evidence", "L-9999", "--vid", "VID-001"],
    )
    with pytest.raises(SystemExit) as ex:
        video_ops._cmd_lessons(ctx)
    assert ex.value.code == 1
    err = capsys.readouterr().err
    assert "❌ lesson L-9999 not found" in err


@pytest.mark.parametrize("bad_vid", ["VID-abc", "001"])
def test_lessons_add_evidence_invalid_vid(monkeypatch, patch_paths, capsys, bad_vid):
    video_ops = load_video_ops_module()
    ctx = {"op_paths": {"operator": "kai"}}
    lesson_id = add_lesson("kai", "manual", "seed", evidence=[])

    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        ["video-ops.py", "lessons", "add-evidence", lesson_id, "--vid", bad_vid],
    )
    with pytest.raises(SystemExit) as ex:
        video_ops._cmd_lessons(ctx)
    assert ex.value.code == 1
    out = capsys.readouterr().out
    assert out.startswith("❌")


def test_lessons_add_evidence_multi(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"op_paths": {"operator": "kai"}}
    lesson_id = add_lesson("kai", "manual", "seed", evidence=[])

    for vid in ("VID-001", "VID-002", "VID-003"):
        monkeypatch.setattr(
            video_ops.sys,
            "argv",
            ["video-ops.py", "lessons", "add-evidence", lesson_id, "--vid", vid],
        )
        video_ops._cmd_lessons(ctx)
    _ = capsys.readouterr().out

    row = load_lessons("kai")[0]
    assert row["evidence"] == ["VID-001", "VID-002", "VID-003"]
    assert len(row["evidence"]) == 3



def test_lessons_add_evidence_init_missing_evidence_field(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"op_paths": {"operator": "kai"}}
    lesson_id = add_lesson("kai", "manual", "seed")

    from lib.lessons import _lessons_json
    import json

    path = _lessons_json("kai")
    payload = json.loads(path.read_text(encoding="utf-8"))
    for row in payload["lessons"]:
        if row.get("id") == lesson_id:
            row.pop("evidence", None)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        ["video-ops.py", "lessons", "add-evidence", lesson_id, "--vid", "VID-010"],
    )
    video_ops._cmd_lessons(ctx)
    out = capsys.readouterr().out
    assert f"✅ lessons add-evidence: {lesson_id} += VID-010 (now 1 evidence)" in out

    row = load_lessons("kai")[0]
    assert row["evidence"] == ["VID-010"]
