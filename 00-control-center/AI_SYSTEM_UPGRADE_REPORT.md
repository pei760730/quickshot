# AI System Upgrade Report

## Base

- Branch: claude/review-video-analytics-dashboard-OTShe
- HEAD: 9607991
- Repo root: /home/user/KaiOS-ContentSystem
- Time: 2026-05-12
- Working tree before changes: `M data/kai/pipeline.json`（既有、來自其他 branch sync 過來、本輪不動）
- Working tree after changes: 上述 + `M 01-data-brain/index.md` + `M 01-data-brain/template/CLAUDE.local.md`

## Project snapshot

- Project type: KaiOS short-form video production engine + Kai 紅茶巴士實例（custom Python + Markdown + Shell）
- Primary language: Python 3 + Markdown
- Package manager: 無（pip install pytest/ruff on-demand）
- Main entrypoints:
  - `scripts/ops/video-ops.py` — primary CLI（pipeline / lessons / todos / backfill / verifier-scores）
  - `scripts/lint/rules-lint.py` — cross-file rule linter
  - `scripts/lint/brand_ref_lint.py` — frontmatter brand-ref consistency
  - `scripts/engine/engine_version_check.py` — bump protocol guard
  - `scripts/utils/sync-engine.py` — multi-customer engine sync
  - `dashboard/build.py` — pipeline → static dashboard
- Automation: 5 workflows（territory-lint / rules-lint / engine-version-check / sync-readme-to-main / sync-to-sheets）
- Validation commands available:
  - `python3 -m pytest tests/` ✅ 618 passed
  - `python3 scripts/lint/rules-lint.py --ci` ✅ 0 errors / 21 warnings
  - `python3 scripts/lint/brand_ref_lint.py` ✅ 0 issues
  - `python3 scripts/utils/check-version-sync.py` ✅ pass
  - `python3 scripts/engine/engine_version_check.py --base origin/main --head HEAD` ✅ pass
  - `python3 scripts/ops/video-ops.py validate-all` ✅ 0 errors（29 warnings = legacy `learning_extracted` 欄位欠補）
- AI instruction files:
  - `CLAUDE.md` v4.24（14 禁令 + 資料地圖 + 操作原則）
  - `CLAUDE.local.md`（本 repo 客戶身份 + forbidden_terms）
  - `.claude/rules/workflow.md` v2.30（對話流程 + Adoption-gate v2.24 + Mode W）
  - `AGENTS.md`（Codex 工作守則、引用 agent-collaboration.md v1.10）
- High-risk areas: contract_files 內容改動會觸發 engine-version-check → 強制 bump + CHANGELOG 條目

## What I inspected

1. Git / branch / working tree 狀態（uncommitted: pipeline.json + 本輪兩個 fix）
2. 5 個 GitHub workflows（觸發條件 + `set -*` 安全旗）
3. `.claude/hooks/*.sh` 4 個（session-start / stop / post-tool-use / dashboard-rebuild）
4. 5 個本機驗證指令的退場碼
5. `engine-manifest.json` contract_files / internal_files 完整性（manifest_file_missing → 0）
6. 文件 ↔ 檔案系統漂移（grep `scripts/.*\.\(py\|sh\)` 引用 → 60 個唯一引用 / 14 個 MISSING）
7. brand.md auto-inject 退役 wording 對齊狀態（CLAUDE.local.md / index.md / template / README / design-lineage）
8. 上一輪 sleep mode（2026-05-11）報告 + 已 commit 改動是否落地
9. stop hook 是否真在覆寫 trace（log 顯示 always `skip empty transcript`、未實際進入覆寫路徑）
10. Working tree `data/kai/pipeline.json` 為何持續 dirty（前一 session 已被 Kai 選 1 丟棄、本 session 又出現 → 推測 session-start 過程中由某 sync 動作 re-introduce）

## System-level issues found

### High risk

無。

### Medium risk

- **`docs/codex/sandbox-setup.md` line 138 指引 Codex 跑 `scripts/bootstrap/codex-session-init.sh`、但該檔不存在**。文件用「把上面的 init script 存成 ...」這種「應該存在」的語氣、容易誤導未來 Codex 真的去跑、拿到 `file not found`。
  - **不修原因**：實際解法是 (a) 真把 init script 加進 repo（屬 Codex 領土 `scripts/bootstrap/*`、本 branch 為 claude/* 違反 territory-lint）、(b) 或改文字成「請 Kai / Codex 補上」（屬文檔修改、可行但需驗證 Kai 對此 init script 的最終立場）
  - **建議**：Kai 醒來後確認方向、由 Codex PR 補檔或 Claude 修文字

- **`.claude/hooks/stop.sh` 含 hardcoded `--title-type T1 --hook-type B1 --version B1` fallback、若有 VID 已存在則會覆寫成 garbage 值**。log 確認目前路徑沒被觸發（transcript always empty）、實際無資料污染。但這條 dead code path 是定時炸彈、未來若 trace_extractor 改寫成能讀到 transcript、會立刻引爆。
  - **不修原因**：屬 Claude 領土可改、但會動到「資料寫入」邏輯、改錯比不改危險。Sleep mode 邊界外。
  - **建議**：加入 todos（`scripts/ops/video-ops.py todo add --title "review stop.sh hardcoded fallback"`、Kai 醒來後決定）

- **`scripts/bootstrap/bootstrap-client.sh` 線 38-41 只 copy template/brand.md / cases.md、不 copy template/CLAUDE.local.md**。實際 CLAUDE.local.md 由 `reset-operator.py` 從 template render 生成（已確認、見 `scripts/bootstrap/reset-operator.py:60-92`）、bootstrap 主檔的 comment 文件略不完整。**並非實際 bug**、列入只供參考。

### Low risk（已修）

- **`01-data-brain/index.md` line 6 / line 9**：描述 SessionStart hook 「全文由 SessionStart hook 自動注入 brand.md」、實際 v4.62 起已退役為 lazy load（per CLAUDE.local.md / brain-loading.md v1.5 / CHANGELOG v5.85 entry）。未來 AI 讀到會誤判 brand.md 必然在 context 內、做出基於該誤判的決策。
  - **修法**：line 5-9 整段重寫、加三條觸發路徑（skill 跑時 `brain_loader.load_for_skill()` / 對話按需 Read / SessionStart hook 1 行提示）、刪「Session 注入 ⊆ 產出載入」過時 framing
  - **影響範圍**：本檔不在 contract_files、無需 bump

- **`01-data-brain/template/CLAUDE.local.md` line 14**：template 仍寫「brand.md 全文由 SessionStart hook 自動注入」。`reset-operator.py` 從此 template render 客戶端 CLAUDE.local.md、新客戶會繼承過時敘述。本 repo 自己的 CLAUDE.local.md 已對齊 lazy load、唯獨 template 沒同步。
  - **修法**：複製本 repo CLAUDE.local.md §品牌速查 段落結構、覆蓋 line 14 為 lazy load 三條路徑說明
  - **影響範圍**：本檔不在 contract_files、無需 bump。未來新 customer fork / `bootstrap-client.sh` 流程會繼承正確版本

### Not fixed（contract_files、需 bump、超出 sleep mode 邊界）

> **🟢 2026-05-15 更新**：本節 3 項已於 PR #441（engine v5.94 Post-merge fact realignment v3、3/3 跨 2 commits f87d5f4 + b608c57 + 3rd narrative cleanup e719e09）全部修完。並於 PR #443（engine v5.95）把根因「contract_files 太敏感」解掉、`contract_files` 拆 `semantic_contracts` + `factual_contracts`、純文字 stale 改動不再觸 engine bump、預計類似 deferred 累積不再出現。下列項目保留為 sleep mode v3.0（v5.92）當時 snapshot、不更新內文以維持歷史記錄真實。

- **README.md line 4 / 23 / 313 `engine: v5.90`**：實際 engine_version = `5.92`、漂移 2 個 minor。前一輪 sleep mode 報告也標記為 deferred（理由相同）。✅ Fixed by PR #441
- **`docs/references/design-lineage.md` line 55 §heading `brand.md 為品牌 SSoT（v4.62+ SessionStart hook 全文注入）`**：應對齊 lazy load 表述。contract_files、需 bump。✅ Fixed by PR #441
- **`.claude/rules/workflow.md` line 273-286 `§Codex 待實作 CLI`**：`video-ops.py lessons add-evidence` CLI 已實作（驗證：`python scripts/ops/video-ops.py lessons --help` 回 `<list|add|add-evidence|stats|propose-hardening|archive>`）。section 標題與內容均為過時。contract_files、需 bump。前一輪報告也標記。✅ Fixed by PR #441（commit b608c57、Bash bypass + Kai consent）

## Changes made

### 1. `01-data-brain/index.md` lines 5-9 重寫 Trigger 區分區塊

**Before**:
```
> **Trigger 區分（v3 扁平化、對齊 CLAUDE.md v4.11 + workflow.md v2.8）**：
> - **Session 起手**：`brand.md` 全文由 SessionStart hook 自動注入。v4.62 起廢除 `brand-summary.md` 衍生檔（Opus 4.7 可吃全文、衍生層只帶來漂移同步成本）。
> - **產出腳本時**（本檔定義）：生成型 Skill 被觸發的那一刻、依下表載入完整資料。
>
> Session 注入 ⊆ 產出載入（brand.md 兩者共用）、但 Session 不載 cases / lessons / performance-patterns / banned-words（那些只在生成前載）。
```

**After**:
```
> **Trigger 區分（v4 lazy load、對齊 CLAUDE.local.md + brain-loading.md v1.5+）**：
> - **Session 起手**：SessionStart hook 不再 cat brand.md 全文、只印 1 行提示（v4.62 起 auto-inject 退役、每 session 省 ~27k token baseline）。`CLAUDE.local.md` 已含品牌名 / operator / forbidden_terms 等識別資訊每 session auto-load、身份不受影響。
> - **產出腳本時**（本檔定義）：生成型 Skill 被觸發的那一刻、`scripts/libs/brain_loader.load_for_skill()` 自動載入下表完整資料進 BrainBundle。
> - **對話中按需**：Kai 隨口提品牌事實 / Claude 需 brand context 推理 → Claude 主動 `Read 01-data-brain/brand.md`（單次載入、僅該對話）。
>
> 三條路徑互補、不重複；Session 不再「先載 brand.md」、所以 cases / lessons / performance-patterns / banned-words 一律走 skill load 或 on-demand。
```

### 2. `01-data-brain/template/CLAUDE.local.md` line 14 §品牌速查 重寫

**Before**:
```
## 品牌速查

`01-data-brain/brand.md` 全文由 SessionStart hook 自動注入 context（v4.62+、衍生速查檔已廢除）。
```

**After**:
```
## 品牌速查

`01-data-brain/brand.md` 改 lazy load（v4.62 全文 auto-inject 退役、每 session 省 ~27k token baseline）：

- **skill 跑時**：透過 `scripts/libs/brain_loader.load_for_skill()` 自動載入（見 `02-skill-factory/shared-references/brain-loading.md` v1.5+）
- **對話中**：隨口提品牌事實 / Claude 需 brand context 推理 → Claude 主動 `Read 01-data-brain/brand.md`（單次載入、僅該對話）
- **session-start hook**：不再 cat 全文、只印 1 行提示
- **CLAUDE.local.md 已含的識別資訊**（品牌名 / operator / forbidden_terms）每 session auto-load、身份識別不受影響
```

效益：未來新 customer 透過 `fork-for-client.sh` → `bootstrap-client.sh` → `reset-operator.py` 流程 render CLAUDE.local.md 時、繼承正確的 lazy load 三層描述、不會帶舊 auto-inject 認知。

## Files changed

| File | Reason | In contract_files? | Bump required? |
|------|--------|--------------------|----------------|
| `01-data-brain/index.md` | 修 stale auto-inject 描述、對齊三層 lazy load | No | No |
| `01-data-brain/template/CLAUDE.local.md` | 對齊本 repo CLAUDE.local.md 已修內容、避免新客戶繼承 stale | No | No |
| `00-control-center/AI_SYSTEM_UPGRADE_REPORT.md` | 本輪 sleep mode 報告（覆寫前一份 2026-05-11 報告）| No | No |

## Verification run

| Check | Command | Result | Notes |
|-------|---------|--------|-------|
| rules-lint | `python scripts/lint/rules-lint.py --ci` | ✅ 0 errors / 21 warnings | 與 baseline 相同、本輪修改未引入新警告 |
| brand-ref-lint | `python scripts/lint/brand_ref_lint.py` | ✅ 0 issues | 維持前輪 sleep mode 成果 |
| pytest | `python -m pytest tests/` | ✅ 618 passed in 5.38s | full suite、無 skip |
| version-sync | `python scripts/utils/check-version-sync.py` | ✅ pass | 所有 Skill 版本號一致 |
| engine-version-check | `python scripts/engine/engine_version_check.py --base origin/main --head HEAD` | ✅ pass | 本輪改動不在 contract_files、無需 bump |
| validate-all | `python scripts/ops/video-ops.py validate-all` | ✅ 0 errors / 29 warnings | warnings 來自既有 legacy 資料（learning_extracted 缺欄位、orphan script_path）、與本輪無關 |
| git diff --check | `git diff --check` | ✅ clean | 無 whitespace 錯誤 |

## Issues fixed

1. `01-data-brain/index.md` Trigger 區分敘述對齊 v4.62 lazy load 實況、移除「Session 起手 = brand.md 全文注入」誤導
2. `01-data-brain/template/CLAUDE.local.md` §品牌速查 對齊主 repo 已修內容、堵住新客戶繼承 stale 描述的漏

## Existing issues not fixed

| Issue | Why not fixed | Recommended approach |
|-------|---------------|----------------------|
| `README.md` engine: v5.90 → v5.92 漂移（line 4 / 23 / 313）| README 在 contract_files、單獨改需 bump README + engine_version + CHANGELOG、超出 sleep mode 邊界 | 下次 README 有實質內容改動時順手對齊 |
| `docs/references/design-lineage.md` line 55 §heading 仍寫 `SessionStart hook 全文注入` | contract_files、bump 要求同上 | 與 README engine 對齊同批處理（一個 PR、bump engine_version 一次、減少 churn）|
| `.claude/rules/workflow.md` §Codex 待實作 CLI（line 273-286）| contract_files | 同上、可在同 PR 一起改 |
| `docs/codex/sandbox-setup.md` line 138 指引 Codex 跑不存在的 `scripts/bootstrap/codex-session-init.sh` | 需 Kai 確認方向（補檔 vs 改文字）| 列入 todos |
| `.claude/hooks/stop.sh` hardcoded T1/B1/B1 fallback dead path | 改錯比不改危險、本 session 不動寫入邏輯 | 列入 todos |
| `data/kai/pipeline.json` working tree dirty（491 行 diff、本 session 開頭就存在）| 與本輪 sleep mode task 無關、Kai 已在前一 session 選 1 丟棄、卻又出現、推測為自動 sync 行為 | Kai 醒來後再決定保留 / 丟棄、或追根 session-start 中哪個機制 re-sync |
| README.md line 45 `brand.md ... SessionStart hook 全文注入` | contract_files | 與 line 4 / 23 / 313 一併處理 |

## Remaining risks

1. **stop.sh hardcoded fallback**（見 Medium risk #2）：log 顯示目前不會被觸發（transcript empty）、但若 trace_extractor 改寫變得會抓到 transcript、會立即用 T1/B1/B1 覆寫 VID metadata。優先級：中。
2. **contract_files 漂移累積**：本輪識別的 4 處 stale wording 全在 contract_files、無法在 sleep mode 邊界內處理。每多累積一處、後續對齊 PR 的成本（bump + CHANGELOG 條目）成正比上升。建議 Kai 醒來後安排一次 batch alignment PR。
3. **pipeline.json 自動 re-sync 機制不透明**：working tree 持續被 re-introduce、跨 session 仍存在。若這是 hook 行為、應在 hook 端加 log / state file 讓追蹤可行；若是 git ops 副作用、應確定來源。本 session 不調查、避免擾動。
4. **`scripts/tools/research.py` / `scripts/tools/web_fetch.py` 未實作**：discovery skill discover-trend mode 仍是 prompt-only fallback。文檔已準確標示「待 Codex 寫」、非 stale、但長期未補。對 discovery 質量上限有實質影響。

## Branch cleanup candidates

### Possibly safe to delete after human review

無待清理 local branch。

### Do not delete yet

- `claude/review-video-analytics-dashboard-OTShe`（本 session 工作分支、未 push）
- `claude/video-analytics-dashboard-2ubn3`（含 VID-090~097 backfill、Kai 未決定 merge 與否）
- `main`

## Recommended next actions

依 ROI 排序：

1. **Review 本輪 2 個檔的 diff**（`git diff 01-data-brain/index.md 01-data-brain/template/CLAUDE.local.md`）
2. **決定 working tree pipeline.json 處置**（丟棄 / commit / 追根因）
3. **規劃 batch alignment PR**：把 contract_files 4 處 stale（README × 3 + design-lineage × 1 + workflow.md §Codex 待實作 CLI）一起改、bump engine_version 一次。預估 30 分鐘、效益 = 所有引擎版本與 lazy load wording 對齊。
4. **處理 `claude/video-analytics-dashboard-2ubn3` 紅 X**（README 8.7 / manifest 8.6 mismatch、源自 main 上 `[skip ci]` 漏 lint）— 屬於 (3) batch alignment 的子問題
5. **長期**：補 `scripts/tools/research.py` / `web_fetch.py`（提升 discovery skill 上限）

## Safe to commit?

- **Yes**（針對本輪 2 個 markdown 改動 + 本報告）
- **Why**:
  - 0 lint errors / 0 brand-ref issues / 618 tests pass / engine-version-check pass
  - 兩個改動都不在 contract_files、不觸發 bump 要求
  - 改動性質為「對齊現實」的文字修正、無 production behavior 影響
- **Conditions before commit**:
  - (a) Kai 先決定 `data/kai/pipeline.json` 處置（不要把它一起 commit 進來、否則會與 `claude/video-analytics-dashboard-2ubn3` 內容重疊）
  - (b) 建議 commit message: `docs: align index.md + template/CLAUDE.local.md to lazy-load reality (sleep mode v3.0)`
  - (c) **不需要 bump engine_version**（兩個檔都不在 contract_files）

---

## Sleep Mode v3.0 — 重要提醒

- 沒有 commit
- 沒有 push
- 沒有開 branch
- 沒有開 PR
- 沒有刪除任何檔案
- 沒有碰 secrets / 設定 / 私密資料
- 沒有改 production scripts
- 沒有改 contract schema
- 沒有改 CI workflows
- 沒有大規模重構
- 沒有動 `data/kai/pipeline.json`（既有 uncommitted、留給 Kai 決定）

**本輪 token 轉換成果**：
- 2 個 stale auto-inject 描述對齊 lazy load 實況（index.md + template/CLAUDE.local.md）
- 1 個 template 漏修阻絕新客戶繼承 stale wording
- 1 份報告把剩餘 Medium / contract_files 漂移問題列清楚、給 Kai 安排 batch PR
- 618 tests pass / 0 lint errors / 0 engine-version-check 違規維持
