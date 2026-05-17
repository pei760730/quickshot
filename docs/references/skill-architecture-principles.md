# Skill 架構原則（Opus 4.7 視角沉澱）

> version: 1.7 | last_updated: 2026-05-05 | author: Claude (Opus 4.7) | scope: KaiOS-ContentSystem 全域

## 本檔角色

把 2026-04-25 那次「Opus 4.7 視角重新審視 Claude Code 區塊 skill 架構」研究的**結構性結論**沉澱成長期可引用的設計原則。

下次新增 / 重設計 skill、改動 hook、調整進化迴路時、必先讀本檔。

---

## 起源

這 repo 的 skill 系統由 Opus 4.6 時期協助設計、後續多輪優化、4.24 開始 Opus 4.7 進入維護。研究發現：模型升級後、若把所有舊設計都當成「該為新模型增強」、會誤把問題複雜化。真正該做的、是先看哪些 4.6 留下的設計慣性現在已不是最優解、再用更少的控制點與更清楚的邊界重組。

研究輸出三大結構性發現、本檔把它們固化為可引用的長期原則。完整研究紀錄留在當時對話。

---

## 三大結構性發現

### 發現 A：採用閉環、不是契約閉環

**症狀**：38 支已上線影片中、`generation_trace` 0/38、`verifier_scores` 0/38、`hook_type` 10/38（26%）。

**第一直覺（錯）**：契約沒寫好、補契約。

**真相**：契約已寫好（`docs/contracts/skill-io-schema.md` v1.4 §Learning Loop Contract、2026-04-24 完成、含完整 JSON schema + Codex Task A/B 規格）。**0/38 的原因不是契約缺、是採用斷層**——skill 產出 markdown 給 Kai 看、但沒有任何 skill 在執行末呼叫對應 CLI 寫入 pipeline.json。

**Opus 4.6 設計慣性**：4.6 時代 skill 的角色被設定為「對話中的腳本生成器」、輸出是 markdown 給人讀。沒人想過 skill 該是「系統函式、有對機器的 IO」。

**4.7 應該怎麼看**：skill = 推理單元 + 機器 IO 雙軌輸出。markdown 給人看、JSON / CLI 呼叫給系統吃。少了後者、整個下游（performance-patterns / win-rate / verifier 預測校準 / lesson 觸發）都建在噪音上。

**對應硬化**：`CLAUDE.md` 禁令 #10「Skill 採用閉環強制」。

---

### 發現 B：lessons 從進化前導退化為事後審計

**症狀**：8 soft / **0 hardened** / 4 archived。`hardening-archive.json` 不存在（只有 template）。L-0012（territory 越界）的真實處理路徑：

```
mistake → soft lesson L-0012  ←─┐
                                  │ 同時、平行
CLAUDE.md 禁令 #8 + territory-lint CI gate  ←─┘
```

lesson 還是 soft、CI gate 已硬化、規則層**繞過** lesson 層直接落地。

**Opus 4.6 設計慣性**：4.6 時代 lesson 是「軟規則預載 → 影響下次生成」。這在 4.6 推理穩定度下有實效——把規則塞進 prompt、模型照做。4.7 推理力提升後、Kai 與設計者開始直接寫 CLAUDE.md 禁令、lesson 層空轉。

**4.7 應該怎麼看**：lesson 不是「規則庫」、是「**對話事件流**」。它的價值是記錄「同一模式跨對話 / 跨 VID 反覆出現的證據鏈」、用來**判斷何時該升硬規則或退場**。預設角色從「下次生成必載」退到「按需查詢、按需提硬化」。

**對應硬化**：`.claude/rules/workflow.md` §設計原則（Opus 4.7 視角）工作模式 X「Lesson 先行、規則為硬化結果」。

---

### 發現 C：警告型治理是治標、不是修復

**症狀**：SessionStart hook 印 5 類警告（B1-B5 回填到期、T1-T5 待辦逾期、M1+ brand 過期、P1 transcripts 沉澱、E1 engine lag）。Top 3 失敗（metadata-completer / brand-keeper / harden-guide）都因「印了沒人動」。v2.19 把 warning 升級為 adoption-gate（強迫 Kai 處理）。

**第一直覺（錯）**：gate 解決了「沒人動」、問題已處理。

**真相**：gate 是減速踏板、不是修復。B1-B5 的根因是「回填無自動化、依賴 Kai 截圖 + Claude OCR + Kai 確認」；M1 的根因是「brand.md 沒有新事實 → 自動 diff 提案迴路」。Gate 強制 Kai 處理、但每次處理仍需要全套人工流程。

**Opus 4.6 設計慣性**：4.6 假設「印給 Claude 看 → Claude 自己會驅動」。失敗後加一層「強迫人類介入」。沒回到「為什麼自動化失敗」這層追問。

**4.7 應該怎麼看**：警告 → 自動修復 → 通知 → gate 是**四階段**。不能跳階段直接做 gate。adoption-gate v2.19 是「階段 1 + 階段 4、缺 2/3」的過渡形態、合理但不該是終點。

**對應硬化**：`CLAUDE.md` 禁令 #11「警告型 hook 不能單獨上線」+ `.claude/rules/workflow.md` 工作模式 Y「警告→自動修復→通知→才是 gate」。

---

## Skill 設計準則（A/B/C/D）

詳細條文 + 操作範例見 `02-skill-factory/shared-references/skill-design-principles.md`。本檔只列摘要、避免雙處維護。

| 準則 | 一句話 | 視角 | 觸發場景 |
|------|--------|------|---------|
| **A. 補洞型 skill 是訊號、不是答案** | 想新增「修 X 沒被填好」的 skill 時、優先反問源頭為何沒填好 | 裁減 | 新增 humanizer / verifier / metadata-completer / harden-guide 類 skill 前 |
| **B. 可推理的事不寫死、可機器算的事不留給人類** | 清單先問「能變 lint 嗎」、能就退到 lint；數據先問「能算嗎」、能算就別問人 | 裁減 | 新增 SKILL.md 含「請依下表選擇 / 必遵守 N 條」時 |
| **C. skill 數量不是智能指標** | 過 CLAUDE.md 禁令 #7 三層自問（lint / rule / schema 都不行才寫 skill） | 裁減 | 任何「我們需要一個新 skill 來…」對話開始時 |
| **D. 新增 skill 的真正槓桿是「能力缺口」、不是「現有問題」**（v1.1+） | 審視時必問「Kai 重複手動做、目前 0 系統支援」的工作有哪些 | **擴張** | 每次架構審視（必跑、配 A/B/C 一起） |

**核心反例（記憶錨）**：
- humanizer + script-verifier 重疊掃 AI 味 = 違反準則 A（兩個補洞 skill 並存、源頭 flow-operator 沒被強化）
- title-generator 10 條「必遵守」原則 = 違反準則 B（可變 lint）
- adoption-gate 整套 = 違反準則 C 的反方向（不該存在的人工強制介入點、應該是自動修復不到才出現）
- topic-architect 0 使用 = 違反準則 D（4.6 假設 Kai 缺選題、4.7 發現 Kai 缺篩選；方向錯不是設計差）

---

## v1.1 補丁：v1.0 留下的結構性死角

> v1.0 用「修現有 skill」的 lens 抓到三大發現、但留了三個結構性死角沒處理。本節補上、不修改 v1.0 三大發現的結論（那部分仍正確）。

### 死角 #1：Adoption Loop 解了寫入端、讀取端還沒接

**v1.0 怎麼說**：P0「採用閉環」+ P1「performance-feedback-loop（回填數據自動回流 patterns）」並列、順序對。

**v1.0 沒回答的**：P0 解的是「skill 跑完 → trace JSON → CLI → pipeline.json（**寫進去**）」。P1 預期解「回填數據 → patterns aggregate → 下次 skill 載入（**讀回來**）」。但**「下次 skill 載入」是什麼意思？**

目前 `performance-injection-protocol.md` 設計是 skill 跑時載入 `performance-patterns.json` 的**全局聚合**（hook 勝率、cta 勝率…）。這是 **4.6 慣性**：LLM 讀統計表、自己推理。

**4.7 視角下、正確的「讀回來」應該是 case-based retrieval**：
- 當前選題：加盟主篩選
- 系統自動撈：上 5 支同類選題的 (hook_type / verifier_score / actual_views / 偏離度)
- skill 推理時直接看到：「上次 D3 hook + B 版在這類題拿 8000 views、但偏離度 0.7、kai 拍時改回 D1」

不是「全局統計」、是「**最像本次的歷史案例**」。4.6 推理力下塞 5 個案例進 prompt 太雜、只能塞統計；4.7 推理力下、5 個原始案例比統計表更有資訊密度。

**該做**：v1.0 的 P1 應重新定義為「**case-based retrieval 機制**——不是統計回流、是案例檢索」。可能不是新 skill、是 `performance-injection-protocol.md` v3.0 的內部機制改寫（從 aggregate → retrieve）。

**不該做**：把 P1 做成新 skill（違反準則 C）、或寫成「自動把所有歷史案例塞進 prompt」（會爆 context）。

**時機**：Adoption Loop 跑 1-2 週、有真實 trace 數據後做。沒數據前先做也是空的。

---

### 死角 #2：lesson-pressure 的資料層矛盾（v1.0 P2 是空話）

**v1.0 怎麼說**：P2「lesson-pressure（Claude 主動觀察跨對話反覆模式、自動提硬化）」、Claude only。

**v1.0 沒回答的**：**Claude 不跨會話。** 每個 session start 都是新 context。「主動觀察跨對話反覆模式」唯一的方式是讀**資料層的累積記錄**。

但 `lessons-schema v2.0` 的核心設計是：
- 拿掉 `hit_count`
- 降維為 soft / hardened / archived 三態
- 定位為「對話事件流、不是規則庫」

要做 lesson-pressure、至少需要：
- `last_triggered_at`
- `trigger_session_ids`
- `trigger_contexts`

**這三個欄位本質上就是 hit_count + evidence chain 的進化版。** v2.0 schema 把它們拿掉、現在 lesson-pressure 又需要它們 → 矛盾。

**v1.0 的盲點**：把 lesson 重定義為「對話事件流」是對的、但**沒同時定義「事件流的聚合視窗」**。事件流如果沒有跨時間聚合、就只是日誌、進化迴路一定空轉。

**該做**：選邊。兩者都不完整：

- **選項 A（建議）**：lesson-pressure **不在 Claude 對話層做**、改 hook 自動跑。每次 session start hook 掃 `lessons.json`、挑出 `triggered_count >= 3` 且 `counter_pattern 穩定` 的、印「💡 L-XXXX 候選硬化」。Claude 看到再驅動 `/harden`。符合準則 C「能用 hook 就不寫成 skill」+ 禁令 #11「警告型 hook 四階段」。
- **選項 B（備案）**：把 `hit_count` / `last_triggered_at` 加回 schema、但**改名**叫「事件流聚合欄位」。語義上區別微妙、但保留 v2.0 「事件流」核心定位。

**不該做**：在 Claude 對話層假裝有 cross-session 觀察能力（v1.0 P2 現狀就是這樣、會持續空轉）。

**時機**：隨時。選 A 方案 1 天可寫完 hook + workflow.md 段落。

---

### 死角 #3：v1.0 自己的盲點 — 只修整現有、沒問「有沒有缺的能力」

**v1.0 怎麼說**：三大發現 + 設計準則 A/B/C + 「不該亂改」清單、**全部是針對「現有 skill 怎麼修」**。

**v1.0 沒回答的**：**4.7 推理力下、「應該存在但目前 0 存在」的 skill 是什麼？**

具體缺口：

| 能力 | 目前狀態 | 4.6 為何沒做 | 4.7 是否該做 |
|------|---------|-------------|-------------|
| **策略層**：Kai 這週該拍什麼？月主題？季方向？ | 0 skill、Kai 自己想 | 4.6 對長期策略推理不穩、不敢做 | 該、`series-engine` 是單一系列、缺月度規劃 |
| **Series-level retrospective**：這 5 支同類影片表現規律是什麼？ | 0 skill、靠 weekly-report 看單支 | 4.6 跨多支推理容易 hallucinate | 該、4.7 能 hold 5+ VID 同時推理 |
| **Hook 失敗反事實**：為什麼 D3 hook 在某類題反覆失敗？ | 0 skill、靠 hook-killer 自我介紹 | 4.6 因果推理弱、只能列模式 | 該、4.7 能做反事實（"如果換 D5、會不會好"） |
| **品牌動向偵測**：競品最近策略變化、紅茶巴士該如何回應？ | 0 skill、`trend-adapter` 拆爆紅 Reels（不是策略層）| 4.6 對外部資訊整合弱 | 該、但需 web 工具支援、目前架構未必 ready |

**v1.0 的 lens** 是「**修現有**」、4.7 視角應該也問「**缺什麼**」。準則 C「skill 數量不是智能指標」是反過度新增的保護、不該變成「永遠不新增」的教條。

**該做**：固化為**準則 D**「新增 skill 的真正槓桿是能力缺口、不是現有問題」（已寫進 `02-skill-factory/shared-references/skill-design-principles.md` v1.1）。每次架構審視必跑準則 D 的四個識別問法。

**不該做**：立刻新增 4 個策略層 skill（會違反自己剛立的準則 C）。**先觀察 Kai 一週工作流**、看哪個缺口最常碰到、再新增 1 個（最有可能是 series-level retrospective、因為回填數據開始累積後、跨支分析需求最自然）。

**時機**：觀察期、不立刻動。配合 P6（見下節）。

---

## v1.2 vNext：4 核心 skill 架構（first-principles 推導）

> 對應 `02-skill-factory/shared-references/skill-design-principles.md` v1.2 準則 E + `CLAUDE.md` 禁令 #12「skill 成立 10 條件」。
>
> **方法**：不從現有 14 個 skill 修補、從本質任務 → 失敗模式 → 必要能力 → skill 推導。

### v1.2.1 Claude Code 的本質任務

> **Claude Code = 把使用者意圖（Kai 講話）轉成「安全、可驗證、可回收、可沉澱」的專案變更（資料 / 腳本 / code / 規則）。**

四個關鍵詞：
- **安全**：不破壞 main / 不越權 / 不污染核心檔
- **可驗證**：每個變更有「怎麼知道做完了」的標準
- **可回收**：失敗能 rollback、不留半途狀態
- **可沉澱**：本次學到的東西回流到規則 / lessons / brand

### v1.2.2 不可接受的失敗模式（F1-F6）

| # | 失敗模式 | 後果 |
|---|---------|------|
| F1 | 讀錯 / 漏讀關鍵 context | 生成虛構內容 / 越界改檔 |
| F2 | 改錯範圍（被叫小改卻動到大檔）| 不可逆破壞 |
| F3 | 越權（branch territory 違反、未授權改 .claude/）| territory 違反 |
| F4 | 一次改太大（不可逆操作未確認）| 失敗難 rollback |
| F5 | 驗證不足 / 假完成 | 後續發現錯、信任崩 |
| F6 | 同錯重複（學到的東西沒回流）| 進化迴路斷 |

### v1.2.3 從失敗模式反推「最小必要能力」

| 能力 | 解哪些失敗 | 是否需 AI 判斷 | 落在哪 |
|------|-----------|--------------|------|
| A. 任務定型 | F2、F4 | 是 | **Orientation Skill** |
| B. 上下文選擇 | F1 | 是 | **Orientation Skill**（與 A 同 phase）|
| C. 變更設計 | F2、F4 | 是 | **Generation Skill** |
| D. 驗證定義 | F5 | 部分是 | **Quality Skill** |
| E. 經驗沉澱 | F6 | 是 | **Distillation Skill** |
| F. 邊界遵守 | F3 | **否**（純規則 + CI gate）| 不是 skill、territory-lint CI 守 |

5 個能力（A+B 合併）→ **4 核心 skill**。

### v1.2.4 vNext 4 核心 skill

```
┌────────────────────────────────────────────────┐
│  Kai 講話（task 開始）                          │
└──────────────────┬─────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────┐
│  1. Orientation Skill                          │
│  - 任務定型（小改 / 中改 / 不可逆）             │
│  - 上下文邊界（讀什麼、跳什麼、紅線）           │
│  - active rules（本 task 哪幾條禁令 active）    │
│  - 預期 verification 標準                       │
│  - 風險層級（micro / standard / plan）          │
│  含 Context Contract 邏輯（不獨立成 skill）     │
└──────────────────┬─────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────┐
│  2. Generation Skill (modes)                   │
│  - mode: dual-track（flow-operator 核心）       │
│  - mode: variant（flow-maximizer）              │
│  - mode: series（series-engine）                │
│  - mode: interview（interview-navigator）       │
│  - mode: viral（viral-knowledge）               │
│  - mode: code-change（系統工程任務）             │
└──────────────────┬─────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────┐
│  3. Quality Skill (phases)                     │
│  - phase: check（5 項驗證、verifier_scores）    │
│  - phase: fix（去 AI 味、品牌人格）             │
│  - templates: hook（17 條 reference）+ title    │
│  - 引用 banned-words / red-line-protocol         │
│  合併 humanizer + script-verifier (quality-loop)│
└──────────────────┬─────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────┐
│  4. Distillation Skill                         │
│  - lesson-pressure 對話端                       │
│  - /harden（規則沉澱、升 stage）                │
│  - brand 更新建議                               │
│  - evidence 累積（add-evidence CLI）             │
└────────────────────────────────────────────────┘
```

### v1.2.5 14 → 4 對應表

| 既有 skill | 落在 vNext | 處置 |
|-----------|-----------|------|
| flow-operator v1.50 | Generation Skill 主體 | 升級為核心 |
| flow-maximizer | Generation Skill mode=variant | 合併 |
| series-engine | Generation Skill mode=series | 合併 |
| interview-navigator | Generation Skill mode=interview | 合併 |
| viral-knowledge | Generation Skill mode=viral | 合併 |
| humanizer | Quality Skill phase=fix | 合併 |
| script-verifier | Quality Skill phase=check | 合併 |
| hook-killer | Quality Skill template | 降級（保留 17 條 reference）|
| title-generator | Quality Skill template + lint | 降級 |
| topic-architect | Filter Skill 或併入 Orientation | 反向重設計（先問 Kai）|
| topic-researcher | tool（research API 包裝）| 降級 |
| trend-adapter | tool（Reels 解析）| 降級 |
| harden | Distillation Skill 主體 | 升級為核心 |
| skill-creator | 官方 MCP、不動 | 封版 |

詳細 map 見 `docs/references/skill-consolidation-map.md`（v1.2 新增）。

### v1.2.6 vNext 落地路徑（4 階段）

| Phase | 內容 | 風險 | 目前進度 |
|-------|------|------|---------|
| **Phase 1** | 規則 + 文件層（準則 E + 禁令 #12 + Orientation Phase 1 + vNext 章節 + consolidation map）| 低 | **本 PR 落地** |
| **Phase 2** | 降級類（hook-killer / title-generator → template；topic-researcher / trend-adapter → tool；topic-architect 反向重設計）| 中 | 待做 |
| **Phase 3** | 合併類 - Generation Skill（5 generation skill → 1 + 5 modes）| 中高 | 待做 |
| **Phase 4** | 合併類 - Quality + Distillation + Orientation Skill 升級 | 中高 | 待做 |

每 Phase 獨立可 merge、有 rollback 路徑。

### v1.2.7 為什麼 Context Contract 不獨立成 skill

| 方案 | 判斷 | 理由 |
|------|------|------|
| A. 獨立 skill | ❌ | 與 Orientation Skill 邊界模糊（task 定型 + context 邊界本質是同一 mental phase）|
| **B. 併入 Orientation**（採用）| ✅ | 同一控制點不該拆兩個 skill；員工只學 1 個 skill |
| C. 降級成 template / rule layer | 部分採用 | active_rules + 6 元素結構 → rule layer（workflow.md §Orientation Phase 1）；contract 內容 → AI 推理 |
| D. 暫時不做 | ❌ | v1.0/v1.1 已點問題、不做 = 接受 context noise |

**結論**：Phase 1 規則化（workflow.md §Orientation）、Phase 4 升級為 Orientation Skill（含 Context Contract 邏輯為 first-phase output）。

---

## v1.3 補丁：vNext 4 → **5** 核心 skill（補 Discovery 漏判）

> v1.2 vNext 寫 4 核心 skill、漏判 **Discovery**（選題發現）這個能力。漏判源頭是準則 D「擴張視角」沒跑徹底——v1.0 死角 #3 已點出「品牌動向偵測缺口」、但被「需 web 工具支援、目前架構未必 ready」輕輕帶過、沒進 vNext 必要能力清單。
>
> 2026-04-25 Kai 主動驅動 topic-architect 工作流確認對話揭露：選題真正瓶頸是 **(a) 想不到題目** + **(c) 不知怎麼切角**、且選題來源 **(b) 同業 / (c) 員工問題 / (d) IG/TikTok 熱門**——**完全是外部觸發 + 內部大腦交互**。這對應 4.6 推理力下不敢做、4.7 能 hold 的「外部資訊整合」能力。
>
> v1.3 補：vNext 從 4 核心改 5 核心、加 Discovery Skill。

### v1.3.1 失敗模式 F7（補 v1.2.2）

| # | 失敗模式 | 後果 |
|---|---------|------|
| **F7**（v1.3 新增）| **靈感被個人視野限制** | 選題長期同類 / 漏掉外部熱點 / 跟不上同業策略變化 |

F1-F6 仍正確、F7 是 4.7 能 hold 但 4.6 不敢做的擴張類失敗模式。

### v1.3.2 必要能力 G（補 v1.2.3）

| 能力 | 解哪些失敗 | 是否需 AI 判斷 | 落在哪 |
|------|-----------|--------------|------|
| **G. 選題發現**（v1.3 新增）| F7 | 是（外部熱點 + 大腦交互、需推理「這個熱點對紅茶巴士有沒有意義」）| **Discovery Skill** |

### v1.3.3 vNext **5** 核心 skill 架構

```
┌────────────────────────────────────────────────┐
│  Kai 講話（task 開始）                          │
└──────────────────┬─────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────┐
│  1. Orientation Skill                          │
│  - 任務定型（小改 / 中改 / 不可逆）             │
│  - 上下文邊界（讀什麼、跳什麼、紅線）           │
│  - 含 Context Contract 邏輯                     │
└──────────────────┬─────────────────────────────┘
                   ↓
       【若 task = 找選題、走 Discovery】
                   ↓
┌────────────────────────────────────────────────┐
│  5. Discovery Skill（v1.3 新增）                │
│  - 整合 web 即時熱點 + brand.md + cases.md      │
│  - 同業監控（brand.md [6]）                     │
│  - 員工 FAQ 萃取（brand.md [12]）               │
│  - IG/TikTok 趨勢 fetch                         │
│  - 輸出 5-10 個選題建議 + 切角 + 信心分數       │
└──────────────────┬─────────────────────────────┘
                   ↓
       【若 task = 拍既有選題、走 Generation】
                   ↓
┌────────────────────────────────────────────────┐
│  2. Generation Skill (modes)                   │
│  - mode: dual-track / variant / series /        │
│    interview / viral / code-change              │
└──────────────────┬─────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────┐
│  3. Quality Skill (phases)                     │
└──────────────────┬─────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────┐
│  4. Distillation Skill                         │
└────────────────────────────────────────────────┘
```

### v1.3.4 Discovery Skill 規格摘要

| 欄位 | 內容 |
|------|------|
| **本質能力** | G 選題發現（外部熱點 + 內部大腦 → 選題建議）|
| **失敗模式** | F7（靈感被個人視野限制）|
| **核心責任** | 整合 web 即時熱點 + brand.md + cases.md + 同業監控 + 員工 FAQ → 5-10 個選題建議 + 角度建議 |
| **Input** | 觸發訊號（"下週要拍什麼" / "這月該做什麼系列" / "競品最近做什麼"）+ brain_loader 載入結果 + web fetch 結果 |
| **Output** | 5-10 個選題建議、每個含：標題草稿 + 切角建議 + 對應 brand.md sections + 來源（同業 / 員工 / 熱門 / 大腦交互）+ 信心分數 |
| **成功條件** | (1) Kai 從推薦中選 ≥1 進入 Generation Skill 拍 (2) 推薦能力跨 task 重用 |
| **不負責** | 內容生成（→ Generation）、品質檢驗（→ Quality）、規則沉澱（→ Distillation）|
| **合併** | **topic-architect 重新定位**（從「萃取 50+ 選題」→「外部 + 內部交互、推薦 5-10 個 + 切角」）|
| **依賴** | brain_loader、web fetch tool（Codex 待實作）、shared-references |
| **modes** | discover-week（週度選題）、discover-month（月主題）、discover-trend（即時熱點響應）|

### v1.3.5 14 → 5 對應表（補正 v1.2.5）

**topic-architect 處置改變**（之前 v1.2.5 寫「反向重設計成 Filter Skill 或併入 Orientation」）：

| Skill | v1.2.5（錯）| v1.3 修正 |
|-------|-----------|----------|
| topic-architect | 反向 Filter / 併入 Orientation | **升級為 Discovery Skill 主體** |

完整 14 → 5 map 見 `docs/references/skill-consolidation-map.md` v1.1。

### v1.3.6 落地路徑調整（補正 v1.2.6）

| Phase | 內容調整 |
|-------|---------|
| Phase 1 | 不變（已完成）|
| Phase 2 | **不動 topic-architect**（從降級類移除）— Phase 2 從 5 動作變 4 動作（hook-killer / title-generator / topic-researcher / trend-adapter） |
| Phase 3 | 不變（Generation Skill 5 modes）|
| Phase 4 | **加 Discovery Skill 建立**（從 topic-architect 升級）+ 既有 Quality + Distillation + Orientation 升級 |

Phase 4 工作量增加（新建 Discovery Skill）、但 topic-architect 既有設計可作起點、不從零寫。

### v1.3.7 為什麼漏判 Discovery（自我檢討）

v1.2 推導時：
1. **失敗模式只列 F1-F6**：聚焦「Claude 執行任務時的失敗」、漏判「Kai 自己工作流的失敗」（F7 屬此類）
2. **必要能力只列 A-F**：5 個能力都是「task 內部能力」、漏判「pre-task 能力」（G 選題發現是 pre-Generation 能力）
3. **準則 D 四問跑了、但結論被 v1.0 死角 #3「需 web 工具、未必 ready」遮蔽**：4.6 慣性的「等工具 ready 才推導能力」、不該影響能力清單建立

**修正方法**：
- F1-F6 + F7 = task 內外失敗模式皆考慮
- A-F + G = task 內部能力 + pre-task 能力皆考慮
- 「需 future tool」≠「能力不存在」、應明標「能力 X、依賴 future tool Y、Phase Z 落地」

### v1.3.8 為什麼 v1.3 而不是 v2.0

v1.2 三大發現 + 4-5 核心 skill 主結構正確、Discovery 是補一個漏判能力、不是改主架構。minor bump（v1.2 → v1.3）合適。

未來若 v1.3 vNext 5 核心被反證（例：Discovery 應併入 Orientation、不獨立）、再考慮 major bump。

---

## v1.4 補丁：第二輪退役預備條款（4.7 mature 視角自我批判）

> v1.3 vNext 5 核心是「4.7 初期 first-principles」推導的結果。Phase 5 落地後（engine v5.42-v5.44）、用 4.7 mature 視角再批判一次、發現 v1.3 自己也有未盡的設計慣性。

### v1.4.1 v1.3 推導本身的盲點（4.7 初期慣性）

| 盲點 | 表現 | 為什麼是 4.7 初期慣性 | mature 視角 |
|------|------|--------------------|-----------|
| **「能力 = skill」這跳沒被檢驗** | 5 個必要能力 → 5 個 skill | 推導路徑「失敗模式 → 必要能力 → skill」第三跳是 implicit、未過準則 E 5 層退場測試 | 該過準則 F（v1.4 新增、shared-references/skill-design-principles.md）4 層退場測試後再決定 |
| **「task 線性 pipeline」假設** | orientation → discovery → generation → quality → distillation 線性圖 | 4.6 怕飄移強分階段；4.7 可同時 hold 多階段 | 階段分離仍有 verification checkpoint 價值、但「線性」可放鬆、特別是 Quality + Distillation 常並行 |
| **Output Contract 強制 fenced JSON** | 每個生成型 skill 末附 JSON block | 4.6 LLM 容易忘 / 寫錯欄位、強制 JSON 是保險 | 合理 trade-off、保留；但要意識到這是顯式選擇、不是「永遠對的」 |

### v1.4.2 vNext 5 核心 skill 的準則 F 重新檢視

依準則 F（4 層退場測試、shared-references/skill-design-principles.md v1.4）：

| Skill | 通過準則 F | 真實層次 |
|-------|----------|---------|
| Discovery | ✅ 通過（外部 fetch + 大腦交互、跨 session 重用、需 AI 推理整合）| skill |
| Generation | ✅ 通過（5 modes、明確 IO、需 AI 判斷）| skill |
| Quality | ✅ 通過（check/fix loop、需 AI 推理灰區）| skill |
| **Orientation** | ⚠️ 通過第 1 層（對話準則即可、workflow.md §Orientation Phase 1 已運作）| 應降回 workflow.md §Orientation |
| **Distillation** | ⚠️ 通過第 1+2+3 層組合（collect 是準則 + propose 是 hook + harden 是 command）| 應拆對話準則 + hook + command 三層、不塞一個 skill |

### v1.4.3 第二輪退役（5 → 3 真 skill）— 預備條款、不立即執行

**目標架構**（觀察期後考慮）：

```
3 真 Skill：
  Discovery / Generation / Quality

2 對話準則（workflow.md）：
  §Orientation     → task contract（3 元素 free-form）
  §Distillation    → task 末對比 + 對話中 evidence 累積

3 Command（.claude/commands/）：
  /harden / /scan / /sync-engine

Tool / Data / Governance 層維持不變
```

**收斂效果**：valid_skills 7 → 3、控制點 30+ → 21、員工只學 3 個 skill 名。

### v1.4.4 為什麼不立即執行第二輪退役

| 理由 | 說明 |
|------|------|
| 剛 Phase 5 完、需消化 | engine v5.42-v5.44 才 merge、5-skill 形態剛跑、再大重組會疲勞 |
| 沒實踐數據驗證 | v1.4 的批判是 mature 視角推理、需 1-2 月實際使用驗證 |
| 違反準則 C 的反向 | 為了「更乾淨」做變動本身違反「不為升級而升級」 |
| Orientation Skill v1.0 + Distillation Skill v1.0 已寫 | 若降級、需配套移除 SKILL.md / 改 entry stub / 改 valid_skills / 改 brain_loader、是大配套 |

### v1.4.5 第二輪退役觸發條件（觀察期數據）

需 1-2 月觀察期、累積以下數據才考慮觸發：

1. **5 個 SKILL.md 的觸發頻率**：哪幾個跑得多？哪幾個 0 使用？
2. **Orientation Phase 1 規則 vs SKILL.md 命中率差**：升 skill 後是否真有改善？
3. **Distillation Skill 跑時實際做了什麼**：跟對話準則 + hook 重複嗎？
4. **員工 / Kai 實際操作中**：5 skill 名是否需要記憶負擔過大？

數據累積後、若 ≥3/4 條件指向「該收斂」、才進入第二輪退役討論。

### v1.4.6 與既有結論的關係

- v1.0 三大發現（採用閉環 / lesson 退化 / 警告型治理）：**仍正確、不變**
- v1.1 三死角：reading loop（Phase 6 P0 解）、lesson-pressure（已 hook 化）、缺能力（Discovery 已補）
- v1.2 vNext 推導框架：**仍正確、不變**（失敗模式 → 必要能力 → skill 邏輯仍對、只是「→ skill」這跳要再加準則 F 過濾）
- v1.3 補 Discovery：**仍正確、不變**

v1.4 不推翻 v1.0-v1.3 結論、只補「準則 F 4 層退場測試」這個過濾層、和「第二輪退役預備條款」這個觀察期框架。

### v1.4.7 為什麼是 v1.4 而不是 v2.0

v1.0-v1.3 的主結構（三大發現 / 必要能力 A-G / 5 核心 skill）仍正確、v1.4 是補一個自我批判機制、不是改主架構。minor bump 合適。

未來若觀察期數據觸發第二輪退役、實際從 5 → 3 收斂、再 bump v2.0。

---

## 不該因模型升級亂改的部分

升 4.7 後**封版**的設計（改動 ROI < 風險）：

| 區塊 | 為什麼封版 |
|------|-----------|
| `flow-operator` v1.50 | 剛完成 466→180 去食譜化、消化中、再動是過度優化 |
| `territory-lint` CI（禁令 #8） | 4.24 才硬化、解決 PR#260/#261 真實傷口、改了會退化 |
| `/harden` skill v1.2 | 結構正確、缺的是觸發信號（lesson-pressure 補）、skill 本身穩 |
| `02-skill-factory/shared-references/` 7 份共用規則 | 低層基礎、改一點漣漪到所有 skill |
| `CLAUDE.md` 禁令 #1 / #3 / #7 | 對話安全紅線、永遠保留 |
| `CLAUDE.local.md` 客戶上下文機制 | 多 repo 多客戶設計關鍵抽象、不該動 |
| `title-generator` v1.14、`hook-killer` v1.14 | 雖有食譜化殘留、但 Kai 已有使用直覺、改動 ROI < 風險 |
| `topic-architect` / `topic-researcher` 區分 | 內外資料來源邊界清楚、無重疊 |

封版的標準：穩定、邊際收益低、改了會增加維護成本、Kai 已有直覺。

---

## 下一步順序（依槓桿排、v1.1 更新）

| 順序 | 動作 | 槓桿 | 領地 | 狀態 |
|------|------|------|------|------|
| **P0** | 採用閉環（skill-io-schema §Learning Loop Contract + 各 SKILL.md §Output Contract） | 解鎖所有下游自動化、發現 A 的根本修復 | Codex + Claude 跨責任區 | ⚠️ **契約層 2026-04-25 完成**（PR #281-#287 cascade、engine 5.32）／**行為層採用率 0/44 trace、16/44 hook_type**（見下節 v1.5 補注、PR #348 補完中）|
| **P1**（v1.1 重定義） | **case-based retrieval**（從 aggregate 改 retrieve、`performance-injection-protocol.md` v3.0）、不是新 skill | 解死角 #1 reading loop、4.7 推理力的正確用法 | Claude（shared-references）| 觀察期、需 1-2 週真實 trace 數據才動 |
| **P2**（v1.1 重設計） | **lesson-pressure 改 hook 化**（session-start hook 自動掃 lessons + 印候選硬化）、不是 Claude 對話層做 | 解死角 #2 cross-session 矛盾 | Claude（.claude/hooks/）| 隨時、1 天可完成 |
| **P3** | humanizer + script-verifier 整併為 quality-loop（單一 skill、單次跑） | 消除補洞 skill 重疊、回頭強化 flow-operator | Claude（02-skill-factory/）| 等 flow-operator v1.50 實戰驗收後 |
| **P4**（v1.1 新增） | **每週跑準則 D 識別問法**（觀察 Kai 重複手動做的事 / 隱性能力缺口） | 解死角 #3、防 v1.0 lens 系統性盲區 | Kai + Claude 對話層 | **持續、每週對話中跑** |
| **P5**（v1.1 新增、條件觸發） | **第一個缺口型 skill（最可能 series-level retrospective）** | P4 觀察到的最高頻缺口 | Claude（02-skill-factory/）| **不立即做**、等 P4 觀察出明確缺口 |

**現在不要碰**：flow-operator / title-generator / hook-killer / shared-references（除 P1 與 P2 涉及的部分）/ territory-lint / /harden。

**v1.1 與 v1.0 的差異**：
- P0 從「待做」變「已完成」（**v1.5 補注**：契約層完成、行為層尚未落地）
- P1 從「自動回流 patterns」重定義為「case-based retrieval」（從 aggregate → retrieve）
- P2 從「Claude 觀察」重設計為「hook 自動掃」
- 新增 P4 / P5 對應準則 D 的「擴張視角」

### v1.5 補注（2026-04-27、4.7 視角再批判）

> **核心發現**：v1.1 把 P0 標「✅ 完成」、其後 v1.2-v1.4 都建立在「P0 已完成」前提上。但 P0 完成的是**契約層**（schema、CLI 接口、SKILL.md §Output Contract 條文）、**不是行為層**（trace 實際被寫入）。

**實際數據**（main HEAD 7e07723、44 支已上線）：
- `generation_trace`: **0 / 44**
- `verifier_scores`: **0 / 44**
- `hook_type`: **16 / 44**（37%）

**意義**：
1. v1.1-v1.4 下游所有推導（P1 case-based retrieval / 第二輪退役 4 條觀察期 metric / performance-patterns 演算法）**全部建在「trace 數據會累積」前提上、前提是錯的、下游推導全部空轉**。
2. 規則層（CLAUDE.md 禁令 #10）+ 文件層（5 SKILL.md §Output Contract 條文）都寫了、Claude 對話中仍然忘記呼叫 CLI = **規則寫了 ≠ 行為改了**。

**補完路徑**（PR #348 進行中）：
- CLI 強制：`video-ops.py save` 在 `_meta.trace_required_statuses` 列名的狀態下、缺 `--trace` 即 `exit 1`
- CLI 工具：`save-with-trace-from-stdin`（從 stdin 抽 fenced JSON block）+ `adoption-stats`（趨勢觀測）
- 配置：`data/template/pipeline.json` + `data/kai/pipeline.json` `_meta.trace_required_statuses` 加上必填狀態

**長期教訓**（建議寫進規則層、不寫進準則）：
> 任何禁令 / 準則 / 契約上線 1 個月後、必看實際 metric。若 metric 為 0、視同未上線、追根因到行為層機制（CLI / hook / schema）、不再加禁令。

**v1.5 視角下、v1.4 「觀察期 1-2 月」設計也違反禁令 #11 四階段**：v1.4 列「4 條觀察期 metric」但沒設計「誰收集 / 自動觸發 / 數據存哪」、是「警告階段 1、缺階段 2-4」的禁令 #11 自身重演。`adoption-stats` CLI（PR #348）是這層的修法 — 把「人工偵測 metric」變成「CLI 一鍵看趨勢」。

**v1.5 與既有結論的關係**：
- v1.0 三大發現（採用閉環 / lesson 退化 / 警告型治理）：仍正確、不變
- v1.1-v1.4 對 P0 的「✅ 完成」錨定錯誤、本節為勘誤、不重寫 v1.1-v1.4 主體
- 不新增準則 G（避免「準則化慣性」）、教訓寫入長期規則層
- 「不要再做 v1.6 研究」：v1.5 之後 3 個月鎖期、累積 trace 數據再評估

---

## 與其他文件的關係

| 文件 | 角色 |
|------|------|
| `CLAUDE.md` | 含本檔派生的禁令 #10、#11（採用閉環、警告型 hook 四階段）|
| `.claude/rules/workflow.md` | 含本檔派生的工作模式 X、Y（lesson 先行、警告→修復→通知→gate）|
| `02-skill-factory/shared-references/skill-design-principles.md` | 本檔提到的準則 A/B/C 完整條文、是 02-skill-factory 內部 SSoT |
| `docs/contracts/skill-io-schema.md` v1.4 | §Learning Loop Contract 是發現 A 的解法規格、Codex Task A/B 待執行 |
| `docs/contracts/lessons-schema.md` v2.3 | lessons 三態（soft/hardened/archived）、發現 B 的資料層基礎 |
| `docs/contracts/agent-collaboration.md` v1.8 | §9.3 責任區 + §9.12 Codex base check、本檔執行 P0 時必依 |

---

## 修改本檔的時機

- 出現新的「Opus 4.X 視角」研究、產生與本檔不一致的結論
- 發現 A/B/C/D 四大發現之一被反證（例：lesson 層在某新機制下重新有效）
- 設計準則 A/B/C/D 在實踐中發現第 5 條值得加入
- 三個結構性死角任一被解、應更新「狀態」欄

不該頻繁修改。本檔是長期錨點、不是工作日誌。

---

## 版本歷史

- **v1.0**（2026-04-25）：三大發現 + 準則 A/B/C + 不該亂改清單 + P0-P3 順序
- **v1.1**（2026-04-25）：補 v1.0 三個結構性死角（reading loop / lesson-pressure 矛盾 / 缺的能力）+ 新增準則 D（擴張視角）+ P0 標記完成 + P1/P2 重定義 + 新增 P4/P5。對應 lesson L-0015（Claude 沉澱層 vs 行動層保守混淆的修正）。
- **v1.2**（2026-04-25）：first-principles 推導 + vNext 4 核心 skill 架構 + 14 → 4 對應表 + 4 Phase 落地路徑。對應 Kai 主動驅動 first-principles skill consolidation 研究 + Phase 1 規則 + 文件層落地（PR #292）。
- **v1.3**（2026-04-25）：補 v1.2 漏判 Discovery（第 5 核心 skill）。F1-F6 加 F7、A-F 加 G、4 核心改 5 核心、topic-architect 處置從「降級 / 反向」改「升級為 Discovery 主體」。對應 Kai 主動驅動 topic-architect 工作流確認對話揭露的 4.6 慣性漏判（「需 web 工具就先不推導能力」）。
- **v1.4**（2026-04-25）：4.7 mature 視角自我批判 — 補 v1.3 三盲點（能力=skill 跳沒檢驗 / task 線性 pipeline 假設 / Output Contract fenced JSON）+ 第二輪退役預備條款（5 → 3 真 skill + 2 對話準則、觀察期 1-2 月後考慮）+ 對齊 skill-design-principles.md v1.4 準則 F（4 層退場測試）。對應 Kai 命「全修」深度分析。
- **v1.6**（2026-04-29）：第二輪退役執行（不等觀察期）+ 元規則「研究退場條件」。配合 PR #367 採用閉環行為層 + Generation/Quality v1.1 即時回饋。對應 Kai 命「再做一輪 4.7 mature 視角研究」、產出反而是「拒絕展開新研究、執行 v1.4 已寫但未動的結論」。
- **v1.7**（2026-05-05、engine v5.87）：補注 §盲點 3 + v1.5 hypothesis 雙證偽記錄。對應 v5.87 generation/quality v1.3 §Output Contract 動詞硬化（移除 fenced JSON 中介層 + 「呼叫 CLI」→「Bash tool 執行」）。本補注**不預測 v1.3 修法成功**、只記錄 v1.4.1 §盲點 3「fenced JSON 合理 trade-off」+ v1.5 hypothesis「CLI 強制 = 行為層解」**已觀察到的失敗**。對應 Kai 命「兩個紅叉全關」、reframe v5.87 commit 末「沒做也沒打算做」立場。

---

## v1.6 補注（2026-04-29、第二輪退役執行 + 元規則「研究退場條件」）

> 觸發：Kai 命「用 4.7 mature 視角再審視 skill 架構」。本輪研究反過來發現：v1.0-v1.5 已 cover 80%+、再展開新研究 = 「在自己的 paradigm 裡優化」、是工作模式 Z 警告的研究慣性本身。改執行 v1.4 §第二輪退役預備條款已寫但未動的結論。

### v1.6.1 為什麼提前執行第二輪退役（不等 v1.4 「1-2 月觀察期」）

v1.4 §第二輪退役預備條款列 4 條觀察期 metric（5 個 SKILL.md 觸發頻率 / Orientation 升 skill 命中率差 / Distillation 跑時實際做了什麼 / 員工心智負擔）。

v1.5 揭露根本問題：
- `generation_trace`: 0/61（trace 採用率永久空轉）
- `verifier_scores`: 0/61
- `hook_type`: 13/61（21%）
- 觀察期 metric 全部依賴「trace 累積→分析」、trace=0 = metric 永遠來不了

→ chicken-and-egg trap：等下去 = 3 個月後仍是 0、v1.7 再寫一次「等觀察期」、迴圈。
→ first-principles 直判：v1.4 結論已正確（5 → 3）、不需要 metric 證明、執行即可。

### v1.6.2 第二輪退役本次落地範圍

| 動作 | 落點 | 狀態 |
|------|------|------|
| `02-skill-factory/orientation/SKILL.md` v1.0 → v2.0 stub | 規則回 workflow.md §Orientation Phase 1 | ✅ 本 PR |
| `02-skill-factory/distillation/SKILL.md` v1.0 → v2.0 stub | 三 phase 拆 workflow.md §Lesson 硬化提議 + session-start hook + `/harden` command | ✅ 本 PR |
| `02-skill-factory/shared-references/brain-loading.md` v1.3 → v1.4 | §適用 skill 表標 stub | ✅ 本 PR |
| engine-manifest.json + CHANGELOG | 版本同步 | ✅ 本 PR |
| `.claude/skills/orientation.md` description 更新 | 標 stub | ⚠️ 待 Kai 授權 .claude/ 編輯後 follow-up |
| `.claude/skills/distillation.md` description 更新 | 標 stub | ⚠️ 同上 |
| `.claude/rules/workflow.md` §Orientation Phase 1 → §Orientation 正式版 + §Distillation 統一段 | 規則層收斂 | ⚠️ 同上 |

短期不影響運作：SKILL.md stub 仍指向 workflow.md 既存段落（§Orientation Phase 1 / §Lesson 硬化提議 / §對話期間的進化提案）、規則層原本就跑得起來。.claude/ 改動是 cosmetic / 維護整齊度、非功能性阻塞。

### v1.6.3 元規則：架構研究的退場條件

> 寫進長期規則、避免下次 v1.7 / v1.8 再開一輪「請用 X.X mature 視角再 review」迴圈。

**規則**：當以下三條同時成立時、不得開新一輪架構研究、改執行已存在但未落地的結論：

1. 上一輪研究結論（如 v1.4 §第二輪退役預備條款）寫了「觀察期後執行」、但觀察期數據因採用閉環失敗永遠不會累積（trace=0 / verifier=0 / hook_type < 30%）
2. 既有結論已包含當前問題的答案（如「5→3 真 skill」+「即時回饋」+「CLI 強制」三層配套）
3. 再開一輪研究的觸發是「模型能力升級」這個自我宣稱、不是新傷口（沒有真實生產卡點 / 沒有反證既有結論）

違反代價：v1.X → v1.X+1 → ... 形成研究迴圈、結論執行率 0、與 Top 3 失敗（metadata-completer / brand-keeper / harden-guide）同構。

**觸發模型**：
- 任何「請用 4.X 視角重新審視 skill 架構」對話、Claude 必先跑此退場條件
- 三條全成立 → 不展開 8 區塊研究、改回「執行待辦結論清單」+ 拒答理由（如本輪 v1.6 對 Kai 的回覆）
- 三條任一不成立（如：發現新傷口 / 既有結論明確矛盾真實使用）→ 才展開研究、且須先列「上一輪結論為什麼還沒落地」

**與既有規則的關係**：
- 工作模式 Z（架構審視批判上次審視）：要求「若做、必批判前次」
- 本元規則：要求「先判斷該不該做」
- 兩者互補、Z 在前提下審視、本規則在前提之前判斷

### v1.6.4 與既有結論的關係

- v1.0 三大發現（採用閉環 / lesson 退化 / 警告型治理）：仍正確、不變
- v1.1 三死角：reading loop（待 trace 數據 ≥10 支才動）、lesson-pressure（已 hook 化）、缺能力（Discovery 已補）
- v1.2 vNext + v1.3 5 核心：本次退役後留 3 真 skill（discovery / generation / quality）、Orientation/Distillation 改 stub
- v1.4 §第二輪退役預備條款：本 v1.6 是其執行（提前 1-2 月、由 v1.5 觀察期 trap 觸發）
- v1.5 補注「不再做 v1.6 研究」：本 v1.6 不是「新研究」、是「v1.4 結論執行 + 元規則沉澱」、與 v1.5 相容

### v1.6.5 為什麼是 v1.6 而不是 v2.0

v1.0-v1.4 主結構不變、v1.5 補注確認、v1.6 執行 v1.4 已寫結論並沉澱元規則 — 仍是 minor bump 範圍。

未來若 3 個 hardened 真 skill（discovery / generation / quality）任一被反證、或 Discovery 在實際 Kai 工作流中被驗證為不該獨立、才考慮 v2.0。

---

## v1.7 補注（2026-05-05、§盲點 3 + v1.5 hypothesis 雙證偽記錄）

> **本節定位**：純記錄已觀察的反證、**不預測 v1.3（v5.87）的解是否成功**。v1.3 能否解 14 天後才知道、但下面兩個 hypothesis 已經被現實證偽、這個事實不依賴 v1.3 結果。

### v1.7.1 證偽 #1：v1.4.1 §盲點 3「Output Contract 強制 fenced JSON 是合理 trade-off」

**原文**（v1.4.1 §盲點 3）：

> | **Output Contract 強制 fenced JSON** | 每個生成型 skill 末附 JSON block | 4.6 LLM 容易忘 / 寫錯欄位、強制 JSON 是保險 | **合理 trade-off、保留**；但要意識到這是顯式選擇、不是「永遠對的」 |

**v1.4.1 判斷**：fenced JSON 是 4.6 慣性、但「合理 trade-off」、保留。

**現實證偽**：v1.5 補注（30+ 天觀察）顯示 `generation_trace 0/30、verifier_scores 0/30、hook_type 13%`。fenced JSON block 印在對話中、Claude 必須再呼叫 CLI 把 JSON 抄進 --trace、是「Claude → 自己看的 JSON → CLI」3 段傳遞、第 3 段持續失敗。

**v1.7 reframe**：v1.4.1 的「合理 trade-off」判斷錯了。fenced JSON 不是 human-Claude-conversation artifact 的 trade-off、是 4.6 慣性「skill = markdown 給人看」的延續。4.7 mature 視角下、trace 應該是 skill 執行不可分割的一部分、不是「印給 Claude 自己看的 JSON、再叫 Claude 抄到 CLI」。

**對應修法**：v5.87 generation/quality v1.2 → v1.3 移除 fenced JSON 中介層、trace 直接 inline 進 --trace heredoc arg。v1.3 解不解 trace 0/30 是 14 天後才知道的事、但「v1.4.1 §盲點 3 的 trade-off 判斷錯」這事實**不依賴 v1.3 結果**。

### v1.7.2 證偽 #2：v1.5 補注 hypothesis「PR #348 CLI 強制 = 行為層解」

**原文**（v1.5 補注）：

> **補完路徑**（PR #348 進行中）：
> - CLI 強制：`video-ops.py save` 在 `_meta.trace_required_statuses` 列名的狀態下、缺 `--trace` 即 `exit 1`
> - CLI 工具：`save-with-trace-from-stdin`（從 stdin 抽 fenced JSON block）+ `adoption-stats`（趨勢觀測）
> - 配置：`data/template/pipeline.json` + `data/kai/pipeline.json` `_meta.trace_required_statuses` 加上必填狀態

**v1.5 隱含 hypothesis**：CLI 強制（exit 1 擋下無 trace 的 save）= 行為層解、trace 採用率會升上來。

**現實證偽**：CLI 強制 + `trace_required_statuses = ['剪輯中', '已上線']` 已落地 30+ 天、`generation_trace 仍 0/30`。CLI 擋下「呼叫了但沒帶 trace」、**擋不下「呼叫前 Claude 在對話中印了 fenced JSON 給 Kai 看就停了」**。

**v1.7 reframe**：「機械擋下」 ≠ 「行為改變」。CLI 強制是事後拒絕（rejected after attempted save）、不是事前驅動（driven before attempted save）。Claude 對話中如果根本沒走到 save 那一步、CLI 強制無從觸發。trace 0/30 真實根因不是 CLI 強制不夠硬、是 SKILL.md 動詞「呼叫 CLI」+ 印 Bash code block 在 Claude 4.6 慣性下退化為「展示給 Kai 抄」。

**對應修法**：v5.87 SKILL.md 動詞硬化（呼叫 → Bash tool 直接執行）+ 移除中介層。同上、v1.3 解不解是 14 天後才知道、但「v1.5 hypothesis（CLI 強制 = 行為層解）不夠」這事實已成立。

### v1.7.3 為什麼此補注不違反元規則 v1.6.3「研究退場條件」

v1.6.3 三條件再檢視：

1. **觀察期 metric 因採用閉環失敗永遠不會累積** — 仍成立（trace 0/30）
2. **既有結論已包含當前問題的答案** — **不成立**：v1.5 寫「CLI 強制 = 解」、被現實證偽。這是新傷口、v1.7 是記錄它、不是新研究輪
3. **觸發是「模型能力升級」自我宣稱** — 不適用（本補注由 v5.87 commit 觸發、是真實證偽記錄、不是 4.X mature 自宣）

三條中第 2 條不成立 → 依 v1.6.3「三條任一不成立 → 才展開研究、且須先列『上一輪結論為什麼還沒落地』」、本補注合規。

且本補注**不展開新 8 區塊研究**、只記錄已觀察的證偽、保留 v1.6.3 的研究退場精神。

### v1.7.4 為什麼此補注不違反 CLAUDE.md 禁令 #13「預測 → 不做」

禁令 #13 禁止「預測會用到 X 能力」式的 skill 新增。

本補注**不預測 v1.3 修法成功**、只記錄 v1.4.1 §盲點 3 + v1.5 hypothesis **已觀察到的失敗**。記錄反證 ≠ 預測解。

v1.3 14 天後若達標、再寫 v1.8 補注「動詞硬化驗證有效」；若未達標、寫 v1.8 補注「動詞硬化也不夠、追下一層 root」。**本 v1.7 不寫 v1.3 結果、也不需要寫**。

### v1.7.5 為什麼是 v1.7 而不是 v2.0

v1.0-v1.6 主結構（三大發現 / vNext 5→3 真 skill / 元規則 v1.6.3）不變、v1.7 補一個雙證偽記錄、不改主結構。minor bump 合適。

未來若 v1.3 修法 14 天後也被證偽、寫 v1.8 補「動詞硬化也不夠」；若 v1.3 達標、寫 v1.8 補「動詞硬化驗證有效」。任一情況都仍是 minor bump、除非主結構（5 → 3 真 skill）被反證才考慮 v2.0。

### v1.7.6 與既有結論的關係

- v1.0 三大發現（採用閉環 / lesson 退化 / 警告型治理）：仍正確、不變
- v1.1 三死角：reading loop（待 trace 數據 ≥10 支才動）/ lesson-pressure（已 hook 化）/ 缺能力（Discovery 已補）— 不變
- v1.2 vNext + v1.3 5 核心 → v1.6 第二輪退役 3 真 skill：不變
- **v1.4.1 §盲點 3「fenced JSON 合理 trade-off」**：v1.7 證偽、改為「4.6 慣性、應移除中介層」
- **v1.5 hypothesis「CLI 強制 = 行為層解」**：v1.7 證偽、改為「CLI 強制是事後拒絕、不是事前驅動、不夠」
- v1.6.3 元規則「研究退場條件」：仍正確、本 v1.7 過了三條件檢查才寫

### v1.7.7 與 workflow.md §設計原則 Mode W 的關係

v5.87 commit 同時提案 workflow.md §設計原則新增 **Mode W「1 個月 metric 驗證原則」**（沉澱 v1.5 補注末教訓「上線 1 個月看 metric、0 = 未上線、追行為層、不再加禁令」）。Mode W 是規則層、本 v1.7 補注是研究層、兩者互補：

| 層 | 文件 | 角色 |
|----|------|------|
| 研究層 | 本檔 v1.7 | 記錄 v1.4.1 + v1.5 雙證偽、不預測 v1.3 結果 |
| 規則層 | workflow.md Mode W | 把「1 個月 metric 驗證」固化為對話流程行為規則 |
| 元規則層 | 本檔 v1.6.3 | 何時不該開新研究輪、本 v1.7 過此檢查才寫 |
