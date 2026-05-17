"""Tests for quick-shot optimized commands (quick-add, batch-quick-add, query-pending-scripts)."""

import subprocess
import sys

import pytest

from lib.pipeline import (
    load_tracking, add_video, query_pending_scripts, set_hook_type, set_trace,
)
from path_bootstrap import load_video_ops_module, video_ops_script_path
from timeouts import PROCESS_TIMEOUT_SEC


class TestQuickAddCLI:
    """Integration tests for the `quick-add` CLI command."""

    def _run(self, patch_paths, args):
        """Run video-ops.py with given args, return (returncode, stdout)."""
        script = video_ops_script_path()
        env_patch = {
            "PYTHONPATH": str(script.parent),
        }
        import os
        env = {**os.environ, **env_patch}
        result = subprocess.run(
            [sys.executable, str(script)] + args,
            capture_output=True, text=True, env=env,
            check=False, timeout=PROCESS_TIMEOUT_SEC,
        )
        return result.returncode, result.stdout, result.stderr

    def test_quick_add_basic(self, patch_paths):
        data = load_tracking()
        vid = add_video(
            data, "快拍測試", "生活", title="快拍標題",
            source="quick-shot", initial_status="剪輯中",
            script_status="待補",
        )
        assert vid == "VID-001"
        assert data["videos"][0]["source"] == "quick-shot"
        assert data["videos"][0]["script_status"] == "待補"
        assert data["videos"][0]["status"] == "剪輯中"

    def test_quick_add_online(self, patch_paths):
        data = load_tracking()
        add_video(
            data, "已上線測試", "美食", title="好吃的",
            source="quick-shot", initial_status="已上線",
            script_status="待補",
        )
        assert data["videos"][0]["status"] == "已上線"
        assert data["videos"][0]["publish_date"] == "2026-03-17"
        assert data["videos"][0]["backfill_due_date"] is not None

    def test_quick_add_with_hook_type(self, patch_paths):
        data = load_tracking()
        add_video(
            data, "帶 hook 補登", "生活", title="有 hook",
            source="quick-shot", initial_status="剪輯中",
            script_status="待補", hook_type="B2",
        )
        assert data["videos"][0]["hook_type"] == "B2"

    def test_quick_add_without_hook_type_backward_compat(self, patch_paths):
        data = load_tracking()
        add_video(
            data, "不帶 hook", "生活", title="舊行為",
            source="quick-shot", initial_status="剪輯中",
            script_status="待補",
        )
        assert "hook_type" not in data["videos"][0]

    def test_quick_add_invalid_hook_type_rejected(self, patch_paths):
        import pytest
        data = load_tracking()
        # Seed _meta.valid_hook_types so validation fires (prod pipeline has it、
        # 最小 fixture 沒有、所以 test 自行塞一組保證驗證觸發)
        pipeline_data = data.get("_pipeline_ref", data)
        pipeline_data.setdefault("_meta", {})["valid_hook_types"] = [
            "B1", "B2", "B3", "D1", "D2", "D3", "D4", "D5",
        ]
        with pytest.raises(ValueError, match="非法 hook_type"):
            add_video(
                data, "非法 hook", "生活", title="壞值",
                source="quick-shot", initial_status="剪輯中",
                script_status="待補", hook_type="ZZ99",
            )


class TestSetHookType:
    """Tests for set_hook_type() backfill path (Wave 2)."""

    def _seed_valid_ht(self, data):
        pipeline_data = data.get("_pipeline_ref", data)
        pipeline_data.setdefault("_meta", {})["valid_hook_types"] = [
            "B1", "B2", "B3", "D1", "D2", "D3", "D4", "D5",
        ]

    def test_set_hook_type_success(self, patch_paths):
        data = load_tracking()
        self._seed_valid_ht(data)
        add_video(
            data, "存量影片", "生活", title="需回填",
            source="quick-shot", initial_status="已上線", script_status="待補",
        )
        ok, msg = set_hook_type(data, "VID-001", "B2")
        assert ok is True
        assert data["videos"][0]["hook_type"] == "B2"
        assert "原未設" in msg

    def test_set_hook_type_overwrite(self, patch_paths):
        data = load_tracking()
        self._seed_valid_ht(data)
        add_video(
            data, "已有 hook", "生活", title="覆蓋",
            source="quick-shot", initial_status="已上線", script_status="待補",
            hook_type="B1",
        )
        ok, msg = set_hook_type(data, "VID-001", "D3")
        assert ok is True
        assert data["videos"][0]["hook_type"] == "D3"
        assert "原 B1" in msg

    def test_set_hook_type_not_found(self, patch_paths):
        data = load_tracking()
        ok, msg = set_hook_type(data, "VID-999", "B2")
        assert ok is False
        assert "找不到" in msg

    def test_set_hook_type_invalid_rejected(self, patch_paths):
        data = load_tracking()
        self._seed_valid_ht(data)
        add_video(
            data, "壞值測試", "生活", title="壞值",
            source="quick-shot", initial_status="已上線", script_status="待補",
        )
        ok, msg = set_hook_type(data, "VID-001", "ZZ99")
        assert ok is False
        assert "非法 hook_type" in msg
        assert "hook_type" not in data["videos"][0]


class TestSetTrace:
    def _seed_valid_meta(self, data):
        pipeline_data = data.get("_pipeline_ref", data)
        meta = pipeline_data.setdefault("_meta", {})
        meta["valid_hook_types"] = ["B1", "B2", "B3", "D1", "D2", "D3", "D4", "D5"]
        meta.setdefault("valid_title_types", ["T1", "T2", "T3", "T4", "T5"])

    def test_set_trace_success(self, patch_paths):
        data = load_tracking()
        self._seed_valid_meta(data)
        add_video(
            data, "trace 主題", "生活", title="trace",
            source="quick-shot", initial_status="已上線", script_status="待補",
        )
        trace = {
            "skill_used": "generation",
            "skill_version": "1.44",
            "generated_at": "2026-04-24",
            "title_type": "T2",
            "hook_type": "B2",
            "version_chosen": "D",
        }
        ok, msg = set_trace(data, "VID-001", trace)
        assert ok is True
        assert "trace 已記錄" in msg
        assert data["videos"][0]["generation_trace"]["skill_used"] == "generation"

    def test_set_trace_missing_required(self, patch_paths):
        data = load_tracking()
        self._seed_valid_meta(data)
        add_video(
            data, "trace 主題", "生活", title="trace",
            source="quick-shot", initial_status="已上線", script_status="待補",
        )
        trace = {
            "skill_used": "generation",
            "skill_version": "1.44",
            "generated_at": "2026-04-24",
            "title_type": "T2",
            "hook_type": "B2",
        }
        ok, msg = set_trace(data, "VID-001", trace)
        assert ok is False
        assert "缺少 required" in msg
        assert "version_chosen" in msg

    def test_set_trace_invalid_hook_type(self, patch_paths):
        data = load_tracking()
        self._seed_valid_meta(data)
        add_video(
            data, "trace 主題", "生活", title="trace",
            source="quick-shot", initial_status="已上線", script_status="待補",
        )
        trace = {
            "skill_used": "generation",
            "skill_version": "1.44",
            "generated_at": "2026-04-24",
            "title_type": "T2",
            "hook_type": "ZZ99",
            "version_chosen": "D",
        }
        ok, msg = set_trace(data, "VID-001", trace)
        assert ok is False
        assert "非法 hook_type" in msg

    def test_set_trace_not_found(self, patch_paths):
        data = load_tracking()
        trace = {
            "skill_used": "generation",
            "skill_version": "1.44",
            "generated_at": "2026-04-24",
            "title_type": "T2",
            "hook_type": "B2",
            "version_chosen": "D",
        }
        ok, msg = set_trace(data, "VID-999", trace)
        assert ok is False
        assert "找不到 VID-999" in msg


class TestSetTraceCLI:
    def _seed_valid_meta(self, data):
        pipeline_data = data.get("_pipeline_ref", data)
        meta = pipeline_data.setdefault("_meta", {})
        meta["valid_hook_types"] = ["B1", "B2", "B3", "D1", "D2", "D3", "D4", "D5"]
        meta["valid_title_types"] = ["T1", "T2", "T3", "T4", "T5"]

    def test_set_trace_cli_success(self, monkeypatch, patch_paths):
        video_ops = load_video_ops_module()
        data = load_tracking()
        self._seed_valid_meta(data)
        add_video(data, "trace", "tag", title="t", source="quick-shot", initial_status="已上線", script_status="待補")
        ctx = {"data": data, "op_paths": {"operator": "kai"}}
        monkeypatch.setattr(
            video_ops.sys,
            "argv",
            [
                "video-ops.py", "set-trace", "VID-001", "--trace",
                '{"skill_used":"generation","skill_version":"1.50","generated_at":"2026-04-25","title_type":"T2","hook_type":"B2","version_chosen":"D"}',
            ],
        )
        video_ops._cmd_set_trace(ctx)
        assert data["videos"][0]["generation_trace"]["skill_version"] == "1.50"

    def test_set_trace_cli_json_parse_error(self, monkeypatch, patch_paths):
        video_ops = load_video_ops_module()
        ctx = {"data": load_tracking(), "op_paths": {"operator": "kai"}}
        monkeypatch.setattr(video_ops.sys, "argv", ["video-ops.py", "set-trace", "VID-001", "--trace", "{bad-json"])
        with pytest.raises(SystemExit) as exc:
            video_ops._cmd_set_trace(ctx)
        assert exc.value.code == 1

    def test_set_trace_cli_missing_required(self, monkeypatch, patch_paths):
        video_ops = load_video_ops_module()
        data = load_tracking()
        self._seed_valid_meta(data)
        add_video(data, "trace", "tag", title="t", source="quick-shot", initial_status="已上線", script_status="待補")
        ctx = {"data": data, "op_paths": {"operator": "kai"}}
        monkeypatch.setattr(
            video_ops.sys,
            "argv",
            [
                "video-ops.py", "set-trace", "VID-001", "--trace",
                '{"skill_used":"generation","skill_version":"1.50","generated_at":"2026-04-25","title_type":"T2","hook_type":"B2"}',
            ],
        )
        with pytest.raises(SystemExit) as exc:
            video_ops._cmd_set_trace(ctx)
        assert exc.value.code == 1

    def test_set_trace_cli_invalid_hook_type(self, monkeypatch, patch_paths):
        video_ops = load_video_ops_module()
        data = load_tracking()
        self._seed_valid_meta(data)
        add_video(data, "trace", "tag", title="t", source="quick-shot", initial_status="已上線", script_status="待補")
        ctx = {"data": data, "op_paths": {"operator": "kai"}}
        monkeypatch.setattr(
            video_ops.sys,
            "argv",
            [
                "video-ops.py", "set-trace", "VID-001", "--trace",
                '{"skill_used":"generation","skill_version":"1.50","generated_at":"2026-04-25","title_type":"T2","hook_type":"ZZ99","version_chosen":"D"}',
            ],
        )
        with pytest.raises(SystemExit) as exc:
            video_ops._cmd_set_trace(ctx)
        assert exc.value.code == 1


class TestBatchQuickAdd:
    """Tests for batch-quick-add functionality (using add_video in loop)."""

    def test_batch_multiple(self, patch_paths):
        data = load_tracking()
        items = [
            {"topic": "主題1", "tag": "標籤1", "title": "標題1"},
            {"topic": "主題2", "tag": "標籤2", "title": "標題2"},
            {"topic": "主題3", "tag": "標籤3", "title": "標題3"},
        ]
        vids = []
        for item in items:
            vid = add_video(
                data, item["topic"], item["tag"], title=item["title"],
                source="quick-shot", initial_status="剪輯中",
                script_status="待補",
            )
            vids.append(vid)
        assert vids == ["VID-001", "VID-002", "VID-003"]
        assert len(data["videos"]) == 3
        assert all(v["source"] == "quick-shot" for v in data["videos"])

    def test_batch_mixed_status(self, patch_paths):
        data = load_tracking()
        add_video(data, "T1", "tag", title="t1",
                  source="quick-shot", initial_status="剪輯中",
                  script_status="待補")
        add_video(data, "T2", "tag", title="t2",
                  source="quick-shot", initial_status="已上線",
                  script_status="待補")
        assert data["videos"][0]["status"] == "剪輯中"
        assert data["videos"][1]["status"] == "已上線"


class TestQueryPendingScriptsIntegration:
    """Integration tests combining add + query_pending_scripts."""

    def test_mixed_videos(self, patch_paths):
        """Only quick-shot with script_status=待補 should appear."""
        data = load_tracking()
        # Pipeline video (no pending)
        add_video(data, "pipeline", "tag", title="t",
                  source_inspiration="i", skill_used="generation")
        # Quick-shot pending
        add_video(data, "quick1", "tag", title="t1",
                  source="quick-shot", script_status="待補")
        # Quick-shot but script provided (not pending)
        add_video(data, "quick2", "tag", title="t2",
                  source="quick-shot", script_status=None)

        pending = query_pending_scripts(data)
        assert len(pending) == 1
        assert pending[0]["topic"] == "quick1"

    def test_transcript_clears_pending_on_query(self, patch_paths):
        """Videos with transcript but still script_status=待補 should show has_transcript=True."""
        data = load_tracking()
        add_video(data, "有逐字稿", "tag", title="t",
                  source="quick-shot", script_status="待補")
        data["videos"][0]["transcript"] = "逐字稿內容"

        pending = query_pending_scripts(data)
        assert len(pending) == 1
        assert pending[0]["has_transcript"] is True
