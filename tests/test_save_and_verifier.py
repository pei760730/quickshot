"""Tests for save_script command and backfill verifier accuracy comparison."""

from pathlib import Path

import pytest
from conftest import make_video, write_sharded_pipeline
from path_bootstrap import load_video_ops_module


def _pipeline_with_meta(videos, next_vid=2):
    """Create pipeline data with _meta enums."""
    items = []
    for v in videos:
        item = {"idea_id": f"IDEA-{v['vid'].split('-')[1]}", "topic": v["topic"]}
        item.update(v)
        items.append(item)
    return {
        "_meta": {
            "version": "2.0",
            "last_updated": "2026-03-17",
            "next_idea_id": 10,
            "next_vid": next_vid,
            "valid_title_types": ["T1", "T2", "T3", "T4", "T5"],
            "valid_hook_types": ["D1", "D2", "D3", "B1", "B2", "B3"],
            "valid_versions": [
                "A1", "A2", "A3", "B1", "B2", "B3",
                "C1", "C2", "C3", "D1", "D2", "D3", "D4", "D5",
            ],
            "valid_verifier_predictions": ["high", "normal", "low"],
        },
        "items": items,
    }


def _pipeline_with_trace_required(videos, trace_required_statuses, next_vid=2):
    data = _pipeline_with_meta(videos, next_vid=next_vid)
    data["_meta"]["trace_required_statuses"] = trace_required_statuses
    return data


# ── save_script tests ──────────────────────────────────────


class TestSaveScript:

    def test_save_success(self, patch_paths):
        from lib.pipeline import load_tracking, save_script

        v = make_video(vid="VID-001", status="待拍")
        data = _pipeline_with_meta([v])

        # Write sharded pipeline
        write_sharded_pipeline(patch_paths / "data" / "kai", data)

        data = load_tracking()
        ok, msg = save_script(
            data, "VID-001",
            script_path="03-production-line/02-ready-to-shoot/test.md",
            title_type="T3",
            hook_type="B2",
            version="B2",
            verifier_prediction="high",
        )
        assert ok
        assert "已存檔" in msg
        assert "B2" in msg

        # Verify fields were written
        video = data["videos"][0]
        assert video["title_type"] == "T3"
        assert video["hook_type"] == "B2"
        assert video["version"] == "B2"
        assert video["verifier_prediction"] == "high"
        assert video["script_path"] == "03-production-line/02-ready-to-shoot/test.md"
        assert video["save_date"] == "2026-03-17"

    def test_save_rejects_wrong_status(self, patch_paths):
        from lib.pipeline import load_tracking, save_script

        v = make_video(vid="VID-001", status="已上線")
        data = _pipeline_with_meta([v])

        write_sharded_pipeline(patch_paths / "data" / "kai", data)

        data = load_tracking()
        ok, msg = save_script(
            data, "VID-001",
            script_path="test.md",
            title_type="T3",
            hook_type="B2",
            version="B2",
            verifier_prediction="high",
        )
        assert not ok
        assert "待拍" in msg

    def test_save_rejects_invalid_title_type(self, patch_paths):
        from lib.pipeline import load_tracking, save_script

        v = make_video(vid="VID-001", status="待拍")
        data = _pipeline_with_meta([v])

        write_sharded_pipeline(patch_paths / "data" / "kai", data)

        data = load_tracking()
        ok, msg = save_script(
            data, "VID-001",
            script_path="test.md",
            title_type="X9",
            hook_type="B2",
            version="B2",
            verifier_prediction="high",
        )
        assert not ok
        assert "title_type=X9" in msg

    def test_save_rejects_invalid_version(self, patch_paths):
        from lib.pipeline import load_tracking, save_script

        v = make_video(vid="VID-001", status="待拍")
        data = _pipeline_with_meta([v])

        write_sharded_pipeline(patch_paths / "data" / "kai", data)

        data = load_tracking()
        ok, msg = save_script(
            data, "VID-001",
            script_path="test.md",
            title_type="T3",
            hook_type="B2",
            version="Z9",
            verifier_prediction="high",
        )
        assert not ok
        assert "version=Z9" in msg

    def test_save_rejects_invalid_hook_type(self, patch_paths):
        from lib.pipeline import load_tracking, save_script

        v = make_video(vid="VID-001", status="待拍")
        data = _pipeline_with_meta([v])

        write_sharded_pipeline(patch_paths / "data" / "kai", data)

        data = load_tracking()
        ok, msg = save_script(
            data, "VID-001",
            script_path="test.md",
            title_type="T3",
            hook_type="X1",
            version="B2",
            verifier_prediction="high",
        )
        assert not ok
        assert "hook_type=X1" in msg

    def test_save_rejects_invalid_verifier_prediction(self, patch_paths):
        from lib.pipeline import load_tracking, save_script

        v = make_video(vid="VID-001", status="待拍")
        data = _pipeline_with_meta([v])

        write_sharded_pipeline(patch_paths / "data" / "kai", data)

        data = load_tracking()
        ok, msg = save_script(
            data, "VID-001",
            script_path="test.md",
            title_type="T3",
            hook_type="B2",
            version="B2",
            verifier_prediction="excellent",
        )
        assert not ok
        assert "verifier_prediction=excellent" in msg

    def test_save_not_found(self, patch_paths):
        from lib.pipeline import load_tracking, save_script

        data = _pipeline_with_meta([])

        write_sharded_pipeline(patch_paths / "data" / "kai", data)

        data = load_tracking()
        ok, msg = save_script(
            data, "VID-999",
            script_path="test.md",
            title_type="T3",
            hook_type="B2",
            version="B2",
            verifier_prediction="high",
        )
        assert not ok
        assert "找不到" in msg

    def test_save_with_generation_trace(self, patch_paths):
        from lib.pipeline import load_tracking, save_script

        v = make_video(vid="VID-001", status="待拍")
        data = _pipeline_with_meta([v])

        write_sharded_pipeline(patch_paths / "data" / "kai", data)

        data = load_tracking()
        trace = {
            "skill_used": "flow-operator",
            "skill_version": "1.50",
            "generated_at": "2026-04-25",
            "title_type": "T3",
            "hook_type": "B2",
            "version_chosen": "D",
            "patterns_injected": ["B2", "D3"],
            "risk_patterns_avoided": ["開場太慢"],
            "persona_deviation_score": 3,
        }
        ok, msg = save_script(
            data, "VID-001",
            script_path="test.md",
            title_type="T3",
            hook_type="B2",
            version="B2",
            verifier_prediction="high",
            generation_trace=trace,
        )
        assert ok
        video = data["videos"][0]
        assert "generation_trace" in video
        gt = video["generation_trace"]
        assert gt["patterns_injected"] == ["B2", "D3"]
        assert gt["risk_patterns_avoided"] == ["開場太慢"]
        assert gt["persona_deviation_score"] == 3.0

    def test_save_without_generation_trace(self, patch_paths):
        from lib.pipeline import load_tracking, save_script

        v = make_video(vid="VID-001", status="待拍")
        data = _pipeline_with_meta([v])

        write_sharded_pipeline(patch_paths / "data" / "kai", data)

        data = load_tracking()
        ok, msg = save_script(
            data, "VID-001",
            script_path="test.md",
            title_type="T3",
            hook_type="B2",
            version="B2",
            verifier_prediction="high",
        )
        assert ok
        video = data["videos"][0]
        assert "generation_trace" not in video


class TestSaveCliTraceFlag:
    def _write_pipeline(self, patch_paths):
        v = make_video(vid="VID-001", status="待拍")
        data = _pipeline_with_meta([v])
        write_sharded_pipeline(patch_paths / "data" / "kai", data)

    def test_save_with_trace_flag_writes_generation_trace(self, monkeypatch, patch_paths):
        self._write_pipeline(patch_paths)
        video_ops = load_video_ops_module()
        from lib.pipeline import load_tracking
        ctx = {"data": load_tracking(), "op_paths": {"operator": "kai"}}
        monkeypatch.setattr(
            video_ops.sys,
            "argv",
            [
                "video-ops.py", "save", "VID-001",
                "--script-path", "03-production-line/02-ready-to-shoot/test.md",
                "--title-type", "T3",
                "--hook-type", "B2",
                "--version", "B2",
                "--verifier-prediction", "high",
                "--trace",
                '{"skill_used":"flow-operator","skill_version":"1.50","generated_at":"2026-04-25","title_type":"T3","hook_type":"B2","version_chosen":"D","patterns_injected":["B2"]}',
            ],
        )
        video_ops._cmd_save(ctx)
        assert ctx["data"]["videos"][0]["generation_trace"]["version_chosen"] == "D"

    def test_save_without_trace_flag_is_rejected(self, monkeypatch, patch_paths):
        self._write_pipeline(patch_paths)
        video_ops = load_video_ops_module()
        from lib.pipeline import load_tracking
        ctx = {"data": load_tracking(), "op_paths": {"operator": "kai"}}
        monkeypatch.setattr(
            video_ops.sys,
            "argv",
            [
                "video-ops.py", "save", "VID-001",
                "--script-path", "03-production-line/02-ready-to-shoot/test.md",
                "--title-type", "T3",
                "--hook-type", "B2",
                "--version", "B2",
                "--verifier-prediction", "high",
            ],
        )
        with pytest.raises(SystemExit) as exc:
            video_ops._cmd_save(ctx)
        assert exc.value.code == 1

    def test_save_with_trace_flag_json_parse_error(self, monkeypatch, patch_paths):
        self._write_pipeline(patch_paths)
        video_ops = load_video_ops_module()
        from lib.pipeline import load_tracking
        ctx = {"data": load_tracking(), "op_paths": {"operator": "kai"}}
        monkeypatch.setattr(
            video_ops.sys,
            "argv",
            [
                "video-ops.py", "save", "VID-001",
                "--script-path", "03-production-line/02-ready-to-shoot/test.md",
                "--title-type", "T3",
                "--hook-type", "B2",
                "--version", "B2",
                "--verifier-prediction", "high",
                "--trace", "{bad-json",
            ],
        )
        with pytest.raises(SystemExit) as exc:
            video_ops._cmd_save(ctx)
        assert exc.value.code == 1

    def test_save_requires_trace_on_first_save_when_status_is_enforced(self, monkeypatch, patch_paths, capsys):
        v = make_video(vid="VID-001", status="待拍")
        data = _pipeline_with_trace_required([v], ["待拍"])
        write_sharded_pipeline(patch_paths / "data" / "kai", data)

        video_ops = load_video_ops_module()
        from lib.pipeline import load_tracking
        ctx = {"data": load_tracking(), "op_paths": {"operator": "kai"}}
        monkeypatch.setattr(
            video_ops.sys,
            "argv",
            [
                "video-ops.py", "save", "VID-001",
                "--script-path", "03-production-line/02-ready-to-shoot/test.md",
                "--title-type", "T3",
                "--hook-type", "B2",
                "--version", "B2",
                "--verifier-prediction", "high",
            ],
        )
        with pytest.raises(SystemExit) as exc:
            video_ops._cmd_save(ctx)
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "trace 必填、見 generation SKILL.md §Output Contract" in out

    def test_save_rejects_followup_without_trace_even_when_trace_already_exists(self, monkeypatch, patch_paths):
        v = make_video(vid="VID-001", status="待拍")
        v["generation_trace"] = {
            "skill_used": "flow-operator",
            "skill_version": "1.50",
            "generated_at": "2026-04-25",
            "title_type": "T3",
            "hook_type": "B2",
            "version_chosen": "D",
            "patterns_injected": ["B2"],
        }
        data = _pipeline_with_trace_required([v], ["待拍"])
        write_sharded_pipeline(patch_paths / "data" / "kai", data)

        video_ops = load_video_ops_module()
        from lib.pipeline import load_tracking
        ctx = {"data": load_tracking(), "op_paths": {"operator": "kai"}}
        monkeypatch.setattr(
            video_ops.sys,
            "argv",
            [
                "video-ops.py", "save", "VID-001",
                "--script-path", "03-production-line/02-ready-to-shoot/test.md",
                "--title-type", "T3",
                "--hook-type", "B2",
                "--version", "B2",
                "--verifier-prediction", "high",
            ],
        )
        with pytest.raises(SystemExit) as exc:
            video_ops._cmd_save(ctx)
        assert exc.value.code == 1


# ── backfill verifier accuracy tests ───────────────────────


class TestVerifierAccuracy:

    def test_backfill_compares_verifier_prediction_match(self, patch_paths):
        from lib.pipeline import load_tracking
        from lib.backfill import backfill_video

        v = make_video(vid="VID-001", status="已上線", publish_date="2026-03-10")
        v["verifier_prediction"] = "high"
        data = _pipeline_with_meta([v])

        write_sharded_pipeline(patch_paths / "data" / "kai", data)

        data = load_tracking()
        ok, msg, result = backfill_video(
            data, "VID-001",
            views=500000, retention_3s=80, completion_rate=50,
        )
        assert ok
        assert "verifier_accuracy" in result
        assert result["verifier_accuracy"]["predicted"] == "high"
        assert result["verifier_accuracy"]["actual"] == "high"
        assert result["verifier_accuracy"]["match"] is True

    def test_backfill_compares_verifier_prediction_mismatch(self, patch_paths):
        from lib.pipeline import load_tracking
        from lib.backfill import backfill_video

        v = make_video(vid="VID-001", status="已上線", publish_date="2026-03-10")
        v["verifier_prediction"] = "high"
        data = _pipeline_with_meta([v])

        write_sharded_pipeline(patch_paths / "data" / "kai", data)

        data = load_tracking()
        ok, msg, result = backfill_video(
            data, "VID-001",
            views=1000, retention_3s=30, completion_rate=10,
        )
        assert ok
        assert "verifier_accuracy" in result
        assert result["verifier_accuracy"]["predicted"] == "high"
        assert result["verifier_accuracy"]["actual"] == "low"
        assert result["verifier_accuracy"]["match"] is False

    def test_backfill_skips_verifier_when_no_prediction(self, patch_paths):
        from lib.pipeline import load_tracking
        from lib.backfill import backfill_video

        v = make_video(vid="VID-001", status="已上線", publish_date="2026-03-10")
        # No verifier_prediction field
        data = _pipeline_with_meta([v])

        write_sharded_pipeline(patch_paths / "data" / "kai", data)

        data = load_tracking()
        ok, msg, result = backfill_video(
            data, "VID-001",
            views=1000, retention_3s=50, completion_rate=25,
        )
        assert ok
        assert "verifier_accuracy" not in result
