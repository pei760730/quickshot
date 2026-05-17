# 引擎同步協議（Sync Protocol）

> version: 2.2 | last_updated: 2026-05-15
> 本文件寫給「客戶專案的 Claude」看，告訴它如何從引擎 repo 同步更新。
>
> **v2.2 變更（2026-05-15、engine v5.95）**：`contract_files` 拆成 `semantic_contracts` + `factual_contracts`。語義契約（規則 / API / SKILL / schema）改動仍強制 bump + CHANGELOG；事實契約（README / changelog / 參考歷史）改動只檢 inline version 對齊、不觸發 engine bump。客戶端同步時兩類都納入同步範圍，但 semantic 顯示「規則變動」警告、factual 顯示「事實對齊、可選」提示。
>
> **v2.1 變更（2026-04-23、波次 3 · T3-1）**：blacklist 範例描述對齊 — `data/**` 範例從「pipeline / patterns / **skill-memory** 等」改為「pipeline / patterns / **lessons / todos** 等」（skill-memory/ v4.76 已退役）。
>
> **v2.0 變更（Opus 4.7 全修 Stage E、engine v4.65）**：engine-manifest.json 結構從單層 `files` 變成兩層 `contract_files` + `internal_files`；engine_version_check 的強制 scope 從「全部非 blacklist 路徑」收斂到「contract_files」。rationale 見 §為何兩層化。v2.0 改動**只動版本協議強制範圍**、sync 同步範圍（blacklist 判定）不變。
>
> **v1.2 歷史（2026-04-21、engine v4.38）**：operator 定義從引擎層 `scripts/ops/lib/config.py` 硬寫移到客戶側 `data/.operators.json`（blacklist 保護）。客戶跑 bootstrap-client.sh 時、operator 註冊寫入 `.operators.json`、下次 `/sync-engine` 不會覆蓋、operator 永久保留。同步加 step 0 sanity check（`current_operator ∈ OPERATORS`）。
>
> **v1.0 歷史**：同步模型從 opt-in 清單（`_meta.files`）改為 opt-out blacklist（`_meta.sync_blacklist`）。預設全部同步、只有 blacklist 中 glob 規則 match 到的路徑不同步。
> - 理由：opt-in 模式每次都要人記得分類（曾 v4.17 誤把 dashboard/ 加進、v4.23 才移除）。opt-out 只需維護一份黑名單、規則不變就永遠不出錯。

---

## 為何契約再分層（v2.2）

`engine-manifest.json` 曾從單層 `files` 拆成 `contract_files` + `internal_files`，解決「內部 scripts/tests 小改也要求 engine bump」的摩擦。v5.95 進一步把 `contract_files` 拆成兩種契約，因為 README / changelog / 歷史參考這類**純事實對齊**不會改變客戶 Claude 行為，卻長期與真正規則變動共用同一條 bump gate（v8.6 / v8.7 / v8.8 / v8.9 連續 README engine 版本對齊就是症狀）。

**v2.2 三層 schema**：
- `semantic_contracts`：規則 / API / SKILL / schema / lifecycle 等會改變客戶 Claude 決策或對外介面的契約；改動必須 bump `_meta.engine_version` 並補 CHANGELOG `🔧` 條目。
- `factual_contracts`：README、CHANGELOG、歷史 / lineage / worktree guide / sync SOP 等事實描述；改動不觸發 engine bump，但若檔案有 inline `> version:`，仍必須與 manifest entry 一致。
- `internal_files`：引擎內部實作（`scripts/**`、`tests/**`、hooks/commands/stub 等）；不觸發 bump，null entry 表示只納入 registry / sync visibility、不追 inline version。

兩類 contract 與 internal 檔案仍**都會**被 sync-engine 推給客戶 repo（同步範圍看 blacklist）。差異只在 guard 與 UX：semantic 是「規則變動」；factual 是「事實對齊、可選」。

**判準原則**：如果客戶 repo 的 Claude 會讀此檔來決策、呼叫 CLI/API、理解 schema 或套用 SKILL 行為，它是 semantic；如果只是描述既有狀態、版本、歷史或操作背景，它是 factual；如果主要是 runtime code/test/hook，它是 internal。

> **Migration note（v5.95）**：`contract_files` key 完全廢棄，不保留 manifest alias。客戶端看到 v5.95 CHANGELOG 的 `🚨 schema-migration` 標記時，應停止自動 merge、手動把本地 manifest 的 `contract_files` 拆成 `semantic_contracts` / `factual_contracts`，再保留 `_meta.client` 後套用新版 manifest。


## 架構

```
pei760730/KaiOS-ContentSystem         ← 引擎 repo（主 repo = Kai 的實例 + 引擎發布源）
  engine-manifest.json
    _meta.engine_version              ← 版本號（觸發客戶同步的關鍵）
    _meta.sync_blacklist              ← **唯一 SSoT**：哪些路徑不推給客戶
    semantic_contracts                ← 規則 / API / SKILL / schema（改動強制 bump + CHANGELOG）
                                        （v2.2+；e.g. CLAUDE.md、SKILL.md、docs/contracts/*.md）
    factual_contracts                 ← 事實 / 描述 / 歷史（只檢 inline version、不強制 bump）
                                        （v2.2+；e.g. README.md、CHANGELOG、docs/references/*.md）
    internal_files                    ← 引擎內部實作（改動不強制 bump）
                                        （e.g. scripts/**、tests/**、.claude/hooks/*.sh）
  07-changelog/CHANGELOG.md           ← 🔧 引擎變更紀錄

pei760730/KaiOS-Client-XXX            ← 客戶 repo（獨立資料 + 引擎同步進來的檔）
  engine-manifest.json                ← sync 時從引擎 repo 複製
```

> **Backward compatibility**: `engine_version_utils.parse_manifest_files()` 保留能讀舊 `files` dict 作為 fallback、現有 customer repo 不會 break。舊格式中有 inline version 的項目自動視為 contract。

---

## 同步模型（v2.2 核心）

**預設：主 repo 所有檔案都是「引擎」、都會推給客戶。**

**例外：`_meta.sync_blacklist` 中 glob 規則 match 到的 → 不推**。

### Blacklist glob 語法

- `data/**` → `data/` 下所有深度的檔案
- `!data/template/**` → 明確排除（negation 優先於 blacklist）
- `docs/contracts/*-collaboration.md` → 特定檔名 pattern

### 當前 blacklist（讀 `engine-manifest.json._meta.sync_blacklist`）

| 路徑 glob | 理由 |
|-----------|------|
| `data/**` | 客戶專屬運行資料（pipeline / patterns / lessons / todos 等）|
| `!data/template/**` | 例外：`data/template/` 是引擎新客戶模板、要同步 |
| `01-data-brain/brand*.md` | 品牌知識（每個客戶不同）|
| `01-data-brain/cases.md` | 案例庫（客戶不同）|
| `01-data-brain/transcripts/**` | Kai 語音原文 |
| `03-production-line/**` | 腳本（客戶生產）|
| `00-control-center/todo/**` | 待辦 |
| `dashboard/**` | **Kai 特有 Vercel dashboard**（客戶可能用別的部署）|
| `docs/contracts/*-collaboration.md` | **工具協作憲章**（綁定特定工具、客戶工具鏈可能不同）|
| `!docs/contracts/agent-collaboration.md` | **例外（v2.1 新增）**：此檔是通用 Claude × Codex 協作憲章、客戶必需 |
| `CLAUDE.local.md` | 客戶身份設定 |
| `.claude/settings.local.json` | 客戶本地 permission 設定 |

**`_meta.sync_blacklist` 是唯一 SSoT**。本文件引用它、不重複定義。

---

## 同步步驟

Kai 說「同步引擎」時，執行以下步驟：

### 1. 拉引擎最新

```bash
git fetch engine main
```

### 2. 讀引擎 `engine_version` + `sync_blacklist`

```bash
# 從 git 取（不影響 working tree）
git show engine/main:engine-manifest.json | jq '._meta.engine_version'
git show engine/main:engine-manifest.json | jq '._meta.sync_blacklist'
```

### 3. 比對版本

- 本地 `engine_version` == 引擎 `engine_version` → 回報「已是最新」、結束
- 否則 → 繼續

### 4. 計算要同步的檔案清單

```
diff = git diff local-engine-version..engine/main --name-only
candidate = diff files
filtered = [path for path in candidate if not is_blacklisted(path, sync_blacklist)]
```

### 5. 讀 CHANGELOG 差異

```bash
git show engine/main:07-changelog/CHANGELOG.md
```

提取本地 `engine_version` 到引擎最新版之間的 🔧 條目（📦 條目跳過）。

### 6. 展示同步計畫給 Kai

```
📦 引擎同步計畫（v{本地} → v{引擎}）

要更新的檔案（{N} 個，已過濾 blacklist {M} 個）：
• ⚠️ 規則變動（semantic）：檔 A：{CHANGELOG 摘要}
• ℹ️ 事實對齊（factual，可選）：檔 B：{fact alignment 摘要}
• 內部實作（internal）：檔 C：{CHANGELOG 摘要或 diff 摘要}
• ...

Blacklist（不動）：
• data/** / 01-data-brain/brand*.md / ...（不逐個列、點一下 engine-manifest 看完整）

回「同步」執行、「跳過」停。
```

### 7. 執行同步（Kai 確認後）

對每個非 blacklist 檔：
```bash
git show engine/main:<path>  → 寫到本地對應位置
```

更新本地 `engine-manifest.json`：
- `_meta.engine_version` 對齊引擎
- `_meta.sync_blacklist` 對齊引擎
- `semantic_contracts` / `factual_contracts` / `internal_files` 對齊引擎（版本 registry 用途）
- 移除舊 `contract_files` key；v5.95 起不保留 legacy alias
- **保留客戶本地** `_meta.client` 欄位（若有）

### 8. 驗證

```bash
python -m pytest tests/ -q
python scripts/lint/rules-lint.py --ci
python scripts/ops/video-ops.py --operator <客戶> validate-all
```

任一 fail → 不 commit、回報給 Kai。

### 9. Commit

```
chore: sync engine vX.X → vY.Y
```

---

## 新客戶初始化

從引擎 repo fork 或複製：
1. 複製**所有非 blacklist 路徑**的檔（依 `_meta.sync_blacklist`）
2. 建立空的客戶資料目錄結構（依自家 operator）：
   - `data/{operator}/pipeline.json`（從 `data/template/pipeline.json` 複製、改 operator 欄位）
   - `data/{operator}/performance-patterns.json`（空模板）
   - `01-data-brain/brand.md` + `cases.md`（空模板，客戶自填）
   - `03-production-line/02-ready-to-shoot/{operator}/` + `03-done/{operator}/`
   - `00-control-center/todo/`
3. 建立 `CLAUDE.local.md`（客戶身份設定）
4. 設定 `scripts/ops/lib/config.py` 的 OPERATORS dict
5. 跑 pytest 驗證基礎架構
6. 開始填品牌知識

---

## 注意事項

- **不要同步 blacklist 路徑** — 按 `_meta.sync_blacklist`
- **同步後一定要跑測試** — 引擎可能改 schema，客戶資料可能需配合調整
- **CHANGELOG 的 📦 標記條目不要同步** — 那是引擎 repo 自己的資料操作

---

## 升版協議（Engine Version Bump Protocol）

> 核心原則：**客戶端同步靠版本號觸發**。引擎側改動若沒升版，客戶端跑 `/sync-engine` 會顯示「已是最新」→ 真實改動抓不到。

### 何時必須升版

PR 改動若觸及 `semantic_contracts` 路徑，必須：

- 升 `engine-manifest.json._meta.engine_version` +0.01 或以上
- 補 `07-changelog/CHANGELOG.md` 🔧 新版本條目
- 若動到有 inline `> version: X.Y` header 的檔 → 升 inline 版本號 + 同步 `semantic_contracts` 值

PR 改動若只觸及 `factual_contracts` 路徑：

- 不要求 engine bump / CHANGELOG
- 若檔案有 inline `> version: X.Y` header，manifest 的 `factual_contracts[path]` 必須同步更新
- sync-engine 顯示為「ℹ️ 事實對齊（可選）」而非「⚠️ 規則變動」

### 不需升版（自動略過）

- 純 blacklist 路徑變動（見 `_meta.sync_blacklist`，代表性路徑：`data/**`、`01-data-brain/brand*.md`、`03-production-line/**`、`00-control-center/todo/**`、`dashboard/**`、`docs/contracts/*-collaboration.md`）
- `internal_files` 路徑變動
- `factual_contracts` 純事實對齊（仍需 inline version 一致）
- 註解/排版微調且無語意變更

### CI 擋點

`.github/workflows/engine-version-check.yml` 對每個 PR 執行 `scripts/engine/engine_version_check.py`：

- 若 PR diff 觸及非 blacklist 路徑：
  - `_meta.engine_version` 必須與 `origin/main` 不同 → 否則 fail
  - `CHANGELOG.md` 必須包含對應新版本號的 🔧 條目 → 否則 fail
  - 動到的檔案若有 inline 版本號，manifest 值必須一致 → 否則 fail
- 若 PR 只動 blacklist 檔 → 不觸發升版檢查（可 merge）

### Bump 工具

`python scripts/engine/bump_engine.py [--dry-run] [--apply]`：
- 掃 `git diff origin/main...HEAD --name-only`
- 過濾 blacklist
- 提議新 `engine_version` + inline 版本號 + CHANGELOG stub
- `--apply` 套入 manifest + CHANGELOG

### 為什麼 opt-out blacklist > opt-in 清單

舊 opt-in 模式的失敗模式（踩過 3 次）：
- v4.17：Claude 把 dashboard/* 加進 manifest registry → 客戶會抓到 Vercel 配置
- v4.23：PR #161 移除 dashboard/* → 補洞
- 本版（v4.24）：若再有新 Kai 特有檔，opt-in 模式要再開 PR 補洞

新 opt-out 模式：
- 新加引擎檔 → 預設在白名單（不 match blacklist），自動同步
- 新加 Kai 特有檔 → 路徑放 blacklist 規則下，自動不同步
- blacklist 規則用 glob（`dashboard/**`、`*-collaboration.md`），涵蓋未來所有同類新檔
- 維護從「每次想」變「一次寫對」

---

## 本文件變動時機

- 新增一條 blacklist 規則 → 改 `engine-manifest.json._meta.sync_blacklist`，本檔的「當前 blacklist」表格同步更新
- 同步流程變動 → 升版 + 更新「同步步驟」章節
- 升版協議變動 → 升版 + 更新對應章節

保持簡潔、不擴張成其他職責。
