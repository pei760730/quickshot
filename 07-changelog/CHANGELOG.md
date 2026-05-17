# 系統變更紀錄（CHANGELOG）

> 紀錄每次系統優化的內容和原因。最新版本在最上面。
>
> 標記：🔧 引擎（Skill / script / rule，跨客戶通用）｜📦 資料（品牌知識 / 腳本 / 回填，客戶專屬）
>
> **歷史版本**：本檔保留 v5.50+（最近約 1 週）。v5.00 ~ v5.49 見 [CHANGELOG-archive-v5.x.md](./CHANGELOG-archive-v5.x.md)、v1.1 ~ v4.99 見 [CHANGELOG-archive-v4.x.md](./CHANGELOG-archive-v4.x.md)。切檔於 v5.72（2026-04-30）。

---

## v6.02（2026-05-15）

**主題：🔧 sync-to-sheets workflow 在 `GOOGLE_CREDENTIALS_JSON` 缺時 silent skip（不 fail）**

### 背景

`.github/workflows/sync-to-sheets.yml` 在 `GOOGLE_CREDENTIALS_JSON` secret 缺 / 過期 / quota 爆時 `exit 1` → CI red。

對客戶 repo / fork（不接 Google Sheets、永遠沒這個 secret）而言、每次 workflow 跑都 fail、PR 上掛紅 X、Kai 主 repo 行為不受影響但客戶端體驗破。

### 歷史

- **2026-04-30**：LONGBRO 客戶 repo（per CLAUDE.local.md Q6 path A client-isolation 範本驗證場）撞同問題、commit `99d80fb5` surgical 修過（`[ -z "$CREDS" ]` → `echo warning + exit 0`）、commit msg 註「T-0001 #4 engine 漏修」、寄望 engine 下版照修
- **2026-04-30 ~ 2026-05-15**：engine 端沒接收這個 fix、本機保留 surgical 版本
- **2026-05-15**：LONGBRO 跑 v5.73 → v5.99 sync（PR #28）、per Q6 path A「永遠追隨主引擎」、workflow 被 engine 版完整覆蓋、surgical fix 消失、`exit 1` 復活

→ 同樣 fix 在 LONGBRO 已寫過、每次 sync 都被洗掉、必須收進引擎根因解。

### 修法

`.github/workflows/sync-to-sheets.yml`：

1. `Write Google credentials` step：
   - 加 `id: creds`
   - `[ -z "$CREDS" ]` → `echo ::warning::` + `echo has_creds=false >> $GITHUB_OUTPUT` + `exit 0`（不再 `::error::` + `exit 1`）
   - 有 creds → `echo has_creds=true >> $GITHUB_OUTPUT`
2. `Run sync` step 加 `if: steps.creds.outputs.has_creds == 'true'`

其他 step（`Debug` / `Determine sync mode` / `Sync data files to main`）不依賴 secret（grep 過 `google-credentials\|gspread\|sheets-direct` 確認）、保持無條件執行、客戶 fork 仍能正常做 branch → main 的 data 同步。

### 影響

| 環境 | 行為 |
|------|------|
| Kai 主 repo（secret 已設） | `has_creds=true`、`Run sync` 跑、行為不變 |
| LONGBRO / 客戶 fork（secret 未設） | workflow 印 `::warning::`、`Run sync` skipped、其他 step 照跑、整體 workflow status = success |

### 對應規則

- CLAUDE.md 禁令 #4 精準修改：只動 secret 檢查那段 + 給 `Run sync` 加 if condition、不順手改其他 step
- CLAUDE.local.md Q6 path A：本修屬引擎根因解、客戶 fork（LONGBRO commit `99d80fb5`）禁客戶端 surgical 重複修、走上游 sync 路徑

### 影響檔案

| 檔 | 領土 | 改動 |
|----|------|------|
| .github/workflows/sync-to-sheets.yml | 共享（CI workflow） | `Write Google credentials` 改 silent skip + `Run sync` 加 if |
| engine-manifest.json | 共享 | engine 6.01 → 6.02 |
| 07-changelog/CHANGELOG.md | Claude | 本 entry |

### 無 schema migration

純 CI 行為變動、無資料層 / 規則層 schema 變動、客戶端 `/sync` 自動拉到、無 migration step。

---

## v6.01（2026-05-15）

**主題：🔧 清「§Orientation Phase 1」 historical 字樣（3 檔 8 處）**

### 背景

`.claude/rules/workflow.md` v2.25+（commit `5d...` in v5.67 / Phase 6）已把第二輪退役預備條款的章節升正式版（`## Orientation Phase 1` → `## Orientation`、`## Distillation Phase 2` → `## Distillation`）、但 3 個 `02-skill-factory/` 下的 semantic_contracts 檔的 active pointer 仍指向 `§Orientation Phase 1`、引用了不存在的 section name。

LONGBRO 客戶 fork（PR #27、2026-05-06、已關閉）試圖客戶端 surgical 清這個落差、被 CLAUDE.local.md Q6 path A「永遠追隨主引擎、不做客製分支」判定不可、改由引擎統一清。

### 修法

- `02-skill-factory/orientation/SKILL.md`（v2.0 → v2.1）：5 處 active pointer
  - L3 `description:` 內、L13 ⚠️ warning banner、L27 bullet、L34 觸發方式段、L53 相關文件清單
- `02-skill-factory/shared-references/brain-loading.md`（v1.7 → v1.8）：2 處 active pointer
  - L87 §適用 skill 表 orientation row、L117 v1.4 changelog entry 內 pointer
- `02-skill-factory/shared-references/skill-design-principles.md`（v1.5 → v1.6）：1 處
  - L255 §反例記憶錨表「對話準則（workflow.md §Orientation Phase 1）」→ 「對話準則（workflow.md §Orientation）」

### 不動（保留 historical / lineage）

- `02-skill-factory/CHANGELOG.md` L201/L217：v1.4 改版記錄（描述當時 workflow.md 還寫 Phase 1）
- `docs/references/skill-architecture-principles.md` L287/L300/L448/L485/L634/L640/L642：設計推導 / vNext Phase 1 計畫 lineage
- `docs/references/skill-consolidation-map.md` L95/L151：Phase 1 計畫表 / 退場推導
- `README.md` L306：v8.0 歷史 CHANGELOG entry

判斷原則：**指向 workflow.md 當前 section 的 active pointer 要清；描述「v1.4 當時還叫 Phase 1」的 historical narration 保留**。

### 對應規則

- CLAUDE.md 禁令 #4 精準修改：只清 3 檔 8 處 active pointer、不順手改 historical narration
- CLAUDE.local.md Q6 path A：本清理屬引擎統一動作、客戶 fork（LONGBRO PR #27）禁客戶端 surgical、走上游 sync 路徑

### 影響檔案

| 檔 | 領土 | 改動 |
|----|------|------|
| 02-skill-factory/orientation/SKILL.md | Claude | 5 處 + frontmatter version bump |
| 02-skill-factory/shared-references/brain-loading.md | Claude | 2 處 + 頂部 version bump |
| 02-skill-factory/shared-references/skill-design-principles.md | Claude | 1 處 + 頂部 version bump |
| engine-manifest.json | 共享 | engine 6.00 → 6.01 + 3 semantic_contracts entries 同步 bump |
| 07-changelog/CHANGELOG.md | Claude | 本 entry |

### 無 schema migration

純文字 cosmetic 清理、無 schema / 行為層變動、客戶端 `/sync` 自動拉到、無 migration step。

---

## v6.00（2026-05-15）

**主題：🔧 tests fixture operator 參數化（解客戶 fork 9 fail）**

### 背景

LONGBRO 客戶 fork（PR #28、commit `11a1e1f5`）升 engine v5.99 後跑 `pytest tests/ -q` 撞 9 failures、全部根因 `tests/conftest.py` + 5 個 test 檔對 operator=`kai` 硬寫死、跟客戶端 `data/.operators.json={longbro}` 對撞。

按 CLAUDE.local.md Q3「CI 紅自動分類表」、本失敗不屬 surgical 範圍（一改超過 1 檔 5 行限制、且改了下次 sync 又被覆蓋）— 屬引擎契約問題、上游修正。

### 修法

- `tests/conftest.py`：
  - 新增 `operator_fixture`（params=["kai"]、未來可加 longbro / 多 operator matrix）
  - `tmp_project` / `patch_paths` 改用 `operator_fixture` 取代寫死 `"kai"` / `kai_dir`
  - `patch_paths` 同時 patch `lib.config.*` 與 `scripts.ops.lib.config.*` 兩條 import path（兩個 module object、共享同檔但獨立 globals）
  - 新增 `patch_operator_registry` fixture：給用 `tmp_path` 而非 `tmp_project` 的 tests 用、最小化 patch 量
  - `with patch(...), patch(...), ...` 改 `ExitStack`（避免 Python 20 nested-blocks 上限）
- `tests/test_adoption_gate_defer.py`：3 tests 改吃 `operator_fixture` + `patch_operator_registry`、`_write_minimal_data` 加 operator 參數
- `tests/test_adoption_gate_owner.py`：`test_owner_split_gate_count` 改用 fixture、assert 改 `i.owner == operator_fixture`
- `tests/test_brand_owner_routing.py`：兩 tests 都用 fixture、`assert owners["4"] == operator_fixture`、`collect_items(operator=operator_fixture)`
- `tests/test_cli_contract.py`：無需動 test、`patch_paths` 自動 patch `lib.config.DEFAULT_OPERATOR` 後 4 個 `record-verifier-scores` exits tests 自動綠（不走 `kai_only` marker fallback）
- `tests/test_sedimentation.py`：`add_lesson(operator_fixture, ...)` / `operator=operator_fixture`、`test_context_uses_meta_max_proposals` 加 `patch_paths` + `operator_fixture` 兩個 fixture

### 對應規則

- CLAUDE.md 禁令 #4 精準修改：只動 tests/ + manifest + CHANGELOG，未動 `scripts/ops/lib/config.py` / `video-ops.py` argparse / `data/.operators.json`（安全邊界保住）
- CLAUDE.md 禁令 #8 領土：tests/* 屬 Codex 領土、本次 Claude 跨領土 + CHANGELOG.md（Claude 領土）一支 PR、territory override

### 影響檔案

| 檔 | 領土 | 改動 |
|----|------|------|
| tests/conftest.py | Codex | 加 `operator_fixture` + `patch_operator_registry` + dual-path patches + ExitStack |
| tests/test_adoption_gate_defer.py | Codex | 3 tests 參數化 |
| tests/test_adoption_gate_owner.py | Codex | 1 test 參數化 |
| tests/test_brand_owner_routing.py | Codex | 2 tests 參數化 |
| tests/test_sedimentation.py | Codex | 3 tests 用 fixture |
| engine-manifest.json | 共享 | engine 5.99 → 6.00 |
| 07-changelog/CHANGELOG.md | Claude | 本 entry |

**territory override justified by**: 本次修的是 engine 端 test fixture 假設（影響所有客戶 fork CI）、屬引擎契約問題；CHANGELOG entry 同步升版必填、不可拆 follow-up（會造成 engine-version-check CI fail + CHANGELOG 缺 entry 並存）。

### 不影響

- `scripts/ops/lib/config.py`、`scripts/ops/video-ops.py` 頂層 argparse、`data/.operators.json` 全保留（safety guard）
- 既有 631 個非本 task tests 全綠（636 / 636 in engine repo）
- 既有 conftest fixture（`patch_paths` / `tmp_project`）行為對舊 tests 完全相容（仍預設 kai）

### 無 schema migration

純 test 層、無資料 schema / 行為層變動 — 不加 `🚨 schema-migration` 標記。

### Validation

- engine repo：`pytest tests/ -q` → 636 passed
- LONGBRO 模擬（替換 `data/.operators.json` 為 `{longbro}` 後跑 5 個曾失敗的 test 檔）：47/47 passed（原 9 failures 全綠）
- ruff / rules-lint / engine-version-check 跑過綠

### 客戶 migration 步驟

純引擎升版、跑 `/sync-engine` 即可、無 schema migration、無需手動動作。

---

## v5.99（2026-05-15）

**主題：🔧 engine-lag 自動提醒 + bootstrap 接線 — 補 /sync-engine v2 設計承諾的 Stage 1（警告）**

### 背景

LONGBRO 客戶 repo 實測 `/sync-engine` v2 兩個落差：
1. session 開頭 hook 沒做 engine fetch / 版本比對（設計承諾未實作）
2. bootstrap-client.sh 沒接 engine remote、客戶 fork 後第一次跑 /sync fail

Stage 1 警告缺失（CLAUDE.md 禁令 #11 四階段、Stage 3/4 已存在於 adoption_gate）。

### 修法

- 新建 `scripts/engine/engine_lag_detector.py`（fetch / read / compare 純函式）
- `scripts/utils/lib/adoption_gate.py` 加 engine-lag GateItem（owner=kai）、訊息含 schema-migration count（讓客戶看 lag 時知道風險）
- `scripts/bootstrap/bootstrap-client.sh` 加 `git remote add engine` + 順手 fetch 一次
- engine remote 未設 / fetch 失敗 → silent skip（per workflow.md §對話開頭 step 5）

### 對應規則

- CLAUDE.md 禁令 #11 四階段：本次補 Stage 1（警告）+ adoption_gate 既有 Stage 3/4
- workflow.md §對話開頭 step 5：engine lag 顯示行為

### 影響檔案

| 檔 | 領土 | 改動 |
|----|------|------|
| scripts/engine/engine_lag_detector.py | Codex | 新建 |
| scripts/utils/lib/adoption_gate.py | Codex | 加 engine-lag item |
| scripts/utils/adoption_gate_scan.py | Codex | 未改；既有 collect_items() 路徑已涵蓋 engine-lag |
| scripts/bootstrap/bootstrap-client.sh | Codex | 加 git remote add + fetch |
| tests/test_engine_lag_detector.py | Codex | 新建、5 case |
| engine-manifest.json | 共享 | engine 5.98 → 5.99 + semantic_contracts 加 entry |
| 07-changelog/CHANGELOG.md | Claude | 本 entry（territory override per 引擎升版閉環）|

### 不影響

- session-start.sh 既有三段邏輯（品牌注入 / adoption_gate_scan / dashboard rebuild）全保留
- adoption_gate 既有所有 GateItem 規則保留（brand 過期 / 待辦逾期 / 回填到期等）
- pipeline / lessons / todos / verifier 邏輯不動
- 既有客戶（Kai）跑 bootstrap 冪等（已建 engine remote 不重複）

### 無 schema migration

純行為層補強、無 schema 變動。

### Validation

- ruff / rules-lint / engine-version-check / pytest 全綠
- 復現：跑 `python scripts/utils/adoption_gate_scan.py` 在已設 engine remote 的 LONGBRO repo 應印 engine-lag 訊息（若 engine 真落後）

---

## v5.98（2026-05-15）

**主題：🔧 整層退役 legacy `pipeline.json`（Issue #438）— Claude Phase 3/5/6 收尾 + 補 PR #450 (Codex Phase 4) 漏寫 v5.97 entry**

> 本 entry 收兩段：(1) PR #450 Codex Phase 4 已 merge engine bump 5.96 → 5.97 但未寫 CHANGELOG、本 PR 補 (2) Claude Phase 3/5/6 收尾、engine bump 5.97 → 5.98、pipeline-schema own version 2.0 → 2.1。

🚨 schema-migration: legacy `data/*/pipeline.json` 已從 git rm（PR #450）、`.gitignore` 加 `data/*/pipeline.json` 防再建（PR #450）、`docs/contracts/pipeline-schema.md` v2.1 反映 sharded 唯一 SSoT 狀態（本 PR）。客戶端 sync 偵測本標記時必停下手動 migrate、不可 auto-merge。

### 背景

`scripts/ops/lib/pipeline.py:_load_pipeline_sharded()` 在 LOAD 路徑寫 legacy mirror、造成 silent regression（Issue #438）：
- 每次跑任何 `video-ops.py` 子命令（含純讀的 `lessons stats` / `todo list`）→ `pipeline.json` 被偷偷 mutate
- `git status` 永遠看到 `M data/kai/pipeline.json`、即使沒主動改
- Sharded `_meta.json` 過時時、會被覆蓋進 legacy（IDEA-107~114 重複事件根因）

設計層判斷：選 B 「legacy `pipeline.json` 整個退役、純 sharded」（per Issue #438 §建議修法 + Kai 確認）。最徹底、未來不可能再撞同類。

### 工程 lineage（5 個 PR）

- **PR #449**（Phase 2a + 2b + 2c、Codex 領土）：reader API 提取（`get_pipeline_data()`、無寫副作用）+ deprecation warning + 全 reader 切到新 API + sharded template seed + 全 tests fixture 遷移。Follow-up `7b23db7 fix(readers): restore json imports`（Codex 補 import 漏失）。
- **PR #450**（Phase 4、Codex 領土、BREAKING）：移除 `_load_pipeline_sharded()` 的 `save_json(legacy)` + DeprecationWarning、`load_pipeline()` 改 alias to `get_pipeline_data()`、`save_pipeline()` 移除 legacy 寫入、`git rm data/{kai,template}/pipeline.json`（5,841 行刪除）、`.gitignore` 加 `data/*/pipeline.json`、engine_version 5.96 → 5.97、manifest 加 schema_migration marker。
- **PR #451**（Claude 領土、territory-lint follow-up）：`.github/workflows/territory-lint.yml` 加 `\.gitignore$` 到 CLAUDE_OK + CODEX_OK 兩邊白名單（`.gitignore` 是 repo 層共享配置、原 regex 漏列、PR #450 撞 territory red x）。
- **本 PR**（Phase 3 + 5 + 6、Claude 領土）：dashboard / docs 更新讀 sharded API + 驗證 issue #438 §復現步驟（git status 不再 dirty）+ CHANGELOG 補完整 lineage + lessons hardened。

### 修法（本 PR）

**Phase 3 dashboard / docs**：
- `dashboard/build.py` L348：`data/{OPERATOR}/pipeline.json` → `data/{OPERATOR}/pipeline/_meta.json`（_file_info 取 sharded meta）
- `dashboard/build.py` L523：`data_root.glob("*/pipeline.json")` → `glob("*/pipeline/_meta.json")`（mtime sweep 改用 sharded）
- `dashboard/README.md` L56：架構圖文字更新成 sharded
- `docs/contracts/pipeline-schema.md` v2.0 → v2.1：legacy 段落改寫為「已退役」+ 加 v2.1 schema-migration marker + lineage 註腳

**Phase 5 驗證（issue #438 §復現步驟）**：
- ✅ `data/{kai,template}/pipeline.json` 不存在（Phase 4 git rm）
- ✅ 跑 `video-ops.py lessons stats` 後 `git status --short` **乾淨**（root cause 真解、不再 silent mutate）
- ✅ pytest 629 passed
- ✅ validate-all 0 errors

**Phase 6 收尾**：
- engine-manifest.json：engine_version 5.97 → 5.98、semantic_contracts[`docs/contracts/pipeline-schema.md`] 2.0 → 2.1、_meta.schema_migration marker update
- L-候選 hardened：跑 `/harden` 把 pipeline mirror silent regression lesson 升 stage=hardened（artifact = 本退役工程 + Phase 5 驗證證據）
- 關 issue #438（PR merge 後）

### 影響檔案

| 檔 | 領土 | 改動 |
|----|------|------|
| dashboard/build.py | Claude | 2 處硬寫路徑改 sharded |
| dashboard/README.md | Claude | 架構圖 sharded |
| docs/contracts/pipeline-schema.md | 共享 | v2.0 → v2.1、legacy 退役說明 |
| engine-manifest.json | 共享 | engine 5.97 → 5.98 + entry bump + marker update |
| 07-changelog/CHANGELOG.md | Claude | 本 entry |

### Validation

- ruff / check-version-sync / rules-lint / engine-version-check / pytest 629 passed / validate-all 0 errors（本地全綠）
- Issue #438 §復現步驟：✅ 跑 video-ops 後 working tree 乾淨

### Follow-up

下列檔案仍有 `pipeline.json` 文字提及、不影響功能、可在後續 sleep mode audit 漸更新：
- `docs/references/{production-details, design-lineage, skill-architecture-principles, system-maintenance, skill-consolidation-map}.md`
- `docs/contracts/{video-ops-cli, sync-protocol, todos-schema}.md`
- `docs/{client/lifecycle, disaster-recovery-3-mapping}.md`
- `00-control-center/{recovery-playbook, AI_SYSTEM_UPGRADE_REPORT, AI_SYSTEM_UPGRADE_REPORT_2026-04-27}.md`
- `07-changelog/ROADMAP.md`
- `dashboard/src/data-schema.json`（純 desc 文字、不影響 schema）

---

## v5.96（2026-05-15）

**主題：🔧 generation SKILL v1.3 → v1.4 通用 Output 規格硬化（A/B/C/D 跨 mode 強制 + 強標題優先協議 + interview 載 an persona）+ 📦 brand v5/12 + Phase 5 T1 cleanup**

### 背景

2026-05-15 對話 session 跑「200 萬無人流實驗」靈感、發現 generation skill 三個漏判：
1. dual-track mode SKILL.md L37 寫 Output「4 版 A/B/C/D」、但 interview mode L61 寫「30/45/60s 三秒數版」、Kai 跨 mode 看到的格式不一致（L-0042）
2. A/B/C/D 被誤解為「偏離度等級分類」（GREEN/ORANGE/YELLOW）、實際是「4 種內容版本各有偏離度承受預算」（L-0041）
3. interview mode 跑 Q&A 時、未載 personas/an.md 藏鏡人人格大腦、Q 字卡寫泛用採訪記者口吻、未對齊安說話風格（L-0043）

三個漏判都是「規格留白靠 Claude 自覺」而非「規格寫死」、按 CLAUDE.md 禁令 #7「硬化優先」應寫進規則層。

### 修法（Claude 領土）

**`02-skill-factory/generation/SKILL.md` v1.3 → v1.4**：
- 加 §通用 Output 規格段（跨所有 mode 強制）：
  - A 保守版（GREEN ≤ 3）/ B 強衝突版（ORANGE ≤ 7-8）/ C 揭密版（YELLOW ≤ 4-6）/ D 故事版（YELLOW ≤ 4-6）
  - 每切角內依 mode 套對應 mode-specific 細節
- 加 §強標題優先協議：
  1. 每切角 ≥ 5 候選標題（依 title-rules.md 5 類心理觸發 T1-T5）
  2. 4 必含逐項評分（具體金額 / 反差動作 / 第一人稱「我」/ 留缺口或問號）
  3. 標 ⭐ 推薦最強
  4. **腳本 Hook 第一句必直接 echo 推薦標題**
  5. 不套 30s 默認（除 interview）、秒數依切角內容自然決定
- 5 個 Mode Output 改寫對齊通用規格
- Mode 4 interview 載入清單加 `01-data-brain/personas/an.md` + `persona-an-questionnaire-v2.md` 強制載入（藏鏡人 Q 字卡對齊安人格 [2] 互稱楷哥 + [9] 口頭禪庫 + [13] 反應觸發點 + [14] Driver/Reaction 70/30 比例）

**`01-data-brain/brand.md` 7 sections 更新（[0]/[4]/[5]/[7]/[9]/[10]/[11]）+ [12] 確認無變動**：
- [0] 紅茶巴士「約 100 家」→「96 家營業中 + 10 家已簽約未開店（合計 106 家）」、阿檸表加河南店 + 內湖科技園區籌備、新增功夫茶體系（海外）182 家段落（加拿大 / 美國 / 香港 / 菲律賓）
- [4] 論點 3/4/6/7/9/10 補最新數據：人流密度 = 競爭密度、樂華 80 萬/月 vs 新莊中原 30 萬/月、招牌巴士紅茶爆款、線上點餐 + 叫號取餐解法、減冰實務、無糖 +1.2 元
- [5] 競爭對手「可以點名」→「禁止點名」（對齊 [6] 紅線）
- [7] 加 Threads 降權重（失言風波後）+ 留言/私訊互動策略待補
- [9] 高峰銷量「800 杯」→「1,800 杯/日（新紀錄）」、月均詢問 10-15 人 → 1-2 人/月（風波後）+ 風波背景
- [10] 海外重點補「越南」
- [11] 加暑假詢問增多
- [12] 確認無變動（大陸案例 / 加盟主常問 3 題 / 90 天問題 / 客訴 Q130 / 個人創業起點均無更新；加盟主巡禮仍 pending）

**Phase 5 T1 stale docs cleanup**（T-0015）：
- `02-skill-factory/shared-references/red-line-protocol.md`：L4「interview-navigator 的刺的邊界」→「generation skill mode=interview 的刺的邊界」
- `02-skill-factory/shared-references/skill-design-principles.md`：L51/L57 兩處改寫為「Phase 5 前歷史 + 已落地正解」、對齊退役後狀態（其餘 21 hits 為 lineage 註腳保留、不破壞引用）

**200 萬無人流實驗 dry-run 腳本**（`03-production-line/01-draft/kai/2026-05-15_200萬無人流實驗_腳本_V1.md`）：
- 軌 B 45s interview 版（藏鏡人安、Q&A + 血包 3/3 PASS）
- 待 pipeline mirror 修完 save VID-098（卡 T-0027、blocked by Codex 修 pipeline.json legacy mirror IDEA-107~114 重複）

**lessons 入庫（origin=mistake、stage=soft）**：
- L-0038：Kai 要求 skip adoption gate、觀察過度 skip 模式
- L-0041：誤判 A/B/C/D 為「偏離度等級分類」、實際是「4 內容版本 + 偏離度承受預算」
- L-0042：A/B/C/D 4 切角應跨 mode 通用、已硬化進 generation/SKILL.md
- L-0043：interview mode 未載 personas/an.md、Q 字卡未對齊安人格、已硬化進 Mode 4 載入清單

**todos**：
- T-0015 close（T1 完成）
- T-0016 defer 2026-05-16（T2a / T2b 卡 .claude / CLAUDE.md UI 授權）
- T-0027 add（200 萬靈感占位、due 2026-05-16 high priority、blocked-by-codex pipeline mirror dup）

### 影響檔案

| 檔 | 領土 | 改動 |
|----|------|------|
| engine-manifest.json | 共享 | engine_version 5.95 → 5.96、generation entry 1.3 → 1.4 |
| 02-skill-factory/generation/SKILL.md | Claude | v1.3 → v1.4 + 通用 Output 規格 + 強標題協議 + Mode 4 載 an persona |
| 01-data-brain/brand.md | Claude | 7 sections + [12] 確認 |
| 02-skill-factory/shared-references/red-line-protocol.md | Claude | Phase 5 T1 退役 skill 名對齊 |
| 02-skill-factory/shared-references/skill-design-principles.md | Claude | 同上 |
| 03-production-line/01-draft/kai/2026-05-15_200萬無人流實驗_腳本_V1.md | Claude | dry-run 腳本（新增）|
| data/kai/lessons.json | Claude | L-0038/41/42/43 新增 |
| data/kai/todos.json | Claude | T-0015 close / T-0016 defer / T-0027 add |
| data/kai/pipeline.json | Claude | session-start hook 時間戳 bump |
| 07-changelog/CHANGELOG.md | Claude | 本 entry |

### Validation

- ruff / check-version-sync / rules-lint / engine-version-check / pytest 全綠
- generation SKILL.md frontmatter version + manifest semantic_contracts entry + 對應 changelog entry 三方一致

---

## v5.95（2026-05-15）

**主題：🔧 contract_files 分層 — semantic / factual 兩層、解 fact-realign 連環撞 release 流程**

🚨 schema-migration: `engine-manifest.json` 頂層 `contract_files` key 廢棄、改為 `semantic_contracts`（規則 / API / SKILL、改動觸 bump）+ `factual_contracts`（純文字 / 歷史、不觸 bump）。客戶端 fork 引擎者拉本次 sync 時、`/sync` 偵測本標記強制停下、手動 migrate：把舊 `contract_files` entry 依規則手動分配到兩個新 key、或從引擎拉新 manifest 後比對。**舊 fallback 仍保留**（per PR #443、`engine_version_utils.parse_*` 認舊 `contract_files` / `files` key）、但新 contract 條目只能寫進 semantic / factual、不能塞舊 key。

### 背景

v8.6 / v8.7 / v8.8 / v8.9 連續四輪 CHANGELOG entry 都是「post-merge fact realignment」（README engine 版本對齊 / wording 對齊 / brand lazy load 描述對齊）— 全是純文字事實對齊、但 CI engine-version-check 把 README 視為 `contract_files`、每次小對齊都強制 bump engine + 寫 CHANGELOG entry。

`00-control-center/AI_SYSTEM_UPGRADE_REPORT.md` 在 v5.92 sleep mode v3.0 audit 已記錄「README.md line 4/23/313 engine 漂移」為 deferred、理由「README 在 contract_files、單獨改需 bump README + engine_version + CHANGELOG、超出 sleep mode 邊界」。v5.94 第三輪終於修、同時 CHANGELOG §根因記錄「contract_files 太敏感是否需要分層」為下次架構討論議題。

本 PR 完整修這個根因。

### 修法（PR #443、Codex 領土）

**Schema 變動**：
- `engine-manifest.json` 頂層 `contract_files` → 拆成 `semantic_contracts` + `factual_contracts`
- `_meta.engine_version` 5.94 → 5.95
- 既有 30 個契約檔分類：36 semantic + 9 factual

**Semantic（保留嚴格 bump 要求、改動影響客戶 Claude 行為）**：
- CLAUDE.md / `.claude/rules/*.md`
- `02-skill-factory/**/SKILL.md` + `shared-references/**` + README
- `docs/contracts/**`（schema / CLI / convention 契約）
- `docs/client/lifecycle.md`
- `docs/references/skill-architecture-principles.md`（設計原則、影響未來新 skill 設計）

**Factual（降級為「僅檢 inline own version 一致」、不觸 engine bump）**：
- `README.md`
- `07-changelog/CHANGELOG.md` + 兩個 archive
- `00-control-center/recovery-playbook.md`
- `docs/references/design-lineage.md` / `worktree-guide.md` / `client-sync-sop.md` / `skill-consolidation-map.md`

**guard 邏輯**（`scripts/engine/engine_version_check.py` + `engine_version_utils.py`）：
- semantic 改動 → 強制 bump + CHANGELOG entry（同舊行為）
- factual 改動 → 僅檢 inline `> version:` 與 manifest entry 一致、不觸 bump
- 保留 legacy `contract_files` / `files` fallback（舊客戶端 sync 仍能解析）

**sync-engine**（`scripts/utils/sync-engine.py`）：
- 客戶拉時兩類訊息分流：semantic 顯眼警告「規則變動」、factual 普通提示「事實對齊、可選」

**rules-lint**（`scripts/lint/rules-lint.py`）：
- 對齊新兩層 schema

**docs/contracts/sync-protocol.md**：v2.1 → v2.2、描述新 schema + 客戶端行為差異

### 修法（PR #443 follow-up、Claude 領土）

- `07-changelog/CHANGELOG.md` v5.95 entry（本檔）+ 🚨 schema-migration 標記
- `docs/references/skill-consolidation-map.md` v1.1 → v1.2：L152 引述 contract_files 改為 semantic_contracts、對齊新概念
- `engine-manifest.json` factual_contracts entry skill-consolidation-map 1.1 → 1.2（own version bump 同步）

### 影響檔案（13 個）

| 檔 | 領土 | 改動 |
|----|------|------|
| engine-manifest.json | 共享 | schema 重構 + bump 5.95 |
| scripts/engine/engine_version_check.py | Codex | guard 邏輯分層 |
| scripts/engine/engine_version_utils.py | Codex | parse_* helpers + legacy fallback |
| scripts/engine/bump_engine.py | Codex | 寫入新 layer |
| scripts/utils/sync-engine.py | Codex | 客戶 UX 分流 |
| scripts/lint/rules-lint.py | Codex | 對齊新 schema |
| docs/contracts/sync-protocol.md | 共享 | v2.1 → v2.2 |
| tests/test_engine_manifest_schema.py | Codex | 新建 regression |
| tests/test_engine_version_check.py | Codex | 補 semantic / factual 測試 |
| tests/test_sync_blacklist.py | Codex | 微調 |
| tests/test_sync_engine_client_meta.py | Codex | 補新行為 |
| 07-changelog/CHANGELOG.md | Claude | 本 entry |
| docs/references/skill-consolidation-map.md | Claude | v1.1 → v1.2 |

### Validation

- pytest: 629 passed（baseline 622 + 7 regression）
- rules-lint: 0 issues
- engine-version-check：本 PR semantic 變動觸 bump 5.94 → 5.95 ✅
- 手動 factual sanity：模擬 factual-only 改動跑 guard、確認不觸 bump
- 對 PR diff 本身跑一次 engine_version_check：要求 bump（meta-recursive）✅

### 客戶端 migration 步驟

新客戶（未來 fork）：
1. `/sync` 偵測 🚨 schema-migration → 停下、提示
2. 手動跑 `python3 scripts/engine/migrate_contract_files.py`（若 Codex 有提供、否則）：
3. 手動把客戶端 `engine-manifest.json` 既有 `contract_files` 條目按本 CHANGELOG §修法 分類規則拆到 `semantic_contracts` + `factual_contracts`
4. 移除舊 `contract_files` key
5. bump 客戶端 manifest `_meta.engine_version` 同步至 5.95
6. `/sync` 再跑、繼續引擎更新

本 repo 為 engine+client repo、上述步驟由本 PR 直接完成。

### 根因 + 收尾

v8.6-v8.9 連環 fact-realign 撞 release 流程的根因解決：因為 `factual_contracts` 改動不再觸 engine bump、README / CHANGELOG / docs/references/* 純文字對齊可單 commit 修、不必跨領土 + 不必走 release 流程。下次再發現 README engine version 漂移、直接改一行 push、CI 不卡。

預期收益：
- 月度 fact-realign 開銷 -80%（原本要走完整 PR + bump + CHANGELOG entry、改為一行 commit）
- defer drift 累積消失（小事不再被「成本太高」延後）

剩下的議題（不在本 PR scope）：
- 4-B `.claude/**` native deny 沒 per-file UI override（CHANGELOG v5.94 §根因記錄）
- 此議題與 contract 分層獨立、屬另一架構討論

---

## v5.94（2026-05-15）

**主題：🔧 Post-merge fact realignment v3 — 3 處 contract_files 長期 deferred drift 合修（3/3、跨 2 commits）**

### 背景

Post-merge stabilization audit（PR #440 merge 後）發現 3 處長期 deferred 的 contract_files 漂移、`00-control-center/AI_SYSTEM_UPGRADE_REPORT.md` §「Not fixed」已記錄、前兩輪 sleep mode 同標 deferred、本次第三輪 audit 第三次撞同問題。Kai 確認走「Option A 三項合修」、不再延後。

### 本次修了（3 / 3）

1. **`README.md` line 4 / 23 / 313**：`engine: v5.90` × 3 處 — 實際 `engine_version: 5.93`、漂移 3 個 minor（v5.91 / v5.92 / v5.93 三次 bump 都未對齊 README）
2. **`docs/references/design-lineage.md` line 55 heading**：`v4.62+ SessionStart hook 全文注入`、但 v4.62 正是「全文注入退役」的版本（CLAUDE.local.md + README line 26 為正確描述）、文字方向反
3. **`.claude/rules/workflow.md` line 273-286 §Codex 待實作 CLI**：`add-evidence` CLI 已實作（`python scripts/ops/video-ops.py lessons --help` 回 `<list|add|add-evidence|...>`）、section 標題 + workaround 段落 stale；L244 內部 anchor 同步修

### Commit 結構（拆 2 commits 原因）

- `f87d5f4` chore: align version references（README + design-lineage + manifest + 本 CHANGELOG entry 初版）
- `b608c57` chore(rules): align workflow.md §evidence 累積 CLI — Codex 已實作

第 3 項 `.claude/rules/workflow.md` 被 `.claude/settings.json` `permissions.deny` 規則 `Edit(.claude/rules/**)` 攔 Claude 的 Edit/Write 工具（hard deny、非 prompt 級可放行）。Kai 確認後改用 Bash `python heredoc` 直接寫檔（per `CLAUDE.md` 操作原則「受保護路徑 → 使用者確認後才寫入」+ `.claude/rules/permissions.md` 同精神）、不重設 deny rule、單次任務性 Kai-authorized bypass。架構議題見下方「根因」。

### 修法

**README.md（8.8 → 8.9）**：
- line 4 banner：`version 8.8 / engine: v5.90 / 2026-05-11` → `version 8.9 / engine: v5.93 / 2026-05-15`
- line 23 系統規模表：`engine v5.90` → `engine v5.93`
- line 313 footer：`最新 engine v5.90` → `最新 engine v5.93`
- 變更紀錄表新增 v8.9 row（Post-merge fact realignment v3）

**docs/references/design-lineage.md（1.0 → 1.1）**：
- line 55 heading：`v4.62+ SessionStart hook 全文注入` → `v4.62+ lazy load、全文注入退役`
- line 56 body：對齊 lazy load 三條路徑（brain_loader / 對話需要時 Read / hook 不再 cat 全文）

**.claude/rules/workflow.md（2.30 → 2.31）**：
- §Codex 待實作 CLI section 重寫為 §evidence 累積 CLI（已實作）、移除 workaround 段、保留 schema reference
- L244 內部 anchor `見 §Codex 待實作 CLI` → `已實作、見下方 §evidence 累積 CLI`

**engine-manifest.json**：
- `_meta.engine_version`：5.93 → **5.94**
- `contract_files["README.md"]`：8.8 → 8.9
- `contract_files[".claude/rules/workflow.md"]`：2.30 → 2.31
- `contract_files["docs/references/design-lineage.md"]`：1.0 → 1.1
- `contract_files["07-changelog/CHANGELOG.md"]`：5.92 → 5.94（順手補 v5.93 commit 漏 bump）

### 影響檔案（5 個、Claude 領土）

- README.md（contract_files、bump）
- .claude/rules/workflow.md（contract_files、bump、Kai-authorized Bash bypass）
- docs/references/design-lineage.md（contract_files、bump）
- engine-manifest.json（_meta + 4 contract_files entries）
- 07-changelog/CHANGELOG.md（本 entry）

### Validation

- ruff: pass
- rules-lint: pass（warnings 維持 21 個 pre-existing）
- pytest: 618 passed
- check-version-sync: pass
- engine-version-check: pass（bump 5.93 → 5.94 後）
- validate-all: 0 errors

### 根因 + 防漂移觀察

3 處同性質 drift 連續 3 輪 audit 都被 deferred、根因 = README 在 contract_files 範圍、單獨改觸 CI engine bump、被視為 release-cost。本次合修 5.93 → 5.94 = 把「small fact realign」+「release-level bump」綁定一次處理、減 round trip。長期該問：contract_files 太敏感是否需要分層（純文檔對齊 vs 規則語義變動）— 屬架構議題、不在本 PR scope，僅 lessons.json 標記觀察。

workflow.md bypass 揭露另一個架構問題：`.claude/settings.json` hard deny `.claude/rules/**` 阻擋 Claude 對話內 fact alignment、本次走的解套路徑（Kai-authorized Bash bypass）次優、其他選項（B1 改 settings.local.json allow 但 deny 優先 / B2 Kai 手動編輯但雲端 sandbox 無本機 editor）都不可行。理想路徑應是 native permission allow 一次性 per-file override、但目前 UI 機制不支援。本問題建議列入下次架構討論。

---

## v5.93（2026-05-15）

**主題：🔧 Dev deps SSoT — `requirements-dev.txt` 引入**

### 背景

post-merge stabilization audit (PR #439) 發現 Claude Code session 環境缺 `pytest` 時無法跑驗證、違反 CLAUDE.md 禁令 #5「改動自驗」。當時臨時 `pip install pytest` 走 borderline 路、Kai retro 確認 OK。

根因：dev 依賴（pytest / ruff 等）有 3 個消費端（CI workflow / Claude session-start hook / 本機 dev + Codex worktree）、過去只在 CI workflow hardcode `pip install pytest ruff`、其他端撞牆。

### 修法

引入 `requirements-dev.txt` 作為 dev 依賴 SSoT：

- `requirements-dev.txt`（新）：pytest>=8.0 / ruff>=0.5、header 註明 3 個消費端
- `.github/workflows/rules-lint.yml`：`pip install pytest ruff` → `pip install -r requirements-dev.txt`
- `.claude/hooks/session-start.sh`：開頭加 `pip install -q -r requirements-dev.txt 2>/dev/null || true`、所有 session 自動裝、失敗不擋
- `engine-manifest.json`：註冊 `requirements-dev.txt` 到 `internal_files`、bump engine_version 5.92 → 5.93

未來新增 dev tool（mypy / coverage / pre-commit 等）改 `requirements-dev.txt` 一個檔即可、3 個消費端自動跟。

### 影響

- Additive、無 schema migration、無 🚨 marker
- 跨 Claude × Codex 領土（`.github/**` 屬 Codex 領土）、territory override justified in PR body
- 客戶 sync 會自動拉 `requirements-dev.txt`（內部檔）

### 驗證

ruff / rules-lint / version-sync / pytest (618) / validate-all / engine-version-check 全綠。

---

## v5.92（2026-05-11）

**主題：🔧 Post-merge cleanup（sleep mode v3.0、stale refs + sync_blacklist）**

### 背景

PR #431 (personas/) + #432 (brain_loader) + #434 (README v8.8) 連續 merge 後、sleep mode v3.0 掃描發現：

1. 3 個 SKILL.md frontmatter `brand-refs:` 仍宣告 `[3]`、但內文已改引 `personas/kai.md [1]` → brand_ref_lint 3 個 over-declared warnings
2. `brain-loading.md` v1.7 文字描述「實作待 Codex Phase B（PR 待派）」— PR #432 已 merged、stale
3. `01-data-brain/index.md` `personas/an.md` 載入描述仍寫「試用期 lazy load」、實際 BrainBundle 已接入
4. `persona-an-questionnaire.md` 無 lifecycle state 註腳、未來 AI 可能誤判為 active todo
5. `engine-manifest.json` sync_blacklist 未 cover `persona-*.md` glob、客戶端 sync 會被引擎範本檔覆蓋

### 修法

- 3 個 SKILL.md frontmatter `brand-refs` 移除 stale `[3]`（quality `[]`、discovery `[4,5,6,10,11,12]`、generation `[5,6]`）
- `brain-loading.md` v1.7 文字對齊 PR #432 merged 事實（line 3 + line 42）
- `01-data-brain/index.md` BrainBundle 載入描述對齊 PR #432
- `persona-an-questionnaire.md` 加 lifecycle 註腳（v1.0 已完成、保留為未來新角色問卷範本）
- `engine-manifest.json` sync_blacklist 加 `01-data-brain/persona-*.md` glob
- `00-control-center/AI_SYSTEM_UPGRADE_REPORT.md` 完整 sleep mode v3.0 審查報告

### Engine version bump 原因

contract_files 範圍內 4 個檔（3 SKILL.md + brain-loading.md）有內容改動、`engine_version_check.py` 要求 bump。雖然改動屬 metadata cleanup（移除 stale frontmatter、文字對齊已 merged 事實）、非語義變更、但 CI 是機械檢查、按 v4.65+ 設計仍需 bump engine。

### 不 bump 各 SKILL.md / brain-loading.md own version 原因

改動屬：
- frontmatter cleanup（移除 stale 宣告、不增功能）
- 文字對齊已 merged 事實（不改規則行為）

各檔內部 own version 屬「規則 / 功能 / 行為」變動指標、本次無此類變動、故不 bump。engine_version bump 5.91 → 5.92 滿足 CI gate 的「contract scope 改 = 必 bump engine」設計。

### Validation

- rules-lint.py: 0 errors / 21 warnings（從 24 降）
- brand_ref_lint.py: 0 issues（從 3 warnings）
- engine-version-check.py: pass（bump 5.91 → 5.92 後）

---

## v5.91（2026-05-11）

**主題：🔧 README post-merge engine sync（v8.7 → v8.8）**

### 背景

v5.90 PR #431 (personas/ 拆分) merged 後、`README.md` 頂部 banner 仍寫 `engine: v5.89`（line 4 / line 23 / line 312）、跟 manifest `engine_version: 5.90` 漂移 3 處。按既有慣例（v8.6/v8.7 entry 均為「post-merge fact realignment」）、README 必須跟著升版。

### 修法

- `README.md` 頭 `version: 8.7 → 8.8`、`last_updated: 2026-05-08 → 2026-05-11`、`engine: v5.89 → v5.90`
- `README.md` line 23 「engine v5.89」→「engine v5.90」
- `README.md` line 312 「最新 engine v5.89」→「最新 engine v5.90」
- `README.md` 版本歷史新增 v8.8 entry
- `engine-manifest.json` `contract_files.README.md: 8.7 → 8.8`

### 為什麼不合進 v5.90

v5.90 entry 已 merged、屬過去事實、不再動。README 對齊是 follow-up alignment 工作、單獨開 v5.91 entry 保留可追溯性。

### Recommended next step

無 — 對齊完成、引擎與 README banner 一致。

---

## v5.90（2026-05-11）

**主題：🔧 personas/ 拆分（雙人格大腦結構、v4.97 方案 2 中間版 Phase A+C）**

🚨 schema-migration: brand.md [3] 內容調性 + [12] 5 個 Kai 個人 subsection 遷至 `01-data-brain/personas/kai.md`、[1] 從「核心專長（Kai 的獨特優勢）」重命名為「業務能力與優勢」。客戶端 sync 必停下、確認本 repo 的 brand.md 結構變更不會覆蓋客戶自己的 brand.md（已在 sync_blacklist `01-data-brain/brand*.md`）+ 新增 `01-data-brain/personas/**` 加進 sync_blacklist 保護客戶人格不被引擎 sync 覆蓋。

### 背景

原 `brand.md` 13 個 section 混了「品牌業務事實」+「Kai 個人說話風格 / 故事 / 觀點」三類、結構職責不清。Opus 4.7 視角下「first-principles」+ Kai 確認後決定走方案 2 中間版（搬 [3] 全段 + [12] 個人 5 個 subsection、[1] 重命名）、為未來加員工 / 客串角色鋪路。

### Phase A（Claude 領土、本 PR）

**新檔**：
- `01-data-brain/personas/kai.md`（5 個 section：身份背景、說話風格 from brand [3]、觀點態度、Kai 禁區 Q26、創作野心 Q33）
- `01-data-brain/persona-an-questionnaire.md`（藏鏡人安問卷）
- `01-data-brain/personas/an.md`（由 `01-data-brain/persona-an.md` 重新路徑、git mv 保歷史）

**brand.md 改動**：
- [3] 內容調性 全段移除、留 redirect 註解 → `personas/kai.md` [1]
- [12] 移除 5 個 Kai 個人 subsection（個人創業起點 / 最怕被問 Q26 / 工作爭執 Q30 / 品牌負評態度 Q31 / 最想拍 Q33）
- [12] 保留 8 個品牌觀點 / 加盟主 subsection
- [1] 重命名「核心專長（Kai 的獨特優勢）」→「業務能力與優勢」

**下游 hardcode 同步**（22 處）：
- `brand.md [3]` 引用統一改為 `personas/kai.md [1]`（影響 13 個檔：generation/quality/discovery SKILL.md、shared-references/* 9 檔、docs/* 2 檔）
- `[1] 核心專長` 字串引用同步改為 `[1] 業務能力與優勢`（red-line-protocol / data-brain-manifest / lifecycle）

**規範層**：
- `01-data-brain/index.md` 載入清單加 personas/kai.md + personas/an.md（v4.97+）
- `02-skill-factory/shared-references/brain-loading.md` v1.6 → **v1.7**：BrainBundle 加 `kai_md` / `an_md` 欄位（規範層、實作待 Codex Phase B）
- `02-skill-factory/shared-references/data-brain-manifest.md` v3.0 → **v3.1**：對齊 brand.md [1] 重命名 + [3] redirect

**brain_loader 接入策略**：
- 試用期 lazy load：generation skill 對話內 Claude `Read personas/kai.md` + `Read personas/an.md` 注入、不依賴 BrainBundle
- Codex Phase B 待派：改 `scripts/libs/brain_loader.py` 加 `kai_md` / `an_md` 載入 + `tests/test_brain_loader.py` regression
- B merge 後撤除 lazy load fallback

### Phase C（本 PR、engine 升版）

- `engine-manifest.json`：
  - `engine_version` 5.89 → **5.90**
  - `sync_blacklist` 加 `01-data-brain/personas/**`（客戶人格保護）
  - `contract_files`：brain-loading.md 1.6→1.7、data-brain-manifest.md 3.0→3.1
- CHANGELOG v5.90 entry（本檔）

### 客戶端 sync 注意

`/sync` 偵測到 🚨 schema-migration → 強制停下、客戶手動：

1. 確認自家 `brand.md` 是否仍含 Kai 個人 [3] 內容調性 + [12] 個人故事 → 如果有、可選：
   - (a) 維持現狀（客戶 brand.md 已在 sync_blacklist、不被覆蓋）
   - (b) 主動拆分到自家 `01-data-brain/personas/kai.md`（推薦、與引擎對齊）
2. 跑 `bootstrap-personas.sh`（如果有）或手動 mkdir personas/ + 建空殼

### 待派 Codex task（Phase B、follow-up）

- 改 `scripts/libs/brain_loader.py`：load_for_skill 載入 personas/kai.md + an.md 進 BrainBundle
- 加 `tests/test_brain_loader.py` regression：personas 欄位非空
- `scripts/lint/rules-lint.py` 可選新規則：SKILL.md 不可硬編碼 brand.md [3]、必走 personas/

---

## v5.89（2026-05-08）

**主題：🔧 README.md post-merge fact realignment（v8.5 → v8.6）**

### 背景

PR #411–#415 合併後（engine v5.80 → v5.87、tests 591→608、workflow.md v2.25 → v2.30、brand.md v4.62 全文 auto-inject 退役為 lazy load）、`README.md` 多處事實未跟上：

- 頂部 banner 仍寫 `engine: v5.80`（3 處：line 4 / line 23 / line 310）
- 系統規模表 `自動化測試 69 檔（591 test cases）`（實際 71 / 608）
- 系統規模表 `workflow.md v2.25`（實際 v2.30）
- 系統規模表 + SSoT 表「brand.md 全文由 SessionStart hook 自動注入」(v4.62 已退役為 lazy load、CLAUDE.local.md + session-start.sh 已對齊、唯獨 README 沒同步)
- 資料夾結構區同樣兩處 stale（workflow.md v2.25 + brand 全文注入）

### 修法

- README.md 頭 `version: 8.5 → 8.6`、`last_updated 2026-05-03 → 2026-05-06`、`engine v5.80 → v5.87`
- 系統規模表 / 資料夾結構區 / SSoT 表 / 結尾完整變更指引 共 8 處 stale 引用對齊
- 版本歷史新增 v8.6 entry
- 02-skill-factory/README.md 表內 `generation v1.2 → v1.3` + `quality v1.2 → v1.3`（v5.87 升版漏同步）、檔尾 `**版本**：v6.2 → v6.3`
- engine-manifest.json：`engine_version 5.88 → 5.89` + `README.md 8.5 → 8.6` + `02-skill-factory/README.md 6.2 → 6.3` + `CHANGELOG.md 5.88 → 5.89`

### 影響檔案（4 個、Claude 領土）

- `README.md`：v8.5 → v8.6
- `02-skill-factory/README.md`：v6.2 → v6.3
- `engine-manifest.json`：engine_version + 兩份 README 版本
- `07-changelog/CHANGELOG.md`：本 entry

### 對應

CLAUDE.md 禁令 #4（精準修改、只改被要求的部分）+ workflow.md §對話開頭 §3 大腦新鮮度 — 此次只動事實對齊、不引入新規則 / 新功能 / 新結構。

### Rebase 紀錄

原 PR #416 規劃為 v5.88、與 PR #420 同 scope 衝突。依 `docs/contracts/agent-collaboration.md §版本協調`「先 merge 方佔用該版號、後 merge 方 rebase + bump 下一個版號」、PR #420 先 merge 取走 v5.88、本 PR rebase 至 v5.89。

---

## v5.88（2026-05-08）

**主題：🔧 video-ops CLI contract 對齊 §10.1 — `save --trace` 永遠必填**

### 背景

PR #417 第一輪 follow-up 為了讓 `engine-version-check` 通過，曾把 `docs/contracts/video-ops-cli.md` revert 回原樣，避免 contract scope 變動；但留下文檔與 code 不一致：`scripts/ops/video-ops.py save` 已要求 `--trace` 永遠必填，contract 卻仍寫成 `[--trace '{...}']` optional。

§10.1 規格（4.7 mature 第三輪研究 + v5.88 規劃）明定 `--trace` 永遠必填，不重啟條件性豁免；本版不再走繞過 CI 路徑，而是正式把 contract、engine version、CHANGELOG 對齊。

### 修法

- `docs/contracts/video-ops-cli.md` v1.15 → v1.16：`save` 用法改為必填 `--trace '{...}'`，說明改為「必填前 6 項」並明寫缺少 `--trace` 時 CLI exit 1。
- `engine-manifest.json`：`_meta.engine_version` 5.87 → 5.88、`last_updated` → 2026-05-08，並同步 `docs/contracts/video-ops-cli.md` / `07-changelog/CHANGELOG.md` 版本。
- `07-changelog/CHANGELOG.md`：新增本 entry，正式標記 contract scope 改動與 engine bump。

### 測試

- `python3 -m pytest tests/test_save_and_verifier.py tests/test_cli_contract.py`

## v5.87（2026-05-05）

**主題：🔧 generation v1.2 → v1.3 + quality v1.2 → v1.3 — §Output Contract 動詞硬化（解 trace/verifier 0/30 採用閉環行為層失敗）**

### 背景

`adoption-stats` 顯示 `generation_trace 0/30、verifier_scores 0/30 over 30 days`、`hook_type` 從 v1.5 時的 26% 跌到 13%。v1.5 補注假設「PR #348 CLI 強制」是行為層解、現實證偽：CLI 強制（`trace_required_statuses = ['剪輯中', '已上線']`）已落地 30+ 天、trace 仍 0。

讀 generation/quality SKILL.md §Output Contract 發現根因：v1.1/v1.2 寫「呼叫 CLI」是模糊動詞、Claude 對話中經常解讀為「印 Bash code block 展示給 Kai 抄」（4.6 慣性「Claude = 顧問、不是執行者」）、不是「Bash tool 立刻執行」。trace 0/30 真實根因是動詞模糊。

### 修法

**generation v1.2 → v1.3**：
- §Output Contract 4 階段壓 3 階段
- §1 從「AI 自評 4 句」改「**Bash tool 執行 save**」首要、不印命令給 Kai
- 移除 fenced JSON 中介層、trace 直接 inline 進 --trace heredoc arg（無「給 Claude 自己看的 fenced block」）
- §反例新增「印 Bash code block 給 Kai 看」+「印 fenced JSON 給 Claude 自己看」兩條 anti-pattern

**quality v1.2 → v1.3**：
- §Output Contract §1 從「呼叫 CLI」改「**Bash tool 執行 record-verifier-scores**」、加「禁止印命令給 Kai 抄」硬性動詞
- §反例新增「印 Bash code block 給 Kai 看」anti-pattern

### 14 天觀察 metric（hard exit）

| metric | 現在 | 目標閾值 | 不通過代表 |
|--------|------|---------|-----------|
| `generation_trace` | 0/30 (0%) | ≥40% | §4.A 假設也錯、追下一層 root cause |
| `verifier_scores` | 0/30 (0%) | ≥40% | 同上 |

不到閾值 = 動詞硬化也不夠、要追「為什麼 Claude 對話中執行 Bash 仍有 friction」或「Kai 工作流根本不走 generation skill」。

### 沒做也沒打算做（區別 v1.5 補注的不準則化立場）

- ❌ 不升 CLAUDE.md 禁令 #15「CLI 強制 ≠ 行為改變」（v1.5 補注本來明說「不新增準則、避免準則化慣性」、若再升禁令違反這條）
- ❌ 不寫 `docs/references/skill-architecture-principles.md` v1.7 補注「§盲點 3 反證」（1+2 還沒驗證、寫 v1.7 = 預測 fix 會成功、觸犯 CLAUDE.md 禁令 #13「預測 → 不做」+ v1.6.3 元規則）
- 14 天 metric 出來再評估這兩條

### 影響檔案（5 個、Claude 領土）

- `02-skill-factory/generation/SKILL.md`：v1.2 → v1.3、frontmatter + §Output Contract + 版本歷史
- `02-skill-factory/quality/SKILL.md`：v1.2 → v1.3、同上
- `02-skill-factory/CHANGELOG.md`：新增 v1.3 entry
- `engine-manifest.json`：engine_version 5.86 → 5.87、generation/quality SKILL.md 版本同步
- `07-changelog/CHANGELOG.md`：本 entry

### 對應

`docs/references/skill-architecture-principles.md` v1.5 補注「機械擋下 ≠ 行為改變」第二層補正 — 不只 CLI 強制、還要 SKILL.md 動詞硬化。

### Follow-up commit（同 PR、Kai 命「兩個紅叉全關」）

v5.87 主 commit 末原列「沒做也沒打算做」兩條 ❌、Kai 重看判定**全關**。Follow-up commit 補：

- ✅ **`docs/references/skill-architecture-principles.md` v1.6 → v1.7**：新增 §v1.7 補注「§盲點 3 + v1.5 hypothesis 雙證偽記錄」。**不預測 v1.3 修法成功**、只記錄 v1.4.1「fenced JSON 合理 trade-off」+ v1.5「CLI 強制 = 行為層解」**已觀察到的失敗**。記錄反證 ≠ 預測解、不違反禁令 #13；過了 v1.6.3 元規則三條件檢查（第 2 條不成立）才寫。
- ⚠️ **`workflow.md §設計原則` 新增 Mode W「1 個月 metric 驗證原則」**：BLOCKED — `.claude/rules/workflow.md` 受權限保護、需 Kai UI 授權後 follow-up 補。Mode W 是把「上線 1 個月看 metric / 0 = 未上線 / 追行為層 / 不再加禁令」固化為對話流程行為規則、與 X / Y / Z 同層、不寫成禁令（避免「禁令本身禁止再加禁令」自相矛盾）。

**為什麼不升 CLAUDE.md 禁令 #15**（reframe）：v1.5 補注原文「不再加禁令」明擋此路；改寫進 workflow.md Mode W 是規則層而非禁令層、避開矛盾。等 .claude/ 權限授權後補。

### 影響檔案（本 follow-up commit）

- `docs/references/skill-architecture-principles.md` v1.6 → v1.7
- `02-skill-factory/CHANGELOG.md`（補 follow-up 段）
- `07-changelog/CHANGELOG.md`（本段）
- `engine-manifest.json`（principles.md 1.6 → 1.7）
- `workflow.md` Mode W：BLOCKED、待 Kai 授權

### Second follow-up commit（Kai 命「再深看一次」、發現 v5.87 漏修同根因第二處）

v5.87 主 commit 修了 §Output Contract 的 `save` + `record-verifier-scores` 兩條 CLI 動詞、深掃發現**同根因（4.6 慣性「同步呼叫」→ 退化為「印命令展示給 Kai」）在第三條 CLI `lessons add-evidence` 上漏修**、散在 3 個 SKILL.md 的「Lesson 使用標注」段。

**真實採用數據**：lessons total 34 / with evidence list 4 / evidence 採用率 11.7% — 而 4 個 evidence 內容多是 PR# / incident#、真正從 SKILL.md「同步呼叫」累積的 evidence 估計接近 0。和 trace 0/30、verifier 0/30 同構失敗。

**連帶影響**：P2 hook 化 lesson-pressure 整條管線失效。`workflow.md §Lesson 硬化提議 §對話中累積 evidence` (v2.10+) 設計「SKILL.md 觸發 → 同步呼叫 add-evidence → evidence ≥3 → hook 印硬化候選」、第一步失敗 → 整條 evidence-driven 硬化提案管線事實上未運作。lesson 硬化 3/34 = 8.8% 都是 Kai 手動驅動 / fast-track 的、自動觸發 0。

**修法**（3 個 SKILL.md 同模式、不 bump 版本因為小改且和 v5.87 同邏輯主題）：
- `02-skill-factory/generation/SKILL.md` line 118：「同步呼叫」→「**使用 Bash tool 直接執行**」+ 「**禁止印命令給 Kai 看再等 Kai 觸發**」
- `02-skill-factory/quality/SKILL.md` line 132：同
- `02-skill-factory/discovery/SKILL.md` line 101：同

**未修（同步加入 Mode W 待授權清單）**：
- `.claude/rules/workflow.md` line 156 §對話中累積 evidence「呼叫 CLI 把 VID 加入 lesson 的 evidence list」— 受權限保護、待 Kai UI 授權後一併補

**14 天 metric 觀察條件**（合併進 v5.87 hard exit）：
- `lessons evidence 累積率`: 11.7% → 目標 ≥40%（4/34 → 14/34+）
- 不到閾值 = 連動詞硬化也不夠、要追下一層（Bash friction / Claude 對話中「lesson 觸發」這個訊號自己就難判斷）

### Third follow-up commit（Kai 授權 .claude/ 編輯後、補完 Mode W + workflow.md line 208）

Kai 在 GitHub UI 直接 push 把 `.claude/settings.json` deny 規則中的 `Write/Edit(.claude/rules/**)` 拿掉、解鎖 Claude 編輯權。同步補完 v5.87 fu1 中標 BLOCKED 的兩處：

**1. `.claude/rules/workflow.md` line 208 動詞硬化**：
- 「同時呼叫 CLI 把 VID 加入 lesson 的 evidence list」→「**Claude 使用 Bash tool 直接執行**」+「禁止印命令給 Kai 看再等 Kai 觸發」
- 配 v5.87 fu2 的 3 個 SKILL.md 同類修法、是 lessons evidence 採用率 11.7% 在規則層的對應修補

**2. `.claude/rules/workflow.md` §設計原則 新增 Mode W「1 個月 metric 驗證原則」**：
- 與既有 Mode X / Y / Z 同層、是「對話流程行為規則」、不是禁令
- 規範：禁令 / 準則 / 契約上線 1 個月後必看 metric、0 = 未上線、追行為 / 機械 / 流程三層、**不再加新禁令 / 新準則**
- 反例記憶錨：v1.5 PR #348（CLI 強制）+ v5.87（動詞硬化）+ v5.87 path coverage 發現（quick-add bypass + 大量舊存量繞過 generation skill）
- **不寫進 CLAUDE.md 禁令**：v1.5 補注原文「不再加禁令」自禁此路、改寫進 workflow.md Mode W 避開「禁令本身禁止再加禁令」矛盾

**3. workflow.md frontmatter version 2.29 → 2.30** + **engine-manifest workflow.md 版本同步** + **engine_version 仍 5.87**（third follow-up 同 v5.87 邏輯主題、不另 bump）

**影響檔案**（3 個）：
- `.claude/rules/workflow.md` 2.29 → 2.30（line 208 動詞硬化 + Mode W 新增）
- `07-changelog/CHANGELOG.md`（本段）
- `engine-manifest.json`（workflow.md 版本同步）

**v5.87 三波 + Mode W 整體狀態（C=c 完整版）**：

| 修法 | 主題 | 狀態 |
|------|------|------|
| v5.87 main | SKILL.md §Output Contract trace/verifier 動詞硬化 | ✅ |
| v5.87 fu1 | architecture-principles v1.7 雙證偽記錄 | ✅ |
| v5.87 fu2 | 3 SKILL.md lessons add-evidence 動詞硬化 | ✅ |
| v5.87 fu3（本 commit）| workflow.md line 208 動詞硬化 + Mode W 規則層落地 | ✅ |

---

## v5.86（2026-05-05）

**主題：🔧 /scan followup — harden 版本鏈 + brain-loading pin v5.85 漏修補齊（partial、待 Kai 授權 .claude/ 完成剩餘 4 處）**

> territory override justified by: cross-territory engine bump（Claude 改 02-skill-factory 內容 + engine-manifest 共享、CHANGELOG 同 entry、§9.11 規則）

### 背景

PR #409（v5.85）對 Phase 5/5b 退役做了文檔層對齊、`/scan` 後續掃描發現 v5.85 漏了 harden 自己的版本鏈 + 三個生成 SKILL.md 的 brain-loading.md pin。本 PR 為 #2 號發現的補修。

### 已完成（本 PR）

- 🔴 `02-skill-factory/README.md`：harden 版本欄位 v2.0 → v2.1（對齊 SKILL.md frontmatter v2.1、2026-04-30 已升）
- 🟡 `02-skill-factory/discovery/SKILL.md` 步驟 0：brain-loading.md pin v1.2+ → v1.6+
- 🟡 `02-skill-factory/generation/SKILL.md` 步驟 0：同上
- 🟡 `02-skill-factory/quality/SKILL.md` 步驟 0：同上
- engine-manifest.json：`_meta.engine_version` 5.85 → 5.86 + `last_updated` 不變

### 待 Kai 授權後補（同 PR、後續 commit）

下列 3 檔在 `.claude/**` 受保護路徑內、`settings.json` deny rule 擋 Edit/Write/Bash、需 Kai 在 UI 或 CLI 明確授權後補入：

- 🔴 `.claude/commands/harden.md:22` SKILL.md v1.0 → v2.1（極度過期、跳兩個 minor）
- 🟡 `.claude/rules/workflow.md:230, 572` harden v1.2 → v2.1（兩處）
- 🟡 `.claude/rules/workflow.md` 加 §Brand Section Owner 對照表（對應 /scan 第 #3a 號發現、補禁令 #11 v4.21+ owner 分流的決策依據文檔）

### 跨區協作

- Codex 已於 PR #410（merged 2026-05-05）處理 #3b（adoption_gate.py BRAND_SECTION_OWNER 補 [6][8]）+ todo owner=auto 邏輯 + tests
- 確認 `video-ops.py lessons add-evidence` CLI 已落地（PR #410 跑過 `tests/test_lessons_add_evidence.py` 11 passed）— 未來 #1 lesson-pressure hook 補實作的 Codex 配套就位

### 驗證

- `python scripts/engine/engine_version_check.py --base origin/main --head HEAD` ✅ passed
- `python scripts/lint/rules-lint.py` ✅ 0 errors（21 warnings 為既有腳本檔 AI pattern、與本 PR 無關）

### 為什麼分批 commit

`.claude/**` 是 hard deny（per `permissions.md` 受保護路徑）、Kai UI 端需明確授權才能解禁。本 PR 先把可獨立 commit 的 4 處推進、Kai 授權後再追加 4 處於同 entry。避免「改了一半但不能安全 commit」的 branch 狀態。

---

## v5.85（2026-05-05）

**主題：🔧 數據大腦消費鏈深度審計 + 全修（Phase 5/5b 退役後文檔漂移清理）**

### 背景

`/scan` 級審計發現 7 個節點漂移、全部位於文檔層（不影響資料層 schema、不影響 brain_loader 行為）。根因：Phase 5（v5.42）退役 12 stub redirect + Phase 5b（v3.0 lint-driven manifest）落地後、shared-references 內的 backlink / 流程描述 / SKILL.md「載入規範」章節未同步、產生 4 處 broken active 引用 + 3 處過時版本 pin / 標註。

### 修復清單

- 🔴 `shared-references/README.md` 升 v1.2 → v1.3：
  - 表格內 `data-brain-manifest.md` 從「⚠️ 內容過時、待 Phase 5b 重寫」改為「v3.0 lint-driven（Phase 5b 完成）」
  - 情境 6 失效鏈條（`flow-operator/SKILL.md §人設偏離度計分`）改指 `persona-deviation-scoring.md`（實際 SSoT）
  - 情境 3 / 4 殘留 `title-generator / hook-killer / flow-operator / script-verifier` 替換為 `quality phase=fix / generation mode=dual-track / quality phase=check`
  - 平行規範段「6 個生成 skill」過時計數改為「vNext 3 真 skill」
- 🔴 `shared-references/quality-gates.md` 升 v2.4 → v3.0：流程主述名從 4 個獨立 skill（humanizer / hook-killer / script-verifier / title-generator）對齊到 `quality` skill 的 phase=check / phase=fix 雙階段。SSoT 內容已遷至 `shared-references/{ai-pattern-detection, hook-templates, title-rules}.md`、流程語意不變、敘述對齊。
- 🔴 `shared-references/persona-deviation-scoring.md` §歷史段：明標 `brain-interface` v2.2 / `flow-operator` v1.50 兩 skill 皆已退役、目錄不存在於 `02-skill-factory/`、僅作來源敘事保留（避免讀者點過去 404）
- 🟡 `shared-references/data-brain-manifest.md`：模組簡介表 [4] row 從「discovery / generation mode=dual-track（C 版）」改為「discovery（C 版切角推理用、generation 不直接引用）」、與 lint manifest 實際結果對齊
- 🟡 `02-skill-factory/{discovery,generation,quality}/SKILL.md`「載入規範」章節 → 重命名為「步驟 0：載入」、補上 `scripts/libs/brain_loader.load_for_skill("<operator>", "<skill-name>")` 顯式樣板（對齊 brain-loading.md v1.2+ §Skill prompt stage 0 引用格式）+ `Lesson 使用標注` 段落（對齊 workflow.md v2.10+ §對話中累積 evidence）
- 🟡 `generation/SKILL.md` stale pin 修：`data-brain-manifest.md v2.3+` → `v3.0+`
- engine-manifest.json：`README.md` 1.2 → 1.3、`quality-gates.md` 2.4 → 3.0

### 驗證

- `python scripts/lint/brand_ref_lint.py`：✅ 0 issues、manifest 矩陣修改前後完全一致（無誤動依賴關係）
- `python scripts/lint/rules-lint.py`：✅ 0 errors（21 warnings 為既有腳本檔的 AI pattern、與本 PR 無關）
- `git diff --name-only`：8 檔、全在 Claude 領土白名單 + engine-manifest.json（共享路徑、PR body 標 owner）

### 為什麼 not skill / hook 加碼

對應 CLAUDE.md 禁令 #7 三層問：
- (a) lint：brand_ref_lint 已在、抓 [N] 引用 over/under-declared、本次修不擴 lint
- (b) 規則：本次修就是把規則層（README / quality-gates）寫到對齊
- (c) 資料層：無 schema 變動、所以 **無 🚨 schema-migration 標記**（per 禁令 #14、客戶端 sync 安全 auto-merge）

不增 skill、不增 hook、不增 lint 規則 — 純文檔對齊。

---

## v5.84（2026-05-04）

**主題：🔧 brain_loader.py PR #365 silent regression 修復（lessons stage filter 對齊 v4.63 schema）**

> territory override justified by: cross-territory engine bump（Codex 修 brain_loader.py + tests/lint、Claude 同步契約 + CHANGELOG + manifest、§9.11 規則）

### 背景

PR #406 後深掘 `scripts/libs/brain_loader.py` 揭露 1 個 critical bug + 7 個 contract drift。本 PR 處理最高 ROI 的 #1（lessons stage filter silent regression）：

`brain_loader.py:_active_lessons` 從 PR #365（2026-04-29）起用已退役的 4 態 schema：

```python
return [row for row in rows if row.get("stage") in ("candidate", "active")]
```

但 `lessons-schema` v2.3 + `data/kai/lessons.json` 實值為 `soft / hardened / archived`、`brain-loading.md` v1.2 SSoT 寫 `stage == "soft"`。

### 影響量測（修前 / 修後）

| skill / mode | 修前 bundle.lessons 命中 | 修後預期 |
|--------------|-------------------------|---------|
| generation/dual-track | 0 / 31 | 應 ~24（24 條 soft 中 scope 通過的） |
| quality/check | 0 | ~24 |
| discovery/discover-week | 0 | ~24 |
| harden（LEGACY_SKILLS）| 0 | ~24 |

**6 天內無 test 抓到** — bundle.lessons = 0 不 raise、外觀像「沒 soft lessons」。

### 變更

| 檔 | 動作 | 領土 |
|----|------|------|
| `scripts/libs/brain_loader.py:82-83` | `("candidate", "active")` → `"soft"` | Codex（PR `codex/fix-brain-loader-stage-drift`） |
| `tests/test_brain_loader.py`（新）| 4 個 regression test | Codex |
| `scripts/lint/rules-lint.py` | 新規則防 stage 舊名再混入 | Codex |
| `02-skill-factory/shared-references/brain-loading.md` | 1.5 → **1.6**：§Lessons 過濾規則加 ⚠️ v1.6 修正紀錄段、Changelog 加 v1.6 entry | Claude（本 PR）|
| `02-skill-factory/CHANGELOG.md` | 新 entry：brain-loading v1.6 + reframe v1.0 §發現 B | Claude（本 PR）|
| `engine-manifest.json` | engine 5.83 → **5.84**、brain-loading.md 1.5 → 1.6、CHANGELOG 5.83 → 5.84 | Claude（本 PR）|
| `data/kai/lessons.json` | 加 L-NEW（origin=mistake、stage=hardened、scope=engine/brain-loader、紀錄 silent regression 教訓）| Claude（透過 video-ops.py CLI）|

### Reframe `docs/references/skill-architecture-principles.md` v1.0 §發現 B

原解釋：「lessons 從進化前導退化為事後審計、原因是 Kai 直接寫 CLAUDE.md 禁令、lesson 層空轉」（設計層問題）。

真因：`brain_loader.py` filter 用舊 schema、所有 skill 載入 lessons = 0 → lesson 不是空轉、是被 silent code bug 弄死。

→ v1.0 §發現 B 結論修正、待修復後 1-2 週觀察期重評 lesson 機制（lesson-pressure / case-based retrieval 等下游推導都建在 lesson 命中前提）。

### 元教訓（已硬化為 lint rule）

> Schema 降維後、必跑 grep 全 repo 找舊名引用 + 對中央 reader（brain_loader）加 contract test + lint 規則區分「migration helper 用舊名（合理）」vs「read path 用舊名（bug）」。

### 配套關係

- 本 Claude PR 與 Codex PR `codex/fix-brain-loader-stage-drift` 是 cross-territory pair（§9.11）
- Codex PR 處理 scripts/libs + tests + lint、Claude PR 處理 02-skill-factory + 07-changelog + engine-manifest + data
- Merge 順序建議：Codex PR 先（核心 fix 立刻生效）、Claude PR 後（依 main 上 Codex PR 已 merge 的 sha rebase）

### 不做（Task B、後續另開）

- #2 scope `'generation' ∈ scope` pass-through code 未實作
- #3 `CORE_VNEXT_SKILLS` 仍含已退役 stub orientation/distillation
- #4 viral mode 違反「不綁大腦」契約
- #5 `LEGACY_SKILLS` 死碼
- #6 `web_fetch_placeholder` 占位（tool 不存在）
- #7 `GENERATION_MODE_SCOPE` 命名與內容不符
- #8 variant mode SKILL.md vs brain_loader 對齊

→ Task B 在 #1 修完 + 觀察 1-2 週 lesson 命中率回正後另派、避免一次太多 drift 並行造成 review 疲勞。

### 驗證

- Codex PR：`pytest tests/test_brain_loader.py -v` + `python scripts/lint/rules-lint.py`（新 rule 命中修前、修後不命中）
- Claude PR：本檔自身 + brain-loading.md frontmatter + manifest 對齊
- 觀察期：1-2 週後跑 `python3 -c "from brain_loader import load_for_skill; ..."` 確認 bundle.lessons > 0、實際看 skill 行為差異

---

## v5.83（2026-05-04）

**主題：🔧 brand.md auto-inject 退役、改純 lazy load（token cost −27k/session）**

7 陷阱對照本 repo baseline 後判定：trap #3 hook 群體偷塞最高槓桿單點 = `session-start.sh` 把 brand.md 全文（~27k token）每 session cat 進 context。同時 `brain_loader.py` 已存在做 skill 跑時的結構化載入 = 雙倍載入。本 PR 移除 hook auto-inject、所有路徑統一走 brain_loader / on-demand Read。

### 變更

| 檔 | 動作 |
|----|------|
| `.claude/hooks/session-start.sh` | 拿掉 `cat "$BRAND"` 全文塞、改 1 行提示 |
| `02-skill-factory/shared-references/brain-loading.md` | 1.4 → **1.5**：§本文件角色 加 v1.5 重要變更段、Changelog 新增 entry |
| `CLAUDE.local.md` | §品牌速查 從「全文 auto-inject」改為「lazy load by skill / on-demand Read by 對話」 |
| `02-skill-factory/CHANGELOG.md` | 本變動 entry |
| `engine-manifest.json` | 5.82 → **5.83**、brain-loading.md + CHANGELOG.md 版本對齊 |

### 為什麼

- baseline 量測：CLAUDE.md 24k + workflow.md 48k + brand.md 27k + 其他 ≈ 103k token / session
- 本變動後：≈ 76k（−27k、−26%）
- 純工程對話（估 30-50% 對話）100% 受益、skill 對話去雙倍載入（54k → 27k）
- 身份識別不掉 — CLAUDE.local.md 含品牌名 / operator / forbidden_terms 仍每 session auto-load

### 對應 4.7 mature 視角

`docs/references/skill-architecture-principles.md` v1.6 元規則 + 工作模式 Z：v4.62 「衍生速查檔已廢除、改全文 auto-inject」是 4.6 慣性（「載入越多越安全」）。4.7 推理力下、lazy load + on-demand 已足、Pre-load 是反向浪費。

### 不做（保守）

- 不拆 brand-core / brand-detail（兩檔同步成本）
- 不加 task-type 偵測 hook（判斷邏輯本身是新負擔）
- 各 SKILL.md 的 brain_loader pointer 不變
- brand.md 本體 100% 不動

### 驗證

- `bash -n .claude/hooks/session-start.sh` ✓
- 下次新對話：session 開頭只剩 1 行 brand 提示 + adoption gate
- skill 跑時 brain_loader 仍正常返 BrainBundle

### 後續（不在本 PR）

- Trap #1：CLAUDE.md / workflow.md 版本史下沉 design-lineage.md（~−35k baseline）
- Trap #4：1 小時 prompt cache 配置（需查 Claude Code settings schema）
- Trap #5：MCP server 審計（看 Kai 真用幾個）

---

## v5.82（2026-05-03）

**主題：🔧 workflow.md §平行任務 — Boris team tip #1（git worktree）落地**

`docs/references/worktree-guide.md` v1.0 早就存在、但 workflow.md 沒掛勾、Claude 對話中不會主動建議 worktree。本 PR 補對話流程層引用、配 Mode A 派遣等待空檔使用。

### 變更

| 檔 | 動作 |
|----|------|
| `.claude/rules/workflow.md` | 2.28 → **2.29**：插入 §平行任務 區段（~40 行）— 何時用矩陣、常用指令、Claude 自驅原則、限制 |
| `engine-manifest.json` | engine 5.81 → 5.82、workflow.md 2.28 → 2.29、CHANGELOG 5.81 → 5.82 |
| `07-changelog/CHANGELOG.md` | 本 entry |

### 為什麼

Boris team 把 worktree 列為「single biggest productivity unlock」、本 repo guide 已存在但 0 引用。Mode A 派遣 Codex 後等 5-30 分鐘空檔、Claude 應主動開 worktree 處理 Claude 領土事、不空等。

### 限制（明寫於規則內）

- 只在本機 `claude` CLI 可用
- 網頁版 Claude / Codex Desktop 用戶跳過此節
- worktree 數量超過 5 → 反而 context 成本上升

### 不做（保守）

- 不寫 worktree wrapper 工具 / slash command（Boris 自己也是純 git 指令）
- 不強制 Claude 對所有多 task 都開 worktree（看情境）

---

## v5.81（2026-05-03）

**主題：🔧 Codex CLI 整合軸 5 PR 後對齊（README / AGENTS.md stale ref）**

PR #397 → #402 連續 5 PR 把 Codex CLI 整合軸打通、但 README.md 自我引用還停在 engine v5.75（v8.4 那輪定的）、AGENTS.md §11 還寫 agent-dispatch.md v1.0+。本 PR 對齊。

### 變更

| 檔 | 動作 |
|----|------|
| `README.md` | 8.4 → **8.5**：4 處 engine 引用 v5.75 → v5.80（line 4 inline / line 23 skill row / line 23 footnote / line 309 footer）+ 加 v8.5 entry 表 |
| `AGENTS.md` §11 | 權威引用 `agent-dispatch.md v1.0+` → `v1.2+`（含 §10 註記）|
| `engine-manifest.json` | engine 5.80 → 5.81、README 8.4 → 8.5、CHANGELOG 5.80 → 5.81 |
| `07-changelog/CHANGELOG.md` | 本 entry |

### 不做

- AGENTS.md 不加 inline version（一直沒有、保持 frontmatter-only 結構）
- AGENTS.md 不加進 contract_files（避免本輪同時碰版本追蹤決策、留另一輪）
- T-0020 close 由 Kai 操作 / 之後另跑 video-ops.py todo close（本 PR 不混 data 層）

---

## v5.80（2026-05-03）

**主題：🔧 agent-dispatch.md v1.2 + workflow.md v2.28 — Codex Desktop 為 Mode A 替代路徑、優先級高於 Mode B-plus CLI**

實證沉澱：本日 PR #401（T-0020 修 adoption_gate.py defer 機制）走的不是 v1.1 設計的 Mode B-plus CLI 路線、而是 Codex Desktop GUI。Kai 5 分鐘搞定、CLI 路線卡 30 分鐘（npm 升級 + Windows cmd 不支援 heredoc）。沉澱進契約、未來 Claude 預設建議 Desktop。

### 變更

| 檔 | 動作 |
|----|------|
| `docs/contracts/agent-dispatch.md` | 1.1 → **1.2**：§10.1 加 Codex 3 條調用路徑表（CLI / Desktop / Cloud）、§10.3 重排 fallback 優先級（Mode B-desktop 優先 > Mode B-plus CLI）、§10.5 實務建議重排（Desktop 為網頁 Claude 場景預設）|
| `.claude/rules/workflow.md` | 2.27 → **2.28**：§Dispatch §環境檢測 改建議 Codex Desktop、不再預設 heredoc bash |
| `engine-manifest.json` | 5.79 → 5.80、agent-dispatch 1.1 → 1.2、workflow.md 2.27 → 2.28、CHANGELOG 5.79 → 5.80 |
| `07-changelog/CHANGELOG.md` | 本 entry |

### 為什麼

v1.1 §10 假設 fallback 路徑只有 Mode B-plus（Kai 複製 bash heredoc 到本機 terminal）。實際操作發現：
1. Windows cmd 不支援 `cat <<'EOF'` heredoc
2. Codex CLI 版本過舊（gpt-5.5 model 需新版）、要先 `npm i -g @openai/codex@latest`
3. Codex Desktop GUI 完全跳過 1+2、直接貼 prompt 開 PR

### 元教訓

契約 v1.0 → v1.1 → v1.2 都是「**實際使用發現缺口、即時沉澱**」、不是預先設計。對齊 CLAUDE.md 禁令 #13「skill 不該被新增、應該被識別」+ workflow.md §對話期間的進化提案。

### 後續

無剩餘 deferred。Codex CLI 整合軸 5 PR 完整收尾（#397 + #398 + #399 + #400 + 本 PR）+ #401 為首次實證。

---

## v5.79（2026-05-03）

**主題：🔧 workflow.md §Dispatch cross-ref agent-dispatch.md v1.1 §10**

PR #399 的 deferred 項目落地。讓 Claude 對話流程層（workflow.md）也認識 v1.1 新增的環境檢測 + Mode B-plus fallback、避免下個 session 在網頁版沙箱直接跑 Mode A 失敗。

### 變更

| 檔 | 動作 |
|----|------|
| `.claude/rules/workflow.md` | 2.26 → 2.27、§Dispatch 加 §環境檢測 子節（env probe + B-plus 降級指引）、引用 v1.0 → v1.1 |
| `engine-manifest.json` | engine 5.78 → 5.79、`workflow.md: 2.26 → 2.27`、CHANGELOG 5.78 → 5.79 |
| `07-changelog/CHANGELOG.md` | 本 entry |

### 為什麼

agent-dispatch.md v1.1 §10 已寫環境前提、但 workflow.md（Claude 第一線查的對話流程規則）只指 v1.0、不知道有 §10。下個 session 看 workflow.md → 直接嘗試 `codex exec` → 沙箱沒 codex → fail。

### 解（workflow.md §Dispatch 新增 §環境檢測 子節）

```bash
which codex 2>/dev/null && codex --version 2>/dev/null
```

- exit 0 → Mode A 可用
- exit ≠ 0 → 降級 Mode B-plus（Claude 寫完整 payload、請 Kai 複製到本機跑）
- 不嘗試 Mode A（會 fail）

### Codex CLI 整合三層全收尾

| 層 | 檔 | 版本 |
|----|------|------|
| Canonical 契約 | `docs/contracts/agent-dispatch.md` | v1.1 |
| Codex 端摘要 | `AGENTS.md` §11 | （含於 PR #398）|
| Claude 對話流程層 | `.claude/rules/workflow.md` §Dispatch | **v2.27（本 PR）** |

---

## v5.78（2026-05-03）

**主題：🔧 agent-dispatch.md v1.1 — 環境前提 + Mode B-plus fallback**

v1.0 假設 Claude orchestrator 與 Codex CLI 在同一執行環境（`bash` 看得到 `which codex`）、但 claude.ai/code 網頁版沙箱與本機隔離 — 本輪 session 實際撞到此 gap、沉澱進契約避免下次再踩。

### 變更

| 檔 | 動作 |
|----|------|
| `docs/contracts/agent-dispatch.md` | v1.0 → v1.1、加 §10「環境前提 + Fallback」（5 子節：why / 檢測 / Mode B-plus payload 規範 / 環境變化處理 / Kai 介面建議）|
| `engine-manifest.json` | engine 5.77 → 5.78、`agent-dispatch.md: 1.0 → 1.1`、CHANGELOG 5.77 → 5.78 |
| `07-changelog/CHANGELOG.md` | 本 entry |

### 為什麼

實際踩坑：本 session 走網頁版 Claude、`which codex` 失敗、發現 Mode A 只在本機 `claude` CLI 可用。v1.0 沒明文這個前提、Claude 下次又會嘗試 dispatch + 失敗、Kai 又得問同樣問題。

### 解法（§10 三層）

1. **檢測**：每 session 第一次 dispatch 前跑 `which codex`、決定 Mode A 或 Mode B-plus
2. **Mode B-plus**：Claude 仍寫完整 payload（不省略格式）、Kai 只做複製貼上 + 跑 + 貼回。比純 Mode B 好（payload 我寫、不靠 Kai 即興）
3. **環境變化**：同 session 中環境改變（如切到本機）、Claude 重檢測、可從 B-plus 升回 A

### 不做

- 不寫 codex CLI 自動安裝邏輯（會破壞 Kai 環境邊界）
- 不寫網頁版 + 本機橋接（如 SSH tunnel 等）— overengineering、Kai 切介面就好

### 後續

`.claude/rules/workflow.md` §Dispatch 應加一行 cross-ref §10、但需 Kai UI 授權。本輪不一起做、避免 PR 卡 .claude/ deny 重演。

---

## v5.77（2026-05-03）

**主題：🔧 Mode A 雙代理派遣協議落地（agent-dispatch.md v1.0）**

承續 PR #397 把 Codex CLI 帶入本機後、把「Claude 當 orchestrator、Codex 當 worker」的呼叫協議寫成正式契約、不再靠每次對話即興設計。Kai 不再當人肉 router、單一視窗對 Claude、Codex 透過 `codex exec` 派遣。

### 變更

| 檔 | 動作 |
|----|------|
| `docs/contracts/agent-dispatch.md` | 新增、v1.0、~180 行：定位 / 角色 / dispatch 決策樹 / payload 格式 / Mode 三種 / 失敗處理 / Codex 端回應契約 / 反例 / 演化條件 |
| `AGENTS.md` | 新增 §11 Headless dispatch、摘要 Codex 端 8 條核心契約 + 典型 payload 範例 |
| `.claude/rules/workflow.md` | 2.25 → 2.26、新增 §Dispatch 區段（決策樹 + bash template + audit trail 格式 + 失敗處理 + 演化觸發）|
| `engine-manifest.json` | engine 5.76 → 5.77、新增 contract `docs/contracts/agent-dispatch.md: 1.0`、bump `.claude/rules/workflow.md: 2.25 → 2.26`、CHANGELOG 5.76 → 5.77 |
| `07-changelog/CHANGELOG.md` | 本 entry |

### 為什麼現在做

1. PR #397 已落地 `AGENTS.md` + 共享 working tree + 本地 territory hook → dispatch 基礎設施齊
2. Mode A 比 Mode B（兩窗複製貼上）少一個人腦中介、可即時驗證
3. 規則寫進契約 + 跨對話穩定（每次對話不重新設計呼叫協議）

### 不做

- 不新增 `/dispatch` slash command（per CLAUDE.md 禁令 #13、預測 → 不做、跑 ≥3 次再升級）
- 不寫 dispatch log 檔（對話 audit + git history 已足；連續 5 次同 pattern → 才升 skill）

---

## v5.76（2026-05-01）

**主題：🔧 補齊 lessons add-evidence CLI（P2 lesson-pressure evidence 累積）**

依 workflow.md v2.10 既有規格補完 `video-ops.py lessons add-evidence` 的測試覆蓋與錯誤輸出語意、確保 P2 hook 可穩定累積跨 VID evidence。

### 變更

| 檔 | 動作 |
|----|------|
| `scripts/ops/video-ops.py` | `lessons add-evidence`：lesson 不存在時改為 stderr 輸出錯誤 + exit 1（其餘行為維持 idempotent / no-op）|
| `tests/test_lessons_add_evidence.py` | 新增「evidence 欄位不存在時自動初始化」case、並校正 not-found 斷言改讀 stderr；覆蓋 append / idempotent / not-found / init-missing-evidence |
| `engine-manifest.json` | engine 5.75 → 5.76、CHANGELOG contract version 5.75 → 5.76 |
| `07-changelog/CHANGELOG.md` | 新增 v5.76 entry（本 PR、領土邊界 split 自 codex PR #393）|

### 為什麼 split

Codex PR #393（branch `codex/add-cli-command-for-lessons-add-evidence`）原本同 commit 含 CHANGELOG entry、但 `07-changelog/CHANGELOG.md` 屬 Claude 領土（CLAUDE.md 禁令 #8 §9.3 + 禁令 #6 CODEX_OK 白名單排除）。territory-lint 會 red。本 PR 拆出 CHANGELOG entry、Codex PR 同步 drop 該檔、兩 PR 一起 merge 完成本次補齊。

根因：上一輪 Claude 寫的 Codex 交辦文案漏標 `territory override justified by:` 也未拆 follow-up — L-0021 同類重演、本輪會記 lesson。

---

## v5.75（2026-04-30）

**主題：🔧 Post-merge version align（PR #391 後修補）**

PR #391（v5.74）merge 後盤點、發現 README v8.3 自身有 4 處 engine 版本自我引用錯（寫 v5.73、實際應 v5.74）+ `02-skill-factory/README.md` 版本標 v6.1 漏改 v6.2（已在 v5.74 升版、但 README tree note + 引用兩處沒同步）。

### 變更（純文件層、無功能 / schema 動）

| 檔 | 動作 |
|----|------|
| `README.md` | 8.3 → 8.4、6 處對齊（line 4 header / line 23 skill row / line 60 tree note / line 236 引用 / line 296 v8.3 row 描述 / line 308 footer）|
| `engine-manifest.json` | 5.74 → 5.75、`README.md` 8.3→8.4、`07-changelog/CHANGELOG.md` 5.74→5.75 |
| `07-changelog/CHANGELOG.md` | 新增 v5.75 entry（本條）|

### 不在範圍

- `CLAUDE.md` line 65 引用 `workflow.md v2.24` 應改 v2.25（permission-denied、需 Kai UI 授權後另跑）

### 為什麼這次調整

PR #391 自身在 commit 時 README 的 engine 自我引用沒對齊到 v5.74（本來 PR 內就把 manifest bump 5.73→5.74、但 README 內文 4 處仍寫 5.73）。merge 後 sync-readme bot 也只是 mirror 同樣內容、不檢查 engine 版本一致性。本 PR 補回。

---

## v5.74（2026-04-30）

**主題：🔧 Sleep-mode fact realignment（5.64 → 5.73 累積文件層漂移修正）**

引擎 5.64 → 5.73 累積 9 個版本、`README.md` / `02-skill-factory/README.md` / `02-skill-factory/harden/SKILL.md` 多項 fact 漂移：tests 64→69 / 579→591 cases、Python 12,800→13,600 行（+18 ops/lib + 12 utils/lib）、契約 8→9（多 test-path-bootstrap）、workflow.md v2.24→v2.25、skill 版本表（orientation v1.0→v2.0 stub / generation v1.0→v1.2 / quality v1.0→v1.2 / distillation v1.0→v2.0 stub）。

### 變更（純 Sleep-mode 文件層、無 schema 動）

| 檔 | 動作 |
|----|------|
| `README.md` | 8.2 → 8.3、9 處事實對齊 + 版本歷史新增 v8.3 / v8.2 兩列 |
| `02-skill-factory/README.md` | 6.1 → 6.2、skill 版本表對齊實際 SKILL.md frontmatter |
| `02-skill-factory/harden/SKILL.md` | 2.0 → 2.1、原 stub 引用已退役 distillation/SKILL.md → 改 redirect 至 `.claude/commands/harden.md` + `scripts/ops/lib/hardening.harden_from_dialog()` |
| `engine-manifest.json` | 5.73 → 5.74、4 個 contract_files version 同步、清除 `lessons_retrieval.py` / `ai_patterns_lint.py` 在 contract_files / internal_files 兩處 dup（保留 internal_files 版） |
| `07-changelog/CHANGELOG.md` | manifest 版本標籤 5.71 → 5.74（之前漂移）|

### 不在範圍

- `.claude/rules/workflow.md:52` `build_items()` → `collect_items()` callable 名漂移（permission-denied、需 Kai UI 授權）
- `.claude/skills/harden.md` stub description 對齊 v2.1（permission-denied）
- workflow.md v2.25 line 230 / 443 引用 `harden/SKILL.md v1.2` stale（actual v2.1、permission-denied）
- `.claude/commands/harden.md` 引用「完整規格見 harden/SKILL.md v1.0」stale（permission-denied）
- `data/kai/pipeline.json` regression-guard 報 VID-003 backfill non-null → null（資料層 / Codex 領土、不動）

### 為什麼這次調整

距上次 README fact realignment（v8.2 / engine v5.65、2026-04-28）僅 2 天、引擎已跳 9 版至 5.73、累積漂移：
- pipeline storage shard 化（v5.73）= 多 tests / 程式碼增加
- 二輪退役（v5.67、orientation/distillation 降 stub）= skill 表結構改
- workflow.md v2.24 → v2.25（v5.67）= 文件版本

對 AI 下次進來的影響：README 是 root truth、若 fact 漂移多版本、Claude 對「系統規模 / 版本 / skill 結構」的初判會錯。本次補回。

### 配套（engine-manifest dup 清理）

`engine-manifest.json` 移除 `scripts/utils/lessons_retrieval.py` + `scripts/lint/ai_patterns_lint.py` 在 `contract_files` 區塊的 null 條目（兩檔同時也在 `internal_files` 出現、JSON 解析時後者勝、語意上不該分散兩區）。修復後 contract_files 45 / internal_files 126、無重複 key。

---

## v5.73（2026-04-30）

**主題：🔧 pipeline storage shard 化（per-VID/IDEA files、解 stale branch overwrite 風險）**

PR：#388

🚨 schema-migration: `data/[operator]/pipeline.json` → `data/[operator]/pipeline/{_meta.json + items/VID-NNN.json + items/IDEA-NNN.json}`。客戶端 sync 本 entry 後、必跑 `python3 scripts/ops/migrate_pipeline_to_sharded.py --operator <name>` 完成 migration。Legacy `pipeline.json` 仍由 lib 自動 regenerate、外部工具讀取不影響。

### 背景

過去 30 天發生 3 次 disaster recovery（v5.69/v5.70/v5.71、PR #373/#377/#380）、全部因 feature branch stale `data/[op]/pipeline.json` 經 sync-to-sheets workflow 整檔 overwrite 回 main、退回 50+ 支已上線編碼。

PR #373 落地 `pipeline-regression-guard` lint 是事後偵測、不是事前防火牆。本 PR 拆檔讓 stale branch 最壞情況只 overwrite 單一 VID 檔、不會把整 pipeline 退回。

### 變更

| 檔 | 動作 |
|----|------|
| `data/kai/pipeline/_meta.json` | **新增**（next_vid / next_idea_id / thresholds / 整體設定）|
| `data/kai/pipeline/items/VID-NNN.json` × 80 | **新增**（每支 VID 一檔）|
| `data/kai/pipeline/items/IDEA-NNN.json` × N | **新增**（每支 idea 一檔）|
| `data/kai/pipeline.json`（legacy） | 保留、由 lib 自動 regenerate（外部工具相容）|
| `scripts/ops/lib/pipeline.py` | 加 `_pipeline_paths()` / `_load_pipeline_sharded()`、`load_pipeline()` / `save_pipeline()` 雙寫 sharded + legacy |
| `scripts/ops/migrate_pipeline_to_sharded.py` | **新增**（含 `--rollback` 還原為單檔）|
| `.github/workflows/sync-to-sheets.yml` | 排除 legacy `data/*/pipeline.json` 從 branch→main sync |
| `docs/contracts/pipeline-schema.md` | inline 1.3 → **2.0**（breaking schema change）|
| `engine-manifest.json` | `_meta.engine_version` 5.72 → **5.73**、`contract_files["docs/contracts/pipeline-schema.md"]` 1.3 → **2.0** |

### 不在範圍

- `dashboard/build.py` 升 shared loader（Claude follow-up、現仍讀 legacy regenerated 檔、不影響功能）
- 其他 client repo migration（由各客戶 sync 本 entry 後跑 migrate 工具）

### 驗證

- [x] `pytest -q` 全綠（601 passed）
- [x] `python3 scripts/lint/rules-lint.py` 0 errors
- [x] migrate + rollback + 再 migrate 都成功
- [x] dashboard build 成功（仍讀 legacy）
- [x] Vercel preview deploy success
- [ ] CI: check-territory + engine-version-check + lint-and-test 全綠

### territory override

§9.11 engine bump 配對 CHANGELOG（atomic、Codex owner 此輪）。

### 觸發脈絡

Kai 第三輪 4.X 視角架構審視（前一輪 Claude 對話結論）→ Claude 識別 pipeline 整檔 SSoT 為 systemic disaster recovery 風險源 → 寫 Codex 交辦文案 → Codex 落地 PR #388。

---

## v5.72（2026-04-30）

**主題：🔧 CHANGELOG 切檔（LONGBRO 4.7 mature audit TASK 8、純位置搬移）**

PR：本 PR

### 背景

`07-changelog/CHANGELOG.md` 累積 8573 行（v1.1 2026-02-05 ~ v5.70 2026-04-30）、grep 與新對話載入變慢。LONGBRO 範本驗證場觀察主檔過大、列入 4.7 mature audit TASK 8。

### 變更

| 檔 | 範圍 | 行數 |
|----|------|------|
| `07-changelog/CHANGELOG.md`（主檔） | v5.50 ~ v5.71（最近約 1 週、20 個版本） | 904 |
| `07-changelog/CHANGELOG-archive-v5.x.md`（**新檔**） | v5.00 ~ v5.49（Opus 4.7 全修週） | 2579 |
| `07-changelog/CHANGELOG-archive-v4.x.md`（**新檔**） | v1.1 ~ v4.99（系統雛型 ~ Opus 4.7 全修中段） | 5107 |
| `engine-manifest.json` | bump 5.70 → 5.71、`files` 加兩 archive 檔 | — |

### 切點選擇

- **主檔保留 v5.50+**：最近 5 天（2026-04-26 起）、目標 < 2000 行（實際 904）
- **archive-v5.x**：v5.00 milestone（Opus 4.7 全修完成）~ v5.49（2026-04-26 之前）
- **archive-v4.x**：v1.1（最早雛型）~ v4.99（Opus 4.7 全修中段）
- 切點皆在版本邊界、沒有 entry 被截斷

### 不在範圍

- 不刪歷史條目、只搬位置
- 不改 CHANGELOG entry 內容（保留歷史原貌）
- 不動 schema、CLAUDE.md 禁令 #14 不適用（純位置搬移、非 schema-migration）

### 驗證

- [x] `wc -l 07-changelog/CHANGELOG.md` = 904（< 2000 目標）
- [x] 三檔總行數 = 8590（原 8573 + 主檔頂部 archive 指引 + 兩 archive 頂部 header、entry 內容無增刪）
- [x] grep `## v4.36` 在 archive-v4.x、不在主檔
- [x] grep `## v5.30` 在 archive-v5.x、不在主檔
- [x] grep `## v5.70` 仍在主檔
- [ ] CI rules-lint + engine-version-check 通過
- [ ] LONGBRO sync 後跑驗收清單 close TASK 8

---

## v5.71（2026-04-30）

**主題：🔧 generation / quality Output Contract 雙層化 — 人話層 4 句話為主視覺、技術數字降為腳註（解 verifier_scores 0/61 採用閉環的 UX 根因）**

PR：（claude/project-design-review-4YYoy branch）

### 背景

v1.1（engine v5.67）解了「Claude 寫不寫 trace」、把 `generation_trace` / `verifier_scores` 寫入率從 0/61 推向採用閉環。但 Kai 在對話中提出：**就算 Claude 寫了、Kai 也看不懂技術數字、不會自然回看分數來決策**。

對話中診斷出採用閉環價值-成本不對稱的**第二層**：

- v1.1 處理：寫入成本（Claude 端） — 已用 fenced JSON + CLI 強制解
- v1.2 處理：呈現格式 vs user 認知成本（Kai 端） — `conflict=7 / retention=B / ai_residue=1` 對 Kai 沒 actionable value、看到不會做決策

### 變更

**Phase 1 — Output Contract 雙層化**

| 檔 | v 號 | 變更 |
|----|------|------|
| `02-skill-factory/quality/SKILL.md` | 1.1 → 1.2 | §Output Contract 拆 4 階段：CLI 寫入 → 體檢結果（人話層 4 句、Kai 主視覺）→ 技術詳情（一行腳註）→ 完成判定 |
| `02-skill-factory/generation/SKILL.md` | 1.1 → 1.2 | §Output Contract 拆 5 階段：AI 自評 4 句（Kai 主視覺）→ trace fenced JSON → CLI 寫入 → 技術摘要（一行腳註）→ 完成判定。fenced JSON 從 §1 降為 §2（角色從「主視覺」變「stdin 食材」）|
| `docs/contracts/skill-io-schema.md` | 2.1 → 2.2 | 新增 §Human-Layer Presentation Spec：4 句話結構 + 翻譯規則 + 機器層降級規則 + validation rule |

**Phase 2 — 4 句話人話層規格**

```
─── AI 自評 ─── （generation 用）
👍 [可拍 / 建議重改 / 棄] [一句理由]
⚠️ [最弱那點 + 怎麼改]（無弱點則省略）
💡 引用大腦：[N]論點 X、[M]案例 Y
📊 同類預測：[hook=X、近 N 支平均 retention=Y]

─── 體檢結果 ─── （quality 用）
👍 [可拍 / 建議重改 / 拒收] [一句總結]
⚠️ [最弱那項 + 修法]（5 項全過則省略）
💡 引用大腦：[N]論點 X、[M]案例 Y
📊 同類對比：[超平均 / 偏低]
```

**翻譯規則**：每句的來源欄位 + 強制要求（禁套話、禁技術代號、actionable specific）寫進 `skill-io-schema.md` v2.2 §Human-Layer Presentation Spec。

**Phase 3 — 機器層降級**

v1.1 的「即時回饋」段（包含 fenced JSON / CLI summary / 同類比較數字）整體降為一行腳註：

```
（技術詳情：mode=X / hook=Y / pass=N/5 / 跑 `video-ops.py adoption-stats` 看完整趨勢）
```

技術數字仍寫進 pipeline.json（不破壞 schema、不破壞 `adoption-stats` 累積分析）、但 Kai 對話視覺中從「主體」降為「腳註」。

### 觸發脈絡

skip adoption gate（Kai 4/30 對話、L-0027 已記）→ Kai 提出「verifier_scores 沒人看得懂、要不更直覺更第一性原理」→ 對話中產出「原版 vs 新版範例對照」→ Kai 確認 Plan + 動手。

### 影響

- `verifier_scores` 0/61 採用率根因從「Claude 不寫」轉診斷為「寫了 Kai 也看不懂」、v1.2 是後者的修法
- 現有 pipeline.json schema 完全不變、`adoption-stats` CLI 不變、契約完全相容
- 下次 Kai `確認要拍：XXX` 應觀察到生成完直接附 4 句 AI 自評（非 fenced JSON 為首）

### Lint 落地策略

per CLAUDE.md 禁令 #7「能用 prompt 擋就先用 prompt」、本 PR 不寫 lint code、規範由 Claude 對話中守。若觀察到反覆違反、再升級為 `scripts/lint/skill-io-lint.py` 規則（依 lessons 硬化路徑）。

---


## v5.70（2026-04-30）

**主題：🔧 + 📦 disaster recovery 2 + pipeline-regression-guard 落地（L-0026 hardening artifact）**

PR：#373（Codex lint guard）+ commits 14e86d7 / b1e74c1（Claude pipeline 還原 + L-0026 lesson）

### 背景：第二次 stale-branch overwrite 事故

2026-04-30 Vercel dashboard 顯示影片數從 61 部回退到 41 部、回填數據大量消失。追查發現：

| 時間點 | items | online | backfill | next_vid |
|--------|-------|--------|----------|----------|
| cdbcaef（4/29 良好）| 90 | 61 | 60 | 78 |
| 69f21ea（supplement-t1 sync）| 87 | 60 | 53 | — |
| f8503a0（handle-t1 sync 災難級）| 70 | 41 | 30 | 61 |
| 34a90a0（事故當下 main HEAD）| 71 | 41 | 30 | 61 |

**根因**：`claude/supplement-t1-Awa8S` 與 `claude/handle-t1-hot-topics-db2OK` 兩支 feature 分支在 stale `pipeline.json` 上工作、`sync-to-sheets.yml` workflow 把整檔 overwrite 回 main、把 19 支 VID（含 3 支已上線）+ 28 筆倖存 VID 的 backfill 全部擦掉、17 支倖存 VID 狀態從 已上線 → 待拍。

105eb7a「DISASTER RECOVERY」之後**第二次同樣事故**、僅修當下未硬化、L-0026 補規則層。

### 變更

**Phase 1 — 還原止血（Claude commits 14e86d7 + b1e74c1）**
- 從 cdbcaef 還原 `data/kai/pipeline.json` → 90 items / 61 online / 60 bf / next_vid=78 / next_idea_id=95
- `data/kai/lessons.json` 加 L-0026（origin=mistake、stage=soft）

**Phase 2 — 規則層硬化（Codex PR #373）**
- `scripts/lint/rules-lint.py` 加 `pipeline-regression-guard`：偵測 `_meta.next_vid` / `_meta.next_idea_id` 回退、`已上線 → 待拍/剪輯中` 倒退、backfill `非 null → null` 擦除 → 全部 ERROR block PR
- 旁路條件：PR body 含 `pipeline-override justified by:` 跳過（仿 territory-lint 模式）
- main push 時 base==head、自動 skip
- `.github/workflows/rules-lint.yml`：`fetch-depth: 0` + 注入 `GITHUB_EVENT_NAME` / `GITHUB_REF_NAME` / `PR_BODY` 給 guard
- `tests/test_pipeline_regression_guard.py`：6 個 case（next-id 回退 / status 回退 / backfill 擦除 / PR override / main push / 純新增 VID）

### L-0026 hardening 路徑

- soft（4/30 b1e74c1）→ artifact 落地（PR #373）→ 待 Kai `/harden L-0026` 升 stage=hardened

### 影響

- 之後任何 PR 試圖回退 pipeline.json 關鍵欄位（VID 計數、status、backfill）會被 CI 直接 block、非 `pipeline-override justified by:` 不可繞
- 解決 2026-04-29 disaster recovery 1 + 2026-04-30 disaster recovery 2 同類事故的根因

---


## v5.69（2026-04-29）

**主題：🔧 v5.67 第二輪退役 follow-up — `.claude/skills/` 兩 stub description 對齊 + workflow.md §Orientation 去 Phase 1 + 加 §Distillation 統一段**

PR：（claude/follow-up-v5.67-stubs branch）

### 背景

v5.67 第二輪退役（5 → 3 真 skill）merge 時、Kai 尚未授權 `.claude/` 編輯、CHANGELOG 標的 follow-up 留待補完：
- `.claude/skills/orientation.md` description 還寫 v1.0 升級語氣、跟 SKILL.md v2.0 stub 不對齊
- `.claude/skills/distillation.md` description 同樣寫 v1.0 三 phase 主體、跟 stub 不對齊
- `.claude/rules/workflow.md` §Orientation Phase 1 標題殘留「Phase 1」字樣（Phase 1 觀察期已被 v1.5 「trace=0 永久空轉」一次性判定收尾）+ 缺 §Distillation 統一段

本 PR 補完三項。

### 變更

- `.claude/skills/orientation.md`：description 改 stub redirect 型（指向 workflow.md §Orientation）
- `.claude/skills/distillation.md`：description 改 stub redirect 型（指向三 phase 拆三層的三個落點）
- `.claude/rules/workflow.md` v2.24 → v2.25：
  - §Orientation Phase 1 → §Orientation（去 Phase 1 字樣、quote block 改為「規則層、第二輪退役後正式作為主體」）
  - §失敗 → 升級條件 改為 §退役後再評估（語意翻轉：不是「等升級」、是「退役後若需要再評估升回」）
  - 新增 §Distillation 統一段（三 phase 拆三層對照表 + 為什麼拆 + 退役後再評估）
- `engine-manifest.json` 5.68 → 5.69 + workflow.md 2.24 → 2.25 同步

### 為什麼

第二輪退役的「規則層為主、SKILL.md 為 stub」結構需要 .claude/ 三檔（兩 stub description + workflow.md 統一段）對齊、否則 brain_loader 引用穩定但語意分裂、未來開發者讀 stub description 仍以為是 v1.0 主體。本 PR 把 v5.67 沒做完的對齊收尾。

### 不在本 PR 範圍

- `02-skill-factory/orientation/SKILL.md` v2.0 stub 內容（已寫好、不動）
- `02-skill-factory/distillation/SKILL.md` v2.0 stub 內容（已寫好、不動）
- 重升級觸發條件實作（觀察未來、本 PR 只寫規則）

### 驗證

- engine-version-check：5.68 → 5.69 + workflow.md inline 2.25 同步 contract_files
- territory-lint：全 Claude 白名單路徑、無 override
- rules-lint：0 errors（warnings 為腳本內容、與本 PR 無關）

---


## v5.68（2026-04-29）

**主題：🔧 VID inference observability + skill-io-schema v2.1（PR #370 follow-up of #369 Q1/Q2/Q3）**

PR：#370（codex/implement-decisions-from-pr-#369-follow-up branch）

### 變更

- `docs/contracts/skill-io-schema.md` v2.0 → v2.1：新增 §VID Inference Stats（collector path / record schema / 30-day miss_rate metric / 10% alert threshold）
- `scripts/utils/lib/trace_extractor.py`：新增 `_record_vid_inference()` 寫 `data/.adoption-stats/vid_inference.jsonl`、docstring 補 strict 策略 + silent-skip 理由（Q1 / Q2 決策來源）
- `scripts/ops/video-ops.py`：`adoption-stats --vid-inference` 新模式、報 7/30 日 fenced/inferred/miss_rate、>10% 印 alert
- `tests/utils/test_trace_extractor.py` + `tests/test_video_ops_adoption_stats.py`：JSONL 寫入行為 + CLI flag + miss_rate 計算 + alert 觸發

### 為什麼

PR #369 Q3 決策保留 silent-skip 但需可觀測性；本 PR 補 metric 路徑、>10% miss rate 時提醒考慮把 VID 升必填。additive schema、無需 client migration。

### 驗證

- pytest tests/utils/test_trace_extractor.py（pass）
- pytest tests/test_video_ops_adoption_stats.py（pass）
- engine-version-check：5.67 → 5.68 + skill-io-schema.md inline 2.1 同步 contract_files

---


## v5.67（2026-04-29）

**主題：🔧 第二輪退役執行（5 → 3 真 skill）+ Generation/Quality v1.1 採用閉環行為層 + skill-architecture v1.6**

PR：（claude/review-skill-architecture-dOII6 branch、Kai 命「全動」）

### 背景

Kai 命「用 Opus 4.7 mature 視角再審視 Claude Code skill 架構」。研究反過來發現：v1.0-v1.5 已 cover 80%+、再展開新研究 = 工作模式 Z 警告的研究慣性本身。改執行 v1.4 §第二輪退役預備條款已寫但未動的結論 + 補完 PR #367 採用閉環行為層配套。

### 變更

**v5.67 行為層補完（B、配 PR #367 CodeX 端 CLI 強制）**：
- `02-skill-factory/generation/SKILL.md` v1.0 → v1.1：§Output Contract 改 3 階段（對話 trace fenced JSON + CLI save / save-with-trace-from-stdin + 即時回饋對照）
- `02-skill-factory/quality/SKILL.md` v1.0 → v1.1：§Output Contract 改 2 階段（CLI record-verifier-scores + 即時回饋對照 + 異常標註）
- 解決問題：`generation_trace` 0/61、`verifier_scores` 0/61、`hook_type` 13/61。價值-成本不對稱 — 把「未來累積分析價值」變「當下視覺價值」。

**v5.67 第二輪退役（C、5 → 3 真 skill）**：
- `02-skill-factory/orientation/SKILL.md` v1.0 → v2.0 stub：規則回 workflow.md §Orientation Phase 1
- `02-skill-factory/distillation/SKILL.md` v1.0 → v2.0 stub：三 phase 拆三層（workflow.md §Lesson 硬化提議 + session-start hook + `/harden` command）
- `02-skill-factory/shared-references/brain-loading.md` v1.3 → v1.4：§適用 skill 表標 stub
- `docs/references/skill-architecture-principles.md` v1.5 → v1.6：補注「第二輪退役執行 + 元規則『研究退場條件』」

**為什麼提前執行（不等 v1.4 「1-2 月觀察期」）**：v1.5 揭露 trace=0 永久空轉、觀察期 metric 全部依賴 trace 累積、chicken-and-egg trap。first-principles 直判 v1.4 結論執行、不靠 metric 證明。

### 不在本 PR 範圍（待 Kai 授權 .claude/ 編輯後 follow-up）

- `.claude/skills/orientation.md` description 更新（標 stub）
- `.claude/skills/distillation.md` description 更新
- `.claude/rules/workflow.md` §Orientation Phase 1 → §Orientation 正式版（去「Phase 1」字樣）+ §Distillation 統一段

不影響功能：SKILL.md stub 仍指向 workflow.md 既存段落（§Orientation Phase 1 / §Lesson 硬化提議 / §對話期間的進化提案）、原本就跑得起來。.claude/ 改動是維護整齊度、非功能性。

### 不在本 PR 範圍（CodeX 領土、無需動）

- `scripts/lint/canonical-registry.json` valid_skills 不動（orientation / distillation 已在 stub_backfill_allowlist）
- `scripts/lint/rules-lint.py` 不動

### 驗證

- rules-lint 0 errors
- engine-version-check：5.66 → 5.67 + 4 個 contract_files version 同步
- 後續 `存檔` 流程觀察 7-14 天、看 trace 採用率是否從 0% 上升

### 觀察期

3-6 週後跑 `adoption-stats`：
- trace 採用率仍 0% → §1 即時回饋假設錯、回 plan
- trace 採用率 ≥ 50% → 行為層補完成功、可進 P1 case-based retrieval
- 5 stub 是否需真退役（Phase 6+）→ 看 Kai 工作流是否觸發 orientation / distillation 名稱

---

## v5.66（2026-04-29）

**主題：🔧 pipeline-schema 1.3 + engine-manifest sync（L-0024 災後配套）**

PR：（main 直推、簽署 bypass、緊急清污）

### 背景

L-0024 retention=0 sentinel 災後修復產生連鎖 schema 變動：

1. **e6c83e2** docs(contracts): pipeline-schema add unknown performance + retention=null rule（v1.2 → 加新行 / 新欄位、未升 inline version）
2. **4d6e4dd** docs(contracts): bump pipeline-schema 1.2 → 1.3（intentional flag、stop schema_drift false-positive blocking PR #365/#366）
3. **f212b21** fix: classify_performance None guard + VID-077/078 tags（unblock CI）

但漏了 engine-manifest 同步、`engine_manifest_inline_mismatch` lint 紅、卡 PR #366 CI。

### 改動

- `engine-manifest.json`：
  - `_meta.engine_version`: 5.65 → **5.66**
  - `_meta.last_updated`: 2026-04-29
  - `contract_files["docs/contracts/pipeline-schema.md"]`: 1.2 → **1.3**

### 後續

- PR #365 + #366 需 rebase 上 main 後 CI 過
- Codex follow-up 開新 task 修 schema_drift parser（不該把 classification rule 表 row 當 schema field）

---

## v5.65（2026-04-28）

**主題：🔧 Sleep Mode 文件層 fact realignment（README + manifest 同步）**

PR：claude/optimize-system-debt-1kWQe（Sleep Mode autonomous）

### 背景

Sleep Mode 第三輪 autonomous run 偵測到 README.md 多處事實漂移、與 main 主幹現況不一致：

| 欄位 | README 寫的 | 實際 |
|------|------------|------|
| engine version | v5.52 | v5.64 |
| 自動化測試 | 61 檔 / 560 cases | 64 檔 / 579 cases |
| CLAUDE.md 版本 | v4.22 | v4.24 |
| CLAUDE.md 禁令數 | 13 條 | 14 條 |

新人 / 未來 AI agent 進來會先讀 README、被誤導。歷史上每兩週就需要做一次這種對齊（v8.1 / 04-26 也做過）。

### 動作

1. `README.md` v8.1 → v8.2：6 處事實對齊（引擎 / 測試 / CLAUDE.md 版本 + 禁令數 / Skill 區塊內 engine pointer / 結尾 changelog pointer）
2. `02-skill-factory/README.md` v6.0 → v6.1：`skill-design-principles.md` 引用從「v1.3+ A/B/C/D/E 五準則」更新為「v1.5+ A/B/C/D/E/F 六準則」（4.7 mature 視角新增的準則 F 漏標）
3. `engine-manifest.json`：README 8.1 → 8.2、02-skill-factory/README 6.0 → 6.1、`engine_version` 5.64 → 5.65、`last_updated` → 2026-04-28
4. `.github/workflows/rules-lint.yml`：移除 PR/push paths 過濾、改 branches 過濾。修舊版漏抓 engine-manifest.json / 01-data-brain/** / README.md / 07-changelog/** / docs/** 改動的 lint 死角（v5.65 補強）
5. `docs/references/production-details.md`：語音筆記分流表「→ 記錄到對應 skill-memory」更新為「→ 記錄到 `data/[operator]/lessons.json`」（v4.36 起 skill-memory/ 已退役、本處漏標）
6. `00-control-center/AI_SYSTEM_UPGRADE_REPORT_2026-04-28.md`：Sleep Mode 自主審查報告

### 不在範圍

- `.claude/rules/workflow.md:52` `build_items()` callable 名漂移：受保護路徑、需 Kai 在 UI 授權後改（從 v5.64 報告延續、Codex PR #347 已 close）
- `02-skill-factory/CHANGELOG.md` 同步 v5.65 entry：屬 design changelog、本輪 fact-only 不侵入
- VID-009 script_path 漂移（pipeline 標 `02-ready-to-shoot/2026-02-05_..._雙軌腳本_V1.md`，實檔在 `03-done/2026-02-28_..._腳本_V1.md`）：需 Kai 判斷該標 `已上線` 還是把 script 移回、Sleep Mode 不替 Kai 決策業務狀態
- `scripts/utils/lib/sync_tabs.py:280` HOLD 殘留：Codex 領土、territory-lint 擋

### Engine bump 原因

contract scope 改動（README.md 是 contract_files）→ engine-version-check.yml 強制 bump。`v5.65` 為 v5.64 後最近可用版號。

---


## v5.64（2026-04-27）

**主題：🔧 skill-architecture-principles v1.4 → v1.5（Sleep Mode 文件層校準、4.7 視角再批判）**

PR：claude/review-skill-architecture-eAizG

### 背景

Sleep Mode autonomous run（Kai 指定 token burn loop）發現 v1.4 §下一步 P0「✅ 完成」與行為層真實狀態（trace 0/44、verifier_scores 0/44、hook_type 16/44）矛盾。v1.1 標 P0 完成、其後 v1.2-v1.4 推導全建在錯誤前提上。

### 動作

1. `docs/references/skill-architecture-principles.md` v1.4 → v1.5：P0 status 校正、v1.1 與 v1.0 差異段加 v1.5 補注、新增 §v1.5 補注完整段（4.7 視角再批判 + 「規則寫了 ≠ 行為改了」教訓 + 觀察期 metric 設計違反禁令 #11 四階段的自我批判）。不重寫 v1.1-v1.4 主體、加 patch 段、保留 lineage。
2. `02-skill-factory/shared-references/skill-design-principles.md:193`：`hook-templates.md` 補 `templates/` 子目錄前綴（唯一漏標處）。
3. `00-control-center/AI_SYSTEM_UPGRADE_REPORT_2026-04-27.md`：Sleep Mode 自主審查報告。

### 不在範圍

- `.claude/rules/workflow.md:52` `build_items()` → `collect_items()` callable 名漂移：受保護路徑、需 Kai 在 UI 授權後改
- 5 SKILL.md frontmatter 加 owner field：設計變動、Sleep Mode 不該動、留報告 P2

> v5.63 號碼預留給 PR #348（Codex 採用閉環行為層補完、`_meta.trace_required_statuses` + `save-with-trace-from-stdin` + `adoption-stats`、進行中）。本 PR 升 5.64 避開撞號。

---


## v5.62（2026-04-27）

**主題：🔧 Dashboard 智能 auto-rebuild（Phase A、Claude 領土）— PostToolUse hook + freshness pill**

PR：claude/fix-rating-count-mismatch-W5dTk

### 背景

Kai 發現 dashboard sidebar「表現分級」加總（9+14+4=27）跟 KPI「樣本」27/38 視覺對不起來。實算邏輯沒 bug — 真正問題是 `dashboard/dist` 不會自動更新、回填後得手動 `python3 dashboard/build.py` 才看到新數字、Kai 看到的是過期 snapshot。檢討報告（對話內）也指出 sidebar 沒呈現「已上線但未回填」這 11 支落差感。

Phase A 解這個自動化空缺；Phase B（Codex 領土）解 save_pipeline() 直接 import 路徑、follow-up task 處理。

### 動作

#### 1. `.claude/hooks/dashboard-rebuild.sh`（新檔、Claude 領土）

雙模 hook：
- **PostToolUse 模式**（從 stdin 收 JSON）：用 `shlex` tokenize command、跳過 `--operator` 等全域 flag + 它們的值、找出真正的 verb / sub-verb、比對 mutation 集合（save / backfill / quick-add / quick-shot / set-hook-type / record-verifier-scores / add-idea / confirm / advance-status / advance / sync-online，加 todo:{add,close,archive,defer,migrate,complete,reopen} / lessons:{add,add-evidence}）
- **--check 模式**（無 stdin、給 SessionStart 用）：純 mtime 短路

智能特性：
- **mtime short-circuit**：`find data/ -name '*.json'` 取最新 mtime 對 `dashboard/dist/data.json` 比較、newer 才 rebuild
- **file lock**（`flock -n 9`）：避免並行 rebuild 衝突
- **state file**（`dashboard/dist/.rebuild-state.json`）：成功歸零、失敗累積 consecutive_failures、最後 1KB output 留證
- **多 operator**：`data/*/pipeline.json` 通吃、不寫死 operator
- **同步且快**（build.py < 1s、timeout 30s 保險）+ 永遠 exit 0、不擋 Claude / Kai 工作流

#### 2. `.claude/hooks/session-start.sh`（修改、+23 行）

加 stage 2 靜默 rebuild（成功不印 / 不打擾 Kai）+ stage 3 連續 3 次失敗顯示警告 + 修復路徑。對應 owner=auto 分流（CLAUDE.md 禁令 #11 + workflow.md v2.24）。

#### 3. `dashboard/build.py`（修改、meta block 擴充）

```diff
"meta": {
  "generated_at": "2026-04-27 15:39",
+ "generated_at_iso": "2026-04-27T15:39:13",
+ "build_epoch": 1777304353,
+ "newest_data_mtime_epoch": 1777303421,
+ "newest_data_source": "data/kai/pipeline.json",
  "operator": "kai",
  ...
}
```

#### 4. `dashboard/src/index.html`（修改、freshness pill）

- crumb 右側加綠/黃/紅三層 freshness pill（< 5 min fresh、< 30 min stale、≥ 30 min very-stale）
- JS 每 30s 更新文字、每 90s `fetch data.json` 偵測新 build → 自動 reload（保留 hash）
- fresh 狀態的 dot 帶 pulse 動畫

### Hook 四階段對應（CLAUDE.md 禁令 #11）

| 階段 | 實作 | Owner |
|------|------|-------|
| 1. 警告 | SessionStart 偵測 dist 落後 | auto |
| 2. 自動修復 | PostToolUse + SessionStart 兩條路徑都會跑 build.py | auto |
| 3. 通知 | 連續 3 次失敗顯示在 SessionStart、印詳情路徑 | employee |
| 4. gate | 跳過 — dashboard 是看板、壞掉不該擋資料寫入 | n/a |

### 測試（11 case 全 PASS）

| Case | 預期 | 結果 |
|------|------|------|
| `--operator kai todo add` | rebuild | PASS |
| `lessons stats`（唯讀） | skip | PASS |
| `todo list`（唯讀） | skip | PASS |
| `todo close T-0001` | rebuild | PASS |
| `git status` | skip | PASS |
| `cd /tmp && python3 /full/path/video-ops.py backfill VID-001` | rebuild | PASS |
| `save VID-077` / `--operator kai save VID-077` / `lessons add ...` | rebuild | PASS |
| SessionStart 整合 + 靜默 rebuild | success silent | PASS |
| 連續 3 次失敗 → stage 3 警告顯示 | failure_count=3 + 印警告 | PASS |
| 恢復後 → counter 歸零 | failure_count=0 | PASS |

### Kai 行動

`.claude/settings.json` 還沒加 PostToolUse hook（受保護路徑、需 Kai 在 UI 授權）。下面 §「Kai 授權」區附具體 diff、批准後 Phase A 全鏈生效。

### Phase B 移交

跟本 PR 一起放 Codex task prompt（在對話 / PR description）— 讓 Codex 改 `scripts/ops/lib/pipeline.py:save_pipeline()` 加 post-write subprocess call build.py、補完 Kai 手動跑 video-ops.py / 其他 script 直接 import 的 5% case。

---
## v5.61（2026-04-27）

**主題：🔧 Pipeline VID-055~059 回歸修復 + 進口紅茶搬到 VID-060（T-0003 提前完成、含 engine_version bump）**

PR：claude/merge-branches-6bjRF

### 背景

挖到比 v5.59 更深的回歸 — `claude/good-morning-Sffdy` 的 auto-sync（c4fc55e）不只砍了 template marker，**整個 pipeline VID-055~059 mapping 被洗回**。merge-base e0818eb（PR #336 merge 點）原本已有正確的 VID-055~059 對應、被 good-morning 的舊 pipeline 狀態（只有 VID-055=進口紅茶）覆蓋。

### 對比（修復前 vs 修復後）

| VID | 修復前（main） | 修復後 |
|-----|--------------|--------|
| VID-055 | 為什麼要用進口紅茶（D2、2840 views、4/27）| 新店面選址 還有隱藏成本（B2、13142、4/15）|
| VID-056 | 不存在 | 西屯阿檸開幕預告（D1、5303、4/16）|
| VID-057 | 不存在 | 實際走訪松柏嶺茶廠（B2、4054、4/17）|
| VID-058 | 不存在 | 生吃茶葉 台灣茶歷史（B2、2799、4/20）|
| VID-059 | 不存在 | 飲料店茶葉一天用量（D3、3993、4/21）|
| VID-060 | 不存在 | **為什麼要用進口紅茶（從原 VID-055 搬來、保留所有 metadata）** |

`_meta.next_vid`：56 → 61
`_meta.next_idea_id`：71 → 76（IDEA-070~075 都已分配）

### 動作

#### 1. `data/kai/pipeline.json`
- VID-055~059 取自 `claude/store-location-costs-SUYKx`（ground truth、與 merge-base e0818eb 一致）
- 原 main 的 VID-055（進口紅茶）整個搬到 VID-060、idea_id IDEA-070 → IDEA-075
- 進口紅茶的 hook_type / backfill / learning / publish_date 全部保留、無資料遺失
- _meta.next_vid 56 → 61、next_idea_id 71 → 76

#### 2. `data/kai/lessons.json` L-0022 evidence
- evidence: `['VID-055']` → `['VID-060']`（D2 hook 失效是進口紅茶那支、現在編號是 VID-060）
- source_note 加註：「原綁 VID-055、因 2026-04-27 pipeline VID 重編改為 VID-060、進口紅茶搬家保留 hook/views/learning」

#### 3. `data/kai/performance-patterns.json` risk_patterns
- 原 VID-055 的 Hook 弱 entry → VID-060
- 補上 VID-056（完播弱）/ VID-057（Hook 弱）/ VID-058（Hook 弱）/ VID-059（Hook 弱）4 個 risk pattern entry（取自 store-location 的 backfill 結果）

### T-0003 狀態

T-0003「IG 51 vs pipeline 54 對表」原 defer 到 5/4。本 PR 完成核心對齊（缺的 4 支補齊 + 撞號 1 支重編），但若 IG 上還有其他 51 之外的差異、5/4 重新檢視。todos 不關閉、due 維持 5/4 作 follow-up 確認點。

### 為什麼選「進口紅茶搬 VID-060」而非反向

按時間順序：4/15-4/21 五支早於 4/22 進口紅茶。VID 編號歷史上對應 publish 時序、保留新店面選址=VID-055 較對齊歷史；進口紅茶是最後上線、放 VID-060 順理成章。

### Engine version

5.60 → 5.61（pipeline.json 不在 contract scope、但 CHANGELOG 是、且本變更 architecturally 重要）

---

## v5.60（2026-04-27）

**主題：🔧 修補 sync-to-sheets.yml auto-sync workflow（L-0023/L-0024 治本層）**

PR：claude/merge-branches-6bjRF

### 背景

v5.59 修補了 template 回歸（症狀層）。本 PR 修 root cause（治本層）— GitHub Actions `sync-to-sheets.yml` 的 `Sync data files to main` step（line 100-155）有兩個設計缺陷：

1. **Path filter 過廣**：`01-data-brain/`、`03-production-line/`、`data/` 涵蓋 template 子目錄。template 是共享引擎狀態、不該被任意 per-operator branch 的舊版本覆蓋。
2. **Blind overwrite**：用 `git diff --name-only origin/main HEAD` 取得 ALL 不同的檔案、無視該檔是否 branch commits 真的修過。stale branch 上的舊狀態會直接洗掉 main 的新狀態。

### 動作（本 PR、CI/workflow 層）

#### `.github/workflows/sync-to-sheets.yml` 兩處改動（territory override）

**Path 排除 template/**：
```diff
- DATA_FILES=$(git diff --name-only origin/main HEAD -- \
-   "data/" \
-   "03-production-line/" \
-   "01-data-brain/" \
+ DATA_FILES=$(git log --name-only --pretty=format: "$BRANCH_BASE..HEAD" -- \
+   "data/" ":!data/template/**" \
+   "03-production-line/" ":!03-production-line/template/**" \
+   "01-data-brain/" ":!01-data-brain/template/**" \
```

**Branch-modified 而非 diff vs main**：用 `git log --name-only $BRANCH_BASE..HEAD` 只列 branch 自己 commits 改過的檔。stale branch 沒動過的檔不參與 sync、避免「老狀態洗新狀態」。

### 驗證（commit 前）

模擬 good-morning-Sffdy branch 觸發 workflow：
- OLD logic：sync `01-data-brain/template/CLAUDE.local.md`（會誤刪 marker）+ `data/kai/lessons.json`
- NEW logic：sync `data/kai/lessons.json` + `data/kai/performance-patterns.json` + `data/kai/pipeline.json`、**不 sync template** ✓

模擬 store-location-costs-SUYKx branch：
- 只 sync 該 branch commits 真的改過的 2 個檔（`data/kai/performance-patterns.json` + `data/kai/pipeline.json`）✓

### Lesson L-0024（新）

新增 lesson 記錄此 pattern、未來 CI workflow 設計時自我提醒。

### Territory override

`.github/workflows/**` 是 Codex 領土（per `docs/contracts/agent-collaboration.md` §1）。本 PR 由 Claude 改、原因：

1. 此 bug 直接造成今日 main 上的回歸（template marker 砍掉、L-0022 撞號）— critical bug、需快速止血
2. 修法極小（2 個 path 排除 + 1 個 git log 改 git diff）— 風險低
3. Kai 在線、明確指示「最優解 陸續 PR 陸續 MERGE」

> `territory override justified by: critical CI workflow bug causing main regression, fix is minimal, Kai instructed 最優解 陸續 PR`

### Engine version

5.59 → 5.60（CHANGELOG 屬 contract scope）

---

## v5.59（2026-04-27）

**主題：🔧 修復 main 上的 template 回歸 + 解 L-0022 撞號**

PR：claude/merge-branches-6bjRF

### 背景

2026-04-27 多分支整理時發現兩個問題：

1. **Template 回歸**：`01-data-brain/template/CLAUDE.local.md` 的 `POLLUTION_PATTERNS_START/END` marker block（PR #332/#333 加的、L-0022 sync-engine 四層防護的 Q5 配套）被 GitHub Actions bot auto-sync（c4fc55e、從 `claude/good-morning-Sffdy` 自動覆蓋）砍掉 12 行。新客戶 fork 引擎時 template 缺 marker、Q5 污染掃描廢。

2. **Lesson L-0022 撞號**：兩個 Claude session 同日各自寫 L-0022：
   - `claude/fix-alignment-issues-tzf2q`：sync-engine 四層防護（origin=manual、common-ancestor 上的版本）
   - `claude/good-morning-Sffdy`：D2 反問 hook 在『受眾無預設立場』題材失效（origin=verifier、與 VID-055 證據綁定）
   - 後者透過 auto-sync 進 main、覆蓋了前者
   - 兩條都是真實 lesson、不該擇一丟掉

### 動作（本 PR、文件層）

#### 1. `01-data-brain/template/CLAUDE.local.md` 還原 marker block
- 重新插入 `POLLUTION_PATTERNS_START/END` block（含 `{{BRAND_NAME}} / {{BRAND_NAME_EN}} / {{OWNER_NAME}}` 三個預留 placeholder）
- 位置：`## 品牌速查` 後、`## 使用者習慣` 前

#### 2. 解 L-0022 撞號
- L-0022 保留為 D2 hook（origin=verifier、已沉澱、VID-055 evidence）
- L-0023 新編 sync-engine 四層防護（origin=manual、scope=sync-engine、stage=soft）

#### 3. 後續觀察項
- bot auto-sync workflow（`.github/workflows/data-sync-from-feature.yml` 或類似）跳過 PR / CI 直接 push 到 main、是這次回歸根源。後續評估是否關閉 / 改 PR-only 模式（待 Kai 決策）

### 驗證

- `01-data-brain/template/CLAUDE.local.md` 含 `POLLUTION_PATTERNS_START` ✓
- `data/kai/lessons.json` L-0023 sync-engine 四層防護存在、L-0022 維持 D2 hook ✓
- engine_version bumped 5.58 → 5.59 ✓

---

## v5.58（2026-04-27）

**主題：🔧 L-0022 客戶 sync 四層防護整合 — 文件層落地（PR-2+4 合併、PR-1 #332 / PR-3 #333 已 merge）**

PR：claude/update-optimize-kaios-9QSBi

### 背景

L-0022（2026-04-27 對話發現）：客戶 sync 防護完全依賴 `_meta.sync_blacklist` 人工維護、無雙層保護、無 sha 校驗、污染掃描寫死 Kai 紅茶巴士字樣對其他客戶失效、無 schema-migration 警告。四層防護方案：

| 層 | 內容 | PR |
|---|------|---|
| A | 硬編碼 `HARDCODED_CLIENT_TERRITORY` 雙層防護 | #332（Codex）|
| B | sync 前後 sha snapshot/verify/restore | #332（Codex）|
| C | 污染掃描 patterns 改讀客戶 `CLAUDE.local.md` forbidden_terms | #333（Codex）|
| D | `🚨 schema-migration` marker 偵測、客戶端 sync 強制停下 | #333（Codex）|

### 動作（本 PR、文件層）

#### 1. `.claude/commands/sync-engine.md`
- **Step 5.5 新增**：跑 `has_schema_migration_marker(changelog_text)`、偵測到 → 強制停下不 auto-merge、列 marker hits、要求客戶手動 migration
- **Step 6 補強**：sync 前 `snapshot_client_territory` → 覆蓋 → sync 後 `verify_client_territory_unchanged` → 不一致則 `restore_client_territory` + abort
- **Q5 patterns 改讀**：`POLLUTION_PATTERNS` 從寫死改成 `load_forbidden_terms(CLAUDE.local.md)`、客戶各自填、引擎不再寫死紅茶巴士字樣

#### 2. `CLAUDE.md` 新禁令 #14
- 資料層 schema 變動必標 `🚨 schema-migration`、CHANGELOG 必含對應 entry、客戶端偵測到強制停下不 auto-merge
- 例外：additive 變動可註明免標、非破壞性

#### 3. `CLAUDE.local.md` 加 `POLLUTION_PATTERNS_START/END` section
- Kai 紅茶巴士的 forbidden_terms：紅茶巴士 / Red Tea Bus / 阿檸 / 功夫茶 / Kung Fu Tea / 800 杯 / 129.8 萬 / 楷哥
- `01-data-brain/template/CLAUDE.local.md` 同步加 `{{BRAND_NAME}}` placeholder section（客戶 fork 時自填）

### 工程層

- engine_version 5.57 → 5.58
- contract_files: `CLAUDE.md` 4.23 → 4.24
- L-0022 stage：soft → hardened（PR merge 後跑 `/harden`）

### 對應四層防護驗證

- A+B：PR #332 14 條 unit test（snapshot / verify / restore / negation）
- C：PR #333 4 條 unit test（marker / placeholder / exclude / empty）
- D：PR #333 3 條 unit test（detect marker / case-insensitive / multiline）
- 文件層：本 PR 跑 rules-lint + engine-version-check 通過

---

## v5.57（2026-04-26）

**主題：🔧 L-0021 followup — Codex 反問規則寫進 task prompt 模板（避免 Codex 不讀 markdown）+ brand.md [13] meta 撤回到 CLAUDE.md（避免污染 generation skill）**

PR：claude/l0021-followup

### 背景

L-0021 v1.9 硬化（PR #330）後留 2 項餘量、本 PR 全修：

1. **餘量 1**：agent-collab v1.9 §Codex 側紀律段落寫了「Codex 收到模糊指令要回問」、但 Codex 不讀 repo markdown、只看每次 task prompt → 規則寫了等於沒寫。
2. **餘量 2**：brand.md [13] AI 工程協作備忘雖標 meta、但 `scripts/libs/brain_loader.py` 載入整份 brand.md、generation skill 仍會看到工程文字、有污染腳本生成的潛在風險。

### 動作

#### 項 1：agent-collab v1.9 → v1.10
- §Codex 任務 prompt 模板 §必須前綴 加 step 1.5：
  > 任務指令含模糊動作詞（"補一行" / "修一下" / "處理" / "澄清" 等）→ 停下、不要 push、改在現有 PR 留 comment 回問 Kai 動作位置：「請問 X 是要：(a) edit PR #N body / (b) 修檔案 Y 第 Z 行 / (c) 開新 PR / (d) 不改 PR、只回 comment？」
- 直接寫進 bash 模板區塊註解、變成每次 task prompt 必帶內容
- Header 版本 1.9 → 1.10、加變更註記

#### 項 2：brand.md [13] 移除 + CLAUDE.md 禁令 #6 擴充
- 刪 `01-data-brain/brand.md` [13] AI 工程協作備忘 整節（從 SessionStart 注入內容拿掉、避免污染 generation skill）
- `CLAUDE.md` v4.22 → v4.23：禁令 #6 結尾加 pointer 句（指向 agent-collab v1.10、附 territory pre-flight + 動作位置兩條摘要）
- CLAUDE.md 也是 SessionStart 自動注入、visibility 不損失、但內容歸位（工程規則 → CLAUDE.md、不在品牌大腦）

### 工程層

- engine_version 5.56 → 5.57
- contract_files: `docs/contracts/agent-collaboration.md` 1.9 → 1.10、`CLAUDE.md` 4.22 → 4.23

### L-0021 後續更新

- `data/kai/lessons.json` L-0021 hardening_artifacts 加第 3 / 4 筆（agent-collab v1.10、CLAUDE.md v4.23、brand.md 移除）
- `data/kai/hardening-archive.json` 第 2 筆 entry（source="dialog"、follow-up）

### 驗證

- pytest 561 passed
- rules-lint 0 errors
- engine-version-check passed
- check-version-sync passed

### 預期效果

- 餘量 1 解：Codex 收到「補一行」「修一下」這類指令會主動回問、不預設開新 PR（PR #328 反例不該再發生）
- 餘量 2 解：brand.md 純品牌內容、generation skill 不再看到工程規則文字
- L-0021 進化迴路完整收尾、無餘量

---

## v5.56（2026-04-26）

**主題：🔧 L-0021 硬化 — Codex 任務 prompt 模板加 Pre-flight territory check + Action location explicit**

PR：claude/harden-l0021

### 背景

2026-04-26 sleep-mode 後續、PR #327/#328 連續觸發兩種錯：
- **#327 territory 違規**：Claude task prompt 寫「engine_version 5.52 → 5.54 + 加 CHANGELOG v5.54 entry」、CHANGELOG 屬 Claude 領土、Codex 照做、territory-lint fail。Codex 沒錯、Claude task prompt 設計錯。
- **#328 動作位置誤判**：Claude 對 Codex 說「PR body 補一行 territory override」、Codex 解讀為「開新 PR + 把 override 寫進 CHANGELOG 內文」（即 PR #328 自身）。Codex 預設選「開新 PR」、未明示否決就會跑這條。

兩個錯都記入 L-0021（origin=mistake、stage=soft）。Kai 親口確認模式、走 `/harden` 升 hardened。

### 動作

#### 1. `docs/contracts/agent-collaboration.md` v1.8 → v1.9
- §Codex 任務 prompt 模板 擴充三段：
  - **Pre-flight territory check**：path 對照 CODEX_OK 預檢、列出兩種處理（拆 follow-up vs 預授 override）
  - **Action location must be explicit**：四種動作的明寫法（edit PR body / 修檔案 / 開新 PR / 不 push）+ 不要寫的反模式
  - **Sandbox no-origin fallback**：base-check bash 改為支援 Codex sandbox 無 origin remote（HEAD == target sha 即放行）
- 兩個反例寫入文中當記憶錨：PR #327（territory）+ PR #328（動作位置）
- Claude / Codex 雙側紀律段更新

#### 2. `01-data-brain/brand.md` 加 §[13] AI 工程協作備忘（meta）
- 明確標記為「meta、非品牌內容」、生成型 skill 載入時應跳過
- 簡述 territory pre-flight + 動作位置規則 + 反例
- 完整規則指向 `docs/contracts/agent-collaboration.md`
- 此節在 SessionStart hook 注入 brand.md 全文時、Claude 每次對話都能看到（高 visibility）

#### 3. L-0021 stage=hardened
- `data/kai/lessons.json`：L-0021 stage 從 soft 升 hardened、加 hardening_artifacts pointer
- `data/kai/hardening-archive.json`：新增 entry、source="dialog"

### 工程層

- engine_version 5.55 → 5.56
- contract_files: `docs/contracts/agent-collaboration.md` 1.8 → 1.9

### 驗證

- pytest 561 passed（無 regression）
- rules-lint 0 errors
- engine-version-check passed
- check-version-sync passed

### 預期效果

- 下次 Claude 寫 Codex task prompt、會自動跑 territory pre-flight + 動作位置明示
- 同類錯（PR #327 / #328）不該再發生
- L-0021 退役為 hardened、進入 lessons archive 視野

---

## v5.55（2026-04-26）

**主題：🔧 Test bootstrap helper 收斂 + path-bootstrap contract v1.0 → v1.1**

PR #326（`codex/perform-bootstrap-templates-cleanup`）

### 動作

#### 1. tests/test_bootstrap.py 重構
- 新增 `_run_bootstrap()` shared helper、收斂三處重複的 `subprocess.run([\"bash\", str(script), ...])` pattern。
- 統一 `timeout=PROCESS_TIMEOUT_SEC`、失敗時統一 surface `exit_code` / `stdout` / `stderr` 訊息。
- 三個現有 bootstrap test 改用新 helper、行數 -3 / 改寫 +21。

#### 2. docs/contracts/test-path-bootstrap.md v1.0 → v1.1
- 新增 §Canonical bootstrap paths 後的 **Priority rule**：「prepend in helper order so the intended test target path stays at index 0」。
- §Rules 結構化為 **Allowed** / **Forbidden** 兩塊：
  - Allowed：呼叫現有 helper、或為新 path domain 新增 helper
  - Forbidden：在個別測試中當 helper 已涵蓋還做 ad-hoc `sys.path.insert/append`

### 工程層
- engine_version 5.54 → 5.55
- contract_files: `docs/contracts/test-path-bootstrap.md` 1.0 → 1.1

### 備註
- 本 PR 原始 task 是「補完 multi-operator bootstrap + 清死路徑」，但 Codex 解讀偏向 test-bootstrap helper 收斂。經 review 判定工作品質有獨立價值、改作為 quality PR 接受。原始 #2/#3 任務由 PR #327 完成。

### 驗證
- pytest 560 passed
- rules-lint 0 errors
- engine-version-check passed

---

## v5.54（2026-04-26）

**主題：🔧 PR #326 任務對齊修正（#2/#3）+ engine 升版修 CI**

PR：work（follow-up for #326 review）

### 動作

- `scripts/utils/lib/config.py`：移除未使用常數 `TODO_ROOT`（清理 dead config）。
- `scripts/utils/lib/sync_tabs.py`：報表月統計不再獨立計算 `HOLD` 欄位；舊資料中的 `HOLD` 改併入「總在製」。
- `scripts/utils/lib/builders.py`：報表「本月影片產量」移除 `HOLD` 顯示列，與狀態策略一致。
- `engine-manifest.json`：`engine_version` 由 5.52 升至 5.54（5.53 已使用）。

### 備註

- 任務 #1（`scripts/bootstrap/bootstrap-client.sh` 補 3 行 `copy_if_missing`）依 review 指示，待 #325 merge 後再處理，避免撞檔與 rebase 成本。

---


## v5.53（2026-04-26）

**主題：🔧 Sleep-mode autonomous run — README 真相對齊 + CI workflow 防卡死 + session-start hook 容錯 + multi-operator template 補完**

PR：claude/system-optimization-KuVCP（Claude Code Opus 4.7 sleep mode 自動產出）

### 背景

Kai 將進入離線狀態、給 Claude Code 「sleep mode」任務：在 token budget 內把當下系統的架構債 / 文件債 / 驗證債 / 維護債盡量做完、不開新 skill、不大重構、不 commit/push（後改由 stop hook 觸發 commit + push）。

### 動作

#### 1. README 9 處事實漂移修正
- engine v5.42 → v5.52（隨後 5.53）
- Python ~11,466 → ~12,800 lines、ops/lib + utils/lib 拆開計
- 自動化測試 54/522 → 61/560（兩處）
- CLAUDE.md v4.20/12 禁令 → v4.22/13 禁令
- workflow.md v2.22 → v2.24
- `.claude/skills` 19 stub → 7 stub（Phase 5 真退役後實際）
- Skill thinning timeline 補上 v5.52 stable
- 結尾 PR pointer 改為「最新 engine v5.53」

#### 2. workflow.md broken file refs（contract）
- `shared-references/title-rules.md` / `shared-references/templates/hook-templates.md` 加上 `02-skill-factory/` 前綴
- 對齊 brand.md / index.md / cases.md / CHANGELOG 已在用的 full-path 慣例
- rules-lint missing_file warning 7 → 5（剩餘是內容檔 AI-pattern）

#### 3. CI workflow 加 timeout-minutes（5 個）
- engine-version-check / sync-readme-to-main / territory-lint：5 min
- rules-lint：10 min
- sync-to-sheets：15 min（job-level，原本只有單一 step 5min）
- 防 GitHub Actions hang 燒 quota

#### 4. sync-to-sheets.yml 死路徑清理
- Debug step 不再 cat 已退役的 `00-control-center/todo/工作待辦.md` / `雜事待辦.md`、改為列出 `data/<op>/todos.json` item count
- `Sync data files to main` step 從 git diff pathspec 移除 `00-control-center/todo/`（目錄已不存在）

#### 5. session-start hook 失敗容錯
- `.claude/hooks/session-start.sh` 的 remote-only `apt-get install ffmpeg` + `pip install faster-whisper` 加 `|| true`、避免 set -e 終止整個 hook 導致 brand.md 不注入

#### 6. 補完 contract 版本標籤（contract）
- `docs/contracts/test-path-bootstrap.md` 補上 `> version: 1.0 | last_updated: 2026-04-26` inline header
- 原本 manifest 標 v1.0 但檔案沒 inline → rules-lint check_engine_manifest_inline_versions() 靜默 skip
- 補上後 lint 會把它納入版本一致性檢查

#### 7. dashboard README 修 broken doc link
- `dashboard/README.md` 兩處引用的 `docs/contracts/design-collaboration.md` 已歸檔、改指向 `docs/archive/design-collaboration.md`（v1.0 已歸檔註記）

#### 8. data/template/ 補完 + schema 對齊
- 新增 `data/template/brand-monitor.json`（空殼、新 client bootstrap 後可填關鍵字）
- 新增 `data/template/social-followers.json`（tiktok/instagram/facebook 三平台 placeholder）
- 新增 `data/template/topic-history.json`（30-day rolling schema 空殼）
- `data/template/hardening-archive.json` schema_version 0.1 → 0.2、description 對齊 `_ARCHIVE_EMPTY` 在 `scripts/ops/lib/hardening.py` 的 v4.67 dialog-only 定義
- 配套 Codex task：`scripts/bootstrap/bootstrap-client.sh` 需追加三行 `copy_if_missing`（不在本 PR 範圍、屬 Codex 領土；已開 codex branch `codex/perform-bootstrap-templates-cleanup` 處理）

#### 9. AI_SYSTEM_UPGRADE_REPORT 落檔
- `00-control-center/AI_SYSTEM_UPGRADE_REPORT_2026-04-26.md` — 本輪 sleep-mode session 的執行記錄、剩餘 risks、recommended next actions

### 工程層

- engine_version 5.52 → 5.53
- 4 commits（README sync / CI hardening / system resilience / report）+ 1 fix-up commit（territory + version bump）

### 驗證

- pytest 560 passed
- rules-lint 0 errors（5 warnings 全為內容檔 AI-pattern）
- skill-io-lint / brand-ref / check-version-sync 全綠
- validate-all 0 errors（1 warning：VID-009 script_path、需 Kai 判斷）
- 5 個 workflow YAML parse OK

### 餘量（後續處理）

- VID-009 資料一致性需 Kai 判斷
- `scripts/utils/lib/config.py:20 TODO_ROOT` 死路徑（Codex 領土、已開 task）
- `scripts/utils/lib/sync_tabs.py + builders.py` HOLD 狀態殘留審視（Codex 領土、已開 task）
- 2 處 utils/lib hardcode `data/kai/...`（Codex 領土、未開 task）

---


## v5.52（2026-04-26）

**主題：🔧 Multi-branch consolidation cleanup — Codex bootstrap superset 收斂 + 18 PR 雜亂收束 + manifest drift 補齊**

PR：claude/merge-current-changes-jkv5a（merge session 收尾）

### 背景

本次 session 對齊三件事：
1. **PR #321 merge**：Codex 同一任務 `task_e_69ed072dccc083308aa4f897a29d2423` 跑了 10 次、產生 10 支 codex/define-task-boundaries-* 變體 + 10 個 PR。#321 是最新 / 最完整版（file-level superset 跨 9 變體驗證）、其他 9 支落敗 close。merge 時撞 `tests/conftest.py` conflict、Claude 在 codex/* branch 解 conflict + 走 territory override（PR body `territory override justified by:`）。
2. **PR #322 merge**：T-0019 defer record（T1 IG vs pipeline 釐清 deferred until 2026-04-29）落地進 main。
3. **Stale branch cleanup**：~15 支 stale branch 由 Kai 從 GitHub UI 手動刪（git proxy 對 `--delete` 操作回 HTTP 403、CLI 路徑無解）。

### 動作

#### 1. engine-manifest.json drift 補齊

- 加 `docs/contracts/test-path-bootstrap.md`（v1.0、#321 帶進來但漏進 manifest）→ contract_files
- 加 4 internal_files：`tests/path_bootstrap.py`、`tests/timeouts.py`、`tests/test_import_bootstrap.py`、`tests/test_pytest_invocation_consistency.py`
- engine_version 5.51 → 5.52

#### 2. 3 條 session lessons（origin=manual）

- L-NEW-1：「Codex 同一任務跑 N 次、產生 N 個 PR、累積 stale → merge 撞 conflict 地獄」  
  counter：「觸發 Codex task 後等結果處理（merge / close / 改 prompt 重觸發）；不重複觸發同一 task」
- L-NEW-2：「Open PR 累積到 18 才被注意 → cleanup 成本爆炸」  
  counter：「Open PR > 3 應入 adoption gate（owner=kai）、session 開頭強制 review」
- L-NEW-3：「Defer 機制 add `defer:` todo 但 hook 沒辨識 prefix、原 T-0003 持續 surface」  
  counter：「Codex 修 `scripts/utils/lib/adoption_gate.py`：defer 機制偵測 `defer:` prefix、suppress 對應原 todo（task brief 進 todos）」

#### 3. Codex task brief 寫入 todos

T-NEW：defer 機制 hook 修復 prompt（含 base-check + repro + 預期 fix 方向 + test case）、待 Kai 觸發 Codex。

### 學到的教訓（meta）

- **Claude × Codex 領土**：`tests/**` 是 Codex 領土、Claude 不該動。本次 conflict resolution 走 territory override 是例外、不是常態。長期解法是把 Codex 觸發紀律寫進 CLAUDE.md（待後續 lesson 升 hardened）
- **Manifest drift 是慢性病**：每次 PR merge 後該驗 manifest 是否同步、不該等到下次 sync-engine 才發現
- **「全做」級指令必走 Plan mode**：本次正確走 plan mode（禁令 #3.5 觸發）、出清單 → Kai approve → 執行、避免「邊做邊問」失控

---


## v5.51（2026-04-26）

**主題：🔧 T-0017 Phase 5b Claude 配對 — 5 核心 SKILL.md 加 brand-refs frontmatter + data-brain-manifest 改 lint-driven**

PR：claude/phase-6-brand-refs（配對 Codex PR #319）

### 背景

Codex PR #319（engine v5.50）落地 `scripts/lint/brand_ref_lint.py`、自動掃 SKILL.md 的 `brand.md [N]` 引用 + frontmatter `brand-refs:` 宣告。本 PR 對齊 SKILL.md 端：
1. 5 核心 SKILL.md frontmatter 加 `brand-refs:` 宣告（消除 under/over-declared warning）
2. `data-brain-manifest.md` v2.3 → v3.0：刪手寫矩陣、改 lint pointer

### 動作

#### 1. 5 核心 SKILL.md frontmatter 加 brand-refs（不 bump 版本、純 metadata 加欄位）

對應 lint inline manifest：
- `02-skill-factory/discovery/SKILL.md`: `brand-refs: [3, 4, 5, 6, 10, 11, 12]`
- `02-skill-factory/generation/SKILL.md`: `brand-refs: [5, 6]`
- `02-skill-factory/quality/SKILL.md`: `brand-refs: [3]`
- `02-skill-factory/orientation/SKILL.md`: `brand-refs: []`（顯式宣告無 brand 依賴）
- `02-skill-factory/distillation/SKILL.md`: `brand-refs: []`（同上）

#### 2. `02-skill-factory/shared-references/data-brain-manifest.md` v2.3 → **v3.0**

- 刪手寫 skill × brand section 矩陣（14 個舊 skill 名）
- 改寫為「跑 `brand_ref_lint --manifest` 看當前依賴」說明
- 加設計說明（為什麼從手寫改 lint、4.6 慣性 vs 4.7 視角）
- 保留「模組簡介」表（人類可讀 brand.md section 內容速查、不參與 lint）

#### 3. `engine-manifest.json`
- engine_version 5.50 → 5.51
- contract_files：data-brain-manifest.md 2.3 → 3.0

### 4.7 視角原則對齊

- 準則 B（可變 lint 就 lint）：手寫矩陣 → lint 自動推導
- 準則 C（規則化勝於文檔化）：SKILL.md frontmatter 是 SSoT、文檔降為 derived
- 準則 F（層次正確）：本能力停在 lint + CLI 層、不該升 skill

### Verification

- rules-lint --ci ✅ 0 errors
- brand_ref_lint ✅ frontmatter `brand-refs:` 跟內文 inline 一致、no under/over-declared warnings
- check-version-sync ✅
- engine-version-check ✅
- pytest 預期全綠

### territory override

無 — 全為 Claude 領土。

### 相關

- 配對 Codex PR #319（engine v5.50、`brand_ref_lint.py` 落地）
- T-0017 Phase 5b 完成（從原手寫矩陣重寫變成自動化 lint）
- skill-design-principles.md v1.5 + skill-architecture-principles.md v1.4 三大發現

---


