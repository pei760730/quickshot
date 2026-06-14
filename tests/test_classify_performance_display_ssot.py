"""Ensure utils display classification stays aligned with ops SSoT thresholds."""

import lib.backfill as ops_backfill
from path_bootstrap import load_module_from_repo

_utils_config = load_module_from_repo("scripts/utils/lib/config.py", "utils_config_for_test")


def _utils_category(display):
    """Map utils emoji display -> ops level vocabulary for comparison."""
    if "低" in display:
        return "low"
    if "普通" in display:
        return "normal"
    return "high"  # 🟢 高 / 🟡 留存高


# Points chosen to span the band where ops-hardcoded 50/25 used to diverge from
# the SSoT 40/15: retention in [40,50) or completion in [15,25) must land "normal",
# not "low". These exercise the REAL default path (no injected thresholds, no
# monkeypatch) — the gap the previous rigged test could never catch.
_DEFAULT_PATH_CASES = [
    # views, retention_3s, completion_rate, expected_level
    (10000, 45, 20, "normal"),   # in old divergence band -> must be normal under 40/15
    (10000, 48, 16, "normal"),   # ditto
    (10000, 30, 50, "low"),      # retention < 40 -> low
    (10000, 50, 10, "low"),      # completion < 15 -> low
    (10000, 50, 25, "normal"),   # just above low on both
    (500000, 80, 50, "high"),    # high_B
]


def test_ops_and_utils_agree_on_default_thresholds():
    """ops classify_performance and utils display must agree on the default path.

    This is the guard that actually fails when ops PERFORMANCE_THRESHOLDS drifts
    from the SSoT (the 50/25 vs 40/15 split). No monkeypatch, no injected
    thresholds — both sides use their real defaults.
    """
    for views, retention_3s, completion_rate, expected in _DEFAULT_PATH_CASES:
        ops_level, _path, _reason = ops_backfill.classify_performance(
            views, retention_3s, completion_rate
        )
        utils_display = _utils_config.classify_performance_display(
            views, retention_3s, completion_rate
        )
        utils_level = _utils_category(utils_display)
        assert ops_level == expected, (
            f"ops drift: ({views},{retention_3s},{completion_rate}) "
            f"-> {ops_level}, expected {expected}"
        )
        assert utils_level == expected, (
            f"utils drift: ({views},{retention_3s},{completion_rate}) "
            f"-> {utils_display} ({utils_level}), expected {expected}"
        )
        assert ops_level == utils_level


def test_utils_display_honors_injected_meta_thresholds():
    """When _meta.thresholds.performance is passed, utils must honor it (data-driven)."""
    tuned = {
        "high_A": {"retention_3s": 75, "completion_rate": 45},
        "high_B": {"views": 500000, "completion_rate": 45},
        "low": {"retention_3s_below": 35, "completion_rate_below": 12},
    }
    # retention=33 < 35 -> low under the tuned thresholds (would be normal under defaults).
    display = _utils_config.classify_performance_display(
        10000, 33, 50, thresholds=tuned
    )
    assert "低" in display
