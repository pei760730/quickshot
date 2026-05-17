# AI 痕跡掃描（24 patterns）

> version: 1.0 | last_updated: 2026-04-25
> 從 humanizer v1.28 抽出。Phase 5 退役 humanizer 後改放此處。
> 下游 skill：`quality/SKILL.md` phase=fix。

## 用法

掃描全文、對照下方 24 patterns 標記觸發項。**中文腳本跳過 #16、#18**；#13、#15 需判斷語境（見「中文適用性」）。

來源：Wikipedia:Signs of AI writing（WikiProject AI Cleanup）

## Content Patterns

| # | 名稱 | Watch words / 線索 | 問題 |
|---|------|-------------------|------|
| 1 | Undue Emphasis on Significance | testament, pivotal, enduring, evolving landscape, indelible mark, key turning point, setting the stage | 用誇張辭彙膨脹重要性 |
| 2 | Notability & Media Coverage | independent coverage, leading expert, active social media presence, cited in NYT/BBC | 列媒體名單無脈絡地宣稱「被認可」 |
| 3 | Superficial -ing Analyses | highlighting, underscoring, emphasizing, reflecting, contributing to, cultivating, showcasing | 用 -ing 子句假裝有深度 |
| 4 | Promotional Language | boasts, vibrant, rich, nestled, in the heart of, groundbreaking, breathtaking, must-visit, stunning | 觀光簡介腔，失去中立 |
| 5 | Vague Attributions | industry reports, observers have cited, experts argue, some critics argue | 把意見歸給模糊的權威 |
| 6 | Challenges & Future Prospects | despite its challenges, despite these challenges, future outlook | 公式化的「挑戰與展望」段 |

## Language & Grammar

| # | 名稱 | Watch words / 線索 | 問題 |
|---|------|-------------------|------|
| 7 | AI Vocabulary | additionally, delve, emphasizing, fostering, interplay, intricate, key, landscape, pivotal, showcase, tapestry, testament, underscore, vibrant | 2023 後暴增的 AI 高頻詞 |
| 8 | Copula Avoidance | serves as, stands as, marks, represents, boasts, features, offers | 用累贅結構取代 is/are |
| 9 | Negative Parallelisms | not only…but…, it's not just X, it's Y | 過度使用對比句式 |
| 10 | Rule of Three | A, B, and C 的三元組；三個形容詞連發 | 硬湊三個以顯全面 |
| 11 | Elegant Variation | 同一主語用三四個同義詞輪替 | repetition-penalty 造成的同義詞循環 |
| 12 | False Ranges | from X to Y 但 X Y 不在同一尺度 | 假裝講了大範圍 |

## Style Patterns

| # | 名稱 | Watch words / 線索 | 問題 |
|---|------|-------------------|------|
| 13 | Em Dash Overuse | — 過多 | 模仿銷售文的「punchy」斷句 |
| 14 | Boldface 機械式使用 | 每行都粗體 | 強調失焦 |
| 15 | Inline-Header Vertical Lists | - **Header:** 說明文字 | 清單假結構 |
| 16 | Title Case Headings | Strategic Negotiations And Global Partnerships | 標題詞詞大寫（中文跳過） |
| 17 | Emojis | 🚀💡✅ 開頭的 bullet | 機械式 emoji 裝飾 |
| 18 | Curly Quotes | `"..."` vs `"..."` | 中文跳過 |

## Communication Patterns

| # | 名稱 | Watch words / 線索 | 問題 |
|---|------|-------------------|------|
| 19 | Chatbot Artifacts | I hope this helps, Of course!, Certainly!, Let me know, Here is a… | 對話殘留被貼成內容 |
| 20 | Knowledge-Cutoff Disclaimers | as of [date], up to my last training update, while specific details are limited | 訓練時間免責聲明殘留 |
| 21 | Sycophantic Tone | Great question! You're absolutely right! That's an excellent point | 人情討好腔 |

## Filler & Hedging

| # | 名稱 | Watch words / 線索 | 問題 |
|---|------|-------------------|------|
| 22 | Filler Phrases | in order to, due to the fact that, at this point in time, has the ability to, it is important to note | 贅字 |
| 23 | Excessive Hedging | could potentially possibly, might have some effect | 過度保守修飾 |
| 24 | Generic Positive Conclusions | the future looks bright, exciting times lie ahead, a step in the right direction | 空泛正向收尾 |

## 中文適用性

24 patterns 源自英文 Wikipedia。用於中文口語腳本時：

**完全適用（直接掃描）**：#1 #2 #3 #4 #5 #6 #9 #10 #11 #12 #19 #20 #21 #22 #23 #24
— 這些 pattern 的中文版同樣常見（如「值得一提的是」「不僅…更…」「展現了…的重要性」）

**需要調整**：
- **#7** 中文 AI 高頻詞對照表：**此外、值得注意的是、不僅…更…、至關重要、深入探討、致力於、彰顯、賦能、與此同時、打造、賦予、構建、彰顯、拓展**
- **#13** em dash：中文「——」可用於口語戲劇停頓，不一律刪除
- **#14** boldface：**Kai 風格常用粗體強調關鍵字**，保留「有意義的強調」，只刪機械式粗體
- **#15** vertical lists：中文腳本本身分段，不像英文常見粗體 header + colon
- **#16 #18**：中文不適用，跳過

**特別注意**：先讀 `01-data-brain/personas/kai.md` [1] 的高頻詞彙和口頭禪，Kai 語氣詞不算 AI 味。

## 歷史

- 24 patterns 與「Voice and Soul」品牌人格注入流程歷史上由 `humanizer` skill v1.28 維護
- engine v5.42 退役 `humanizer`、清單遷至本檔為 SSoT
- 將來可考慮升為 lint（依準則 B、`02-skill-factory/shared-references/skill-design-principles.md`）
