#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migrate data/<operator>/pipeline.json <-> data/<operator>/pipeline/ sharded files."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.ops.lib import config
from scripts.ops.lib.pipeline import load_pipeline, save_pipeline


def migrate(operator: str) -> None:
    config.set_operator(operator)
    data = load_pipeline()
    save_pipeline(data)
    print(f"✅ migrated to sharded: {config.PIPELINE_JSON.parent / 'pipeline'}")


def rollback(operator: str) -> None:
    config.set_operator(operator)
    root = config.PIPELINE_JSON.parent / "pipeline"
    if root.exists():
        shutil.rmtree(root)
    data = load_pipeline()
    from scripts.ops.lib.storage import save_json
    save_json(str(config.PIPELINE_JSON), data)
    print(f"✅ rolled back to legacy file: {config.PIPELINE_JSON}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--operator", default=config.DEFAULT_OPERATOR)
    ap.add_argument("--rollback", action="store_true")
    args = ap.parse_args()
    if args.rollback:
        rollback(args.operator)
    else:
        migrate(args.operator)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
