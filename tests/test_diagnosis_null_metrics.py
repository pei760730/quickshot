"""diagnose_video must not crash on null retention/completion (L-0024)."""

from lib.diagnosis import diagnose_video


def test_diagnose_video_handles_null_metrics():
    """L-0024 允許 retention_3s / completion_rate 為 null（來源無資料）。
    diagnose_video 直接拿來比大小過、None 會 TypeError；本測試守住 coerce。"""
    bf = {"views": 1000, "retention_3s": None, "completion_rate": None}
    result = diagnose_video(bf, performance_patterns={})
    assert isinstance(result, dict)
    assert "weaknesses" in result
    assert "prescriptions" in result


def test_diagnose_video_null_one_metric():
    """單邊 null 也不可炸。"""
    bf = {"views": 1000, "retention_3s": None, "completion_rate": 30.0}
    result = diagnose_video(bf, performance_patterns={})
    assert isinstance(result, dict)
