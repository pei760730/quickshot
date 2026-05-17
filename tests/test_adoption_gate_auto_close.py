from scripts.utils.lib.adoption_gate import auto_close_todos


def test_auto_close_related_vid_backfilled():
    pipeline = [{"vid": "VID-001", "status": "已上線", "backfill": {"views": 1}}]
    todos = [{"id": "T-0001", "state": "pending", "related_vid": "VID-001"}]
    closed = auto_close_todos(pipeline, todos, dry_run=False)
    assert closed == ["T-0001"]
    assert todos[0]["state"] == "archived"
    assert todos[0]["closed_reason"] == "related VID backfilled"
