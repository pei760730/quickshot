# Skill 設計準則（Opus 4.7 視角）

> version: 1.6 | last_updated: 2026-05-15 | scope: 02-skill-factory 內所有 skill

## 本檔角色

`02-skill-factory/shared-references/` 第 8 份共用規則。**新增 / 重設計 skill 前必讀。**

研究背景與三大結構性發現見 `docs/references/skill-architecture-principles.md`。本檔只放可操作的設計準則。

與既有 7 份規則的關係：
- `quality-gates.md` 管「skill 跑時的品質流程」
- `red-line-protocol.md` / `banned-words.md` / `output-quality-rules.md` 管「skill 輸出的內容紅線」
- `performance-injection-protocol.md` / `data-brain-manifest.md` / `brain-loading.md` 管「skill 輸入的資料協議」
- **本檔（skill-design-principles.md）管「該不該有這個 skill / skill 該長什麼樣」**——前置於以上所有人

---

## 準則 A：補洞型 skill 是訊號、不是答案

### 條文

當需求被描述為「需要一個 skill 來修 / 補 / 驗證 X 沒被做好」時、**優先反問源頭為何沒做好**、不直接新增。

補洞型 skill 的存在本身代表上游設計缺陷、加它只是把缺陷藏進「另一道牆」、不解決問題。

### 識別

candidate skill 名字含以下字眼 → 高機率是補洞型：
- `*-completer`（補東西沒填好）
- `*-fixer` / `*-corrector`（修東西做錯）
- `*-verifier` / `*-validator`（檢查東西沒做對）
- `*-keeper` / `*-guard`（守東西不被破壞）
- `*-cleanup`（清東西沒清乾淨）

**不一定壞**——但出現時必過下面的決策樹。

### 決策樹

```
1. 上游 skill 為何沒做好這件事？
2. 能不能改上游 skill 的 prompt / Hard Gate / 規則沉澱解決？
3. 若上游改了仍會漏 → 是不是上游本身的責任邊界錯了？
4. 真的需要獨立補洞 skill → 在 SKILL.md 開頭明標「本 skill 是 X 缺陷的補丁、長期目標是消失」
```

只有第 4 步走完、補洞 skill 才上線。

### 反例記憶錨

- （Phase 5 前歷史）`humanizer` + `script-verifier §③ AI 味檢查` 並存——兩個補洞 skill、源頭 flow-operator 在生成階段沒被強化人格控制。**正解已落地**：source 強化、quality-loop 整併（Phase 5 整併 humanizer + script-verifier → `quality` skill phase=check/fix、flow-operator → `generation` skill）。見 `docs/references/skill-architecture-principles.md` P3。
- 歷史 Top 3 退役：`metadata-completer`（補欄位沒填）、`brand-keeper`（檢查 brand 漂移）、`harden-guide`（提示要硬化）——都是補洞型、都失敗於「印了沒人動」。

### 與既有 skill 的關係

- `harden` v1.2 看似補洞、但本質是**規則沉澱層**（不是修補產出、是把學到的東西寫進規則）、不適用本準則。
- （Phase 5 前）`script-verifier` 是補洞型、長期目標應與 humanizer 整併、強化 flow-operator 後降級——**已於 Phase 5 整併進 `quality` skill phase=check、flow-operator 整併進 `generation` skill**、本反例已落地。

---

## 準則 B：可推理的事不寫死、可機器算的事不留給人類

### 條文

新增 SKILL.md / hook / 對話流程時、依下列順序追問：

1. 這個「必遵守 N 條原則」可不可以變成 **lint 規則**？能就寫 `scripts/lint/rules-lint.py`、不寫進 SKILL.md。
2. 這個「請依下表選擇」可不可以交給 **LLM 推理**？4.7 推理力下能就交、不寫成菜單。
3. 這個「Kai 必須回答」可不可以**自動算**？能就算、不問人。

只有三層都不行、才寫進 skill 推理流程或人工問答。

### 邊界

- **內容紅線**（red-line-protocol）必寫死成規則、不交推理。
- **品牌主觀判斷**（哪個標題更好）必交人、不自動算。
- **跨會話事實**（這支影片的回填數字）必算 / 必問、不能推理。

### 反例記憶錨

- `title-generator` v1.14 寫死 10 條「必遵守」原則（第一人稱 / 負面框架 / 數字開頭…）——大部分可變 lint。
- `humanizer` 24 patterns 寫死掃描——已是規則化、保留為 lint 即可、不需 skill 推理。
- 早期 `flow-operator` v1.39 含「表 1：5 類心理觸發 / 表 2：選擇邏輯…」決策樹——v1.50 去食譜化（466→180 行）、把決策還給推理、是這條準則的成功實踐。

### 與既有 skill 的關係

- 食譜化殘留 skill：`hook-killer` v1.14 / `viral-knowledge` v1.22 / `trend-adapter` v1.20。**現狀封版**（見 `docs/references/skill-architecture-principles.md`「不該因模型升級亂改」）、未來重看時依本準則處理。

---

## 準則 C：skill 數量不是智能指標

### 條文

新增 skill 前、過 `CLAUDE.md` 禁令 #7「硬化優先」三層自問：

| 層 | 自問 | 通過則 |
|---|------|-------|
| (a) | 能用 lint / test / `scripts/lint/rules-lint.py` 規則擋嗎？ | 寫規則、不開 skill |
| (b) | 能用 `CLAUDE.md` 禁令 / `workflow.md` 段落 / `brand.md` 寫清楚嗎？ | 寫文件、不開 skill |
| (c) | 能用 schema 欄位 / `data/.operators.json` 等資料層約束嗎？ | 寫 schema、不開 skill |

三層**都不行**才寫 feature code（含新 skill）。三層模糊不清 → 先列方案問 Kai、不擅自開新 skill。

### 為什麼

模型變強 ≠ skill 系統要變複雜。多一個 skill 就多一份維護成本（SKILL.md + entry stub + README + CHANGELOG + 升版連動）。Opus 4.7 推理力的正確用法是**用更少的控制點解決更多問題**、不是「因為模型強、可以承受更多 skill」。

### 反例記憶錨

- 歷史 Top 3 退役：`metadata-completer` / `brand-keeper` / `harden-guide`——三個 skill 都因為「能用 hook + CLI 解決、卻寫成 skill」而失敗。
- `daily-raw-to-inbox-lite` v1.15 + `publish-optimizer` v1.00（v4.8 退役）——使用率 0、功能重疊、是「skill 化過早」的例子。

### 與既有 skill 的關係

- 14 個現有 skill 的審視在 `docs/references/skill-architecture-principles.md`「不該因模型升級亂改」+「下一步順序」兩段。
- 短期不新增 skill。研究中提到的 `quality-loop`（humanizer + verifier 整併）是**減少**1 個 skill、不是新增。

---

## 準則 D：新增 skill 的真正槓桿是「能力缺口」、不是「現有問題」（v1.1+）

### 條文

審視 skill 架構時、不能只用「現有 skill 哪裡有問題」這個 lens。**還必須問**：「Kai 在做什麼工作時、目前完全沒系統支援、Kai 自己處理但耗時 / 容易漏？」

準則 A/B/C 是 **裁減視角**（防止過度新增），準則 D 是 **擴張視角**（防止系統性盲區）。**缺一個、整個準則體系永遠只能裁不能加、會錯過真正該做的能力**。

### 識別問法

每次架構審視必跑這四個問題：

1. **Kai 重複手動做的事**：哪些工作 Kai 每週 / 每月反覆做、目前 0 系統支援？
2. **隱性能力缺口**：哪些能力 4.6 推理力下不敢做（容易 hallucinate / 因果推理弱 / 跨多支推理不穩）、但 4.7 能 hold 住？
3. **跨多 VID 的 pattern 識別**：目前 weekly-report 看單支、有沒有「跨 N 支同類影片表現規律」這種 series-level 分析需求？
4. **策略層工作**：Kai 想「這週該拍什麼 / 月主題 / 季方向」時、有沒有 skill 支援？

### 識別失敗的反例

- **`topic-architect` 0 使用**：v1.0 把它列進「不該因模型升級亂改」清單、但 0 使用是事實。**v1.0 / v1.2 的判斷都錯**：v1.0 假設「方向錯、需反向重設計成篩選器」、v1.2 沿用此判斷。**v1.3 修正**：2026-04-25 Kai 工作流確認對話揭露真實需求：選題來源 (b) 同業 / (c) 員工問題 / (d) IG/TikTok 熱門、瓶頸 Q2.a 缺生成 + Q2.c 缺切角——**完全是「外部觸發 + 大腦交互」**、不是「篩選現有靈感」。topic-architect 升級為 Discovery Skill 主體（v1.3 vNext 第 5 核心）、不降級不反向。
- **三層教訓**：
  1. 4.6 設計時：「自動化幫 Kai 想選題」（生成方向）— **錯**
  2. v1.0/v1.2 推導時：「Kai 缺篩選不缺生成」（篩選方向）— **錯**
  3. v1.3 修正：「Kai 缺『外部 + 大腦交互的選題建議』」（Discovery 方向）— **對**
- **識別失敗的元教訓**：準則 D 四問跑了不夠、必確認與 Kai **實際工作流**對齊（不是只憑 Claude 推測）。先問 Kai 工作流再下判斷、不要自己猜。

### 邊界與成本

- 準則 D **不會強制新增 skill**——它只強制「審視時要問」。問了之後、新增與否仍要過準則 A / B / C。
- 識別出 N 個缺口、不代表要做 N 個 skill。**先觀察 1-2 週實際工作流**、看哪個缺口最常碰到、再做 1 個。

### 與準則 A/B/C 的關係

| 準則 | 視角 | 防的錯 |
|------|------|--------|
| A | 裁減 | 補洞 skill 過多 |
| B | 裁減 | 寫死規則過多 |
| C | 裁減 | 過度新增 skill |
| **D** | **擴張** | **盲區（該存在的能力 0 存在）** |

A/B/C/D 缺一不可。

### 反例記憶錨

- **Reading loop 缺口**（Adoption Loop 完成後浮現）：寫入端解了（trace JSON → CLI → pipeline.json），讀取端還沒接（skill 推理時主動拉「上次同情境怎麼處理」）。詳見 `docs/references/skill-architecture-principles.md` 死角 #1。
- **Series-level retrospective 缺口**：跨 5 支同類影片的表現規律分析、目前 0 skill。
- **Hook 失敗反事實推理**：「為什麼 D3 hook 在某類題反覆失敗」、4.7 能做、目前 0 skill。

---

## 準則 E：能力 vs 規則 vs 模板 vs 工具的分層判斷（v1.2+、對應 CLAUDE.md 禁令 #12）

### 條文

新增 candidate 時、依以下順序自問、找到第一個答 Yes 的層、就停在那層、**不**進 skill 層：

1. 是「**規則**」嗎？（永遠 active、不需 task 推理）→ 寫 `CLAUDE.md` 禁令 / `shared-references/*.md` rule layer
2. 是「**模板**」嗎？（task 寫 artifact 時 reference）→ 寫 `shared-references/templates/<name>.md`
3. 是「**工具**」嗎？（呼叫式、有明確 input/output）→ 寫 `scripts/` + 在 skill 內呼叫
4. 是「**Local workflow**」嗎？（單次 / 偶發、不跨 task 重用）→ 寫 `.claude/rules/workflow.md` 段落
5. **以上四層都不是**、需要 AI 判斷 + 跨 task 重用 + 獨立邊界 + 過了 CLAUDE.md 禁令 #12 「skill 成立 10 條件」 → 才考慮 skill

### 為什麼這條準則

之前 14 個 skill 中 **9 個是 4.6 慣性產物**（拆細以求穩定 / 食譜化以避飄移 / 補洞累積）。深層原因：4.6 時代沒有清楚的「規則 / 模板 / 工具 / skill」分層、什麼有用就包成 skill、結果 skill 變成萬用垃圾桶。

4.7 推理力下、**模型自己會判斷該套規則 / 該查模板 / 該呼叫工具**、不需要把每個能力都封裝成 skill 強迫 AI 推理。

### 反例（誤把規則 / 模板 / 工具當 skill）

| 誤分類 | 真實層級 | 處置 |
|--------|---------|------|
| `hook-killer` 17 條 H/HD 模板 | 模板（reference）| 降級為 `shared-references/templates/hook-templates.md` |
| `title-generator` 10 條原則 | 部分規則（lint）+ 部分模板 | 拆為 `shared-references/title-rules.md`（lint）+ personas/kai.md [1] 引用 |
| `topic-researcher` 外部資料 fetch | 工具 | 拆為 `scripts/tools/research.py`、Generation Skill 內按需呼叫 |
| `trend-adapter` Reels 解析 | 工具 | 同上 |
| `metadata-completer`（已退役）| 工具 + hook | 已正確處理（CLI 接管）|

### 正例（真 skill、過了準則 E + 禁令 #12）

| Skill | 為什麼是 skill |
|-------|--------------|
| `flow-operator`（→ Generation Skill 主體）| 跨 task 重用、需 AI 判斷 4 版選邊、有明確 IO（腳本 markdown）、不可降級為純模板 |
| `humanizer` + `script-verifier`（→ Quality Skill）| 同上、品質檢查需 AI 推理「這段是不是 AI 味」、不是固定規則 |
| `harden`（→ Distillation Skill 主體）| 跨 task 重用、需 AI 判斷 lesson 升路徑、明確 IO（lesson stage 變動）|
| **`topic-architect`（→ Discovery Skill 主體、v1.3 修正）**| 跨 task 重用、需 AI 判斷「外部熱點對品牌的意義」（推理性、非規則）、明確 IO（5-10 個選題建議 + 切角）、不可降級（web fetch + 大腦交互非 template/tool 能單獨做到、需 skill 級推理整合）|

### v1.3 反例新增：**自我漏判**（準則 E + 準則 D 的元教訓）

> v1.2 vNext 推導時、把 topic-architect 標「反向重設計或併入 Orientation」、實際上 topic-architect **本來就是真 skill**、只是設計時方向錯了。v1.0/v1.2 連續兩次推導都漏判、源頭是「準則 D 四問跑了、但結論被『需 web 工具、目前架構未必 ready』遮蔽」。

| Skill | v1.0/v1.2 誤判 | v1.3 修正 | 教訓 |
|-------|------------|---------|------|
| topic-architect | 反向重設計 / 降級 | 升級為 Discovery Skill 主體 | 「需 future tool」≠「能力不存在」、應明標「能力 X、依賴 future tool Y、Phase Z 落地」、不該因為 tool 還沒寫就漏列能力 |

**元教訓**：準則 E 5 層判斷時、若某能力依賴 future tool、不要一律推到「降級或反向」、應評估「是否本質就是 skill 級能力、只是 tool 還沒到位」。**先確認本質、再決定 tool readiness**。

### 與準則 A/B/C/D 的關係

| 準則 | 視角 | 防的錯 |
|------|------|--------|
| A | 裁減 | 補洞 skill 過多 |
| B | 裁減 | 寫死規則過多 |
| C | 裁減 | 過度新增 skill |
| D | 擴張 | 盲區（該存在的能力 0 存在）|
| **E** | **分層** | **誤把規則 / 模板 / 工具當 skill** |

A/B/C/D 守 skill **數量**邊界、**E 守 skill 層級**邊界。五準則互補。

---

## 準則 F：層次正確優先於 skill 完整（v1.4+、4.7 mature 視角）

### 條文

升級到正式 skill 之前、必跑 4 層退場測試（順序由輕到重）：

1. 能停留在「**對話準則**」（`workflow.md` §段落、Claude 自然遵守）嗎？能就停。
2. 能停留在「**跨 session hook + CLI**」（資料層自動觸發、Claude 看到再動）嗎？能就停。
3. 能停留在「**command**」（`/X`、Kai 或 Claude 顯式呼叫）嗎？能就停。
4. 能停留在「**shared-references 規則**」（內容 SSoT、skill 引用而非內化）嗎？能就停。

四層**都不能停**、且符合 CLAUDE.md 禁令 #12「skill 成立 10 條件」、才升 skill。

### 為什麼這條準則

準則 E 已說「skill 是最後選擇」、但實踐中仍可能升錯：把「對話準則層」的能力（如 task 開始時的 contract 宣告）升成 skill、把「跨 session 機制 + command 組合」的能力（如 lesson 沉澱的 collect/propose/harden 三段）塞進一個 skill。

4.7 mature 視角下、能力的「**觸發模型**」決定它的層次、不是「主題相關性」。同一主題的能力如觸發模型不同、應拆三層、不塞一個 skill。

### 反例記憶錨

| 升級錯誤 | 真實層次 | 為什麼錯 |
|---------|---------|---------|
| Orientation 升 SKILL.md（vNext Phase 4）| 對話準則（workflow.md §Orientation）| 已規則化跑得起來、升 skill 邊際收益低、增加維護成本 |
| Distillation 整包成 SKILL.md（vNext Phase 4）| collect 是對話準則 + propose 是 hook + harden 是 command | 三個 phase 觸發模型完全不同、塞同一 skill 是「skill-as-folder」非「skill-as-capability」 |

### 與準則 E 的關係

- 準則 E：判斷該不該是 skill（5 層分層）
- **準則 F**：判斷該不該升正式 skill（4 層退場測試）
- E 在「新增前」用、F 在「升級前」用（兩個不同決策時點）

### 與 vNext 5 核心 skill 的對照（檢討、非立即重組）

依準則 F 重新檢視 vNext 5：

| Skill | 通過準則 F 嗎？ | 真實層次（若不通過）|
|-------|---------------|------------------|
| Discovery | ✅（外部 fetch + 大腦交互、跨 session 重用、需 AI 推理整合）| skill |
| Generation | ✅（5 modes、明確 IO、需 AI 判斷）| skill |
| Quality | ✅（check/fix loop、需 AI 推理灰區、24 patterns 引用 SSoT）| skill |
| **Orientation** | ⚠️ 通過 1（對話準則層即可）| 應降回 workflow.md §Orientation |
| **Distillation** | ⚠️ 通過 1+2+3 組合、不該塞 skill | 應拆對話準則 + hook + command |

**處置**：vNext 5 → 觀察 1-2 月實踐命中率、再決定是否第二輪退役。**v1.4 不立即拆**、避免在剛 Phase 5 退役後再大重組。

### Owner 對應（v1.5+、配 CLAUDE.md 禁令 #11 owner 分流 + workflow.md v2.24 §Adoption-gate）

準則 F 的 4 層退場測試**還必須過 owner 過濾**：

| 能力 owner | 該停層 | 為什麼 |
|-----------|-------|------|
| `owner=employee`（員工操作） | 停在 hook + CLI 層、**不升 skill** | 員工不會用 skill 框架（沒 Claude Code 對話）、需要的是 CLI / 介面 |
| `owner=auto`（系統自動） | 停在 hook + CLI 層、**不升 skill** | 自動化能力不需 LLM 推理介面、CLI 即可 |
| `owner=kai`（Kai 對話操作） | 才考慮 skill（過完 4 層退場 + 10 條件）| Kai 透過 Claude Code 對話、skill 是合理介面 |

**反例（違反 owner 對應）**：
- 假設未來有人想做「backfill skill 自動回填影片數據」、按準則 F 4 層退場：
  - 對話準則層：Claude 對話中問 Kai 截圖 ❌（Kai 不負責回填）
  - hook + CLI 層：員工跑 CLI 補登 ✅（**這層停**）
  - command 層：/backfill ❌（員工不用對話）
  - shared-references：規範文件 ✅（補配套）
  - **→ 結論：CLI + 介面、不升 skill**
- 「backfill skill」表面通過準則 E（跨 task 重用 + AI 推理 + 明確 IO），但 owner=employee → 員工根本不會跑 skill、做了等於 metadata-completer / brand-keeper / harden-guide Top 3 退役命運（Kai 不操作 = 0 使用）

**判定流程**：
1. 識別能力的 owner（誰實際操作這個能力？）
2. 若 owner ≠ kai → 停在 hook + CLI 層、加配套介面（員工 web / 後台、員工自動跑 cron）
3. 若 owner = kai → 才繼續跑 4 層退場 + 10 條件決策

### 升版時機

本準則加入後、新增任何 skill 前必跑「準則 E 5 層 + 準則 F 4 層 + owner 過濾」三過。

---

### 實作層連動

- CLAUDE.md 禁令 #12「skill 成立 10 條件」是準則 E 的硬化版（10 條件全符合才得進 skill 層）
- 準則 E 是 10 條件的決策樹（先過 4 層降級、再考慮 10 條件）
- `docs/references/skill-consolidation-map.md`（v1.2 新增）依準則 E 分類 14 個既有 skill 處置

---

## 升版時機

- 三準則之一在實踐中被反證 → 改條文、bump major（v1.0 → v2.0）
- 出現第 4 條值得固化的準則 → 加入、bump minor（v1.0 → v1.1）
- 反例記憶錨清單擴充 → 加入、bump patch（v1.0 → v1.0.1）

不該頻繁修改。本檔是 02-skill-factory 內的長期錨點、與 `docs/references/skill-architecture-principles.md` 對齊。

---

## 在 shared-references 總索引中的位置

升版時若需新增條目到 `shared-references/README.md` SSoT 表、本檔的職責欄位填：「**Skill 該不該存在 / 該長什麼樣的設計準則（前置於品質 / 內容 / 資料協議三類）**」、主要使用者填「**新增 / 重設計 skill 時的 Claude / Kai**」。

但如本檔 v1.0 不主動修改 README——讓 README 維護者於下次升版時自然納入、避免雙處同步漂移。
