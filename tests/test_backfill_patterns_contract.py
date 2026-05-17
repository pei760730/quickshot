"""Contract tests preventing patterns/backfill export drift."""


def test_backfill_reexports_pattern_helpers_exist(patch_paths):
    """Regression guard: backfill should keep pattern helper re-exports importable."""
    from lib import backfill

    expected = [
        "PATTERN_KEYS",
        "win_rate_note",
        "load_performance_patterns",
        "save_performance_patterns",
        "_check_pattern_decay",
        "_add_vid_evidence",
        "_remove_vid_from_patterns",
        "_remove_vid_from_low_evidence",
        "cleanup_unverified_formulas",
    ]
    for name in expected:
        assert hasattr(backfill, name), f"missing backfill export: {name}"
