# AI System Upgrade Report

> Sleep Mode autonomous run（Kai 指定 token burn loop、不 commit / push / PR）。

## Base
- **Branch**: `claude/optimize-system-debt-1kWQe`
- **HEAD before**: `37217f5`（Merge PR #352）
- **Time**: 2026-04-28
- **Mode**: 系統級優化（不寫新 skill、不重構、不 commit、不 push）
- **Adoption gate 狀態**：本輪開頭 hook 顯示 `0 項需決定（員工類不算）`、無 Kai 待決事項擋路、可直接進

## What I inspected

### Stage 1：建立真相
- 跑 `git status` / `git log -20`、確認分支已是 harness 指定 `claude/optimize-system-debt-1kWQe`
- 跑 `find` 全 repo 結構、`engine-manifest.json` 內容、近兩輪 Sleep Mode 報告（2026-04-26 / 2026-04-27）
- 跑 `pytest tests/`（579 passed）/ `rules-lint --ci` / `skill-io-lint` / `brand-ref-lint` / `check-version-sync` / `validate-all`
- 跑 `engine_version_check.py`（local 環境 origin/main 無 merge base、crash；real CI 不受影響）

### Stage 2：找系統級問題
1. **README 版本錨點漂移**（5.52 vs 5.64、13 vs 14 禁令、560 vs 579 tests、4.22 vs 4.24 CLAUDE.md）
2. **`02-skill-factory/README.md`**：引用 `skill-design-principles.md` v1.3+「五準則 A-E」、實檔已 v1.5 + 準則 F
3. **README.md 內結構樹**：同樣的「五準則」漂移
4. **`docs/references/production-details.md`**：語音筆記分流表保留「→ 記錄到對應 skill-memory」、skill-memory v4.36 起退役
5. **`.github/workflows/rules-lint.yml`** paths 過濾：PR 觸發漏抓 `engine-manifest.json` / `01-data-brain/**` / `README.md` / `07-changelog/**` / `docs/**` / `00-control-center/**` 改動 — 純文檔層 PR 會悄悄跳過 lint
6. **`engine_version_check.py` 在無 merge base 環境 crash**：subprocess CalledProcessError 直接拋、無友善訊息（Codex 領土、本輪未動）
7. **VID-009 `script_path` 漂移**：pipeline 標 `02-ready-to-shoot/2026-02-05_..._雙軌腳本_V1.md`、實檔在 `03-done/2026-02-28_..._腳本_V1.md`（前 2 輪報告已標、需 Kai 業務決策）
8. **`scripts/utils/lib/sync_tabs.py:280` HOLD 殘留**：v3.7 已退役狀態、code 仍有判斷分支（Codex 領土）
9. **`.claude/rules/workflow.md:52` `build_items()` callable 名漂移**：實函式為 `collect_items()`（受 deny list 保護、需 Kai UI 授權）
10. **`scripts/lint/canonical-registry.json` 描述「7 條禁令」stale**：實際 14 條（Codex 領土）
11. **`02-skill-factory/CHANGELOG.md`**：未記 v1.5 視角研究（design-changelog 範圍、本輪非範圍）
12. **schema-drift in agent-collaboration.md**：8 個 NON-BREAKING、6 個標 `(intentional, v1.8 → v1.10)`、2 個 markdown 結構誤報、無真實漂移

## Changes made

### 1. README.md（v8.1 → v8.2、6 處事實對齊）

| 行 | 從 | 到 |
|----|----|------|
| 4 | `engine: v5.52` | `engine: v5.64` + last_updated `2026-04-28` |
| 10 | `13 條禁令` | `14 條禁令` |
| 22 | `61 檔（560 test cases）` | `64 檔（579 test cases）` |
| 23 | Skill 區塊 `engine v5.52` | `engine v5.64` |
| 24 | `CLAUDE.md v4.22（13 條禁令）` | `v4.24（14 條禁令）` |
| 34 | `CLAUDE.md v4.22、13 條禁令` | `v4.24、14 條禁令` |
| 65 | `# A/B/C/D/E 五準則` | `# A/B/C/D/E/F 六準則` |
| 86 | `tests/ 61 檔、560 cases` | `64 檔、579 cases` |
| 278 | `pytest # 61 檔、560 cases` | `64 檔、579 cases` |
| 306 | `最新 engine v5.52` | `最新 engine v5.64` |

### 2. `02-skill-factory/README.md`（v6.0 → v6.1）
- 引用 `skill-design-principles.md v1.3+ A/B/C/D/E 五準則` → `v1.5+ A/B/C/D/E/F 六準則（F 為 4.7 mature 視角新增）`

### 3. `engine-manifest.json`（contract scope bump）
- `_meta.engine_version` 5.64 → 5.65
- `_meta.last_updated` 2026-04-27 → 2026-04-28
- `contract_files["README.md"]` 8.1 → 8.2
- `contract_files["02-skill-factory/README.md"]` 6.0 → 6.1

### 4. `07-changelog/CHANGELOG.md`（新增 v5.65 entry）
- 標題「🔧 Sleep Mode 文件層 fact realignment」
- 列 6 處動作 + engine bump 原因 + 不在範圍項目

### 5. `.github/workflows/rules-lint.yml`（CI 死角補強）
- 移除 `paths` 過濾、改 `branches: [main, claude/**, codex/**]`
- 之前 paths 漏抓 `engine-manifest.json` / `README.md` / `01-data-brain/**` / `07-changelog/**` / `docs/**` 改動 → 純契約檔 PR 悄悄繞過 lint、版本漂移無人擋
- 加註解說明根因（v5.65 補強）

### 6. `docs/references/production-details.md`
- 語音筆記分流表 `→ 記錄到對應 skill-memory` → `→ 記錄到 data/[operator]/lessons.json（v4.36 起、skill-memory/ 已退役）`

## Files changed

```
M  .github/workflows/rules-lint.yml      | -10  -10
M  02-skill-factory/README.md            | +3   -3
M  07-changelog/CHANGELOG.md             | +42  +0
M  README.md                             | +10  -10
M  docs/references/production-details.md | +1   -1
M  engine-manifest.json                  | +4   -4
─────────────────────────────────────────────────────
6 files changed, 67 insertions(+), 31 deletions(-)
```

無新檔（除本報告）、無刪檔、無重命名。

## Verification run

```
pytest tests/ -q                              → 579 passed in 3.78s
python scripts/lint/rules-lint.py --ci        → 0 errors, 5 warnings (pre-existing 內容檔 AI-pattern)
python scripts/utils/check-version-sync.py    → ✅ 所有 Skill 版本號一致
python scripts/lint/skill-io-lint.py          → ✅ skill-io lint passed
python scripts/lint/brand_ref_lint.py         → ✅ 0 issues
python scripts/ops/video-ops.py validate-all  → 0 errors, 3 warnings + 8 schema-drift NON-BREAKING (預存)
yaml.safe_load × 5 workflows                  → 全 OK
bash -n session-start.sh                      → OK
JSON validity × 7 critical files              → 全 OK
git diff --stat                                → 6 files / +67 -31
```

未跑：
- `engine_version_check.py` — 本機環境無 origin/main merge base、crash；real CI 環境正常。本輪只動 contract scope（README + 02-skill-factory/README + manifest）+ CHANGELOG 已 bump、CI 該過。
- `python -m compileall` — 本輪未動 Python 檔
- `dashboard/build.py` — 跑過、輸出 `dashboard/dist/index.html (64.9 KB) + data.json`、確認沒因 README 改動而崩

## Issues fixed

| # | 問題 | 修復 |
|---|------|------|
| 1 | README 9 處事實漂移（engine / tests / 禁令數 / CLAUDE.md 版本）| Edit + manifest + CHANGELOG bump |
| 2 | `02-skill-factory/README.md` 漏標準則 F | inline 引用更新 + 版本 6.0→6.1 |
| 3 | rules-lint.yml PR/push paths 漏抓契約層改動 | 移除 paths 過濾、改 branches 過濾 |
| 4 | `production-details.md` 語音分流表 stale skill-memory ref | 更新為 `lessons.json`（含 v4.36 退役註）|
| 5 | engine-manifest contract_files README 條目 8.1 漂移 8.2 | manifest 同步 |

## Issues identified but NOT fixed

按嚴重度排：

### 🚧 P1：擋在 permission（需 Kai 授權）

| # | 問題 | 動作 |
|---|------|------|
| A | `.claude/rules/workflow.md:52` `build_items()` → `collect_items()` callable 名漂移 | Kai UI / CLI 授權 Claude Edit `.claude/rules/**`、或 Kai 1 行 edit。**從 04-27 報告延續未解、Codex PR #347 已 close** |

### 🚧 P2：Codex 領土（territory-lint 擋）

| # | 問題 | 處理人 |
|---|------|------|
| B | `scripts/utils/lib/sync_tabs.py:280` HOLD 殘留分支（v3.7 已退役）| Codex 確認該保留為歷史相容性還是清掉 |
| C | `scripts/lint/canonical-registry.json` 描述「7 條禁令」stale | Codex 1 字改（"7 條禁令" → "14 條禁令"）|
| D | `scripts/engine/engine_version_check.py` 無 merge base 時 crash 無友善訊息 | Codex 加 `try / except CalledProcessError` 印「無 merge base、跳過 check」exit 0 |
| E | `scripts/utils/lib/performance_injection.py:14` + `lessons_retrieval.py:13` 把 `data/kai/...` 寫死成模組層常數 | 04-26 報告提過、Codex 領土未動 |
| F | `scripts/utils/lib/config.py:20` `TODO_ROOT` 是否還有死路徑 | 04-26 報告稱已清、本輪 grep 確認無殘留 ✓ |

### 🚧 P3：Kai 業務決策

| # | 問題 | 動作 |
|---|------|------|
| G | VID-009 `script_path` 指向不存在檔（pipeline 標 `02-ready-to-shoot/.../2026-02-05_加盟割韭菜_雙軌腳本_V1.md`、實檔在 `03-done/.../2026-02-28_加盟割韭菜_腳本_V1.md`）| 二選一：(a) `transition VID-009 已上線` + 補 publish_date + 改 script_path、(b) 把實檔 mv 回 `02-ready-to-shoot` 並改名匹配 |
| H | brand.md 11 sections last_updated 47+ 天前 | Adoption gate v2.24 標 `owner=employee`、純等 Kai 補新事實後一次更新（系統設計如此、不擋） |

### ⚠️ P4：架構債務（不 Sleep Mode 範圍）

| # | 問題 | 為什麼留 |
|---|------|---------|
| I | 5 個 vNext SKILL.md HTML 註解仍引 `skill-architecture-principles.md v1.3` | 04-27 報告分類為 P2、改的話需逐一動 SKILL.md（可能影響 frontmatter version 一致性檢查）、設計層變動而非 fact-fix |
| J | `02-skill-factory/CHANGELOG.md` 未記 v1.4/v1.5 設計研究 entry | 屬 design changelog 範圍、由 design-doc 主導 |
| K | `dashboard/build.py:25 OPERATOR = "kai"` 單 tenant 假設 | 04-26 確認為設計選擇、不重構 |
| L | `sync-from-github.bat` 寫死 Windows 路徑 + 無條件 `git pull origin main` | 在非 main 分支會產生 unwanted merge commit、但是 user 工具 Kai 自己用、改動會驚擾 |
| M | `.claude/hooks/dashboard-rebuild.sh` 失敗 3 次後升員工顯示、但無自動 issue 創建 | hook owner=auto、設計上對齊禁令 #11 階段 2-3、failure rate 太低不值得加 issue 自動化 |

## Remaining risks

1. **`.claude/rules/workflow.md:52` 仍 stale（同 04-27 風險）**：影響低，文件可讀性問題
2. **本 branch `claude/optimize-system-debt-1kWQe` 與 main 關係**：本機環境無 origin/main merge base、不知 branch 是否已落後；建議 Kai 醒來後 `git fetch origin main && git log --oneline origin/main..HEAD` 確認
3. **engine_version 5.65 vs main 衝突**：若有並行 PR 也 bump 到 5.65（如 Codex PR #348 用 5.63 預留位、本 PR 用 5.65、應安全）、merge 時無撞號
4. **rules-lint.yml paths 移除可能讓 lint 在無關 PR 也跑**：權衡是 trade off，每 PR 多 ~10s CI 時間、換得契約層 PR 的 lint 覆蓋率
5. **schema-drift 8 個 NON-BREAKING warning**：6 個標 intentional、2 個是 markdown table cell 被誤判為 schema field（agent-collaboration.md v1.10 加的「選項」「不改 PR、只補資訊」等）— 屬 detector 誤報、不是真漂移，可考慮 Codex 在 detector 加白名單忽略 markdown table

## Recommended next actions

按執行順序：

1. **Kai 醒來檢視本輪 6 檔改動**：`git diff` 看是否認可
2. **Kai 30 秒 1 行修**：`.claude/rules/workflow.md:52` `build_items()` → `collect_items()`
3. **Codex 跟一個小 PR**（territory：scripts/）：
   - `canonical-registry.json` 描述「7 條禁令」→「14 條禁令」
   - `scripts/engine/engine_version_check.py` 無 merge base graceful exit
4. **Kai 業務決策**：VID-009 該標已上線還是搬回（看實檔內容判斷）
5. **本 PR commit + push 時機**：建議 6 檔合併為 1 PR（標題「docs: realign README/manifest facts to engine v5.65 + lint coverage fix」），與下一個 Codex 跟單 PR 隔開

## Safe to commit?

**Yes**（如果 Kai 同意），建議分 1 個 commit：
- 標題：`docs: realign README/skill-factory facts to engine v5.65 + tighten rules-lint coverage`
- 內容：6 檔（README + skill-factory README + manifest + CHANGELOG + workflow + production-details）
- territory check：全部在 Claude 白名單（README / engine-manifest / 02-skill-factory / 07-changelog / .github / docs/references）— 無越界、不需 PR body override

**不建議**：
- 拆多 commit（fact-realign + lint-coverage 強相關、放一起好回滾）
- amend / force push（fresh autonomous branch、保留 linear history）

**這份 report 自身**：不要 commit（per Kai 任務規則、`不要 commit、push、開 branch、開 PR、除非我明確要求`）

---

## Token burn loop summary

完成輪次：
- **Round 1**：建立真相 + 跑全 lint/test 基線
- **Round 2**：發現 README 9 處事實漂移、修 + bump engine 5.64→5.65 + CHANGELOG entry
- **Round 3**：補 02-skill-factory/README 准則 F + 再掃 README 找出更多 stale 點 + 寫入 manifest
- **Round 4**：CI 工作流 paths 死角補強（rules-lint.yml）
- **Round 5**：docs/references/ 掃 skill-memory stale ref、修 1 處
- **Round 6**：dashboard build smoke test（OK）+ 全 lint + test + JSON + YAML + bash 最終驗證

未發現需要更深入修復的高 ROI 項目。剩餘問題分類為 permission-gated（Kai 1 行修）/ Codex 領土 / 業務決策、已列入 §Issues NOT fixed。

---
*generated by Claude Code (Opus 4.7) in sleep mode @ 2026-04-28 — 6 token-burn rounds*
