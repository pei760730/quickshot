# AI System Upgrade Report

> 由 Claude Code (Opus 4.7) 在 sleep-mode 自動產出。請當作系統優化建議與已執行清單，不要當作 release notes。

## Base
- **Branch**: `claude/system-optimization-KuVCP`
- **HEAD before**: `16696b3` (Merge PR #323)
- **Time (UTC)**: 2026-04-26T16:37:31Z
- **Mode**: 系統級優化（不寫新 skill、不重構、不 commit、不 push）
- **Adoption gate 狀態**：本輪 session bypass（Kai 任務指令明示「不要停下來等我確認」、自動記為 `skip adoption gate`、納入 lessons.json 後續處理）

## What I inspected

### 第 1 階段：建立真相
- `git status` / `git log` / 全 repo 結構 / 主要 README & manifest
- 跑 `pytest` / `rules-lint --ci` / `skill-io-lint` / `brand-ref lint` / `ai-patterns lint` / `check-version-sync` / `engine-version-check` / `validate-all`
- 全 repo JSON 解析 / Python 編譯 / Shell 語法檢查

### 第 2 階段：找系統級問題
1. **架構一致性**：README.md vs 實際檔案的 LOC / 測試數 / 版本號漂移
2. **自動化可靠性**：5 個 GitHub workflow 的 timeout / 死路徑 / 錯誤處理
3. **驗證與測試**：560 case 全綠，但 lint 有 broken file refs
4. **文件與維護**：dashboard README 指向已歸檔的 contract、引擎 manifest 中的 contract 缺 inline version
5. **未來 AI 協作安全**：session-start hook 在 remote 環境 install 失敗會炸掉整個 hook（brand.md 不注入）
6. **多 operator 體質**：`data/template/` 缺 3 個檔案、新 client bootstrap 不完整

## Changes made

### A. README 真相對齊（系統最重要的入口、AI 下次進來會先讀這個）
- `version: ... | engine: v5.42` → `engine: v5.52`
- `Python 程式 ~11,466 行（17 lib 模組...）` → `~12,800 行（17 ops/lib + 10 utils/lib...）`
- `自動化測試 54 檔（522 cases）` → `61 檔（560 cases）`（兩處）
- `CLAUDE.md v4.20（12 條禁令）+ workflow.md v2.22` → `v4.22（13 條禁令）+ v2.24`
- 「12 條禁令 + 資料地圖」→「13 條禁令 + 資料地圖」（兩處）
- `.claude/skills/  # 19 個 entry stub` → `7 個 entry stub`（Phase 5 真退役後實際只剩 7）
- 引擎版本說明 + Skill thinning timeline 補上 v5.52
- 結尾「最新 engine v5.40、PR #297 已 merged」→「最新 engine v5.52」

### B. 對話開頭規則 broken-ref 修復
`.claude/rules/workflow.md` L408–409：
- `shared-references/title-rules.md` → `02-skill-factory/shared-references/title-rules.md`
- `shared-references/templates/hook-templates.md` → `02-skill-factory/shared-references/templates/hook-templates.md`

對齊 brand.md / cases.md / index.md / CHANGELOG.md 已在用的 full-path 慣例。`rules-lint missing_file warning` 從 7 → 5（剩餘 5 個是某腳本 content 檔的 AI-pattern warning、不是系統問題）。

### C. CI workflow 加 timeout（防 GitHub Actions 卡住燒 quota）
全部 5 個 workflow 都加 `timeout-minutes`：
| workflow | timeout |
|---|---|
| `engine-version-check.yml` | 5 min |
| `rules-lint.yml` | 10 min |
| `sync-readme-to-main.yml` | 5 min |
| `territory-lint.yml` | 5 min |
| `sync-to-sheets.yml` | 15 min（job-level、原本只有單一 step 5min）|

### D. sync-to-sheets.yml 死路徑清理
- Debug 步驟原本 `cat 00-control-center/todo/工作待辦.md` 與 `雜事待辦.md`、兩個檔案 v4.39 後就被 `data/<op>/todos.json` 取代、CI log 永遠印 `(file not found)` 是純噪音。改為列出 `data/*/todos.json` 的 item 數。
- `Sync data files to main` step 的 `git diff -- pathspec` 包含 `00-control-center/todo/`、改為移除（保留 `data/`、`03-production-line/`、`01-data-brain/`）。

### E. session-start hook 失敗容錯
`.claude/hooks/session-start.sh`：
- `set -euo pipefail` + remote-only `apt-get install ffmpeg` chain 失敗會終止整個 hook，導致 brand.md 全文不注入。改為 `(apt-get update -qq && apt-get install -y -qq ffmpeg) >/dev/null 2>&1 || true` 與 `pip install -q faster-whisper >/dev/null 2>&1 || true`，確保安裝失敗時 brand.md 仍能注入、Adoption gate 仍能掃。
- 加註解說明這是刻意為了不讓 hook 因為 install 失敗炸掉。

### F. 補完 contract 版本標籤
`docs/contracts/test-path-bootstrap.md` 是 `engine-manifest.contract_files` v1.0、但檔案沒有 `> version:` header → `rules-lint check_engine_manifest_inline_versions()` 因 `if found is not None` 而靜默 skip，等於 manifest 與檔案版本毫無連動驗證。補上 `> version: 1.0 | last_updated: 2026-04-26`、lint 現在會把它納入版本一致性檢查。

### G. 補完 dashboard README 指向已歸檔 contract
`dashboard/README.md` 兩處引用 `docs/contracts/design-collaboration.md`，但該檔已歸檔到 `docs/archive/design-collaboration.md`。改為指向 archive，附上「v1.0 已歸檔」標記。

### H. 補完 data/template/ 缺檔（multi-operator bootstrap 缺口）
`data/kai/` 有但 `data/template/` 沒有 → 新 client repo bootstrap 不完整：
- 新增 `data/template/brand-monitor.json`（schema-compliant 空殼）
- 新增 `data/template/social-followers.json`（tiktok / instagram / facebook 三平台 placeholder）
- 新增 `data/template/topic-history.json`（30-day rolling schema 空殼）

同時 `data/template/hardening-archive.json` 的 `schema_version` 從 `0.1` 升到 `0.2`、`description` 對齊 `_ARCHIVE_EMPTY` 在 `scripts/ops/lib/hardening.py` 中的當前定義（v4.67 dialog-only 版）。

> 注意：`scripts/bootstrap/bootstrap-client.sh` 屬 Codex territory，**未在這次優化內被改**。Codex 需追加三行 `copy_if_missing` 才能讓 bootstrap 真的把這三個檔案 copy 到新 client。詳見 §Recommended next actions。

## Files changed
```
M  .claude/hooks/session-start.sh
M  .claude/rules/workflow.md
M  .github/workflows/engine-version-check.yml
M  .github/workflows/rules-lint.yml
M  .github/workflows/sync-readme-to-main.yml
M  .github/workflows/sync-to-sheets.yml
M  .github/workflows/territory-lint.yml
M  README.md
M  dashboard/README.md
M  data/template/hardening-archive.json
M  docs/contracts/test-path-bootstrap.md
A  data/template/brand-monitor.json
A  data/template/social-followers.json
A  data/template/topic-history.json
A  AI_SYSTEM_UPGRADE_REPORT.md  (本檔)
```

## Verification run

```
pytest tests/ -q                              → 560 passed in 3.30s
python scripts/lint/rules-lint.py --ci        → 0 errors, 5 warnings (all 內容檔 AI-pattern、非系統)
python scripts/utils/check-version-sync.py    → ✅ 所有 Skill 版本號一致
python scripts/lint/skill-io-lint.py          → ✅ skill-io lint passed
python scripts/lint/brand_ref_lint.py         → ✅ 0 issues
python scripts/ops/video-ops.py validate-all  → 0 errors, 1 warning (VID-009 script_path、見 Remaining risks)
python scripts/engine/engine_version_check.py → ✅ engine-version-check passed
yaml.safe_load × 5 workflows                  → 全 OK
bash -n session-start.sh                      → OK
session-start.sh smoke                        → brand.md 正常注入 + adoption gate 正常顯示
```

## Issues fixed (summary)

1. **README 9 處事實漂移** — engine version / LoC / test count / CLAUDE.md / workflow.md / 禁令數 / skill stub 數 / Phase 5 timeline / CHANGELOG pointer
2. **workflow.md 2 個 broken file ref** — title-rules.md / hook-templates.md 缺 `02-skill-factory/` 前綴
3. **5 個 workflow 缺 job-level timeout** — 任何 hang 會吃光 GitHub Actions quota
4. **sync-to-sheets.yml 2 個死路徑** — `00-control-center/todo/工作待辦.md` / `雜事待辦.md`（v4.39 已遷移到 `todos.json`）
5. **session-start hook 在 remote 安裝失敗會殺掉整個 brand 注入** — `set -e` + 沒 `|| true`
6. **`docs/contracts/test-path-bootstrap.md` 缺 inline version** — 導致 lint 對它的版本一致性檢查靜默 skip
7. **`dashboard/README.md` 2 處指向已歸檔的 contract**
8. **`data/template/` 缺 3 個 schema 樣板** — 新 client bootstrap 不完整、`hardening-archive.json` schema 版本落後

## Remaining risks（未在這輪改）

### 高風險（建議下次優先）
- **VID-009 資料一致性問題**：pipeline 標 `待拍`，但 script 已存在 `03-production-line/03-done/kai/2026-02-28_加盟割韭菜_腳本_V1.md`。只有 Kai 能判斷「應該標已上線、補 publish_date」還是「script 應該移回 02-ready-to-shoot」。`validate-all` 已在每次跑時噪音化此警告。
- **`scripts/utils/lib/config.py:20` 死路徑**：`TODO_ROOT = "00-control-center/todo"` 目錄已不存在。屬 Codex 領土、無法在 Claude branch 改。
- **`data/.operators.json` 中如新增非 kai operator，dashboard 不支援**：`dashboard/build.py:25 OPERATOR = "kai"` 是硬編碼。設計上是「每 client repo 自己 fork dashboard」、單 tenant per repo 是預期行為，但若想 multi-tenant 需要重構。

### 中風險
- **`scripts/utils/lib/sync_tabs.py:280` + `builders.py:431` 仍引用 `HOLD` 狀態**：v3.7 已從 pipeline 移除 HOLD 狀態（見 VID-009 的 `notes` 欄位）。這兩處仍是歷史相容性碼路徑、值得 Codex 確認還是否需要保留。
- **`scripts/utils/lib/performance_injection.py:14` + `lessons_retrieval.py:13`** 把 `data/kai/...` 寫死成模組層常數。在新 operator 環境會炸或讀錯。屬 Codex 領土。

### 低風險（純資訊）
- **`brand.md last_updated` 11 sections 過期 47+ 天**：Adoption gate v2.24 已標為 `owner=employee`、不擋新任務、純等 Kai 補新事實後一次更新。系統設計上是合理的。

## Recommended next actions

按 ROI 排序：

1. **Codex：給 `scripts/bootstrap/bootstrap-client.sh` 補 3 行 `copy_if_missing`**（讓本輪新增的 3 個 template 檔案真的會被 copy 到新 client）
   ```bash
   copy_if_missing "data/template/brand-monitor.json"   "data/$OPERATOR/brand-monitor.json"
   copy_if_missing "data/template/social-followers.json" "data/$OPERATOR/social-followers.json"
   copy_if_missing "data/template/topic-history.json"   "data/$OPERATOR/topic-history.json"
   ```

2. **Codex：清理 `scripts/utils/lib/config.py:20` 的 `TODO_ROOT`**、確認沒人還用、移除或改指向 `data/$op/todos.json`。

3. **Kai：判 VID-009 該往哪邊**（`已上線` + 補 publish_date / 把 script 移回 ready-to-shoot），讓 `validate-all` 警告歸零。

4. **Codex：審視 `HOLD` 狀態殘留**（`scripts/utils/lib/sync_tabs.py` + `builders.py`），決定是純歷史相容還是該清。

5. **長期：把 `rules-lint check_engine_manifest_inline_versions` 從 silent-skip 改為 hard-fail**（當 manifest 標版本但檔案沒 `> version:` header 時）。本輪已先補上 `test-path-bootstrap.md` 的 header、但根本上檢查邏輯本身可以更嚴格。

6. **架構長期觀察**：dashboard 單 tenant 假設（`OPERATOR = "kai"`）vs multi-operator 系統哲學的張力。目前是「每 client 自己 fork dashboard」、若未來變成「一個 dashboard 顯示多 operator」則需動 build.py 結構。

## Safe to commit?

- **Yes**，但建議分 3 個 logical commits：
  1. `docs: sync README facts to current engine state` — 只 README.md
  2. `ci: add timeout-minutes + clean dead paths in workflows` — `.github/workflows/*` 5 檔
  3. `fix: resilient session-start hook + missing template files + doc-link drift` — 其他

- **不建議在 push 前做的事**：
  - 不要 amend、不要 force push（這個 branch 是 fresh autonomous run）
  - PR body 內最好註明：「`.claude/`、`.github/`、`02-skill-factory/`、`data/template/` 全部都在 Claude territory 白名單裡（territory-lint.yml regex 已驗證）— 沒有 Codex 領土越界」
  - PR body 不需要 `territory override justified by:` — 因為沒違規

- **這份 report 自身不要 commit**（除非 Kai 明確要）：根據規則 `不要 commit、push、開 branch、開 PR，除非我明確要求`。

---
*generated by Claude Code (Opus 4.7) in sleep mode @ 2026-04-26 — token-burn passes: 1 baseline + 4 optimization rounds + 1 final verification*
