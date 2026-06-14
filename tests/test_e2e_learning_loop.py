"""End-to-end integration tests for learning-loop write paths."""

from lib.backfill import backfill_video
from lib.pipeline import (
    add_video,
    find_video,
    load_tracking,
    record_verifier_scores,
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

    # Step 3: record-verifier-scores 寫入 verifier_scores
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

    # Step 4: backfill 寫入表現數據
    ok, _, _ = backfill_video(data, vid, views=1000, retention_3s=50, completion_rate=40)
    assert ok is True
    assert _pipeline_item(data, vid)["backfill"]["views"] == 1000

    # Step 5: 最終 pipeline.json 同時有 3 個資料層
    reloaded = load_tracking()
    item = _pipeline_item(reloaded, vid)
    assert item["hook_type"] == "B2"
    assert item["verifier_scores"] is not None
    assert item["backfill"] is not None


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
