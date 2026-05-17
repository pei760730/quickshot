"""Ensure utils display classification stays aligned with ops SSoT thresholds."""

import lib.backfill as ops_backfill
from path_bootstrap import load_module_from_repo


def _to_ops_thresholds(meta_perf_thresholds):
    """Convert pipeline _meta.thresholds.performance schema -> ops schema."""
    return {
        "high": {
            "path_A": {
                "retention_3s_min": meta_perf_thresholds["high_A"]["retention_3s"],
                "completion_rate_min": meta_perf_thresholds["high_A"]["completion_rate"],
            },
            "path_B": {
                "views_min": meta_perf_thresholds["high_B"]["views"],
                "completion_rate_min": meta_perf_thresholds["high_B"]["completion_rate"],
            },
        },
        "low": {
            "retention_3s_max": meta_perf_thresholds["low"]["retention_3s_below"],
            "completion_rate_max": meta_perf_thresholds["low"]["completion_rate_below"],
        },
    }


def test_utils_display_uses_meta_thresholds_and_matches_ops(monkeypatch):
    utils_config = load_module_from_repo("scripts/utils/lib/config.py", "utils_config_for_test")

    # Simulate _meta.thresholds.performance being tuned by product/ops.
    meta_perf_thresholds = {
        "high_A": {"retention_3s": 75, "completion_rate": 45},
        "high_B": {"views": 500000, "completion_rate": 45},
        "low": {"retention_3s_below": 35, "completion_rate_below": 12},
    }

    # This case is "normal" under new thresholds (was high under old defaults).
    views, retention_3s, completion_rate = 320000, 72, 41

    monkeypatch.setattr(
        ops_backfill,
        "PERFORMANCE_THRESHOLDS",
        _to_ops_thresholds(meta_perf_thresholds),
    )

    utils_display = utils_config.classify_performance_display(
        views, retention_3s, completion_rate, thresholds=meta_perf_thresholds
    )
    ops_display = ops_backfill.classify_performance_display(
        views, retention_3s, completion_rate
    )

    assert utils_display == ops_display
    assert "普通" in utils_display
