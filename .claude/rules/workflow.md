# 工作流程

> version: 2.31 | last_updated: 2026-05-15
> 精煉版。詳細步驟按需載入 `docs/references/`。

---

## 對話開頭（掃描五項，無則不顯示，不阻塞）

1. **回填到期**：pipeline.json 已上線 + backfill 為空 + backfill_due_date ≤ 今天 → `📊 VID-XXX 上線 N 天，回填到期`
2. **待辦逾期**：`data/[operator]/todos.json` 中 `state=pending` 且 `due` ≤ 今天 → `📋 ⚠️「title」逾期 N 天（T-NNNN）` (v4.39+)
3. **大腦新鮮度**：brand.md 任一 section `last_updated` > 30 天 → `🧠 [section] 已 N 天未更新`
4. **Transcripts 沉澱門檻**（v2.5+）：`01-data-brain/transcripts/` 計數 ≥ 5 → `📚 觸發批次沉澱`；3-4 篇顯示距離門檻
5. **Engine lag**（v2.7+、對應 v4.58 sync-engine v2）：engine remote 有新版 → `🔄 engine 落後 v{local} → v{remote}（說「同步」拉）`；engine remote 未設 silent skip

Kai 忽略就不重複催促（同一對話只提醒一次）。

## Adoption-gate（v2.19+、v2.24 加 owner 分流、對應 CLAUDE.md 禁令 #9 + #11）

> **為什麼**：過去 Top 3（metadata-completer / brand-keeper / harden-guide）都失敗於「工具建得比用得快、警告印了沒人動」。hook 每 session 印 5+ 警告、Claude 看完直接進下個任務、同一批警告累積數週。v2.19 把 warning 升級為 **action gate**。**v2.24（Phase 6 落地、配 Codex `adoption_gate.py`）加 owner 分流** — 把員工 / Kai / 自動三類分開、避免 Kai 被員工事卡住。

### 觸發

`.claude/hooks/session-start.sh` 印出「⏰ 對話開頭檢查」區段時、**依 owner 分組**：

```
⏰ 對話開頭檢查

[員工待辦]（資訊、不擋）
  📊 VID-NNN 回填到期 ...
  📋 待辦逾期 ...
  🧠 brand.md N sections 過期 ...

[Kai 決策]（待你回覆）
  [T1] ...
  [E1] ...

─── Adoption gate ───
N 項需決定（員工類不算）
```

### Owner 分流規範（v2.24）

每個 hook 項目有 `owner` 欄位（per `scripts/utils/lib/adoption_gate.py`）、決定行為：

| owner | 例子 | 行為 |
|-------|------|------|
| `kai` | 架構決策 / 跨領土授權 / 引擎落差 / IG vs pipeline 對表 | **入 adoption gate**、擋新任務、Kai 必回覆 |
| `employee` | 回填截圖（B1-B5）/ 員工待辦（部分 T*）/ brand 過期等待新事實（M1+） | **純 info-only**、印但不入 gate、Kai 可忽略 |
| `auto` | 系統可自修（todo auto-close 已回填的 related_vid / transcripts 沉澱觸發）| **stage 2 自動處理**、成功不印、失敗才升 employee |

**判定邏輯**：在 `adoption_gate.py:build_items()`、每個 GateItem 構造時指定 owner。Codex 領土維護、Claude 文件層對齊。

### Claude 必須做

進 **任何新任務** 前、**只看 Kai 決策類項目**（owner=kai）的 Kai 回覆。員工類項目不參與 gate 計數。合法回覆 4 種（針對 Kai 類）：

| Kai 說 | Claude 動作 |
|-------|------------|
| `處理 <codes>`（例：`處理 T1,E1`） | 依序驅動執行（todo 問關閉原因、引擎落差跑 /sync）、完成一項劃掉一項、失敗停下報告 |
| `defer <codes> until YYYY-MM-DD` | 呼叫 `video-ops.py todo add --title "defer: {原 warning}" --due YYYY-MM-DD`、該日前不再於 hook 顯示 |
| `defer all until YYYY-MM-DD` | 上述對所有 gated code 批次執行 |
| `skip adoption gate` | 本輪 session bypass、但**自動記 lesson**（origin=mistake、pattern="Kai 要求 skip adoption gate、觀察過度 skip 模式"）—— 偶爾 OK、連續 3 次會 surface |

**員工類項目（owner=employee）的處理**：
- Kai 不需回覆、純資訊呈現
- 若 Kai 主動說「處理 B1」、Claude 仍可驅動（手動觸發、不入 gate 計數）
- 員工類項目逾期時間長、Claude 可主動提「這幾項員工任務累積 N 週、要 ping 員工嗎？」（升級討論、不擋）

### Claude 絕對不可做

- ❌ 看到 Kai 決策類項目後、不等 Kai 回覆就動新任務
- ❌ 把員工類項目當 Kai 必處理（這是 v2.24 之前的錯）
- ❌ 自行判斷「Kai 應該會 skip」然後跳過
- ❌ 把 Adoption gate 當「提示」忽略
- ❌ 每 turn 都重印 gate（hook 只在 session 開頭跑一次、不重複）

### 邊界

- Gate **只擋新任務**、不擋 Kai 的資訊性問題（如「看清單」「查 stat」）
- 員工類項目（owner=employee）不參與 gate、純資訊
- Kai 明確用 `處理 XY` 觸發的動作本身、完成後可直接進 Kai 下一個指令、不需重 gate（gate 一 session 一次）

### 過度 skip 處理

Claude 累積觀察到 3 次以上 `skip adoption gate` → 主動提：「最近 N 次 skip、是否警告本身設計有問題？要不要調整 threshold 或重新分 owner？」升級討論、不是默默放棄。

> 實作於 `.claude/hooks/session-start.sh` + `scripts/utils/lib/adoption_gate.py` + `scripts/utils/adoption_gate_scan.py`（v2.24 / Phase 6 / Codex PR #310 落地）。v2.12：移除舊 step 5 Hardening Queue pending。v2.8：移除舊 step 4 Brand ↔ Summary 漂移。**v2.24（2026-04-26）**：加 owner 分流、解 L-0016（B1-B5/T1/M1 持續 skip 根因）。

---

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
| `transcripts/` 累積 ≥ 5 篇 | 觸發批次交叉沉澱（防止對話中一篇一篇看漏整體模式） |

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
- v4.21 owner 分流（禁令 #11）：B1-B5 + T1 + M1 警告印出無人動、加 owner 分流是治標、根因在「員工事卡 Kai」這個流程層問題、不是規則層問題。
- v5.87 path coverage 發現：trace 0/61 真實主因是 quick-add path bypass + 大量舊存量繞過 generation skill、不是 §Output Contract 動詞模糊。動詞硬化只覆蓋 path A、是治表的 follow-up。

**與工作模式 X / Y 的關係**：
- 工作模式 X「Lesson 先行」：規則為硬化結果、不該繞過 lesson 層
- 工作模式 Y「警告→自動修復→通知→才是 gate」：警告類 hook 必走完四階段、不能跳到 gate
- **工作模式 W**：規則 / 警告 / 契約上線後 1 個月看真實 metric、0 = 未上線、追行為 / 機械 / 流程三層、不再加規則
- X 管「規則前怎麼累積證據」、Y 管「警告型治理怎麼設計」、**W 管「規則上線後怎麼驗證有效」**

**與禁令 #11、#13 的關係**：
- 禁令 #11「警告型 hook 不能單獨上線」+ 工作模式 W = 警告類機制必同時有「四階段 + 1 個月 metric 驗證」、缺一不可
- 禁令 #13「skill 不該被新增、應該被識別」+ 工作模式 W = skill 上線後 1 個月若無使用、視同未識別、降級回對話準則 / hook / command（如 Phase 6 第二輪退役對 Orientation / Distillation 的處置）

**為什麼這條不寫進 CLAUDE.md 禁令**：v5.87 commit message 引述 v1.5 補注原文「不再加禁令」— 若把本規則寫成「禁令 #15」、就變成「禁令本身禁止再加禁令」自相矛盾。本規則改寫進 workflow.md §設計原則 Mode W、與 X / Y / Z 同層、是「設計原則 / 對話流程行為規則」、不是禁令、避開矛盾。

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

### evidence 累積 CLI（v2.10 配套、Codex 已實作）

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
  動: .claude/hooks/session-start.sh + workflow.md + engine-manifest + CHANGELOG
  禁: scripts/ops (Codex 領土)、其他 .claude/* (Kai 未授權)
  讀: brain-loading.md、lessons.json schema (on-demand)；brand.md (auto, 跳過、與任務無關)
  active: 禁令 #11 hook 四階段
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
| CLAUDE.md 禁令 #9（adoption-gate）| gate 在 session 開頭、contract 在 task 開頭、互補 |
| CLAUDE.md 禁令 #10 / #11 | 對應 active_rules 內列 |
| brain-loading.md | context.auto + context.on_demand 包含其載入清單 |

### 退役後再評估

第二輪退役後 SKILL.md v2.0 為 stub redirect 至本段。若日後觀察到以下情況、重新評估是否升回 SKILL.md 主體：
- 規則太長（workflow.md §Orientation > 200 行）— 需拆檔
- 三層強度判斷不穩、需 LLM 推理框架
- 跨系統接口（Obsidian / Mode S 等）需 hook point 規格

重升級觸發：Kai 確認 + 跑準則 F 4 層退場測試 + 過 CLAUDE.md 禁令 #12「skill 成立 10 條件」。

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

## Dispatch（Mode A、v1.0+、對應 `docs/contracts/agent-dispatch.md`）

> Codex CLI 已在本機（PR #397）+ 共享 working tree。Claude 是 Kai 唯一入口、用 `codex exec` 派遣 Codex 跑 worker 任務。完整契約見 `docs/contracts/agent-dispatch.md` v1.1（含 §10 環境前提 + Mode B-plus fallback、網頁版 Claude 必讀）。

### 環境檢測（每 session 第一次 dispatch 前必跑、v1.1+）

```bash
which codex 2>/dev/null && codex --version 2>/dev/null
```

- exit 0 + 有版本 → Mode A 可用、繼續走決策樹
- exit ≠ 0 → **不嘗試 Mode A、改建議 Codex Desktop**（v1.2+）：
  1. Claude 寫完整 prompt（純內容、不含 bash 包裝）
  2. 對話中告訴 Kai：「Mode A 不可用、請開 Codex Desktop / chatgpt.com/codex、確認 repo + branch 後貼以下 prompt」
  3. Kai 在 GUI 操作、Codex 自動開 PR、貼 PR 連結回
  4. Claude 看 PR 合成

典型不可用情境：claude.ai/code 網頁版沙箱（與本機隔離、看不到本機 codex CLI）。
**為什麼 Desktop 優先 over CLI heredoc**：Kai 不用碰 cmd / npm install codex CLI、Codex Desktop 直接讀 GitHub repo + AGENTS.md。實證：2026-05-03 PR #401 用 Desktop 5 分鐘、CLI 路線卡 30 分鐘。

完整 fallback 規範（含 Mode B-plus CLI 備案）見 `docs/contracts/agent-dispatch.md` §10。

### 決策樹（拆 vs 不拆）

```
Kai 給任務
  ↓
有明確兩塊獨立產出？（schema + code / 設計 + 探針 / code-heavy 重構 + 測試）
  ├─ 是 → 拆、Claude 派遣 codex
  └─ 否 → 不拆、Claude 自己做
       └─ 但需要客觀資料？→ Bash 直接撈、不 dispatch（overhead 不值）
```

**紅燈**（不拆、即使有 routing block 也覆蓋）：
- 單一架構判斷 / 反省 / 設計
- 品牌 / 創作判斷（Codex 不讀 `brand.md`）
- skill 設計
- ≤30 字純資訊查

### Claude 派遣 bash template

```bash
codex exec --skip-git-repo-check --output-last-message /tmp/codex-out-<task>.txt "$(cat <<'EOF'
你在 KaiOS-ContentSystem repo、已讀 AGENTS.md。
# Task
<一句話、不歧義>
# Mode
read-only          # or write-readonly-output / write-repo
# PR_BRANCH        # write-repo 時必填：codex/<task-name>
# Output format
## Findings
- ...
# Constraints
- 找不到 → "N/A: <原因>"
- 超出 → STOP + "out-of-scope: <什麼>"
- 違反領土 → STOP
完成後 stdout 結尾固定 `<<DISPATCH_DONE>>`。
EOF
)"
```

### 對話內 audit trail（每次 dispatch 後必印）

```
🤖 dispatched to codex: <task name>
   mode: read-only
   exit: 0
   output: <stdout 摘要 / /tmp 路徑>
```

### 失敗處理

| 失敗 | 動作 |
|------|------|
| exit ≠ 0 | 回報 Kai、不靜默 retry |
| 格式不符 | 重派遣**一次**、明寫「上次格式錯」+ 第二次仍錯 → 回報 Kai |
| timeout（30 分） | 取消 + 回報 Kai |

### 演化觸發

- Kai 連續 3 次手動拆窗（用 Mode B）→ 提案「為什麼沒用 dispatch」分析
- 同 dispatch pattern ≥ 5 次 → 升級成 slash command 或 skill（per CLAUDE.md 禁令 #13）

> 完整契約：`docs/contracts/agent-dispatch.md` v1.2

---

## 平行任務（git worktree、本機 CLI 場景）

> 對應 `docs/references/worktree-guide.md` v1.0。Boris team tip #1：「Run 3–5 Claude sessions at once, single biggest productivity unlock」。

### 何時用

| 情境 | 用 worktree | 不用 |
|------|-----------|------|
| 派遣 Codex 後等 PR 回的 5-30 分鐘空檔 | ✓（Claude 開 worktree 做別的） | — |
| 同時開 3 個獨立 feature（互不依賴） | ✓ | — |
| Codex / Claude 領土同 PR 想分開做 | ✓ | — |
| 單一 task / 修一行 / 純資訊查 | — | ✗（overhead 不值） |
| 網頁版 Claude（沙箱）| — | ✗（沙箱單機、無法 worktree） |

### 常用指令

```bash
# 主目錄：/home/user/KaiOS-ContentSystem
git worktree add ../KaiOS-feat-X -b claude/feat-X origin/main
cd ../KaiOS-feat-X
# ... 工作 / commit / push ...

git worktree list                               # 列現有
git worktree remove ../KaiOS-feat-X            # 移除（保留分支）
```

### Claude 自驅原則

- Kai 給多 task 的指令時、Claude 評估能否平行（依 §Dispatch 決策樹）、能就建議「開 worktree 同時跑」
- 派遣 Codex 後、Claude 主動開 worktree 處理 Claude 領土的事、不空等
- 單一 session 內不切 worktree（避免 context confusion）— 平行需要平行 Claude session、Boris 原則

### 限制（必明示）

- 只在本機 `claude` CLI 可用
- 網頁版 Claude / Codex Desktop 用戶 → 跳過此節、走順序執行
- worktree 數量超過 5 → context 管理成本反而上升、降回順序

詳見 `docs/references/worktree-guide.md` v1.0。

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
| `看待辦` / `t` | **v4.39+**：讀 `data/[operator]/todos.json` 過濾 `state in (pending, in_progress)`、按 priority + due 排序 |
| `待辦：XXX` | **v4.39+**：呼叫 `video-ops.py todo add --title "XXX"`、自動給 `T-NNNN` id + state=pending（schema 見 `docs/contracts/todos-schema.md`）|
| `關閉 T-XXXX` / `完成 T-XXXX` | **v4.39+**：Claude 詢問 closed_reason、呼叫 `video-ops.py todo close T-XXXX --reason "..."` |
| `擱置 T-XXXX` | **v4.39+**：`video-ops.py todo archive T-XXXX --reason "..."` |
| `標題：XXX` | quality skill template + `02-skill-factory/shared-references/title-rules.md` v1.0+ |
| `金句：XXX` | quality skill template + `02-skill-factory/shared-references/templates/hook-templates.md` v1.0+ |
| `驗證：[腳本]` | quality skill phase=check（5 項驗證）|
| `語音筆記` | 附音檔 → 自動分流（→ `production-details.md`） |
| `複製贏家：VID-NNN` | 高表現公式複製（→ `production-details.md`） |
| `週報` | weekly-report |
| `看漏斗` | pipeline-stats |
| `記錯：XXX` | 錯誤記憶（→ `system-maintenance.md`）→ 寫入 `data/[operator]/lessons.json`（origin=`mistake`） |
| `看偏差` | analyze-deviations |
| `看 lessons` / `lessons 統計` | `video-ops.py lessons stats`（按 stage 分組：soft / hardened / archived）|
| `提硬化` | `video-ops.py lessons propose-hardening`（列 soft + 有 counter_pattern 的候選、v4.63+ 不靠 hit_count 門檻）|
| `掃描` / `/scan` | 責任區掃描 |
| `/harden` / `升 L-XXXX 為 <path>` / `硬化 L-XXXX` | **v4.64+**：對話內一站式硬化（見 `02-skill-factory/harden/SKILL.md` v1.2）— soft lesson → test / lint / CLAUDE.md 禁令 / workflow.md 規則 / brand.md section。當場寫 artifact + validator + 升 stage=hardened |
| `/sync` / `/sync-engine` / `同步` | **v4.58+**：sync-engine v2 auto 模式（無人介入、一訊息做完）；子命令 `/sync dry` `/sync pause` `/sync cleanup`、見 `.claude/commands/sync-engine.md` |
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
