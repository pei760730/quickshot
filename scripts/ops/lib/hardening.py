#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dialog-time hardening (v4.67+、Stage F Orchestrator 退役後).

v4.67（Opus 4.7 全修 Stage F）移除 queue-based orchestrator（observer / queue /
archive state machine / cron / 禁令 #8 Executor rollback），因實證未運作過。
保留 `/harden` 對話內一站式硬化路徑（Stage D v4.64 建立）作為唯一入口。

對外 API：
- `harden_from_dialog(operator, lesson_id, path, draft_content, archive=True)`

保留 archive 記錄到 `data/<operator>/hardening-archive.json` 作為稽核線（source="dialog"）。
"""

from copy import deepcopy

from . import config as _cfg
from .config import today_str
from .storage import load_json, save_json

# path → action.type mapping（對應 Stage D /harden skill 規格的 5 種路徑）
_DIALOG_PATHS = {
    "test": "test_skeleton",
    "lint": "lint_rule",
    "claude_md": "claude_md_prohibition",
    "workflow_md": "workflow_md_rule",
    "brand_md": "brand_md_entry",
}

_ARCHIVE_EMPTY = {
    "schema_version": "0.2",
    "description": "Dialog hardening archive (v4.67+、queue path 已退役).",
    "items": [],
}


def _archive_json(operator=None):
    return _cfg.get_operator_paths(operator)["data_dir"] / "hardening-archive.json"


def _load_archive_payload(operator=None):
    payload = load_json(_archive_json(operator), deepcopy(_ARCHIVE_EMPTY), label="hardening-archive")
    if not isinstance(payload.get("items"), list):
        payload["items"] = []
    payload["schema_version"] = str(payload.get("schema_version") or _ARCHIVE_EMPTY["schema_version"])
    payload["description"] = payload.get("description") or _ARCHIVE_EMPTY["description"]
    return payload


def _save_archive_payload(operator, payload):
    save_json(_archive_json(operator), payload, update_meta=False)


def harden_from_dialog(operator, lesson_id, path, draft_content, archive=True):
    """Dialog-time hardening（/harden skill 的主要執行 API）.

    Args:
        operator: operator name（e.g. "kai"）
        lesson_id: "L-XXXX"、必須存在且 stage="soft"
        path: one of "test" / "lint" / "claude_md" / "workflow_md" / "brand_md"
        draft_content: concrete artifact content
        archive: if True, 記錄到 hardening-archive.json 供稽核

    Returns:
        dict with keys:
          status: "executed" | "failed" | "not_found" | "invalid_state" | "invalid_path"
          message: str
          target: file path on disk (if any)
          lesson_stage_after: "soft" | "hardened"
    """
    from . import lessons as _lessons

    if path not in _DIALOG_PATHS:
        return {
            "status": "invalid_path",
            "message": f"path must be one of {sorted(_DIALOG_PATHS)}",
        }

    rows = _lessons.load_lessons(operator)
    lesson = next((r for r in rows if r.get("id") == lesson_id), None)
    if not lesson:
        return {"status": "not_found", "message": f"lesson not found: {lesson_id}"}
    if lesson.get("stage") != "soft":
        return {
            "status": "invalid_state",
            "message": f"{lesson_id} stage={lesson.get('stage')}, must be 'soft' to harden",
        }

    action_type = _DIALOG_PATHS[path]
    target = None
    try:
        if action_type == "test_skeleton":
            target = _exec_test_skeleton(lesson_id, draft_content)
        elif action_type == "lint_rule":
            target = _exec_lint_rule(draft_content)
        elif action_type in ("claude_md_prohibition", "workflow_md_rule", "brand_md_entry"):
            target = _dialog_exec_protected_md(action_type, draft_content)
        else:
            return {"status": "invalid_path", "message": f"unsupported action_type: {action_type}"}

        _validate_after_execute(action_type, target_path=target)
    except Exception as exc:
        return {
            "status": "failed",
            "message": f"{action_type} execute or validate failed: {exc}",
            "target": target,
            "lesson_stage_after": lesson.get("stage"),
        }

    _lessons.promote_stage(operator, lesson_id, "hardened")

    if archive:
        _record_dialog_archive(
            operator,
            lesson_id=lesson_id,
            action_type=action_type,
            path=path,
            target=target,
        )

    return {
        "status": "executed",
        "message": f"✅ hardened {lesson_id} via {path} → {target}",
        "target": target,
        "lesson_stage_after": "hardened",
    }


# ─────────────────────────────────────────────────────────────
# Writers（原 hardening_executor.py 的內部邏輯、v4.67 併入此檔）
# ─────────────────────────────────────────────────────────────


def _write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _exec_test_skeleton(lesson_id, content):
    from pathlib import Path
    target = _cfg.PROJECT_ROOT / "tests" / f"test_lesson_{lesson_id}.py"
    _write_file(Path(target), content or "")
    return str(target)


def _exec_lint_rule(content):
    target = _cfg.PROJECT_ROOT / "scripts" / "lint" / "rules-lint.py"
    body = (content or "").rstrip() + "\n"
    existing = target.read_text(encoding="utf-8")
    if body.strip() and body.strip() in existing:
        return str(target)
    with target.open("a", encoding="utf-8") as f:
        f.write("\n" + body)
    return str(target)


def _dialog_exec_protected_md(action_type, draft_content):
    """Append draft to CLAUDE.md / workflow.md / brand.md（繞 Edit deny）."""
    if action_type == "claude_md_prohibition":
        target = _cfg.PROJECT_ROOT / "CLAUDE.md"
    elif action_type == "workflow_md_rule":
        target = _cfg.PROJECT_ROOT / ".claude" / "rules" / "workflow.md"
    elif action_type == "brand_md_entry":
        target = _cfg.PROJECT_ROOT / "01-data-brain" / "brand.md"
    else:
        raise ValueError(f"unsupported protected-md action_type: {action_type}")

    if not target.exists():
        raise RuntimeError(f"target not found: {target}")

    body = (draft_content or "").rstrip()
    if not body:
        raise ValueError("draft_content is empty")

    existing = target.read_text(encoding="utf-8")
    if body in existing:
        return str(target)
    with target.open("a", encoding="utf-8") as f:
        f.write("\n" + body + "\n")
    return str(target)


# ─────────────────────────────────────────────────────────────
# Validators（原 hardening_executor._validate_after_execute、v4.67 併入）
# ─────────────────────────────────────────────────────────────


def _validate_after_execute(action_type, target_path=None):
    import subprocess
    import sys

    if action_type == "test_skeleton":
        if not target_path:
            raise RuntimeError("missing test target path for validator")
        cmd = [sys.executable, "-m", "pytest", target_path]
    elif action_type == "lint_rule":
        cmd = [sys.executable, "scripts/lint/rules-lint.py", "--ci"]
    elif action_type in ("claude_md_prohibition", "workflow_md_rule", "brand_md_entry"):
        cmd = [sys.executable, "scripts/lint/rules-lint.py", "--ci"]
    else:
        return

    res = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=str(_cfg.PROJECT_ROOT))
    if res.returncode != 0:
        stderr = (res.stderr or "").strip()
        stdout = (res.stdout or "").strip()
        detail = stderr or stdout or f"validator failed ({res.returncode})"
        raise RuntimeError(detail)


# ─────────────────────────────────────────────────────────────
# Archive 稽核記錄
# ─────────────────────────────────────────────────────────────


def _record_dialog_archive(operator, lesson_id, action_type, path, target):
    archive_payload = _load_archive_payload(operator)
    archive_payload["items"].append(
        {
            "source": "dialog",
            "lesson_id": lesson_id,
            "action_type": action_type,
            "dialog_path": path,
            "target": target,
            "hardened_at": today_str(),
        }
    )
    _save_archive_payload(operator, archive_payload)
