#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified todos storage for per-operator structured tasks."""

from copy import deepcopy
import re
import warnings

from . import config as _cfg
from .config import today_str
from .storage import load_json, save_json

VALID_STATES = {"pending", "in_progress", "done", "archived"}
VALID_PRIORITIES = {"low", "normal", "high", "urgent"}
TERMINAL_STATES = {"done", "archived"}

_ID_RE = re.compile(r"^T-(\d{4,})$")

_ALLOWED_TRANSITIONS = {
    "pending": {"in_progress", "done", "archived"},
    "in_progress": {"done", "archived"},
    "done": set(),
    "archived": set(),
}

_UPDATE_FIELDS = {
    "title",
    "priority",
    "due",
    "tags",
    "notes",
    "related_vid",
    "related_lesson_id",
    "state",
}

_EMPTY = {
    "schema_version": "1.0",
    "description": "Per-operator structured todo list.",
    "next_id": 1,
    "todos": [],
}


def _todos_json(operator=None):
    paths = _cfg.get_operator_paths(operator)
    return paths["data_dir"] / "todos.json"


def _norm_tags(tags):
    if tags is None:
        return []
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]
    if isinstance(tags, list):
        return [str(t).strip() for t in tags if str(t).strip()]
    return [str(tags).strip()] if str(tags).strip() else []


def _norm_priority(priority):
    p = (priority or "normal").strip()
    if p not in VALID_PRIORITIES:
        raise ValueError(f"invalid priority: {priority}")
    return p


def _norm_state(state):
    s = (state or "pending").strip()
    if s not in VALID_STATES:
        raise ValueError(f"invalid state: {state}")
    return s


def _load_payload(operator=None):
    raw = load_json(_todos_json(operator), deepcopy(_EMPTY), label="todos")
    todos = raw.get("todos") if isinstance(raw.get("todos"), list) else []

    next_id = raw.get("next_id")
    if not isinstance(next_id, int) or next_id <= 0:
        max_id = 0
        for row in todos:
            m = _ID_RE.match(str(row.get("id", "")))
            if m:
                max_id = max(max_id, int(m.group(1)))
        next_id = max_id + 1 if max_id else 1

    payload = {
        "schema_version": str(raw.get("schema_version") or "1.0"),
        "description": raw.get("description") or _EMPTY["description"],
        "next_id": next_id,
        "todos": todos,
    }

    for item in payload["todos"]:
        item["state"] = _norm_state(item.get("state") or "pending")
        item["priority"] = _norm_priority(item.get("priority") or "normal")
        item["tags"] = _norm_tags(item.get("tags"))
        item["due"] = item.get("due") or None
        item["closed_at"] = item.get("closed_at") or None
        item["closed_reason"] = item.get("closed_reason") or None
        item["related_vid"] = item.get("related_vid") or None
        item["related_lesson_id"] = item.get("related_lesson_id") or None
        item["notes"] = item.get("notes") or None
        item.setdefault("created_at", today_str())

    return payload


def _save_payload(operator, payload):
    save_json(_todos_json(operator), payload, update_meta=False)


def _allocate_todo_id(payload):
    todo_id = f"T-{payload['next_id']:04d}"
    payload["next_id"] += 1
    return todo_id


def _find_todo(payload, todo_id):
    for item in payload["todos"]:
        if item.get("id") == todo_id:
            return item
    return None


def _validate_transition(current_state, new_state):
    if new_state == current_state:
        return
    if new_state not in _ALLOWED_TRANSITIONS.get(current_state, set()):
        raise ValueError(f"invalid state transition: {current_state} -> {new_state}")


def load_todos(operator=None):
    return _load_payload(operator)["todos"]


def add_todo(
    operator,
    title,
    priority="normal",
    due=None,
    related_vid=None,
    related_lesson_id=None,
    tags=None,
    notes=None,
):
    title = (title or "").strip()
    if not title:
        raise ValueError("title is required")

    payload = _load_payload(operator)
    prio = _norm_priority(priority)
    now = today_str()

    for item in payload["todos"]:
        if item.get("state") not in ("pending", "in_progress"):
            continue
        if item.get("title", "").strip() == title:
            warnings.warn(
                f"similar open todo exists: {item.get('id')} {title}",
                UserWarning,
            )
            break

    todo_id = _allocate_todo_id(payload)
    payload["todos"].append(
        {
            "id": todo_id,
            "title": title,
            "state": "pending",
            "priority": prio,
            "due": due,
            "created_at": now,
            "closed_at": None,
            "closed_reason": None,
            "related_vid": related_vid or None,
            "related_lesson_id": related_lesson_id or None,
            "tags": _norm_tags(tags),
            "notes": notes or None,
        }
    )
    _save_payload(operator, payload)
    return todo_id


def close_todo(operator, todo_id, reason):
    payload = _load_payload(operator)
    item = _find_todo(payload, todo_id)
    if item is None:
        return False
    _validate_transition(item.get("state", "pending"), "done")
    item["state"] = "done"
    item["closed_at"] = today_str()
    item["closed_reason"] = (reason or "").strip() or "closed"
    _save_payload(operator, payload)
    return True


def reopen_todo(operator, todo_id):
    payload = _load_payload(operator)
    item = _find_todo(payload, todo_id)
    if item is None:
        return False
    if item.get("state") != "done":
        raise ValueError("reopen only supports done -> in_progress")
    item["state"] = "in_progress"
    _save_payload(operator, payload)
    return True


def archive_todo(operator, todo_id, reason):
    payload = _load_payload(operator)
    item = _find_todo(payload, todo_id)
    if item is None:
        return False
    _validate_transition(item.get("state", "pending"), "archived")
    item["state"] = "archived"
    item["closed_at"] = today_str()
    item["closed_reason"] = (reason or "").strip() or "archived"
    _save_payload(operator, payload)
    return True


def update_todo(operator, todo_id, **fields):
    unknown = set(fields.keys()) - _UPDATE_FIELDS
    if unknown:
        raise ValueError(f"unsupported fields: {sorted(unknown)}")

    payload = _load_payload(operator)
    item = _find_todo(payload, todo_id)
    if item is None:
        return False

    current_state = item.get("state", "pending")
    if current_state in TERMINAL_STATES:
        raise ValueError("cannot update terminal todo")

    if "state" in fields:
        new_state = _norm_state(fields["state"])
        _validate_transition(current_state, new_state)
        item["state"] = new_state
        current_state = new_state

    if "title" in fields and fields["title"] is not None:
        title = str(fields["title"]).strip()
        if not title:
            raise ValueError("title is required")
        item["title"] = title

    if "priority" in fields and fields["priority"] is not None:
        item["priority"] = _norm_priority(fields["priority"])

    if "due" in fields:
        item["due"] = fields["due"] or None

    if "tags" in fields:
        item["tags"] = _norm_tags(fields["tags"])

    for key in ("notes", "related_vid", "related_lesson_id"):
        if key in fields:
            item[key] = fields[key] or None

    _save_payload(operator, payload)
    return True


def query(operator, state=None, priority=None, due_before=None, tag=None, overdue=False):
    rows = load_todos(operator)
    today = today_str()
    result = []
    for item in rows:
        item_state = item.get("state")
        item_due = item.get("due")

        if overdue:
            if item_state != "pending":
                continue
            if not item_due or item_due > today:
                continue
        else:
            if state and item_state != state:
                continue
            if priority and item.get("priority") != priority:
                continue
            if due_before and (not item_due or item_due > due_before):
                continue

        if tag and tag not in (item.get("tags") or []):
            continue

        result.append(item)

    return result
