#!/bin/bash
# .claude/hooks/dashboard-rebuild.sh
# v1.0 (2026-04-27) — 智能 dashboard auto-rebuild
#
# 雙模呼叫：
#   PostToolUse mode（從 stdin 收 JSON）：
#     讀 tool_input.command、匹配 video-ops.py mutation verbs → 才 rebuild
#   SessionStart / 手動 mode（無 stdin / --check）：
#     直接 mtime 比對、落後就 rebuild
#
# 對應 CLAUDE.md 禁令 #11 hook 四階段：
#   1. 警告  → SessionStart 印「dashboard 已重新整理」（可選）
#   2. 自動修復 → 本 hook（mtime 落後就 rebuild）← 主軸
#   3. 通知  → rebuild 失敗寫入 state file + stderr
#   4. gate  → 不入 gate（dashboard 不該擋資料寫入）

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
DIST_DIR="$PROJECT_DIR/dashboard/dist"
DIST_DATA="$DIST_DIR/data.json"
LOCK_FILE="$DIST_DIR/.rebuild.lock"
STATE_FILE="$DIST_DIR/.rebuild-state.json"

mkdir -p "$DIST_DIR" 2>/dev/null

# ── 模式判斷 ─────────────────────────────────────────────
MODE="check"
if [ ! -t 0 ] && [ "${1:-}" != "--check" ]; then
    # 有 stdin、走 PostToolUse 路徑
    PAYLOAD="$(cat)"
    if [ -n "${PAYLOAD:-}" ]; then
        MODE="post-tool"
    fi
fi

# ── PostToolUse：解析 command、匹配 mutation verbs（含 --flag value 處理）──
if [ "$MODE" = "post-tool" ]; then
    IS_MUTATION="$(PAYLOAD_JSON="$PAYLOAD" python3 - <<'PYEOF' 2>/dev/null
import json, os, shlex, sys

MUTATION_VERBS = {
    "save", "backfill", "quick-add", "quick-shot",
    "set-hook-type", "record-verifier-scores",
    "add-idea", "confirm", "advance-status", "advance", "sync-online",
}
# todo / lessons 看二級子命令、避免 lessons stats / todo list 等唯讀觸發
SUB_MUTATION = {
    "todo": {"add", "close", "archive", "defer", "migrate", "complete", "reopen"},
    "lessons": {"add", "add-evidence"},
}
# video-ops.py 已知會吃值的全域旗標
FLAGS_WITH_VALUE = {"--operator", "-o", "--mode", "--type", "--config"}

try:
    payload = json.loads(os.environ.get("PAYLOAD_JSON", "") or "{}")
except Exception:
    print("0"); sys.exit(0)
cmd = (payload.get("tool_input") or {}).get("command", "") or ""
try:
    toks = shlex.split(cmd)
except ValueError:
    print("0"); sys.exit(0)

# 找 video-ops.py（容許全路徑前綴）
script_idx = None
for i, t in enumerate(toks):
    if t.endswith("video-ops.py"):
        script_idx = i
        break
if script_idx is None:
    print("0"); sys.exit(0)

# 跳過 video-ops.py 後的全域 flags + 它們的值
i = script_idx + 1
while i < len(toks):
    t = toks[i]
    if t.startswith("--") and "=" in t:
        i += 1
    elif t in FLAGS_WITH_VALUE:
        i += 2
    elif t.startswith("-"):
        i += 1
    else:
        break

verb = toks[i] if i < len(toks) else ""
sub  = toks[i + 1] if i + 1 < len(toks) else ""

is_mutation = False
if verb in SUB_MUTATION:
    is_mutation = sub in SUB_MUTATION[verb]
elif verb in MUTATION_VERBS:
    is_mutation = True

print("1" if is_mutation else "0")
PYEOF
)"
    if [ "${IS_MUTATION:-0}" != "1" ]; then
        exit 0
    fi
fi

# ── 智能 mtime short-circuit：dist 比所有 data 新 → 跳過 ──
NEWEST_DATA_MTIME=0
if [ -d "$PROJECT_DIR/data" ]; then
    NEWEST_DATA_MTIME="$(find "$PROJECT_DIR/data" -maxdepth 2 -name '*.json' -printf '%T@\n' 2>/dev/null \
        | sort -rn | head -1 | cut -d. -f1)"
    NEWEST_DATA_MTIME="${NEWEST_DATA_MTIME:-0}"
fi
DIST_MTIME=0
if [ -f "$DIST_DATA" ]; then
    DIST_MTIME="$(stat -c '%Y' "$DIST_DATA" 2>/dev/null || echo 0)"
fi

if [ "$DIST_MTIME" -ge "$NEWEST_DATA_MTIME" ] && [ "$DIST_MTIME" -gt 0 ]; then
    # dashboard 已是最新、跳過
    exit 0
fi

# ── 並行保護：拿 lock、拿不到代表已有 rebuild 跑、跳過 ──
exec 9>"$LOCK_FILE" 2>/dev/null || exit 0
if ! flock -n 9 2>/dev/null; then
    exit 0
fi

# ── 同步 rebuild（build.py 通常 < 1s、timeout 30s 保險）──
TMP_OUT="$(mktemp)"
trap 'rm -f "$TMP_OUT"' EXIT

if timeout 30 python3 "$PROJECT_DIR/dashboard/build.py" >"$TMP_OUT" 2>&1; then
    SUCCESS=1
else
    SUCCESS=0
fi

# ── 寫 state file（成功清失敗計數、失敗累積）──────────────
python3 - "$STATE_FILE" "$SUCCESS" "$TMP_OUT" "$MODE" <<'PYEOF' 2>/dev/null || true
import json, sys, datetime
from pathlib import Path
state_path = Path(sys.argv[1])
success = sys.argv[2] == "1"
tmp_out = Path(sys.argv[3])
mode = sys.argv[4]
state = {}
if state_path.exists():
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        state = {}
now = datetime.datetime.now().isoformat(timespec="seconds")
if success:
    state["consecutive_failures"] = 0
    state["last_success_at"] = now
    state["last_success_mode"] = mode
    state.pop("last_failure_output", None)
else:
    state["consecutive_failures"] = int(state.get("consecutive_failures", 0)) + 1
    state["last_failure_at"] = now
    state["last_failure_mode"] = mode
    out = ""
    try:
        out = tmp_out.read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass
    state["last_failure_output"] = out[-1000:]  # 最後 1000 char、避免膨脹
state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
PYEOF

if [ "$SUCCESS" = "0" ]; then
    # Stage 3: 通知（PostToolUse 走 stderr、SessionStart 也印 stderr 不影響注入）
    printf '⚠️ dashboard rebuild failed (見 dashboard/dist/.rebuild-state.json)\n' >&2
fi

# 永遠 exit 0、不擋 Claude / Kai 工作流
exit 0
