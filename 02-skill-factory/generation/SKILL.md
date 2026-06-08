---
name: generation
description: 內容生產核心 skill v1.4（vNext 5 核心之一） — 5 modes（dual-track / variant / series / interview / viral）整合於單一 skill。v1.4 §通用 Output 規格硬化：A/B/C/D 4 切角從 dual-track 專屬 → 跨所有 mode 強制 + 偏離度預算對應（A GREEN / B ORANGE / C/D YELLOW）；加 §強標題優先協議（每切角 ≥ 5 候選、依 title-rules.md 5 類心理觸發、4 必含逐項評分、⭐ 推薦、Hook 必 echo 推薦標題、不套 30s 默認）。保留前版 §Output Contract 動詞硬化（Bash tool 直接執行、禁止印命令給 Kai 抄、trace inline）。觸發：Kai 說「確認要拍：XXX」「變體」「拍系列」「訪談」「knowledge」或描述任務。
version: 1.4
last_updated: 2026-06-07
brand-refs: [5, 6]
---
<!-- vNext 5 核心 skill #2 — 對應 docs/references/skill-architecture-principles.md v1.3 §vNext 必要能力 C：變更設計 -->
<!-- engine v5.42 Phase 5 真退役：12 個退役 skill 目錄整刪、SSoT 段落遷至 shared-references/、本 skill 不再引用退役路徑（內容變更但不 bump 版本、避免 stub frontmatter 不同步）-->

# Generation Skill v1.4

> **本質能力 C**：變更設計（最小變更、可回收路徑、生成內容）
> **失敗模式**：F2（改錯範圍）+ F4（一次太大）
> **核心責任**：把 Orientation / Discovery 給的 spec 轉成具體變更（腳本 / 系列 / 變體 / 訪談 / 知識型）

---

## 觸發方式

| Kai 說 | Mode |
|-------|------|
| `確認要拍：[主題]` | mode=dual-track（預設）|
| `變體：[主題或 VID]` | mode=variant |
| `系列：[主題]` / `拍一組` | mode=series |
| `訪談：[主題]` / `interview` | mode=interview |
| `viral：[主題]` / `knowledge` | mode=viral（不綁大腦）|

Discovery Skill 推薦選題後、Kai 說「拍 N」→ Generation 自動以對應 mode 跑。

---

## 5 Modes

> **通用 Output 規格（v1.X+、跨所有 mode 強制）**
>
> 所有 mode 強制產出 **A/B/C/D 4 切角**（不再分版）、各切角有對應偏離度承受預算（per `shared-references/persona-deviation-scoring.md`）：
>
> | 切角 | 內容定位 | 偏離度預算 |
> |------|---------|----------|
> | **A** 保守版 | Kai 標準人設話術、不挑釁 | ≤ 3 GREEN |
> | **B** 強衝突版 | 自我打臉 / 自嘲 / 拉到挑釁上限 | ≤ 7-8 ORANGE |
> | **C** 揭密版 | 揭算盤 / 邏輯 / 行業內幕 | ≤ 4-6 YELLOW |
> | **D** 故事版 | 真實案例 / 大金額彈藥庫驅動 | ≤ 4-6 YELLOW |
>
> 每切角內依 mode 套對應 mode-specific 細節（見各 Mode N 段）。
>
> **強標題優先協議**（v1.X+、跨所有 mode 強制）：
> 0. 先定方向（per `shared-references/direction-principles.md` 心法 A）：這支戳中觀眾哪個沒說出口的恐懼／驅動？標題與 hook 都服務這個恐懼、不是服務「我想講什麼」。
> 1. 每切角產 ≥ 5 候選標題（依 `shared-references/title-rules.md` 5 類心理觸發 T1-T5、各 1-2 個）
> 2. 對每候選跑 `brand.md` [13] 4 必含逐項評分（具體金額 / 反差動作 / 第一人稱「我」/ 留缺口或問號）
> 3. 標 ⭐ 推薦最強（≥ 4/4 優先、不到時取觸發力最強、不純看分數）
> 4. **腳本 Hook 第一句必直接 echo 推薦標題、不另起爐灶**
> 5. 標題服務不到位 → 腳本不算合格、重生
>
> **秒數判斷**：除 mode=interview 明寫 30/45/60s 三版外、其他 mode 不套 30s 默認；秒數依切角內容自然決定（敘述/案例題材建議 60-90s）。

### Mode 1: dual-track（預設）

**Output**：A/B/C/D 4 切角獨白腳本（per 通用規格）+ 毒舌總結排序 + 偏離度計分。
**mode-specific**：自然秒數（內容決定）

**載入**：
- brand.md / cases.md / performance-patterns / lessons（filter scope=generation）
- 偏離度計分 SSoT：`shared-references/persona-deviation-scoring.md`

### Mode 2: variant

**Input**：主題 OR 現有腳本 OR VID
**Output**：A/B/C/D 4 切角變體（per 通用規格）、每切角含開場類型 + CTA 類型 + 推薦理由 + 素材來源 + 完整腳本 + 互動誘餌

**載入**：同 mode=dual-track。

### Mode 3: series

**Input**：主題（含集數 / 版本指定可選）
**Output**：4 集 = A/B/C/D 4 切角各 1 集（per 通用規格）、每集含標題 + 情緒值 + 功能 + 開場類型 + 片長 + 素材來源 + 完整腳本 + 互動誘餌
**特性**：含情緒曲線圖 + 推流時間表

**載入**：同 mode=dual-track。

### Mode 4: interview

**Input**：主題、適用對話壓力式
**Output**：A/B/C/D 4 切角 × 推薦秒數（30/45/60s 擇一、依切角內容決定）（per 通用規格）、Q 字卡 + A 爆點格式、每個 A 必含血包（數字 / 具象敵人 / 判詞金句 ≥2/3）

**載入**：同 mode=dual-track + `shared-references/blood-bag-evaluation.md`。若客戶有藏鏡人 / 對話搭檔人格、由 `01-data-brain/personas/{name}.md` 載入（template 不預設、客戶各自建）。

### Mode 5: viral

**Input**：主題、業內老手通用知識型
**Output**：知識型短影音腳本、反直覺句式（「你以為 A、其實 B」/「越 X 越 Y」）

**載入**：**跳過 brand.md / cases.md**（per brain-loading.md「不綁大腦」清單）、僅載入 lessons + banned-words。

---

## 模式選擇推理（Claude 自決）

依 task 性質：

```
task = 拍既有選題?
  → 單支?
    → mode=dual-track（預設）
  → 同題多角度?
    → mode=variant
  → 多集 (3-7)?
    → mode=series
  → 對話壓力 / Q&A?
    → mode=interview
  → 業內知識通用 (不特定品牌)?
    → mode=viral
```

Claude 觀察 Kai 講法 + brain_loader 載入結果、推理選 mode。錯了 Kai 會喊停、Claude 重選。

---

## 步驟 0：載入

依 `shared-references/brain-loading.md` v1.6+ + `data-brain-manifest.md` v3.0+ 規範載入大腦、透過

```
scripts/libs/brain_loader.load_for_skill("<operator>", "generation")
```

取得 BrainBundle。必要欄位（`brand_md` / `cases_md`）缺失 → STOP。lessons 自動以 `stage == "soft"` 過濾（SSoT 在 brain-loading.md §Lessons 過濾規則、不在本檔重寫）。

各 mode 取用範圍：

| Mode | brand.md | cases.md | performance-patterns | lessons | mode-specific reference |
|------|----------|----------|---------------------|---------|------------------------|
| dual-track | ✅ | ✅ | ✅ | ✅ | `shared-references/persona-deviation-scoring.md` |
| variant | ✅ | ✅ | ✅ | ✅ | 同 dual-track |
| series | ✅ | ✅ | ✅ | ✅ | 同 dual-track |
| interview | ✅ | ✅ | ✅ | ✅ | 同 dual-track + `shared-references/blood-bag-evaluation.md` |
| viral | **❌**（不綁）| **❌**（不綁）| 可選 | ✅ | — |

### Lesson 使用標注（對應 workflow.md v2.10+ §對話中累積 evidence）

若本輪生成真的因某條 soft lesson 改寫 / 避開、對話結尾一句話自然標注（例：「✓ 避開了 L-0023 的破折號殘留」）。有 VID 上下文時、Claude **使用 Bash tool 直接執行**：`video-ops.py lessons add-evidence L-XXXX --vid VID-NNN`、把 evidence 持久化到 lesson 的 evidence list（讓跨 session 反覆訊號可累積）。**禁止印命令給 Kai 看再等 Kai 觸發** — 同 §Output Contract §1 動詞硬化、適用同樣 4.6 慣性退化、是 evidence 採用率 11.7%（4/34）的根因。

---

## 共用協議

所有 modes 共用：

- `shared-references/direction-principles.md` v1.0+（方向心法：hook / 標題的第一性是「戳中觀眾哪個沒說出口的恐懼／驅動」、心法 A 是 title-rules 5 類心理觸發的上游動機）
- `shared-references/performance-injection-protocol.md` v2.0+（高勝率 hook / 結構注入）
- `shared-references/red-line-protocol.md` v2.1+（紅線檢查）
- `shared-references/banned-words.md` v1.0+（禁用詞）
- `shared-references/output-quality-rules.md` v1.0+（Q1-Q7 共用品質）

紅線（red-line-protocol）：
- 不點名競品（brand.md [6]）
- 不虛構數據大腦中沒有的內容（CLAUDE.md 禁令 #1）
- 不違反 brand.md [5] 禁忌

---

## Output Contract（v1.4 §Learning Loop、v1.3 動詞硬化）

Generation Skill 跑完輸出含 3 階段：**Bash tool 執行 save**（trace 直接 inline --trace arg）→ AI 自評 4 句（人話層、Kai 主視覺）→ 技術摘要（次要、Kai 要才展開）。任一缺 = task 沒完成。

> **v1.3 設計核心**：v1.1 加 CLI 強制、v1.2 把人話層升主視覺、trace 仍 0/30 over 30 days。讀現況發現根因在 §Output Contract 寫「呼叫 CLI」+ 印 Bash code block — 這格式 Claude 在對話中常解讀為「展示給 Kai 抄」（4.6 慣性「Claude = 顧問、不是執行者」）。v1.3 把動詞硬化為「Bash tool 執行」、移除 fenced JSON 中介層、trace 直接 inline 進 --trace arg、無「給 Claude 自己看的 fenced block」。詳見 `docs/references/skill-architecture-principles.md` v1.5 補注「機械擋下 ≠ 行為改變」第二層補正。

### 1. Bash tool 執行 save（首要、不印命令給 Kai）

腳本生成完、Claude **必使用 Bash tool 直接執行**以下命令、**禁止印 Bash code block 給 Kai 看再等 Kai 觸發**：

```bash
video-ops.py save VID-NNN \
  --script-path "<path>" --skill generation \
  --mode <dual-track|variant|series|interview|viral> \
  --title-type T? --hook-type B?/D? --version V? \
  --verifier-prediction high/normal/low \
  --trace "$(cat <<'JSON'
{
  "mode": "dual-track",
  "version_chosen": "B",
  "title_type": "T2",
  "hook_type": "B1",
  "verifier_prediction": "high",
  "brand_loaded": ["[3]", "[4]", "[6]"],
  "decisions": ["挑 B 因為 conflict_score 最高", "用 hook B1 因近期同類 win_rate 60%"]
}
JSON
)"
```

`_meta.trace_required_statuses = ["剪輯中", "已上線"]`、必填狀態下缺 `--trace` 即 exit 1（PR #367 CLI 強制）。

**為什麼這條最硬**（v1.3 核心修正）：
- v1.1/v1.2 寫「呼叫 CLI」是模糊動詞、Claude 對話中經常退化為「印 Bash code block 展示給 Kai」（4.6 慣性）。trace 0/30 的真實根因不在 CLI 強制、不在人話格式、在動詞模糊。
- v1.3 強制動詞為「**Bash tool 執行**」、無「印命令給 Kai 抄」中間層。
- trace JSON 用 heredoc inline 進 --trace arg、不在對話中印 fenced JSON block 給 Claude 自己看（移除 Claude → 自己 → CLI 的 3 段傳遞）。
- 違反 = task 沒完成、回頭重做。

### 2. AI 自評 4 句話（人話層、Kai 主視覺）

Bash 執行成功後、Claude **第一時間**在對話中印 4 句話「AI 自評」、這是 Kai 看到的主要回饋（自然語言、不是表格不是 JSON）：

```
─── AI 自評 ───
👍 [可以拍 / 建議重改 / 棄] [一句理由]
⚠️ [最弱那點 + 具體怎麼改]（無明顯弱點則省略）
💡 引用大腦：[N]論點 X、[M]案例 Y（讓 Kai 能驗證有沒有亂編）
📊 同類預測：[hook=X、近 N 支平均 retention=Y、conflict=Z]
```

**4 句話翻譯規則**（從生成決策映射）：

| 人話句 | 來源 | 翻譯邏輯 |
|--------|------|---------|
| 👍 結論 | Claude 自評 + verifier_prediction | high/normal → 可拍；low → 建議重改；違反紅線 → 棄 |
| ⚠️ 弱點 | Claude 對腳本最弱處的判斷 | 不講「鋪陳分數低」、講「鋪陳太平、改成 XX 更有畫面」|
| 💡 引用 | brand-refs / cases-refs（實際讀進來的） | 列具體 brand.md 第 [N] 節 / cases.md 第 N 案例（給 Kai 反查不虛構）|
| 📊 預測 | `adoption-stats` 同 hook_type filter | 用近 30 支同類數字、不用 trace 中的 `verifier_prediction: "high"` 套話 |

不輸出 4 句 = task 沒完成。

### 3. 技術摘要（次要、Kai 要才展開）

人話 4 句後、印一行可選展開的技術摘要、Kai 不關心可忽略：

```
（技術詳情：mode=dual-track / hook=B1 / title=T2 / version=B / 跑 `video-ops.py adoption-stats` 看完整趨勢）
```

### 4. 完成判定

3 階段全做才算「存檔」：
- Bash tool 執行 save 成功（§1、CLI exit 0）✓
- AI 自評 4 句話印出（§2）✓
- 技術摘要一行印出（§3）✓

任一缺、task 不算結束。

### 5. 反例（v1.3 禁止）

❌ **印 Bash code block 給 Kai 看、不直接 Bash tool 執行**：

> 存檔命令如下、Kai 你要不要跑？
> ```bash
> video-ops.py save VID-NNN --trace '...' ...
> ```

→ 違反 v1.3 §1、是 trace 0/30 採用閉環行為層失敗根因。「呼叫 CLI」在 Claude 4.6 慣性下退化為「展示命令給 Kai」、v1.3 強制為「Bash tool 執行」。

❌ **印 fenced JSON 給 Claude 自己看、再 Bash 抄進 --trace**：

> ```json
> {"mode": "...", "hook_type": "..."}
> ```

→ 違反 v1.3 §1、fenced JSON 中介層在 v1.3 移除、trace 用 heredoc inline 進 Bash arg。

❌ **跳過人話 4 句、直接印 CLI 結果**：

> ✓ 存檔 VID-NNN（mode=dual-track / hook=B1）

→ 違反 v1.3 §2、Kai 看完腳本要自己判斷可不可拍、回到「Claude 印機器訊息給 Kai」舊模式。

❌ **4 句人話寫成模板套話**：

> 👍 這支腳本符合品牌調性、可以拍攝

→ 違反 personas/kai.md [1]「無來源的形容詞」+ 沒提弱點 + 沒給 actionable，等於沒講。

❌ **跨 mode 用同一套 4 句模板**：
- mode=viral 不綁大腦、💡 引用大腦句改為 `💡 不綁大腦（業內通用知識型）`
- mode=interview 預測句改為 `📊 同類預測：訪談 30s/45s/60s 三版、選 N 秒`

---

## 不負責

- ❌ 找選題（→ Discovery Skill）
- ❌ 驗證 + 修腳本（→ Quality Skill）
- ❌ 寫 lesson / 升 hardened（→ Distillation Skill）
- ❌ 跨 mode 自動切換（一個 task 用一個 mode、不混用）

---

## 與其他核心 skill 的邊界

| Skill | 邊界 |
|-------|------|
| Orientation | 提供 task spec + mode 建議；Generation 按 spec 跑、不自決 task 範圍 |
| Discovery | 推薦選題；Generation 拿選題拍、不重新挑 |
| Quality | Generation 出 artifact、Quality 驗 + 修；Generation 不自驗 |
| Distillation | task 末讀 generation_trace、累積 evidence |

---

## 合併歷史（lineage）

5 modes 對應原 14 個 skill 中的 5 個（v1.0 之前各自獨立、v1.1 全部退役、邏輯內化於本 skill）：

| 原 skill | v 號（退役前）| 落在 Generation mode | SSoT 內容遷移目的地 |
|----------|------------|------------------|------------------|
| flow-operator | v1.50 | mode=dual-track | `shared-references/persona-deviation-scoring.md` |
| flow-maximizer | v1.55 | mode=variant | （邏輯整合於本檔）|
| series-engine | v1.36 | mode=series | （邏輯整合於本檔）|
| interview-navigator | v1.36 | mode=interview | `shared-references/blood-bag-evaluation.md` |
| viral-knowledge | v1.23 | mode=viral | （邏輯整合於本檔）|

退役歷程：v4.20（Phase 4、PR #295）降為 stub redirect → engine v5.42（Phase 5、本 PR）整刪目錄。

---

## 版本歷史

- **v1.0**（2026-04-25、engine v5.39）：5 modes 整合、保留各退役 skill 的 references / evals 為 mode reference（stub redirect 形態）
- **v1.0**（2026-04-25、engine v5.42、Phase 5 真退役）：內容更新 — 12 個退役目錄整刪、SSoT 段落遷至 shared-references/、本 skill 不再引用退役路徑（不 bump 版本、變更詳見 engine v5.42 CHANGELOG）
- **v1.1**（2026-04-29、engine v5.67）：§Output Contract 改 3 階段（對話 trace fenced JSON + CLI 寫入 + 即時回饋）。配 PR #367 CLI 強制、解採用閉環價值-成本不對稱（trace 0/61 → 目標 ≥ 50%、見 `docs/references/skill-architecture-principles.md` v1.5+）。
- **v1.2**（2026-04-30、engine v5.71）：§Output Contract 拆雙層 — AI 自評 4 句人話為 Kai 主視覺、fenced JSON / CLI 結果 / 技術摘要降為腳註。v1.1 解了「Claude 寫不寫 trace」、v1.2 解「Kai 看不看得懂」（採用閉環價值-成本不對稱的第二層 — 不只寫入成本、還有呈現格式 vs user 認知成本）。配 quality v1.2 同步雙層化。
- **v1.3**（2026-05-05、engine v5.87）：§Output Contract 動詞硬化 — 把「呼叫 CLI」+ 印 Bash code block 改為「**Bash tool 直接執行**、禁止印命令給 Kai 抄」、4 階段壓 3 階段、移除 fenced JSON 中介層、trace 直接 inline 進 --trace heredoc arg。解 trace 0/30 over 30 days 採用閉環行為層失敗（v1.1/v1.2 沒解到的「動詞模糊讓 Claude 4.6 慣性退化為顧問」根因）。配 quality v1.3 同步動詞硬化。對應 `docs/references/skill-architecture-principles.md` v1.5 補注「機械擋下 ≠ 行為改變」第二層補正。14 天觀察 metric：generation_trace 從 0/30 → 目標 ≥40%。
