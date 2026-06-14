"""Performance injection helpers: aggregate context + similar cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(REPO_ROOT))
from lessons_retrieval import get_similar_vids

from scripts.ops.lib.config import get_operator_paths


def _resolve_patterns_path(operator: str | None = None, path: Path | None = None) -> Path:
    if path is not None:
        return path
    return get_operator_paths(operator)["performance_patterns_json"]


def load_aggregate_context(path: Path | None = None, operator: str | None = None) -> dict[str, Any]:
    path = _resolve_patterns_path(operator, path)
    if not path.exists():
        return {"proven_openings": [], "proven_ctas": [], "risk_patterns": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "proven_openings": payload.get("proven_openings", []),
        "proven_ctas": payload.get("proven_ctas", []),
        "risk_patterns": payload.get("risk_patterns", []),
    }


def get_similar_cases(vid: str, n: int = 5, operator: str | None = None) -> list[dict[str, Any]]:
    return get_similar_vids(
        vid=vid,
        limit=n,
        include_fields=["hook_type", "verifier_scores", "actual_views", "deviation_score"],
        operator=operator,
    )


def build_injection_payload(vid: str, n: int = 5, operator: str | None = None) -> dict[str, Any]:
    return {
        "aggregate_background": load_aggregate_context(operator=operator),
        "similar_cases_foreground": get_similar_cases(vid, n=n, operator=operator),
    }
