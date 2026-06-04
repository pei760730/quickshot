#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot migration: reclassify backfill.performance using current thresholds.

預設 dry-run；加 --apply 才會寫回 pipeline.json。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lib.backfill import classify_performance


def _pipeline_paths(repo_root: Path) -> list[Path]:
    """v4.38：動態 iterate OPERATORS、不再硬寫 kai/ruby。"""
    import sys
    ops_lib_path = repo_root / "scripts" / "ops"
    if str(ops_lib_path) not in sys.path:
        sys.path.insert(0, str(ops_lib_path))
    from lib.config import OPERATORS  # noqa: E402
    paths = [cfg["data_dir"] / "pipeline.json" for cfg in OPERATORS.values()]
    return [p for p in paths if p.exists()]


def _classify_item(item: dict) -> tuple[str | None, str | None]:
    bf = item.get("backfill") or {}
    if not all(k in bf for k in ("views", "retention_3s", "completion_rate")):
        return None, None
    level, _path, _reason = classify_performance(
        bf.get("views", 0),
        bf.get("retention_3s", 0),
        bf.get("completion_rate", 0),
    )
    before = bf.get("performance")
    return before, level


def reclassify_pipeline(data: dict) -> tuple[list[dict], int, int]:
    items = data.get("items", [])
    changes: list[dict] = []
    eligible = 0
    low_count = 0
    for item in items:
        before, after = _classify_item(item)
        if after is None:
            continue
        eligible += 1
        bf = item.setdefault("backfill", {})
        if after == "low":
            low_count += 1
        if before != after:
            changes.append(
                {
                    "vid": item.get("vid", "<no-vid>"),
                    "before": before or "unset",
                    "after": after,
                    "retention_3s": bf.get("retention_3s"),
                    "completion_rate": bf.get("completion_rate"),
                }
            )
            bf["performance"] = after
        elif before is None:
            bf["performance"] = after
    return changes, eligible, low_count


def migrate_file(path: Path, apply: bool = False) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    changes, eligible, low_count = reclassify_pipeline(data)
    if apply and changes:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "path": path,
        "changes": changes,
        "eligible": eligible,
        "low_count": low_count,
    }


def main():
    # 強制 UTF-8 輸出：Windows / 非 UTF-8 locale 下，emoji 輸出被 pipe / 重導 / 捕捉時
    # 預設 locale codec（如 cp950）無法編碼 emoji → print 崩潰。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(
        description="Reclassify backfill.performance for all pipeline items using current thresholds."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Only print planned changes (default).")
    mode.add_argument("--apply", action="store_true", help="Write changes to pipeline.json files.")
    args = parser.parse_args()

    apply = args.apply
    repo_root = Path(__file__).resolve().parents[2]
    targets = _pipeline_paths(repo_root)
    if not targets:
        print("⚠️ No pipeline.json files found under any registered operator's data dir")
        return

    print("🔎 migrate_reclassify_performance")
    print(f"模式：{'APPLY' if apply else 'DRY-RUN'}")
    print()

    total_changes = 0
    for p in targets:
        result = migrate_file(p, apply=apply)
        rel = result["path"].relative_to(repo_root)
        print(f"━━ {rel} ━━")
        print(f"eligible: {result['eligible']} | low_count(after): {result['low_count']}")
        if result["changes"]:
            for ch in result["changes"]:
                print(
                    f"  {ch['vid']}: {ch['before']} -> {ch['after']} "
                    f"(retention={ch['retention_3s']}%, completion={ch['completion_rate']}%)"
                )
        else:
            print("  (no changes)")
        print()
        total_changes += len(result["changes"])

    print(f"總變更筆數：{total_changes}")
    if not apply:
        print("（未寫檔；加 --apply 才會套用）")


if __name__ == "__main__":
    main()
