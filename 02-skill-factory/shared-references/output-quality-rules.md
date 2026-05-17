# 輸出品質規則（所有短文案型 Skills 統一）

> version: 1.1 | last_updated: 2026-04-25
> 適用對象：generation skill（5 modes）+ quality skill（短文案 ≤ 15 字檢查）+ shared-references/title-rules.md / hook-templates.md 引用
> 自動執行，未通過的自動重寫，不輸出檢查過程。

---

## 共用規則（7 條）

每條輸出文案必須全部通過：

| # | 規則 | 說明 |
|---|------|------|
| Q1 | ≤ 15 字 | 封面/金句超過 15 字點擊率斷崖下降。只算中文字 + 數字，標點不算 |
| Q2 | 口語化 | 像人說話，不像文章標題 |
| Q3 | 資訊缺口 | 給一半藏一半，讓人不點/不看會癢 |
| Q4 | 具體 > 模糊 | 有數字、有場景、有人物，不要抽象 |
| Q5 | 無禁用詞 | 檢查 `banned-words.md` |
| Q6 | 無 AI 味 | 不用破折號、不用三段式、不用「揭秘」「盤點」「必看」「震驚」等氾濫詞 |
| Q7 | 不是問句 | 封面/金句是勾引不是提問，禁止問號結尾 |

## 禁止清單

- ❌ 超過 15 字
- ❌ 問號結尾
- ❌ 「你知道嗎」「一定要看」「不看後悔」等廉價鉤子
- ❌ 「揭秘」「盤點」「必看」「震驚」等氾濫詞
- ❌ 完整句子（封面/金句是碎片，不是文章）
- ❌ 把所有資訊說完（留缺口才有點擊）
- ❌ AI 味重的排比、破折號、三段式

## Skill 專屬追加

各 skill 可在共用規則之外追加本地規則、寫在各 SKILL.md 的品質檢查段落：

| 對應 | 追加規則 |
|------|---------|
| 三秒金句（hook-templates.md 引用）| 不與封面標題語意重複（見前置檢查「避撞封面標題」）|
| 封面標題（title-rules.md 引用）| （目前無追加）|

---

## 與其他品質機制的分工

| 機制 | 職責 | 適用對象 |
|------|------|---------|
| **本規則** | 短文案品質（≤ 15 字的標題/金句） | generation skill 短文案輸出 + quality skill phase=check |
| `banned-words.md` | 禁用詞黑名單（全文案通用） | 所有生成型 skill |
| `red-line-protocol.md` | 品牌紅線三層分級 | 所有生成型 skill |
| `quality-gates.md` | 長文案共用品質檢查（語氣/素材/故事/人設） | generation skill 5 modes + quality skill phase=check |
| `ai-pattern-detection.md`（24 patterns） | AI 痕跡修正 | quality skill phase=fix |
| Verifier 5 項 | 最終品質驗證 | quality skill phase=check（存檔前）|
