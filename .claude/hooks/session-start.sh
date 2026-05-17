#!/bin/bash
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Dev deps SSoT — 從 requirements-dev.txt 安裝 pytest / ruff / 等
# 失敗不擋（離線 / 受限環境仍可進 session），CLAUDE.md 禁令 #5「改動自驗」前提
if [ -f "$PROJECT_DIR/requirements-dev.txt" ]; then
  pip install -q -r "$PROJECT_DIR/requirements-dev.txt" 2>/dev/null || true
fi

# Remote 環境（Claude Code on the web）才嘗試安裝 ffmpeg / faster-whisper
# 失敗時加 || true 避免 set -e 終止整個 hook
if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
  if ! command -v ffmpeg &>/dev/null; then
    (apt-get update -qq && apt-get install -y -qq ffmpeg) >/dev/null 2>&1 || true
  fi
  if ! python3 -c "import faster_whisper" 2>/dev/null; then
    pip install -q faster-whisper >/dev/null 2>&1 || true
  fi
fi

BRAND="$PROJECT_DIR/01-data-brain/brand.md"

if [ -f "$BRAND" ]; then
  echo "💡 brand.md 改 lazy load（v4.62 全文 auto-inject 退役、每 session 省 ~27k token）"
  echo "   → skill 跑時 brain_loader 自動載；對話需要時 Read 01-data-brain/brand.md"
fi

# ── Stage 2: dashboard 落後靜默 rebuild ──
# 成功不印（不打擾 Kai）；連續 3 次失敗才提示
if [ -x "$PROJECT_DIR/.claude/hooks/dashboard-rebuild.sh" ]; then
  bash "$PROJECT_DIR/.claude/hooks/dashboard-rebuild.sh" --check 2>/dev/null || true
  STATE_FILE="$PROJECT_DIR/dashboard/dist/.rebuild-state.json"
  if [ -f "$STATE_FILE" ]; then
    FAIL_COUNT=$(python3 -c "
import json
try:
    s = json.load(open('$STATE_FILE'))
    print(int(s.get('consecutive_failures', 0)))
except Exception:
    print(0)
" 2>/dev/null || echo 0)
    if [ "${FAIL_COUNT:-0}" -ge 3 ]; then
      echo ""
      echo "⚠️ dashboard rebuild 連續 ${FAIL_COUNT} 次失敗"
      echo "   → 看詳情：cat dashboard/dist/.rebuild-state.json"
      echo "   → 手動修：python3 dashboard/build.py"
    fi
  fi
fi
