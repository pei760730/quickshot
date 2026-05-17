# 數據大腦索引

> **📍 資料地圖 SSoT**（v4.39 新增、統一定義）：本檔是「哪個資料檔在哪、誰寫、誰讀、何時載入」的**單一真相源**。`CLAUDE.md` 的資料地圖 = 本檔摘要指向；`02-skill-factory/shared-references/data-brain-manifest.md` = 本檔的 skill × module 依賴矩陣補充（不重複載入規則）。新增資料層 / 改動載入邏輯 → 只改本檔。

> **Trigger 區分（v4 lazy load、對齊 CLAUDE.local.md + brain-loading.md v1.5+）**：
> - **Session 起手**：SessionStart hook 不再 cat brand.md 全文、只印 1 行提示（v4.62 起 auto-inject 退役、每 session 省 ~27k token baseline）。`CLAUDE.local.md` 已含品牌名 / operator / forbidden_terms 等識別資訊每 session auto-load、身份不受影響。
> - **產出腳本時**（本檔定義）：生成型 Skill 被觸發的那一刻、`scripts/libs/brain_loader.load_for_skill()` 自動載入下表完整資料進 BrainBundle。
> - **對話中按需**：Kai 隨口提品牌事實 / Claude 需 brand context 推理 → Claude 主動 `Read 01-data-brain/brand.md`（單次載入、僅該對話）。
>
> 三條路徑互補、不重複；Session 不再「先載 brand.md」、所以 cases / lessons / performance-patterns / banned-words 一律走 skill load 或 on-demand。

## 載入（產出腳本時）

### 每次產出前必讀

| # | 檔案 | 內容 | 消費者 |
|---|------|------|--------|
| 1 | `brand.md` | 純品牌知識 [0]~[12]（業務 / 受眾 / 洞察 / 禁忌 / 競品 / 平台 / 數據 / 目標）| 所有生成型 Skill |
| 2 | `personas/kai.md` | Kai 人格（[1] 說話風格、[2] 觀點態度、[3] 禁區、[4] 創作野心、身份與背景）| 所有生成型 Skill（v4.97+）|
| 3 | `personas/an.md` | 藏鏡人安 人格（觀眾印象 / 兩種模式 / 口頭禪 / 邊界）| 自動載入 BrainBundle.an_md（PR #432 merged 2026-05-11、選用欄位、缺檔回空字串）|
| 4 | `cases.md` | 案例庫 [8] + 高表現影片記錄 | 需要具體例子時 |
| 5 | `data/[operator]/performance-patterns.json` | 成功模式 + 風險模式 | 所有生成型 Skill（見 `shared-references/performance-injection-protocol.md`） |
| 6 | `data/[operator]/lessons.json` | 統一 lessons（avoid rules / 錯誤 / 偏差 / 畢業規則），schema 見 `docs/contracts/lessons-schema.md` | 所有生成型 Skill（按 stage + scope 過濾、origin 7 種全收） |
| 7 | `02-skill-factory/shared-references/banned-words.md` | 禁用詞黑名單 | 所有生成型 Skill |

### 原文庫（不主動載入，定期沉澱用）

| # | 路徑 | 內容 | 載入時機 |
|---|------|------|---------|
| 8 | `01-data-brain/transcripts/` | Kai 的語音筆記 / 文字原文完整保留 | 沉澱分析時才讀（每累積 5 篇觸發） |
| 9 | `01-data-brain/interview-bank.md` | 訪談題目庫（Q-Bank、Q22~Q130 原文 + 內容價值）| `generation` skill mode=interview 載入；其他 skill 找「Kai 對某題真實回答」時參考 |

### 知識儲存分工

| 儲存 | 寫入者 | 寫入時機 | 作用 |
|------|--------|---------|------|
| `data/[operator]/performance-patterns.json` | backfill auto-extract + compute_pattern_stats | 每次回填後（含 win_rate/confidence 計算） | 注入成功/失敗模式（附信心等級） |
| `data/[operator]/lessons.json` | `video-ops.py 記錯` / `diff-script` / verifier 沉澱 / quality skill phase=fix 高頻（設計中、未實作）/ 對話中 Claude 即時提案 | 事件驅動 + 對話提議 → Kai 確認後透過 `video-ops.py` 寫入（內部呼叫 `add_lesson()` / `promote_stage()`） | 統一避免模式 + 錯誤記憶 + 偏差 + 畢業規則（origin 7 種、stage 3 種：soft/hardened/archived）|
| `data/[operator]/todos.json` | `video-ops.py todo add` / 對話中「待辦：XXX」命令 / lesson close 時自動連動 | 事件驅動 → Kai 確認後透過 `video-ops.py` 寫入 | 待辦清單結構化（id / state / priority / due / related_vid / related_lesson_id）、逾期/重要度可查詢 |
| `data/.operators.json` | `bootstrap-client.sh` → `reset-operator.py` | 新客戶初始化 | operator 註冊（blacklist 保護、sync-engine 不覆蓋） |
| `data/[operator]/hardening-archive.json` | `/harden` 對話內硬化成功後寫入（source="dialog"）| `harden_from_dialog()` 執行成功 | 已硬化記錄（稽核追溯、queue 層 v4.67 退役）|
| `02-skill-factory/shared-references/banned-words.md` | 偏差分析 / 手動 | 人工確認後 | 禁止特定詞彙 |
| `01-data-brain/transcripts/*.md` | 語音筆記流程 | Kai 貼逐字稿 / 錄音轉文字時 | 原文完整保留，定期沉澱交叉分析 |

> **v4.36 合併**（2026-04-20）：`claude-mistakes.json` / `generation-rules.json` / `script-deviations.json` 三檔合併為 `lessons.json`，舊檔改為 `*.legacy.json` 供回滾（v4.76 清除、migration 驗證後 `lessons.json` 11 條皆為 migrated 內容）。合併原因：三者本質都是「下一輪生成要避開 / 要學會的東西」，`origin` 欄位保留來源、`stage` 欄位取代三檔各自的畢業邏輯。完整 schema 見 `docs/contracts/lessons-schema.md`。
> **v4.39 新增**（2026-04-21）：`todos.json`（取代原 `00-control-center/todo/*.md` markdown 純文字機制）、`data/.operators.json`（v4.38 架構改動）。
> **v4.41 lessons 觀測 + 硬化前置契約**（2026-04-21、**已退役**）：原設計加 `hit_count` / `last_hit_at` / `hardening_status` 欄位 + `video-ops.py lessons hit` CLI + hit ≥ 3 門檻觸發硬化。v4.63 Stage C 實證後全退：schema 降維 v2.0（stage = soft / hardened / archived、無 hit 欄位）、CLI 刪、硬化改為對話中 Claude 主動判斷（見 workflow.md v2.9 §對話中自然標注 / §Lesson 硬化提議）。v4.74 清除 video-ops-cli / CLAUDE.md 殘留引用。

## 進化觸發

> **v2 改動**（對齊 `.claude/rules/workflow.md` v2.2）：主驅動改為對話中即時判斷；下列門檻降級為 fallback 安全網。

**主驅動（對話中即時判斷）**：
- 回填對話結束前：Claude 判斷是否揭露新模式 → 提 diff
- 語音筆記 / 逐字稿沉澱後：判斷反覆比喻 / 觀點演化 / 隱藏洞察 → 提 diff
- Kai 說出新品牌事實：問「要更新到大腦嗎？」+ 具體 diff
- quality skill phase=fix / phase=check 連續修到同類：直接提沉澱，不等 ≥3 次
- 錯誤命令「記錯：XXX」：除了記入 lessons，判斷是否已達畢業強度

**Fallback 安全網（門檻不再是主驅動）**：
- 回填累計 ≥ 5 筆未審議 → 強制盤點一次（若主驅動都沒提，代表 Claude 漏判、記入 lessons）
- brand.md 任一 section `last_updated` > 30 天 → 對話開頭提醒
- `transcripts/` 累積 ≥ 5 篇新原文 → 批次交叉沉澱分析（見下方）

### 原文沉澱機制

**觸發**：每累積 5 篇新原文（從上次沉澱後計算）

**分析內容**：
1. **反覆出現的比喻/框架** — 多篇都提到的概念 → 代表 Kai 的核心思維模型，提議寫入 brand.md
2. **觀點演化** — 同一話題早期 vs 後期講法不同 → 捕捉思想變化，更新 brand.md 對應段落
3. **隱藏知識點** — 單篇看不出，多篇交叉比對浮現的新洞察 → 提議寫入 brand.md 或 cases.md
4. **語感/口頭禪** — 累積夠多才能準確抓到 → 提議更新 banned-words.md 替換表或 `lessons.json`（origin=`quality` 或 historical `humanizer`）

**輸出**：在對話中展示沉澱結論，Kai 確認才寫入對應檔案

## 進化紀錄

### 待審議
_無_

### 已執行
- 2026-04-21：v4.39 資料地圖 SSoT 統一 + todos.json 契約（取代 md 純文字待辦）+ data/.operators.json 加入分工表
- 2026-04-20：v4.36 三個 skill-memory JSON 合併為 lessons.json（origin 保留來源、stage 取代畢業邏輯）
- 2026-04-13：新增原文庫（transcripts/）+ 兩層結構（精華→brand.md，原文→transcripts/）+ 每 5 篇沉澱機制
- 2026-04-07：13 模組合併為 brand.md + cases.md，消除假載入規則
- 2026-04-06：數據大腦拆分為索引 + 模組化架構
- 2026-03-27：合併 asset-library 到 JSON
