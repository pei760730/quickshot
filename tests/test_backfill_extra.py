"""Tests for backfill functions missing coverage:
auto_extract_from_script, performance_report.
"""

import json
from pathlib import Path


from conftest import make_video, empty_video_data, empty_patterns


# ── auto_extract_from_script ─────────────────────────────

class TestAutoExtractFromScript:
    """auto_extract_from_script() 從腳本自動解析學習特徵。"""

    def test_returns_none_when_no_content(self, patch_paths):
        from lib.backfill import auto_extract_from_script
        result = auto_extract_from_script(None, transcript=None)
        assert result is None

    def test_returns_none_for_nonexistent_file(self, patch_paths):
        from lib.backfill import auto_extract_from_script
        result = auto_extract_from_script("nonexistent/script.md")
        assert result is None

    def test_extracts_from_transcript(self, patch_paths):
        from lib.backfill import auto_extract_from_script
        transcript = "你知道台灣有多少加盟店嗎？\n超過10萬家。\n但是真正賺錢的不到三成。\n留言告訴我你怎麼看。"
        result = auto_extract_from_script(None, transcript=transcript)
        assert result is not None
        assert result["hook"]  # Should have hook text
        assert result["turning_points"]  # "但是" is a turning word

    def test_detects_D3_opening(self, patch_paths):
        from lib.backfill import auto_extract_from_script
        transcript = "台灣有10萬家加盟店\n但只有3成賺錢\n這個數字很驚人"
        result = auto_extract_from_script(None, transcript=transcript)
        assert result["opening_guess"] == "D3"  # 數字衝擊

    def test_detects_B2_opening(self, patch_paths):
        from lib.backfill import auto_extract_from_script
        transcript = "你知道為什麼很多人創業失敗嗎\n到底是什麼原因\n今天來分析"
        result = auto_extract_from_script(None, transcript=transcript)
        assert result["opening_guess"] == "B2"  # 好奇缺口

    def test_detects_C2_cta(self, patch_paths):
        from lib.backfill import auto_extract_from_script
        lines = ["開頭"] * 20 + ["如果覺得有用記得按讚收藏"]
        transcript = "\n".join(lines)
        result = auto_extract_from_script(None, transcript=transcript)
        assert result["cta_guess"] == "C2"  # 按讚收藏

    def test_detects_C3_cta(self, patch_paths):
        from lib.backfill import auto_extract_from_script
        lines = ["開頭"] * 20 + ["留言告訴我你的想法"]
        transcript = "\n".join(lines)
        result = auto_extract_from_script(None, transcript=transcript)
        assert result["cta_guess"] == "C3"

    def test_turning_points_limit_three(self, patch_paths):
        from lib.backfill import auto_extract_from_script
        transcript = "\n".join([
            "但是第一個問題來了",
            "沒想到結果完全不同",
            "關鍵是這個數字",
            "真相是沒人知道",
            "後來又翻轉了",
        ])
        result = auto_extract_from_script(None, transcript=transcript)
        assert len(result["turning_points"]) == 3  # max 3

    def test_reads_from_script_file(self, patch_paths):
        from lib.backfill import auto_extract_from_script
        # Create a script file
        script_dir = patch_paths / "03-production-line" / "02-ready-to-shoot"
        script_file = script_dir / "2026-03-17_test_腳本_V1.md"
        script_file.write_text(
            "> 影片碼：VID-001\n---\n## 腳本\n你知道5萬家店倒了嗎\n但是真正原因沒人講",
            encoding="utf-8")
        result = auto_extract_from_script(
            "03-production-line/02-ready-to-shoot/2026-03-17_test_腳本_V1.md")
        assert result is not None
        assert result["hook"]

    def test_skips_metadata_lines(self, patch_paths):
        from lib.backfill import auto_extract_from_script
        transcript = "> 影片碼：VID-001\n> 日期\n---\n## 正文\n你知道嗎\n這很重要"
        result = auto_extract_from_script(None, transcript=transcript)
        assert result is not None
        # Hook should not contain metadata
        assert "影片碼" not in result["hook"]

    def test_empty_body_returns_none(self, patch_paths):
        from lib.backfill import auto_extract_from_script
        transcript = "> metadata\n---\n## 腳本\n"
        result = auto_extract_from_script(None, transcript=transcript)
        assert result is None


# ── performance_report ───────────────────────────────────

class TestPerformanceReport:
    """performance_report() 全影片表現總覽。"""

    def test_empty_data(self, patch_paths):
        from lib.backfill import performance_report
        r = performance_report(empty_video_data())
        assert r["total"] == 0
        assert r["backfilled"] == 0
        assert r["high"] == []
        assert r["normal"] == []
        assert r["low"] == []
        assert r["no_backfill"] == []

    def test_categorizes_performance(self, patch_paths):
        from lib.backfill import performance_report
        data = empty_video_data()
        data["videos"].append(make_video(
            vid="VID-001", status="已上線",
            backfill={"views": 500000, "retention_3s": 80, "completion_rate": 50,
                      "performance": "high", "path": "AB"}))
        data["videos"].append(make_video(
            vid="VID-002", status="已上線",
            backfill={"views": 1000, "retention_3s": 50, "completion_rate": 25,
                      "performance": "normal"}))
        data["videos"].append(make_video(
            vid="VID-003", status="已上線",
            backfill={"views": 500, "retention_3s": 20, "completion_rate": 10,
                      "performance": "low"}))
        r = performance_report(data)
        assert len(r["high"]) == 1
        assert len(r["normal"]) == 1
        assert len(r["low"]) == 1
        assert r["backfilled"] == 3
        assert r["high"][0]["vid"] == "VID-001"

    def test_no_backfill_only_published(self, patch_paths):
        from lib.backfill import performance_report
        data = empty_video_data()
        data["videos"].append(make_video(vid="VID-001", status="已上線"))
        data["videos"].append(make_video(vid="VID-002", status="待拍"))
        r = performance_report(data)
        assert "VID-001" in r["no_backfill"]
        assert "VID-002" not in r["no_backfill"]

    def test_opening_and_cta_counts(self, patch_paths):
        from lib.backfill import performance_report
        # Write patterns with data
        pp = empty_patterns()
        pp["proven_openings"] = [
            {"code": "D3", "vid_evidence": ["VID-001", "VID-002"]},
        ]
        pp["proven_ctas"] = [
            {"code": "C1", "vid_evidence": ["VID-001"]},
        ]
        import lib.config as _cfg
        Path(_cfg.PERFORMANCE_PATTERNS_JSON).write_text(
            json.dumps(pp, ensure_ascii=False), encoding="utf-8")

        r = performance_report(empty_video_data())
        assert r["opening_counts"]["D3"] == 2
        assert r["cta_counts"]["C1"] == 1

    def test_degraded_patterns(self, patch_paths):
        from lib.backfill import performance_report
        pp = empty_patterns()
        pp["proven_openings"] = [
            {"code": "D1", "vid_evidence": ["VID-001"],
             "degraded": True, "degraded_date": "2026-03-15",
             "low_evidence": ["VID-005"]},
        ]
        import lib.config as _cfg
        Path(_cfg.PERFORMANCE_PATTERNS_JSON).write_text(
            json.dumps(pp, ensure_ascii=False), encoding="utf-8")

        r = performance_report(empty_video_data())
        assert len(r["degraded_patterns"]) == 1
        assert r["degraded_patterns"][0]["code"] == "D1"

    def test_risk_patterns_count(self, patch_paths):
        from lib.backfill import performance_report
        pp = empty_patterns()
        pp["risk_patterns"] = [
            {"pattern": "無衝突感", "vid_evidence": ["VID-003"]},
        ]
        import lib.config as _cfg
        Path(_cfg.PERFORMANCE_PATTERNS_JSON).write_text(
            json.dumps(pp, ensure_ascii=False), encoding="utf-8")

        r = performance_report(empty_video_data())
        assert r["risk_patterns_count"] == 1

    def test_total_count(self, patch_paths):
        from lib.backfill import performance_report
        data = empty_video_data()
        data["videos"].append(make_video(vid="VID-001", status="待拍"))
        data["videos"].append(make_video(vid="VID-002", status="已上線"))
        r = performance_report(data)
        assert r["total"] == 2
