#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本機資料掃描器：靈感庫 + 待辦 + 工具函數。
"""

import json
import os
from datetime import datetime
from pathlib import Path

from .config import PROJECT_ROOT, TW_TZ, resolve_operator
from scripts.ops.lib.pipeline import get_pipeline_data


def now_tw():
    return datetime.now(TW_TZ)


def as_text_date(date_str):
    """在日期字串前加 ' 強制 Sheets 當純文字，避免被轉成序號。
    只接受有效的 YYYY-MM-DD 日期，無效則回傳空字串。
    """
    if date_str and date_str.strip():
        cleaned = date_str.strip()
        try:
            datetime.strptime(cleaned, "%Y-%m-%d")
            return "'" + cleaned
        except ValueError:
            return ""
    return ""


def scan_inspiration(operator=None):
    """從 pipeline.json（SSoT）讀取靈感列表。

    operator: 若無效則 fallback 到預設 operator
    靈感 = items 中 status 為 inbox / selected / cooldown 的項目。

    回傳格式：[{"title", "tag", "date", "status", "done_date"}]
    """
    IDEA_STATUSES = {"inbox", "selected", "cooldown"}
    items = []
    op = resolve_operator(operator)
    pipeline_json = os.path.join(PROJECT_ROOT, "data", op, "pipeline.json")
    data = get_pipeline_data(pipeline_json=pipeline_json)
    if data is None:
        return items
    for item in data.get("items", []):
        status = item.get("status", "")
        if status not in IDEA_STATUSES:
            continue
        done_date = ""
        items.append({
            "title": item.get("title", "") or item.get("topic", ""),
            "tag": item.get("tags", ""),
            "date": item.get("created_date", ""),
            "status": status,
            "done_date": done_date,
        })
    return items


def scan_todos(operator=None):
    """
    掃描 data/[operator]/todos.json，回傳:
    (work_pending, work_done, misc_pending, misc_done)
    每個元素是 dict: {"task": str, "due_date": str, "done_date": str}

    分組規則（v4.40 + P2 修正）：
    - tags 含 "misc" → 雜事組
    - 其他（含 "work" 或無 tag）→ 工作組（預設）
    """
    work_pending, work_done, misc_pending, misc_done = [], [], [], []
    op = resolve_operator(operator)
    todos_json = Path(PROJECT_ROOT) / "data" / op / "todos.json"
    if not todos_json.exists():
        return work_pending, work_done, misc_pending, misc_done

    try:
        payload = json.loads(todos_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, PermissionError):
        return work_pending, work_done, misc_pending, misc_done

    for row in payload.get("todos", []):
        item = {
            "task": row.get("title", ""),
            "due_date": row.get("due") or "",
            "done_date": row.get("closed_at") or "",
        }
        tags = row.get("tags") or []
        is_misc = "misc" in tags
        state = row.get("state")
        if state in ("pending", "in_progress"):
            (misc_pending if is_misc else work_pending).append(item)
        elif state in ("done", "archived"):
            (misc_done if is_misc else work_done).append(item)

    return work_pending, work_done, misc_pending, misc_done
