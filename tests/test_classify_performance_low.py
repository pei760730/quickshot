"""Boundary tests for low-performance thresholds."""

from lib.backfill import classify_performance
from lib.config import PERFORMANCE_THRESHOLDS


def test_low_when_retention_below_threshold_even_if_completion_ok():
    lo = PERFORMANCE_THRESHOLDS["low"]
    level, _path, _reason = classify_performance(
        views=10000,
        retention_3s=lo["retention_3s_max"] - 0.01,
        completion_rate=lo["completion_rate_max"] + 1,
    )
    assert level == "low"


def test_low_when_completion_below_threshold_even_if_retention_ok():
    lo = PERFORMANCE_THRESHOLDS["low"]
    level, _path, _reason = classify_performance(
        views=10000,
        retention_3s=lo["retention_3s_max"] + 5,
        completion_rate=lo["completion_rate_max"] - 0.01,
    )
    assert level == "low"


def test_not_low_on_exact_boundary_values():
    lo = PERFORMANCE_THRESHOLDS["low"]
    level, _path, _reason = classify_performance(
        views=10000,
        retention_3s=lo["retention_3s_max"],
        completion_rate=lo["completion_rate_max"],
    )
    assert level != "low"


def test_not_low_when_both_above_threshold():
    lo = PERFORMANCE_THRESHOLDS["low"]
    level, _path, _reason = classify_performance(
        views=10000,
        retention_3s=lo["retention_3s_max"] + 0.5,
        completion_rate=lo["completion_rate_max"] + 0.5,
    )
    assert level != "low"
