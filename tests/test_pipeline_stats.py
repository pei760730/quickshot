"""Tests for pipeline_stats funnel."""


from lib.pipeline import pipeline_stats


def _make_pipeline(items):
    return {"_meta": {}, "items": items}


def _item(idea_id, status, vid=None, created="2026-03-01",
          publish=None, backfill=None):
    return {
        "idea_id": idea_id, "vid": vid, "topic": f"topic-{idea_id}",
        "status": status, "created_date": created,
        "publish_date": publish, "backfill": backfill,
        "status_history": [{"status": status, "date": created}],
        "tags": "", "title": None, "source": "pipeline",
    }


class TestPipelineStats:
    def test_empty(self):
        stats = pipeline_stats(_make_pipeline([]))
        assert stats["total_ideas"] == 0
        assert stats["idea_to_vid_pct"] == 0
        assert stats["avg_cycle_days"] is None

    def test_basic_funnel(self):
        items = [
            _item("IDEA-001", "inbox"),
            _item("IDEA-002", "selected"),
            _item("IDEA-003", "已上線", vid="VID-001",
                  created="2026-03-01", publish="2026-03-11",
                  backfill={"views": 100}),
            _item("IDEA-004", "待拍", vid="VID-002"),
            _item("IDEA-005", "archived"),
        ]
        stats = pipeline_stats(_make_pipeline(items))
        assert stats["total_ideas"] == 5
        assert stats["has_vid"] == 2
        assert stats["published"] == 1
        assert stats["backfilled"] == 1
        assert stats["archived"] == 1
        assert stats["idea_to_vid_pct"] == 40.0
        assert stats["vid_to_publish_pct"] == 50.0
        assert stats["idea_to_publish_pct"] == 20.0

    def test_avg_cycle(self):
        items = [
            _item("IDEA-001", "已上線", vid="VID-001",
                  created="2026-03-01", publish="2026-03-11"),
            _item("IDEA-002", "已上線", vid="VID-002",
                  created="2026-03-01", publish="2026-03-21"),
        ]
        stats = pipeline_stats(_make_pipeline(items))
        assert stats["avg_cycle_days"] == 15.0
        assert stats["cycle_sample_size"] == 2

    def test_longest_wait(self):
        items = [
            _item("IDEA-001", "待拍", vid="VID-001", created="2026-01-01"),
            _item("IDEA-002", "待拍", vid="VID-002", created="2026-04-01"),
        ]
        stats = pipeline_stats(_make_pipeline(items))
        lw = stats["longest_wait"]
        assert lw["vid"] == "VID-001"
        assert lw["days"] > 0
