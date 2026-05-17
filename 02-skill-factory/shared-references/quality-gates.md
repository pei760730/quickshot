# 品質責任矩陣（統一版）

> version: 3.0 | last_updated: 2026-05-05
> 本檔案是品質**流程**的中央清冊（三層分級 + Pipeline 執行順序）。規則衝突時以本檔分級為準。
> **內容 SSoT** 分散在其他檔（紅線 → red-line-protocol、禁用詞 → banned-words、Q1-Q7 → output-quality-rules），見 `shared-references/README.md` SSoT 層級圖。
> 自動執行，全部通過 → 不顯示。有問題才顯示 ⚠️。
> v3.0：對齊 Phase 5 退役 — 流程主述名從 4 個獨立 skill（humanizer / hook-killer / script-verifier / title-generator）改為 `quality` skill 的 phase=check / phase=fix 雙階段。SSoT 內容已遷至 `shared-references/{ai-pattern-detection, hook-templates, title-rules}.md`、流程不變、敘述對齊。

---

## 執行順序（Pipeline 模式）

```
生成（generation）→ [L0 紅線] → [L1 共用品質] → quality phase=fix → quality phase=check [L1+L2] → 存檔
```

`generation` skill 完成腳本後 → `quality` skill 自動接：先跑 `phase=fix`（去 AI 味 + 品牌人格注入 + 短文案品質）、再跑 `phase=check`（5 項驗證做最終仲裁）。`phase=fix` 內部串行：長文去 AI 味 → 短文案（金句 / 標題）讀處理後版本生成。`phase=check` 為最終仲裁者、在 `phase=fix` 全部完成後才執行。

| 階段 | 負責者 | 檢查什麼 | 時機 |
|------|--------|---------|------|
| 1. 生成時 | `generation` skill 5 modes | L0 紅線 + L1 共用品質 | 生成當下 |
| 2. AI 味修正 | `quality` phase=fix（SSoT：`ai-pattern-detection.md` 24 patterns） | AI 痕跡掃描 + 品牌人格注入 | 生成後 |
| 3. 短文案品質 | `quality` phase=fix（SSoT：`title-rules.md` + `hook-templates.md`） | L1 短文案規則（Q1-Q7） | 去 AI 味後（短文案讀處理後版本）|
| 4. 最終驗證 | `quality` phase=check（5 項檢查） | L1 驗證 + L2 品質追蹤 | 存檔前（2+3 完成後） |

---

## 規則分級

### L0：觸碰即淘汰（重寫該段，不可只標記）

> 來源：`red-line-protocol.md`（SSoT）

| 規則 | 來源模組 | 處理 |
|------|---------|------|
| 違反不可妥協原則 | brand.md [0]+[5] | 重寫 |
| 違反品牌不能做的事 | brand.md [0]+[1] | 重寫 |
| 攻擊目標客群 | brand.md [2] | 重寫 |
| 使用「絕對不會說的話」 | personas/kai.md [1] | 標記 ⚠️ + 建議修改 |
| 觸碰刻意迴避話題 | brand.md [5] | 標記 ⚠️ + 建議修改 |
| 虛構數據大腦中不存在的內容 | quality phase=check ④ | 必須修改 |
| 引用不存在的案例 ID（如 `[8] 案例 N` 但 cases.md 無此案例） | quality phase=check ④ | 必須修改 |

### L1：必須通過（未通過自動重寫或標記）

**共用品質（所有生成型 Skill）**

| 規則 | 標準 | 檢查者 |
|------|------|--------|
| 語氣 | 符合 personas/kai.md [1]，不說教、不雞湯 | 生成時 + quality phase=fix |
| 素材來源 | 每段標註引用的數據大腦模組 | 生成時 |
| 故事追蹤 | 所有故事來自 [8] 或 [12] | 生成時 + quality phase=check ④ |
| 人設一致 | 全程 Kai 視角，不跳出人設 | 生成時 |
| 迴避 risk_patterns | 未使用已知失敗模式 | 生成時 |
| 無禁用詞 | `banned-words.md` 清單 | 生成時 + quality phase=fix |
| 無 AI 味 | `ai-pattern-detection.md` 24 patterns（SSoT） | quality phase=fix + quality phase=check ③ |

**短文案規則（quality phase=fix 短文案層、引用 `title-rules.md` + `hook-templates.md`）**

> 來源：`output-quality-rules.md`（SSoT）

| 規則 | 標準 |
|------|------|
| Q1 ≤ 15 字 | 只算中文字 + 數字，標點不算 |
| Q2 口語化 | 像人說話 |
| Q3 資訊缺口 | 給一半藏一半 |
| Q4 具體 > 模糊 | 有數字、場景、人物 |
| Q5 無禁用詞 | banned-words.md |
| Q6 無 AI 味 | 不用破折號、三段式、氾濫詞 |
| Q7 不是問句 | 禁止問號結尾 |

**quality phase=check 5 項檢查**

| 檢查 | 層級 | 說明 |
|------|------|------|
| ① 衝突感評分 | L1 | 0-10 分，≤4 建議修改 |
| ② 留存預測 | L1 | 比對 performance-patterns.json |
| ③ AI 味殘留 | L1 | 二次掃描，phase=fix 漏網 |
| ④ 數據一致性 | L0+L1 | 虛構=L0，不確定=L1 |
| ⑤ 格式完整性 | L1 | metadata/畫面/CTA/時長 |

### L2：僅提醒（不阻塞，供參考）

| 規則 | 說明 |
|------|------|
| 灰色地帶強制站隊 | red-line-protocol 第三層 |
| 價值立場矛盾 | red-line-protocol 第三層 |
| 語氣不符但不嚴重 | red-line-protocol 第三層 |
| 非數據大腦素材 | 提醒 Kai 拍攝時用自己的話講 |
| 表現模式比對無匹配 | quality phase=check ② 不扣分 |

---

## 衝突解決

| 情境 | 規則 |
|------|------|
| L0 和 L1 衝突 | L0 優先（重寫） |
| Skill 本地規則和共用規則衝突 | 共用規則優先，除非本地規則更嚴格 |
| quality phase=fix 修改 vs phase=check 判定 | phase=check 為最終仲裁者 |
| 品管模式（嚴格/快速）影響 | 見 `quality/SKILL.md` 品管模式段落 |

---

## Skill 專屬追加

各 Skill 可在上述共用規則之外追加本地檢查，寫在各 SKILL.md 的品質檢查段落：

| Skill / phase | 追加規則 | 路徑 |
|--------------|---------|------|
| `quality` phase=fix（短文案層）| 三秒金句不與封面標題語意重複 | `templates/hook-templates.md` |
| `generation` mode=dual-track | 人設偏離度 ≤ 版本上限（A≤3, B≤8, C:4-6, D≤5） | `persona-deviation-scoring.md` |
| `quality` phase=check | 快速模式跳過完整驗證，僅保留 ④ 虛構攔截 | `quality/SKILL.md` 品管模式段落 |

---

## 子文件索引

| 文件 | 職責 | 關係 |
|------|------|------|
| `red-line-protocol.md` | L0 紅線定義（SSoT） | 本矩陣引用 |
| `output-quality-rules.md` | 短文案 Q1-Q7 規則（SSoT） | 本矩陣引用 |
| `banned-words.md` | 禁用詞黑名單（SSoT） | 被 L1 共用品質引用 |
| `performance-injection-protocol.md` | 表現模式注入方式 | quality phase=check ② 引用 |
| `02-skill-factory/quality/SKILL.md` | 5 項最終檢查（quality phase=check 流程 SSoT） | 本矩陣引用 |
| `ai-pattern-detection.md` | 24 AI patterns（SSoT、Phase 5 從 humanizer v1.28 抽出） | 本矩陣引用 |
| `templates/hook-templates.md` | 17 條 H/HD 三秒金句模板（Phase 2 從 hook-killer 降級）| 短文案層引用 |
| `title-rules.md` | 5 類心理觸發 + 5 條原則（Phase 2 從 title-generator 降級）| 短文案層引用 |
