"""Extract trace payloads from assistant messages.

Strategy: strict. Partially valid fenced blocks are skipped entirely to avoid
silent data corruption in downstream aggregation.
Decision rationale: PR #369 Q1, 2026-04-29.

When trace extraction or VID inference cannot be completed, keep the current
silent-skip behavior (with hook logging handled externally) to avoid duplicate
noise; downstream stage-4 CLI gate will surface actionable reminders.
Decision rationale: PR #369 Q2, 2026-04-29.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
VID_RE = re.compile(r"\bVID-\d{3,}\b")
ADOPTION_STATS_DIR = Path("data/.adoption-stats")
VID_INFERENCE_LOG = ADOPTION_STATS_DIR / "vid_inference.jsonl"


def extract_trace_payload(text: str) -> dict[str, Any] | None:
    """Return first merged payload containing generation_trace/verifier_scores from fenced JSON blocks."""
    if not text:
        return None
    merged: dict[str, Any] = {}
    found = False
    for raw in FENCE_RE.findall(text):
        candidate = raw.strip()
        if not candidate:
            continue
        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        if isinstance(obj.get("generation_trace"), dict):
            merged["generation_trace"] = obj["generation_trace"]
            found = True
        if isinstance(obj.get("verifier_scores"), dict):
            merged["verifier_scores"] = obj["verifier_scores"]
            found = True
    return merged if found else None


def infer_vid(text: str, env: dict[str, str] | None = None) -> str | None:
    """Infer VID from env vars first, then transcript text."""
    env = env or {}
    for key in ("VID", "VIDEO_ID", "CLAUDE_VIDEO_ID", "TARGET_VID"):
        value = (env.get(key) or "").strip()
        if VID_RE.fullmatch(value):
            _record_vid_inference(text=text, vid_inferred=True)
            return value
    if not text:
        return None
    m = VID_RE.search(text)
    inferred = m.group(0) if m else None
    _record_vid_inference(text=text, vid_inferred=bool(inferred))
    return inferred


def _record_vid_inference(text: str, vid_inferred: bool) -> None:
    had_fenced = bool(FENCE_RE.search(text or ""))
    if not had_fenced:
        return
    ADOPTION_STATS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "had_fenced": True,
        "vid_inferred": bool(vid_inferred),
    }
    with VID_INFERENCE_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
