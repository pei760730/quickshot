#!/usr/bin/env python3
"""Retrieve similar historical VIDs by deterministic weighted similarity."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.ops.lib.config import DEFAULT_OPERATOR, get_operator_paths
from scripts.ops.lib.pipeline import get_pipeline_data


def _resolve_pipeline_path(operator: str | None = None, pipeline_path: Path | None = None) -> Path:
    if pipeline_path is not None:
        return pipeline_path
    return get_operator_paths(operator)["pipeline_json"]


def _parse_date(raw: Any) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def _split_tags(item: dict[str, Any]) -> set[str]:
    raw = item.get("tags") or item.get("topic_tags") or ""
    if isinstance(raw, list):
        return {str(x).strip() for x in raw if str(x).strip()}
    return {x.strip() for x in str(raw).replace("，", " ").split() if x.strip()}


def _performance_tier(item: dict[str, Any]) -> str:
    perf = (item.get("backfill") or {}).get("performance")
    if perf in {"high", "normal", "low"}:
        return perf
    return "unknown"


def _time_key(item: dict[str, Any]) -> date:
    for k in ("publish_date", "save_date", "created_date"):
        d = _parse_date(item.get(k))
        if d:
            return d
    return date(1970, 1, 1)


def _time_decay_score(target_date: date, candidate_date: date) -> float:
    gap = abs((target_date - candidate_date).days)
    # Simple linear decay across one year.
    return max(0.0, 1.0 - min(gap, 365) / 365)


def score_similarity(target: dict[str, Any], candidate: dict[str, Any]) -> float:
    target_tags = _split_tags(target)
    cand_tags = _split_tags(candidate)
    union = target_tags | cand_tags
    overlap = 0.0 if not union else len(target_tags & cand_tags) / len(union)

    tier_score = 1.0 if _performance_tier(target) == _performance_tier(candidate) else 0.0

    time_score = _time_decay_score(_time_key(target), _time_key(candidate))
    return overlap * 0.5 + tier_score * 0.3 + time_score * 0.2


def get_similar_vids(
    vid: str,
    limit: int = 5,
    include_fields: list[str] | None = None,
    pipeline_path: Path | None = None,
    operator: str | None = None,
) -> list[dict[str, Any]]:
    pipeline_path = _resolve_pipeline_path(operator, pipeline_path)
    payload = get_pipeline_data(pipeline_json=pipeline_path)
    if payload is None:
        raise FileNotFoundError(f"pipeline shard not found for {pipeline_path}")
    items = [it for it in payload.get("items", []) if it.get("vid")]
    target = next((it for it in items if it.get("vid") == vid), None)
    if target is None:
        raise ValueError(f"VID not found: {vid}")

    include_fields = include_fields or ["hook_type", "verifier_scores", "actual_views", "deviation_score"]
    scored = []
    for row in items:
        if row.get("vid") == vid:
            continue
        backfill = row.get("backfill") or {}
        scored.append((score_similarity(target, row), row, backfill))

    scored.sort(key=lambda x: (x[0], _time_key(x[1])), reverse=True)

    output = []
    for score, row, backfill in scored[:limit]:
        record: dict[str, Any] = {
            "vid": row.get("vid"),
            "similarity_score": round(score, 4),
            "topic_tags": sorted(_split_tags(row)),
            "performance_tier": _performance_tier(row),
        }
        for field in include_fields:
            if field == "actual_views":
                record[field] = backfill.get("views")
            elif field == "deviation_score":
                record[field] = (row.get("deviation") or {}).get("score")
            elif field == "verifier_scores":
                record[field] = row.get("verifier_scores")
            else:
                record[field] = row.get(field)
        output.append(record)
    return output


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Lessons retrieval CLI")
    sub = p.add_subparsers(dest="command")
    s = sub.add_parser("similar-vids")
    s.add_argument("vid")
    s.add_argument("--by", default="topic_tags")
    s.add_argument("--limit", type=int, default=5)
    s.add_argument("--include-fields", default="hook_type,verifier_scores,actual_views,deviation_score")
    s.add_argument("--output", choices=["json"], default="json")
    s.add_argument("--operator", default=DEFAULT_OPERATOR)
    return p


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command != "similar-vids":
        parser.print_help()
        return 1
    include_fields = [x.strip() for x in args.include_fields.split(",") if x.strip()]
    rows = get_similar_vids(args.vid, limit=args.limit, include_fields=include_fields, operator=args.operator)
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
