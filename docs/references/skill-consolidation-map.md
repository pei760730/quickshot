# Skill Consolidation Map（14 → 5、v1.1 修正）

> version: 1.2 | last_updated: 2026-05-15 | author: Claude (Opus 4.7)
> 對應 `skill-architecture-principles.md` v1.3 §vNext + `skill-design-principles.md` v1.3 §準則 E + CLAUDE.md 禁令 #12

## 本檔角色

把 v1.2 vNext 4 核心 skill 架構的 **14 → 4 合併路徑**用一張表呈現、給維護者 / 員工 / 後續客戶 fork 時直接讀。

不重複 vNext 章節的「為什麼」(已在 `skill-architecture-principles.md` v1.2)、本檔只放**操作層 map**。

---

## 處置統計（v1.1 修正：14 → **5** 不是 14 → 4）

| 處置 | 數量 | Skill 名稱 |
|------|------|-----------|
| **保留為核心**（升級 / 主體）| **3** | flow-operator → Generation、harden → Distillation、**topic-architect → Discovery（v1.1 修正）** |
| **合併**（併入核心）| 6 | flow-maximizer / series-engine / interview-navigator / viral-knowledge / humanizer / script-verifier |
| **降級**（→ template / tool / lint）| 4 | hook-killer / title-generator / topic-researcher / trend-adapter |
| **封版**（不動）| 1 | skill-creator |
| **新建核心**（合併接收方 / 升級）| 2 | Orientation Skill、Quality Skill |

**淨數**：14 個 skill → **5 個核心 skill**（Orientation / **Discovery（v1.1 新增）** / Generation / Quality / Distillation）。

> **v1.1 修正歷史**：v1.0 把 topic-architect 列「反向重設計」、源於我對 Kai 工作流的誤判（以為「Kai 缺篩選不缺生成」）。2026-04-25 Kai 工作流確認對話揭露真實需求是「外部熱點 + 大腦交互 → 選題建議」、屬 v1.0 漏判的能力 G「選題發現」。topic-architect 升級為 Discovery Skill 主體、不降級。

---

## 14 個 skill 完整 map

### 保留為核心（升級為 vNext 主體）

| Skill | 現版本 | 落在 vNext | 為什麼保留 | 過了禁令 #12 | 動作 |
|-------|--------|-----------|----------|------------|------|
| **flow-operator** | v1.50 | Generation Skill 主體（mode=dual-track）| T1 主生成器、跨 task 重用、需 AI 判斷 4 版選邊、明確 IO（腳本 markdown）、不可降級為純模板 | ✅ 全 10 條 | Phase 3 升級為 Generation Skill |
| **harden** | v1.2 | Distillation Skill 主體 | 規則沉澱層、跨 task 重用、需 AI 判斷 lesson 升路徑、明確 IO（lesson stage 變動）| ✅ 全 10 條 | Phase 4 升級為 Distillation Skill |
| **topic-architect**（v1.1 新增）| v1.24 | **Discovery Skill 主體**（modes: discover-week / discover-month / discover-trend）| 對應失敗模式 F7（靈感被個人視野限制）、跨 task 重用、需 AI 判斷「外部熱點對品牌有沒有意義」、明確 IO（5-10 個選題建議）| ✅ 全 10 條（過了 v1.3 §F7 + G 推導）| **Phase 4 升級為 Discovery Skill**（需 tool 配套：web fetch tool）|

### 合併（併入核心 skill）

| Skill | 現版本 | 落在 vNext | 為什麼合併 | 動作 |
|-------|--------|-----------|----------|------|
| **flow-maximizer** | v1.55 | Generation Skill mode=variant | 跟 flow-operator 同責任、不同 mode | Phase 3 合併 |
| **series-engine** | v1.36 | Generation Skill mode=series | 同上 | Phase 3 合併 |
| **interview-navigator** | v1.36 | Generation Skill mode=interview | 同上 | Phase 3 合併 |
| **viral-knowledge** | v1.23 | Generation Skill mode=viral | 同上、不綁大腦的特殊 mode | Phase 3 合併 |
| **humanizer** | v1.28 | Quality Skill phase=fix | 跟 verifier 重疊（v1.0 發現 A 補洞重疊）| Phase 4 合併（quality-loop pattern）|
| **script-verifier** | v1.15 | Quality Skill phase=check | 同上 | Phase 4 合併 |

### 降級（→ template / tool / lint）

| Skill | 現版本 | 真實層級（準則 E）| 落在哪 | 動作 |
|-------|--------|--------------|------|------|
| **hook-killer** | v1.14 | 模板（17 條 H/HD）| `02-skill-factory/shared-references/templates/hook-templates.md` | Phase 2 降級 |
| **title-generator** | v1.14 | 部分規則（lint）+ 部分模板 | `shared-references/title-rules.md`（lint）+ personas/kai.md [1] 引用 | Phase 2 降級 |
| **topic-researcher** | v1.10 | 工具（外部資料 fetch）| `scripts/tools/research.py`、Generation Skill 內按需呼叫 | Phase 2 降級 |
| **trend-adapter** | v1.20 | 工具（Reels 解析）| `scripts/tools/trend.py`、Generation Skill 內按需呼叫 | Phase 2 降級 |

### ~~反向重設計~~（v1.1 移除、誤判修正）

> v1.0 把 topic-architect 列「反向 Filter Skill」是錯的。Kai 工作流確認後升級為 Discovery Skill 主體（見上方「保留為核心」+ 「Discovery Skill spec」）。

### 封版（不動）

| Skill | 為什麼封版 | 動作 |
|-------|----------|------|
| **skill-creator** | 官方 MCP 內建、不在我們 skill 系統範圍 | 不動 |

---

## vNext **5** 核心 skill 規格摘要（v1.1 修正）

詳細 spec 見 `docs/references/skill-architecture-principles.md` v1.3 §vNext + §v1.3 補丁。本表只列每個 skill 對應的本質能力 + 失敗模式 + 主要 IO。

| Skill | 本質能力 | 失敗模式 | Input | Output |
|-------|---------|---------|-------|--------|
| **Orientation** | A 任務定型 + B 上下文選擇 | F1、F2、F4 | Kai 對話 + brain_loader 結果 + CLAUDE.md/workflow.md context | task contract（自然語言一句話）+ task spec for downstream |
| **Discovery**（v1.1 新增）| **G 選題發現** | **F7 靈感被個人視野限制** | 觸發訊號（"下週要拍什麼"）+ brain_loader + **web fetch（IG/TikTok/同業/熱點）** | 5-10 個選題建議（標題 + 切角 + 來源 + 信心分數）|
| **Generation** | C 變更設計 | F2、F4 | Orientation 或 Discovery output + brain_loader + mode 選擇 | artifact（.md / code diff / config）+ 變更計畫 |
| **Quality** | D 驗證定義 | F5 | Generation output + verification 標準 | 修改後 artifact + verifier_scores JSON + pass/fail |
| **Distillation** | E 經驗沉澱 | F6 | task 過程 contract 預測 vs 實際 + lessons.json | `lessons add-evidence` 呼叫 + 候選 lesson 提案 + brand 更新建議 |

**邊界遵守 F**（territory）= **不是 skill**、由 territory-lint CI 守（2026-06 輕量重新引入、見 AGENTS.md）。

**流程**：Orientation → 若 task=找選題 → Discovery → Generation → Quality → Distillation。  
若 task=拍既有選題 → 跳過 Discovery、直接 Orientation → Generation → Quality → Distillation。

---

## 落地路徑（4 Phase、每階段獨立可 merge）

| Phase | 內容 | 風險 | 工作量估 | 狀態 |
|-------|------|------|--------|------|
| **Phase 1** | 規則 + 文件層（CLAUDE.md 禁令 #12 + workflow.md §Orientation Phase 1 + 準則 E + vNext 章節 + 本 map）| 低 | 6-8 hr / 5 檔 / 1 PR | **本 PR 落地** |
| **Phase 2** | 降級類（hook-killer + title-generator + topic-researcher + trend-adapter + topic-architect 反向重設計）| 中 | 8-12 hr / 10-15 檔 / 2-3 PR | 待 Phase 1 merge 後 |
| **Phase 3** | 合併類 - Generation Skill（5 generation skill → 1 + 5 modes）| 中高 | 12-16 hr / 15-20 檔 / 2-3 PR | 待 Phase 2 merge 後 |
| **Phase 4** | 合併類 - Quality + Distillation + Orientation Skill 升級 + **Discovery Skill 建立**（從 topic-architect 升級、需寫 web fetch tool）| 中高 | 16-20 hr / 18-25 檔 / 3-4 PR | 待 Phase 3 merge 後 |

每 Phase 之間可選擇：
- 連續做（密集週、每階段間最多停 1 天驗）
- 停 1-2 週觀察員工反應再進下一個（穩健）
- 永遠停（部分接受、不必完成全部）

---

## 與既有資產的對應（vNext 後仍保留）

不變的部分（v1.1 已封版 + Phase 1 新加）：

| 資產 | vNext 後角色 |
|------|------------|
| `01-data-brain/brand.md` + `cases.md` | Orientation Skill + Generation Skill 載入來源（不變）|
| `02-skill-factory/shared-references/` 9 份 | 4 核心 skill 共用（不變）|
| `scripts/libs/brain_loader.py` | Orientation Skill 內部 tool（不變）|
| `scripts/ops/video-ops.py` CLI | 4 核心 skill 都會呼叫（不變）|
| `data/<operator>/pipeline.json` schema | 不變、繼續累積 trace / scores |
| territory-lint CI（2026-06 輕量重新引入） | 守 F「邊界遵守」、4 核心 skill 不取代（不變）|
| `engine-version-check` CI gate | 守版本一致（不變）|
| `/harden` skill（v1.2）| Phase 4 併入 Distillation Skill 為 phase=harden |
| `lesson-pressure` hook（PR #289）| Phase 4 對應 Distillation Skill 對話端 |
| `add-evidence` CLI（PR #290）| Phase 4 對應 Distillation Skill evidence 累積 |

---

## CLI 層配套（Phase 2-4 才需要）

Phase 1 純 prompt / skill 層、無 CLI 工作。後續階段預期需要 CLI 配套：

| Phase | CLI 配套 | 層 |
|-------|----------|------|
| Phase 2 | `scripts/lint/canonical-registry.json` valid_skills 列表更新（4 個 skill 降級時） | CLI 層 |
| Phase 2 | (已退役) skill count check（從 14 降到 11） | CLI 層 |
| Phase 3 | `scripts/libs/brain_loader.py` 加 mode 參數支援（Generation Skill 5 modes）| CLI 層 |
| Phase 3 | canonical-registry valid_skills（從 11 降到 7） | CLI 層 |
| Phase 4 | quality-loop CLI（合併 humanizer + verifier 操作）| CLI 層 |
| Phase 4 | **web fetch tool**（Discovery Skill 配套：IG / TikTok / 競品熱點 fetch）| **CLI 層（v1.1 新增）** |
| Phase 4 | canonical-registry valid_skills（從 7 降到 **5**、不是 4）| CLI 層 |

詳細 task brief 在每 Phase 開始時撰寫。

---

## 與其他文件的關係

| 文件 | 角色 |
|------|------|
| `docs/references/skill-architecture-principles.md` v1.2 | vNext 章節是本 map 的「為什麼」 |
| `02-skill-factory/shared-references/skill-design-principles.md` v1.2 | 準則 E（分層判斷）是本 map 的「怎麼分」 |
| `CLAUDE.md` 禁令 #12 | 10 條件是本 map 「保留 / 合併 / 降級」決策的硬化版 |
| `.claude/rules/workflow.md` v2.22 §Orientation Phase 1 | Phase 1 規則化版本（不立即建 skill）|
| `engine-manifest.json` | 本檔納入 `semantic_contracts` 追蹤（v5.95+ contract 分層後、純文字 stale 屬 `factual_contracts`、僅本檔規則性內容變動才觸 engine bump）|

---

## 修改本檔的時機

- 任一 Phase 完成 / 中止 / 改變範圍 → 更新對應 row 狀態
- 新增 skill candidate 出現 → 加 row 說明處置
- vNext 4 skill 架構本身變動（從 4 變 5 或 3）→ 大改、bump major

不該頻繁修改。本檔是 14 → 4 路徑的長期錨點。

---

## 版本歷史

- **v1.0**（2026-04-25）：Phase 1 建立、對齊 v1.2 vNext 4 核心 skill 架構。對應 lesson L-0015（Claude 沉澱層 vs 行動層保守混淆的修正）+ Kai 主動驅動 first-principles skill consolidation 研究。
- **v1.1**（2026-04-25）：補 v1.0 漏判 Discovery（第 5 核心 skill）+ topic-architect 處置從「反向重設計」改「升級為 Discovery Skill 主體」+ Phase 4 加 web fetch tool 配套。對應 v1.3 §v1.3 補丁。**研究漏判教訓**：Kai 工作流確認 (b) 同業 / (c) 員工問題 / (d) IG/TikTok 是真實選題來源、Q2.a 缺生成 + Q2.c 缺切角是真實瓶頸；Claude 前期判斷「Kai 缺篩選」是錯的。
