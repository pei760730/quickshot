# AI System Upgrade Report

## Base
- **Branch**: `claude/review-skill-architecture-eAizG`
- **HEAD**: `4db5439`（落後 main `7e07723` 7 commits — 含 PR #344-#346 但不含 PR #347/#348）
- **Time**: 2026-04-27（Sleep Mode autonomous run）
- **Mode**: 任務指定的「token burn loop」、不 commit / push / PR

## What I inspected

掃描範圍（保守、避開正在進行的 Codex PR cascade）：

1. **頂層結構**：`HOME.md` / `README.md` / `engine-manifest.json` / `07-changelog/CHANGELOG.md` / `07-changelog/ROADMAP.md`
2. **`.claude/`**：`commands/` 3 個、`hooks/session-start.sh`、`rules/workflow.md`、`rules/permissions.md`、`settings.json`、`skills/` 7 個 stub
3. **`02-skill-factory/`**：5 vNext SKILL.md + harden + skill-creator、`shared-references/` 13 份共用規則 + `templates/`、`CHANGELOG.md`、`README.md`
4. **`docs/references/`**：7 份引擎研究文件（`skill-architecture-principles.md` v1.4 / `skill-consolidation-map.md` v1.1 / `skill-design-principles.md` v1.5 [註：在 shared-references/]、`design-lineage.md` / `production-details.md` / `system-maintenance.md` / `verifier-scores-audit.md` / `worktree-guide.md`）
5. **`docs/contracts/`**：8 份共享 schema（順帶確認、未動）
6. **`01-data-brain/`**：`brand.md`、`cases.md`、`index.md` 結構與引用
7. **`scripts/`**：`engine/`（bump-engine wrapper / bump_engine 實質）、`utils/lib/adoption_gate.py` 函式名、`libs/brain_loader.py`、`bootstrap/` 結構（讀取確認、未動 — Codex 領土）
8. **`data/`**：4 個 operator JSON + 8 個 template JSON 的 schema 一致性（讀取確認、未動 — schema 由 Codex 維護）
9. **`tests/`**：僅 `conftest.py` 結構掃描（未動 — Codex 領土）

## Changes made

### 已落地（2 件）

| # | 檔案 | 修改 | 為什麼 |
|---|------|------|------|
| 1 | `02-skill-factory/shared-references/skill-design-principles.md:193` | `shared-references/hook-templates.md` → `shared-references/templates/hook-templates.md`（補 `templates/` 子目錄前綴）| 死引用：實檔在 `templates/` 子目錄、其他所有引用都正確、僅這 1 處漏。未來 reader 對「降級到哪」會誤判 |
| 2 | `docs/references/skill-architecture-principles.md` 行 531 + 541 + 545 後新增段 | (a) P0 status 從「✅ 完成」改「⚠️ 契約層完成 / 行為層 0/44 trace、16/44 hook_type」 (b) v1.1 與 v1.0 差異段加 v1.5 補注 (c) 新增 v1.5 補注完整段 | 真實狀態校正：v1.1 標 P0 「✅ 完成」、實際 trace 0/44。v1.2-v1.4 推導都建在錯誤前提上。校正不重寫歷史、加 patch 段 + 行內 caveat、保留 lineage |

### 被擋（1 件、需 Kai 介入）

| # | 檔案 | 預定修改 | 擋住原因 |
|---|------|---------|---------|
| 3 | `.claude/rules/workflow.md:52` | `adoption_gate.py:build_items()` → `adoption_gate.py:collect_items()` | `.claude/**` 是 `permissions.md` 列的受保護路徑、Claude Code 原生攔截 Edit。需要 Kai 在 UI / CLI 授權後才能改。**注意**：PR #347（Codex）試圖修這 1 行、但越界 + CI red、被 close。實檔仍 stale |

## Files changed

```
02-skill-factory/shared-references/skill-design-principles.md  +2 -1
docs/references/skill-architecture-principles.md              +33 -3
```

無新檔（除本報告 `AI_SYSTEM_UPGRADE_REPORT.md`）、無刪檔、無重命名。

## Verification run

| 檢查 | 命令 | 結果 |
|------|------|------|
| Rules lint | `python3 scripts/lint/rules-lint.py --ci` | **0 errors, 5 warnings**（warnings 全在 `03-production-line/` 腳本檔內、與本輪修改無關）|
| Brand ref lint | `python3 scripts/lint/brand_ref_lint.py` | **0 issues** |
| Python syntax | `python3 -m compileall scripts/libs/ scripts/engine/ scripts/utils/` | **無錯誤**（silent quiet output）|
| Bash syntax | `bash -n .claude/hooks/session-start.sh` | ✓ OK |
| JSON validity | 7 個關鍵 JSON 檔（`.claude/settings.json` / `engine-manifest.json` / `data/.operators.json` / `data/template/pipeline.json` / `data/kai/{pipeline,lessons,todos}.json`）| **全部 valid** |
| Diff sanity | `git diff --stat` | 2 檔案 / +35 -4 行 |
| 修改後重 grep 校驗 | 確認 `templates/hook-templates` 在位、`v1.5 補注（2026-04-27` 段存在 | ✓ 兩處都在 |

未跑：
- `pytest tests/` — Codex 領土測試、本輪未動 source、跳過避免污染（Kai 跑 PR #348 時已驗 580 passed）
- `python scripts/engine/engine_version_check.py` — 本輪沒動 internal_files、不適用
- `territory-lint`（`.github/workflows/territory-lint.yml` 模擬）— 本輪只動 docs/references 與 02-skill-factory/shared-references、Claude 領土 OK、無越界風險

## Issues fixed

1. **死引用：`hook-templates.md` 缺 `templates/` 路徑前綴**（1 處 / 唯一不對齊處 / 其他 8 處引用都正確）
2. **stale claim：v1.4 P0「✅ 完成」與實際 trace 0/44 矛盾**（補 v1.5 patch 段、保留 v1.1-v1.4 主體不重寫）

## Issues identified but not fixed

按嚴重度排：

### 🚨 P0：行為層問題（PR #348 處理中、不歸 Sleep Mode）

| # | 問題 | 處理人 |
|---|------|------|
| A | `_meta.trace_required_statuses` dead code（main 5.62 上 video-ops.py 的強制邏輯讀不到欄位）| Codex PR #348（已開、CI engine-version red、待修） |
| B | `save-with-trace-from-stdin` / `adoption-stats` / `skill-io-schema §CLI Enforcement Notes` 缺 | 同上、PR #348 範圍 |

### 🚧 P1：擋在 permission（需 Kai 授權）

| # | 問題 | 動作 |
|---|------|------|
| C | `.claude/rules/workflow.md:52` `build_items()` → `collect_items()`（callable 名漂移）| Kai 在 UI 授權 Claude 改、或 Kai 自己 1 行 edit |

### ⚠️ P2：架構債務（不 Sleep Mode 範圍、需設計討論）

| # | 問題 | 為什麼留 |
|---|------|---------|
| D | 5 個 vNext SKILL.md frontmatter 全部沒 `owner:` field、未對齊 v1.4 §Owner 對應 + workflow.md v2.24 owner 分流 | 設計變動、Sleep Mode 不該動。建議下次 PR 補 owner=kai (4 個) + 至少 quality 考慮 owner=mixed（Kai 對話 + 員工錄完素材跑）|
| E | `docs/references/skill-consolidation-map.md` v1.1 仍引用 `skill-architecture-principles.md v1.3`、本次 v1.5 補注未反向同步 | 改了會跟 main 主幹其他 references 不一致、屬於上下游版本同步問題、不是 Sleep Mode 該動的高頻變動內容 |
| F | `README.md` 寫 `engine: v5.52` / `CLAUDE.md v4.22` / `61 檔（560 test cases）` — 主幹已演進到 5.62 / v4.24 / 580+ tests | 版本錨點高頻變動、由維護者隨主版本 bump 同步、Sleep Mode 不侵入 |
| G | `02-skill-factory/CHANGELOG.md` 最新 entry 是 2026-04-25 Phase 5 退役、未含 v1.5 視角研究 entry | 屬於設計層 changelog、本輪 v1.5 補注是 references 層、不必雙處同步（CHANGELOG 由 design-doc 主導）|

### 🎯 P3：低槓桿 / 觀感（Sleep Mode 拒絕做）

按任務「不要為了顯得完整而列一堆低槓桿建議」原則、不列。

## Remaining risks

- **Kai 醒來看 PR #348 review prompt** 才能推進採用閉環、本輪 Sleep Mode 不能繞道
- **Fix #3（workflow.md `build_items` → `collect_items`）需 Kai 1 步授權**、否則該行繼續 stale。風險程度：低（不影響運行、只影響文件可讀性）
- **本 branch 落後 main 7 commits**：建議 Kai 醒來後 rebase（`git fetch origin main && git rebase origin/main`）再決定要不要 commit 本輪兩個 fix
- **rules-lint 5 warnings 全在 `03-production-line/2026-03-26_茶葉產地系列_腳本_V1.md`**：是腳本內容的 AI pattern #14（情緒值標註行）、不影響運行、與本輪修改無關、由腳本擁有者決定是否清理

## Recommended next actions

按執行順序：

1. **Kai 醒來第一動**：看 PR #348 進度、貼上輪 review prompt 給 Codex（如果他還沒貼）
2. **Kai 順手做**（30 秒）：直接在 UI 把 `.claude/rules/workflow.md:52` 的 `build_items()` 改成 `collect_items()`、解 Fix #3
3. **本輪 2 個 fix 何時 commit**：建議跟 PR #348 merge 之後一起、走 Claude follow-up PR（`claude/skill-output-contract-uplift` 或類似）合併處理
4. **不要做**：v1.6 視角研究、新 skill、SKILL.md 大改、第二輪退役（5→3）— 全部等 PR #348 merge + trace 數據累積 1-2 月後評估

## Safe to commit?

**No** — 三個原因：

1. Kai 沒明示要 commit / push / PR（任務明確說「不 commit、不 push、不 PR、除非我明確要求」）
2. Branch 落後 main 7 commits、commit 前應 rebase
3. 兩個 fix 內容相關（都跟 v1.5 視角的「文件層校準」有關）、合併進未來的 Claude follow-up PR 比單獨開支線更乾淨

**何時可 commit**：
- Kai 確認後、且
- 已 rebase 到 main HEAD、且
- 跟 Claude follow-up PR（5 SKILL.md Output Contract / workflow.md / 禁令 #10 補強制機制）合一支 PR、避免 PR 累積（L-0017 / L-0018 教訓）
