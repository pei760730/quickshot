"""End-to-end integration tests for learning-loop write paths."""

from lib.backfill import backfill_video
from lib.pipeline import (
    add_video,
    find_video,
    load_tracking,
    record_verifier_scores,
    set_hook_type,
    set_trace,
    transition,
)


def _seed_valid_meta(data):
    pipeline_data = data.get("_pipeline_ref", data)
    meta = pipeline_data.setdefault("_meta", {})
    meta.setdefault("valid_hook_types", ["B1", "B2", "B3", "D1", "D2", "D3", "D4", "D5"])
    meta.setdefault("valid_title_types", ["T1", "T2", "T3", "T4", "T5"])


def _pipeline_item(data, vid):
    _, video = find_video(data, vid)
    assert video is not None, f"missing video: {vid}"
    return video


def test_e2e_quick_shot_with_full_learning_loop(patch_paths):
    data = load_tracking()
    _seed_valid_meta(data)

    # Step 1: quick-add 新影片 + hook_type
    vid = add_video(
        data,
        topic="e2e-test",
        tag="test",
        title="e2e 測試",
        source="quick-shot",
        initial_status="剪輯中",
        script_status="待補",
        hook_type="B2",
    )
    assert vid == "VID-001"
    assert _pipeline_item(data, vid)["hook_type"] == "B2"

    # Step 2: transition 到已上線
    ok, _ = transition(data, vid, "已上線")
    assert ok is True
    assert _pipeline_item(data, vid)["status"] == "已上線"

    # Step 3: set-trace 寫入 generation_trace
    trace = {
        "skill_used": "generation",
        "skill_version": "1.50",
        "generated_at": "2026-04-24",
        "title_type": "T2",
        "hook_type": "B2",
        "version_chosen": "D",
    }
    ok, _ = set_trace(data, vid, trace)
    assert ok is True
    assert _pipeline_item(data, vid)["generation_trace"]["skill_used"] == "generation"
    assert _pipeline_item(data, vid)["generation_trace"]["version_chosen"] == "D"

    # Step 4: record-verifier-scores 寫入 verifier_scores
    scores = {
        "conflict_score": 8,
        "retention_prediction": "high",
        "ai_residue_count": 2,
        "data_consistency": True,
        "format_complete": True,
        "pass_count": "4/5",
    }
    ok, _ = record_verifier_scores(data, vid, scores)
    assert ok is True
    assert _pipeline_item(data, vid)["verifier_scores"]["pass_count"] == "4/5"
    assert _pipeline_item(data, vid)["verifier_scores"]["data_consistency"] is True

    # Step 5: backfill 寫入表現數據
    ok, _, _ = backfill_video(data, vid, views=1000, retention_3s=50, completion_rate=40)
    assert ok is True
    assert _pipeline_item(data, vid)["backfill"]["views"] == 1000

    # Step 6: 最終 pipeline.json 同時有 4 個資料層
    reloaded = load_tracking()
    item = _pipeline_item(reloaded, vid)
    assert item["hook_type"] == "B2"
    assert item["generation_trace"] is not None
    assert item["verifier_scores"] is not None
    assert item["backfill"] is not None


def test_e2e_set_trace_before_set_hook_type_is_fine(patch_paths):
    data = load_tracking()
    _seed_valid_meta(data)

    vid = add_video(
        data,
        topic="trace-first",
        tag="test",
        title="先 trace 後 hook",
        source="quick-shot",
        initial_status="剪輯中",
        script_status="待補",
    )

    trace = {
        "skill_used": "generation",
        "skill_version": "1.50",
        "generated_at": "2026-04-24",
        "title_type": "T2",
        "hook_type": "B2",
        "version_chosen": "D",
    }
    ok, _ = set_trace(data, vid, trace)
    assert ok is True

    ok, _ = set_hook_type(data, vid, "B2")
    assert ok is True

    item = _pipeline_item(load_tracking(), vid)
    assert item["generation_trace"]["version_chosen"] == "D"
    assert item["hook_type"] == "B2"


def test_e2e_verifier_scores_rollback_on_partial_failure(patch_paths):
    data = load_tracking()
    _seed_valid_meta(data)

    vid = add_video(
        data,
        topic="scores-failure",
        tag="test",
        title="verifier fail",
        source="quick-shot",
        initial_status="剪輯中",
        script_status="待補",
    )

    # 缺少必要欄位，應整筆拒絕，且不殘留 verifier_scores。
    partial_scores = {
        "conflict_score": 8,
        "pass_count": "4/5",
    }
    ok, msg = record_verifier_scores(data, vid, partial_scores)
    assert ok is False
    assert "缺少必要欄位" in msg
    assert "verifier_scores" not in _pipeline_item(load_tracking(), vid)
