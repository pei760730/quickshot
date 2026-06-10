#!/usr/bin/env bash
# Codex Cloud sandbox init script
# 平台側設定方式見 docs/references/codex-sandbox-setup.md。
# 在 Codex Cloud environment 的 setup script 欄位填：bash scripts/codex/setup.sh
# 需要的 secret：GITHUB_TOKEN（fine-grained PAT、Contents + Pull requests 讀寫）
set -euo pipefail

echo "── quickshot Codex sandbox setup ──"

# 1. Python 依賴（lint + pytest、與 CI 對齊）
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements-dev.txt
echo "✓ Python deps installed ($(python --version 2>&1))"

# 2. git 身份（commit 需要、與 territory 規範一致：Codex 的 PR 用 codex/ 前綴）
git config --global user.name "codex-agent"
git config --global user.email "codex-agent@users.noreply.github.com"
echo "✓ git identity set"

# 3. GitHub 認證 — 讓 Codex 能自己 push / 開 PR / close PR
#    GITHUB_TOKEN 由 Codex Cloud environment secret 注入、不寫進 repo
if [ -n "${GITHUB_TOKEN:-}" ]; then
  git config --global credential.helper \
    '!f() { echo "username=x-access-token"; echo "password=${GITHUB_TOKEN}"; }; f'
  # gh CLI 若存在、同一 token 直接可用（gh 原生讀 GITHUB_TOKEN env）
  if command -v gh >/dev/null 2>&1; then
    echo "✓ gh CLI present — GITHUB_TOKEN env 直接生效"
  fi
  echo "✓ git push auth configured (x-access-token)"
else
  echo "⚠ GITHUB_TOKEN 未設定 — Codex 只能改檔、不能 push / 管 PR"
  echo "  → 到 Codex Cloud environment 加 secret，步驟見 docs/references/codex-sandbox-setup.md"
fi

# 4. 自驗：lint + 測試跑得動（sandbox 內 fail-fast、別等派工後才發現環境壞）
python scripts/lint/rules-lint.py
python -m pytest tests/ -q --no-header -x
echo "── setup 完成 ──"
