#!/usr/bin/env bash
# PostToolUse hook — 自動格式化 Edit/Write/MultiEdit 後的檔案
#
# 對應 Boris team tip #9 / paddo.dev/blog/claude-code-team-tips：
# 「Edit 完跑 formatter、不靠 CI 才發現格式問題」
#
# 設計原則：
# - **永不 block**（任何錯誤 silent ignore、exit 0）
# - **idempotent**（多次跑不破壞）
# - **保守 scope**：只格式化 *.py 用 ruff format
#   .json / .md / .yml 暫不動（前者 video-ops.py CLI 管理、後兩者格式風險高）
# - 讀 stdin 解析 tool_input.file_path（Claude Code hook 標準）

set +e

input=$(cat)

file_path=$(echo "$input" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('file_path', ''))
except Exception:
    pass
")

[[ -z "$file_path" ]] && exit 0
[[ ! -f "$file_path" ]] && exit 0

case "$file_path" in
  *.py)
    if command -v ruff &>/dev/null; then
      ruff format "$file_path" >/dev/null 2>&1 || true
    fi
    ;;
esac

exit 0
