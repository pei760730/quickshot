"""Tests for record_verifier_scores + validate warning."""

from conftest import make_video

from lib.pipeline import (
    load_tracking, find_video,
    record_verifier_scores, validate_verifier_scores, add_video,
)
from lib.validate import validate


def _add_test_video(data, vid_num="001"):
    """Add a properly structured video through add_video."""
    return add_video(
        data, topic="測試主題", tag="測試",
        title="測試標題", source_inspiration="test",
        skill_used="flow-operator",
    )


class TestRecordVerifierScores:
    def test_record_scores_success(self, patch_paths):
        data = load_tracking()
        vid = _add_test_video(data)

        scores = {
            "conflict_score": 8,
            "retention_prediction": "A",
            "ai_residue_count": 0,
            "data_consistency": True,
            "format_complete": True,
            "pass_count": "5/5",
        }
        ok, msg = record_verifier_scores(data, vid, scores)
        assert ok is True
        assert "verifier_scores" in msg

        # Reload and verify persisted
        data2 = load_tracking()
        _, video = find_video(data2, vid)
        vs = video["verifier_scores"]
        assert vs["conflict_score"] == 8
        assert vs["retention_prediction"] == "A"
        assert vs["ai_residue_count"] == 0
        assert vs["data_consistency"] is True
        assert vs["format_complete"] is True
        assert vs["pass_count"] == "5/5"
        assert vs["date"] == "2026-03-17"

    def test_record_scores_vid_not_found(self, patch_paths):
        data = load_tracking()
        ok, msg = record_verifier_scores(data, "VID-999", {})
        assert ok is False
        assert "找不到" in msg

    def test_rejects_partial_scores(self, patch_paths):
        data = load_tracking()
        vid = _add_test_video(data)

        scores = {"conflict_score": 6, "pass_count": "3/5"}
        ok, msg = record_verifier_scores(data, vid, scores)
        assert ok is False
        assert "缺少必要欄位" in msg

    def test_rejects_invalid_conflict_score_range(self, patch_paths):
        data = load_tracking()
        vid = _add_test_video(data)
        scores = {
            "conflict_score": 11,
            "retention_prediction": "A",
            "ai_residue_count": 0,
            "data_consistency": True,
            "format_complete": True,
            "pass_count": "5/5",
        }
        ok, msg = record_verifier_scores(data, vid, scores)
        assert ok is False
        assert "0~10" in msg

    def test_rejects_invalid_pass_count_format(self, patch_paths):
        data = load_tracking()
        vid = _add_test_video(data)
        scores = {
            "conflict_score": 8,
            "retention_prediction": "A",
            "ai_residue_count": 0,
            "data_consistency": True,
            "format_complete": True,
            "pass_count": "5 / 5",
        }
        ok, msg = record_verifier_scores(data, vid, scores)
        assert ok is False
        assert "pass_count 格式" in msg

    def test_rejects_pass_count_numerator_out_of_range(self, patch_paths):
        data = load_tracking()
        vid = _add_test_video(data)
        scores = {
            "conflict_score": 8,
            "retention_prediction": "A",
            "ai_residue_count": 0,
            "data_consistency": True,
            "format_complete": True,
            "pass_count": "6/5",
        }
        ok, msg = record_verifier_scores(data, vid, scores)
        assert ok is False
        assert "0~5" in msg

    def test_rejects_bool_for_integer_fields(self, patch_paths):
        data = load_tracking()
        vid = _add_test_video(data)
        scores = {
            "conflict_score": True,
            "retention_prediction": "A",
            "ai_residue_count": 0,
            "data_consistency": True,
            "format_complete": True,
            "pass_count": "5/5",
        }
        ok, msg = record_verifier_scores(data, vid, scores)
        assert ok is False
        assert "conflict_score 必須為整數" in msg

    def test_validate_helper_returns_normalized_payload(self):
        ok, result = validate_verifier_scores({
            "conflict_score": 8,
            "retention_prediction": "  A  ",
            "ai_residue_count": 0,
            "data_consistency": True,
            "format_complete": True,
            "pass_count": " 5/5 ",
        })
        assert ok is True
        assert result["retention_prediction"] == "A"
        assert result["pass_count"] == "5/5"

    def test_validate_helper_rejects_unexpected_field(self):
        ok, msg = validate_verifier_scores({
            "conflict_score": 8,
            "retention_prediction": "A",
            "ai_residue_count": 0,
            "data_consistency": True,
            "format_complete": True,
            "pass_count": "5/5",
            "extra_field": "unexpected",
        })
        assert ok is False
        assert "不支援的欄位" in msg

    def test_validate_helper_rejects_non_dict(self):
        ok, msg = validate_verifier_scores(None)
        assert ok is False
        assert "必須為物件" in msg


class TestValidateVerifierScoresWarning:
    def test_warning_when_prediction_without_scores(self):
        v = make_video("VID-001", status="待拍")
        v["verifier_prediction"] = "5/5 通過"
        data = {"_meta": {}, "videos": [v]}
        warnings = []
        validate(data, warnings=warnings)
        assert any("verifier_scores" in w for w in warnings)

    def test_no_warning_when_both_present(self):
        v = make_video("VID-001", status="待拍")
        v["verifier_prediction"] = "5/5 通過"
        v["verifier_scores"] = {"conflict_score": 8, "pass_count": "5/5", "date": "2026-03-17"}
        data = {"_meta": {}, "videos": [v]}
        warnings = []
        validate(data, warnings=warnings)
        assert not any("verifier_scores" in w for w in warnings)

    def test_no_warning_when_neither_present(self):
        v = make_video("VID-001", status="待拍")
        data = {"_meta": {}, "videos": [v]}
        warnings = []
        validate(data, warnings=warnings)
        assert not any("verifier_scores" in w for w in warnings)
