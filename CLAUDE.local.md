# 龍OS — 客戶身份設定

> 此 repo 的品牌與操作員配置。短期客戶 template、不被引擎覆蓋。

## 身份

- **品牌**：龍OS
- **主要創作者 / 預設 operator**：longbro（Longbro）
- **額外 operator**（若有，逐行填）：

## 品牌速查

完整精華見 `01-data-brain/brand-summary.md`（每次對話由 SessionStart hook 自動注入 context）。
細節 brand.md 在 `01-data-brain/brand.md`。

## 使用者習慣（可選填）

<!--
溝通偏好、口氣要求、禁忌話題、以及任何「Claude 每次對話都該記得的個人化指示」寫在這裡。
範例：
- 我喜歡直接說結論，不用先鋪陳
- 回覆盡量短，超過 5 段我會覺得囉唆
- 我不喝酒，不要推薦酒類主題
-->

（暫未填寫 — 使用一段時間後再來記錄會更準）

---

## 為什麼有這個檔

`CLAUDE.md` 是引擎規則（禁令、資料地圖、操作原則）、適用所有短期客戶。
`CLAUDE.local.md` 是此 repo 獨有的身份設定，放品牌資訊 + 個人化習慣。

Claude Code 讀取順序：`CLAUDE.md`（引擎規則）→ `CLAUDE.local.md`（客戶特異），兩個都會進入對話 context。
