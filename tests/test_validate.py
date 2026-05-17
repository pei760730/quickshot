"""Tests for lib/validate.py — validation + migration."""

from conftest import make_video

from lib.validate import validate, validate_all, migrate
from lib.pipeline import load_tracking, add_video, save_tracking
from lib.backfill import backfill_video


class TestValidate:
    def test_valid_data(self):
        data = {"videos": [make_video()]}
        errors = validate(data)
        assert len(errors) == 0

    def test_duplicate_vid(self):
        data = {"videos": [make_video("VID-001"), make_video("VID-001")]}
        errors = validate(data)
        assert any("重複" in e for e in errors)

    def test_invalid_vid_format(self):
        v = make_video()
        v["vid"] = "INVALID"
        data = {"videos": [v]}
        errors = validate(data)
        assert any("格式" in e for e in errors)

    def test_invalid_status(self):
        v = make_video()
        v["status"] = "不存在"
        data = {"videos": [v]}
        errors = validate(data)
        assert any("非法狀態" in e for e in errors)

    def test_missing_topic(self):
        v = make_video()
        v["topic"] = ""
        data = {"videos": [v]}
        errors = validate(data)
        assert any("topic" in e for e in errors)

    def test_missing_created_date(self):
        v = make_video()
        v["created_date"] = ""
        data = {"videos": [v]}
        errors = validate(data)
        assert any("created_date" in e for e in errors)

    def test_invalid_publish_date(self):
        v = make_video()
        v["publish_date"] = "not-a-date"
        data = {"videos": [v]}
        errors = validate(data)
        assert any("publish_date" in e for e in errors)

    def test_shangxian_no_publish_date(self):
        v = make_video(status="已上線")
        v["publish_date"] = ""
        v["status_history"] = [{"status": "已上線", "date": "2026-03-01"}]
        data = {"videos": [v]}
        errors = validate(data)
        assert any("publish_date" in e for e in errors)

    def test_status_history_mismatch(self):
        v = make_video(status="待拍")
        v["status_history"] = [{"status": "剪輯中", "date": "2026-03-01"}]
        data = {"videos": [v]}
        errors = validate(data)
        assert any("status_history" in e for e in errors)

    def test_deprecated_field(self):
        v = make_video()
        v["hard_gates_result"] = "some value"
        data = {"videos": [v]}
        errors = validate(data)
        assert any("廢棄" in e for e in errors)

    def test_missing_source_warning(self):
        v = make_video()
        del v["source"]
        data = {"videos": [v]}
        warnings = []
        validate(data, warnings=warnings)
        assert any("source" in w for w in warnings)

    def test_pipeline_missing_required_fields(self):
        """skill_used is auto-filled by migrate(), not checked by validate().
        Verify validate doesn't raise errors for an otherwise-valid video."""
        v = make_video(source="pipeline")
        v["skill_used"] = ""
        data = {"videos": [v]}
        errors = validate(data)
        # skill_used is not in REQUIRED_FIELDS_BY_SOURCE; migrate() handles it
        assert not any("skill_used" in e for e in errors)


class TestValidateAll:
    def test_clean_state(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot")

        result = validate_all(data)
        assert len(result["errors"]) == 0

    def test_performance_recalc_mismatch(self, patch_paths):
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot",
                  initial_status="已上線")
        backfill_video(data, "VID-001", views=500000, retention_3s=80, completion_rate=50)

        # Manually corrupt performance level
        data["videos"][0]["backfill"]["performance"] = "low"
        save_tracking(data, skip_validate=True)

        result = validate_all(data)
        assert any("重算" in e for e in result["errors"])

    def test_performance_patterns_bad_vid_ref(self, patch_paths):
        """performance-patterns 引用不存在的 VID → error。"""
        import json
        pp_path = patch_paths / "data" / "kai" / "performance-patterns.json"
        pp = {
            "_meta": {"last_updated": "2026-03-17"},
            "proven_openings": [{"code": "D3", "vid_evidence": ["VID-888"]}],
            "proven_ctas": [], "proven_formulas": [], "risk_patterns": [],
        }
        pp_path.write_text(json.dumps(pp, ensure_ascii=False), encoding="utf-8")
        data = load_tracking()
        result = validate_all(data)
        assert any("VID-888" in e and "不存在" in e for e in result["errors"])

    def test_script_path_warning(self, patch_paths):
        """script_path 指向不存在的檔案 → warning。"""
        data = load_tracking()
        add_video(data, "test", "tag", title="t", source="quick-shot")
        data["videos"][0]["script_path"] = "03-production-line/02-ready-to-shoot/nonexistent.md"
        save_tracking(data, skip_validate=True)

        result = validate_all(data)
        assert any("不存在" in w for w in result["warnings"])

    def test_normal_learning_extracted_without_learning_is_not_warning(self, monkeypatch):
        """normal performance only marks extraction complete; no learning field is expected."""
        monkeypatch.setattr("lib.validate.load_performance_patterns", lambda: {})
        v = make_video("VID-001")
        v["backfill"] = {"performance": "normal", "learning_extracted": True}

        result = validate_all({"videos": [v]})

        assert not any("learning_extracted=true" in w for w in result["warnings"])

    def test_non_normal_learning_extracted_without_learning_still_warns(self, monkeypatch):
        """high/low performance extraction should still produce a learning object."""
        monkeypatch.setattr("lib.validate.load_performance_patterns", lambda: {})
        v = make_video("VID-001")
        v["backfill"] = {"performance": "high", "learning_extracted": True}

        result = validate_all({"videos": [v]})

        assert any("learning_extracted=true" in w for w in result["warnings"])


class TestMigrate:
    def test_adds_missing_source(self):
        v = make_video()
        del v["source"]
        data = {"videos": [v]}
        result = migrate(data)
        assert any(c["field"] == "source" for c in result["migrated"])
        assert data["videos"][0]["source"] == "pipeline"

    def test_adds_missing_title(self):
        v = make_video()
        v["title"] = ""
        data = {"videos": [v]}
        result = migrate(data)
        assert any(c["field"] == "title" for c in result["migrated"])
        assert data["videos"][0]["title"] == "測試主題"

    def test_idempotent(self):
        v = make_video()
        data = {"videos": [v]}
        migrate(data)
        result2 = migrate(data)
        assert len(result2["migrated"]) == 0

    def test_adds_script_status(self):
        v = make_video()
        del v["script_status"]
        data = {"videos": [v]}
        result = migrate(data)
        assert any(c["field"] == "script_status" for c in result["migrated"])


class TestStatusHistoryChronology:
    """status_history 日期順序驗證。"""

    def test_valid_chronology(self):
        v = make_video(status="已上線")
        v["status_history"] = [
            {"status": "待拍", "date": "2026-03-01"},
            {"status": "剪輯中", "date": "2026-03-05"},
            {"status": "已上線", "date": "2026-03-10"},
        ]
        errors = validate({"videos": [v]})
        assert not any("日期倒序" in e for e in errors)

    def test_detects_backward_dates(self):
        v = make_video(status="已上線")
        v["status_history"] = [
            {"status": "待拍", "date": "2026-03-10"},
            {"status": "剪輯中", "date": "2026-03-05"},  # Backward!
            {"status": "已上線", "date": "2026-03-15"},
        ]
        errors = validate({"videos": [v]})
        assert any("日期倒序" in e for e in errors)

    def test_same_day_allowed(self):
        v = make_video(status="剪輯中")
        v["status_history"] = [
            {"status": "待拍", "date": "2026-03-10"},
            {"status": "剪輯中", "date": "2026-03-10"},  # Same day = OK
        ]
        errors = validate({"videos": [v]})
        assert not any("日期倒序" in e for e in errors)

    def test_invalid_date_format_in_history(self):
        v = make_video(status="待拍")
        v["status_history"] = [
            {"status": "待拍", "date": "not-a-date"},
        ]
        errors = validate({"videos": [v]})
        assert any("日期格式無效" in e for e in errors)


class TestBackfillRangeValidation:
    """backfill 數值範圍驗證。"""

    def test_valid_backfill_passes(self):
        v = make_video(status="已上線", backfill={
            "views": 50000, "retention_3s": 65, "completion_rate": 35,
            "engagement_rate": 5.2, "performance": "normal",
        })
        errors = validate({"videos": [v]})
        assert not any("超出" in e or "負數" in e for e in errors)

    def test_retention_over_100(self):
        v = make_video(status="已上線", backfill={
            "views": 1000, "retention_3s": 150, "completion_rate": 30,
            "performance": "normal",
        })
        errors = validate({"videos": [v]})
        assert any("retention_3s=150" in e and "超出" in e for e in errors)

    def test_negative_completion_rate(self):
        v = make_video(status="已上線", backfill={
            "views": 1000, "retention_3s": 50, "completion_rate": -10,
            "performance": "normal",
        })
        errors = validate({"videos": [v]})
        assert any("completion_rate=-10" in e and "超出" in e for e in errors)

    def test_negative_views(self):
        v = make_video(status="已上線", backfill={
            "views": -5000, "retention_3s": 50, "completion_rate": 30,
            "performance": "normal",
        })
        errors = validate({"videos": [v]})
        assert any("views=-5000" in e and "負數" in e for e in errors)

    def test_zero_values_ok(self):
        v = make_video(status="已上線", backfill={
            "views": 0, "retention_3s": 0, "completion_rate": 0,
            "performance": "low",
        })
        errors = validate({"videos": [v]})
        assert not any("超出" in e or "負數" in e for e in errors)

    def test_boundary_100_ok(self):
        v = make_video(status="已上線", backfill={
            "views": 1000, "retention_3s": 100, "completion_rate": 100,
            "engagement_rate": 100, "performance": "high",
        })
        errors = validate({"videos": [v]})
        assert not any("超出" in e for e in errors)

    def test_no_backfill_ok(self):
        v = make_video(status="待拍")
        errors = validate({"videos": [v]})
        assert not any("backfill" in e for e in errors)
