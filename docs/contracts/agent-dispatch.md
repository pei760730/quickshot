# Agent Dispatch — Mode A 雙代理派遣協議

> version: 1.2 | last_updated: 2026-05-03

## 0. 定位

- **共享契約**（Claude orchestrator + Codex worker 雙方依此）
- **上位於** `AGENTS.md` §11 + `.claude/rules/workflow.md` §Dispatch（兩者為摘要 / 對話流程層）
- **衝突時**：本檔 < `CLAUDE.md` / `AGENTS.md` 紅線禁令 < Kai 當下指示

---

## 1. 為什麼有 Mode A

**背景**：Codex CLI 已在本機（PR #397 落地 `AGENTS.md` + 共享 working tree）。傳統 Mode B「Kai 兩窗複製貼上」改為 Mode A「Claude 當入口、headless 跑 Codex」。

**痛點解**：
- Kai 不再當人肉 router
- Codex 看本地 git state、共用 hook
- 規則內建 `AGENTS.md`、不靠 prompt 前綴

---

## 2. 角色

| 角色 | 是誰 | 做什麼 |
|------|------|-------|
| **Orchestrator** | Claude Code | Kai 唯一入口、解析任務、派遣、合併 |
| **Worker** | Codex CLI（透過 `codex exec`） | 收 payload、做事、回 stdout |
| **Synthesis owner** | Claude | 最後合併判斷、輸出給 Kai |

---

## 3. 何時 dispatch、何時不要

### 該 dispatch（綠燈）

- 任務有**明確兩塊獨立產出**（如 design schema → 寫對應 code）
- 需要**客觀資料探針**（檔列表、commit 史、lint 結果、coverage）
- **code-heavy** 任務（重構、test 寫作、CLI 行為改）

### 不要 dispatch（紅燈）

- 單一**架構判斷 / 反省 / 設計**（拆 = 腦袋分裂、合不回來）
- 涉及**品牌 / 創作判斷**（Codex 不讀 `brand.md`、無語感）
- **skill 設計 / 規則沉澱**（Claude 主場）
- 小（≤30 字）純資訊查（直接 Bash 更快、dispatch overhead 不值）

### 一句話判別

> **「拆完兩半各做、合得回來嗎？」合不回來 → 不拆。**

---

## 4. Master prompt routing block 約定

當 Kai 寫的任務本身有 routing 意圖、頂部加 routing block：

```markdown
# Routing
- Claude: <領土 1>, <領土 2>
- Codex: <領土 3>, <領土 4>
- Synthesis: Claude

# Sections
## [Claude] <子任務>
## [Codex-data] <資料探針>
## [Codex-code] <code 改動>
## [Synthesis] <Claude 整合條件>
```

**Claude 行為**：
- 看到 routing block → 自動分流、依本契約 §5 派遣
- 沒 routing block + 任務看起來單一 → 不拆、直接做
- 看到 routing block 但 §3 紅燈條件 → **覆蓋 routing**、不拆、跟 Kai 說「routing 提示了但本任務是反省型、不適合拆」

---

## 5. Claude 端 dispatch 協議

### 5.1 呼叫格式

```bash
codex exec --skip-git-repo-check --output-last-message /tmp/codex-out-<task>.txt "$(cat <<'EOF'
你在 KaiOS-ContentSystem repo、已讀 AGENTS.md。

# Task
<一句話描述、不歧義>

# Mode
<read-only | write-readonly-output | write-repo>

# Output format
（必明寫、否則回給 Claude 不可解析）
## Findings
- ...
## Numbers
- ...

# Constraints
- 找不到資料 → "N/A: <原因>"、不臆測
- 超出 task 範圍 → STOP、回 "out-of-scope: <什麼超出>"、不擴大
- 違反 AGENTS.md 領土 → STOP、不執行

完成後 stdout 結尾固定 `<<DISPATCH_DONE>>` marker。
EOF
)"
```

### 5.2 Mode 三種

| Mode | 行為 | 何時用 |
|------|------|-------|
| `read-only` | 只讀、輸出到 stdout | **預設**、90% 用例（資料探針、現況盤點）|
| `write-readonly-output` | 寫到 `/tmp/*`、不動 repo | 大量輸出、stdout 太多 |
| `write-repo` | 可改檔 + commit + push | 真正分叉並行 code 工作 |

預設：`read-only`。Claude 必須在 payload `# Mode` 段明寫一個。`write-repo` 必同時明寫 `PR_BRANCH=codex/<task-name>`。

### 5.3 失敗處理

| 失敗 | Claude 動作 |
|------|-----------|
| exit ≠ 0 | 回報 Kai、**不靜默 retry** |
| timeout（30 分鐘上限）| 取消 + 回報 Kai |
| output 不符 format | 重派遣**一次**、明寫「上次格式錯」+ 失敗第二次 → 回報 Kai |
| Codex 寫到非預期路徑 | `.githooks/pre-commit` 攔截（territory-lint 守門）、Claude 收到 exit ≠ 0 走第一條 |

### 5.4 Audit trail（對話內、不另開 log 檔）

每次 dispatch 完、Claude 在對話中明示：

```
🤖 dispatched to codex: <task name>
   mode: read-only
   exit: 0
   output: <stdout 摘要 / /tmp 路徑>
```

**為什麼不寫 log 檔**：避免重型治理。對話本身 + git history（write-repo 模式）已足。連續 5 次 dispatch 都用同一 task pattern → 該 pattern 升級成 skill / command（per CLAUDE.md 禁令 #13）。

---

## 6. Codex 端回應契約

Codex 收到 `codex exec` payload 時（已讀 `AGENTS.md` 為前提）：

1. **識別 `# Mode` 段**、超出該 mode 的動作即拒
2. **識別 `# Output format` 段**、嚴格遵守、不自由發揮
3. **找不到資料 → `N/A: <原因>`**、不臆測、不假填
4. **`read-only` 下禁止**：任何 write tool / git commit / 修改 working tree
5. **`write-repo` 下必檢查**：payload 中有 `PR_BRANCH=codex/<...>` 才動 commit、否則 STOP
6. **完成後 stdout 結尾固定** `<<DISPATCH_DONE>>` marker（Claude 解析依據）
7. **違反 `AGENTS.md` 領土規則 → 仍 STOP**（dispatch 不豁免領土）

本節摘要進 `AGENTS.md` §11、Codex CLI 自動讀。

---

## 7. 反例 / 不該做

### 反例 1：拆架構判斷
Kai 給「review my skill architecture」→ Claude 拆「list skills」給 Codex + 自己做判斷。
**錯**：list skills 是 Claude 自己 5 行 Bash 能做、不需 dispatch。Dispatch overhead > 收益。

### 反例 2：dispatch 後不等
Claude 跑 `codex exec`、不等 stdout 直接繼續推理。
**錯**：Codex 結果可能否決前提、白做。必等 exit + stdout 才繼續。

### 反例 3：模糊 task description
`# Task: 看一下 scripts/` → Codex 不知做什麼、隨意輸出。
**對**：`# Task: 列出 scripts/ops/ 下所有 .py 檔、依 mtime 倒序、輸出 path + 最後 commit sha`。

### 反例 4：write-repo 不指定 branch
`# Mode: write-repo` 無 `PR_BRANCH=` → Codex 在當前 branch 改 → 可能 main 或污染 → CI red。
**對**：永遠 `PR_BRANCH=codex/<task-name>` 明寫。

---

## 8. 演化條件

本契約 v1.0、下列觸發時升版：

| 訊號 | 升版動作 |
|------|---------|
| Kai 連續 3 次手動拆窗（用 Mode B 而非 A）| 檢視為何沒採用、加 §10 「為什麼 dispatch 沒被選」分析 |
| Codex CLI lifecycle hook 公開規格 | 加 §9 hook 整合（取代 `<<DISPATCH_DONE>>` marker）|
| 真實 dispatch 失敗 ≥ 2 次 | 強化 §5.3 失敗處理 |
| Dispatch ≥ 5 次同 pattern | 該 pattern 升級成 slash command 或 skill（per 禁令 #13）|

---

## 9. 與其他契約的接口

| 契約 | 接口 |
|------|------|
| `agent-collaboration.md` §9.3 / §9.11 | 領土 + base check 規則承襲、本檔不重複 |
| `AGENTS.md` §11 | 摘要 §6 Codex 端契約給 Codex 自動讀 |
| `.claude/rules/workflow.md` §Dispatch | 摘要 §3 決策樹 + §5 bash template 給 Claude 對話流程 |
| `.githooks/pre-commit` | `write-repo` mode 的最終守門（territory-lint 在 commit 層擋）|
| `CLAUDE.md` 禁令 #13 | dispatch pattern ≥ 5 次同類才考慮升 skill、本契約優先嘗試降低門檻 |

---

**一句話：Claude 是入口、Codex 是工人、Kai 不再當 router。**

---

## 10. 環境前提 + Fallback（v1.1+、2026-05-03 補）

### 10.1 為什麼有這節

v1.0 預設 Claude orchestrator 與 Codex CLI **在同一執行環境**（`bash` 看得到 `which codex`）。但實務上、Codex 有 **3 條完全不同的調用路徑**、Claude 對應的派遣模式也不同：

| 路徑 | 觸發環境 | 互動方式 | Mode A bash dispatch | 何時用 |
|------|---------|---------|--------------------|-------|
| **(1) 本機 `codex` CLI** | 同 Claude bash 環境（terminal `claude` / Desktop / IDE）| `codex exec "<payload>"` headless | ✓ 自動 | Claude 對話中即時派遣 |
| **(2) Codex Desktop app**（GUI）| 獨立 app、雲端執行 | 圖形介面貼 prompt、選 repo + branch | ✗（不需）| Kai 手動操作、適合 Windows / 不熟 CLI 場景 |
| **(3) Codex Cloud（chatgpt.com/codex）**| 瀏覽器 | 網頁貼 prompt | ✗（不需）| 路徑 (2) 的網頁版、行動裝置可用 |

**Claude Code 介面（orchestrator）vs (1) CLI 可用性**：

| Claude Code 介面 | `which codex` | Mode A 可用？ |
|----------------|--------------|--------------|
| Terminal `claude` CLI（本機跑）| ✓ | ✓ |
| Desktop app（Mac/Windows）| 多半 ✓ | 多半可 |
| **claude.ai/code 網頁版** | **✗** | **✗** |
| VS Code / JetBrains 擴充 | 通常 ✓ | 通常可 |

**關鍵洞察**：路徑 (2)/(3) **不需要 Mode A bash dispatch**、因為 Codex 自己有獨立 GUI 入口。當 Claude orchestrator 在網頁版（無 CLI）時、與其降級 Mode B-plus 要 Kai 複製 bash heredoc、**不如直接建議走路徑 (2) Desktop**、最少摩擦。

**根因**：Mode A 派遣 = Claude 跑 `bash → codex exec`。網頁版沙箱跟本機完全隔離、`bash` 找不到本機裝的 codex CLI。但 Codex Desktop 是另一條獨立路徑、跳過 bash 完全可達。

### 10.2 Claude 開工前必檢測

每次 session 第一次想 dispatch 前、跑：

```bash
which codex 2>/dev/null && codex --version 2>/dev/null
```

- exit 0 + 有版本輸出 → Mode A 可用、走 §5 派遣協議
- exit ≠ 0 / no output → **降級 Mode B-plus**（見 §10.3）、不嘗試 dispatch

### 10.3 Mode A 不可用時的兩條 fallback（v1.2 修正、優先級重排）

當 Mode A 不可用（網頁 Claude / 沙箱無 codex CLI）、依降序選：

**(a) Mode B-desktop（推薦、v1.2+）**：建議 Kai 用 **Codex Desktop / Cloud**（路徑 2/3）

1. Claude 完整寫 dispatch payload（同 §5.1 全格式）、但**不**包 bash heredoc
2. 對話中明示：
   ```
   ⚠️ Mode A 不可用（網頁 Claude 無 codex CLI）。建議走 Codex Desktop：
      1. 開 Codex Desktop / chatgpt.com/codex
      2. 確認 repo 選 pei760730/KaiOS-ContentSystem、branch=main
      3. 把以下 prompt 整段貼進去：
      ----
      <純 prompt、不含 bash 包裝>
      ----
      4. 等 Codex 開 PR、把 PR 連結貼回我
   ```
3. Kai 在 Desktop GUI 操作、Claude 看 PR 合成

**為什麼優先 (a)**：Kai 不用碰 cmd / heredoc / npm install codex CLI、最少摩擦。Codex Desktop 直接讀 GitHub repo + AGENTS.md、自動開 PR。實證：本契約 v1.2 sediment 自 2026-05-03 PR #401（Kai 用 Desktop 解 T-0020、5 分鐘搞定、CLI 路線卡 30 分鐘 npm + heredoc）。

**(b) Mode B-plus（fallback 的 fallback）**：Kai 已習慣 CLI / 想用本機環境

1. Claude 寫完整 payload、用 bash heredoc 包：
   ```bash
   codex exec --skip-git-repo-check "$(cat <<'EOF'
   <payload>
   EOF
   )"
   ```
2. Kai 複製到本機 terminal 跑、貼結果回

**(a) vs (b) 選擇**：預設 (a)。除非 Kai 明確說「我要用 CLI」、否則不要建議 (b)。

**Mode B-plus vs 純 Mode B 差別**（保留供參考）：
- 純 Mode B：兩窗各自寫 prompt（Kai 當 router + 內容設計者）
- Mode B-plus：Claude 寫完整 payload、Kai 只「複製貼上 + 跑 + 貼回」（router、不設計）

### 10.4 環境變化處理

- 同一 session 中 codex CLI 中途裝上（如 Kai 切到本機 terminal）→ Claude 下次 dispatch 前重檢測、可從 Mode B-plus 升回 Mode A
- 環境檢測失敗時、Claude **不可** 自動安裝 codex CLI（破壞 Kai 環境邊界）、必明示降級

### 10.5 給 Kai 的實務建議（v1.2 重排、Desktop 優先）

| 場景 | 建議介面 |
|------|---------|
| 寫腳本 / 內容創作 / 對話討論 / 看資料 | 網頁版 Claude |
| Codex code 任務（網頁 Claude 場景）| **Codex Desktop / chatgpt.com/codex**（GUI 貼 prompt、自動開 PR、最簡單）|
| Mode A 全自動 bash dispatch（Claude 自動派遣 + 即時看 stdout）| 本機 terminal 跑 `claude` + 已裝 codex CLI |
| 純 Codex code 任務、不需 Claude 參與 | Codex Desktop **或** 本機 `codex "xxx"`、看你習慣 |

**根本解**：
- **預設**：網頁版 Claude（討論 / 內容）+ Codex Desktop（code 任務）— 兩個 GUI、零 CLI、Windows / Mac 都可
- **進階**：要 Mode A 自動 dispatch 才切本機 `claude` CLI、需多一層 codex CLI 安裝 + 認證
