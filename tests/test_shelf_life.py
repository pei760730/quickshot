"""Tests for shelf_life on ideas."""

from datetime import datetime

import pytest

from lib.pipeline import (
    load_pipeline, save_pipeline, add_item, classify_idea_freshness,
)


class TestAddItemShelfLife:
    def test_add_idea_with_trending(self, patch_paths):
        pdata = load_pipeline()
        idea_id = add_item(pdata, "食安新聞", shelf_life="trending")
        pdata2 = load_pipeline()
        item = next(i for i in pdata2["items"] if i["idea_id"] == idea_id)
        assert item["shelf_life"] == "trending"

    def test_add_idea_with_timely(self, patch_paths):
        pdata = load_pipeline()
        idea_id = add_item(pdata, "季節限定", shelf_life="timely")
        pdata2 = load_pipeline()
        item = next(i for i in pdata2["items"] if i["idea_id"] == idea_id)
        assert item["shelf_life"] == "timely"

    def test_add_idea_with_evergreen(self, patch_paths):
        pdata = load_pipeline()
        idea_id = add_item(pdata, "加盟主的一天", shelf_life="evergreen")
        pdata2 = load_pipeline()
        item = next(i for i in pdata2["items"] if i["idea_id"] == idea_id)
        assert item["shelf_life"] == "evergreen"

    def test_add_idea_default_none(self, patch_paths):
        pdata = load_pipeline()
        idea_id = add_item(pdata, "普通靈感")
        pdata2 = load_pipeline()
        item = next(i for i in pdata2["items"] if i["idea_id"] == idea_id)
        assert item["shelf_life"] is None

    def test_add_idea_invalid_shelf_life(self, patch_paths):
        pdata = load_pipeline()
        with pytest.raises(ValueError, match="非法 shelf_life"):
            add_item(pdata, "壞的", shelf_life="urgent")


class TestPreSaveValidateShelfLife:
    def test_invalid_shelf_life_blocked(self, patch_paths):
        pdata = load_pipeline()
        # Manually craft an item with bad shelf_life
        pdata["items"].append({
            "idea_id": "IDEA-001",
            "vid": None,
            "topic": "test",
            "tags": "",
            "title": None,
            "status": "inbox",
            "created_date": "2026-03-17",
            "status_history": [{"status": "inbox", "date": "2026-03-17"}],
            "publish_date": None,
            "script_path": None,
            "source": "pipeline",
            "source_inspiration": "test",
            "skill_used": None,
            "script_status": None,
            "notes": None,
            "backfill": None,
            "shelf_life": "INVALID",
        })
        with pytest.raises(ValueError, match="非法 shelf_life"):
            save_pipeline(pdata)

    def test_null_shelf_life_ok(self, patch_paths):
        pdata = load_pipeline()
        pdata["items"].append({
            "idea_id": "IDEA-001",
            "vid": None,
            "topic": "test",
            "tags": "",
            "title": None,
            "status": "inbox",
            "created_date": "2026-03-17",
            "status_history": [{"status": "inbox", "date": "2026-03-17"}],
            "publish_date": None,
            "script_path": None,
            "source": "pipeline",
            "source_inspiration": "test",
            "skill_used": None,
            "script_status": None,
            "notes": None,
            "backfill": None,
            "shelf_life": None,
        })
        # Should not raise
        save_pipeline(pdata)


# ── classify_idea_freshness 測試 ─────────────────────────

_THRESHOLDS = {
    "shelf_life_stale_days": {"timely": 14, "trending": 3},
    "shelf_life_expire_days": {"trending": 7},
}
_TODAY = datetime(2026, 4, 9)


def _make_idea(shelf_life, created_date):
    return {"shelf_life": shelf_life, "created_date": created_date}


class TestClassifyIdeaFreshness:
    def test_trending_fresh(self):
        item = _make_idea("trending", "2026-04-08")
        label, key = classify_idea_freshness(item, _THRESHOLDS, _TODAY)
        assert label == "fresh"
        assert key == 0

    def test_trending_stale(self):
        item = _make_idea("trending", "2026-04-05")
        label, key = classify_idea_freshness(item, _THRESHOLDS, _TODAY)
        assert label == "stale"
        assert key == 3

    def test_trending_expired(self):
        item = _make_idea("trending", "2026-04-01")
        label, key = classify_idea_freshness(item, _THRESHOLDS, _TODAY)
        assert label == "expired"
        assert key == 4

    def test_timely_fresh(self):
        item = _make_idea("timely", "2026-04-01")
        label, key = classify_idea_freshness(item, _THRESHOLDS, _TODAY)
        assert label == "fresh"
        assert key == 1

    def test_timely_stale(self):
        item = _make_idea("timely", "2026-03-20")
        label, key = classify_idea_freshness(item, _THRESHOLDS, _TODAY)
        assert label == "stale"
        assert key == 3

    def test_timely_expired(self):
        item = _make_idea("timely", "2026-03-01")
        label, key = classify_idea_freshness(item, _THRESHOLDS, _TODAY)
        assert label == "expired"
        assert key == 4

    def test_evergreen_always_fresh(self):
        item = _make_idea("evergreen", "2025-01-01")
        label, key = classify_idea_freshness(item, _THRESHOLDS, _TODAY)
        assert label == "fresh"
        assert key == 2

    def test_null_shelf_life_always_fresh(self):
        item = _make_idea(None, "2025-01-01")
        label, key = classify_idea_freshness(item, _THRESHOLDS, _TODAY)
        assert label == "fresh"
        assert key == 2

    def test_sort_order(self):
        """trending fresh < timely fresh < evergreen < stale < expired"""
        items = [
            _make_idea(None, "2026-04-08"),         # evergreen fresh
            _make_idea("trending", "2026-04-08"),    # trending fresh
            _make_idea("timely", "2026-04-01"),      # timely fresh
            _make_idea("trending", "2026-04-01"),    # trending expired
            _make_idea("timely", "2026-03-20"),      # timely stale
        ]
        results = [classify_idea_freshness(i, _THRESHOLDS, _TODAY) for i in items]
        keys = [r[1] for r in results]
        assert keys == [2, 0, 1, 4, 3]
        # sorted: trending(0), timely(1), evergreen(2), stale(3), expired(4)
        assert sorted(keys) == [0, 1, 2, 3, 4]
