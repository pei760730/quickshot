#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot migration: markdown todo files -> structured todos.json."""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import config as _cfg
from lib.todos import _load_payload, _save_payload, _allocate_todo_id

_DUE_RE = re.compile(r"📅(\d{4}-\d{2}-\d{2})")
_DONE_RE = re.compile(r"✅(\d{4}-\d{2}-\d{2})")
_CHECKBOX_RE = re.compile(r"^-\s*\[(?P<mark>[ xX])\]\s*(?P<body>.+)$")

SOURCE_FILES = [
    ("工作待辦.md", ["work"]),
    ("雜事待辦.md", ["misc"]),
]


def _todo_dir():
    return _cfg.PROJECT_ROOT / "00-control-center" / "todo"


def _source_candidates(name):
    todo_dir = _todo_dir()
    return [todo_dir / name, todo_dir / name.replace(".md", ".legacy.md")]


def _first_existing(paths):
    for p in paths:
        if p.exists():
            return p
    return None


def _normalize_title(body):
    line = _DUE_RE.sub("", body)
    line = _DONE_RE.sub("", line)
    line = re.sub(r"逾期\s*\d+\s*天", "", line)
    return line.strip()


def _parse_markdown(path):
    items = []
    in_comment = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if line.startswith("<!--"):
            if "-->" not in line:
                in_comment = True
            continue

        m = _CHECKBOX_RE.match(line)
        if not m:
            continue

        done = m.group("mark").lower() == "x"
        body = m.group("body").strip()
        title = _normalize_title(body)
        if not title:
            continue

        due_m = _DUE_RE.search(body)
        done_m = _DONE_RE.search(body)

        items.append(
            {
                "title": title,
                "due": due_m.group(1) if due_m else None,
                "state": "done" if done else "pending",
                "closed_at": done_m.group(1) if done_m else None,
                "closed_reason": "migration from md" if done else None,
            }
        )
    return items


def run_migration(operator=None):
    operator = operator or _cfg.DEFAULT_OPERATOR
    payload = _load_payload(operator)
    now = _cfg.today_str()

    existing_keys = {
        (
            (t.get("title") or "").strip(),
            t.get("state"),
            t.get("due") or "",
            t.get("closed_at") or "",
        )
        for t in payload.get("todos", [])
    }

    migrated = 0
    parsed_rows = 0
    renamed = []

    for source_name, source_tags in SOURCE_FILES:
        src = _first_existing(_source_candidates(source_name))
        if src is None:
            continue

        rows = _parse_markdown(src)
        parsed_rows += len(rows)

        for row in rows:
            key = (row["title"], row["state"], row.get("due") or "", row.get("closed_at") or "")
            if key in existing_keys:
                continue

            todo_id = _allocate_todo_id(payload)
            payload["todos"].append(
                {
                    "id": todo_id,
                    "title": row["title"],
                    "state": row["state"],
                    "priority": "normal",
                    "due": row.get("due"),
                    "created_at": now,
                    "closed_at": row.get("closed_at"),
                    "closed_reason": row.get("closed_reason"),
                    "related_vid": None,
                    "related_lesson_id": None,
                    "tags": list(source_tags),
                    "notes": None,
                }
            )
            existing_keys.add(key)
            migrated += 1

        if src.name.endswith(".md") and not src.name.endswith(".legacy.md"):
            legacy = src.with_name(src.name.replace(".md", ".legacy.md"))
            if not legacy.exists():
                src.rename(legacy)
                renamed.append((src.name, legacy.name))

    _save_payload(operator, payload)
    return {
        "operator": operator,
        "parsed_rows": parsed_rows,
        "migrated": migrated,
        "after": len(payload.get("todos", [])),
        "renamed": renamed,
        "output": str(_cfg.get_operator_paths(operator)["data_dir"] / "todos.json"),
    }


def main():
    parser = argparse.ArgumentParser(description="Migrate markdown todo files to structured todos.json")
    parser.add_argument("--operator", default=_cfg.DEFAULT_OPERATOR)
    args = parser.parse_args()
    result = run_migration(operator=args.operator)
    print(
        f"✅ migrate_todos complete: operator={result['operator']} "
        f"parsed={result['parsed_rows']} migrated={result['migrated']} after={result['after']}"
    )


if __name__ == "__main__":
    main()
