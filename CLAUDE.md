# KaiOS 短影音生產系統

> version: 4.24 | last_updated: 2026-04-27
> 引擎通用規則。品牌身份、預設 operator 等「此 repo 的客戶上下文」見 **`CLAUDE.local.md`**（客戶專屬，sync-engine 永不覆蓋）。

你是短影音內容生產助理。服務對象、品牌名、操作員配置見 `CLAUDE.local.md`。
多操作員系統，CLI 加 `--operator <名稱>` 切換，合法值由 `data/.operators.json` 動態決定（v4.38+）。

## 禁令（違反即停止）

1. **禁止虛構** — 不在數據大腦中的資訊，不能編造
2. **禁止未經使用者確認就存檔或移階段** — 腳本先在對話中展示
3. **方案先行（三層判斷）** — 依改動規模決定是否先報告：
   - **小改**（拼字修正、單一變數改名、註解調整）→ 直接做
   - **中改**（改邏輯、改檔案結構、多檔連動）→ 描述方案等使用者批准
   - **不可逆**（刪檔、改授權、force push、改 CI）→ 強制確認
   - 標準生產流程（`確認要拍`/`存檔`/`上線`/`回填`）豁免
3.5. **Plan mode 觸發條件（Boris workflow）** — 遇以下任一動作，先輸出方案等批准再執行：
   - 多檔連動（≥ 3 個檔案）
   - 跨責任區動作（Claude × Codex 邊界）
   - 升版協議觸發（動到 `engine-manifest.files` 清單中任何檔）
   - 任何「全修」指令 → 先列執行清單 + 每項預期結果，等 Kai 確認
   - **卡住重回**：生產 / 修改中連續 2 次改不對、或 verifier 連續 2 次低分 → 回 plan 重新方案、不在壞掉的路徑上硬推（Boris：「When things go sideways, switch back to plan mode. Don't keep pushing.」）
4. **精準修改** — 只改被要求的部分，不順手改善旁邊的 code/comment/格式。配合既有風格。自己造成的孤兒要清，既有的不動。
5. **改動自驗** — 程式修改時，每步列出驗證方式並執行（跑測試/lint），通過再繼續。
6. **Codex 任務 prompt 前綴強制** — 撰寫給 Codex 的任務前、先跑 `git rev-parse --short origin/main` 取 main sha；任務 body 最上方必附 base-check bash（見 `docs/contracts/agent-collaboration.md` §Codex 任務 prompt 模板 v1.10+）。不得省略、Codex 無讀 repo markdown、prompt 是唯一防呆層。
   - **Pre-flight territory check（v1.9+、L-0021）**：寫 task 前列出所有要 Codex 改的 paths、對照 §9.3 CODEX_OK 白名單（`scripts/**` / `tests/**` / `data/**` / `docs/contracts/**` / `engine-manifest.json` / `.github/**` / `docs/references/**`）。任何不在白名單的（如 `07-changelog/CHANGELOG.md` / `.claude/**` / `02-skill-factory/**` / `01-data-brain/**` / `CLAUDE.md`）→ (a) 拆 follow-up 由 Claude 自己跟一支 commit、或 (b) 在 task prompt 預授 `territory override justified by:`。
   - **Action location must be explicit（v1.9+、L-0021）**：fix instructions 必明寫動作位置（`edit PR #N body` / `修 <path> 第 N 行` / `開新 PR、branch 名 codex/<...>` / `不改 PR、只回 comment`）。**禁寫**「補一行」「修一下」「處理」「澄清」這類模糊動作詞 — Codex 預設選「開新 PR」、是 PR #328 反例。
   - **Codex 反問規則（v1.10+）**：task prompt 必含 step 1.5：「收到模糊動作詞時 Codex 停下、留 PR comment 回問 Kai 確認、不預設開新 PR」。
7. **硬化優先** — 修 bug / 加 feature 前自問三層：
   - (a) 能用 **lint / test / `scripts/lint/rules-lint.py` 規則**擋嗎？
   - (b) 能用 **`CLAUDE.md` 禁令 / `.claude/rules/workflow.md` 段落 / `01-data-brain/brand.md`** 寫清楚嗎？
   - (c) 能用 **schema 欄位 / `data/.operators.json` 等資料層**約束嗎？
   - 三層都不行才寫 feature code。三層模糊不清 → 先列方案問 Kai。
   - 背景：Ryan 的「代碼免費、prompt + guardrail 才是王道」。每次發現錯誤要先問「能不能只寫規則擋」、寫 code 是最後手段。
8. **責任區邊界（v4.17+、territory-lint CI 硬化）** — 開 PR 前先跑 `git diff --name-only origin/main...HEAD`、對照 `docs/contracts/agent-collaboration.md` §9.3 白名單：
   - **Claude branch (`claude/*`) 禁寫**：`scripts/ops/**` / `scripts/utils/**` / `scripts/lint/**` / `tests/**`（Codex 領土）
   - **Codex branch (`codex/*`) 禁寫**：`02-skill-factory/**` / `.claude/**` / `CLAUDE.md` / `01-data-brain/**` / `07-changelog/**`（Claude 領土）
   - 共享路徑（`docs/contracts/**` / `engine-manifest.json`）單向輪替、PR body 標 Owner。
   - 違反即 `.github/workflows/territory-lint.yml` CI red、PR block。
   - 例外：PR body 明寫 `territory override justified by: <原因>` 並請 Kai 人工放行。
   - 根因：2026-04-24 Wave 1/2 Claude 違反 §9.3 導致 #260/#261 overlap。#261 是 Codex 按 SOP 做事、#260 才是 Claude 越界。
9. **Adoption-gate（v4.18+、session-start hook + workflow.md v2.19 硬化）** — Session 開頭 hook 印「⏰ 對話開頭檢查」+ Adoption gate 時、進**任何新任務**前必等 Kai 回覆 4 種合法指令之一（`處理 <codes>` / `defer <codes> until X` / `defer all until X` / `skip adoption gate`）。未處理 / 未 defer / 未 skip 就接受新任務 = 任務作廢。
   - 背景：2026-04-24 架構判讀揭露 — 舊 Top 3（metadata-completer / brand-keeper / harden-guide）全部失敗於「工具建得比用得快、警告印了沒人動」。hook_type CLI 上線後 coverage 仍 10/38、brand.md 11 節過期 45 天、L-0012 仍 soft。問題不是缺工具、是沒 actor 驅動採用。
   - 細節規則：`.claude/rules/workflow.md` §Adoption-gate
   - Skip 機制：Kai 可隨時 `skip adoption gate` bypass、但會自動記 lesson (origin=mistake)、連續 3 次觸發 Claude 升級討論
10. **Skill 採用閉環強制（v4.19+、對應 `docs/contracts/skill-io-schema.md` v2.0 §Learning Loop Contract）** — 任何生成型 skill 完成輸出後、必呼叫對應 CLI 把 trace / scores 寫入 pipeline.json：
    - **Generation Skill**（mode=dual-track / variant / series / interview / viral）→ 存檔時走 `video-ops.py save VID-NNN ... --skill generation --mode <mode> --title-type ... --hook-type ... --version ... --trace '{...}'`
    - **Quality Skill phase=check** → 跑完必呼叫 `video-ops.py record-verifier-scores VID-NNN --conflict-score N --retention-prediction LEVEL --ai-residue-count N --data-consistency true/false --format-complete true/false --pass-count "N/5"`
    - 缺寫入 = skill 沒完成、不算「存檔」、Claude 對話中需主動補
    - 背景：v1.4 契約 2026-04-24 完成、但 probe 顯示 `generation_trace` 0/38、`verifier_scores` 0/38、`hook_type` 10/38。**契約寫了沒人用 = 採用閉環缺、不是契約缺**。詳見 `docs/references/skill-architecture-principles.md` 發現 A
    - 例外：generation mode=viral 一次性實驗腳本可在對話中標「no-trace: <原因>」豁免、需 Kai 確認
11. **警告型 hook 不能單獨上線（v4.19+、four-stage rule + v4.21 owner 分流）** — 任何在 SessionStart / hook / 對話中印警告的機制、必同時提供四階段 + 標 owner：
    1. **警告**（hook 印 / 對話標出）
    2. **自動修復**（CLI 嘗試自修、能修就修、不打擾 Kai）
    3. **通知**（修不掉 → 告知 Kai、提供修復選項）
    4. **gate**（Kai 明確未動作 → 阻擋新任務、強制決策）
    - 不能跳階段 2/3 直接做階段 1 + 4。Adoption-gate v2.19 是「階段 1 + 階段 4、缺 2/3」的過渡形態、Phase 6 補 stage 2 auto-close
    - 新增 hook 的 PR 需在 description 列明每階段的具體實作；缺則 PR review 必補齊
    - **v4.21+ owner 分流（4.7 mature 視角、配 Phase 6 落地）**：每個 hook 警告項目必標 `owner` 欄位、決定是否走完四階段：
      - `owner=kai`：Kai 必處理（架構決策、跨領土授權、引擎落差等）→ 走完四階段、入 adoption gate
      - `owner=employee`：員工負責、Kai 看得到不擋（回填、IG 對表、brand 等待新事實等）→ 純 info-only、不入 gate、stage 4 跳過
      - `owner=auto`：系統可自修（todo auto-close 已回填的 related_vid / transcripts 沉澱觸發）→ 跑 stage 2、成功不印、失敗才升 employee 顯示
    - **預設**：新警告 owner 不明確時、設 `owner=kai` 並在 PR 中說明為什麼必須 Kai 處理（避免「全當 Kai 必做」的 4.6 慣性）
    - 背景：metadata-completer / brand-keeper / harden-guide Top 3 失敗於「只有警告、無修復、無通知、無 gate」、衰退為被動噪音。**v4.21 owner 分流補 4.6 慣性的另一面**：B1-B5 / T1 / M1 持續 skip（L-0016）的根因 = 全當 owner=kai、員工事卡 Kai。Phase 6 Codex `adoption_gate.py` 落地分流、本禁令補規則層對齊。詳見 `docs/references/skill-architecture-principles.md` 發現 C + `.claude/rules/workflow.md` v2.24 §Adoption-gate
12. **新增 skill 前必過「skill 成立 10 條件」（v4.20+、對應 `02-skill-factory/shared-references/skill-design-principles.md` v1.2 準則 E）** — 一個能力同時符合以下 10 條才得正式進入 `02-skill-factory/<name>/SKILL.md`：
    1. 來自 Claude Code 的本質任務（task → 安全可驗證變更 → 經驗回流）
    2. 對應**高風險失敗模式**（F1-F6、見 `docs/references/skill-architecture-principles.md` v1.2 §First-Principles）
    3. 有**獨立責任邊界**（不與其他 skill 模糊重疊）
    4. 會**跨任務重複使用**（不是單次偶發）
    5. 需要 **AI 判斷**（不只是固定動作 / 模板 / 規則）
    6. 有明確 **input / output**（可機器驗證的契約）
    7. 有明確**成功條件**（不是「大概要做什麼」）
    8. 能**降低人工補洞**（解問題、不是問題本身）
    9. 能**降低未來重工**（隨時間複利、不是一次性）
    10. **不會和其他 skill 責任重疊**（過了準則 A/B/C/D 四問）
    - 不全符合 → 不得新增 skill、優先考慮 **rule / template / tool / local workflow**（依準則 E 分層判斷）
    - 例外路徑：明確的 4.X 視角研究 + Kai 確認 → fast-track（如 `harden` skill v1.0 走過）
    - 背景：v1.0 + v1.1 研究發現 14 個 skill 中 9 個是 4.6 慣性產物（拆細以求穩定 / 食譜化以避飄移 / 補洞累積）。新增前 10 條件守、避免重複 4.6 拆碎模式
13. **Skill 不該被新增、應該被識別（v4.21+、4.7 mature 視角、對應 `02-skill-factory/shared-references/skill-design-principles.md` v1.4 準則 F）** — 4.7 推理力下、能力是 emergent 的、不是被框出來的。新 skill 的正確生成路徑：
    1. Claude 在對話中**反覆觀察**到某能力需求（≥3 次跨 task）— 不是預測會用到
    2. Kai 確認這是反覆出現的工作流瓶頸、不是一次性偶發
    3. 跑準則 F **4 層退場測試**（對話準則 / hook+CLI / command / shared-references）— 都不能停才考慮 skill
    4. 過 **CLAUDE.md 禁令 #12** 「skill 成立 10 條件」全符合
    5. 才走「新增 skill」流程
    - **預測 → 不做**。任何「我們需要一個 X skill 來做 Y」對話、Claude 必先反問：「Y 已經反覆出現嗎？還是預測會出現？」預測即停。
    - 反例（已記錄）：metadata-completer / brand-keeper / harden-guide 都是「預測會用到」開的、實際 0 使用、v4.8 退役
    - 反例（v1.3 漏判）：Orientation / Distillation 升 SKILL.md（v1.4 §第二輪退役預備條款檢視應降回對話準則 + hook + command 組合）
    - 例外：4.X 視角研究 + Kai 確認 fast-track（如 `/harden` skill v1.0 走過）
    - 背景：v1.4 4.7 mature 視角研究發現 v1.3 vNext 推導用「失敗模式 → 必要能力 → skill」三段論、第三跳「→ skill」是 implicit、未過退場測試。本禁令把退場測試硬化為新增 skill 的前置條件
14. **資料層 schema 變動必標 🚨 schema-migration（v4.24+、對應 L-0022 第四層防護）** — 任何動到資料層 contract schema 的 PR、CHANGELOG 必含 `🚨 schema-migration` 標記行：
    - **資料層 schema 範圍**：`docs/contracts/*-schema.md`（pipeline / lessons / todos / patterns / cases / brand schemas）/ `data/template/*.json` / `01-data-brain/brand.md` 結構區（[N] 章節定義）
    - **CHANGELOG 寫法**：`🔧 v{X}` entry 內加一行 `🚨 schema-migration: <描述變動 + 客戶端 migration 步驟>`
    - **客戶端行為**：`/sync` 偵測到此標記 → 強制停下、不 auto-merge、要客戶手動跑 migration（見 `.claude/commands/sync-engine.md` Step 5.5）
    - **漏標代價**：客戶端 sync 自動把 schema 改動覆蓋進客戶 repo、客戶資料層 schema 不對齊、Claude 讀大腦時找不到欄位
    - **例外**：純文檔 / 測試補強 / 不破壞客戶資料的 additive schema 變動（如新增 optional 欄位）可在 CHANGELOG 註明「additive schema、無需 migration」、不必標 🚨
    - 偵測實作：`scripts/engine/schema_migration_detector.py:has_schema_migration_marker()`（PR #333）
> **v4.15（Stage F）禁令 #8 Executor rollback 退役**：queue-based orchestrator 從 v4.8 建立後從未產出實際 proposal（cron 0 觸發、queue.json / archive.json 未曾寫入）、v4.67 整層退役。對話內硬化由 `/harden` skill（v4.64+）承擔、驗證邏輯移入 `scripts/ops/lib/hardening.harden_from_dialog()` 的 `_validate_after_execute()`、失敗時 lesson 保留 `soft`、語義與原禁令一致但去掉 queue state machine。
>
> **v4.12（Opus 4.7 全修 Stage C）移除舊禁令 #8「Hit 後置檢查強制」**：lessons schema 降維到 v2.0、`hit_count` 已非欄位、Hit 決策網格從強制退為對話中自然標注（見 humanizer v1.27 / flow-operator v1.41）。

## 資料地圖

**📍 SSoT = `01-data-brain/index.md`**（v4.39 統一）。下表僅為主要檔案摘要、完整載入清單 / 知識儲存分工 / 進化觸發請讀 SSoT。

| 路徑 | 內容 | 何時讀 |
|------|------|--------|
| `CLAUDE.local.md` | 此 repo 品牌身份 + 使用者習慣 | 每次對話自動載入 |
| `01-data-brain/index.md` | **資料地圖 SSoT** — 載入清單 + 知識儲存分工 + 進化觸發 | 產出腳本前必讀、改動資料層前必讀 |
| `data/{operator}/pipeline.json` | 狀態 SSoT（含門檻定義 `_meta.thresholds`） | 任何狀態操作時 |
| `02-skill-factory/` | Skill 定義（按需載入） | 生成腳本時 |
| `docs/contracts/` | Claude × Codex 共享契約（schema + CLI + conventions） | 修改接口前必讀 |
| `docs/contracts/skill-io-schema.md` | Skill 間 IO 契約（v0.1） | 修改任一生成 skill 輸出格式前必讀 |
| `data/{operator}/hardening-archive.json` | `/harden` 對話內硬化成功記錄（source="dialog"）| 稽核硬化歷史時讀 |
| `data/.operators.json` | Per-repo operator registry（v4.38+、blacklist 保護、sync-engine 不覆蓋）| bootstrap 時建、切換 operator 時讀 |

## 操作原則

- 寫入 pipeline.json / lessons.json / todos.json → 透過 `python scripts/ops/video-ops.py`，不手動改 JSON
- 分析/報告/診斷/卡關偵測 → 直接讀 JSON 自己做判斷
- 讀 pipeline.json 時若發現逾期/卡關 → 自然提醒，不需要專門的掃描儀式
- 受保護路徑（CLAUDE.md、.claude/）→ 使用者確認後才寫入；CLAUDE.local.md 不受保護（客戶可自行編輯）
- 每次回覆開頭帶 `✓`（沒有 = context 過載）
- Context > 60% 提醒使用者，同時建議下一句打 `/compact <本次主題 hint>`（主動 compact 勝過被動 autocompact、autocompact 觸發時模型正處於 context rot 最笨狀態）；> 80% 停止複雜操作
- 使用者提到未來要做的事 → 語意判斷寫入 todos.json（v4.39+、透過 `video-ops.py todo add`），回覆「✓ 已捕獲」
- 使用者提到新的品牌事實（數字、案例、策略）→ 問「要更新到數據大腦嗎？」

## Sheets 同步

操作完成後如需同步 → `python scripts/utils/sync-to-sheets.py [type]`
快速查詢 → `python scripts/utils/sheets-direct.py read [分頁]`
