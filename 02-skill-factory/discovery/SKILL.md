---
name: discovery
description: 選題發現核心 skill v1.0（vNext 5 核心之一） — 整合 web 即時熱點 + 內部數據大腦 + 同業監控 + 員工 FAQ → 5-10 個選題建議 + 切角。觸發：Kai 說「下週要拍什麼」「這月該做什麼系列」「最近熱點」「什麼題目值得拍」「discovery」。
version: 1.0
last_updated: 2026-04-25
brand-refs: [4, 5, 6, 10, 11, 12]
---
<!-- vNext 5 核心 skill #2（v1.3 補正新增）— 對應 docs/references/skill-architecture-principles.md v1.3 §v1.3 補丁 §1.3.4 -->
<!-- engine v5.42 Phase 5 真退役：topic-architect / topic-researcher / trend-adapter 整刪、本 skill 邏輯已內化（內容變更但不 bump 版本、避免 stub frontmatter 不同步）-->
<!-- 依賴未來的 web fetch / research / trend tool（scripts/tools/、Wave C 待寫）-->

# Discovery Skill v1.0

> **本質能力 G**：選題發現（外部熱點 + 內部大腦交互 → 選題建議）
> **失敗模式**：F7（靈感被個人視野限制）
> **核心責任**：整合外部 + 內部、輸出 5-10 個選題建議 + 切角 + 信心分數

---

## 觸發方式

| Kai 說 | Mode |
|-------|------|
| `下週要拍什麼` / `週度選題` | discover-week |
| `這月該做什麼系列` / `月主題` | discover-month |
| `最近熱點` / `競品在做什麼` | discover-trend |
| `discovery` / `選題` / `什麼題目值得拍` | 由 Claude 推理選 mode |

---

## 三個 Mode

### Mode 1: discover-week（週度選題）

**Input**：
- 觸發訊號（Kai 講話）
- brain_loader 載入結果（brand.md / cases.md / performance-patterns）
- 上週 / 本月既有腳本（pipeline.json items 過濾）
- IG/TikTok 熱點（**需 web fetch tool**、目前 prompt-only fallback）

**Output**：5-10 個選題建議、每個含：
- 標題草稿
- 切角建議
- 對應 brand.md sections
- 來源（同業 / 員工 / 熱門 / 大腦交互）
- 信心分數（高 / 中 / 低）

### Mode 2: discover-month（月主題）

跨多個系列的月度策略選題：
- 連結 brand.md [10] 長期目標
- 對應 brand.md [11] 季節性節點
- 跨多個系列主題的整合視角（mode=series 落點）

### Mode 3: discover-trend（即時熱點響應）

即時對外部熱點做品牌 fit 判斷：
- 熱點 X 對品牌有沒有意義？（推理：對應 brand.md [3] 說話風格 + [4] 商業洞察 + [6] 競爭對手）
- 該怎麼切才不踩雷？（對應 brand.md [5] 禁忌）
- 多快回應？（即時 / 本週 / 本月）

---

## 選題來源（4 類）

對應 Kai 工作流確認 (Q1 答 b/c/d)：

| 來源 | 落點 | Tool 需求 |
|------|------|---------|
| **(b) 同業 / 競品** | brand.md [6] 競爭對手 + web fetch（同業近況）| web fetch |
| **(c) 員工 / 加盟主問題** | brand.md [12] 加盟主常問問題（已 SSoT）| 無（讀 brand.md）|
| **(d) IG/TikTok 熱門** | web fetch（即時熱點）| web fetch |
| **(內部) 大腦交互** | brand.md + cases.md + lessons + performance-patterns | brain_loader（已存在）|

---

## 步驟 0：載入

依 `shared-references/brain-loading.md` v1.6+ 規範載入大腦、透過

```
scripts/libs/brain_loader.load_for_skill("<operator>", "discovery")
```

取得 BrainBundle。必要欄位（`brand_md` / `cases_md`）缺失 → STOP。lessons 自動以 `stage == "soft"` 過濾、scope filter 對 discovery / generation。

| 欄位 | 必要 | 用途 |
|------|------|------|
| `brand_md` | ✅ | [4]/[5]/[6]/[10]/[11]/[12] 整份載入、跨 mode 都要 |
| `kai_md` | — | [1] 說話風格、選題切角對齊（A8 規範、待 brain_loader B1 接；loader 選用、缺檔則本項對齊降級）|
| `cases_md` | ✅ | [8] 案例庫、選題比對與切角推薦 |
| `performance_patterns` | ✅ | 高勝率 hook / 結構參考、信心分數計算 |
| `lessons` | — | scope=discovery 或 generation 的 soft lessons |

**外部 fetch（Wave C 待寫、tool 層不走本協議）**：
- `scripts/tools/web_fetch.py`（IG/TikTok/同業/熱點 fetch；目前 prompt-only fallback）
- `scripts/tools/research.py`（外部資料 fetch；原 topic-researcher v1.10 邏輯）
- `scripts/tools/trend.py`（Reels 解析；原 trend-adapter v1.20 邏輯）

### Lesson 使用標注（對應 workflow.md v2.10+ §對話中累積 evidence）

若本輪選題真的因某條 soft lesson 改寫 / 避開（如避踩 L0 紅線、避用 risk_pattern）、對話結尾一句話自然標注。有 VID 上下文時、Claude **使用 Bash tool 直接執行**：`video-ops.py lessons add-evidence L-XXXX --vid VID-NNN`、持久化 evidence。**禁止印命令給 Kai 看再等 Kai 觸發** — 同 v5.87 §Output Contract 動詞硬化、適用同樣 4.6 慣性退化、是 evidence 採用率 11.7%（4/34）的根因。

---

## Output 格式

```
🔍 Discovery 選題建議（mode=<week|month|trend>）：

【1】「<標題草稿 1>」（信心：高 ⚡）
  切角：<為什麼這個題、什麼觀眾、3 點切點>
  來源：📊 IG 熱點「XXX」+ brand.md [4] 核心論點 N 連結
  對齊 brand.md：[4]、[12]
  Hook 候選：D3 數字衝擊（過去類似題勝率 60%）

【2】「<標題草稿 2>」（信心：中）
  ...

【...】

說「拍 1」/「拍 2」→ 進 Generation Skill 拍對應選題
說「再來」→ 重新生成
說「不對、要更 XX 的」→ 調整 mode / 來源 / 信心門檻
```

---

## Output Contract（v1.4 §Learning Loop）

Discovery Skill 跑完輸出（給 pipeline.json）：

```json
{
  "discovery_trace": {
    "mode": "discover-week",
    "candidates_proposed": 7,
    "external_sources_used": ["IG", "competitor_X"],
    "kai_selected": ["candidate_3"],
    "completed_at": "2026-04-25T15:30:00Z"
  }
}
```

寫入 CLI 後續實作（Phase 5 配套）。

---

## 不負責

- ❌ 立即生成腳本（→ Generation Skill）
- ❌ 驗證選題品質（→ Quality Skill 不適用、選題層次不需 quality-loop）
- ❌ 擅自更新 brand.md（→ Distillation Skill 提建議、Kai 確認）
- ❌ 點名競品（red-line-protocol、brand.md [6] 紅線）

---

## 與其他核心 skill 的邊界

| Skill | 邊界 |
|-------|------|
| Orientation | task 開始時若是「找選題」類、走 Discovery；其他 task 不過 Discovery |
| Generation | Kai 從 Discovery 選定後、進 Generation 拍 |
| Quality | 不參與（Discovery output 是選題建議、不是 artifact）|
| Distillation | Discovery 過程揭露的新事實 → Distillation 提 brand 更新建議 |

---

## 合併歷史（lineage）

| 原 skill | v 號（退役前）| 落在 Discovery |
|----------|------------|--------------|
| topic-architect | v1.24 | Discovery 主體（從「萃取 50+ 選題」改「外部 + 內部交互、推薦 5-10 個 + 切角」、方向反轉）|
| trend-adapter | v1.20 | Wave C `scripts/tools/trend.py`（Reels 解析、待寫）|
| topic-researcher | v1.10 | Wave C `scripts/tools/research.py`（外部資料 fetch、待寫）|

退役歷程：v4.20（Phase 4、PR #295）topic-architect 升級為 Discovery 主體 + topic-researcher / trend-adapter 標 stub redirect → engine v5.42（Phase 5、本 PR）整刪 3 個目錄、tool 拆分留 Wave C 處理。

---

## ⚠️ Wave C 完成才完整 live

本 skill v1.1 **prompt-only fallback**、外部 fetch 部分用 Claude 自身知識補（不準、不即時）。

真正即時 fetch 需要 Wave C 三個 tool（規格待 Kai 拍板後另起 PR）：
- `scripts/tools/web_fetch.py`（IG/TikTok/同業/熱點 fetch）
- `scripts/tools/research.py`（外部資料 fetch、原 topic-researcher 邏輯）
- `scripts/tools/trend.py`（Reels 解析、原 trend-adapter 邏輯）

Wave C 後 Discovery Skill 才從 prompt-only 變成「真即時 + 大腦交互」。

**現狀（Wave A/B 完成後）**：Discovery Skill 框架到位、prompt-only 跑得起來、選題質量有限制（沒即時熱點）。

---

## 版本歷史

- **v1.0**（2026-04-25、engine v5.39）：prompt-only、3 modes、引用 topic-architect / topic-researcher / trend-adapter stub
- **v1.0**（2026-04-25、engine v5.42、Phase 5 真退役）：內容更新 — 3 個原 skill 整刪、邏輯內化、Wave C tools 待寫（不 bump 版本、變更詳見 engine v5.42 CHANGELOG）

未來：
- Wave C 後：integrate 3 個 tool、即時 fetch
- 進一步：與 Distillation Skill 互動（Discovery 揭露的新事實自動進 brand 更新候選）
