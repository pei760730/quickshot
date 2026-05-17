# {{BRAND_NAME}} — 客戶身份設定

> 此 repo 的品牌與操作員配置。**sync-engine 永不覆蓋此檔**。
> 初始化自引擎 {{ENGINE_VERSION}}（{{INIT_DATE}}）

## 身份

- **品牌**：{{BRAND_NAME}}
- **主要創作者 / 預設 operator**：{{OPERATOR_KEY}}（{{OPERATOR_LABEL}}）
- **額外 operator**（若有，逐行填）：

## 品牌速查

`01-data-brain/brand.md` 改 lazy load（v4.62 全文 auto-inject 退役、每 session 省 ~27k token baseline）：

- **skill 跑時**：透過 `scripts/libs/brain_loader.load_for_skill()` 自動載入（見 `02-skill-factory/shared-references/brain-loading.md` v1.5+）
- **對話中**：隨口提品牌事實 / Claude 需 brand context 推理 → Claude 主動 `Read 01-data-brain/brand.md`（單次載入、僅該對話）
- **session-start hook**：不再 cat 全文、只印 1 行提示
- **CLAUDE.local.md 已含的識別資訊**（品牌名 / operator / forbidden_terms）每 session auto-load、身份識別不受影響

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

## 跨 repo 自主推進共識（v4.58 sync-engine v2）

此 repo 的 Claude 使用 `/sync-engine`（或 `/sync`、`同步`）時走 auto 模式：

### 自主邊界
- **Kai 觸發第一下**：SessionStart hook 提示 engine 落後（第 7 類）時、等 Kai 說「同步」才執行
- **auto 模式自動完成**：fetch → diff → 污染掃描 → 覆蓋 → 驗證 → push → PR → monitor CI → 滿足門檻 admin merge
- **門檻預設**：CI 全綠 + diff < 20 檔 + 無污染 → auto admin merge；否則停等 Kai 看 PR
- **可調整**：`.claude/settings.local.json` 的 `sync_engine.auto_merge_diff_threshold`

### CI 紅 → 依分類表（見 `.claude/commands/sync-engine.md` Q3）
- 引擎層問題（engine_version_check / pytest 停 scripts/） → 停、產提示詞給 Kai 貼主引擎 repo
- 客戶層小問題（tests/*.py CHANGELOG 漏改） → surgical fix 限 5 行
- 其他 → 停、貼完整 output、不猜

### 絕不做
- 改引擎層檔（`scripts/`、`.claude/`、`docs/contracts/`）
- force push main
- merge 到主引擎 repo
- 擴 MCP 雙 repo 授權（Kai 已拍：不擴）

### 通道
- 同步方向：主引擎 repo → 本 repo（WebFetch public raw、單向）
- 回報方向：本 repo → 主引擎 repo = 透過 PR body（當 mailbox）、Kai 轉貼

> 此段為 v4.58 引入、客戶可按需改寫。blacklist 保護、`/sync-engine` 永不覆蓋此檔。

---

## 為什麼有這個檔

`CLAUDE.md` 是所有客戶共用的引擎規則（禁令、資料地圖、操作原則），被 `sync-engine` 同步時會**覆寫**。
`CLAUDE.local.md` 是此 repo 獨有的身份設定，**不會被 sync-engine 覆蓋**，你可以放心寫入客戶專屬資訊。

Claude Code 讀取順序：`CLAUDE.md`（引擎規則）→ `CLAUDE.local.md`（客戶特異），兩個都會進入對話 context。
