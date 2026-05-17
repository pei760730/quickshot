"""Owner-splitting adoption gate scanner + auto-close stage."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from scripts.ops.lib.config import DEFAULT_OPERATOR, get_operator_paths
from scripts.engine import engine_lag_detector as eld
from scripts.ops.lib.pipeline import get_pipeline_data


def _get_section_owners(operator: str | None = None) -> dict[str, str]:
    owner = operator or DEFAULT_OPERATOR
    return {str(i): ("auto" if i in {1, 2, 3} else owner) for i in range(13)}


def _project_scoped_path(project: Path, path: Path) -> Path:
    try:
        return project / path.relative_to(REPO_ROOT)
    except ValueError:
        return path


@dataclass
class GateItem:
    code: str
    owner: str
    message: str
    kind: str = ""


def _parse_date(raw: Any) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None




def _parse_brand_sections(text: str) -> list[tuple[str, date]]:
    sections: list[tuple[str, date]] = []
    current_section: str | None = None
    for line in text.splitlines():
        section_match = re.match(r"^##\s*\[(\d+)\]", line.strip())
        if section_match:
            current_section = section_match.group(1)
            continue
        updated_match = re.search(r"last_updated:\s*(\d{4}-\d{2}-\d{2})", line)
        if not updated_match or not current_section:
            continue
        parsed = _parse_date(updated_match.group(1))
        if parsed:
            sections.append((current_section, parsed))
            current_section = None
    return sections


def _touch_brand_section_last_updated(text: str, section: str, today: date) -> tuple[str, bool]:
    pattern = re.compile(
        rf"(##\s*\[{re.escape(section)}\][\s\S]*?last_updated:\s*)(\d{{4}}-\d{{2}}-\d{{2}})",
        re.MULTILINE,
    )
    updated, count = pattern.subn(rf"\g<1>{today.isoformat()}", text, count=1)
    return updated, count > 0

def _todo_owner(todo: dict[str, Any], operator: str | None = None) -> str:
    tags = {str(t).strip().lower() for t in (todo.get("tags") or [])}
    meta = (todo.get("notes") or "").lower()
    title = (todo.get("title") or "").lower()
    if "auto" in tags or "auto-stage2" in tags:
        return "auto"
    if "employee" in tags or "ig" in tags or "對表" in title or "ig" in meta:
        return "employee"
    return operator or DEFAULT_OPERATOR


def _parse_defer_target_code(title: str) -> int | None:
    match = re.search(r"\bdefer:\s*T(\d+)\b", title, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def auto_close_todos(pipeline_items: list[dict[str, Any]], todos: list[dict[str, Any]], dry_run: bool) -> list[str]:
    by_vid = {i.get("vid"): i for i in pipeline_items if i.get("vid")}
    closed = []
    for item in todos:
        if item.get("state") != "pending":
            continue
        related = item.get("related_vid")
        if not related:
            continue
        v = by_vid.get(related)
        if not v:
            continue
        if v.get("status") != "已上線" or not v.get("backfill"):
            continue
        closed.append(item.get("id"))
        if not dry_run:
            item["state"] = "archived"
            item["closed_reason"] = "related VID backfilled"
            item["closed_at"] = date.today().isoformat()
    return closed


def collect_items(project: Path, today: date | None = None, dry_run: bool = False, operator: str | None = None) -> tuple[list[GateItem], list[str]]:
    today = today or date.today()
    operator = operator or DEFAULT_OPERATOR
    items: list[GateItem] = []
    auto_messages: list[str] = []

    paths = get_operator_paths(operator)
    pipe_path = _project_scoped_path(project, paths["pipeline"])
    todo_path = _project_scoped_path(project, paths["todos"])

    pipe_data = get_pipeline_data(pipeline_json=pipe_path)
    pipeline = pipe_data.get("items", []) if pipe_data else []
    todo_payload = json.loads(todo_path.read_text(encoding="utf-8")) if todo_path.exists() else {"todos": []}
    todos = todo_payload.get("todos", [])

    overdue = [
        it for it in pipeline
        if it.get("vid") and it.get("status") == "已上線" and not it.get("backfill") and (_parse_date(it.get("backfill_due_date")) or date.max) <= today
    ]
    for idx, row in enumerate(overdue[:5], start=1):
        items.append(GateItem(f"B{idx}", "employee", f"📊 {row['vid']} 回填到期"))

    auto_closed = auto_close_todos(pipeline, todos, dry_run=dry_run)
    for tid in auto_closed:
        auto_messages.append(f"✓ {tid} 自動關閉")
    if auto_closed and not dry_run:
        todo_path.write_text(json.dumps(todo_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    due_todos = []
    defer_suppressed_codes: set[int] = set()
    for row in todos:
        if row.get("state") != "pending":
            continue
        defer_target = _parse_defer_target_code(str(row.get("title") or ""))
        if defer_target is not None:
            defer_suppressed_codes.add(defer_target)
            continue  # marker 不進 due_todos、不論 due 是否過期
        due = _parse_date(row.get("due"))
        if due is None or due > today:
            continue
        due_todos.append(row)

    tcount = 0
    for idx, row in enumerate(due_todos, start=1):
        if idx in defer_suppressed_codes:
            continue
        tcount += 1
        if tcount > 5:
            break
        owner = _todo_owner(row, operator=operator)
        items.append(GateItem(f"T{tcount}", owner, f"📋 {row.get('title')}（{row.get('id')}）"))

    brand = project / "01-data-brain" / "brand.md"
    monitor_path = _project_scoped_path(project, paths["brand_monitor"])
    if brand.exists():
        text = brand.read_text(encoding="utf-8")
        sections = _parse_brand_sections(text)
        stale_sections = [(sec, (today - updated).days) for sec, updated in sections if (today - updated).days > 30]

        updated_text = text
        auto_touched: list[tuple[str, int]] = []
        auto_failed: list[tuple[str, int, str]] = []
        for sec, days in stale_sections:
            owner = _get_section_owners(operator).get(sec, "employee")
            if owner != "auto":
                items.append(GateItem(f"M{sec}", owner, f"🧠 brand [{sec}] {days} 天未更新（owner={owner}、需確認事實或明示無變動）"))
                continue
            if days < 30:
                continue
            if dry_run:
                auto_touched.append((sec, days))
                continue
            updated_text, ok = _touch_brand_section_last_updated(updated_text, sec, today)
            if ok:
                auto_touched.append((sec, days))
            else:
                auto_failed.append((sec, days, "找不到 last_updated 行"))

        if not dry_run and updated_text != text:
            brand.write_text(updated_text, encoding="utf-8")

        if auto_touched:
            existing = {"items": []}
            if monitor_path.exists():
                existing = json.loads(monitor_path.read_text(encoding="utf-8"))
                if not isinstance(existing, dict):
                    existing = {"items": []}
            monitor_items = existing.get("items")
            if not isinstance(monitor_items, list):
                monitor_items = []
            for sec, days in auto_touched:
                monitor_items.append({"section": sec, "days": days, "source": "auto", "touched_at": today.isoformat()})
                auto_messages.append(f"✓ brand [{sec}] 自動 touch（{days} 天）")
            existing["items"] = monitor_items
            if not dry_run:
                monitor_path.parent.mkdir(parents=True, exist_ok=True)
                monitor_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        for sec, days, reason in auto_failed:
            items.append(GateItem(f"M{sec}", "employee", f"📍 brand [{sec}] 章 {days} 天未更新（auto-touch 失敗：{reason}）"))

    _append_engine_lag_item(project, items)

    return items, auto_messages


def _append_engine_lag_item(project: Path, items: list[GateItem]) -> None:
    """Append engine-lag warning when engine/main is reachable and newer."""
    if not eld.fetch_engine_main(project):
        return

    local = eld.read_local_engine_version(project)
    remote = eld.read_remote_engine_version(project)
    if eld.compare_versions(local, remote) != "behind":
        return

    migration_count = eld.count_remote_schema_migrations(project, local or "", remote or "")
    message = f"🔄 engine 落後 v{local} → v{remote}"
    if migration_count > 0:
        message += f"（含 {migration_count} 個 🚨 schema-migration、需手動）"
    message += "（說「同步」拉）"
    items.append(GateItem("E0", "kai", message, kind="engine-lag"))


def render_report(items: list[GateItem], auto_messages: list[str], operator: str | None = None) -> str:
    operator = operator or DEFAULT_OPERATOR
    employees = [i for i in items if i.owner == "employee"]
    kai = [i for i in items if i.owner in {operator, "kai"}]
    out = ["⏰ 對話開頭檢查", "", "[員工待辦]（資訊、不擋）"]
    if employees:
        for i in employees:
            out.append(f"  {i.message}")
    else:
        out.append("  （目前無）")
    out.extend(["", "[Kai 決策]（待你回覆）"])
    if kai:
        for i in kai:
            out.append(f"  [{i.code}] {i.message}")
    else:
        out.append("  （目前無）")
    out.extend(["", "─── Adoption gate ───", f"{len(kai)} 項需決定（員工類不算）"])
    if auto_messages:
        out.append("")
        out.append("ℹ️ 自動修復")
        out.extend([f"  {m}" for m in auto_messages])
    return "\n".join(out)
