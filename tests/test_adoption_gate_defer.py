import json
from datetime import date
from pathlib import Path

from conftest import write_sharded_pipeline
from scripts.utils.lib.adoption_gate import collect_items


def _write_minimal_data(tmp_path: Path, operator: str, todos: list[dict]) -> None:
    (tmp_path / "data" / operator).mkdir(parents=True, exist_ok=True)
    (tmp_path / "01-data-brain").mkdir(parents=True, exist_ok=True)
    write_sharded_pipeline(tmp_path / "data" / operator, {"_meta": {}, "items": []})
    (tmp_path / "data" / operator / "todos.json").write_text(
        json.dumps({"todos": todos}, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "01-data-brain" / "brand.md").write_text("# brand\n", encoding="utf-8")


def test_defer_pending_suppresses_original_todo(
    tmp_path: Path, operator_fixture, patch_operator_registry
):
    todos = [
        {
            "id": "T-0003",
            "title": "原始待辦",
            "state": "pending",
            "due": "2026-05-01",
            "tags": [],
        },
        {
            "id": "T-0019",
            "title": "defer: T1 原始待辦",
            "state": "pending",
            "due": "2026-05-15",
            "tags": [],
        },
    ]
    _write_minimal_data(tmp_path, operator_fixture, todos)

    items, _ = collect_items(
        tmp_path, today=date(2026, 5, 3), dry_run=True, operator=operator_fixture
    )
    todo_messages = [it.message for it in items if it.code.startswith("T")]

    assert todo_messages == []


def test_defer_archived_restores_original_todo(
    tmp_path: Path, operator_fixture, patch_operator_registry
):
    todos = [
        {
            "id": "T-0003",
            "title": "原始待辦",
            "state": "pending",
            "due": "2026-05-01",
            "tags": [],
        },
        {
            "id": "T-0019",
            "title": "defer: T1 原始待辦",
            "state": "archived",
            "due": "2026-05-15",
            "tags": [],
        },
    ]
    _write_minimal_data(tmp_path, operator_fixture, todos)

    items, _ = collect_items(
        tmp_path, today=date(2026, 5, 3), dry_run=True, operator=operator_fixture
    )
    todo_messages = [it.message for it in items if it.code.startswith("T")]

    assert len(todo_messages) == 1
    assert "原始待辦" in todo_messages[0]


def test_defer_marker_itself_suppressed_when_due_past(
    tmp_path: Path, operator_fixture, patch_operator_registry
):
    """Defer marker 自己的 due 過期時、也不該出現在 gate（只當 suppression marker 用）。"""
    todos = [
        {
            "id": "T-0003",
            "title": "原始待辦",
            "state": "pending",
            "due": "2026-04-25",
            "tags": [],
        },
        {
            "id": "T-0019",
            "title": "defer: T1 原始待辦",
            "state": "pending",
            "due": "2026-04-29",
            "tags": [],
        },
    ]
    _write_minimal_data(tmp_path, operator_fixture, todos)

    items, _ = collect_items(
        tmp_path, today=date(2026, 5, 3), dry_run=True, operator=operator_fixture
    )
    todo_messages = [it.message for it in items if it.code.startswith("T")]

    # 原 todo 被 marker suppress、marker 自己也不顯示
    assert todo_messages == [], f"Expected no T items, got: {todo_messages}"
