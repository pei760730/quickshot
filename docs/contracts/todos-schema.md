# todos.json Schema Contract

> version: 1.1 | last_updated: 2026-04-23
> 角色：Claude (consumer) × CLI 層 (writer + CLI)

SSoT 檔案：`data/[operator]/todos.json`

---

## 為什麼合併

v4.38 前 Kai 待辦用**純 markdown**（`00-control-center/todo/工作待辦.md` + `雜事待辦.md`）。問題：

1. 無 ID、無 state（只有勾掉或沒勾）、無 priority
2. 跟 `pipeline.json` 的影片 / `lessons.json` 的教訓**無關聯**（待辦裡提到 VID-XXX 只是文字、不是 foreign key）
3. 逾期靠 session-start hook 算日期字串（`📅YYYY-MM-DD`）、脆弱
4. 完成靠手動刪行、無 audit trail
5. 規模放大（10+ 條）會失控

v4.39 升級為**結構化 JSON**（`todos.json`）、整合到引擎的資料層。

---

## 結構

```json
{
  "schema_version": "1.0",
  "description": "Per-operator structured todo list.",
  "next_id": 1,
  "todos": [
    {
      "id": "T-0001",
      "title": "📊 每週整理：IG/FB/YT 總粉絲人數",
      "state": "pending",
      "priority": "normal",
      "due": "2026-04-25",
      "created_at": "2026-03-10",
      "closed_at": null,
      "closed_reason": null,
      "related_vid": null,
      "related_lesson_id": null,
      "tags": ["運營", "週期"],
      "notes": "每週一執行、資料來源：dashboard/"
    }
  ]
}
```

---

## 欄位定義

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `id` | string | Y | 唯一識別碼、格式 `T-NNNN`、由 `next_id` 遞增 |
| `title` | string | Y | 待辦標題（含 emoji prefix 如 `📊` / `⚠️` / `🎬`）|
| `state` | enum | Y | `pending` / `in_progress` / `done` / `archived` |
| `priority` | enum | N | `low` / `normal` / `high` / `urgent`、預設 `normal` |
| `due` | string | N | YYYY-MM-DD 截止日、無則永續 |
| `created_at` | string | Y | YYYY-MM-DD |
| `closed_at` | string | N | 僅 state 為 `done` / `archived` 時填 |
| `closed_reason` | string | N | 完成原因 / 擱置原因、自由文字 |
| `related_vid` | string | N | `VID-NNN`、關聯影片 |
| `related_lesson_id` | string | N | `L-NNNN`、關聯 lesson（例如從某個 lesson 衍生的追蹤事項） |
| `tags` | string[] | N | 標籤清單（如 `["運營"]` / `["品牌"]` / `["技術債"]`）|
| `notes` | string | N | 補充說明 |

---

## enum：state

| 值 | 語意 | 轉換規則 |
|---|---|---|
| `pending` | 待辦（新建預設） | → `in_progress` / `done` / `archived` |
| `in_progress` | 進行中 | → `done` / `archived` |
| `done` | 完成（必填 `closed_at` + `closed_reason`）| 終態、不可回溯（要重開 → 另建新 todo 參照 `related_lesson_id`）|
| `archived` | 擱置 / 取消（必填 `closed_at` + `closed_reason`）| 終態 |

---

## enum：priority

| 值 | 使用時機 |
|---|---|
| `low` | 想到再做、無時間壓力 |
| `normal` | 一般待辦（預設）|
| `high` | 重要、本週要處理 |
| `urgent` | 緊急、今明兩天必須 |

---

## 消費方式

### 對話中（Claude）

- Kai 說「看待辦」/「`t`」→ Claude 讀 `todos.json` 過濾 `state in (pending, in_progress)`、按 priority + due 排序顯示
- Kai 說「待辦：XXX」→ Claude 呼叫 `video-ops.py todo add --title "XXX"`（自動給 `T-NNNN` id + state=pending）
- Kai 說「關閉 T-XXXX / 完成 T-XXXX」→ Claude 詢問 closed_reason、呼叫 `video-ops.py todo close T-XXXX --reason "..."`

### session-start hook

原本 hook 掃 `00-control-center/todo/*.md` 算逾期、改為讀 `todos.json`：
- 過濾 `state=pending` + `due` 已過今天 → 印「📋 ⚠️「title」逾期 N 天」
- 同 todo 一次對話只提醒一次

### 與 lesson 的連動

`lesson` close 時（stage=graduated 或 archived）、若當初是從某個 todo 產生、可自動關閉對應 todo（透過 `related_lesson_id` 反查）。

---

## Migration（一次性執行）

詳見 `scripts/ops/lib/migrate_todos.py`。原則：

1. 讀 `00-control-center/todo/工作待辦.md` + `雜事待辦.md`
2. 解析 markdown 條目（`- [ ]` / `- [x]`、`📅YYYY-MM-DD` due date、emoji prefix 當 tags）
3. `- [ ]` → `state=pending`、`- [x]` → `state=done` + `closed_at=<手動解析或 today>`
4. 寫入 `data/[operator]/todos.json`
5. 原 md 檔 rename 為 `*.legacy.md`、migration 驗證後清除（v4.73 清除、內容已全數進 todos.json）

**Migration 映射**：

| Markdown | JSON |
|----------|------|
| `- [ ] 任務 📅2026-04-25` | `state: pending`、`title: "任務"`、`due: "2026-04-25"` |
| `- [x] 任務 ✅2026-04-20` | `state: done`、`closed_at: "2026-04-20"`、`closed_reason: "migration"` |
| emoji prefix（🚗 / 🎬 / 📊 / ⚠️ 等）| 保留在 title、不自動轉 tags（Kai 可事後加）|
| 「逾期 N 天」統計字串 | 丟棄（由查詢時動態計算）|

---

## 去重規則

- 主鍵：`id`（純遞增、無天然重複）
- 新建時只檢查 title 是否有太相似的 open todo（`state in (pending, in_progress)`）、有就提醒 Kai「已有類似、要合併嗎？」

---

## CLI 規格

`video-ops.py todo <subcommand>`：

| 子命令 | 用法 | 說明 |
|-------|------|------|
| `add` | `todo add --title "..." [--priority high] [--due 2026-04-25] [--related-vid VID-001] [--related-lesson L-0001] [--tags 運營,週期]` | 新增、回傳 new id |
| `list` | `todo list [--state pending] [--priority high] [--due-before 2026-04-21] [--tag 運營]` | 列出、支援多條件過濾 |
| `close` | `todo close T-0001 --reason "完成"` | 狀態設 done + closed_at + closed_reason |
| `reopen` | `todo reopen T-0001` | state 從 done → in_progress（保留 closed_at / closed_reason 作歷史）|
| `archive` | `todo archive T-0001 --reason "擱置"` | 狀態設 archived |
| `update` | `todo update T-0001 [--title ...] [--priority ...] [--due ...]` | 修改 pending / in_progress todo 的欄位 |

---

## 修改規則

- 所有修改走 `video-ops.py todo` CLI、不手動改 JSON（對齊其他 data 檔規範）
- 新增 enum 值（state / priority）需改本契約 + `todos.py` + bump schema_version
- `T-NNNN` id 一旦指派不重用（即使 archived）
- 終態（done / archived）不可直接跳回 pending、只能透過 `reopen` 明示
