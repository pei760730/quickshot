"""Tests for lib/deviations.py — script deviation recording + analysis + auto-diff."""


from lib.deviations import (
    record_deviation, link_performance, count_deviations,
    load_deviations, analyze_deviations,
    extract_spoken_lines, diff_script, auto_diff_and_record,
    VALID_LEVELS,
)


class TestRecordDeviation:
    """Test deviation recording."""

    def test_record_minimal(self, patch_paths):
        ok, msg = record_deviation("VID-001", "minimal")
        assert ok is True
        assert "minimal" in msg
        data = load_deviations()
        assert len(data["deviations"]) == 1
        assert data["deviations"][0]["level"] == "minimal"
        assert data["deviations"][0]["changes"] == []

    def test_record_with_changes(self, patch_paths):
        changes = [{"original": "其實", "actual": "我跟你講", "reason": "太文"}]
        ok, msg = record_deviation("VID-001", "moderate", changes=changes)
        assert ok is True
        assert "1 個改動" in msg
        data = load_deviations()
        assert data["deviations"][0]["changes"][0]["original"] == "其實"

    def test_record_significant(self, patch_paths):
        ok, msg = record_deviation("VID-001", "significant")
        assert ok is True
        data = load_deviations()
        assert data["deviations"][0]["level"] == "significant"

    def test_invalid_level(self, patch_paths):
        ok, msg = record_deviation("VID-001", "invalid")
        assert ok is False
        assert "level" in msg

    def test_invalid_changes_not_list(self, patch_paths):
        ok, msg = record_deviation("VID-001", "minimal", changes="not a list")
        assert ok is False
        assert "list" in msg

    def test_invalid_changes_not_dict(self, patch_paths):
        ok, msg = record_deviation("VID-001", "minimal", changes=["not a dict"])
        assert ok is False
        assert "dict" in msg

    def test_overwrite_on_same_vid(self, patch_paths):
        """Same VID should overwrite (re-backfill scenario)."""
        record_deviation("VID-001", "minimal")
        record_deviation("VID-001", "significant",
                         changes=[{"original": "X", "actual": "Y", "reason": "Z"}])
        data = load_deviations()
        assert len(data["deviations"]) == 1
        assert data["deviations"][0]["level"] == "significant"

    def test_multiple_vids(self, patch_paths):
        record_deviation("VID-001", "minimal")
        record_deviation("VID-002", "moderate")
        data = load_deviations()
        assert len(data["deviations"]) == 2


class TestLinkPerformance:
    """Test linking backfill performance to deviation records."""

    def test_link_existing(self, patch_paths):
        record_deviation("VID-001", "minimal")
        result = link_performance("VID-001", "high")
        assert result is True
        data = load_deviations()
        assert data["deviations"][0]["performance"] == "high"

    def test_link_nonexistent(self, patch_paths):
        result = link_performance("VID-999", "high")
        assert result is False


class TestCountDeviations:
    """Test counting complete deviation records."""

    def test_empty(self, patch_paths):
        assert count_deviations() == 0

    def test_without_performance(self, patch_paths):
        """Records without performance don't count."""
        record_deviation("VID-001", "minimal")
        assert count_deviations() == 0

    def test_with_performance(self, patch_paths):
        record_deviation("VID-001", "minimal")
        link_performance("VID-001", "normal")
        assert count_deviations() == 1


class TestAnalyzeDeviations:
    """Test deviation analysis."""

    def test_empty(self, patch_paths):
        report = analyze_deviations()
        assert report["total"] == 0
        assert report["sufficient"] is False

    def test_insufficient(self, patch_paths):
        """Less than 10 records -> not sufficient."""
        for i in range(5):
            record_deviation(f"VID-{i:03d}", "minimal")
            link_performance(f"VID-{i:03d}", "normal")
        report = analyze_deviations()
        assert report["total"] == 5
        assert report["sufficient"] is False

    def test_sufficient_analysis(self, patch_paths):
        """10+ records triggers full analysis."""
        for i in range(10):
            level = "moderate" if i % 2 == 0 else "minimal"
            perf = "high" if i < 3 else "normal"
            changes = [{"original": "其實", "actual": "我跟你講", "reason": "太文"}] if i % 2 == 0 else []
            record_deviation(f"VID-{i:03d}", level, changes=changes)
            link_performance(f"VID-{i:03d}", perf)

        report = analyze_deviations()
        assert report["total"] == 10
        assert report["sufficient"] is True
        assert report["with_changes"] == 5
        assert report["level_dist"]["moderate"] == 5
        assert report["level_dist"]["minimal"] == 5
        assert "frequent_originals" in report
        assert report["frequent_originals"][0]["original"] == "其實"
        assert report["frequent_originals"][0]["count"] == 5

    def test_trend_improving(self, patch_paths):
        """Recent lower deviation levels → improving trend."""
        # Earlier: all significant
        for i in range(7):
            record_deviation(f"VID-{i:03d}", "significant")
            link_performance(f"VID-{i:03d}", "normal")
        # Recent 5: all minimal
        for i in range(7, 12):
            record_deviation(f"VID-{i:03d}", "minimal")
            link_performance(f"VID-{i:03d}", "normal")

        report = analyze_deviations()
        assert report["trend"] == "improving"

    def test_trend_worsening(self, patch_paths):
        """Recent higher deviation levels → worsening trend."""
        # Earlier: all minimal
        for i in range(7):
            record_deviation(f"VID-{i:03d}", "minimal")
            link_performance(f"VID-{i:03d}", "normal")
        # Recent 5: all significant
        for i in range(7, 12):
            record_deviation(f"VID-{i:03d}", "significant")
            link_performance(f"VID-{i:03d}", "normal")

        report = analyze_deviations()
        assert report["trend"] == "worsening"

    def test_perf_by_level(self, patch_paths):
        """Performance cross-tabulation by deviation level."""
        # minimal + high
        record_deviation("VID-001", "minimal")
        link_performance("VID-001", "high")
        # significant + low
        record_deviation("VID-002", "significant")
        link_performance("VID-002", "low")

        report = analyze_deviations()
        assert report["perf_by_level"]["minimal"]["high"] == 1
        assert report["perf_by_level"]["significant"]["low"] == 1

    def test_frequent_reasons(self, patch_paths):
        """Reason aggregation."""
        for i in range(3):
            record_deviation(f"VID-{i:03d}", "moderate",
                             changes=[{"original": f"A{i}", "actual": f"B{i}", "reason": "太文"}])
            link_performance(f"VID-{i:03d}", "normal")

        report = analyze_deviations()
        assert report["frequent_reasons"][0]["reason"] == "太文"
        assert report["frequent_reasons"][0]["count"] == 3


class TestValidLevels:
    """Test level validation constants."""

    def test_valid_levels(self):
        assert VALID_LEVELS == {"minimal", "moderate", "significant"}


# ── 自動比對測試 ────────────────────────────────────────────

# 簡單格式腳本（「引號」對白）
SIMPLE_SCRIPT = """\
> 影片碼：VID-034
> 生成日期：2026-03-20
> Skill：flow-operator
> 封面標題：一個塑膠杯，漲了40%

---

**開頭（0-3s）**
「戰爭，讓我花了五百萬。」

**衝突展開（3-15s）**
「塑膠是石油做的，油價一漲，杯子、封膜、吸管全部跟著漲。」

**真相揭露（15-30s）**
「那這筆錢誰出？不是消費者，因為我不敢漲價。」

**收尾（30-45s）**
「所以一杯飲料的背後，你是想像不到的。」
"""

# 對話格式腳本
DIALOGUE_SCRIPT = """\
> 影片碼：VID-010
> 生成日期：2026-03-07
> Skill：flow-operator v3.0

---

## 完整腳本

【畫面】中景・手持・室內暗光

安（藏鏡人）：又打來了？

Kai：三點半欸

安：誰

Kai：加盟主

安：什麼事？

Kai：鐵門打不開

【畫面】特寫・Kai 表情無奈

安：蛤？鐵門？

Kai：對啊，上次是停電

【字幕收尾】開店不只是算帳，是扛人

## 結構拆解

| 段落 | 時間 |
|------|------|
| 開場 | 0-3s |
"""


class TestExtractSpokenLines:
    """Test extracting spoken lines from script formats."""

    def test_simple_format(self):
        lines = extract_spoken_lines(SIMPLE_SCRIPT)
        assert len(lines) == 4
        assert lines[0] == "戰爭，讓我花了五百萬。"
        assert lines[1] == "塑膠是石油做的，油價一漲，杯子、封膜、吸管全部跟著漲。"
        assert lines[3] == "所以一杯飲料的背後，你是想像不到的。"

    def test_dialogue_format(self):
        lines = extract_spoken_lines(DIALOGUE_SCRIPT)
        assert "又打來了？" in lines
        assert "三點半欸" in lines
        assert "加盟主" in lines
        assert "鐵門打不開" in lines
        assert "開店不只是算帳，是扛人" in lines

    def test_dialogue_skips_stage_directions(self):
        lines = extract_spoken_lines(DIALOGUE_SCRIPT)
        for line in lines:
            assert not line.startswith("【畫面】")

    def test_dialogue_stops_at_structure_section(self):
        """Should not include content from 結構拆解 or later sections."""
        lines = extract_spoken_lines(DIALOGUE_SCRIPT)
        for line in lines:
            assert "段落" not in line
            assert "時間" not in line

    def test_empty_script(self):
        lines = extract_spoken_lines("> metadata\n\n---\n\n")
        assert lines == []


class TestDiffScript:
    """Test intelligent script-vs-subtitle comparison."""

    def test_identical(self):
        orig = ["戰爭，讓我花了五百萬。", "塑膠是石油做的。"]
        subtitle = "戰爭，讓我花了五百萬。\n塑膠是石油做的。"
        result = diff_script(orig, subtitle)
        assert result["similarity"] >= 0.95
        assert result["level"] == "minimal"
        assert result["changes"] == []

    def test_minor_word_change(self):
        orig = ["戰爭，讓我花了五百萬。", "塑膠是石油做的，油價一漲全部跟著漲。"]
        subtitle = "戰爭，讓我花了五百萬。\n塑膠是石油做的，油價一漲通通跟著漲。"
        result = diff_script(orig, subtitle)
        assert result["level"] == "minimal"

    def test_moderate_changes(self):
        orig = [
            "戰爭，讓我花了五百萬。",
            "塑膠是石油做的，油價一漲，杯子封膜吸管全部跟著漲。",
            "那這筆錢誰出？不是消費者。",
            "所以一杯飲料的背後，你是想像不到的。",
        ]
        subtitle = (
            "戰爭，讓我多花了五百萬。\n"
            "塑膠原料是石油，油價漲什麼都漲。\n"
            "這錢誰出？消費者不出。\n"
            "一杯飲料背後，你想不到。"
        )
        result = diff_script(orig, subtitle)
        assert result["level"] in ("minimal", "moderate")
        assert len(result["changes"]) > 0

    def test_significant_changes(self):
        orig = [
            "戰爭，讓我花了五百萬。",
            "塑膠是石油做的，油價一漲全部跟著漲。",
        ]
        subtitle = "今天來聊一個完全不同的話題。\n你知道開店最累的是什麼嗎？\n不是做飲料，是管人。"
        result = diff_script(orig, subtitle)
        assert result["level"] == "significant"
        assert result["similarity"] < 0.55

    def test_added_lines(self):
        orig = ["第一句。"]
        subtitle = "第一句。\n第二句是新加的。\n第三句也是。"
        result = diff_script(orig, subtitle)
        added = [c for c in result["changes"] if c["type"] == "added"]
        assert len(added) >= 1

    def test_removed_lines(self):
        orig = ["第一句。", "第二句。", "第三句。"]
        subtitle = "第一句。"
        result = diff_script(orig, subtitle)
        removed = [c for c in result["changes"] if c["type"] == "removed"]
        assert len(removed) >= 1

    def test_both_empty(self):
        result = diff_script([], "")
        assert result["similarity"] == 1.0
        assert result["level"] == "minimal"

    def test_summary_format(self):
        orig = ["原文第一句。", "原文第二句。"]
        subtitle = "改過的第一句。\n原文第二句。"
        result = diff_script(orig, subtitle)
        assert "相似度" in result["summary"]


class TestAutoDiffAndRecord:
    """Test the full auto-diff pipeline."""

    def test_full_flow(self, patch_paths, tmp_project):
        """Full flow: script exists → diff → record."""
        from lib.pipeline import load_pipeline, save_pipeline

        # Setup: create script file + pipeline entry
        script_dir = tmp_project / "03-production-line" / "02-ready-to-shoot" / "kai"
        script_dir.mkdir(parents=True, exist_ok=True)
        script_file = script_dir / "2026-03-20_test_腳本_V1.md"
        script_file.write_text(SIMPLE_SCRIPT, encoding="utf-8")

        rel_path = "03-production-line/02-ready-to-shoot/kai/2026-03-20_test_腳本_V1.md"

        data = load_pipeline()
        data["items"].append({
            "idea_id": "IDEA-099",
            "vid": "VID-099",
            "topic": "test",
            "status": "已上線",
            "created_date": "2026-03-20",
            "script_path": rel_path,
            "backfill": {"performance": "high"},
        })
        save_pipeline(data)

        # Run auto-diff with slightly modified subtitle
        subtitle = "戰爭，讓我多花了五百萬。\n塑膠是石油做的，油價一漲，杯子封膜吸管全部跟著漲。\n那這筆錢誰出？不是消費者，因為我不敢漲價。\n所以一杯飲料的背後，你是想像不到的。"

        ok, result = auto_diff_and_record("VID-099", subtitle)
        assert ok is True
        assert "similarity" in result
        assert result["level"] in VALID_LEVELS
        assert result["performance_linked"] == "high"

        # Verify deviation was recorded
        dev_data = load_deviations()
        assert len(dev_data["deviations"]) == 1
        assert dev_data["deviations"][0]["vid"] == "VID-099"

    def test_vid_not_found(self, patch_paths):
        ok, result = auto_diff_and_record("VID-999", "some text")
        assert ok is False
        assert "找不到" in result

    def test_no_script_path(self, patch_paths):
        from lib.pipeline import load_pipeline, save_pipeline

        data = load_pipeline()
        data["items"].append({
            "idea_id": "IDEA-098",
            "vid": "VID-098",
            "topic": "test",
            "status": "已上線",
            "created_date": "2026-03-20",
        })
        save_pipeline(data)

        ok, result = auto_diff_and_record("VID-098", "some text")
        assert ok is False
        assert "script_path" in result

    def test_script_file_missing(self, patch_paths):
        from lib.pipeline import load_pipeline, save_pipeline

        data = load_pipeline()
        data["items"].append({
            "idea_id": "IDEA-097",
            "vid": "VID-097",
            "topic": "test",
            "status": "已上線",
            "created_date": "2026-03-20",
            "script_path": "nonexistent/path.md",
        })
        save_pipeline(data)

        ok, result = auto_diff_and_record("VID-097", "some text")
        assert ok is False
        assert "不存在" in result
