# Red Tea Bus 內容生產系統

> 系統快速入口。所有實際操作都在 Claude Code 裡完成。

---

## 快速入口

| 去哪裡 | 連結 |
|--------|------|
| 📋 **待辦清單** | `data/kai/todos.json`（v4.39+、原 `工作待辦.md` / `雜事待辦.md` 已合併為 JSON）|
| 🎬 **生產中腳本** | [[03-production-line/02-ready-to-shoot]] |
| ✅ **已完成腳本** | [[03-production-line/03-done]] |

---

## 生產線

| 階段      | 對應 pipeline 狀態 | 存檔位置 |
| ------- | ---------------- | -------- |
| 1. 靈感收集 | `inbox` / `selected` / `cooldown` | `data/kai/pipeline.json` |
| 2. 待拍   | `待拍`             | `03-production-line/02-ready-to-shoot/kai/` |
| 3. 剪輯中 | `剪輯中`           | 同上 |
| 4. 已上線 | `已上線`           | `03-production-line/03-done/kai/` |

---

## 知識庫

| 區域 | 連結 |
|------|------|
| 🧠 **數據大腦** | [[01-data-brain/brand.md]] + [[01-data-brain/cases.md]] |
| 📚 **原文庫** | [[01-data-brain/transcripts]]（≥5 篇觸發批次沉澱）|
| 📊 **表現模式** | `data/kai/performance-patterns.json`（回填自動提取）|
| 🎓 **錯誤記憶 / 偏差** | `data/kai/lessons.json`（v4.36 起統一、取代原 skill-memory 三 JSON）|

---

## 系統

| 文件 | 連結 |
|------|------|
| 📊 變更日誌 | [[07-changelog/CHANGELOG.md]] |
| 🗺️ 路線圖 | [[07-changelog/ROADMAP.md]] |
| ⚙️ 系統總指南 | [[CLAUDE.md]]（AI 開機記憶）|
| 🛠️ 工作流程 | [[.claude/rules/workflow.md]] |

---

> 💡 這是首頁，只用來導航。所有實際操作都在 Claude Code 裡完成。
> 最常用三個指令：`丟靈感：`、`確認要拍：`、`上線：VID-NNN`
