#!/usr/bin/env bash
# bootstrap-client.sh — 初始化（或新增）operator
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "用法：bash scripts/bootstrap/bootstrap-client.sh <operator_name> <brand_name>"
  exit 1
fi

OPERATOR="$1"
BRAND="$2"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

mkdir -p "data/$OPERATOR"
mkdir -p "03-production-line/02-ready-to-shoot/$OPERATOR"
mkdir -p "03-production-line/03-done/$OPERATOR"

copy_if_missing() {
  local src="$1"
  local dst="$2"
  if [[ -f "$dst" ]]; then
    echo "⚠️ 已存在，跳過：$dst"
    return
  fi
  cp "$src" "$dst"
}

copy_if_missing "data/template/pipeline.json" "data/$OPERATOR/pipeline.json"
mkdir -p "data/$OPERATOR/pipeline/items"
copy_if_missing "data/template/pipeline/_meta.json" "data/$OPERATOR/pipeline/_meta.json"
copy_if_missing "data/template/todos.json" "data/$OPERATOR/todos.json"
copy_if_missing "data/template/lessons.json" "data/$OPERATOR/lessons.json"
copy_if_missing "data/template/performance-patterns.json" "data/$OPERATOR/performance-patterns.json"
copy_if_missing "data/template/hardening-archive.json" "data/$OPERATOR/hardening-archive.json"
copy_if_missing "data/template/brand-monitor.json"   "data/$OPERATOR/brand-monitor.json"
copy_if_missing "data/template/social-followers.json" "data/$OPERATOR/social-followers.json"
copy_if_missing "data/template/topic-history.json"   "data/$OPERATOR/topic-history.json"

if [[ -d "01-data-brain/template" ]]; then
  copy_if_missing "01-data-brain/template/brand.md" "01-data-brain/brand.md"
  copy_if_missing "01-data-brain/template/cases.md" "01-data-brain/cases.md"
fi

python3 scripts/bootstrap/reset-operator.py \
  --operator "$OPERATOR" \
  --brand "$BRAND" \
  --init-date "$(date +%Y-%m-%d)"

# Engine remote setup（Patched 補強 2：加完順手 fetch 一次）
if git rev-parse --is-inside-work-tree >/dev/null 2>&1 && \
   ! git remote get-url engine >/dev/null 2>&1; then
  git remote add engine https://github.com/pei760730/KaiOS-ContentSystem.git
  git fetch engine main -q 2>/dev/null && \
    echo "✓ engine remote 已接上 KaiOS-ContentSystem + 初次 fetch 完成" || \
    echo "✓ engine remote 已接上 KaiOS-ContentSystem（初次 fetch 失敗、下次 session 自動重試）"
fi

echo "✅ operator=$OPERATOR bootstrap 完成、可用 video-ops.py --operator $OPERATOR 切換"
