"""Tests for pipeline.py — CRUD + state machine."""

import pytest
from conftest import make_video

from lib.pipeline import (
    load_tracking, save_tracking, find_video, next_vid,
    add_video, transition, format_video, update_publish_date,
    add_transcript, query_pending_scripts, bind_script_path, delete_video,
)
from lib.pipeline import _get_transitions


class TestFindVideo:
    def test_find_existing(self):
        data = {"videos": [make_video("VID-001"), make_video("VID-002")]}
        idx, v = find_video(data, "VID-002")
        assert idx == 1
        assert v["vid"] == "VID-002"

    def test_find_missing(self):
        data = {"videos": [make_video("VID-001")]}
        idx, v = find_video(data, "VID-999")
        assert idx is None
        assert v is None

    def test_find_empty(self):
        data = {"videos": []}
        idx, v = find_video(data, "VID-001")
        assert idx is None
        assert v is None


class TestNextVid:
    def test_empty_list(self):
        data = {"_meta": {}, "items": []}
        assert next_vid(data) == "VID-001"

    def test_cached_next_vid(self):
        data = {"_meta": {"next_vid": 5}, "items": []}
        assert next_vid(data) == "VID-005"

    def test_fallback_scan(self):
        data = {
            "_meta": {},
            "items": [make_video("VID-003"), make_video("VID-001")],
        }
        assert next_vid(data) == "VID-004"


class TestAddVideo:
    def test_add_pipeline(self, patch_paths):
        data = load_tracking()
        vid = add_video(
            data, "加盟割韭菜", "創業",
            source_inspiration="想講加盟",
            skill_used="flow-operator",
            title="加盟是不是割韭菜",
        )
        assert vid == "VID-001"
        assert len(data["videos"]) == 1
        assert data["videos"][0]["status"] == "待拍"
        assert data["videos"][0]["source"] == "pipeline"

    def test_add_quickshot(self, patch_paths):
        data = load_tracking()
        vid = add_video(
            data, "臨時拍的", "生活", title="隨便拍",
            source="quick-shot", initial_status="剪輯中",
            script_status="待補",
        )
        assert vid == "VID-001"
        assert data["videos"][0]["source"] == "quick-shot"
        assert data["videos"][0]["script_status"] == "待補"

    def test_add_invalid_status(self, patch_paths):
        data = load_tracking()
        with pytest.raises(ValueError, match="非法初始狀態"):
            add_video(data, "test", "tag", title="t", source="quick-shot",
                      initial_status="不存在")

    def test_add_invalid_source(self, patch_paths):
        data = load_tracking()
        with pytest.raises(ValueError, match="非法來源"):
            add_video(data, "test", "tag", title="t", source="invalid")

    def test_add_pipeline_missing_fields(self, patch_paths):
        data = load_tracking()
        with pytest.raises(ValueError, match="缺少必填欄位"):
            add_video(data, "test", "tag")  # missing title, skill_used, source_inspiration

    def test_add_increments_vid(self, patch_paths):
        data = load_tracking()
        vid1 = add_video(data, "T1", "tag", title="t1", source="quick-shot")
        vid2 = add_video(data, "T2", "tag", title="t2", source="quick-shot")
        assert vid1 == "VID-001"
        assert vid2 == "VID-002"


class TestTransition:
    def test_valid_transition_dai_to_jianji(self, patch_paths):
        """待拍 → 剪輯中 (with script_path)"""
        data = load_tracking()
        # Create a script file
        sp = "03-production-line/02-ready-to-shoot/2026-03-01_test_腳本_V1.md"
        script_file = patch_paths / sp
        script_file.parent.mkdir(parents=True, exist_ok=True)
        script_file.write_text("> 影片碼：VID-001\n---\n腳本內容", encoding="utf-8")

        add_video(data, "test", "tag", title="t", source="quick-shot",
                  script_path=sp)
        ok, msg = transition(data, "VID-001", "剪輯中")
        assert ok is True
        assert data["videos"][0]["status"] == "剪輯中"

    def test_missing_script_blocks_jianji(self, patch_paths):
        """待拍 → 剪輯中 without script_path should fail"""
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot")
        ok, msg = transition(data, "VID-001", "剪輯中")
        assert ok is False
        assert "script_path" in msg

    def test_illegal_transition(self, patch_paths):
        """剪輯中 → 待拍 is forbidden"""
        data = load_tracking()
        sp = "03-production-line/02-ready-to-shoot/2026-03-01_test_腳本_V1.md"
        script_file = patch_paths / sp
        script_file.parent.mkdir(parents=True, exist_ok=True)
        script_file.write_text("test", encoding="utf-8")

        add_video(data, "test", "tag", title="t", source="quick-shot",
                  script_path=sp)
        transition(data, "VID-001", "剪輯中")
        ok, msg = transition(data, "VID-001", "待拍")
        assert ok is False
        assert "禁止" in msg

    def test_transition_nonexistent_vid(self, patch_paths):
        data = load_tracking()
        ok, msg = transition(data, "VID-999", "剪輯中")
        assert ok is False
        assert "找不到" in msg

    def test_transition_invalid_status(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot")
        ok, msg = transition(data, "VID-001", "不存在的狀態")
        assert ok is False
        assert "非法狀態" in msg

    def test_valid_transitions_config(self):
        """Verify transition config from _meta: 已上線 has no outgoing transitions"""
        data = load_tracking()
        transitions = _get_transitions(data)
        assert transitions["已上線"] == []
        assert "剪輯中" in transitions["待拍"]
        assert "已上線" in transitions["剪輯中"]
        assert "待拍" not in transitions["剪輯中"]

    def test_shangxian_moves_script(self, patch_paths):
        """已上線 should move script from 02-ready-to-shoot to 03-done"""
        data = load_tracking()
        sp = "03-production-line/02-ready-to-shoot/2026-03-01_test_腳本_V1.md"
        script_file = patch_paths / sp
        script_file.parent.mkdir(parents=True, exist_ok=True)
        script_file.write_text("> 影片碼：VID-001\n---\n腳本", encoding="utf-8")

        add_video(data, "test", "tag", title="t", source="quick-shot",
                  script_path=sp)
        transition(data, "VID-001", "剪輯中")
        ok, msg = transition(data, "VID-001", "已上線")
        assert ok is True
        assert "03-done" in data["videos"][0]["script_path"]
        assert (patch_paths / "03-production-line" / "03-done" / "2026-03-01_test_腳本_V1.md").exists()

    def test_transition_back_to_jianji_moves_script_back_to_ready(self, patch_paths):
        """跨邊界反向轉換時應同步搬回 02-ready-to-shoot。"""
        data = load_tracking()
        data["_meta"].setdefault("transitions", {})["已上線"] = ["剪輯中"]
        sp = "03-production-line/03-done/2026-03-01_test_腳本_V1.md"
        script_file = patch_paths / sp
        script_file.parent.mkdir(parents=True, exist_ok=True)
        script_file.write_text("> 影片碼：VID-001\n---\n腳本", encoding="utf-8")

        add_video(
            data, "test", "tag", title="t", source="quick-shot",
            initial_status="已上線", script_path=sp,
        )
        ok, _msg = transition(data, "VID-001", "剪輯中")
        assert ok is True
        assert "02-ready-to-shoot" in data["videos"][0]["script_path"]
        assert (patch_paths / "03-production-line" / "02-ready-to-shoot" / "2026-03-01_test_腳本_V1.md").exists()


class TestBindAndDelete:
    def test_bind_script_path_requires_existing_file(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot")
        ok, msg = bind_script_path(data, "VID-001", "03-production-line/02-ready-to-shoot/missing.md")
        assert ok is False
        assert "不存在" in msg

    def test_bind_script_path_sets_only_path(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot")
        sp = "03-production-line/02-ready-to-shoot/2026-03-17_bind_腳本.md"
        p = patch_paths / sp
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("content", encoding="utf-8")
        ok, _msg = bind_script_path(data, "VID-001", sp)
        assert ok is True
        assert data["videos"][0]["script_path"] == sp

    def test_delete_video_removes_only_data(self, patch_paths):
        data = load_tracking()
        sp = "03-production-line/02-ready-to-shoot/2026-03-17_delete_腳本.md"
        p = patch_paths / sp
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("content", encoding="utf-8")
        add_video(data, "test", "tag", title="t", source="quick-shot", script_path=sp)
        ok, _msg, _removed = delete_video(data, "VID-001")
        assert ok is True
        assert find_video(data, "VID-001")[1] is None
        assert p.exists()


class TestUpdatePublishDate:
    def test_update_date(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot")
        data["videos"][0]["publish_date"] = "2026-03-01"
        save_tracking(data)

        ok, msg, old, new = update_publish_date(data, "VID-001", "2026-03-10")
        assert ok is True
        assert data["videos"][0]["publish_date"] == "2026-03-10"

    def test_update_invalid_date(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot")
        ok, msg, _, _ = update_publish_date(data, "VID-001", "not-a-date")
        assert ok is False
        assert "日期無效" in msg

    def test_update_same_date(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot")
        data["videos"][0]["publish_date"] = "2026-03-01"
        save_tracking(data)

        ok, msg, _, _ = update_publish_date(data, "VID-001", "2026-03-01")
        assert ok is False

    def test_update_nonexistent(self, patch_paths):
        data = load_tracking()
        ok, msg, _, _ = update_publish_date(data, "VID-999", "2026-03-10")
        assert ok is False
        assert "找不到" in msg


class TestAddTranscript:
    def test_add_transcript_success(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        ok, msg = add_transcript(data, "VID-001", "大家好，今天要跟你們聊一個話題")
        assert ok is True
        assert "15 字" in msg
        assert data["videos"][0]["transcript"] == "大家好，今天要跟你們聊一個話題"

    def test_add_transcript_not_shangxian(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot")  # 待拍
        ok, msg = add_transcript(data, "VID-001", "text")
        assert ok is False
        assert "已上線" in msg

    def test_add_transcript_empty(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        ok, msg = add_transcript(data, "VID-001", "")
        assert ok is False
        assert "空" in msg

    def test_add_transcript_nonexistent(self, patch_paths):
        data = load_tracking()
        ok, msg = add_transcript(data, "VID-999", "text")
        assert ok is False
        assert "找不到" in msg

    def test_add_transcript_strips_whitespace(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        ok, msg = add_transcript(data, "VID-001", "  有空白  \n")
        assert ok is True
        assert data["videos"][0]["transcript"] == "有空白"


class TestFormatVideo:
    def test_basic_format(self):
        v = make_video()
        text = format_video(v)
        assert "VID-001" in text
        assert "測試主題" in text
        assert "待拍" in text

    def test_format_with_transcript(self):
        v = make_video()
        v["transcript"] = "大家好這是一段很長的逐字稿內容" * 5
        text = format_video(v)
        assert "逐字稿" in text
        assert "字）" in text


class TestQueryPendingScripts:
    def test_empty(self):
        data = {"videos": []}
        assert query_pending_scripts(data) == []

    def test_no_pending(self):
        data = {"videos": [make_video("VID-001")]}
        assert query_pending_scripts(data) == []

    def test_finds_pending(self):
        v = make_video("VID-001")
        v["script_status"] = "待補"
        v["source"] = "quick-shot"
        data = {"videos": [v]}
        result = query_pending_scripts(data)
        assert len(result) == 1
        assert result[0]["vid"] == "VID-001"
        assert result[0]["days_pending"] >= 0

    def test_sorted_by_days_desc(self):
        v1 = make_video("VID-001")
        v1["script_status"] = "待補"
        v1["created_date"] = "2026-03-20"
        v2 = make_video("VID-002")
        v2["script_status"] = "待補"
        v2["created_date"] = "2026-03-10"
        data = {"videos": [v1, v2]}
        result = query_pending_scripts(data)
        assert result[0]["vid"] == "VID-002"  # older = more days
        assert result[1]["vid"] == "VID-001"

    def test_has_transcript_flag(self):
        v = make_video("VID-001")
        v["script_status"] = "待補"
        v["transcript"] = "逐字稿內容"
        data = {"videos": [v]}
        result = query_pending_scripts(data)
        assert result[0]["has_transcript"] is True

    def test_ignores_non_pending(self):
        v1 = make_video("VID-001")
        v1["script_status"] = "待補"
        v2 = make_video("VID-002")
        v2["script_status"] = None
        data = {"videos": [v1, v2]}
        result = query_pending_scripts(data)
        assert len(result) == 1
        assert result[0]["vid"] == "VID-001"
