"""Tests for migrate --fix-learning-field helper behavior."""

from lib.pipeline import add_video, load_tracking, save_tracking
from path_bootstrap import load_video_ops_module


def test_fix_learning_field_sets_false_when_script_missing(patch_paths):
    data = load_tracking()
    add_video(data, "t", "tag", title="tt", source="quick-shot", initial_status="已上線")
    data["videos"][0]["backfill"] = {"performance": "normal", "learning_extracted": True}
    save_tracking(data, skip_validate=True)

    video_ops = load_video_ops_module()
    fixed = video_ops._fix_learning_field(data)

    assert fixed == [("VID-001", "set-learning_extracted-false")]
    assert data["videos"][0]["backfill"]["learning_extracted"] is False


def test_fix_learning_field_marks_skipped_when_script_exists(patch_paths):
    data = load_tracking()
    sp = "03-production-line/02-ready-to-shoot/2026-03-17_fix_learning.md"
    p = patch_paths / sp
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("腳本內容", encoding="utf-8")

    add_video(
        data, "t", "tag", title="tt", source="quick-shot",
        initial_status="已上線", script_path=sp,
    )
    data["videos"][0]["backfill"] = {"performance": "normal", "learning_extracted": True}

    video_ops = load_video_ops_module()
    fixed = video_ops._fix_learning_field(data)

    assert fixed == [("VID-001", "mark-skipped")]
    assert data["videos"][0]["learning"]["type"] == "skipped-auto-migrate"
