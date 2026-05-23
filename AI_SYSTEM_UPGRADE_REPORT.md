# AI System Upgrade Report

> Sleep Mode v3.0 第三輪、未 commit / 未 push。
> 前一輪（PR #15、第二輪 ops 清理）已 merge 進 main、本輪基線乾淨後續做。
> 本 session 早期已 commit 一輪 /code-review high 的 bug fix（HEAD 33b55c9、本輪在其上續做、所有第三輪改動為新增 unstaged）。

## Base

- Branch: `claude/code-review-high-Ixmsj`
- HEAD before this round: `33b55c9` (`fix: /code-review high — 修真實 bug + 砍死路徑`)
- HEAD after this round: `33b55c9`（無新 commit）
- Repo root: `/home/user/quickshot`
- Time: 2026-05-21
- Working tree before: clean
- Working tree after: 10 modified + 1 untracked（皆未 commit）

## Project snapshot

- Project type: AI 驅動的短影音生產 template（短期客戶 ≤30 天驗證型精簡版）
- Primary language: Python 3.11
- Package manager: pip + `requirements-dev.txt`（pytest + ruff）
- Main entrypoints:
  - `scripts/ops/video-ops.py`（狀態 SSoT 寫入唯一入口）
  - `scripts/lint/rules-lint.py` / `brand_ref_lint.py` / `skill-io-lint.py`
  - `scripts/utils/wipe_client.py`（短期客戶結束清洗）
  - Claude Code slash commands `/init` `/check` `/scan` `/harden`
- Automation:
  - `.github/workflows/rules-lint.yml`（ruff + rules-lint --ci + brand-ref + pytest + validate-all）
  - `.github/workflows/sync-to-sheets.yml`
  - `.github/workflows/wipe-client.yml`（三層 manual dispatch 安全）
  - `.githooks/pre-commit`（territory check）
  - `.pre-commit-config.yaml`（opt-in：rules-lint + brand-ref）
  - `.claude/hooks/session-start.sh`
- Validation commands: `pytest tests/` / `ruff check --select E9,F63,F7,F82 scripts tests` / `python scripts/lint/rules-lint.py --ci` / `python scripts/lint/brand_ref_lint.py` / `python scripts/ops/video-ops.py validate-all`
- AI instruction files: `CLAUDE.md` / `CLAUDE.local.md` / `.claude/rules/{workflow,permissions}.md` / `.claude/skills/*.md` / `.claude/commands/*.md`
- High-risk areas（deny list）: `CLAUDE.md` / `.claude/rules/**` / `.claude/skills/**` / `.claude/commands/**` / `.claude/settings.json`

## What I inspected

- Git state + branch + remote + last 5 commits
- 218 tracked files
- 全套驗證基線：`pytest` (542 → 562 passed / 1 skipped) / `ruff` critical + F401/F811/F841 / `rules-lint --ci` / `brand_ref_lint` / `validate-all` / `compileall scripts tests`
- README.md / 01-data-brain/index.md 中所有 `.md` 引用是否解析得到（自寫 link check 腳本）
- 全 repo grep `pipeline.json` 出現點 vs 實際 sharded layout
- 全 repo grep `kaios / KaiOS` lineage cross-ref 確認是否歷史標註 vs 真實 drift
- 受 deny list 保護路徑（CLAUDE.md / .claude/**）— 列為 remaining risk、不動
- 死碼盤點：`scripts/engine/__pycache__`（無 source）、`tests/fixtures/engine-versioning-rules.json`
- 新增驗證：`wipe_client.py` 之前 0 test 覆蓋、是 destructive 操作、補 20 test

## System-level issues found

### High risk

無。本輪基線（main + 33b55c9）已乾淨、無資料毀損 / 流程中斷風險。

### Medium risk

**M1. `wipe_client.py` 0 test 覆蓋（destructive 操作、有歷史 bug）**
- 早期 /code-review 已修兩個真 bug（gather vs execute 用 `shutil.rmtree` 忽略 `PRESERVE_FILENAMES`、`title` 欄位不存在卻在 filter）。但這兩個 bug 之所以發生是因為沒有任何 regression test。
- 影響：若未來有人 revert 修復、或加新邏輯破壞 dry-run/execute 對稱性、CI 不會抓到。
- 已修：補 `tests/test_wipe_client.py` 20 test、含：
  - `test_preserves_readme_in_root_dirs_delete` — 對應之前的 gather/execute 對稱性 bug
  - `test_ignores_title_field` — 對應 schema 一致性
  - `test_corrupt_json_returns_zero` — 對應 narrow exception
  - `test_non_canonical_schema_returns_zero` — 確保 dead fallback keys 不會被 re-introduce
- 風險：純測試新增、無生產邏輯動、CI 不會 regress。

### Low risk

**L1. 5 個 ruff F401 / F841 死碼（unused imports / variable）**
- `scripts/lint/skill-io-lint.py:7` — `import sys` 未使用
- `scripts/ops/video-ops.py:1101` — `kv = _parse_kv_args(...)` 賦值後 dead（函式內無用到）
- `tests/test_pipeline_regression_guard.py:1` — `import pytest` 未使用
- `tests/test_rules_lint_paths.py:3` — `from pathlib import Path` 未使用（早期 /code-review 砍 test 後遺留）
- `tests/test_save_and_verifier.py:3` — `from pathlib import Path` 未使用
- 已修：全 5 個刪除。
- 影響：純 linter clean、無行為改動。`ruff F401/F811/F841` 全 repo clean。

**L2. `README.md` 命令清單漏 `init` + `check`**
- L40 `commands/{harden,scan}.md` — 但 `.claude/commands/` 實有 4 個（init.md / check.md / harden.md / scan.md、PR #7 加 init + check）。
- 影響：新人 / 未來 AI 看 README directory tree 不知道有 `/init` 跟 `/check`。
- 已修：`commands/{init,check,harden,scan}.md`。

**L3. `README.md` directory tree 仍寫 legacy `pipeline.json` 單檔**
- L52 `data/{operator}/pipeline.json # 狀態 SSoT` — pipeline-schema v2.1+ 已全面轉 sharded、`.gitignore` 主動防誤建。前一輪修了 `canonical-registry.json` / `03-production-line/README.md`、但 root README 漏改。
- 影響：高頻 doc、新讀者第一個看到的就是錯的。
- 已修：`pipeline/  # 狀態 SSoT（sharded：_meta.json + items/VID-NNN.json）`。

**L4. `01-data-brain/index.md` 內相對路徑 link 錯誤**
- L22 寫 `shared-references/performance-injection-protocol.md`、實際在 `02-skill-factory/shared-references/...`。
- 影響：未來 AI 從 brain index 連結時找不到。
- 已修：補全路徑前綴。

**L5. `docs/references/wipe-client-sop.md` 與 code 不同步**
- L112 仍寫 `data/{op}/pipeline.json` 為 reset row、但 `.gitignore` 主動 block 此 path、實際 wipe SSoT 是 `pipeline/`（L118 已正確列）。兩 row 重複、第一 row 是 dead。
- L125 `pattern/counter_pattern/title 不含...` — 早期 /code-review 已從 code 砍 `title`（lessons schema 無此欄）、但 doc 漏更新。
- 影響：destructive 操作的 SOP 描述 vs 真實行為對不上。
- 已修：合併兩 row 為 `pipeline/`、註記 legacy 已被 gitignore 防誤建；filter 描述砍 `title`。

**L6. `docs/contracts/video-ops-cli.md:95` `validate` 描述用 legacy 詞**
- 寫 「驗證 pipeline.json schema」、實際驗證的是 sharded data。
- 已修：「驗證 pipeline schema（sharded：`_meta.json` + items）」。

**L7. `requirements-dev.txt` 註解含 KaiOS lineage 殘留**
- L1 寫 `KaiOS-ContentSystem`、L9 `engine-manifest.json internal_files`（後者檔不存在、PR #4 刪了）。
- 影響：未來 AI 看 dev deps SSoT 註解可能誤以為是 KaiOS / 要去找 engine-manifest.json。
- 已修：改 `quickshot 短期客戶 template`、刪 engine-manifest 那行。

## Changes made

| 檔 | 變更 | 風險 |
|----|------|------|
| `README.md` | L40 commands list 補 init/check、L52 pipeline.json → pipeline/ sharded | 純文字 |
| `01-data-brain/index.md` | L22 link 補 02-skill-factory/ 前綴 | 純文字 |
| `docs/references/wipe-client-sop.md` | L112 合併兩 row + 註記 gitignore、L125 砍 title | 純文字、對齊 code |
| `docs/contracts/video-ops-cli.md` | L95 validate 描述更新 | 純文字 |
| `requirements-dev.txt` | 註解清 KaiOS + engine-manifest lineage | 純註解 |
| `scripts/lint/skill-io-lint.py` | 刪 unused `import sys` | dead code |
| `scripts/ops/video-ops.py` | 刪 `_cmd_vid_inference_stats` 內 unused `kv = _parse_kv_args(...)` | dead code、未影響行為 |
| `tests/test_pipeline_regression_guard.py` | 刪 unused `import pytest` | dead code |
| `tests/test_rules_lint_paths.py` | 刪 unused `from pathlib import Path` | dead code |
| `tests/test_save_and_verifier.py` | 刪 unused `from pathlib import Path` | dead code |
| `tests/test_wipe_client.py`（新增）| 20 test 補 destructive op 之前 0 覆蓋 | 純新增 |

## Files changed

```
 01-data-brain/index.md                            |  2 +-
 README.md                                         |  4 +-
 docs/contracts/video-ops-cli.md                   |  2 +-
 docs/references/wipe-client-sop.md                |  5 +-
 requirements-dev.txt                              |  5 +-
 scripts/lint/skill-io-lint.py                     |  1 -
 scripts/ops/video-ops.py                          |  1 -
 tests/test_pipeline_regression_guard.py           |  2 -
 tests/test_rules_lint_paths.py                    |  2 -
 tests/test_save_and_verifier.py                   |  2 -
 tests/test_wipe_client.py                         | 207 +++++++++++++ (new)
 11 files changed, 217 insertions(+), 16 deletions(-)
```

## Verification run

| Check | Command | Result | Notes |
|---|---|---|---|
| pytest | `python -m pytest tests/ -q` | 562 passed / 1 skipped | +20 net 新增（wipe_client tests）|
| ruff critical | `ruff check --select E9,F63,F7,F82 scripts tests` | All checks passed | |
| ruff dead-code | `ruff check --select F401,F811,F841 scripts tests` | All checks passed | 改動前 5 hit、改動後 0 |
| rules-lint CI | `python scripts/lint/rules-lint.py --ci` | 0 errors / 0 warnings | |
| validate-all | `python scripts/ops/video-ops.py validate-all` | 0 errors / 0 warnings / 0 schema drift | 基線已從 5 NON-BREAKING 收斂到 0 |
| compile scripts/tests | `python -m compileall scripts tests -q` | clean | |
| Sharded pipeline smoke | manual test items in tmp dir | items_total + by_status 正確 | 對應早期 /code-review fix 的 e2e 驗證 |
| Wipe dry-run smoke | `python scripts/utils/wipe_client.py default --dry-run` | 9 files, 0 lessons kept | 正常運作 |

## Issues fixed

- M1：補 `wipe_client.py` 20 test、含對 gather/execute 對稱性 bug 的 regression guard
- L1：清 5 個 ruff F401/F841 hit
- L2：README.md commands list 補 init/check
- L3：README.md pipeline.json → sharded
- L4：01-data-brain/index.md link 補全路徑
- L5：wipe-client-sop.md 對齊 code（title 砍、pipeline 路徑合併）
- L6：video-ops-cli.md validate 描述更新
- L7：requirements-dev.txt 註解清 KaiOS lineage

## Existing issues not fixed

- **受 deny list 保護、本輪不動**：
  - `CLAUDE.md` L62 仍寫 `data/{operator}/pipeline.json`（legacy 路徑）— 同 PR #15 報告所述、需 Kai 顯式授權才能改。修動 1 行、純文字、對齊現實。
  - `.claude/rules/workflow.md` / `.claude/skills/*.md` / `.claude/commands/*.md` / `.claude/settings.json` — 本輪未發現新 drift。
- **死碼但暫不動（保守保留、刪除為不可逆）**：
  - `tests/fixtures/engine-versioning-rules.json`：grep 過全 repo、零 code 引用、僅 AI_SYSTEM_UPGRADE_REPORT + CHANGELOG-archive 提到名字。屬 KaiOS engine-versioning-gate lineage 死 fixture。建議下輪 Kai 確認後刪。
  - `scripts/engine/__pycache__/`：本身 untracked（.gitignore 蓋 `__pycache__/`）、dir source 已刪、僅本地 stale 殘留。fresh clone 不會有此問題、可忽略。
  - `dashboard/dist/{index.html,data.json,.rebuild-state.json,.rebuild.lock}`：本身 untracked（.gitignore 蓋 `dashboard/`）、無 source / 無 build script 在 repo 內、僅本地 stale。fresh clone 不會有、可忽略。
- **效能改善（既有 review agent 指出、本輪不動、value < 安全 cost）**：
  - `session-start.sh` 無條件 `pip install -q -r requirements-dev.txt` — 每 session ~1-3s 噪音、用 marker file 可解。`.claude/hooks/` 非 deny、可改、但 session 啟動行為動改是 explicit-auth 級行為。flag 在此供 Kai 決定。
  - `rules-lint.py` `_file_reference_exists` 每次 missing-ref 跑 `REPO_ROOT.rglob(basename)`、無 cache、CI lint 多輪 full-tree walk。實測 lint 仍 <10s、不是 hot pain、留待未來 lint slow 時再優化。
  - `brand_ref_lint` 在 `rules-lint.py:check_brand_ref_contract` 內被叫一次、CI yaml 又獨立叫一次。重複 ~1s/CI、行為一致。可移除 yaml 那道 standalone step、但會降低「單跑 brand-ref」discoverability、本輪保持。
- **長度但不會崩**：`scripts/ops/video-ops.py` 2284 行、`SIMPLE_COMMAND_HANDLERS` dispatcher dict 只覆蓋一半 command、其餘 `elif` chain。可移完、但屬中型重構、非本輪範疇。

## Remaining risks

1. **CLAUDE.md L62 legacy `pipeline.json` 路徑**：本輪未修（受 deny）。如 Kai 在線、可一次到底改 + bump `last_updated` 日期。修動 1 行、純文字。
2. **02-skill-factory / shared-references 內 `pipeline.json` 概念引用（~10 處）**：多為「概念上的 schema 名」而非真實檔案路徑、技術正確但措辭過時。逐一修為「pipeline 資料 / pipeline schema」是純語意 polish、ROI 低、跳過。
3. **`scripts/utils/wipe_client.py PER_OP_RESET_FILES` 仍含 `"pipeline.json"`**：`.gitignore` block 此 file、`data/template/pipeline.json` 不存在、`shutil.copy2 if src.exists()` guard 讓此 entry 為 no-op。屬 dead config entry、刪會更乾淨但不影響行為。下輪可順手清。

## Branch cleanup candidates

### Possibly safe to delete after human review

（未檢視 remote / `git branch -r`、保守不列）

### Do not delete yet

- 當前 branch `claude/code-review-high-Ixmsj`（本 session 兩輪累積：早期 /code-review 已 commit + push、本輪未 commit 的 10 改 + 1 新）

## Recommended next actions

1. **Kai 檢視本檔 + 11 個未 commit 變更、決定是否 commit + push**（Claude 受 sleep mode 規則限制未自行 commit）。建議 commit message：
   ```
   docs+test: 第三輪 sleep mode — 文件對齊現實 + 補 wipe_client 20 test + 清 5 dead imports

   - README.md commands list 補 init/check、directory tree 對齊 sharded pipeline
   - 01-data-brain/index.md link 補全路徑
   - docs/{contracts/video-ops-cli, references/wipe-client-sop}.md 對齊 code 真相
   - requirements-dev.txt 註解清 KaiOS lineage
   - tests/test_wipe_client.py 補 20 test 守住先前修的 gather/execute 對稱性 bug
   - 清 5 ruff F401/F841 hit（含 video-ops.py _cmd_vid_inference_stats dead kv）
   ```
2. **可選 Kai 一次到底**：`CLAUDE.md` L62 legacy `pipeline.json` 路徑 → `pipeline/`（sharded）— 受 deny、需顯式授權
3. **下輪可探**：
   - 刪 `tests/fixtures/engine-versioning-rules.json` 孤立 fixture
   - 清 `scripts/utils/wipe_client.py PER_OP_RESET_FILES` 內 dead `"pipeline.json"`
   - `session-start.sh` pip install marker file gating（每 session 省 1-3s）

## Safe to commit?

- **Yes**（前提：Kai 看過 diff 確認）
- 原因：
  - 全 11 檔皆為純文字 / 註解 / dead-code 清除 / 新增 test、無生產邏輯修改
  - 完整驗證鏈通過（pytest 562 / 全 lint 0 / validate-all 0 / ruff F401/F841 0 / compileall clean）
  - 改動目的單一：對齊現實 + 補驗證缺口 + 清死碼
- Conditions before commit:
  - 確認 `test_wipe_client.py` 20 test 是 Kai 想要的驗證邊界（含 `test_ignores_title_field` 對應之前的 schema fix）
  - 確認 README 的 sharded 描述措辭跟 Kai 預期一致

## 重要提醒

- 沒有 commit（本輪所有改動仍在 working tree）
- 沒有 push
- 沒有開 branch（在 sleep-mode 觸發前已存在的 `claude/code-review-high-Ixmsj`）
- 沒有開 PR
- 沒有刪除任何檔案
- 沒有改任何 deny list 路徑下檔案（CLAUDE.md / .claude/rules/** / .claude/skills/** / .claude/commands/** / .claude/settings.json）
- 沒有改 secrets / credentials / google-credentials.json 等敏感檔
