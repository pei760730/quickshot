# shared-references 總索引（SSoT 層級圖）

> version: 1.3 | last_updated: 2026-05-05
> 本檔目的：釐清共用規則的**SSoT 職責**與**升版順序**，避免升一份忘了同步另一份。
> v1.3：對齊 Phase 5/5b 退役後的 backlink — 修 data-brain-manifest 標註（v3.0 lint-driven 已落地）+ 修情境 6 失效鏈條（brain-interface / flow-operator 皆退役、公式 SSoT 在 persona-deviation-scoring.md）。

---

## 共用規則的角色（Phase 5 對齊 vNext 5 核心 skill）

| 檔案 | SSoT 職責 | 主要使用者 | 誰引用它 |
|------|----------|-----------|---------|
| `red-line-protocol.md` | **L0 紅線內容**（品牌禁區三層分級）| 所有生成型 skill 輸出前 | quality-gates（L0 層引用） |
| `banned-words.md` | **禁用詞黑名單**（輸出內容用語）| generation skill 5 modes + quality skill phase=fix | quality-gates（L1 引用）|
| `output-quality-rules.md` | **短文案 Q1-Q7 規則**（≤15 字輸出品質）| generation 短文案輸出 + quality phase=check | quality-gates（L1 短文案層引用） |
| `quality-gates.md` | **品質檢查流程**（Pipeline 執行順序 + 三層分級 L0/L1/L2 架構）| 整個生成→修正→驗證流程 | generation + quality skill |
| `performance-injection-protocol.md` | **表現模式注入規範**（proven/risk patterns 怎麼灌進生成）| generation skill 5 modes | 單向引用 skill、無反向 |
| `data-brain-manifest.md` | **Skill × brand.md section 依賴矩陣**（漂移偵測）| 大腦內容更新時的影響評估 | v3.0 lint-driven（Phase 5b 完成）— 矩陣由 `scripts/lint/brand_ref_lint.py --manifest` 自動推導、本檔降為設計說明 |
| `brain-loading.md` | **Stage 0 統一載入協議**（BrainBundle / filter 規則）| vNext 5 核心 skill 的 Step 0 | brain_loader.py 實作契約 |
| `ai-pattern-detection.md` | **24 AI patterns 掃描清單**（Phase 5 從 humanizer v1.28 抽出）| quality skill phase=fix | — |
| `persona-deviation-scoring.md` | **人設偏離度計分公式**（Phase 5 從 flow-operator v1.50 抽出）| generation skill 5 modes（dual-track/variant/series/interview）| — |
| `blood-bag-evaluation.md` | **血包三件套（A 段落驗證）**（Phase 5 從 interview-navigator/evals 抽出）| generation skill mode=interview | — |
| `templates/hook-templates.md` | **17 條 H/HD 三秒金句模板**（Phase 2 從 hook-killer 降級）| generation 短文案輸出 + quality phase=check | — |
| `title-rules.md` | **5 類心理觸發 + 5 條原則 + gotcha**（Phase 2 從 title-generator 降級）| generation 短文案輸出 + quality phase=check | personas/kai.md [1] 上游對齊 |
| `skill-design-principles.md` | **Skill 該不該存在 / 該長什麼樣的設計準則**（A/B/C/D/E/F 六準則） | 新增 / 重設計 skill 時的 Claude / Kai | CLAUDE.md 禁令 #12 + skill-architecture-principles.md |

---

## SSoT 層級（誰是誰的權威）

```
                     ┌─────────────────────────────────┐
                     │    quality-gates.md             │← 品質流程總指揮
                     │    （中央清冊 + 執行順序）         │
                     └───┬──────────────┬──────────────┘
                         │ 引用 L0 紅線  │ 引用 L1 短文案規則
                         ↓              ↓
              ┌────────────────────┐  ┌────────────────────┐
              │ red-line-protocol  │  │ output-quality-rules│
              │   （內容 SSoT）     │  │    （Q1-Q7 SSoT）    │
              └────────────────────┘  └──────────┬─────────┘
                                                  │ 引用禁用詞
                                                  ↓
                                        ┌────────────────────┐
                                        │ banned-words.md    │
                                        │   （黑名單 SSoT）   │
                                        └────────────────────┘
```

**平行規範**（不屬於品質流程，但共用）：
- `performance-injection-protocol.md` — 生成時注入邏輯
- `data-brain-manifest.md` — 大腦漂移偵測
- `brain-loading.md` — vNext 3 真 skill（discovery / generation / quality）的 Step 0 統一載入協議（對齊 `scripts/libs/brain_loader.py`）

---

## 升版順序（跨檔一致性原則）

當有規則變動時，依以下順序升版同步，避免中間狀態不一致：

### 情境 1：新增一個**紅線**（例：新品牌禁忌）
1. `red-line-protocol.md`（加條目、升版）
2. `quality-gates.md`（若影響 L0 分級定義，順便升版）
3. 相關 skill 的本地 Gotchas 段落（非必須，可指向 SSoT）

### 情境 2：新增一個**禁用詞**
1. `banned-words.md`（加詞、升版）
2. `output-quality-rules.md` 的 Q5 若有例舉，也升版
3. 不需改 quality-gates（它只引用 Q1-Q7 的檔案路徑，不內聯條目）

### 情境 3：改 **Q1-Q7 短文案規則**
1. `output-quality-rules.md`（升版）
2. `quality-gates.md`（若 L1 分級定義變動）
3. `quality/SKILL.md` phase=fix 短文案層段落（若本地有追加規則要對齊）

### 情境 4：改**品質檢查 Pipeline 流程**（例：pipeline 並行改序列）
1. `quality-gates.md`（升版）
2. 相關 skill 的 Process 段落（例：`generation` mode=dual-track 步驟 / `quality` phase=check 執行時機）
3. **不動** red-line / banned-words / output-quality（這些是「內容」，流程改不影響內容）

### 情境 5：改 **performance 注入門檻**（例：confidence 等級 ≥2 改 ≥3）
1. `performance-injection-protocol.md`（升版）
2. `docs/contracts/performance-patterns-schema.md`（若門檻數字也在 schema 定義，同步升版）
3. 不動 quality-gates

### 情境 6：改 **data-brain 欄位定義**
1. `docs/contracts/performance-patterns-schema.md`（patterns 欄位 SSoT；歷史背景：brain-interface v5.27 退役 → flow-operator v5.42 退役、公式 SSoT 現位於 `02-skill-factory/shared-references/persona-deviation-scoring.md`）
2. `data-brain-manifest.md`（v3.0 lint-driven、不再手寫矩陣；改 brand.md section 後跑 `python scripts/lint/brand_ref_lint.py --manifest` 確認）
3. 相關 skill 的 frontmatter `brand-refs:` 列表（lint 自動偵測 over/under-declared）

---

## 衝突解決優先級

當兩份檔案規則互相衝突時：

| 衝突類型 | 以誰為準 |
|---------|---------|
| red-line vs quality-gates | red-line 的**內容**、quality-gates 的**流程** |
| output-quality vs banned-words | 各管各的範圍（Q 規則 vs 黑名單）不會真衝突 |
| performance-injection vs quality-gates L1 | 若低信心 pattern 產出違反 L1 → L1 勝（信心不足不能繞過品質） |
| Skill 本地規則 vs shared-references | shared 勝，除非 skill 本地規則**更嚴格**（例：B 版紅線） |

---

## 本檔 vs `02-skill-factory/README.md` 的差別

| 面向 | shared-references/README.md（本檔） | 02-skill-factory/README.md |
|------|-----------------------------------|---------------------------|
| 範圍 | 只講 7 份共用規則的層級與升版 | 17 個 skill 的版本列表與調用方式 |
| 讀者 | 維護共用規則時的 Claude / Kai | 日常查 skill 版本時的 Kai |

---

## 變動此檔的時機

- 新增一份 shared-reference 檔案
- 任一份 SSoT 職責變動（例：從「內容」擴張到「流程 + 內容」）
- 升版順序實際踩雷需要修正

保持簡潔、不擴張成其他職責。
