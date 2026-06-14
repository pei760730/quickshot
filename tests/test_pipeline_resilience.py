"""Pipeline 故障容忍：壞 shard skip + counter 漂移偵測。"""

from conftest import write_sharded_pipeline
from lib.pipeline import get_pipeline_data
from lib.validate import validate_all


def test_corrupt_shard_skipped_not_fatal(tmp_path, capsys):
    """一個半寫壞的 shard 不該讓整個 load SystemExit；其餘 items 照常載入。"""
    data_dir = tmp_path / "data" / "kai"
    write_sharded_pipeline(
        data_dir,
        {
            "_meta": {"next_vid": 3, "next_idea_id": 3},
            "items": [
                {"vid": "VID-001", "idea_id": "IDEA-001", "status": "已上線"},
                {"vid": "VID-002", "idea_id": "IDEA-002", "status": "已上線"},
            ],
        },
    )
    # 故意把一個 shard 寫成壞 JSON（模擬 crash 半寫）
    (data_dir / "pipeline" / "items" / "VID-001.json").write_text(
        "{ broken json", encoding="utf-8"
    )

    payload = get_pipeline_data(pipeline_json=data_dir / "pipeline.json")
    vids = {it.get("vid") for it in payload["items"]}
    assert vids == {"VID-002"}  # 壞的跳過、好的留（沒有 SystemExit）
    assert "跳過損壞" in capsys.readouterr().out


def test_validate_all_flags_next_vid_drift():
    """_meta.next_vid <= 現有最大 VID → error（防下次配號撞號蓋舊影片）。"""
    video_data = {
        "_meta": {"next_vid": 2},
        "videos": [
            {"vid": "VID-001", "status": "待拍", "topic": "x",
             "created_date": "2026-01-01", "status_history": []},
            {"vid": "VID-005", "status": "待拍", "topic": "y",
             "created_date": "2026-01-01", "status_history": []},
        ],
    }
    result = validate_all(video_data)
    assert any("next_vid" in e for e in result["errors"])


def test_validate_all_ok_when_next_vid_ahead():
    """next_vid 領先現有最大號 → 不該誤報。"""
    video_data = {
        "_meta": {"next_vid": 6},
        "videos": [
            {"vid": "VID-005", "status": "待拍", "topic": "y",
             "created_date": "2026-01-01", "status_history": []},
        ],
    }
    result = validate_all(video_data)
    assert not any("next_vid" in e for e in result["errors"])
