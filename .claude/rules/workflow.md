# 工作流程

> version: 2.35 | last_updated: 2026-06-10
> 精煉版。詳細步驟按需載入 `docs/references/`。

---

## 對話開頭（掃描五項，無則不顯示，不阻塞）

1. **回填到期**：pipeline.json 已上線 + backfill 為空 + backfill_due_date ≤ 今天 → `📊 VID-XXX 上線 N 天，回填到期`
2. **待辦逾期**：`data/{operator}/todos.json` 中 `state=pending` 且 `due` ≤ 今天 → `📋 ⚠️「title」逾期 N 天（T-NNNN）` (v4.39+)
3. **大腦新鮮度**：brand.md 任一 section `last_updated` > 30 天 → `🧠 [section] 已 N 天未更新`
4. **Transcripts 沉澱門檻**（v2.35 短期適配）：冷啟動完成後、`01-data-brain/transcripts/` **新增**計數 ≥ 2 → `📚 觸發批次沉澱`（原 KaiOS ≥5 是持續經營型門檻、30 天客戶累積不到、形同虛設；冷啟動匯入的存量素材不計入、已在冷啟動 7 步流程中盤點過）
5. **Day-30 收尾偵測**（v2.35+）：operator 首支影片 `publish_date` 距今 ≥ 30 天且未跑過收尾 → `🏁 客戶滿 30 天、建議跑驗證收尾`（見 §Day-30 驗證收尾；同一對話只提醒一次）

Kai 忽略就不重複催促（同一對話只提醒一次）。

## 對話期間的進化提案（v2.2 新增、取代固定門檻為主驅動）

**主驅動：對話中即時判斷。** 每當發生以下場景時，Claude 不等任何筆數/天數門檻，直接在對話中提出升級提案：

| 場景 | Claude 動作 |
|------|------------|
| 回填對話結束前 | 判斷本次數據是否揭露新成功模式 / 失敗模式 / 品牌事實 / 禁忌紅線。有就提 diff 給 Kai |
| Kai 語音筆記 / 逐字稿沉澱後 | 判斷是否出現反覆比喻、觀點演化、新隱藏洞察、新口頭禪。有就提 diff |
| Kai 修正訊號（非指令）：「錯了 / 這不對 / 不是這樣 / 不對不對」 | Claude 回覆結尾**強制**追問「這條要沉澱進 lessons 或規則嗎？」—— 不自己判斷、不等門檻。Kai 說要 → 走 `記錯` 流程；說不要 → 放過。根源：Boris 官方 CLAUDE.md「End corrections with: Now update CLAUDE.md so you don't make that mistake again.」|
| 錯誤命令「記錯：XXX」 | 除了記入 lessons（`origin=mistake`、`stage=soft`），額外判斷是否已達可升 `hardened` 的強度 |
| Kai 在對話中說出新品牌事實 | 直接問「要更新到大腦嗎？」+ 提具體 diff（對應 brand.md 第 [N] 節）|
| Kai 要求我跑 humanizer / verifier、連續修到同類 AI pattern 或低分 | 直接提議沉澱（`origin=humanizer` / `verifier`），不等 ≥3 次 |
| Kai 主動提到「這支又被 verifier 打低分」/「humanizer 又改同樣東西」 | 同上、直接提沉澱 |

**提案原則**：
- 每次對話最多提 1-2 個最強的升級，不轟炸
- 提 diff 時具體到 brand.md 第 [N] 節 / lessons 新增條目
- Kai 一句話確認才寫入

**安全網（fallback 門檻、不再是主驅動）**：

| 門檻 | 角色 |
|------|------|
| 回填累計 ≥ 5 筆未審議 | 對話中如 Claude 都沒主動提、到這個數字時強制盤點一次 |
| brand.md 某 section `last_updated` > 30 天 | 對話開頭提醒（已實作於上節） |
| `transcripts/` 冷啟動後新增 ≥ 2 篇 | 觸發批次交叉沉澱（防止對話中一篇一篇看漏整體模式；v2.35 短期適配、原 ≥5 為 KaiOS 持續經營型門檻） |

這三個門檻**只保留為安全網**：正常情況下 Claude 應在對話中先行提出，門檻不會被碰到；若門檻被觸發，代表 Claude 判斷漏了，需要補一次盤點 + 記入 lessons 當作「Claude 漏判」教訓。

**漏判教訓寫入格式**：
- `origin="manual"`
- `pattern` 模板：「Claude 在 N 次對話中未主動提及 X 模式的進化（觸發時 N=...、X=...）」
- `counter_pattern`：「下次觀察到相同訊號時、應於當輪對話內提 diff、不等 fallback 門檻」

---

## 設計原則（Opus 4.7 視角、v2.20+）

> 對應 `docs/references/skill-architecture-principles.md` 三大發現的對話層落地。本節只列**對話 / 流程行為規則**、不重複研究結論。

### 工作模式 X：Lesson 先行、規則為硬化結果

**禁止**：對話中發生 mistake 時、同時寫 soft lesson + 直接寫 CLAUDE.md 禁令 / lint。

**應走**：

```
mistake 發生
  → lessons.add(origin=mistake, stage=soft) 先行
  → 觀察反覆（跨對話 / 跨 VID）
  → counter_pattern 穩定後、Claude 主動提硬化
  → Kai 確認 → /harden
  → 寫 CLAUDE.md 禁令 / lint / brand.md
  → lesson stage = hardened
```

**例外**（fast-track）：Kai 明確說「直接寫禁令、不等反覆」可跳階段。需在 lesson 中標 `source_note: "fast-track / 規則先行"`、且該 lesson 不再 soft、直接寫 hardened。

**反例記憶錨**：L-0012（territory 越界）— 真實處理路徑是「mistake → soft lesson + 同時寫 CLAUDE.md 禁令 #8」、lesson 仍 soft、CI gate 已硬化。這在 4.7 視角下不該再發生（規則層繞過 lesson 層 = 進化迴路斷環）。

**為什麼**：lesson 層不是「規則庫」、是「對話事件流」、價值在記錄反覆證據鏈用以判斷何時升硬化。規則層直接落地 = lesson 層空轉 = 下次同類問題沒有事件流可查。

### 工作模式 Y：警告 → 自動修復 → 通知 → 才是 gate

**規則**：任何對話內 / hook 中的警告類機制、Claude 設計時必走完四階段：

| 階段 | 動作 | 跳過代價 |
|------|------|---------|
| 1. 警告 | 偵測異常、印出 / 標註 | 缺 = 沒人知道有問題 |
| 2. 自動修復 | CLI 嘗試自修、能修就修、不打擾 Kai | 缺 = 警告衰退為被動噪音 |
| 3. 通知 | 修不掉時主動告知 Kai、提供修復選項 | 缺 = Kai 不知該怎麼處理 |
| 4. gate | Kai 明確未動作 → 阻擋新任務 | 缺 = Kai 可忽略、回到衰退 |

**禁止**：跳階段 2/3 直接做階段 1 + 4。Adoption-gate v2.19 屬此情形、是過渡形態、未來應補階段 2/3 後降級。

**新增警告類機制 / hook 時的對話檢查**：Claude 在提案階段必明列四階段的具體實作。缺則先停下問 Kai「階段 2/3 怎麼做」、不直接寫 gate。

**為什麼**：警告型治理（只印不修）已被 Top 3 失敗證明會衰退（metadata-completer / brand-keeper / harden-guide）。Gate 化是治標、不是修復。長期該回到「為什麼自動化失敗」這層追問。

### 工作模式 Z：架構審視時、必批判「上次審視」自己（v2.23+、4.7 mature 視角）

**規則**：每次大型 skill / 規則 / 流程架構審視（不論 4.6 → 4.7 或 4.7 mature）的最後一步、必跑「上次審視結論可能存在的本期慣性」自我批判：

1. **上次審視用什麼框架？**（例：v1.3 vNext 用「失敗模式 → 必要能力 → skill」三段論）
2. **這個框架本身有沒有預設？**（例：「能力一定要 skill 化」是 implicit、未過準則 E/F 退場測試）
3. **跨期慣性是什麼？**（例：4.7 初期慣性 — 「skill-centric thinking」「task 線性 pipeline」「Output Contract 強制 fenced JSON」）

**禁止**：把上次審視結論當作「假定已最優」就停下。架構審視會落入維護者陷阱、永遠在自己的 paradigm 裡優化、看不到 paradigm 本身。

**對應硬化**：`docs/references/skill-architecture-principles.md` v1.4 §第二輪退役預備條款（4.7 mature 視角自我批判 v1.3 三盲點）+ `02-skill-factory/shared-references/skill-design-principles.md` v1.4 §準則 F（4 層退場測試）。

**反例記憶錨**：
- v1.0 vNext 推導用「修現有 skill」lens → 漏判 Discovery 缺口（v1.3 補正）
- v1.2/v1.3 推導用「能力 → skill」implicit 跳 → 把 Orientation/Distillation 不該升 skill 的也升了（v1.4 §第二輪退役預備條款）
- 元教訓：每次「first-principles 推導」其實都帶有當期模型能力的盲點、必下次審視時自我批判

**觸發**：
- 任何「重新設計 skill 架構」「審視 skill 架構」「優化 skill 架構」級別的對話
- 不適用：單一 skill 升版、單檔 lineage 清理、bug fix

**為什麼**：4.7 視角下、4.6 慣性容易看見（「拆細以求穩定」「食譜化」明顯）；但 4.7 自己的初期慣性（升級 skill / 線性 pipeline / 過度形式化）需要 mature 視角才看見。沒這條規則、下次審視會重複「在自己 paradigm 裡優化」、進化迴路斷。

### 工作模式 W：1 個月 metric 驗證原則（v2.30+、對應 v5.87 trace/verifier 0/30 教訓）

**規則**：任何禁令 / 準則 / 契約 / SKILL.md §Output Contract 上線後 1 個月、必看實際 metric。若 metric 為 0 或顯著低於預期、視同**未真實上線**、**追根因到行為層機制**（CLI / hook / schema / SKILL.md 動詞）、**不再加新禁令 / 新準則**作為應對。

**禁止**：對「規則寫了但沒人動」這類採用閉環失敗、用「再加一條禁令」「再寫一條準則」回應。這條路已被 v1.5 PR #348（CLI 強制）+ v5.87 行為層硬化兩輪證明：每次「加規則修規則」是同一陷阱的下一層、不是解。

**檢查節奏**：
- 上線當天記錄目標 metric 與閾值（寫進 CHANGELOG / 對應 SKILL.md 版本歷史）
- 1 個月後跑 `adoption-stats` 或對應 metric CLI、對比閾值
- 不到閾值 → 不加新規則、改追下列三層之一：
  1. **行為層**：SKILL.md 動詞夠不夠硬？「呼叫 / 推薦 / 遵守」是模糊動詞、會被 4.6 慣性退化為「展示 / 建議 / 參考」
  2. **機械層**：CLI / hook / schema 有沒有強制？或強制了但被別的路徑繞過（如 quick-add 不收 --trace）？
  3. **流程層**：Kai 的真實工作流走不走這條路？或這條路根本是 Claude / Kai 預設的、不是 Kai 真實使用的？

**反例記憶錨**：
- v1.5 PR #348（CLI 強制）+ v5.87（SKILL.md 動詞硬化）：trace 0/30 over 30 days、規則寫了 30+ 天、行為仍 0。每升一層規則、下層的「行為退化」就跑到下下層。
- v4.21 owner 分流（原 KaiOS 禁令 #11、quickshot template 未保留；對應原則合併進本檔 §設計原則 Mode Y 警告四階段）：B1-B5 + T1 + M1 警告印出無人動、加 owner 分流是治標、根因在「員工事卡 Kai」這個流程層問題、不是規則層問題。
- v5.87 path coverage 發現：trace 0/61 真實主因是 quick-add path bypass + 大量舊存量繞過 generation skill、不是 §Output Contract 動詞模糊。動詞硬化只覆蓋 path A、是治表的 follow-up。

**與工作模式 X / Y 的關係**：
- 工作模式 X「Lesson 先行」：規則為硬化結果、不該繞過 lesson 層
- 工作模式 Y「警告→自動修復→通知→才是 gate」：警告類 hook 必走完四階段、不能跳到 gate
- **工作模式 W**：規則 / 警告 / 契約上線後 1 個月看真實 metric、0 = 未上線、追行為 / 機械 / 流程三層、不再加規則
- X 管「規則前怎麼累積證據」、Y 管「警告型治理怎麼設計」、**W 管「規則上線後怎麼驗證有效」**

**與工作模式 Y、禁令 #9 的關係**：
- 工作模式 Y「警告 → 自動修復 → 通知 → gate 四階段」（原 KaiOS 禁令 #11、quickshot 未保留、概念合併進本檔 §Mode Y）+ 工作模式 W = 警告類機制必同時有「四階段 + 1 個月 metric 驗證」、缺一不可
- 禁令 #9「skill 不該被新增、應該被識別」+ 工作模式 W = skill 上線後 1 個月若無使用、視同未識別、降級回對話準則 / hook / command（如 Phase 6 第二輪退役對 Orientation / Distillation 的處置）

**為什麼這條不寫進 CLAUDE.md 禁令**：v5.87 commit message 引述 v1.5 補注原文「不再加禁令」— 若把本規則寫成「禁令 #15」、就變成「禁令本身禁止再加禁令」自相矛盾。本規則改寫進 workflow.md §設計原則 Mode W、與 X / Y / Z 同層、是「設計原則 / 對話流程行為規則」、不是禁令、避開矛盾。

---

## 多代理協作（Claude × Codex / sub-agent、v2.32+）

> 本 repo 同時被 Claude Code 與 Codex / sub-agent 協作時的規則。Codex 入口見根目錄 `AGENTS.md`（瘦入口、指回本段 + CLAUDE.md 完整規則）。
> 多數情況 **Claude 是派工方、Codex / sub-agent 是執行方**；本段管「派工 → 收 PR → 驗收」這條鏈。

### 領土邊界

- 明確劃分各 agent 能改的**路徑白名單**；越界由 `territory-lint` CI 硬擋（白名單定義見 `.github/agent-territory.json`，分支前綴對應 territory）。
- 共享路徑（如 `docs/contracts/` 契約檔）**單向輪替**、PR body 標明 owner、不同時雙寫。

> **已知限制（honor-system、刻意不硬化、v2.34 記）**：`territory-lint` 只能靠**分支前綴**判定 territory（本 repo 所有 PR——人類 / Claude / Codex——都同一個 GitHub 帳號開，沒有 bot 帳號可用作者區分）。後果：agent 只要不用 `codex/` 前綴開 PR（如 `fix/x`）就會被 skip、完全繞過 gate。
> 目前**刻意不堵**：單帳號 + agent 由派工 prompt 驅動、實際風險低；依「別預先硬化沒人用的 gate」（本檔 §設計原則 Mode W），先記限制、觀察。
> **補償控制**：① 派工 prompt 一律指定 `codex/<name>` 前綴 ② 驗收方收 PR 必查 merge-base + 變更檔清單（下面 §收 agent 的 PR）。
> **升級觸發**：若真出現一次「agent 用非 `codex/` 前綴繞過領土」事件 → 才升 default-deny（config 加受信任前綴白名單、未知前綴一律 fail）。

### 派任務 prompt 必含

- **base-check**：先取當下 `main` sha、寫進 prompt（讓 agent 從正確 base 切）。
- **明確動作位置**：「改 X 檔第 N 行」/「開新 branch `codex/<name>`」。
  禁寫「修一下 / 處理 / 補一行」這種模糊動詞 —— agent 會自行亂解讀（CLAUDE.md 禁令 #4 精準修改的派工版）。
- **防 resume**：prompt 頂加隨機 `task_seed` + 「DO NOT resume any previous task」+ 全新 branch 名。

### 收 agent 的 PR：第一件事查 merge-base

```
git merge-base <PR> origin/main   # 必須 = 當下 main HEAD
```

不等於 → agent 從舊 base 切出（resume 舊任務）、會重複帶已 merge 的檔 → **先重設 branch 到 main、只留 net-new**、再 review。

### 不信 CI 全綠就好

agent 在隔離 sandbox 跑的「測試通過」未必反映目標環境（如 Windows）；關鍵改動**本地實測**才算數（CLAUDE.md 禁令 #5 改動自驗 + 跨平台教訓）。

---

## Lesson 硬化提議（v2.10+、對應 lessons-schema v2.0、配 P2 hook 化）

> **v2.10 改動**（v1.1 P2 解死角 #2）：lesson-pressure 改 hook 自動掃 + Claude 對話內主動標注 evidence。Claude 不假裝跨會話、改靠 `evidence list` 累積（v2.0 schema 已有的欄位、不破壞「事件流」定位）。
>
> **v2.9 改動**（保留）：移除「Hit 後置檢查強制」+「hit_count ≥ 3 門檻觸發」。schema 降維至 v2.0、Claude 對話中主動判斷何時提議硬化、不靠計數。

### 對話中累積 evidence（v2.10 新增、配 P2 hook）

Claude 在生成腳本 / humanize 等流程中、若**真的**因某條 soft lesson 改寫或避開、**有 VID 上下文時**：

1. 回覆末尾用一句話標出（同 v2.9）：
   > ✓ 本次避開了 L-0023 的破折號殘留模式、L-0017 不適用（主題無關）
2. **同時**Claude **使用 Bash tool 直接執行**（v2.10 新增、v2.30+ 動詞硬化）：
   ```
   video-ops.py lessons add-evidence L-0023 --vid VID-NNN
   ```
   **禁止印命令給 Kai 看再等 Kai 觸發** — 同 v5.87 SKILL.md §Output Contract §1 動詞硬化、適用同樣 4.6 慣性退化、是 evidence 採用率 11.7%（4/34）的根因。
   （此 CLI 已實作、見下方 §evidence 累積 CLI）

evidence 累積到 ≥3 → P2 hook（session-start）下次自動印「💡 L-XXXX 候選硬化（已跨 N 支觸發）」、Claude 看到再驅動 `/harden`。

**為什麼**：Claude 不跨會話、無法主動觀察。靠 evidence list 持久化跨 session、把「跨對話反覆」這個訊號從「Claude 記憶」（不存在）轉成「資料層計數」（可靠）。

### 硬化提議（對話中主動、不靠門檻）

Claude 觀察到**同一條 soft lesson 已反覆出現在多次對話 / 多支腳本、且 counter_pattern 穩定**時、主動提：

```
💡 L-XXXX 建議硬化：
  觀察：<反覆觀察到的模式、具體在哪幾次對話 / VID>
  路徑：<prompt | lint | test | brand>
  差異：<軟規則 → 硬規則的執行力差>
  要不要升？
```

Kai 說「升」→ 走 `/harden`（v4.64+、見 `02-skill-factory/harden/SKILL.md` v1.2）→ Claude 當場寫對應 test / lint / CLAUDE.md 禁令 / workflow.md 規則 / brand.md diff → 成功後 `stage = "hardened"`。

### 硬化路徑（不變）

| Lesson 類型 | 建議路徑 |
|------------|---------|
| 程式邏輯錯誤（hardcoded、schema 違反）| 生成 `tests/test_xxx.py` 或 `scripts/lint/rules-lint.py` 新規則 |
| 對話行為（提 diff 時機、禁忌邊界）| 寫進 `CLAUDE.md` 禁令 或 `.claude/rules/workflow.md` 段落 |
| 品牌知識（競品、禁止點名）| 寫進 `01-data-brain/brand.md` 對應 section |
| 一次性偶發 | `stage = "archived"`、保留為歷史 |

### evidence 累積 CLI（v2.10 配套）

P2 hook 化的 evidence 累積 CLI 已上線（驗證：`python scripts/ops/video-ops.py lessons --help` 列出子命令 `<list|add|add-evidence|stats|propose-hardening|archive>`）：

```
video-ops.py lessons add-evidence L-XXXX --vid VID-NNN
  - 找 L-XXXX、若 VID-NNN 不在 evidence list 則 append
  - 若已存在、no-op + exit 0
  - 找不到 lesson → exit 1
```

Claude 對話中觸發 lesson 時直接呼叫此 CLI、單行完事。

### Context 健康
- Kai 切換任務類型（如：寫腳本 → 系統維護 → 回填數據）時，建議「開新對話再做，context 更乾淨」
- 腳本生成不滿意 → 建議 Kai 用 rewind（Esc Esc）倒回重來，而非在舊 context 上追加修正

---

## Orientation（v2.25+、第二輪退役 follow-up）

> **規則層、不是 skill**。第二輪退役（v5.67、4.7 mature 視角）已判：規則層 + workflow.md + brain-loading.md 整合足夠、SKILL.md 退為 stub redirect 至本段。
>
> 對應 `docs/references/skill-architecture-principles.md` v1.6 §第二輪退役執行、合併 v1.0/v1.1 「Context Contract」研究結論（決定併入 Orientation、不獨立成 skill）。`02-skill-factory/orientation/SKILL.md` v2.0 為 stub redirect。

### 觸發

每個**新 task 開始時**。定義：
- Kai 給 instruction（不是同一 task 內細節澄清）
- 不適用：純資訊問題（「main HEAD？」）、純打字確認（「好」/「OK」）、跟前一 task 同 scope 的後續

### Claude 必須做：第一個回覆頂部宣告 Task Contract

**自然語言、~100 字、6 元素中的 5 必含 + 1 條件觸發**：

| # | 元素 | 強度 | 內容 |
|---|------|------|------|
| 1 | task_intent | 必含 | 一句話、要做什麼 |
| 2 | scope | 必含 | 動什麼（can_modify）/ 不動什麼（cannot_modify）/ 跨系統 flag |
| 3 | context | 必含 | auto-injected（hook 注入但本 task 用不用）/ on_demand（將讀）/ skipped（標 anti-hallucination）|
| 4 | verification | 必含 | machine（lint/test/CI）+ human（Kai 必判斷的點）|
| 5 | active_rules | 必含 | task-extra only（紅線禁令 #1/#4/#8 always-active、不重複）|
| 6 | evolution_signals | **條件觸發** | 只當真有「規則缺口 / 新事實 / 反覆 lesson」訊號才寫；多數 task 完全省略 |

**範例**（取 P2 hook 實作 task）：
```
✓ Context: P2 hook 化 lesson-pressure 實作
  動: .claude/hooks/session-start.sh + workflow.md + CHANGELOG
  禁: 其他 .claude/* (Kai 未授權)
  讀: brain-loading.md、lessons.json schema (on-demand)；brand.md (auto, 跳過、與任務無關)
  active: 工作模式 Y hook 四階段
  驗: rules-lint + engine-version-check + bash -n + 本地 hook 跑、Kai merge PR
```

### 三層強度（Claude 自決、不問 Kai）

| 層級 | 任務型態 | Contract 寫法 |
|------|---------|--------------|
| **Micro** (≤30 字) | 純讀 / 純查 / 一句話確認 | `✓ 純讀取、無動作` 或省略 |
| **Standard** (~100 字) | 單 PR / 單 branch / 6 元素聲明 | 上面範例格式 |
| **Plan** (detailed) | 多檔連動 / 跨領土 / 不可逆 / 「全修」 | 觸發 CLAUDE.md 禁令 #3.5 Plan mode + 詳細 contract |

### Claude 絕對不可做

- ❌ 跳過 contract 直接動工（除非是 Micro 層級的純查）
- ❌ 把 always-active 紅線（#1/#4/#8）列進 active_rules（屬噪音）
- ❌ 強迫每 task 寫 evolution_signals（沒訊號就省略）
- ❌ 寫成 YAML / 表格（必自然語言一句話、≤100 字）
- ❌ 把 Plan 級 contract 視為 Kai 必確認（除非禁令 #3.5 觸發）

### 自我進化（與 P2 lesson-pressure 咬合）

每個 Standard / Plan task 結束時、Claude 內部對比：

```
contract.verification (預測) vs 實際 (執行)
contract.scope (預測) vs 實際 (動到)
contract.active_rules (預測) vs 實際 (觸發 / 被 Kai 修正)
```

漏判處 → 候選 evidence、走 `video-ops.py lessons add-evidence L-XXXX --vid VID-NNN`（v2.10+ §對話中累積 evidence 已規範）。

### 與其他規則的接口

| 規則 | 接口 |
|------|------|
| CLAUDE.md 禁令 #3 / #3.5 | Plan 級 contract 觸發 Plan mode、不取代 |
| CLAUDE.md 禁令 #8 / #9 | 對應 active_rules 內列 |
| brain-loading.md | context.auto + context.on_demand 包含其載入清單 |

### 退役後再評估

第二輪退役後 SKILL.md v2.0 為 stub redirect 至本段。若日後觀察到以下情況、重新評估是否升回 SKILL.md 主體：
- 規則太長（workflow.md §Orientation > 200 行）— 需拆檔
- 三層強度判斷不穩、需 LLM 推理框架
- 跨系統接口（Obsidian / Mode S 等）需 hook point 規格

重升級觸發：Kai 確認 + 跑準則 F 4 層退場測試 + 過 CLAUDE.md 禁令 #8「skill 成立 10 條件」。

---

## Distillation（v2.25+、第二輪退役 follow-up）

> **規則層、不是 skill**。三 phase 拆三層：collect-evidence 進對話準則、propose 進 session-start hook（lesson-pressure）、harden 進 `/harden` command。
>
> 對應 `02-skill-factory/distillation/SKILL.md` v2.0 stub redirect 至本段、`docs/references/skill-architecture-principles.md` v1.6 §第二輪退役執行。

### 三 phase 拆三層

| Phase | 觸發模型 | 落點 |
|-------|---------|------|
| **collect-evidence**（被動累積）| 對話中、任何 task 內 | 本檔 §Lesson 硬化提議 §對話中累積 evidence + §對話期間的進化提案 |
| **propose**（提硬化候選）| session-start hook 自動掃 + 對話中 Claude 主動提 | `.claude/hooks/session-start.sh` lesson-pressure 區段 + 本檔 §Lesson 硬化提議 §硬化提議 |
| **harden**（規則沉澱）| Kai 顯式呼叫 | `.claude/commands/harden.md` + `02-skill-factory/harden/SKILL.md` |

### 為什麼拆三層

三個 phase 觸發模型完全不同（被動累積 / 跨 session 偵測 / 顯式 command）、塞同一 skill = 「skill-as-folder」非「skill-as-capability」、違反準則 F。第二輪退役（v5.67、4.7 mature 視角）正視此事、回歸三層各司其職。

### 退役後再評估

若日後觀察到三 phase 接口需重新整合（跨 phase 狀態同步 / hook + command 無法滿足）、考慮升回 SKILL.md 主體。觸發條件同 §Orientation 退役後再評估。

---


## 冷啟動萃取（短期客戶 template 原創、v1.0+）

> **為什麼**：KaiOS 主引擎的「語音筆記」流程 + 對話期間進化提案 = **持續經營型**（已有客戶、每週新 transcripts 進來、被動觀察 1-2 個就提）。短期客戶（≤30 天驗證型）是**冷啟動**：第一次就要從 0 到 [2.5] 主彈藥備齊、不能等「累積 5 篇 transcripts 觸發批次沉澱」、太慢。
>
> 本工作流是 quickshot 原創、無 KaiOS 對應、需 1 個月內看真實採用率（per workflow.md §設計原則 Mode W）。

### 觸發

| 場景 | 觸發詞 / 訊號 |
|------|--------------|
| Kai 主動丟一批歷史素材 | `冷啟動：[音檔 / 文章 / 連結]`（≥2 個素材視同冷啟動）|
| 對話開頭 Claude 偵測 | brand.md [2.5] §個人經歷 / §行業誤會 / §圈內事 任一**完全空白**、且這是首次對話 → Claude 主動問「你有過往訪談 / podcast / 文章嗎？」|
| Kai 抗拒冷啟動填表 | Kai 說「我不知道從哪講起」「太多了不知道挑哪些」→ Claude 切冷啟動：「給我你最近的素材、我先萃取候選、你選」|

### 7 步流程

```
1. Claude: 「你有過往訪談 / podcast / 文章 / 語音嗎？貼給我或丟連結。3-10 篇就夠」
2. Kai 丟 N 篇歷史素材(音檔 / 文字 / URL)
3. Claude 一次轉譯:
   - 音檔 → python scripts/utils/transcribe.py
   - 文章 → 直接 Read
   - URL → 提醒 Kai 抓下來貼(不主動爬)
4. Claude 全存進 01-data-brain/transcripts/YYYY-MM-DD_主題.md
5. Claude 跨多篇盤點、出候選清單(不是 diff、是「我看到這 N 個候選、你選哪 X 個進大腦」):
   - 反覆比喻 / 口頭禪 → [3] §高頻詞彙 候選
   - 反覆論點 → [4] §商業洞察 候選
   - 反覆故事 → [2.5] §個人經歷 / 故事 候選
   - 反覆「外人以為 X、其實是 Y」→ [2.5] §行業誤會 候選
   - 反覆「圈內人才知道」→ [2.5] §圈內事 候選
   - 反覆數字 / 案例 → cases.md / [9] §可複用數字 候選
6. Kai 對候選清單標 ✅(採用)/ ⚠(修改後用)/ ❌(不用)三色
7. Claude 寫入對應 brand.md section、附 Hook 適用 + 可拍嗎 兩 tag(per [2.5] template)
```

### 與 KaiOS 元件的差別

| 維度 | KaiOS「語音筆記」流程 | quickshot「冷啟動」流程 |
|------|---------------------|----------------------|
| 觸發頻率 | 高頻、持續經營(每週數次)| 一次性、客戶 onboarding |
| 一次處理量 | 1 篇 transcript | 3-10 篇歷史素材 |
| Claude 提案模式 | 看到就提 1-2 個 diff | 跨多篇盤點、出 12-15 個候選清單 |
| Kai 動作 | 一句話確認 | 三色標記、批次寫入 |
| 終態 | brand.md 增量更新 | [2.5] 主彈藥備齊、能開拍 |

### 候選清單呈現格式

```
✓ 已轉譯 N 篇進 01-data-brain/transcripts/
✓ 跨篇盤點完成、出 X 個候選:

[2.5] §個人經歷 候選(M 條):
1. (摘要 1 句)— 出自 transcript A / C
2. (摘要 1 句)— 出自 transcript B
...

[2.5] §行業誤會 候選(M 條):
1. 外人以為 X / 實際是 Y — 出自 transcript C
...

[2.5] §圈內事 候選(M 條):
1. (摘要 1 句)— 出自 transcript D
...

[3] §高頻詞彙 候選(M 個):
1.「XXX」(在 transcript A/B/C 反覆出現)
...

請對每條標 ✅ / ⚠ / ❌、⚠ 的話補一句改寫方向。
```

### Claude 絕對不可做

- ❌ 跳過 Kai 確認直接寫進 brand.md(違反 CLAUDE.md 禁令 #2)
- ❌ 對 ≤2 篇素材跑冷啟動(資料量太少、會幻覺)
- ❌ 一次寫入 ≥ 10 條候選(Kai 認知負荷爆、品質會降)
- ❌ 把候選清單藏在長篇分析中(Kai 找不到要標的地方)

### 自我進化(per Mode W)

每跑一次冷啟動後、Claude 內部對比:

```
Claude 萃取的候選 vs Kai 標 ✅ 採用的比例
```

採用率 < 30% → 表示候選品質低、下次冷啟動前先讀 lessons.json `origin=cold-start-rejected` 看歷次被 Kai 否決的模式、調整萃取啟發法。

1 個月後跑 metric:冷啟動觸發次數 / 完成率 / 平均 [2.5] section 填寫完成度。0 = 規則未真實上線、追行為 / 機械 / 流程三層、不再加新規則。

---

## Day-30 驗證收尾（短期客戶 template 原創、v2.35+）

> **為什麼**：quickshot 定位是「≤30 天驗證型」、系統的終極 output 不是腳本、是**驗證結論**——這客戶值不值得續、數據說了什麼。沒有收尾流程、30 天結束時只有散落的回填數據、沒有可交付的結論。本節是生產迴圈的終點、與「冷啟動萃取」（起點）成對。
> 全部復用既有 CLI、不新增機器。1 個月內看真實採用率（per §設計原則 Mode W、metric 與凍結規則見 CHANGELOG 2026-06-10 entry）。

### 觸發

- Kai 說「收尾」/「驗證結論」/「客戶結束」
- 或對話開頭掃描第 5 項偵測到滿 30 天（見 §對話開頭）

### 流程（復用既有 CLI）

1. **數據盤點**：`pipeline-stats` + `analyze-deviations` + `lessons stats` + 讀 `performance-patterns.json`
2. **產出一頁驗證結論**（對話中先展示、Kai 確認後才存檔、CLAUDE.md 禁令 #2）：
   - 產出量：N 支腳本 / M 支上線 / 回填率
   - 表現：win patterns（哪類 hook / 題材有效）、失敗模式、與 brand.md 假設的偏差
   - **續約判斷建議**：續（理由 + 下一步）/ 不續（理由）/ 數據不足（缺什麼、需再幾天）
   - 若建議續約 → 附升級 KaiOS 交接清單（brand.md、lessons、performance-patterns、pipeline 帶走；治理機器原地復用）
3. **強制總沉澱一次**：transcripts + lessons + 回填洞察總盤點（取代持續經營型的節奏式沉澱、這是短期客戶唯一一次全量盤點）
4. **終態分流**：客戶結束 → `wipe-client`（見 `docs/references/wipe-client-sop.md`）；續約 → 交接清單執行

### Claude 絕對不可做

- ❌ 用不完整數據硬給「續 / 不續」結論（回填率 < 50% 必標「數據不足」、列缺口）
- ❌ 跳過 Kai 確認直接把結論存檔或外發
- ❌ 收尾報告寫成長篇分析（一頁、Kai 能直接轉述給客戶的密度）

---


## 生產線

### 完整路線

靈感 → 選題 → 腳本生成 → 品質處理 → 存檔 → 拍攝 → 上線 → 回填

| 階段 | 觸發 | 核心動作 | 詳細步驟 |
|------|------|---------|---------|
| ① 靈感 | `丟靈感：XXX` | `add-idea`，Claude 判斷 shelf-life | — |
| ② 確認要拍 | `確認要拍：XXX` | confirm → 大腦 → 標題 → Skill → 品質 | `docs/references/production-details.md` |
| ③ 存檔 | `存檔` | `video-ops.py save` + verifier-scores | 同上 |
| ④ 上線 | `上線：VID-NNN` | 狀態改已上線 + 腳本移 03-done/ | — |
| ⑤ 回填 | Kai 提供截圖 | 讀數字 → Kai 確認 → backfill → 洞察 | `docs/references/production-details.md` |

### 快拍路線

`補登：XXXX` → Claude **強制依序問**：
  1. 階段（剪輯中 / 已上線）
  2. `hook_type`（B1/B2/B3/D1/D2/D3/D4/D5；不知道可選 `skip`）

→ `video-ops.py quick-add --topic X --tag Y --title Z --initial-status [狀態] [--hook-type CODE]`

**規則（v2.17+、Wave 1 止血）**：
- `hook_type` 一定要問、Kai 不知道才 skip；不要自己猜測代號代寫入。
- CLI 端 `--hook-type` 為可選（向後相容），**但 Claude 這層強制**——跳過會造成 performance-patterns 無法算 win_rate。
- 背景：2026-04-24 probe 顯示 38 支已上線中 28 支缺 hook_type、阻塞 sedimentation。

### 回填 hook_type（Wave 2、存量補齊）

當 Kai 說「補 hook_type」或 Claude 偵測存量仍有缺時：

1. **列出缺的 VID**（讀 pipeline.json、過濾 `status=已上線` 且無 `hook_type`、按 publish_date 由舊到新）
2. **逐支問 Kai**：顯示 VID + 標題 + 主題、等 Kai 回 hook_type 代號（B1/B2/B3/D1/D2/D3/D4/D5）或 `skip`
3. **寫入**：`video-ops.py set-hook-type VID-NNN --hook-type CODE`（v2.18+ 新 CLI）
4. **可中斷**：Kai 中途說「先停」Claude 停下、下次回來接著做

**規則**：
- 一次最多做 5 支（避免對話疲勞）、做完問要不要繼續
- 代號 Kai 真的不記得 → 列 B1-B3/D1-D5 定義提示（不要擅自猜）
- 寫入後不做其他副作用（不動 status / publish_date / 其他欄位）

### 多步流程追蹤

進入完整路線（`確認要拍` 10 步、`回填` 含洞察分析、`掃描 全修` 等）時，Claude 建立 TodoWrite 追蹤每一步。Kai 隨時看進度、Claude 不跳步。單步快速動作（`丟靈感`、`看待辦`、`同步`）不用。

---

## 常用指令

| 輸入 | 動作 |
|------|------|
| `丟靈感：XXX` | add-idea 進靈感箱 |
| `確認要拍：XXX` | 完整路線 ②→⑩ |
| `存檔` | save + verifier |
| `補登：XXX` | quick-shot 路線 |
| `上線：VID-NNN` | 狀態改已上線 |
| `看靈感箱` / `i` | 列出靈感 |
| `看影片清單` / `q` | 列出影片 |
| `看待辦` / `t` | **v4.39+**：讀 `data/{operator}/todos.json` 過濾 `state in (pending, in_progress)`、按 priority + due 排序 |
| `待辦：XXX` | **v4.39+**：呼叫 `video-ops.py todo add --title "XXX"`、自動給 `T-NNNN` id + state=pending（schema 見 `docs/contracts/todos-schema.md`）|
| `關閉 T-XXXX` / `完成 T-XXXX` | **v4.39+**：Claude 詢問 closed_reason、呼叫 `video-ops.py todo close T-XXXX --reason "..."` |
| `擱置 T-XXXX` | **v4.39+**：`video-ops.py todo archive T-XXXX --reason "..."` |
| `標題：XXX` | quality skill template + `02-skill-factory/shared-references/title-rules.md` v1.0+ |
| `金句：XXX` | quality skill template + `02-skill-factory/shared-references/templates/hook-templates.md` v1.0+ |
| `驗證：[腳本]` | quality skill phase=check（5 項驗證）|
| `語音筆記` | 附音檔 → 自動分流（→ `production-details.md`） |
| `複製贏家：VID-NNN` | 高表現公式複製（→ `production-details.md`） |
| `看漏斗` | pipeline-stats |
| `記錯：XXX` | 錯誤記憶（→ `system-maintenance.md`）→ 寫入 `data/{operator}/lessons.json`（origin=`mistake`） |
| `看偏差` | analyze-deviations |
| `看 lessons` / `lessons 統計` | `video-ops.py lessons stats`（按 stage 分組：soft / hardened / archived）|
| `提硬化` | `video-ops.py lessons propose-hardening`（列 soft + 有 counter_pattern 的候選、v4.63+ 不靠 hit_count 門檻）|
| `掃描` / `/scan` | 責任區掃描 |
| `/harden` / `升 L-XXXX 為 <path>` / `硬化 L-XXXX` | **v4.64+**：對話內一站式硬化（見 `02-skill-factory/harden/SKILL.md` v1.2）— soft lesson → test / lint / CLAUDE.md 禁令 / workflow.md 規則 / brand.md section。當場寫 artifact + validator + 升 stage=hardened |
| `/init` / `新客戶開始` / `onboarding` | 新客戶 day-1 一站式 bootstrap（見 `.claude/commands/init.md`）— 5 步：品牌名 / operator / persona / brand.md MVP / 歷史素材冷啟動 |
| `/check` / `健康度` | 大腦健康度單行可視化（見 `.claude/commands/check.md`）— 跑 `video-ops.py health`、列各 dimension 原始數字（brand MVP/cases/personas/operators/pipeline/lessons/todos/patterns/transcripts）、不算 overall score |
| `同步全部` | sync-to-sheets all |
| `填大腦` | 載入填充引導手冊 |

---

## 關鍵規則

### 腳本格式

```
> 影片碼：VID-NNN
> 生成日期：YYYY-MM-DD
> Skill：[名稱]
> 封面標題：[標題]
> 來源靈感：[原始靈感]
```

檔名：`YYYY-MM-DD_主題關鍵字_腳本_V版本.md`

### 選題去重

生成前跑 `list-topics`。重疊 → 禁止推薦。cooldown → 標註。最近 5 支同類 ≥ 3 → 提醒換類型（不阻塞）。

### 版本連動

Skill 升版 / 新建 / 規則更新 → 一次改完所有關聯副本（SKILL.md + stub + README + CHANGELOG）。詳見 `docs/references/system-maintenance.md`。
