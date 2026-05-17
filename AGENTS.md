# AGENTS.md — Codex 工作守則

> 給 Codex CLI / Codex Cloud agent 讀。Claude Code 讀 `CLAUDE.md`、本檔不重複它的內容、只列 Codex 必須遵守的規則。
>
> **權威來源**：本檔是摘要、衝突時以 `docs/contracts/agent-collaboration.md`（v1.10+）為準。

---

## 1. 你是誰、Repo 是什麼

- **Repo**：KaiOS-ContentSystem（短影音生產引擎 + Kai 紅茶巴士實例）
- **協作對象**：Claude Code（在同 repo、同 working tree、讀 `CLAUDE.md`）
- **Operator 預設**：`kai`（單 operator、寫入 `data/kai/**`）
- **你的分支前綴**：`codex/*`（強制、territory-lint 依此判斷領土）

---

## 2. 開工前必做（每次 task）

```bash
# Base check — 沒做 = 違反契約
git fetch origin main 2>/dev/null || true
if git rev-parse origin/main >/dev/null 2>&1; then
  git checkout -B codex/<task-name> origin/main
else
  # sandbox 無 origin、HEAD 是否對任務指定 sha 一致才放行
  CURRENT=$(git rev-parse --short HEAD)
  echo "no origin, HEAD=$CURRENT — 確認此 sha 是任務指定才繼續"
fi
git rev-parse --short HEAD                 # 回報 base sha
python3 -c "import json; print('engine:', json.load(open('engine-manifest.json'))['_meta']['engine_version'])"
```

**規則**：
- Base sha ≠ 任務指定 → STOP、回報、不在舊 base 動手
- engine_version 落後當時最低門檻 → STOP（避免 #276 stale base 重做）
- PR body 必記 `Base verified: origin/main @ <sha>` + `Engine version observed: <X.Y>`

---

## 3. 領土白名單（你能寫 / 不能寫）

### 你（Codex）可以寫

```
scripts/**
tests/**
data/**/*.json     # 但只能透過 video-ops.py CLI、不手改
docs/contracts/**  # 共享、單向輪替、PR body 標 Owner
docs/references/**
engine-manifest.json
.github/**
AGENTS.md          # 本檔、Codex 主場
.githooks/**       # 共享 hook 基礎設施
```

### 你（Codex）不能寫

```
02-skill-factory/**     # Claude 領土（skill 定義）
.claude/**              # Claude 領土（hook、規則、設定）
01-data-brain/**        # Claude 領土（品牌知識）
03-production-line/**   # Claude 領土（腳本檔）
07-changelog/**         # Claude 領土（CHANGELOG）
00-control-center/**    # Claude 領土
dashboard/**            # Claude 領土
CLAUDE.md               # Claude 領土
CLAUDE.local.md         # Claude 領土
HOME.md                 # Claude 領土
README.md               # 共享、但本檔修改前先確認
```

### 違反時

- 本地 `.githooks/pre-commit` 會擋（commit 前阻止）
- GitHub `.github/workflows/territory-lint.yml` 也會擋（push 後 PR red）
- **唯一豁免**：PR body 寫 `territory override justified by: <具體原因>`、由 Kai 人工放行

---

## 4. 動作位置必明寫（L-0021 教訓）

收到 Claude / Kai 給的任務時、若指令含**模糊動作詞**（「補一行」「修一下」「處理」「澄清」）、**停下、留 PR comment 回問、不要預設開新 PR**：

```
請問 X 是要：
  (a) edit PR #N body
  (b) 修檔案 Y 第 Z 行
  (c) 開新 PR
  (d) 不改 PR、只回 comment？
```

Kai / Claude 回覆後再執行。

**反例**（PR #328）：Claude 說「PR body 補一行」、Codex 解讀成「開新 PR + 寫進 CHANGELOG」→ territory 違規 + 動作錯位 + 二次踩坑。

---

## 5. Engine bump 規則（§9.11、解 #271/#272 deadlock）

**你（Codex）的 PR 不要自己 bump `engine-manifest.json._meta.engine_version`。**

原因：engine bump 必對應 `07-changelog/CHANGELOG.md` 新 entry、但 CHANGELOG 是 Claude 領土。Codex 自己 bump engine = 卡死等 rescue。

**正確流程**：
1. 你的 PR：改 contract file（`docs/contracts/**`）+ 對應 code、**不動 engine_version**
2. Claude 開「配對 CHANGELOG PR」：bump engine + CHANGELOG entry
3. Merge 順序：**Claude 配對 PR 先 merge** → 你 rebase → 通過 `engine-version-check`

**例外**（可自己 bump）：純 `scripts/**` / `tests/**` 內部改動、PR body 寫 `no CHANGELOG needed: internal-only scope`。

---

## 6. 資料層紀律

- **禁止手改** `data/**/*.json`（pipeline / lessons / todos / patterns / cases）
- 透過 `python scripts/ops/video-ops.py` 寫入（CLI 是 contract、見 `docs/contracts/video-ops-cli.md`）
- 測試禁止 mock CLI、必真跑（避免 schema 漂移）

---

## 7. Schema migration 標記（v4.24+、CLAUDE.md 禁令 #14）

動到資料層 schema（`docs/contracts/*-schema.md` / `data/template/*.json`）時、CHANGELOG entry 必含：

```
🚨 schema-migration: <描述變動 + 客戶端 migration 步驟>
```

漏標 → 客戶端 `/sync` 會自動覆蓋客戶資料層 schema、客戶大腦讀不到欄位、災難。

例外：純 additive schema（新增 optional 欄位、不破壞）可註明「additive schema、無需 migration」、不必標 🚨。

---

## 8. PR 描述最小集

每個 PR body 必含：

```
## 改動範圍
<檔案 / 模組>

## 測試結果
<指令 + 結果>

## 共享區
<是 / 否、若是哪幾檔>

## Base / Engine
Base verified: origin/main @ <sha>
Engine version observed: <X.Y>
```

跨領土時加：
```
territory override justified by: <原因>
```

---

## 9. 跟 Claude Code 協作

- Claude 跟你共享同一個 working tree（你們在同台機器跑）
- Claude 可以看到你未 push 的 commit、你也看得到 Claude 的
- 不要兩邊同時改同名檔案（跨區規則：先問 Kai「對方在改這個檔嗎？」確認沒有才動）
- Claude 救援你的失敗 PR 時、會在 `codex/*` 原分支追加 commit、不另開 `claude/*`
- 你救援 Claude 不適用（Claude 領土你不碰）

---

## 10. 完整規則在哪

| 想找什麼 | 看這裡 |
|---------|-------|
| 完整協作 SOP（v1.10、520 行） | `docs/contracts/agent-collaboration.md` |
| Headless dispatch 協議（Mode A）| `docs/contracts/agent-dispatch.md` |
| Schema 契約（pipeline / lessons / todos） | `docs/contracts/*-schema.md` |
| video-ops CLI 契約 | `docs/contracts/video-ops-cli.md` |
| Sync protocol（多客戶引擎複製） | `docs/contracts/sync-protocol.md` |
| Claude 自己的規則（讀此檔可懂 Claude 在想什麼） | `CLAUDE.md` + `.claude/rules/workflow.md` |
| 客戶身份（Red Tea Bus 速查） | `CLAUDE.local.md` |

衝突時：本檔 < `docs/contracts/agent-collaboration.md` < Kai 當下指示。

---

## 11. Headless dispatch（Claude → 你 via `codex exec`）

當 Claude 用 `codex exec` 呼叫你時、你是 worker、Claude 是 orchestrator。

**權威**：`docs/contracts/agent-dispatch.md` v1.2+（含 §10 環境前提 + Mode B-desktop fallback）

**核心契約**（payload 進來時你必做）：

1. **識別 `# Mode` 段**（`read-only` / `write-readonly-output` / `write-repo`）、超出該 mode 的動作即拒
2. **識別 `# Output format` 段**、嚴格遵守、不自由發揮
3. **找不到資料 → `N/A: <原因>`**、不臆測、不假填
4. **`read-only` 下禁止**：任何 write tool / git commit / 修改 working tree
5. **`write-repo` 下必檢查**：payload 中有 `PR_BRANCH=codex/<...>` 才動 commit、否則 STOP 回報
6. **完成後 stdout 結尾固定** `<<DISPATCH_DONE>>` marker（Claude 解析依據、漏寫即視為任務未完）
7. **超出 task 範圍 → STOP**、回 `out-of-scope: <什麼超出>`、不擴大解讀
8. **領土規則仍生效**（§3 白名單）— dispatch **不豁免** territory，違反就停

**典型 payload 範例**：

```
你在 KaiOS-ContentSystem repo、已讀 AGENTS.md。

# Task
列出 scripts/ops/ 下所有 .py 檔、依 mtime 倒序、輸出 path + 最後 commit sha

# Mode
read-only

# Output format
## Files
- <path>: <sha>

# Constraints
找不到 → "N/A: <原因>"；超出 → STOP；領土違反 → STOP

完成後 stdout 結尾固定 `<<DISPATCH_DONE>>`。
```

**反例**：模糊 task / 沒 Mode / 沒 Output format → 你回問 Claude 確認、不要自行解讀。
