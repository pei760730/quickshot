# AI System Upgrade Report

> Sleep Mode v3.0 第二輪、未 commit / 未 push。
> 第一輪報告（branch `lWYux`、PR #10）已 merge、本輪在乾淨 `main` 基線上續做。

## Base

- Branch: `claude/repo-optimization-SPsEh`
- HEAD before changes: `b4af539` (`Merge pull request #14 from pei760730/claude/changelog-hygiene`)
- HEAD after changes: `b4af539`（無 commit）
- Repo root: `/home/user/quickshot`
- Time: 2026-05-19
- Working tree before: clean
- Working tree after: 7 files modified（皆未 commit）

## Project snapshot

- Project type: AI 驅動的短影音生產 template（KaiOS-ContentSystem 短期客戶 ≤30 天精簡版）
- Primary language: Python 3.11
- Package manager: pip + `requirements-dev.txt`
- Main entrypoints:
  - `scripts/ops/video-ops.py`（ops CLI、所有狀態寫入唯一入口）
  - `scripts/lint/rules-lint.py` / `brand_ref_lint.py`（lint）
  - `scripts/utils/sync-to-sheets.py`（GH Action 觸發、人工不直接跑）
  - Claude Code slash commands `/init` `/check` `/scan` `/harden`
- Automation:
  - `.github/workflows/rules-lint.yml`（lint + pytest + validate-all、每 PR 跑）
  - `.github/workflows/sync-to-sheets.yml`（push 到 main / claude/* 自動 sync）
  - `.github/workflows/wipe-client.yml`（manual dispatch、三層安全）
  - `.githooks/pre-commit`（本機 territory check，需 `git config core.hooksPath .githooks`）
  - `.pre-commit-config.yaml`（opt-in、跑 rules-lint + brand-ref lint）
  - `.claude/hooks/{session-start,post-tool-use,stop}.sh`
- Validation commands: `pytest tests/` / `ruff check --select E9,F63,F7,F82 scripts tests` / `python scripts/lint/rules-lint.py --ci` / `python scripts/lint/brand_ref_lint.py` / `python scripts/ops/video-ops.py validate-all`
- AI instruction files: `CLAUDE.md` / `CLAUDE.local.md` / `.claude/rules/{workflow.md,permissions.md}` / `.claude/skills/*.md` / `.claude/commands/*.md`
- High-risk areas: `.claude/**`（受保護、deny list、需 Kai 確認）/ `CLAUDE.md`（同）/ `data/{operator}/pipeline/` shards

## What I inspected

- Git state + branch + remote + last 10 commits（PR #10~#14 已 merge 進 main）
- 218 tracked files
- 全套驗證基線：`pytest` (543 passed / 1 skipped) / `ruff` critical / `rules-lint --ci` / `brand_ref_lint` / `validate-all` / `bash -n` × 4 hook + `.githooks/pre-commit` / `compileall scripts`
- 跨 repo grep 死引用：legacy `pipeline.json` 路徑、`/sync-engine` / `agent-collaboration` / `territory-lint` / `engine-manifest` / `00-control-center` / `interview-bank` / `00-control-center/todo` / `禁令 #11/#12/#13` / 各種「N 個 Skill」計數
- `scripts/lint/canonical-registry.json` 內所有欄位 vs 實際資料
- `01-data-brain/` 目錄結構 vs README 描述 vs index.md 資料地圖
- `.claude/skills/*.md` stub 一致性
- `tests/path_bootstrap.py` + `scripts/engine/` 是否仍被使用
- `scripts/ops/lib/health.py compute_transcripts_health()` 對缺檔的容錯
- `tests/fixtures/engine-versioning-rules.json` 是否仍被引用

## System-level issues found

### High risk

無。本輪基線已乾淨，無資料毀損 / 流程中斷風險。

### Medium risk

**M1. `scripts/lint/canonical-registry.json` 中 SSoT 描述 drift**
- 此檔是 rules-lint 的「合法值真相源」。兩處 drift：
  1. L14：`"系統總指南（7 條禁令 + 資料地圖）"` — CLAUDE.md 實為 9 條禁令（#1-#9）
  2. L48：`"pipeline": "data/{operator}/pipeline.json"` — legacy 單檔路徑已退役（pipeline-schema v2.1 / engine v5.97、`.gitignore` 防誤建）、實 SSoT 為 sharded `data/{operator}/pipeline/`
- 影響：未來 Claude / Kai 讀此檔當作「真相」、會把錯誤的禁令數 + 已退役路徑當有效資訊。
- 同時 bump `_version` 2.5 → 2.6、`_updated` 2026-04-25 → 2026-05-19。
- 已修。
- 行為層說明：grep 過 `scripts/lint/rules-lint.py`、`rules_files` 只用鍵、`ssot_files` 完全未被 lint 行為消費；改描述對行為 0 影響、純治理層誠實。

**M2. `README.md` skill 計數 drift**
- L58：`02-skill-factory/ # 8 個 Skill` — 實際只有 7 個（`ls -d 02-skill-factory/*/` 排除 shared-references 後得 7：discovery / distillation / generation / harden / orientation / quality / skill-creator）。
- `02-skill-factory/README.md` 自己寫的就是 7（一致），是 root README 算錯。
- 已修：8 → 7、並列全 7 個名稱避免再 drift。

### Low risk

**L1. `03-production-line/README.md` + `03-done/README.md` 引用已退役 legacy `pipeline.json` 路徑**
- 兩檔的「配套追蹤」描述仍寫 `data/{operator}/pipeline.json`（單檔形式）。
- 實 SSoT 已 v2.1 全面轉 sharded（`pipeline/_meta.json` + `pipeline/items/*.json`）、單檔路徑被 `.gitignore` 主動防誤建。
- 影響：未來 Claude / Kai 讀此 README 會誤判可手改該 JSON、或誤建立。
- 已修：兩檔的相關段落改指 sharded 路徑 + cross-ref pipeline-schema.md。同步將「不要手改 pipeline.json」改為「不要手改 pipeline 檔案」（指 shards）。

**L2. `01-data-brain/README.md` 結構圖與實際不符**
- 列了 `transcripts/`（首次使用前不存在、無 `.gitkeep`）
- 缺 `index.md`（資料地圖 SSoT、是本目錄最重要的檔）
- 缺 `personas/`（已 tracked、含 `.gitkeep`、brain_loader 載入點）
- 缺 `template/`（已 tracked、新客戶 bootstrap 用）
- 影響：新客戶 / 未來 AI 看到 README 會以為 transcripts/ 應該存在但缺少了、且漏掉 index.md / personas / template 三個關鍵入口。
- 已修：結構圖補齊 5 項並標 transcripts/ 為「首次自動建」、其他三項補上簡要說明。

**L3. `01-data-brain/index.md` interview-bank.md 為 per-client 檔但無標示**
- L31 列入「原文庫」表、但本 template 預設不附此檔（屬客戶有訪談素材時才建）。
- `scripts/libs/brain_loader.py` 不載入此檔；`brain-loading.md` L86 提到 generation mode=interview「需 interview-bank.md」但 brain_loader 不會 raise（該 skill 自己跑時用 Read 工具讀）。
- 影響：客戶第一次跑 `訪談：...` 時 Claude 可能 silently 找不到此檔。
- 已修：在 index.md 對應 row 加註「短期客戶 template 預設不附、客戶有訪談素材時手動建立」。

**L4. `docs/references/skill-architecture-principles.md` 描述目標架構含 `/sync-engine`（quickshot 無此 command）**
- L464 描述 v1.4.3 第二輪退役目標架構含 3 個 command：`/harden / /scan / /sync-engine`。前兩個 quickshot 有、`/sync-engine` 為 KaiOS 主引擎專屬、已隨 README §砍掉的 3 大模組退役。
- 影響：未來 AI 讀此目標架構可能以為 quickshot 也應有 `/sync-engine`。
- 已修：在表後加一行內聯註：「quickshot template 已不含 /sync-engine、本表為 KaiOS 主引擎觀察期目標架構」。

## Changes made

| 檔 | 變更 | 風險 |
|----|------|------|
| `scripts/lint/canonical-registry.json` | `_version` 2.5→2.6、`_updated` 2026-04-25→2026-05-19、`CLAUDE.md` 描述 7→9 條禁令、`ssot_files.pipeline` legacy→sharded 描述 | 純資料描述、rules-lint 不消費此兩值 |
| `README.md` | L58 `8 個 Skill` → `7 個 Skill (...)` + 列全 7 個名稱 | 純文字 |
| `03-production-line/README.md` | 配套追蹤 + 工作流程「pipeline.json」描述改 sharded、「不要手改 pipeline.json」改「不要手改 pipeline 檔案」 | 純文字 |
| `03-production-line/03-done/README.md` | 同上、單行替換 | 純文字 |
| `01-data-brain/README.md` | 結構圖補 index.md / personas / template、`transcripts/` 加註「首次自動建」 | 純文字 |
| `01-data-brain/index.md` | L31 對 `interview-bank.md` 加註「per-client、預設不附」 | 純文字 |
| `docs/references/skill-architecture-principles.md` | L464 後加內聯註指出 quickshot 不含 /sync-engine | 純文字 |

## Files changed

```
 01-data-brain/README.md                          |  9 +++++----
 01-data-brain/index.md                           |  2 +-
 03-production-line/03-done/README.md             |  2 +-
 03-production-line/README.md                     | 10 +++++-----
 README.md                                        |  2 +-
 docs/references/skill-architecture-principles.md |  1 +
 scripts/lint/canonical-registry.json             |  8 ++++----
 7 files changed, 18 insertions(+), 16 deletions(-)
```

## Verification run

| Check | Command | Result | Notes |
|---|---|---|---|
| pytest | `python -m pytest tests/ -q` | 543 passed / 1 skipped | 改動前後皆 pass |
| ruff critical | `ruff check --select E9,F63,F7,F82 scripts tests` | All checks passed | |
| rules-lint CI | `python scripts/lint/rules-lint.py --ci` | 0 errors / 0 warnings | |
| brand-ref lint | `python scripts/lint/brand_ref_lint.py` | 0 errors / 0 warnings | |
| validate-all | `python scripts/ops/video-ops.py validate-all` | 0 errors / 0 warnings | Schema drift 5 NON-BREAKING（baseline、performance-patterns-schema v1.0→v1.1 intentional） |
| hook syntax | `bash -n` × 3 hook + `.githooks/pre-commit` | OK | |
| compile scripts | `python -m compileall scripts -q` | clean | |
| canonical-registry JSON | `python -c "import json; json.load(...)"` | valid | 改動後 JSON 結構仍合法 |

## Issues fixed

- M1：`canonical-registry.json` 中禁令數 + pipeline SSoT 描述對齊事實
- M2：`README.md` skill 計數修正、列全名
- L1：`03-production-line/{README,03-done/README}.md` pipeline 路徑對齊 sharded 現實
- L2：`01-data-brain/README.md` 結構圖補齊三個關鍵入口
- L3：`01-data-brain/index.md` interview-bank.md 標 optional
- L4：`docs/references/skill-architecture-principles.md` 補 `/sync-engine` 退役註

## Existing issues not fixed

- **受 deny list 保護、本輪不動**：
  - `CLAUDE.md`：L62 仍寫 `data/{operator}/pipeline.json`（legacy 路徑），需 Kai 顯式授權才能改。
  - `.claude/rules/workflow.md` / `.claude/skills/*.md` / `.claude/commands/*.md` / `.claude/settings.json`：本輪未發現新 drift。
- **死碼但暫不動（保守保留）**：
  - `scripts/engine/`：空 dir，僅含 `__pycache__/`，`tests/path_bootstrap.py` 有 `ENGINE_LIB_ROOT` + `bootstrap_engine_test_sys_path()` 但無測試使用。屬 KaiOS 引擎 lineage 死碼，刪會破壞 contract 表面、暫留。
  - `tests/fixtures/engine-versioning-rules.json`：無 test / script 引用，孤立 fixture。屬 KaiOS engine-versioning-gate lineage，刪會丟歷史 baseline、暫留。
- **Baseline 已知 schema drift**：`docs/contracts/performance-patterns-schema.md` v1.0→v1.1（Codex → CLI 層、intentional），5 NON-BREAKING + 4 INFO warnings，CI 接受、保留。

## Remaining risks

1. **CLAUDE.md 內 legacy `pipeline.json` 路徑（L62）**：本輪未修（受 deny）。同 PR #14 之後 main 已穩定、Kai 在線時可一次到底改該行 + bump `last_updated` 日期。修動 1 行、純文字。
2. **`scripts/engine/` + 對應 test path bootstrap 死碼**：屬可刪不刪的死碼、不影響運作。若未來引入新 sub-CLI 把 engine 借屍還魂、可重用此 contract；若確定永不會用、建議下一輪 Kai 確認後刪 dir + helper + ENGINE_LIB_ROOT。
3. **`tests/fixtures/engine-versioning-rules.json` 孤立 fixture**：同上，可刪不刪。

## Branch cleanup candidates

### Possibly safe to delete after human review

（未檢視 remote / `git branch -r`、保守不列）

### Do not delete yet

- 當前 branch `claude/repo-optimization-SPsEh`（本輪 7 個未 commit 修改在這）
- 其他 `claude/*` 分支 — 未檢視

## Recommended next actions

1. **Kai 檢視本檔 + 7 個 staged 修改、決定是否 commit**（Claude 受規則限制未自行 commit）。建議 commit message：`docs: 第二輪 ops 清理 — canonical-registry/README 計數/路徑/結構圖 對齊現實`
2. **可選 Kai 一次到底**：`CLAUDE.md` L62 legacy `pipeline.json` 路徑 → `pipeline/`（sharded）— 受 deny、需顯式授權
3. **下一輪可探**：是否刪 `scripts/engine/` + `tests/path_bootstrap.py` 中的 ENGINE_LIB_ROOT helpers + `tests/fixtures/engine-versioning-rules.json` 三個 KaiOS lineage 死碼

## Safe to commit?

- **Yes**（前提：Kai 看過 diff 確認）
- 原因：
  - 全 7 檔皆為純文字 / metadata 校正、無 schema / 邏輯改動
  - 完整驗證鏈通過（pytest 543 / 全 lint 0 / validate-all 0 / ruff 0 / compileall clean）
  - 改動目的單一：把已知對應現實的描述對齊現實、降低未來 AI 誤判
- Conditions before commit:
  - 確認新 README skill 計數 7 個與真實 02-skill-factory dirs 一致（已 ls 驗證）
  - 確認 sharded pipeline 描述語義是 Kai 想呈現的（提及 `docs/contracts/pipeline-schema.md` cross-ref、不留懸空名詞）

## 重要提醒

- 沒有 commit
- 沒有 push
- 沒有開 branch（已在指定 branch `claude/repo-optimization-SPsEh` 工作）
- 沒有開 PR
- 沒有刪除任何檔案
- 沒有改任何 deny list 路徑下檔案
