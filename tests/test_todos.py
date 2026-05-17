"""Tests for structured todos storage."""

import pytest

from lib.todos import add_todo, load_todos, close_todo, reopen_todo, archive_todo, update_todo, query


def test_add_and_load(patch_paths):
    todo_id = add_todo("kai", title="週報整理", due="2026-03-20", tags=["運營"])
    rows = load_todos("kai")
    assert todo_id == "T-0001"
    assert len(rows) == 1
    assert rows[0]["title"] == "週報整理"


def test_duplicate_title_warns(patch_paths):
    add_todo("kai", title="重複任務")
    with pytest.warns(UserWarning):
        add_todo("kai", title="重複任務")


def test_state_transitions_and_reopen(patch_paths):
    todo_id = add_todo("kai", title="VID-013 確認")
    assert close_todo("kai", todo_id, reason="完成") is True
    row = load_todos("kai")[0]
    assert row["state"] == "done"
    assert row["closed_reason"] == "完成"

    assert reopen_todo("kai", todo_id) is True
    row = load_todos("kai")[0]
    assert row["state"] == "in_progress"
    assert row["closed_at"] == "2026-03-17"

    assert archive_todo("kai", todo_id, reason="擱置") is True
    assert load_todos("kai")[0]["state"] == "archived"

    with pytest.raises(ValueError):
        close_todo("kai", todo_id, reason="再次關閉")


def test_update_and_query_filters(patch_paths):
    a = add_todo("kai", title="A", priority="normal", due="2026-03-17", tags=["運營"])
    add_todo("kai", title="B", priority="high", due="2026-03-30", tags=["品牌"])

    assert update_todo("kai", a, priority="urgent", notes="today", related_vid="VID-001") is True
    assert len(query("kai", priority="urgent")) == 1
    assert len(query("kai", due_before="2026-03-20")) == 1
    assert len(query("kai", tag="品牌")) == 1
    assert len(query("kai", overdue=True)) == 1


def test_update_terminal_rejected(patch_paths):
    todo_id = add_todo("kai", title="terminal")
    close_todo("kai", todo_id, reason="done")
    with pytest.raises(ValueError):
        update_todo("kai", todo_id, title="nope")
