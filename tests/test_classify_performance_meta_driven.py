"""Bounded Option A: 存檔分類路徑跟著 pipeline _meta.thresholds.performance 走。"""

from lib.backfill import classify_performance, resolve_performance_thresholds
from lib.config import PERFORMANCE_THRESHOLDS

# 自訂 low 門檻 60/30（高於常數 40/15），用來驗證 _meta 真的被吃。
_CUSTOM_META = {
    "thresholds": {
        "performance": {
            "high_A": {"retention_3s": 70, "completion_rate": 40},
            "high_B": {"views": 300000, "completion_rate": 40},
            "low": {"retention_3s_below": 60, "completion_rate_below": 30},
        }
    }
}


def test_classify_follows_meta_thresholds():
    """retention=55：自訂 low=60 下判 low、常數 low=40 下判 normal。"""
    assert classify_performance(1000, 55, 50, meta=_CUSTOM_META)[0] == "low"
    assert classify_performance(1000, 55, 50)[0] == "normal"  # 無 meta → 常數 fallback


def test_resolve_falls_back_to_constant():
    """meta 缺漏 / 格式不符 → 回常數（不炸、不漂）。"""
    assert resolve_performance_thresholds(None) is PERFORMANCE_THRESHOLDS
    assert resolve_performance_thresholds({}) is PERFORMANCE_THRESHOLDS
    assert resolve_performance_thresholds({"thresholds": {}}) is PERFORMANCE_THRESHOLDS
    assert resolve_performance_thresholds({"thresholds": {"performance": "bad"}}) is PERFORMANCE_THRESHOLDS
