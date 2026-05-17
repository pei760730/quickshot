#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.adoption_gate import collect_items, render_report
from scripts.ops.lib.config import DEFAULT_OPERATOR


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--operator", default=DEFAULT_OPERATOR)
    args = parser.parse_args()

    project = Path(args.project)
    items, auto_messages = collect_items(
        project=project,
        today=date.today(),
        dry_run=args.dry_run,
        operator=args.operator,
    )
    print(render_report(items, auto_messages, operator=args.operator))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
