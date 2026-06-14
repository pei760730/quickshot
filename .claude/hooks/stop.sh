#!/usr/bin/env bash
set -u

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
LOG_FILE="$PROJECT_DIR/data/.claude-hooks.log"
VIDEO_OPS="$PROJECT_DIR/scripts/ops/video-ops.py"
PYTHON_BIN="${PYTHON_BIN:-python3}"

log() {
  mkdir -p "$(dirname "$LOG_FILE")"
  printf '[%s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$1" >> "$LOG_FILE"
}

TRANSCRIPT="${CLAUDE_TRANSCRIPT:-${CLAUDE_LAST_ASSISTANT_MESSAGE:-}}"
if [ -z "$TRANSCRIPT" ] && [ -n "${1:-}" ] && [ -f "${1}" ]; then
  TRANSCRIPT="$(cat "$1")"
fi
if [ -z "$TRANSCRIPT" ]; then
  log "stop-hook: skip (empty transcript)"
  exit 0
fi

EXTRACTED_JSON="$($PYTHON_BIN - <<'PY' "$TRANSCRIPT"
import json, os, sys
from scripts.utils.lib.trace_extractor import extract_trace_payload, infer_vid
text = sys.argv[1]
payload = extract_trace_payload(text) or {}
vid = infer_vid(text, os.environ)
out = {"vid": vid, "payload": payload}
print(json.dumps(out, ensure_ascii=False))
PY
)"

VID="$($PYTHON_BIN -c 'import json,sys;print((json.loads(sys.argv[1]).get("vid") or ""))' "$EXTRACTED_JSON")"
if [ -z "$VID" ]; then
  log "stop-hook: skip (no VID)"
  exit 0
fi

HAS_SCORES="$($PYTHON_BIN -c 'import json,sys;print("1" if isinstance(json.loads(sys.argv[1]).get("payload",{}).get("verifier_scores"),dict) else "")' "$EXTRACTED_JSON")"

# v5.x「縮」：generation_trace 自動捕獲已移除（trace 30 天零消費、短期客戶不需自我進化 forensic）。
# 本 hook 只保留 verifier_scores 捕獲（每支品質回饋 → performance-patterns → 下一支更好）。
if [ -z "$HAS_SCORES" ]; then
  log "stop-hook: skip ($VID no scores)"
  exit 0
fi

SCORES_JSON="$($PYTHON_BIN -c 'import json,sys;print(json.dumps(json.loads(sys.argv[1])["payload"]["verifier_scores"], ensure_ascii=False))' "$EXTRACTED_JSON")"
printf '%s' "$SCORES_JSON" | "$PYTHON_BIN" "$VIDEO_OPS" record-verifier-scores "$VID" --from-stdin 1 >/dev/null 2>&1 || log "stop-hook: scores write failed for $VID"

log "stop-hook: done ($VID scores=$HAS_SCORES)"
exit 0
