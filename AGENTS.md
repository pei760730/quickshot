# AGENTS.md — Codex / sub-agent 協作入口

> version: 1.0 | last_updated: 2026-06-04
> 給 Codex / sub-agent 讀的入口。Claude Code 讀 `CLAUDE.md`；本檔讓非 Claude 的 agent 拿到同一套規則。

## 完整規則在哪

本 repo 的工作原則、禁令、資料地圖、操作流程是**單一正本**，不在這裡重抄：

- **`CLAUDE.md`** — 禁令（虛構 / 存檔確認 / 方案先行三層 / 精準修改 / 改動自驗 / 硬化優先）、資料地圖、操作原則。**動工前必讀。**
- **`.claude/rules/workflow.md`** — 工作流程 + 設計原則（工作模式 X/Y/Z/W）+ §多代理協作（下面這段的正本）。
- **`CLAUDE.local.md`** — 此 repo 品牌 / operator 身份。

凡 `CLAUDE.md` 與本檔衝突，以 `CLAUDE.md` 為準。

## 重點摘要（細節見上面兩檔）

- **精準修改**：只改被要求的部分，不順手改旁邊的 code / 註解 / 格式。配合既有風格。
- **方案先行**：中改（改邏輯 / 改結構 / 多檔連動）先描述方案等批准；不可逆（刪檔 / 改 CI / force push）強制二次確認。
- **改動自驗**：每次修改列出驗證方式並執行（跑 test / lint），通過再繼續；失敗如實說、附輸出。
- **硬化優先**：寫 feature code 前先問能否用 lint/test、文件規則、schema 擋住。代碼是最後手段。
- **不虛構**：不確定就說「不確定 / 需查證」，不編造。

## 多代理協作（與 `workflow.md` §多代理協作同步）

你是被派工的執行方。遵守：

### 領土邊界

- 只改**派工 prompt 白名單內的路徑**。越界應由 CI lint 擋（檢查待建；在那之前由你自律 + 驗收方 review）。
- 共享路徑（如 `docs/contracts/` 契約檔）單向輪替，不與其他 agent 同時雙寫；PR body 標明 owner。

### 開工前

- **base-check**：從 prompt 指定的 `main` sha 切 branch，不要 resume 任何舊任務。
- 看到 prompt 頂的 `task_seed` + 「DO NOT resume any previous task」→ **務必開全新 branch `codex/<name>`**，不接續舊 session。
- 動作位置照 prompt 明確指示（「改 X 檔第 N 行」）；prompt 模糊就回問，不要自行臆測「修一下 / 處理一下」。

### 交付

- PR 的 merge-base 必須 = 當下 `main` HEAD（會被驗收方用 `git merge-base <PR> origin/main` 檢查）。若帶到已 merge 的舊檔 → 重設 branch 到 main、只留 net-new。
- 隔離 sandbox 的「CI 全綠」不等於目標環境（如 Windows）正確；關鍵改動標明哪些**未在目標環境實測**，由驗收方本地確認。
- 單主題單 PR，未經要求不擅自合併。
