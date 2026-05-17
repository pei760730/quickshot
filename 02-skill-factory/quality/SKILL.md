---
name: quality
description: 品質 + 修正核心 skill v1.3（vNext 5 核心之一） — 整合驗證 + 修正、quality-loop pattern。phase=check 跑 5 項驗證、phase=fix 去 AI 味 + 品牌人格注入。v1.3 §Output Contract 動詞硬化：把「呼叫 CLI」改為「**Bash tool 直接執行 record-verifier-scores**、禁止印命令給 Kai 抄」、解 verifier_scores 0/30 over 30 days 行為層失敗（根因在動詞模糊讓 Claude 4.6 慣性退化為顧問）。觸發：Generation 完後自動跑、或 Kai 說「驗證：[腳本]」「humanize：[腳本]」。
version: 1.3
last_updated: 2026-05-05
brand-refs: []
---
<!-- vNext 5 核心 skill #3 — 對應 docs/references/skill-architecture-principles.md v1.3 §vNext 必要能力 D：驗證定義 -->
<!-- engine v5.42 Phase 5 真退役：humanizer / script-verifier / hook-killer / title-generator 整刪、SSoT 段落遷至 shared-references/（內容變更但不 bump 版本、避免 stub frontmatter 不同步）-->

# Quality Skill v1.3

> **本質能力 D**：驗證定義（驗 + 修兩階段、產可信任 artifact + scores）
> **失敗模式**：F5（驗證不足 / 假完成）
> **核心責任**：把 Generation 給的 artifact 跑「驗 + 修」quality-loop、產 verifier_scores 與最終 artifact

---

## 觸發方式

### 自動觸發（pipeline 內）

Generation Skill 執行完畢 → Quality Skill 自動接著跑（phase=check 開始、需要時走 phase=fix → 再 check 一輪）。

### 主動觸發

| Kai 說 | Phase |
|-------|------|
| `驗證：[腳本]` | check only（不 fix）|
| `humanize：[腳本]` | fix only（不 check）|
| `品質檢查：[腳本]` | check + fix loop |

---

## quality-loop（v1.0 整合 pattern）

```
[Generation 輸出 artifact]
       ↓
phase=check: 5 項驗證
       ↓
   ┌── pass ──→ 結束、輸出 verifier_scores
   │
   └── fail ──→ phase=fix: 去 AI 味 + 品牌人格 + 對齊 personas/kai.md [1]
                ↓
                phase=check: 再驗一次（最多 2 round）
                ↓
                ├── 仍 fail → 走 Plan mode（per CLAUDE.md 禁令 #3.5「卡住重回」）
                └── pass → 結束
```

**最多 2 round**：避免無限 loop。連續 2 次 fail → 強制 Plan mode、Kai 介入。

---

## Phase: check（5 項驗證）

> 詳細 5 項規格見 `docs/contracts/skill-io-schema.md` v1.5 §Learning Loop Contract Payload 2 (`verifier_scores`)

| 項 | 內容 | 範圍 |
|---|------|------|
| **conflict_score** | 衝突感（張力強弱）| 0-10 |
| **retention_prediction** | 留存預測（高 / 中 / 低）| A/B/C |
| **ai_residue_count** | AI 味殘留（24 patterns 命中數）| ≥ 0 |
| **data_consistency** | 數據一致性（跟 brand.md 對齊）| true/false |
| **format_complete** | 格式完整性（必要 sections 齊備）| true/false |

**通過門檻**：
- conflict_score ≥ 6
- retention_prediction ∈ {A, B}
- ai_residue_count ≤ 2
- data_consistency = true
- format_complete = true

5 項全達 → pass。任一不達 → 觸發 phase=fix。

### 模式

- **full 模式**（預設、Hard Gate 用）：5 項全跑
- **fast 模式**（僅虛構攔截）：**有假閉環風險、不建議做為最終品管**。Hard Gate 位置必 full、否則拒絕

---

## Phase: fix（去 AI 味 + 品牌人格注入）

### 兩階段

1. **AI 痕跡掃描**（24 patterns）：見 `shared-references/ai-pattern-detection.md` v1.0+
2. **品牌人格注入**：對齊 `01-data-brain/personas/kai.md` [1] 說話風格 + `shared-references/title-rules.md` 部分原則

### 不改的核心訊息

- preserve_meaning = true（核心訊息不變）
- 只改：詞彙 / 句式 / 語氣 / 標點

---

## Templates 引用

| Template | 用途 | 在哪 |
|----------|------|------|
| Hook templates | 三秒金句 17 條 H/HD reference | `shared-references/templates/hook-templates.md` v1.0+ |
| Title rules | 5 類心理觸發 + 5 條原則 | `shared-references/title-rules.md` v1.0+ |
| Banned words | 禁用詞清單 | `shared-references/banned-words.md` v1.0+ |
| Output quality rules | Q1-Q7 共用品質規則 | `shared-references/output-quality-rules.md` v1.0+ |
| Red line protocol | 紅線檢查 | `shared-references/red-line-protocol.md` v2.1+ |

Quality Skill 跑時、依 task 性質載入適用 template。

---

## 步驟 0：載入

依 `shared-references/brain-loading.md` v1.6+ 規範載入大腦、透過

```
scripts/libs/brain_loader.load_for_skill("<operator>", "quality")
```

取得 BrainBundle。必要欄位（`brand_md` / `cases_md` / `banned_words`）缺失 → STOP。lessons 自動以 `stage == "soft"` 過濾（SSoT 在 brain-loading.md §Lessons 過濾規則、不在本檔重寫）。

| 欄位 | 必要 | 用途 |
|------|------|------|
| `brand_md` | ✅ | 商業禁忌 [5] + 品牌定位 [0] 等對齊 |
| `kai_md` | ✅ | [1] 說話風格 核心比對（A8 規範、待 brain_loader B1 接）|
| `cases_md` | ✅ | 故事追蹤 ④ 驗證 |
| `lessons` | ✅ | filter scope=quality 或 generation 的 soft lessons |
| `performance_patterns` | — | 留存預測 ② 比對（有就用、缺檔不阻斷）|
| `banned_words` | ✅ | phase=fix 短文案層引用 |

### Lesson 使用標注（對應 workflow.md v2.10+ §對話中累積 evidence）

若本輪 phase=check / phase=fix 真的因某條 soft lesson 改寫 / 避開、對話結尾一句話自然標注（例：「✓ 避開了 L-0023 的破折號殘留」）。有 VID 上下文時、Claude **使用 Bash tool 直接執行**：`video-ops.py lessons add-evidence L-XXXX --vid VID-NNN`、持久化 evidence。**禁止印命令給 Kai 看再等 Kai 觸發** — 同 §Output Contract §1 動詞硬化、適用同樣 4.6 慣性退化、是 evidence 採用率 11.7%（4/34）的根因。

---

## Output Contract（v1.4 §Learning Loop、v1.3 動詞硬化）

Quality Skill 跑完輸出含 3 階段：**Bash tool 執行 record-verifier-scores**（機器層）→ 體檢結果（人話層、Kai 主視覺）→ 技術詳情（次要、Kai 要才展開）。任一缺 = task 沒完成。

> **v1.3 設計核心**：v1.1 加 CLI、v1.2 把人話層升主視覺、verifier_scores 仍 0/30 over 30 days。讀現況發現根因在 §1 寫「呼叫 CLI」+ 印 Bash code block — 這格式 Claude 在對話中常解讀為「展示給 Kai 抄」（4.6 慣性「Claude = 顧問」）。v1.3 把動詞硬化為「Bash tool 執行」、移除「印命令給 Kai 抄」中介。詳見 `docs/references/skill-architecture-principles.md` v1.5 補注「機械擋下 ≠ 行為改變」第二層補正。

### 1. Bash tool 執行 record-verifier-scores（首要、不印命令給 Kai）

Quality phase=check 跑完、Claude **必使用 Bash tool 直接執行**以下命令、**禁止印 Bash code block 給 Kai 看再等 Kai 觸發**：

```bash
video-ops.py record-verifier-scores VID-NNN \
  --conflict-score N \
  --retention-prediction A/B/C \
  --ai-residue-count N \
  --data-consistency true/false \
  --format-complete true/false \
  --pass-count "N/5"
```

**為什麼這條最硬**（v1.3 核心修正）：
- v1.1/v1.2 寫「呼叫 CLI」是模糊動詞、Claude 對話中經常退化為「印 Bash code block 展示給 Kai」（4.6 慣性「Claude = 顧問、不是執行者」）。verifier_scores 0/30 的真實根因。
- v1.3 強制動詞為「**Bash tool 執行**」、無「印命令給 Kai 抄」中間層。
- 違反 = task 沒完成、回頭重做。

### 2. 體檢結果（v1.2 人話層、Kai 主視覺）

`record-verifier-scores` 寫入後、Claude **第一時間**在對話中印 4 句話的「體檢結果」、這是 Kai 看到的主要回饋：

```
─── 體檢結果 ───
👍 [可拍 / 建議重改 / 拒收]、[一句總結為什麼]
⚠️ [最弱那項 + 具體怎麼改]（5 項全過則省略此行）
💡 引用大腦：[N]論點 X、[M]案例 Y（讓 Kai 能驗證有沒有亂編）
📊 同類預測：[hook=X、近 N 支平均 retention=Y、conflict=Z]
```

**4 句話翻譯規則**（從 6 欄位映射）：

| 人話句 | 來源欄位 | 翻譯邏輯 |
|--------|----------|---------|
| 👍 結論 | `pass_count` | 5/5 → 可拍；4/5 → 可拍但有弱點；≤ 3/5 → 建議重改；`data_consistency=false` 強制 → 拒收 |
| ⚠️ 弱點 | 不達標的那一項 | 多項不達 → 只講最弱那一項、具體 actionable（不是「ai_residue=2」、是「鉤子有破折號殘留、改成短句」）|
| 💡 引用 | brand-refs / cases-refs | 列實際引用的 brand.md / cases.md 條目（讓 Kai 一眼驗證沒虛構）|
| 📊 預測 | `adoption-stats` 同 hook_type filter | 用近 30 支同類平均對比、不是空泛「MID」|

### 3. 技術詳情（v1.2 次要、Kai 要才展開）

人話層後、印一行可選展開的技術摘要、Kai 不關心可忽略：

```
（技術詳情：pass=4/5 / conflict=7 / retention=B / ai_residue=1 / 跑 `video-ops.py adoption-stats` 看完整趨勢）
```

**為什麼放這裡而不是當主視覺**：6 欄位數字對 Kai 沒有 actionable value（看到 `conflict=7` 不知道要不要改）、但累積到 pipeline.json 後對 `adoption-stats` 有分析價值。把它從「對話主體」降為「技術腳註」、Kai 不必學任何術語、自然採用率就起來。詳見 `docs/references/skill-architecture-principles.md` v1.5+ §採用閉環價值-成本不對稱（v1.2 補正：成本不對稱不是只有「寫不寫」、還有「呈現格式對不對 user」）。

### 4. 完成判定

3 階段全做才算 done：
- CLI `record-verifier-scores` 成功 ✓
- 體檢結果 4 句話印出（人話層）✓
- 技術詳情一行印出（可被 Kai 忽略、但要存在）✓

任一缺、task 不算結束。

### 5. 反例（v1.3 禁止）

❌ **印 Bash code block 給 Kai 看、不直接 Bash tool 執行**：

> 驗證命令如下、Kai 我可以跑嗎？
> ```bash
> video-ops.py record-verifier-scores VID-NNN ...
> ```

→ 違反 v1.3 §1、是 verifier_scores 0/30 採用閉環行為層失敗根因（同 generation v1.3）。「呼叫 CLI」在 Claude 4.6 慣性下退化為「展示命令給 Kai」、v1.3 強制為「Bash tool 執行」。

❌ **只印技術數字、不印人話 4 句**：

> ✓ 驗證 VID-NNN（pass=4/5 / conflict=7 / retention=B / ai_residue=1）

→ 違反 v1.3 §2、Kai 看不懂要不要改、回到「Claude 印機器訊息給 Kai」舊模式。

❌ **人話 4 句寫成模板套話**：

> 👍 這支腳本品質不錯、可以考慮拍攝

→ 違反 personas/kai.md [1]「無來源的形容詞」+ 沒提弱點 + 沒給 actionable，等於沒講。

---

## 不負責

- ❌ 生成新內容（→ Generation）
- ❌ 找選題（→ Discovery）
- ❌ 寫 lesson / 升 hardened（→ Distillation）
- ❌ Hard Gate 用 fast 模式（紅線、會 reject）

---

## 與其他核心 skill 的邊界

| Skill | 邊界 |
|-------|------|
| Generation | 生成 artifact、傳給 Quality；Quality 不重新生成 |
| Quality | 驗 + 修；不對 artifact 結構性改寫（那是 Generation 的事）|
| Distillation | task 末讀 verifier_scores 異常 → 候選 evidence |
| Orientation | 先決定 verification 標準；Quality 按標準跑 |
| Discovery | 不參與 Quality（Discovery 的 output = 選題建議、不是 artifact）|

---

## 合併歷史（lineage）

| 原 skill | v 號（退役前）| 落在 Quality phase | SSoT 內容遷移目的地 |
|----------|------------|------------------|------------------|
| humanizer | v1.28 | phase=fix | `shared-references/ai-pattern-detection.md`（24 patterns）|
| script-verifier | v1.15 | phase=check | （5 項規格在 `docs/contracts/skill-io-schema.md`）|
| hook-killer | v3.0 | template 引用 | `shared-references/templates/hook-templates.md` |
| title-generator | v3.0 | template + lint | `shared-references/title-rules.md` |

退役歷程：v4.20（Phase 4、PR #295）降為 stub redirect → engine v5.42（Phase 5、本 PR）整刪目錄。

合併後 Quality Skill 內部 quality-loop pattern（check ↔ fix）取代「兩個獨立 skill 串接」、減少邊界模糊。

---

## 版本歷史

- **v1.0**（2026-04-25、engine v5.39）：5 項 verification + quality-loop 整合、24 patterns 引用 humanizer/references stub 路徑
- **v1.0**（2026-04-25、engine v5.42、Phase 5 真退役）：內容更新 — 24 patterns SSoT 遷至 `shared-references/ai-pattern-detection.md`、不再引用退役路徑（不 bump 版本、變更詳見 engine v5.42 CHANGELOG）
- **v1.1**（2026-04-29、engine v5.67）：§Output Contract 改 2 階段（CLI 寫入 + 即時回饋）。配 PR #367 adoption-stats CLI、解 verifier_scores 0/61 採用閉環失敗（見 `docs/references/skill-architecture-principles.md` v1.5+）。
- **v1.2**（2026-04-30、engine v5.71）：§Output Contract 拆雙層 — 體檢結果 4 句人話為 Kai 主視覺、技術數字降為腳註。v1.1 解了「Claude 寫不寫」、v1.2 解「Kai 看不看得懂」（採用閉環價值-成本不對稱的第二層 — 不只寫入成本、還有呈現格式 vs user 認知成本）。
- **v1.3**（2026-05-05、engine v5.87）：§Output Contract §1 動詞硬化 — 把「呼叫 CLI」+ 印 Bash code block 改為「**Bash tool 直接執行**、禁止印命令給 Kai 抄」、§5 反例新增 anti-pattern「印命令展示給 Kai」。解 verifier_scores 0/30 over 30 days 採用閉環行為層失敗（v1.1/v1.2 沒解到的「動詞模糊讓 Claude 4.6 慣性退化為顧問」根因）。配 generation v1.3 同步動詞硬化。對應 `docs/references/skill-architecture-principles.md` v1.5 補注「機械擋下 ≠ 行為改變」第二層補正。14 天觀察 metric：verifier_scores 從 0/30 → 目標 ≥40%。

未來：依 P1 reading loop（v1.1 死角 #1）整合 case-based retrieval、verifier 預測校準靠累積數據。24 patterns 將來可變 lint（依準則 B）。
