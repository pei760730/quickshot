from pathlib import Path

from conftest import write_sharded_pipeline
from scripts.utils.lessons_retrieval import get_similar_vids


def test_similar_vids_prefers_tag_overlap(tmp_path: Path):
    payload = {
        "items": [
            {"vid": "VID-001", "tags": "加盟主 合拍", "status": "待拍", "created_date": "2026-04-01", "backfill": {"performance": "normal"}},
            {"vid": "VID-002", "tags": "加盟主 合拍", "status": "已上線", "publish_date": "2026-04-02", "backfill": {"performance": "normal", "views": 100}},
            {"vid": "VID-003", "tags": "創業", "status": "已上線", "publish_date": "2026-04-03", "backfill": {"performance": "high", "views": 999}},
        ]
    }
    write_sharded_pipeline(tmp_path, payload)

    rows = get_similar_vids("VID-001", limit=2, pipeline_path=tmp_path / "pipeline.json")
    assert rows[0]["vid"] == "VID-002"

