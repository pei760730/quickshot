# 龍OS — 客戶身份設定

> 此 repo 的品牌與操作員配置。**sync-engine 永不覆蓋此檔**。
> 初始化自引擎 v4.53（2026-04-22）

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

## 自主推進共識（v4.53+、本 repo 為引擎範本驗證場）

LONGBRO 定位是「客戶隔離架構驗證」、非真實上線案。Kai × Claude 互動降至最少訊息數、6 條拍板：

**Q1. `/sync` 預設 auto** — 觸發詞 `/sync-engine` / `/sync` / `同步` 任一、走 fetch → sync → 驗 → push PR → Monitor CI → Q2 判斷。保守 `/sync pause`、預覽 `/sync dry`。

**Q2. Auto merge 門檻** — CI 全綠 + 無污染殘留 + diff < 20 檔 → admin merge + 切 main + 刪 branch。超出 → 停、貼 PR body 給 Kai。閾值在 `.claude/settings.local.json` 的 `sync_engine.auto_merge_diff_threshold` 覆寫。

**Q3. CI 紅自動分類** —
- `engine_version_check` / `scripts/ops/lib/` traceback → 引擎層、停、產提示詞
- `rules-lint` 只 warn → 忽略
- `validate-all` schema drift breaking → 引擎層、停
- 僅 `tests/*.py` + 明確對應 CHANGELOG 分類原則漏改 → 客戶層 surgical（≤ 1 檔 ≤ 5 行）+ commit msg 要求 engine 下版照修
- 其他 → 停、完整 output 給 Kai

**Q4. Engine-lag hook** — `.claude/hooks/session-start.sh` 開頭 fetch + 比版本、落後印 `🔄 engine 落後 v{LOCAL} → v{REMOTE}（說「同步」拉）`。不自動 sync、Kai 主動推才乾淨。

**Q5. Sync 污染掃描** — 掃 `紅茶巴士 / Red Tea Bus / 800 杯 / 129.8 萬 / 楷哥 / 阿檸` 在 `01-data-brain/*.md`（除 `index.md`）、`00-control-center/*.md`、`CLAUDE.local.md`。命中 → 列批次 approve；無 → silent。

**Q6. 永遠追隨主引擎、不做客製分支（2026-04-27）** —
- Path A 永遠優先：每次 sync 與主引擎 vNext 完全對齊、不保留客戶側舊架構
- 引擎架構級重構（skill 整併 / 目錄重組 / schema 大改）→ 同樣 path A、不問三條路
- 客戶層只保留 4 類：`data/`、`03-production-line/`、`brand*.md`、`CLAUDE.local.md`（blacklist 保護）
- `engine-manifest.json._meta.client` 是唯一引擎檔例外、sync 不覆蓋

**實作分工** — 引擎層（skill / hook / CI 規則）由主引擎 repo 做、LONGBRO 透過 `/sync-engine` 拉；客戶層（本檔 + `.claude/settings.local.json` overrides）LONGBRO 本地維護、blacklist 保護。

---

## 為什麼有這個檔

`CLAUDE.md` 是所有客戶共用的引擎規則（禁令、資料地圖、操作原則），被 `sync-engine` 同步時會**覆寫**。
`CLAUDE.local.md` 是此 repo 獨有的身份設定，**不會被 sync-engine 覆蓋**，你可以放心寫入客戶專屬資訊。

Claude Code 讀取順序：`CLAUDE.md`（引擎規則）→ `CLAUDE.local.md`（客戶特異），兩個都會進入對話 context。
