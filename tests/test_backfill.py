"""Tests for lib/backfill.py — performance classification + backfill + learning + diagnosis."""

from lib.backfill import (
    classify_performance, classify_performance_display,
    backfill_video, extract_learning, query_unextracted,
    load_performance_patterns, save_performance_patterns,
    diagnose_video, cleanup_unverified_formulas,
    _check_pattern_decay, performance_report,
    _best_match, _OPENING_PATTERNS, _CTA_PATTERNS,
    auto_extract_from_script,
    PATTERN_KEYS, win_rate_note, compute_pattern_stats,
    cross_dimensional_stats, skill_effectiveness,
)
from lib.pipeline import load_tracking, add_video, save_tracking


class TestClassifyPerformance:
    """Test the performance classification thresholds."""

    def test_high_path_a(self):
        """retention >= 70% AND completion >= 40% -> high, path A"""
        level, path, reason = classify_performance(10000, 75, 45)
        assert level == "high"
        assert path == "A"

    def test_high_path_b(self):
        """views >= 300000 AND completion >= 40% -> high, path B"""
        level, path, reason = classify_performance(500000, 50, 45)
        assert level == "high"
        assert path == "B"

    def test_high_path_ab(self):
        """Both path A and B -> high, path AB"""
        level, path, reason = classify_performance(500000, 80, 50)
        assert level == "high"
        assert path == "AB"

    def test_low_retention(self):
        """retention < 40% -> low"""
        level, path, reason = classify_performance(10000, 30, 25)
        assert level == "low"
        assert path is None
        assert "留存" in reason

    def test_low_completion(self):
        """completion < 15% -> low"""
        level, path, reason = classify_performance(10000, 50, 10)
        assert level == "low"
        assert "完播" in reason

    def test_low_both(self):
        """Both retention < 40% and completion < 15% -> low"""
        level, path, reason = classify_performance(10000, 30, 10)
        assert level == "low"
        assert "留存" in reason
        assert "完播" in reason

    def test_normal(self):
        """Not high, not low -> normal"""
        level, path, reason = classify_performance(10000, 50, 25)
        assert level == "normal"
        assert path is None

    def test_boundary_high_a_exact(self):
        """Exact boundary: retention=70, completion=40 -> high"""
        level, path, reason = classify_performance(10000, 70, 40)
        assert level == "high"
        assert path == "A"

    def test_boundary_low_retention_exact(self):
        """retention exactly threshold is NOT low (< threshold is low)"""
        from lib.config import PERFORMANCE_THRESHOLDS
        lo = PERFORMANCE_THRESHOLDS["low"]
        level, path, reason = classify_performance(10000, lo["retention_3s_max"], lo["completion_rate_max"] + 1)
        assert level == "normal"

    def test_boundary_low_completion_exact(self):
        """completion exactly threshold is NOT low (< threshold is low)"""
        from lib.config import PERFORMANCE_THRESHOLDS
        lo = PERFORMANCE_THRESHOLDS["low"]
        level, path, reason = classify_performance(10000, lo["retention_3s_max"] + 1, lo["completion_rate_max"])
        assert level == "normal"


class TestClassifyPerformanceDisplay:
    def test_high_reach(self):
        display = classify_performance_display(500000, 80, 50)
        assert "高" in display
        assert "觸及" in display

    def test_high_retention_only(self):
        display = classify_performance_display(10000, 80, 50)
        assert "留存高" in display

    def test_low(self):
        display = classify_performance_display(10000, 30, 10)
        assert "低" in display

    def test_normal(self):
        display = classify_performance_display(10000, 50, 25)
        assert "普通" in display

    def test_handles_string_inputs(self):
        display = classify_performance_display("500000", "80", "50")
        assert "高" in display

    def test_handles_none_inputs(self):
        display = classify_performance_display(None, None, None)
        assert "低" in display  # 0, 0, 0 -> low


class TestBackfillVideo:
    def test_backfill_success(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")

        ok, msg, result = backfill_video(data, "VID-001",
                                         views=100000, retention_3s=60, completion_rate=30)
        assert ok is True
        assert result["level"] == "normal"
        assert data["videos"][0]["backfill"]["views"] == 100000
        # normal 標記已提取（數據已記錄、診斷已完成，無需額外動作）
        assert data["videos"][0]["backfill"]["learning_extracted"] is True

    def test_backfill_high_performance(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")

        ok, msg, result = backfill_video(data, "VID-001",
                                         views=500000, retention_3s=80, completion_rate=50)
        assert ok is True
        assert result["level"] == "high"
        assert result["path"] == "AB"

    def test_backfill_high_no_script_warns(self, patch_paths):
        """高表現但無腳本 → warnings 應包含 need_manual 提醒。"""
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")

        ok, msg, result = backfill_video(data, "VID-001",
                                         views=500000, retention_3s=80, completion_rate=50)
        assert ok is True
        assert result["level"] == "high"
        # 無腳本 → need_manual_high → warning 應被加入
        assert any("手動" in w or "extract-learning" in w for w in result["warnings"])

    def test_backfill_not_shangxian(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot")  # 待拍

        ok, msg, result = backfill_video(data, "VID-001",
                                         views=100, retention_3s=50, completion_rate=30)
        assert ok is False
        assert "已上線" in msg

    def test_backfill_nonexistent(self, patch_paths):
        data = load_tracking()
        ok, msg, result = backfill_video(data, "VID-999",
                                         views=100, retention_3s=50, completion_rate=30)
        assert ok is False
        assert "找不到" in msg

    def test_backfill_preserves_learning_extracted(self, patch_paths):
        """Re-backfilling should preserve learning_extracted=True."""
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")

        backfill_video(data, "VID-001", views=100, retention_3s=50, completion_rate=30)
        data["videos"][0]["backfill"]["learning_extracted"] = True
        save_tracking(data)

        ok, msg, result = backfill_video(data, "VID-001",
                                         views=200, retention_3s=55, completion_rate=35)
        assert ok is True
        assert data["videos"][0]["backfill"]["learning_extracted"] is True
        assert data["videos"][0]["backfill"]["views"] == 200


class TestBackfillBoundsValidation:
    """Test that backfill_video rejects out-of-range values."""

    def test_negative_views(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        ok, msg, _ = backfill_video(data, "VID-001",
                                     views=-1, retention_3s=50, completion_rate=30)
        assert ok is False
        assert "views" in msg

    def test_retention_over_100(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        ok, msg, _ = backfill_video(data, "VID-001",
                                     views=100, retention_3s=150, completion_rate=30)
        assert ok is False
        assert "retention_3s" in msg

    def test_negative_retention(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        ok, msg, _ = backfill_video(data, "VID-001",
                                     views=100, retention_3s=-5, completion_rate=30)
        assert ok is False
        assert "retention_3s" in msg

    def test_completion_over_100(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        ok, msg, _ = backfill_video(data, "VID-001",
                                     views=100, retention_3s=50, completion_rate=200)
        assert ok is False
        assert "completion_rate" in msg

    def test_negative_engagement(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        ok, msg, _ = backfill_video(data, "VID-001",
                                     views=100, retention_3s=50, completion_rate=30,
                                     engagement_rate=-1)
        assert ok is False
        assert "engagement_rate" in msg

    def test_negative_likes(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        ok, msg, _ = backfill_video(data, "VID-001",
                                     views=100, retention_3s=50, completion_rate=30,
                                     likes=-10)
        assert ok is False
        assert "likes" in msg

    def test_zero_video_length(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        ok, msg, _ = backfill_video(data, "VID-001",
                                     views=100, retention_3s=50, completion_rate=30,
                                     video_length_seconds=0)
        assert ok is False
        assert "video_length_seconds" in msg

    def test_multiple_bounds_errors(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        ok, msg, _ = backfill_video(data, "VID-001",
                                     views=-1, retention_3s=200, completion_rate=-5)
        assert ok is False
        assert "views" in msg
        assert "retention_3s" in msg
        assert "completion_rate" in msg

    def test_boundary_zero_valid(self, patch_paths):
        """Edge: views=0, retention=0, completion=0 should be valid."""
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        ok, msg, _ = backfill_video(data, "VID-001",
                                     views=0, retention_3s=0, completion_rate=0)
        assert ok is True

    def test_boundary_100_valid(self, patch_paths):
        """Edge: retention=100, completion=100 should be valid."""
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        ok, msg, _ = backfill_video(data, "VID-001",
                                     views=100, retention_3s=100, completion_rate=100)
        assert ok is True


class TestExtractLearning:
    def test_extract_high(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        backfill_video(data, "VID-001", views=500000, retention_3s=80, completion_rate=50)

        ok, msg = extract_learning(data, "VID-001",
                                   opening="D3", cta="C1", formula="數字衝擊開場")
        assert ok is True
        assert data["videos"][0]["learning"]["type"] == "high"
        assert data["videos"][0]["backfill"]["learning_extracted"] is True

        # Check performance-patterns updated
        pp = load_performance_patterns()
        assert any(o["code"] == "D3" for o in pp["proven_openings"])
        assert any(c["code"] == "C1" for c in pp["proven_ctas"])
        assert any(f["formula"] == "數字衝擊開場" for f in pp["proven_formulas"])

    def test_extract_high_partial_cta_only(self, patch_paths):
        """高表現：只有 CTA 沒有 opening → 應成功（部分匹配）。"""
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        backfill_video(data, "VID-001", views=500000, retention_3s=80, completion_rate=50)

        ok, msg = extract_learning(data, "VID-001", cta="C1")
        assert ok is True
        assert data["videos"][0]["learning"]["cta"] == "C1"
        assert "opening" not in data["videos"][0]["learning"]

    def test_extract_high_partial_opening_only(self, patch_paths):
        """高表現：只有 opening 沒有 CTA → 應成功（部分匹配）。"""
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        backfill_video(data, "VID-001", views=500000, retention_3s=80, completion_rate=50)

        ok, msg = extract_learning(data, "VID-001", opening="D3")
        assert ok is True
        assert data["videos"][0]["learning"]["opening"] == "D3"
        assert "cta" not in data["videos"][0]["learning"]

    def test_extract_high_neither_fails(self, patch_paths):
        """高表現：opening 和 CTA 都沒有 → 應失敗。"""
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        backfill_video(data, "VID-001", views=500000, retention_3s=80, completion_rate=50)

        ok, msg = extract_learning(data, "VID-001")
        assert ok is False

    def test_extract_low(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        backfill_video(data, "VID-001", views=100, retention_3s=20, completion_rate=10)

        ok, msg = extract_learning(data, "VID-001", failure_mode="開場太慢")
        assert ok is True
        assert data["videos"][0]["learning"]["type"] == "low"

        pp = load_performance_patterns()
        assert any(rp["mode"] == "開場太慢" for rp in pp["risk_patterns"])

    def test_extract_low_missing_failure_mode(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        backfill_video(data, "VID-001", views=100, retention_3s=20, completion_rate=10)

        ok, msg = extract_learning(data, "VID-001")
        assert ok is False
        assert "failure-mode" in msg

    def test_extract_normal(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        backfill_video(data, "VID-001", views=10000, retention_3s=50, completion_rate=25)

        ok, msg = extract_learning(data, "VID-001")
        assert ok is True
        assert data["videos"][0]["learning"]["type"] == "normal"

    def test_extract_no_backfill(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")

        ok, msg = extract_learning(data, "VID-001", opening="D3", cta="C1")
        assert ok is False
        assert "回填" in msg


class TestQueryUnextracted:
    def test_finds_unextracted(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        backfill_video(data, "VID-001", views=500000, retention_3s=80, completion_rate=50)

        results = query_unextracted(data)
        assert len(results) == 1
        assert results[0]["vid"] == "VID-001"
        assert results[0]["performance"] == "high"

    def test_extracted_not_included(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        backfill_video(data, "VID-001", views=500000, retention_3s=80, completion_rate=50)
        extract_learning(data, "VID-001", opening="D3", cta="C1")

        results = query_unextracted(data)
        assert len(results) == 0


class TestCleanupFormulas:
    def test_moves_old_no_evidence(self, patch_paths):
        pp = load_performance_patterns()
        pp["proven_formulas"] = [
            {"formula": "old formula", "vid_evidence": [], "added_date": "2020-01-01", "tags": []},
            {"formula": "valid", "vid_evidence": ["VID-001"], "added_date": "2026-01-01", "tags": []},
        ]
        moved = cleanup_unverified_formulas(pp)
        assert len(moved) == 1
        assert moved[0]["formula"] == "old formula"
        assert len(pp["proven_formulas"]) == 1
        assert pp["proven_formulas"][0]["formula"] == "valid"
        assert len(pp["unverified_formulas"]) == 1

    def test_keeps_recent_no_evidence(self, patch_paths):
        pp = load_performance_patterns()
        pp["proven_formulas"] = [
            {"formula": "new formula", "vid_evidence": [], "added_date": "2026-03-15", "tags": []},
        ]
        moved = cleanup_unverified_formulas(pp)
        assert len(moved) == 0
        assert len(pp["proven_formulas"]) == 1

    def test_no_added_date_treated_as_old(self, patch_paths):
        pp = load_performance_patterns()
        pp["proven_formulas"] = [
            {"formula": "ancient", "vid_evidence": [], "tags": []},
        ]
        moved = cleanup_unverified_formulas(pp)
        assert len(moved) == 1


class TestDiagnoseVideo:
    """Test the automatic diagnosis after backfill."""

    def test_saves_dominant_is_collection_type(self):
        bf = {"retention_3s": 60, "completion_rate": 30,
              "likes": 100, "shares": 50, "saves": 300, "engagement_rate": 2.0}
        diag = diagnose_video(bf, performance_patterns={
            "proven_openings": [], "proven_ctas": [], "proven_formulas": [], "risk_patterns": [],
        })
        assert diag["post_type"] == "收藏型"
        assert "saves" in diag["post_type_detail"]

    def test_shares_dominant_is_share_type(self):
        bf = {"retention_3s": 60, "completion_rate": 30,
              "likes": 50, "shares": 400, "saves": 30, "engagement_rate": 2.0}
        diag = diagnose_video(bf, performance_patterns={
            "proven_openings": [], "proven_ctas": [], "proven_formulas": [], "risk_patterns": [],
        })
        assert diag["post_type"] == "分享型"

    def test_likes_dominant_is_like_type(self):
        bf = {"retention_3s": 60, "completion_rate": 30,
              "likes": 500, "shares": 30, "saves": 20, "engagement_rate": 2.0}
        diag = diagnose_video(bf, performance_patterns={
            "proven_openings": [], "proven_ctas": [], "proven_formulas": [], "risk_patterns": [],
        })
        assert diag["post_type"] == "按讚型"

    def test_balanced_type(self):
        bf = {"retention_3s": 60, "completion_rate": 30,
              "likes": 100, "shares": 95, "saves": 98, "engagement_rate": 2.0}
        diag = diagnose_video(bf, performance_patterns={
            "proven_openings": [], "proven_ctas": [], "proven_formulas": [], "risk_patterns": [],
        })
        assert diag["post_type"] == "均衡型"

    def test_dud_low_engagement(self):
        bf = {"retention_3s": 30, "completion_rate": 10,
              "likes": 5, "shares": 1, "saves": 0, "engagement_rate": 0.3}
        diag = diagnose_video(bf, performance_patterns={
            "proven_openings": [], "proven_ctas": [], "proven_formulas": [], "risk_patterns": [],
        })
        assert diag["post_type"] == "啞彈"

    def test_dud_zero_interactions(self):
        bf = {"retention_3s": 30, "completion_rate": 10,
              "likes": 0, "shares": 0, "saves": 0, "engagement_rate": 0.1}
        diag = diagnose_video(bf, performance_patterns={
            "proven_openings": [], "proven_ctas": [], "proven_formulas": [], "risk_patterns": [],
        })
        assert diag["post_type"] == "啞彈"

    def test_missing_interaction_fields(self):
        bf = {"retention_3s": 60, "completion_rate": 30}
        diag = diagnose_video(bf, performance_patterns={
            "proven_openings": [], "proven_ctas": [], "proven_formulas": [], "risk_patterns": [],
        })
        assert diag["post_type"] is None
        assert "likes" in diag["missing_fields"]
        assert "shares" in diag["missing_fields"]
        assert "saves" in diag["missing_fields"]

    def test_hook_weakness_detected(self):
        bf = {"retention_3s": 45, "completion_rate": 30,
              "likes": 100, "shares": 50, "saves": 30, "engagement_rate": 2.0}
        diag = diagnose_video(bf, performance_patterns={
            "proven_openings": [], "proven_ctas": [], "proven_formulas": [], "risk_patterns": [],
        })
        assert any("Hook" in w for w in diag["weaknesses"])

    def test_completion_weakness_detected(self):
        bf = {"retention_3s": 60, "completion_rate": 18,
              "likes": 100, "shares": 50, "saves": 30, "engagement_rate": 2.0}
        diag = diagnose_video(bf, performance_patterns={
            "proven_openings": [], "proven_ctas": [], "proven_formulas": [], "risk_patterns": [],
        })
        assert any("完播" in w for w in diag["weaknesses"])

    def test_engagement_weakness_detected(self):
        bf = {"retention_3s": 60, "completion_rate": 30,
              "likes": 100, "shares": 50, "saves": 30, "engagement_rate": 1.0}
        diag = diagnose_video(bf, performance_patterns={
            "proven_openings": [], "proven_ctas": [], "proven_formulas": [], "risk_patterns": [],
        })
        assert any("互動" in w for w in diag["weaknesses"])

    def test_strengths_detected(self):
        bf = {"retention_3s": 75, "completion_rate": 45,
              "likes": 100, "shares": 50, "saves": 30, "engagement_rate": 4.0}
        diag = diagnose_video(bf, performance_patterns={
            "proven_openings": [], "proven_ctas": [], "proven_formulas": [], "risk_patterns": [],
        })
        assert any("Hook" in s for s in diag["strengths"])
        assert any("完播" in s for s in diag["strengths"])
        assert any("互動" in s for s in diag["strengths"])
        assert len(diag["weaknesses"]) == 0

    def test_prescription_from_proven_openings(self):
        bf = {"retention_3s": 40, "completion_rate": 30,
              "likes": 100, "shares": 50, "saves": 30, "engagement_rate": 2.0}
        pp = {
            "proven_openings": [
                {"code": "D3", "name": "數字衝擊", "vid_evidence": ["VID-001", "VID-005"]},
                {"code": "B2", "name": "好奇缺口", "vid_evidence": ["VID-003"]},
            ],
            "proven_ctas": [], "proven_formulas": [], "risk_patterns": [],
        }
        diag = diagnose_video(bf, performance_patterns=pp)
        assert any("D3" in p for p in diag["prescriptions"])

    def test_prescription_from_proven_ctas(self):
        bf = {"retention_3s": 60, "completion_rate": 30,
              "likes": 100, "shares": 50, "saves": 30, "engagement_rate": 1.0}
        pp = {
            "proven_openings": [],
            "proven_ctas": [
                {"code": "C3", "name": "開放提問", "vid_evidence": ["VID-005", "VID-021", "VID-031"]},
            ],
            "proven_formulas": [], "risk_patterns": [],
        }
        diag = diagnose_video(bf, performance_patterns=pp)
        assert any("C3" in p for p in diag["prescriptions"])

    def test_prescription_from_proven_formulas(self):
        bf = {"retention_3s": 60, "completion_rate": 20,
              "likes": 100, "shares": 50, "saves": 30, "engagement_rate": 2.0}
        pp = {
            "proven_openings": [], "proven_ctas": [],
            "proven_formulas": [
                {"formula": "痛點+揭秘=留存", "vid_evidence": ["VID-021"]},
            ],
            "risk_patterns": [],
        }
        diag = diagnose_video(bf, performance_patterns=pp)
        assert any("痛點" in p for p in diag["prescriptions"])

    def test_prescription_fallback_no_patterns(self):
        bf = {"retention_3s": 40, "completion_rate": 20,
              "likes": 100, "shares": 50, "saves": 30, "engagement_rate": 1.0}
        diag = diagnose_video(bf, performance_patterns={
            "proven_openings": [], "proven_ctas": [], "proven_formulas": [], "risk_patterns": [],
        })
        assert any("樣本不足" in p for p in diag["prescriptions"])

    def test_backfill_writes_diagnosis(self, patch_paths):
        """backfill_video should automatically write diagnosis to JSON."""
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")

        ok, msg, result = backfill_video(
            data, "VID-001",
            views=10000, retention_3s=60, completion_rate=30,
            likes=200, shares=50, saves=100,
        )
        assert ok is True
        assert "diagnosis" in result
        assert result["diagnosis"]["post_type"] == "按讚型"  # likes=200 dominant
        # Check it was persisted
        bf = data["videos"][0]["backfill"]
        assert "diagnosis" in bf
        assert bf["diagnosis"]["post_type"] == "按讚型"

    def test_backfill_diagnosis_without_interaction(self, patch_paths):
        """backfill without likes/shares/saves should still diagnose, with missing_fields."""
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")

        ok, msg, result = backfill_video(
            data, "VID-001",
            views=10000, retention_3s=45, completion_rate=30,
        )
        assert ok is True
        diag = result["diagnosis"]
        assert diag["post_type"] is None
        assert "likes" in diag["missing_fields"]
        assert any("Hook" in w for w in diag["weaknesses"])

    def test_no_weakness_no_prescription(self):
        """When everything is strong, prescriptions should be empty."""
        bf = {"retention_3s": 80, "completion_rate": 50,
              "likes": 300, "shares": 200, "saves": 100, "engagement_rate": 5.0}
        diag = diagnose_video(bf, performance_patterns={
            "proven_openings": [], "proven_ctas": [], "proven_formulas": [], "risk_patterns": [],
        })
        assert len(diag["prescriptions"]) == 0
        assert len(diag["weaknesses"]) == 0


class TestPatternDecay:
    """Test the automatic decay of proven patterns when low-performance videos use them."""

    def test_single_low_no_degrade(self):
        """One low-performance use should add low_evidence but NOT degrade."""
        pdata = {
            "proven_openings": [
                {"code": "D3", "name": "數字衝擊", "vid_evidence": ["VID-001", "VID-002"]},
            ],
            "proven_ctas": [],
        }
        changed = _check_pattern_decay(pdata, opening="D3", vid="VID-010")
        assert changed is True
        assert "VID-010" in pdata["proven_openings"][0]["low_evidence"]
        assert pdata["proven_openings"][0].get("degraded") is not True

    def test_two_low_triggers_degrade(self):
        """Two low-performance uses should trigger degraded=True."""
        pdata = {
            "proven_openings": [
                {"code": "D3", "name": "數字衝擊", "vid_evidence": ["VID-001", "VID-002"],
                 "low_evidence": ["VID-010"]},
            ],
            "proven_ctas": [],
        }
        changed = _check_pattern_decay(pdata, opening="D3", vid="VID-011")
        assert changed is True
        item = pdata["proven_openings"][0]
        assert item["degraded"] is True
        assert "VID-011" in item["low_evidence"]
        assert "degraded_date" in item
        assert "degraded_reason" in item

    def test_no_duplicate_low_evidence(self):
        """Same VID should not be added twice to low_evidence."""
        pdata = {
            "proven_openings": [
                {"code": "D3", "vid_evidence": ["VID-001"],
                 "low_evidence": ["VID-010"]},
            ],
            "proven_ctas": [],
        }
        changed = _check_pattern_decay(pdata, opening="D3", vid="VID-010")
        assert changed is False  # no new data
        assert pdata["proven_openings"][0]["low_evidence"].count("VID-010") == 1

    def test_decay_cta(self):
        """CTA patterns should also decay."""
        pdata = {
            "proven_openings": [],
            "proven_ctas": [
                {"code": "C3", "vid_evidence": ["VID-001"],
                 "low_evidence": ["VID-010"]},
            ],
        }
        _check_pattern_decay(pdata, cta="C3", vid="VID-011")
        assert pdata["proven_ctas"][0]["degraded"] is True

    def test_no_match_no_change(self):
        """Pattern not in proven list should not cause changes."""
        pdata = {
            "proven_openings": [
                {"code": "D3", "vid_evidence": ["VID-001"]},
            ],
            "proven_ctas": [],
        }
        changed = _check_pattern_decay(pdata, opening="B2", vid="VID-010")
        assert changed is False

    def test_extract_low_with_decay(self, patch_paths):
        """extract_learning for low-perf video should trigger decay check on proven patterns."""
        data = load_tracking()
        add_video(data, "test1", "tag", title="t1", source="quick-shot",
                  initial_status="已上線")
        add_video(data, "test2", "tag", title="t2", source="quick-shot",
                  initial_status="已上線")
        add_video(data, "test3", "tag", title="t3", source="quick-shot",
                  initial_status="已上線")

        # Setup: VID-001 is high, establishes D3 as proven
        backfill_video(data, "VID-001", views=500000, retention_3s=80, completion_rate=50)
        extract_learning(data, "VID-001", opening="D3", cta="C3", formula="test")

        # VID-002 is low, uses D3 → first low_evidence
        backfill_video(data, "VID-002", views=100, retention_3s=20, completion_rate=10)
        extract_learning(data, "VID-002", opening="D3", failure_mode="開場太慢")

        pp = load_performance_patterns()
        d3 = [o for o in pp["proven_openings"] if o["code"] == "D3"][0]
        assert "VID-002" in d3.get("low_evidence", [])
        assert d3.get("degraded") is not True  # only 1 low

        # VID-003 is low, uses D3 → second low_evidence → degraded
        backfill_video(data, "VID-003", views=100, retention_3s=20, completion_rate=10)
        extract_learning(data, "VID-003", opening="D3", failure_mode="開場太慢")

        pp = load_performance_patterns()
        d3 = [o for o in pp["proven_openings"] if o["code"] == "D3"][0]
        assert d3["degraded"] is True
        assert len(d3["low_evidence"]) == 2

    def test_performance_report_shows_degraded(self, patch_paths):
        """performance_report should include degraded_patterns."""
        data = load_tracking()
        pp = load_performance_patterns()
        pp["proven_openings"] = [
            {"code": "D3", "vid_evidence": ["VID-001"],
             "low_evidence": ["VID-010", "VID-011"],
             "degraded": True, "degraded_date": "2026-03-20",
             "degraded_reason": "test"},
        ]
        save_performance_patterns(pp)

        r = performance_report(data)
        assert len(r["degraded_patterns"]) == 1
        assert r["degraded_patterns"][0]["code"] == "D3"


class TestBestMatch:
    """Test _best_match priority logic."""

    def test_single_match(self):
        assert _best_match(_OPENING_PATTERNS, "觀看50萬次") == "D3"

    def test_d3_over_d1_when_both_match(self):
        """D3 (priority 1) should beat D1 (priority 2) when both match."""
        text = "結果50萬人卻不知道"
        assert _best_match(_OPENING_PATTERNS, text) == "D3"

    def test_d1_when_only_d1(self):
        text = "結果他卻放棄了"
        assert _best_match(_OPENING_PATTERNS, text) == "D1"

    def test_b1_crisis_keywords(self):
        text = "這家店倒閉了"
        assert _best_match(_OPENING_PATTERNS, text) == "B1"

    def test_no_match_returns_none(self):
        assert _best_match(_OPENING_PATTERNS, "今天天氣真好") is None

    def test_cta_c1_over_c3_when_both(self):
        """C1 (priority 1) should beat C3 (priority 3)."""
        text = "你覺得呢？留言告訴我"
        assert _best_match(_CTA_PATTERNS, text) == "C1"

    def test_cta_c2_when_only_c2(self):
        text = "按讚收藏起來"
        assert _best_match(_CTA_PATTERNS, text) == "C2"

    def test_cta_c4_follow(self):
        text = "追蹤看下一集"
        assert _best_match(_CTA_PATTERNS, text) == "C4"


class TestAutoExtractFromScript:
    """Test auto_extract_from_script with transcript input."""

    def test_basic_extraction(self):
        transcript = "50萬人都不知道的真相\n這件事很嚴重\n你一定要知道\n所以真相是什麼\n按讚收藏起來"
        result = auto_extract_from_script(None, transcript=transcript)
        assert result is not None
        assert result["opening_guess"] == "D3"
        assert result["cta_guess"] == "C2"

    def test_no_transcript_returns_none(self):
        result = auto_extract_from_script(None, transcript=None)
        assert result is None

    def test_empty_transcript_returns_none(self):
        result = auto_extract_from_script(None, transcript="")
        assert result is None

    def test_hook_extracted(self):
        transcript = "第一行\n第二行\n第三行"
        result = auto_extract_from_script(None, transcript=transcript)
        assert result is not None
        assert "第一行" in result["hook"]

    def test_turning_points_detected(self):
        transcript = "開頭\n但是這件事不對\n中間\n沒想到結果完全相反\n結尾留言告訴我"
        result = auto_extract_from_script(None, transcript=transcript)
        assert len(result["turning_points"]) >= 1

    def test_priority_d3_over_b2(self):
        """Script with both number and question — D3 should win."""
        transcript = "你知道50萬人都犯了這個錯嗎\n" * 3 + "留言告訴我"
        result = auto_extract_from_script(None, transcript=transcript)
        assert result["opening_guess"] == "D3"


class TestPatternKeysUnified:
    """Test that PATTERN_KEYS drives all pattern operations uniformly."""

    def test_pattern_keys_covers_all_types(self):
        """PATTERN_KEYS must include all three proven pattern types."""
        assert "proven_openings" in PATTERN_KEYS
        assert "proven_ctas" in PATTERN_KEYS
        assert "proven_formulas" in PATTERN_KEYS

    def test_win_rate_note_computed(self):
        """win_rate_note should be computed from vid_evidence length."""
        item = {"vid_evidence": ["VID-001", "VID-002", "VID-003"]}
        assert win_rate_note(item) == "3 次高表現使用"

    def test_win_rate_note_empty(self):
        """Empty vid_evidence should show 0."""
        assert win_rate_note({"vid_evidence": []}) == "0 次高表現使用"
        assert win_rate_note({}) == "0 次高表現使用"

    def test_decay_formula_via_unified_path(self):
        """Formula decay should work through the same unified PATTERN_KEYS path."""
        pdata = {
            "proven_openings": [],
            "proven_ctas": [],
            "proven_formulas": [
                {"formula": "test公式", "vid_evidence": ["VID-001"],
                 "low_evidence": ["VID-010"]},
            ],
        }
        changed = _check_pattern_decay(pdata, formula="test公式", vid="VID-011")
        assert changed is True
        item = pdata["proven_formulas"][0]
        assert item["degraded"] is True
        assert "VID-011" in item["low_evidence"]

    def test_add_vid_evidence_formula(self, patch_paths):
        """_add_vid_evidence should work for proven_formulas via PATTERN_KEYS."""
        from lib.backfill import _add_vid_evidence
        pdata = {"proven_formulas": []}
        _add_vid_evidence(pdata, "proven_formulas", "數字衝擊", "VID-001")
        assert len(pdata["proven_formulas"]) == 1
        assert pdata["proven_formulas"][0]["formula"] == "數字衝擊"
        assert "VID-001" in pdata["proven_formulas"][0]["vid_evidence"]
        # Should NOT have win_rate_note stored
        assert "win_rate_note" not in pdata["proven_formulas"][0]

    def test_add_vid_evidence_no_win_rate_note(self, patch_paths):
        """After adding evidence, win_rate_note should NOT be stored in the item."""
        from lib.backfill import _add_vid_evidence
        pdata = {"proven_openings": []}
        _add_vid_evidence(pdata, "proven_openings", "D3", "VID-001")
        _add_vid_evidence(pdata, "proven_openings", "D3", "VID-002")
        item = pdata["proven_openings"][0]
        assert len(item["vid_evidence"]) == 2
        assert "win_rate_note" not in item


class TestComputePatternStats:
    """Test compute_pattern_stats enrichment."""

    def _make_pipeline_items(self):
        """Helper: create pipeline items with varying performance and hook types."""
        return [
            {"vid": "VID-001", "hook_type": "D3", "backfill": {"views": 100, "performance": "high", "backfilled_date": "2026-01-01"},
             "learning": {"opening": "D3", "cta": "C3"}},
            {"vid": "VID-002", "hook_type": "D3", "backfill": {"views": 50, "performance": "normal", "backfilled_date": "2026-01-02"},
             "learning": {"opening": "D3"}},
            {"vid": "VID-003", "hook_type": "B2", "backfill": {"views": 200, "performance": "high", "backfilled_date": "2026-01-03"},
             "learning": {"opening": "B2", "cta": "C3"}},
            {"vid": "VID-004", "hook_type": "B2", "backfill": {"views": 30, "performance": "low", "backfilled_date": "2026-01-04"},
             "learning": {"opening": "B2"}},
            {"vid": "VID-005", "hook_type": "B2", "backfill": {"views": 80, "performance": "normal", "backfilled_date": "2026-01-05"}},
            # idea without vid
            {"idea_id": "IDEA-001", "vid": None},
        ]

    def test_opening_stats(self):
        """Compute stats for proven_openings using hook_type from pipeline."""
        pdata = {
            "proven_openings": [
                {"code": "D3", "name": "數字衝擊", "vid_evidence": ["VID-001"]},
                {"code": "B2", "name": "好奇缺口", "vid_evidence": ["VID-003"]},
            ],
            "proven_ctas": [],
            "proven_formulas": [],
        }
        items = self._make_pipeline_items()
        updated = compute_pattern_stats(pdata, items)
        assert updated == 2

        d3 = pdata["proven_openings"][0]
        assert d3["sample_size"] == 1
        assert d3["total_uses"] == 2  # VID-001 + VID-002 both have hook_type D3
        assert d3["win_rate"] == 0.5  # 1/2
        assert d3["confidence"] == "low"  # total_uses=2 < 3

        b2 = pdata["proven_openings"][1]
        assert b2["sample_size"] == 1
        assert b2["total_uses"] == 3  # VID-003, VID-004, VID-005
        assert b2["win_rate"] == round(1/3, 2)
        assert b2["confidence"] == "medium"  # total_uses=3 >= 3

    def test_cta_stats(self):
        """Compute stats for proven_ctas using learning.cta from pipeline."""
        pdata = {
            "proven_openings": [],
            "proven_ctas": [
                {"code": "C3", "name": "開放提問", "vid_evidence": ["VID-001", "VID-003"]},
            ],
            "proven_formulas": [],
        }
        items = self._make_pipeline_items()
        compute_pattern_stats(pdata, items)

        c3 = pdata["proven_ctas"][0]
        assert c3["sample_size"] == 2
        assert c3["total_uses"] == 2  # Only VID-001 and VID-003 have learning.cta=C3
        assert c3["win_rate"] == 1.0
        assert c3["confidence"] == "low"

    def test_formula_stats_uses_evidence_count(self):
        """Formulas can't be matched automatically, so total_uses = sample_size."""
        pdata = {
            "proven_openings": [],
            "proven_ctas": [],
            "proven_formulas": [
                {"formula": "好奇+數字", "vid_evidence": ["VID-001", "VID-003"]},
            ],
        }
        compute_pattern_stats(pdata, self._make_pipeline_items())

        f = pdata["proven_formulas"][0]
        assert f["sample_size"] == 2
        assert f["total_uses"] == 2
        assert f["win_rate"] == 1.0

    def test_empty_patterns(self):
        """Empty patterns should not crash."""
        pdata = {"proven_openings": [], "proven_ctas": [], "proven_formulas": []}
        assert compute_pattern_stats(pdata, []) == 0

    def test_empty_pipeline(self):
        """Patterns with no matching pipeline items use evidence count as floor."""
        pdata = {
            "proven_openings": [
                {"code": "D3", "name": "test", "vid_evidence": ["VID-001"]},
            ],
            "proven_ctas": [],
            "proven_formulas": [],
        }
        compute_pattern_stats(pdata, [])
        d3 = pdata["proven_openings"][0]
        assert d3["total_uses"] == 1  # floor = sample_size
        assert d3["win_rate"] == 1.0
        assert d3["confidence"] == "low"

    def test_confidence_high(self):
        """Confidence should be 'high' when total_uses >= 8."""
        pdata = {
            "proven_openings": [
                {"code": "D3", "name": "test", "vid_evidence": ["VID-001"]},
            ],
            "proven_ctas": [],
            "proven_formulas": [],
        }
        # Create 8 pipeline items with hook_type D3
        items = [
            {"vid": f"VID-{i:03d}", "hook_type": "D3",
             "backfill": {"views": 100, "performance": "normal", "backfilled_date": "2026-01-01"}}
            for i in range(1, 9)
        ]
        compute_pattern_stats(pdata, items)
        assert pdata["proven_openings"][0]["confidence"] == "high"
        assert pdata["proven_openings"][0]["total_uses"] == 8

    def test_win_rate_note_with_enrichment(self):
        """win_rate_note should use enriched fields when available."""
        item = {"vid_evidence": ["VID-001", "VID-002"], "win_rate": 0.667, "confidence": "medium"}
        note = win_rate_note(item)
        assert "67%" in note
        assert "medium" in note

    def test_win_rate_note_without_enrichment(self):
        """win_rate_note should fall back gracefully without enrichment."""
        item = {"vid_evidence": ["VID-001"]}
        assert win_rate_note(item) == "1 次高表現使用"

    def test_add_vid_evidence_sets_last_evidence_date(self):
        """_add_vid_evidence should record last_evidence_date."""
        from lib.backfill import _add_vid_evidence
        pdata = {"proven_openings": []}
        _add_vid_evidence(pdata, "proven_openings", "D3", "VID-001")
        item = pdata["proven_openings"][0]
        assert "last_evidence_date" in item
        assert len(item["last_evidence_date"]) == 10  # YYYY-MM-DD

    def test_add_vid_evidence_updates_last_evidence_date(self):
        """Adding more evidence should update last_evidence_date."""
        from lib.backfill import _add_vid_evidence
        pdata = {"proven_openings": [
            {"code": "D3", "name": "D3", "vid_evidence": ["VID-001"], "last_evidence_date": "2026-01-01"},
        ]}
        _add_vid_evidence(pdata, "proven_openings", "D3", "VID-002")
        item = pdata["proven_openings"][0]
        assert item["last_evidence_date"] != "2026-01-01"  # should be today


class TestCrossDimensionalStats:
    """Test cross-dimensional analysis."""

    def _make_items(self):
        return [
            {"vid": "VID-001", "hook_type": "D3", "version": "B2", "tags": "成本型",
             "skill_used": "flow-operator",
             "backfill": {"views": 500, "retention_3s": 70, "completion_rate": 50,
                          "performance": "high", "backfilled_date": "2026-01-01"}},
            {"vid": "VID-002", "hook_type": "D3", "version": "B2", "tags": "成本型",
             "skill_used": "flow-operator",
             "backfill": {"views": 100, "retention_3s": 60, "completion_rate": 30,
                          "performance": "normal", "backfilled_date": "2026-01-02"}},
            {"vid": "VID-003", "hook_type": "B2", "version": "A1", "tags": "心態型",
             "skill_used": "interview-navigator",
             "backfill": {"views": 300, "retention_3s": 80, "completion_rate": 60,
                          "performance": "high", "backfilled_date": "2026-01-03"}},
            {"vid": "VID-004", "hook_type": "B2", "tags": "成本型",
             "skill_used": "flow-operator",
             "backfill": {"views": 50, "retention_3s": 30, "completion_rate": 10,
                          "performance": "low", "backfilled_date": "2026-01-04"}},
        ]

    def test_by_hook_type(self):
        stats = cross_dimensional_stats(self._make_items())
        d3 = stats["by_hook_type"]["D3"]
        assert d3["count"] == 2
        assert d3["high"] == 1
        assert d3["avg_retention"] == 65.0  # (70+60)/2

    def test_by_version(self):
        stats = cross_dimensional_stats(self._make_items())
        assert "B2" in stats["by_version"]
        assert stats["by_version"]["B2"]["count"] == 2
        assert "A1" in stats["by_version"]

    def test_by_topic_type(self):
        stats = cross_dimensional_stats(self._make_items())
        cost = stats["by_topic_type"]["成本型"]
        assert cost["count"] == 3
        assert cost["high"] == 1

    def test_by_skill(self):
        stats = cross_dimensional_stats(self._make_items())
        assert "flow-operator" in stats["by_skill"]
        assert stats["by_skill"]["flow-operator"]["count"] == 3

    def test_combinations(self):
        stats = cross_dimensional_stats(self._make_items())
        # D3+B2 has 2 items, should appear in combinations
        combos = stats["combinations"]
        d3b2 = [c for c in combos if c["hook_type"] == "D3" and c["version"] == "B2"]
        assert len(d3b2) == 1
        assert d3b2[0]["count"] == 2
        assert d3b2[0]["win_rate"] == 0.5

    def test_empty_items(self):
        stats = cross_dimensional_stats([])
        assert stats["by_hook_type"] == {}
        assert stats["combinations"] == []

    def test_skips_no_backfill(self):
        items = [{"vid": "VID-001", "hook_type": "D3", "backfill": None}]
        stats = cross_dimensional_stats(items)
        assert stats["by_hook_type"] == {}


class TestSkillEffectiveness:
    """Test per-skill effectiveness computation."""

    def test_basic(self):
        items = [
            {"vid": "VID-001", "skill_used": "flow-operator", "version": "B2",
             "backfill": {"views": 500, "retention_3s": 70, "completion_rate": 50,
                          "performance": "high", "backfilled_date": "2026-01-01"}},
            {"vid": "VID-002", "skill_used": "flow-operator", "version": "A1",
             "backfill": {"views": 100, "retention_3s": 50, "completion_rate": 25,
                          "performance": "normal", "backfilled_date": "2026-01-02"}},
            {"vid": "VID-003", "skill_used": "interview-navigator", "version": "B1",
             "backfill": {"views": 300, "retention_3s": 80, "completion_rate": 60,
                          "performance": "high", "backfilled_date": "2026-01-03"}},
        ]
        results = skill_effectiveness(items)
        assert len(results) == 2

        # Sorted by win_rate descending
        assert results[0]["skill"] == "interview-navigator"
        assert results[0]["win_rate"] == 1.0
        assert results[0]["total"] == 1

        fo = results[1]
        assert fo["skill"] == "flow-operator"
        assert fo["total"] == 2
        assert fo["win_rate"] == 0.5
        assert fo["avg_retention"] == 60.0
        assert fo["versions_used"] == {"B2": 1, "A1": 1}

    def test_empty(self):
        assert skill_effectiveness([]) == []

    def test_verifier_accuracy(self):
        items = [
            {"vid": "VID-001", "skill_used": "flow-operator",
             "verifier_accuracy": {"predicted": "high", "actual": "high", "match": True},
             "backfill": {"views": 500, "retention_3s": 70, "completion_rate": 50,
                          "performance": "high", "backfilled_date": "2026-01-01"}},
            {"vid": "VID-002", "skill_used": "flow-operator",
             "verifier_accuracy": {"predicted": "high", "actual": "low", "match": False},
             "backfill": {"views": 50, "retention_3s": 30, "completion_rate": 10,
                          "performance": "low", "backfilled_date": "2026-01-02"}},
        ]
        results = skill_effectiveness(items)
        assert results[0]["avg_verifier_accuracy"] == 0.5

    def test_skips_no_skill(self):
        items = [
            {"vid": "VID-001", "skill_used": "",
             "backfill": {"views": 100, "retention_3s": 50, "completion_rate": 25,
                          "performance": "normal", "backfilled_date": "2026-01-01"}},
        ]
        assert skill_effectiveness(items) == []
