# AI System Upgrade Report

> Sleep Mode v3.0 第三輪、未 commit / 未 push。
> 前兩輪（branch `lWYux` PR #10、branch `SPsEh` PR #15、`Ixmsj` PR #16）已 merge 進 main。
> 本輪在乾淨 branch `claude/sweet-dirac-zj0vv`（基於 HEAD `94f3f0f`）上續做。

## Base

- Branch: `claude/sweet-dirac-zj0vv`
- HEAD before changes: `94f3f0f` (`data: sync 1 file(s) from claude/code-review-high-Ixmsj [skip ci]`)
- HEAD after changes: `94f3f0f`（無 commit）
- Repo root: `/home/user/quickshot`
- Time: 2026-05-24
- Working tree before changes: clean
- Working tree after changes: 2 files modified（皆未 commit）

## Project snapshot

- Project type: AI 驅動的短影音生產 template（KaiOS-ContentSystem 短期客戶 ≤30 天精簡版）
- Primary language: Python 3.11
- Package manager: pip + `requirements-dev.txt`（`pytest>=8.0` / `ruff>=0.5`）
- Main entrypoints:
  - `scripts/ops/video-ops.py`（ops CLI、所有狀態寫入唯一入口、v7.0）
  - `scripts/lint/rules-lint.py` / `brand_ref_lint.py`（lint；rules-lint 內部再呼 `skill-io-lint.py`）
  - `scripts/utils/sync-to-sheets.py`（GH Action 觸發、人工不直接跑）
  - Claude Code slash commands `/init` `/check` `/scan` `/harden`
- Automation:
  - `.github/workflows/rules-lint.yml`（ruff + rules-lint + brand-ref + pytest + validate-all、每 PR / push 跑）
  - `.github/workflows/sync-to-sheets.yml`（push 到 main / claude/* 自動 sync、有 credential 缺失的 graceful skip）
  - `.github/workflows/wipe-client.yml`（manual dispatch）
  - `.githooks/pre-commit`（本機 territory check）+ `.pre-commit-config.yaml`（opt-in）
  - `.claude/hooks/{session-start,post-tool-use,stop}.sh`
- Validation commands available: `pytest tests/` / `ruff check --select E9,F63,F7,F82 scripts tests` / `python scripts/lint/rules-lint.py --ci` / `python scripts/lint/brand_ref_lint.py` / `python scripts/ops/video-ops.py validate-all` / `python -m compileall scripts`
- AI instruction files: `CLAUDE.md` / `CLAUDE.local.md` / `.claude/rules/{workflow.md,permissions.md}` / `.claude/skills/*.md` / `.claude/commands/*.md`
- High-risk areas（deny list、本輪不動）: `.claude/**` / `CLAUDE.md`

## What I inspected

- Git state + branch + remote + last 10 commits（前兩輪 PR #10–#16 已 merge）
- 218 tracked files、目錄結構
- 全套驗證基線（改動前）：pytest 542 passed / 1 skipped、ruff critical clean、rules-lint `--ci` 0、brand-ref lint 0、validate-all 0 errors / 0 drift、compileall scripts clean、4 個 hook `bash -n` OK
- 跨 repo grep 死引用：legacy 單檔 `pipeline.json`、`engine-manifest`、`sync-engine`、`00-control-center`、`interview-bank`、`dashboard/`、`AGENTS.md` / `HOME.md`
- CLI 真實子命令 vs 文件宣稱的命令（`video-ops.py` 全 subcommand 探測）
- `.github/workflows/*.yml` env 檢查 / 失敗遮蔽 / `set -e` 覆蓋
- `scripts/` 內 hardcoded 絕對路徑
- 文件引用的 script 路徑是否存在
- `.gitignore` 是否確實阻擋 legacy `pipeline.json`
- 額外 lint（`ai_patterns_lint.py` / `skill-io-lint.py`）的 wiring

## System-level issues found

### High risk

無。基線乾淨，無資料毀損 / 流程中斷風險。前兩輪已清掉大部分結構債。

### Medium risk

無新增。前兩輪已對齊 canonical-registry 禁令數 + pipeline SSoT 描述、README skill 計數。

### Low risk

**L1.（已修）`README.md` 核心架構樹仍畫 legacy 單檔 `pipeline.json`**
- README L52 架構圖把 `data/{operator}/pipeline.json # 狀態 SSoT` 畫成單一檔案。
- 實際 SSoT 是 sharded：`data/{operator}/pipeline/_meta.json` + `pipeline/items/*.json`（pipeline-schema v2.1+、`.gitignore` 主動防誤建單檔）。
- 前兩輪修了 `03-production-line/{README,03-done/README}.md` 的 pipeline 路徑、但**漏了 root README 這張架構樹**（它是新維護者 / 未來 AI 第一個讀的結構真相圖）。
- 影響：新人 / AI 讀此樹會以為該手建 / 手改 `pipeline.json` 單檔。
- 已修：樹節點改 `pipeline/` + 內聯註指向 pipeline-schema.md、標明 legacy 單檔已退役。同步 bump README `last_updated` 2026-05-17 → 2026-05-24。

**L2.（已修）`requirements-dev.txt` 內含指向不存在檔案的維護指示**
- L9：`# Track new file in 'engine-manifest.json' internal_files when adding new SSoT files.`
- `engine-manifest.json` 是 KaiOS 主引擎的檔、未 port 進 quickshot（`git grep` 證實本 repo 無此檔、僅 changelog 歷史 + `.githooks` 白名單死條目提及）。
- 影響：維護者新增 SSoT 依賴時、照此指示會去找一個不存在的檔。
- 已修：改為一行說明「短期客戶 template 無 engine-manifest.json、該 KaiOS 追蹤檔未 port」。

## Changes made

| 檔 | 變更 | 風險 |
|----|------|------|
| `README.md` | L52 架構樹 `pipeline.json` → `pipeline/`（sharded、附 schema cross-ref + legacy 退役註）；`last_updated` bump | 純文字 |
| `requirements-dev.txt` | L9 stale `engine-manifest.json` 維護指示 → quickshot 現況說明 | 純註解 |

## Files changed

```
 README.md            | 4 ++--
 requirements-dev.txt | 2 +-
 2 files changed, 3 insertions(+), 3 deletions(-)
```

## Verification run

| Check | Command | Result | Notes |
|---|---|---|---|
| pytest | `python -m pytest tests/ -q` | 542 passed / 1 skipped | 改動前後一致 |
| ruff critical | `ruff check --select E9,F63,F7,F82 scripts tests` | All checks passed | |
| rules-lint CI | `python scripts/lint/rules-lint.py --ci` | 0 issues | 含 version / date 一致性檢查 |
| brand-ref lint | `python scripts/lint/brand_ref_lint.py` | 0 issues | |
| validate-all | `python scripts/ops/video-ops.py validate-all` | 0 errors / 0 warnings | Schema drift 0/0/0 |
| compile scripts | `python -m compileall scripts -q` | exit 0 | |
| hook syntax | `bash -n` × 3 hook + `.githooks/pre-commit` | OK（基線、本輪未改 hook）| |

## Issues fixed

- L1：`README.md` 架構樹 pipeline 路徑對齊 sharded 現實（前兩輪漏修的最後一處架構圖）
- L2：`requirements-dev.txt` 移除指向不存在 `engine-manifest.json` 的維護指示

## Existing issues not fixed

- **受 deny list 保護、本輪不動（需 Kai 顯式授權）**：
  - `CLAUDE.md` L62：仍寫 `data/{operator}/pipeline.json`（legacy 單檔路徑、概念名）。多數 CLAUDE.md / workflow.md 內 `pipeline.json` 是「狀態 SSoT 概念名」、語意上不算錯；但 L62 資料地圖那行寫成具體檔路徑、與 sharded 現實有出入。
  - `.claude/rules/workflow.md` L484：`週報` → `weekly-report` 命令映射，但 `video-ops.py` **無 `weekly-report` 子命令**（CLI 僅有 `pipeline-stats` / `adoption-stats`）。屬死命令參考、但檔受保護。`docs/contracts/video-ops-cli.md`（非保護）已正確、未列此死命令。
- **死碼但保守保留（前兩輪已評估、刪除屬破壞性、留給 Kai 決定）**：
  - `tests/path_bootstrap.py` 的 `ENGINE_LIB_ROOT` + `bootstrap_engine_test_sys_path()`：KaiOS 引擎 lineage、無測試使用。
  - `tests/fixtures/engine-versioning-rules.json`：孤立 fixture、無 test / script 引用。
  - `.githooks/pre-commit` 白名單含 KaiOS-only 路徑（`engine-manifest.json` / `00-control-center/` / `dashboard/` / `HOME.md` / `AGENTS.md`）：屬寬鬆白名單死條目、不影響功能；移除會改動 commit-gating 行為、保守不碰。

## Remaining risks

1. **CLAUDE.md L62 legacy `pipeline.json` 路徑**（deny-protected）：Kai 在線時可一次到底改該行 + bump `last_updated`。修動 1 行、純文字。
2. **workflow.md `週報` → `weekly-report` 死命令**（deny-protected）：要嘛在 CLI 補 `weekly-report`（向後相容 alias 到 report 邏輯）、要嘛把 workflow.md 那行改成既有的 `pipeline-stats` / `adoption-stats`。兩者皆需 Kai 授權（CLI 改動非 deny、但 workflow.md 改動受 deny）。
3. **KaiOS lineage 死碼三處**（path_bootstrap helper / engine-versioning fixture / pre-commit 白名單條目）：可刪不刪、不影響運作；若確定 quickshot 永不借屍還魂 KaiOS engine 機制、可由 Kai 確認後一輪清掉。

## Branch cleanup candidates

### Possibly safe to delete after human review

（未檢視 `git branch -r` / remote 狀態，保守不列）

### Do not delete yet

- 當前 branch `claude/sweet-dirac-zj0vv`（本輪 2 個未 commit 修改在這）
- 其他 `claude/*` 分支 — 未檢視，保守保留

## Recommended next actions

1. **Kai 檢視本檔 + 2 個 staged 修改、決定是否 commit**。建議 commit message：`docs: 修 README 架構樹 pipeline sharded 路徑 + requirements-dev 過時 engine-manifest 指示`
2. **可選 Kai 一次到底（受 deny、需授權）**：CLAUDE.md L62 legacy `pipeline.json` → `pipeline/`；workflow.md `週報` 死命令二選一處理。
3. **下一輪可探（需 Kai 確認、屬破壞性）**：清掉三處 KaiOS lineage 死碼。

## Safe to commit?

- **Yes**（前提：Kai 看過 diff 確認）
- 原因：
  - 2 檔皆純文字 / 註解校正、無 schema / 邏輯 / API 改動
  - 完整驗證鏈通過（pytest 542 / 全 lint 0 / validate-all 0 drift / ruff 0 / compileall clean）
  - 改動目的單一：把已知對應現實的描述對齊現實、降低未來 AI / 維護者誤判
- Conditions before commit:
  - 確認 README sharded 描述語義是 Kai 想呈現的（已 cross-ref pipeline-schema.md、不留懸空名詞）

## 重要提醒

- 沒有 commit
- 沒有 push
- 沒有開 branch（已在指定 branch `claude/sweet-dirac-zj0vv` 工作）
- 沒有開 PR
- 沒有刪除任何檔案
- 沒有改任何 deny list 路徑下檔案
