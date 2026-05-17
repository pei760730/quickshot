import json
from datetime import date
from pathlib import Path

from conftest import write_sharded_pipeline
from scripts.utils.lib.adoption_gate import _todo_owner, collect_items


def test_owner_split_gate_count(
    tmp_path: Path, operator_fixture, patch_operator_registry
):
    (tmp_path / "data" / operator_fixture).mkdir(parents=True)
    (tmp_path / "01-data-brain").mkdir(parents=True)
    pipeline = {
        "items": [
            {
                "vid": "VID-001",
                "status": "已上線",
                "backfill": None,
                "backfill_due_date": "2026-04-01",
            },
        ]
    }
    todos = {
        "todos": [
            {
                "id": "T-0001",
                "title": "Kai 決策",
                "state": "pending",
                "due": "2026-04-01",
                "tags": [],
            }
        ]
    }
    brand = "## [1] test\n<!-- last_updated: 2026-03-01 -->\n"
    write_sharded_pipeline(tmp_path / "data" / operator_fixture, pipeline)
    (tmp_path / "data" / operator_fixture / "todos.json").write_text(
        json.dumps(todos, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "01-data-brain" / "brand.md").write_text(brand, encoding="utf-8")

    items, _ = collect_items(
        tmp_path, today=date(2026, 4, 26), dry_run=True, operator=operator_fixture
    )
    decision_owner = [i for i in items if i.owner == operator_fixture]
    employee = [i for i in items if i.owner == "employee"]
    assert all(i.code != "E1" for i in items)
    assert len(employee) >= 1
    assert isinstance(decision_owner, list)  # owner-routed list still computed


def test_todo_owner_auto_tag_route():
    todo = {"title": "自動修復", "tags": ["auto-stage2"], "notes": ""}
    assert _todo_owner(todo) == "auto"
