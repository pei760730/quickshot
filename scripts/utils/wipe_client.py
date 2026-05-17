#!/usr/bin/env python3
"""Wipe client data — short-term template reset.

Clears person-being-filmed data (brand brain, scripts, identity) but preserves
engine-layer learning (hardening-archive, filtered lessons.json).

Usage:
    python scripts/utils/wipe_client.py <operator> [--dry-run] [--output-json PATH]

Called from .github/workflows/wipe-client.yml.
"""

import argparse
import datetime
import json
import re
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Brand brain files reset from 01-data-brain/template/
BRAIN_RESET_FROM_TEMPLATE = ["brand.md", "cases.md"]

# Brand brain files deleted outright (no template, regenerated as needed)
BRAIN_DELETE = ["brand-summary.md", "interview-bank.md"]

# Brand brain dirs cleared (delete all contents, keep dir)
BRAIN_DIRS_CLEAR = ["transcripts"]

# Production line dirs cleared
PRODUCTION_DIRS_CLEAR = [
    "03-production-line/02-ready-to-shoot",
    "03-production-line/03-done",
]

# Root-level dirs deleted entirely (client-specific, regen on next client)
ROOT_DIRS_DELETE = ["00-control-center"]

# Per-operator data files reset from data/template/
PER_OP_RESET_FILES = [
    "pipeline.json",
    "todos.json",
    "performance-patterns.json",
    "brand-monitor.json",
    "social-followers.json",
    "topic-history.json",
]

# Per-operator dirs reset from data/template/<dir>
PER_OP_RESET_DIRS = ["pipeline"]


def load_operators(project_root):
    return json.loads(
        (project_root / "data" / ".operators.json").read_text(encoding="utf-8")
    )


def gather_files_to_clear(project_root, operator):
    """Return list of {path, size_bytes, action} dicts."""
    items = []

    def add_if_exists(rel, action):
        p = project_root / rel
        if p.is_file():
            items.append(
                {
                    "path": str(p.relative_to(project_root)),
                    "size_bytes": p.stat().st_size,
                    "action": action,
                }
            )

    def add_dir_files(rel, action):
        d = project_root / rel
        if d.is_dir():
            for f in sorted(d.rglob("*")):
                if f.is_file():
                    items.append(
                        {
                            "path": str(f.relative_to(project_root)),
                            "size_bytes": f.stat().st_size,
                            "action": action,
                        }
                    )

    for name in BRAIN_RESET_FROM_TEMPLATE:
        add_if_exists(f"01-data-brain/{name}", "reset-from-template")
    add_if_exists("CLAUDE.local.md", "reset-from-template")

    for name in BRAIN_DELETE:
        add_if_exists(f"01-data-brain/{name}", "delete")

    for d in BRAIN_DIRS_CLEAR:
        add_dir_files(f"01-data-brain/{d}", "delete")

    for d in PRODUCTION_DIRS_CLEAR:
        add_dir_files(d, "delete")

    for d in ROOT_DIRS_DELETE:
        add_dir_files(d, "delete")

    op_dir = project_root / "data" / operator
    if op_dir.is_dir():
        for fname in PER_OP_RESET_FILES:
            add_if_exists(f"data/{operator}/{fname}", "reset-from-template")
        for dname in PER_OP_RESET_DIRS:
            add_dir_files(f"data/{operator}/{dname}", "reset-from-template")

    return items


def filter_lessons(lessons_data, operator, brand_name):
    """Filter lessons.json in place. Returns (kept_count, dropped_entries)."""
    if not isinstance(lessons_data, dict) or "lessons" not in lessons_data:
        return 0, []

    keywords = [operator.lower()]
    if brand_name:
        keywords.append(brand_name.lower())

    kept = []
    dropped = []
    for lesson in lessons_data["lessons"]:
        if lesson.get("stage") != "hardened":
            dropped.append(
                {
                    "id": lesson.get("id"),
                    "reason": "stage != hardened",
                    "stage": lesson.get("stage"),
                }
            )
            continue

        text_blob = " ".join(
            str(lesson.get(k, "")) for k in ("pattern", "counter_pattern", "title")
        ).lower()
        matched = [kw for kw in keywords if kw and kw in text_blob]
        if matched:
            dropped.append(
                {
                    "id": lesson.get("id"),
                    "reason": f"text contains {matched}",
                }
            )
            continue

        kept.append(lesson)

    lessons_data["lessons"] = kept
    return len(kept), dropped


def get_archive_count(project_root, operator):
    p = project_root / "data" / operator / "hardening-archive.json"
    if not p.exists():
        return 0
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(d, list):
            return len(d)
        if isinstance(d, dict):
            for key in ("items", "entries", "records", "archive"):
                if isinstance(d.get(key), list):
                    return len(d[key])
    except Exception:
        return 0
    return 0


def append_changelog(project_root, report, tag):
    p = project_root / "07-changelog" / "CHANGELOG.md"
    if not p.exists():
        return

    op = report["operator"]
    date = datetime.date.today().isoformat()
    entry = f"""---

## wipe: {op} client ended ({date})

**主題：🧹 短期客戶 {op} 結束、repo 清回 template 狀態**

- 清掉檔案數：{report["total_files"]}（{report["total_size_bytes"]} bytes）
- 過濾 lessons：保 {report["lessons_filter"]["kept"]} / 砍 {len(report["lessons_filter"]["dropped_entries"])}
- 保留 hardening-archive entries：{report["preserved"]["hardening_archive_entries"]}

### 還原方式

```bash
git checkout {tag}
```

"""
    src = p.read_text(encoding="utf-8")
    # Insert before the first "---" separator (after intro block)
    new = re.sub(r"^---\n", entry + "---\n", src, count=1, flags=re.MULTILINE)
    p.write_text(new, encoding="utf-8")


def execute_wipe(project_root, operator, dry_run, tag=None):
    operators = load_operators(project_root)
    if operator not in operators.get("operators", {}):
        raise SystemExit(f"❌ Operator '{operator}' not found in data/.operators.json")

    op_meta = operators["operators"][operator]
    brand_name = op_meta.get("brand", "")

    files = gather_files_to_clear(project_root, operator)
    total_size = sum(f["size_bytes"] for f in files)

    lessons_path = project_root / "data" / operator / "lessons.json"
    lessons_preview = {"kept": 0, "dropped_entries": []}
    if lessons_path.exists():
        ld = json.loads(lessons_path.read_text(encoding="utf-8"))
        ld_copy = json.loads(json.dumps(ld))
        kept, dropped = filter_lessons(ld_copy, operator, brand_name)
        lessons_preview = {"kept": kept, "dropped_entries": dropped}

    archive_count = get_archive_count(project_root, operator)

    report = {
        "operator": operator,
        "brand": brand_name,
        "dry_run": dry_run,
        "files_to_clear": files,
        "total_files": len(files),
        "total_size_bytes": total_size,
        "lessons_filter": lessons_preview,
        "preserved": {
            "hardening_archive_entries": archive_count,
            "data_skill_memory": "untouched",
            "engine_layers": ".claude/, 02-skill-factory/, scripts/, docs/, tests/, .github/ — untouched",
        },
    }

    if dry_run:
        return report

    template_brain = project_root / "01-data-brain" / "template"
    template_data = project_root / "data" / "template"

    # 1. Reset brand brain files from template
    for name in BRAIN_RESET_FROM_TEMPLATE:
        src = template_brain / name
        dst = project_root / "01-data-brain" / name
        if src.exists():
            shutil.copy2(src, dst)

    # 2. Reset CLAUDE.local.md from template
    src = template_brain / "CLAUDE.local.md"
    if src.exists():
        shutil.copy2(src, project_root / "CLAUDE.local.md")

    # 3. Delete brand-summary / interview-bank
    for name in BRAIN_DELETE:
        p = project_root / "01-data-brain" / name
        if p.exists():
            p.unlink()

    # 4. Clear transcripts/
    for d in BRAIN_DIRS_CLEAR:
        dpath = project_root / "01-data-brain" / d
        if dpath.is_dir():
            for f in dpath.glob("*"):
                if f.is_file():
                    f.unlink()

    # 5. Clear production line
    for rel in PRODUCTION_DIRS_CLEAR:
        dpath = project_root / rel
        if dpath.is_dir():
            for f in dpath.rglob("*"):
                if f.is_file():
                    f.unlink()
            for sd in sorted(dpath.rglob("*"), reverse=True):
                if sd.is_dir() and not any(sd.iterdir()):
                    sd.rmdir()

    # 6. Delete root client-specific dirs
    for rel in ROOT_DIRS_DELETE:
        dpath = project_root / rel
        if dpath.is_dir():
            shutil.rmtree(dpath)

    # 7. Reset per-op data files
    op_dir = project_root / "data" / operator
    if op_dir.is_dir():
        for fname in PER_OP_RESET_FILES:
            src = template_data / fname
            dst = op_dir / fname
            if src.exists():
                shutil.copy2(src, dst)
        for dname in PER_OP_RESET_DIRS:
            src = template_data / dname
            dst = op_dir / dname
            if dst.exists():
                shutil.rmtree(dst)
            if src.exists():
                shutil.copytree(src, dst)

    # 8. Filter lessons.json in place
    if lessons_path.exists():
        ld = json.loads(lessons_path.read_text(encoding="utf-8"))
        filter_lessons(ld, operator, brand_name)
        lessons_path.write_text(
            json.dumps(ld, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    # 9. Remove operator from .operators.json
    operators["operators"].pop(operator, None)
    (project_root / "data" / ".operators.json").write_text(
        json.dumps(operators, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # 10. CHANGELOG entry (only if tag provided)
    if tag:
        append_changelog(project_root, report, tag)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Wipe client data for short-term template reset"
    )
    parser.add_argument(
        "operator", help="Operator name (must exist in data/.operators.json)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview only, no changes"
    )
    parser.add_argument("--output-json", help="Write report to this path")
    parser.add_argument("--tag", help="Backup git tag name (recorded in CHANGELOG)")
    args = parser.parse_args()

    report = execute_wipe(PROJECT_ROOT, args.operator, args.dry_run, tag=args.tag)

    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)

    if args.output_json:
        Path(args.output_json).write_text(output, encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
