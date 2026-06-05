# AI System Upgrade Report

> Sleep Mode — 第五輪。主題：**多代理（Claude × Codex）重新引入後的 doc-vs-reality 對齊**。
> 本輪嚴格模式：**未 commit / 未 push / 未開 branch / 未開 PR**。所有變更留在 working tree 待 Kai review。
> 前四輪（PR #10/#15/#16/#17、跨平台修復等）已 merge 進 main，成果不在此重述。
> 本輪背景：同 session 內 PR #20–#27 把「雙 agent 協作 + territory-lint」以輕量形式重新引入，但多份文件仍停在「該模組已砍掉/退役」的舊敘述 → 產生文件與實作矛盾，本輪對齊。
>
> **後續更新（2026-06-05）**：M1（territory 兩套白名單矛盾）已依 Kai 選 **option A** 處理 —— `.githooks/pre-commit` 的 codex 白名單改寫為 allow + deny（deny 優先），對齊 `.github/agent-territory.json`；11 條樣本路徑 hook 與 CI `territory-lint.py` 判斷 **100% 一致**（已對拍驗證）。claude 側 CI 無對應 territory、保留為本機 local-only 守衛。下方 M1 / Remaining issues 段保留為當時快照。

## Base

- Branch: `main`
- HEAD: `b68342b`
- Repo root: `C:/Users/user/projects/quickshot`
- Time: 2026-06-05
- Platform: Windows 10（本機 Python 3.14；repo CI 用 3.11）
- Working tree before changes: clean
- Working tree after changes: **2 files modified, uncommitted** — `README.md`、`.githooks/pre-commit`

## Project snapshot

- Project type: AI 驅動短影音生產 template（KaiOS 短期客戶 ≤30 天精簡版）；目前乾淨 template（無掛客戶）
- Primary language: Python（CI 3.11 / 本機 3.14）
- Package manager: pip + `requirements-dev.txt`（`pytest>=8.0` / `ruff>=0.5`）
- Main entrypoints: `scripts/ops/video-ops.py`（狀態寫入唯一入口）/ `scripts/lint/*.py` / `scripts/utils/*.py` / Claude Code `/init` `/check` `/scan` `/harden`
- Automation: `.github/workflows/{rules-lint,territory-lint,sync-to-sheets,wipe-client}.yml`；`.githooks/pre-commit` + `.pre-commit-config.yaml`；`.claude/hooks/*.sh`
- Validation commands available: `python -m pytest tests/` / `python -m ruff check --select E9,F63,F7,F82 scripts tests` / `rules-lint.py --ci` / `brand_ref_lint.py` / `video-ops.py validate-all` / `compileall scripts tests`
- AI instruction files: `CLAUDE.md`（受保護）/ `CLAUDE.local.md` / `AGENTS.md`（Codex 入口）/ `.claude/**`（受保護）

## What I inspected

- Git state（main、HEAD b68342b、working tree 乾淨、225 tracked files、111 py / 73 md）
- 全套驗證基線（改動前，Windows）：rules-lint / brand-ref / validate-all / pytest 全綠（pytest 576 passed, 1 skipped）
- 全 repo 搜尋「territory-lint / 雙 agent / 退役 / 砍掉 / agent-collab」找 multi-agent 重新引入後殘留的 stale 敘述
- 兩套 territory 真相比對：`.githooks/pre-commit`（CLAUDE_OK/CODEX_OK regex）vs `.github/agent-territory.json`
- README 架構樹 vs 實際檔案（commands 集合、workflow 數、AGENTS.md）
- 文件記載的驗證指令是否在本機真的可跑

## System-level issues found

### High risk
- 無（無資料損壞 / 流程中斷級問題；repo 健康）。

### Medium risk
- **M1 — 兩套 territory 白名單分歧（互相打架的規則）**：本機 `.githooks/pre-commit` 的 `CLAUDE_OK/CODEX_OK` regex 與 CI 的 `.github/agent-territory.json` 不一致，且**雙向矛盾**：
  - 本檔 CODEX_OK 放行 `docs/contracts/`、`data/`；但 agent-territory.json 對 codex 是 **deny** → 本機 commit 過、CI fail。
  - agent-territory.json 放行 `07-changelog/**`；本檔 CODEX_OK 未列 → 本機 hook **擋**、CI 過。
  - `scripts/lint/rules-lint.py`：本檔放行（`scripts/`）、agent-territory.json deny。
  - **處置**：未改邏輯（屬行為變更、需 Kai 決定哪邊 canonical）。已在兩處加註交叉提醒（見下）+ 本報告。

### Low risk（doc-vs-reality，本輪已修）
- **L1** README「砍掉的 3 大模組」把「雙 agent 協作（territory-lint）」列為已砍 → 與 PR #20–#27 重新引入矛盾。
- **L2** README 架構樹漏 `AGENTS.md`、只列 4 個 workflow 中的 1 個、commands 寫 `{harden,scan}` 實為 `{check,harden,init,scan}`。
- **L3** README「測試 + CI」漏 CI 實際會跑的 ruff 步驟、漏 territory-lint、未提示先裝 dev deps（bare `ruff` 不在本機 PATH → 照 README 跑會 `command not found`）。
- **L4** `.githooks/pre-commit` 標頭宣稱「CI 層 territory-lint 已退役」「template 已無 CI 端 territory-lint」→ 現在皆為假（territory-lint.yml 已存在且 active）。

### Low risk（受保護路徑，未改，交 owner）
- **L5** `.claude/commands/scan.md:5` 宣稱「雙 agent 協作已退役、本 template 單 Claude agent 不適用」。`.claude/**` 為 repo 受保護路徑（permissions.md + settings.json deny），Sleep Mode 下未經 Kai 確認不擅改。
  - 註：此句**部分**為真 —— KaiOS 的重量級 `agent-collaboration.md` 協定（責任區/同步委託/Owner 分流）確實未恢復；但「單 Claude agent」一句已不正確（已用 Codex）。建議 owner 改為「重量級協定未恢復、但已有輕量 multi-agent，見 AGENTS.md」。

## Changes made

1. **README.md — 砍掉模組表對齊**：在「雙 agent 協作」列加 `↺ 已於 2026-06 重新引入` 標記 + 表下加「更新（2026-06）」註，指向 `AGENTS.md` / workflow.md §多代理協作 / territory-lint.yml；保留原列為歷史。
2. **README.md — 架構樹**：加 `AGENTS.md` 一行；commands 改 `{check,harden,init,scan}.md`；`.github/` 展開為 4 個 workflow + `agent-territory.json`。
3. **README.md — 測試 + CI**：加 ruff 步驟、加「先 `pip install -r requirements-dev.txt`、ruff 不在 PATH 改用 `python -m ruff`」提示、CI 區塊補上 `territory-lint.yml`。
4. **.githooks/pre-commit — 標頭註解**：移除「已退役」假敘述；補「現況：territory-lint 已重新引入」+「已知分歧 M1」交叉提醒；修正 violation 時 runtime echo 的「已無 CI 端 territory-lint」字串。

> 全部為**文件 / 註解 / 輸出字串**層級，零程式邏輯變更、零行為變更。未碰受保護路徑（CLAUDE.md / .claude/**）、未碰 secrets、未改 territory 判定邏輯、未改 CI 步驟。

## Files changed

- `README.md`（doc 對齊 L1–L3）
- `.githooks/pre-commit`（註解 + 輸出字串 L4 + M1 交叉提醒）

## Verification run

| Check | Command | Result | Notes |
|---|---|---|---|
| Ruff 嚴重錯誤 | `python -m ruff check --select E9,F63,F7,F82 scripts tests` | ✅ All checks passed | bare `ruff` not on PATH（見 L3），用 module 跑 |
| 跨檔 lint | `python scripts/lint/rules-lint.py --ci` | ✅ 0 issues | 掃 README，交叉引用未壞 |
| brand-ref lint | `python scripts/lint/brand_ref_lint.py` | ✅ 0 issues | |
| JSON 一致性 | `python scripts/ops/video-ops.py validate-all` | ✅ 0 錯誤 / 0 警告 / 0 schema drift | |
| 單元測試 | `python -m pytest tests/ -q` | ✅ 576 passed, 1 skipped | |
| 編譯 smoke | `python -m compileall -q scripts tests` | ✅ exit 0 | ruff 替代 smoke |
| hook 語法 | `bash -n .githooks/pre-commit` | ✅ syntax OK | 改後重驗 |

## Issues fixed

- L1 / L2 / L3 / L4（doc-vs-reality 對齊，見「Changes made」）。

## Existing issues not fixed

- **M1** territory 白名單分歧 — 僅加註，未對齊邏輯（需 Kai 決定 canonical 來源；屬行為變更，Sleep Mode 不擅改）。
- **L5** `.claude/commands/scan.md:5` stale — 受保護路徑，交 owner。
- bare `ruff` 不在本機 PATH — 已在 README 加 `python -m ruff` 提示；本機環境本身不改。

## Remaining risks

- M1 未對齊前，未來 Codex 在本機 commit 與 CI 可能對「同一檔是否越界」給出相反結論（本機過、CI fail，或反向）。已雙處加註，但根因（兩套真相）仍在。
- L5 未改前，`/scan` command 的說明仍會讓讀者誤以為本 template 不支援多代理。

## Branch cleanup candidates

### Possibly safe to delete after human review
- 遠端 `claude/territory-ci-docs` — PR #23 已 merge，分支殘留（疑似 gh `--delete-branch` 未生效，本 session 已多次遇到）。merge 後本應刪除。

### Do not delete yet
- `main`（本地 + 遠端）— 預設分支。

## Recommended next actions

1. **對齊 M1**：擇一為 territory canonical 來源。建議以 `.github/agent-territory.json`（CI gate、本 session 新建）為準，改寫 `.githooks/pre-commit` 的 regex 與之一致；或在 hook 內直接讀 json（避免兩份真相）。屬行為變更、需實測本機 commit 流程。
2. **owner 修 L5**：把 `.claude/commands/scan.md:5` 的「單 Claude agent 不適用」改為「重量級 agent-collaboration 協定未恢復、但已有輕量 multi-agent（AGENTS.md / territory-lint）」。
3. **清理殘留遠端分支** `claude/territory-ci-docs`。
4. 可考慮把 `ruff` 加進本機環境（或在 session-start hook 確保 `pip install -r requirements-dev.txt`），讓 README 的 bare `ruff` 指令本機可用。

## Safe to commit?

- **Yes**（內容上）：純文件 / 註解修正，零邏輯變更，全套驗證綠。
- 但本輪 prompt 明確要求**不 commit / 不 push / 不開 branch / 不開 PR** → 故**未執行**，變更留 working tree 待 Kai review。
- Commit 前提（若 Kai 要收）：在預設分支先開 branch；單主題（doc 對齊）一個 commit；不要把 M1 邏輯對齊混進此 commit。
