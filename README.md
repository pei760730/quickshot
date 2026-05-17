# KaiOS-ContentSystem

> Red Tea Bus 短影音內容生產系統 — AI 驅動、資料自解釋、可自我進化
> version: 8.10 | last_updated: 2026-05-15 | engine: v5.95

## 設計哲學

核心原則（6 條、不增量）：

- **最小規則 + 最完整上下文** — CLAUDE.md 14 條禁令 + 資料地圖、其餘由 AI 從資料結構推斷
- **資料即規則** — 狀態機、門檻、合法轉換定義在 `pipeline.json._meta`、不在規則檔重複
- **寫入靠程式、分析靠 AI** — 程式只負責確定性寫入（防損壞）、報告 / 診斷 / 卡關偵測由 Claude 直接讀 JSON 判斷
- **學習自動閉環** — Claude 對話中主動判斷 → Kai approve → `/harden` 當場寫 test/lint/禁令/brand（見 §硬化）
- **多代理協作** — Claude（prompt / skill / content）+ Codex（backend / CI / tooling）、共享契約定義接口、territory-lint CI 硬化邊界
- **規則可機器驗證** — 契約層（8 份 schema）擋漂移、不再靠文檔口頭約定

## 系統規模

| 指標 | 數值 |
|------|------|
| Python 程式 | ~13,600 行（18 ops/lib + 12 utils/lib 模組 + 6 子目錄：`bootstrap` / `engine` / `libs` / `lint` / `ops` / `utils`） |
| 自動化測試 | 74 檔（629 test cases） |
| Skill | **vNext 5 核心**（orientation / discovery / generation / quality / distillation）+ harden + skill-creator = **7**（Phase 5 真退役完成 + Phase 6 第二輪 orientation/distillation 降 stub、engine v5.95）|
| 系統指令 | `CLAUDE.md` v4.24（14 條禁令）+ `.claude/rules/workflow.md` v2.31（5 項對話開頭檢查 + Adoption-gate + Orientation 規則層 + Mode W metric 驗證原則） |
| 共享契約 | 9 份（`skill-io-schema` / `lessons-schema` v2.3 / `pipeline-schema` / `sync-protocol` / `todos-schema` / `performance-patterns-schema` / `video-ops-cli` / `agent-collaboration` / `test-path-bootstrap`） |
| 數據大腦 | `brand.md` + `cases.md`（13 模組）— brand.md 改 lazy load（v4.62+ 全文 auto-inject 退役、skill 跑時 brain_loader 載 / 對話需要時 Read、每 session 省 ~27k token）|
| 硬化流程 | `/harden` 對話內 skill（v4.64+）5 種 path：test / lint / claude_md / workflow_md / brand_md（v4.67 Stage F queue 整層退役）|
| Multi-operator | `data/.operators.json` 註冊 + `bootstrap-client.sh` 初始化 + `engine-manifest._meta.client` 身份標記 |

## 資料夾結構

```
KaiOS-ContentSystem/
├── CLAUDE.md                   # AI 開機記憶（v4.24、14 條禁令 + 資料地圖）
├── CLAUDE.local.md             # 此 repo 客戶身份（sync-engine 永不覆蓋）
├── .claude/
│   ├── rules/workflow.md       # v2.31（5 項對話開頭 + Adoption-gate + Orientation 規則層 + Mode W metric 驗證）
│   ├── rules/permissions.md    # 受保護路徑
│   ├── hooks/session-start.sh  # 5 項偵測（brand lazy-load 提示 + 回填 / 待辦 / 大腦新鮮度 / transcripts / engine lag）+ Adoption gate
│   ├── skills/                 # 7 個 entry stub（vNext 5 + harden + skill-creator）
│   └── commands/scan.md        # /scan 責任區掃描
│
├── 01-data-brain/              # 品牌知識 SSoT
│   ├── index.md                # 資料地圖（載入表 + 進化觸發）
│   ├── brand.md                # 品牌知識（[0]~[12] 共 13 模組、SessionStart hook 全文注入）
│   ├── cases.md                # 真實案例庫
│   └── transcripts/            # 語音筆記原文（≥5 篇觸發批次沉澱）
│
├── data/                       # JSON 資料層
│   ├── .operators.json         # operator 註冊（sync_blacklist 保護）
│   ├── kai/
│   │   ├── pipeline.json       # 狀態 SSoT（含 _meta.thresholds 門檻定義）
│   │   ├── performance-patterns.json  # 成功 / 風險模式 + 勝率 / 信心等級
│   │   ├── lessons.json        # 統一 lessons（origin / stage / pattern / counter_pattern、v2.0 3 態 schema）
│   │   ├── todos.json          # 追蹤 SSoT
│   │   └── hardening-archive.json     # /harden 對話內硬化成功記錄（v4.67 queue 退役後唯一 source）
│   └── template/               # 新客戶 bootstrap 模板
│
├── 02-skill-factory/           # vNext 5 核心 + harden + skill-creator = 7 個 Skill
│   ├── README.md               # v6.2（vNext 5 + harden + skill-creator 精簡表）
│   ├── orientation/ discovery/ generation/ quality/ distillation/   # vNext 5 核心（v1.0）
│   └── shared-references/
│       ├── brain-loading.md    # v1.1 中央載入協議（對齊 brain_loader.py）
│       ├── quality-gates.md    # L0/L1/L2 品質矩陣
│       ├── skill-design-principles.md  # A/B/C/D/E/F 六準則（對應 CLAUDE.md 禁令 #12 + #13）
│       ├── banned-words.md / red-line-protocol.md / performance-injection-protocol.md
│       └── data-brain-manifest.md
│
├── 03-production-line/         # 腳本檔（ready-to-shoot / done）
├── 00-control-center/          # 待辦 + legacy（todos.json 已接手）
├── 07-changelog/               # 系統變更歷史
│
├── docs/
│   ├── contracts/              # 8 份共享契約（skill-io / lessons / pipeline / todos / sync-protocol / performance-patterns / video-ops-cli / agent-collaboration）
│   └── references/             # 8 份人看文件（skill-architecture-principles / skill-consolidation-map / sync-sop / design-lineage / production-details / system-maintenance / verifier-scores-audit / worktree-guide）
│
├── scripts/
│   ├── ops/video-ops.py        # 核心 CLI（影片 / 靈感 / lessons / todos）
│   │   └── lib/                # 17 個模組（pipeline / backfill / patterns / lessons / hardening / schema_drift / ...）
│   ├── libs/brain_loader.py    # 統一 Step 0 載入 adapter
│   ├── engine/                 # bump_engine + engine_version_check
│   ├── lint/                   # rules-lint + skill-io-lint + pre-commit-engine-check
│   ├── bootstrap/              # bootstrap-client.sh + reset-operator
│   └── utils/                  # sync-to-sheets + sync-engine
│
├── tests/                      # 74 檔、629 cases
└── .github/workflows/
    ├── rules-lint.yml           # Lint + pytest + validate-all
    ├── engine-version-check.yml # semantic_contracts scope 改觸 bump engine_version（factual_contracts 不觸、v5.95+ 分層）
    ├── territory-lint.yml       # Claude × Codex 領土邊界 CI（CLAUDE.md 禁令 #8 硬化）
    └── sync-*.yml               # Sheets / README 同步
```

## 核心架構：多層 SSoT

系統有 6 個 SSoT、各自明確職責：

| SSoT | 檔案 | 內容 |
|------|------|------|
| 狀態 | `data/<op>/pipeline.json` | 影片 + 靈感狀態機、門檻、合法轉換 |
| 學習 | `data/<op>/lessons.json` | 錯誤 / 成功 pattern、v2.0 3 態 schema（soft / hardened / archived）|
| 追蹤 | `data/<op>/todos.json` | 待辦（v4.39+ 取代 markdown 檔）|
| 硬化 | `data/<op>/hardening-archive.json` | `/harden` 成功記錄（v4.67 queue 退役、source="dialog"）|
| 品牌 | `01-data-brain/brand.md` + `cases.md` | 人設 + 案例（brand.md 改 lazy load、skill 跑時 brain_loader 載 / 對話需要時 Read、v4.62+ 全文注入退役）|
| 引擎 | `engine-manifest.json` | `_meta.engine_version` + `semantic_contracts` / `factual_contracts` / `internal_files` 三層（v4.65+ 兩層、v5.95+ contract 分層）|

AI 讀這 6 個 SSoT 即知道系統當下完整狀態 — 不需額外規則檔。

## 硬化（`/harden` 對話內 skill）

自我進化核心、Stage D v4.64 建立、Stage F v4.67 退役 queue-based orchestrator 後為唯一硬化入口。

### 觸發

Kai 在對話中說「升 L-XXXX 為 test」或「硬化這個」、Claude 當場執行：

1. 讀 lesson `pattern` + `counter_pattern`、草擬 artifact
2. 展示 draft + target path、Kai 確認
3. 寫檔（5 種 path：`test` / `lint` / `claude_md` / `workflow_md` / `brand_md`）
4. 跑 validator（pytest / rules-lint）
5. 成功 → lesson `stage = "hardened"` + 寫 `hardening-archive.json`（source="dialog"）
6. 失敗 → lesson 保留 `soft`、不污染狀態

### 為何 v4.67 退役 queue

`hardening-queue.json` 從 v4.8 建立到 v4.67 退役、**0 筆 proposal 實際產出**。observer cron 從未寫檔、Kai 都在線、queue 的「異步累積」價值在本專案場景失效。`/harden` 對話內路徑成為唯一主線。詳見 CHANGELOG v4.67。

## Multi-operator

```bash
# 新增 operator（本 repo 或新 client repo）
bash scripts/bootstrap/bootstrap-client.sh <operator_name> "<brand_name>"

# 切換 operator（所有 CLI 支援）
python scripts/ops/video-ops.py --operator <name> <command>

# 識別 repo 類型
python scripts/utils/sync-engine.py   # → engine+client | pure-engine
```

`data/.operators.json` 在 `sync_blacklist` 保護下、sync-engine 不覆蓋、永久保留客戶註冊。

## 生產路線

### 完整路線

```
丟靈感 → 整理 → 確認要拍 → 標題 → 腳本（generation mode=dual-track）
        → 品質處理（quality phase=check + fix）→ 存檔 → 拍攝 → 上線 → 回填
```

### 快拍路線

```
已拍完 → 補登 → 上線 → 回填
```

## 使用方式

所有操作透過 Claude Code 對話完成。

### 生產指令

| 輸入 | 動作 |
|------|------|
| `丟靈感：XXX` | pipeline [inbox] |
| `確認要拍：XXX` | 分配 VID → 標題 → 腳本 → 品質 |
| `補登：XXX` | quick-shot 路線 |
| `上線：VID-NNN` | 狀態 → 已上線 |
| `回填` + IG 截圖 | 讀數字 → 分類 → 回填 → 洞察 |
| `看影片清單` / `q` | 依狀態分組 |
| `看靈感箱` / `i` | inbox / selected / cooldown |
| `看待辦` / `t` | pending / in_progress |
| `看 lessons` | stage 分佈（soft / hardened / archived）|

### 生成指令（舊 keyword 經 stub redirect 到 vNext 主體）

| 輸入 | 落在 vNext |
|------|-----------|
| `確認要拍：XXX` | generation mode=dual-track |
| `產出變體：XXX` | generation mode=variant |
| `系列：XXX` | generation mode=series |
| `訪談：XXX` | generation mode=interview |
| `knowledge：XXX` | generation mode=viral |
| `下週要拍什麼` / `discovery` | discovery（外部 + 大腦交互推薦）|
| `標題：XXX` / `金句：XXX` | quality template（title / hook） |
| `驗證：[腳本]` / `humanize：[腳本]` | quality phase=check / phase=fix |

### 系統指令

| 輸入 | 動作 |
|------|------|
| `記錯：XXX` | lessons.json（origin=mistake） |
| `/harden L-XXXX <path>` | 對話內一站式硬化（test / lint / claude_md / workflow_md / brand_md） |
| `待辦：XXX` | todos.json（T-NNNN）|
| `掃描` / `/scan` | 責任區深度掃描 → Top3 報告 |
| `掃描 全修` | 直接修改到完成 |
| `語音筆記` | 附音檔 → 轉文字 → 自動分流 |
| `填大腦` | 數據大腦填充引導 |
| `同步全部` | → Google Sheets |

## 學習閉環（6 個迴圈）

1. **生成學習** — Kai 選標題 / 金句 / 版本 → 偏好累積 → 推薦加權
2. **表現學習** — 回填數據 → 成功 / 失敗模式自動提取 → 勝率 + 信心等級
3. **品質沉澱** — verifier 分數累積 → 重複問題自動提議 lesson（`origin=verifier`）
4. **偏差校準** — 字幕 vs 腳本比對 → 拍攝偏好 → 回饋生成語感
5. **對話內硬化**（v4.64+ 取代 v7.0 queue-based orchestrator、v4.67 整層退役）— Claude 在對話中主動判斷 → Kai 同意 → `/harden` 當場寫 test/lint/CLAUDE.md 禁令/workflow.md 規則/brand.md → validator 跑 → lesson stage 升 hardened
6. **Adoption gate**（v4.18+、CLAUDE.md 禁令 #9）— SessionStart hook 列出待決事項（回填到期 / 待辦逾期 / 大腦過期）→ Kai 必回 `處理` / `defer` / `skip` 才能進新任務、避免「警告印了沒人動」衰退

## Skill 架構（vNext 5 核心 + harden + skill-creator = 7）

vNext 收斂自 14 個既有 skill、合併為 5 個核心責任區（v5.39 Phase 3+4 落地、v5.40 配套 register、v5.42 Phase 5 真退役整刪 12 個目錄、v5.52 stable）。

### vNext 5 核心 skill

| Skill | 版本 | 用途 |
|-------|------|------|
| `orientation` | v2.0（stub）| 任務定型 — 第二輪退役、邏輯落於 `.claude/rules/workflow.md` §Orientation |
| `discovery` | v1.0 | 選題發現（外部熱點 + 大腦交互、3 modes：discover-week / discover-month / discover-trend）|
| `generation` | v1.2 | 內容生產（5 modes：dual-track / variant / series / interview / viral）|
| `quality` | v1.2 | 驗證 + 修（quality-loop pattern、phase=check + phase=fix）|
| `distillation` | v2.0（stub）| 經驗沉澱 — 第二輪退役、三 phase 拆三層（workflow.md §Distillation + hook + `/harden` command）|

**流程**：Orientation → 若 task=找選題 → Discovery → Generation → Quality → Distillation。

### 配套 skill

| Skill | 版本 | 用途 |
|-------|------|------|
| `harden` | v2.0 | 對話內一站式硬化（soft lesson → test/lint/CLAUDE.md/workflow.md/brand.md）|
| `skill-creator` | — | 官方 MCP 內建（封版、不在本系統維護範圍）|

**brain_loader 統一載入**：所有 skill 透過 `scripts/libs/brain_loader.load_for_skill(operator, skill_name, mode=, phase=)` 統一載入 BrainBundle（brand / cases / patterns / lessons / banned_words）。

詳見 `02-skill-factory/README.md` v6.2+ + `docs/references/skill-architecture-principles.md` v1.6+ + `docs/references/skill-consolidation-map.md` v1.1+。

## 品質矩陣（三級）

| 層級 | 觸發 | 處理 |
|------|------|------|
| **L0** | 品牌紅線 / 虛構內容 / 不存在案例 ID / 點名競品 | 重寫（阻塞存檔） |
| **L1** | 語氣 / 素材 / 人設 / 禁用詞 / AI 味 / 格式 | 自動修正或標記 |
| **L2** | 灰色地帶 / 非大腦素材 | 僅提醒 |

## 多代理協作

| 代理 | 責任區 | 職責 |
|------|-------|------|
| **Claude** | `.claude/` / `02-skill-factory/` / `01-data-brain/` / `CLAUDE.md` / `03-production-line/` / `07-changelog/` / `00-control-center/todo/` | prompt / skill / content |
| **Codex** | `scripts/ops/` / `scripts/utils/` / `scripts/lint/` / `scripts/engine/` / `scripts/bootstrap/` / `scripts/libs/` / `.github/workflows/` / `tests/` / `data/**/*.json` | backend / CI / tooling |
| **共享** | `docs/contracts/`（8 份） | pipeline / lessons / todos / performance-patterns / skill-io / CLI / sync / 協作憲章 |

**領土邊界 CI 硬化**（v4.17+、CLAUDE.md 禁令 #8）：`territory-lint.yml` 比對 PR diff 與 `agent-collaboration.md §9.3` 白名單、違反即 CI red + PR block。例外需 PR body 標 `territory override justified by: <原因>`。

觸發掃描：`掃描` / `/scan` → 各代理讀憲章 → 掃描自己責任區 → Top3 報告（第 5 段反向委託給對方代理、達成閉環）。

## Safety & Quality

### 4 層防漂移

1. **Pre-commit**（本地）：`pre-commit-engine-check.py` 擋 engine scope 改但未 bump engine_version
2. **CI lint**：`rules-lint.py --ci`（含 skill-io-lint v1.0 + lesson-aware gate）
3. **engine-version-check**：engine scope 改必 bump + CHANGELOG 條目
4. **validate-all**：schema drift 三層分級（breaking / non-breaking / info）+ pipeline 跨檔一致性

### 受保護路徑

`CLAUDE.md` / `.claude/rules/**` / `.claude/skills/**` / `.claude/commands/**` / `.claude/settings.json` 透過 `.claude/settings.json` permissions.deny 攔截 Edit/Write tool。Kai 明確授權後、Claude 用 Python 繞過寫入（不經過 Edit tool、在 permission 意圖內）。

## Google Sheets

Sheets 是「公佈欄」— AI 不依賴它、Kai 用手機看。5 個分頁自動同步。

## 測試 + CI

```bash
pytest tests/ -v                             # 74 檔、629 cases
python scripts/lint/rules-lint.py --ci       # 跨檔 lint（含 skill-io + lesson-aware）
python scripts/utils/check-version-sync.py   # Skill 版本號一致性
python scripts/engine/engine_version_check.py --base origin/main --head HEAD
python scripts/ops/video-ops.py validate-all # JSON 一致性 + schema drift
```

### GitHub Actions

- `rules-lint.yml`：Lint + pytest + validate-all（PR + push）
- `engine-version-check.yml`：`semantic_contracts` scope 改觸 bump + CHANGELOG（`factual_contracts` 不觸、v5.95+ 三層化、解 fact-realign 連環撞 release 流程）
- `territory-lint.yml`：Claude × Codex 領土邊界檢查（v4.17+、CLAUDE.md 禁令 #8）
- `sync-to-sheets.yml` / `sync-readme-to-main.yml`：資料同步

## 版本歷史

| 版本 | 日期 | 主題 |
|------|------|------|
| **v8.10** | 2026-05-15 | **Contract layering wording align**（engine v5.93 → v5.95、PR #443 把 `contract_files` 拆 `semantic_contracts` + `factual_contracts` 後、README L89 / L105 / L288 三處仍寫舊 `contract_files` / 兩層字眼、對齊新 schema；本檔在 factual_contracts、bump 8.9 → 8.10 不觸 engine bump、為 v5.95 紅利首次驗證）|
| **v8.9** | 2026-05-15 | **Post-merge fact realignment v3**（engine v5.90 → v5.93、3 處 engine 版本對齊：line 4 / line 23 / line 313；同期合修 design-lineage.md §brand.md SSoT heading 對齊 v4.62+ lazy load 退役方向 + workflow.md §Codex 待實作 CLI → §evidence 累積 CLI Codex 已實作；workflow.md 因 `.claude/**` native deny 拆 follow-up commit b608c57 完成 3/3）|
| **v8.8** | 2026-05-11 | **Post-merge engine sync**（engine v5.89 → v5.90、personas/ 拆分 PR #431 merged、3 處 engine 版本對齊：line 4 / line 23 / line 312）|
| **v8.7** | 2026-05-08 | **Post-merge fact realignment v2**（engine v5.87 → v5.89、修 v8.5 漏改的 tests `69 檔/591 cases` → `71 檔/608 cases`（line 86 + 278）+ 3 處 engine 版本對齊：line 4 / line 23 / line 311）|
| **v8.6** | 2026-05-06 | **Post-merge fact realignment**（engine v5.80 → v5.87、tests 591→608 / 69→71 檔、workflow.md v2.25 → v2.30、修 README 多處 stale：brand.md 全文注入 → lazy load 描述對齊 v4.62 + 3 處 engine 版本 + 1 處 workflow 版本）|
| **v8.5** | 2026-05-03 | **Codex CLI 整合軸 5 PR 後對齊**（engine v5.75 → v5.80、PR #397/#398/#399/#400/#402 加 AGENTS.md + agent-dispatch.md v1.2 + workflow.md v2.28 + .githooks/pre-commit、修 README 4 處 stale 引擎引用、AGENTS.md §11 v1.0+ → v1.2+）|
| **v8.4** | 2026-04-30 | **Post-merge version align**（engine v5.74 → v5.75、修 v8.3 內 4 處 engine 版本自我引用錯 v5.73 → v5.74/v5.75、補 02-skill-factory/README v6.1→v6.2 漏標兩處）|
| **v8.3** | 2026-04-30 | **Sleep-mode fact realignment**（engine v5.64 → v5.74、tests 64→69 / 579→591 cases、Python 12,800→13,600 行、skill 版本表對齊 SKILL.md frontmatter、workflow.md v2.24→v2.25、契約數 8→9）|
| v8.2 | 2026-04-28 | engine v5.64 文件層 fact realignment（README + 02-skill-factory + manifest + rules-lint paths 死角）|
| **v8.1** | 2026-04-25 | **Phase 5 真退役**（engine v5.42、12 個退役 skill 目錄整刪、SSoT 段落遷至 shared-references/、剩 vNext 5 + harden + skill-creator = 7）|
| **v8.0** | 2026-04-25 | **vNext 5 核心 skill 收斂**（14 → 5 + 14 stub、CLAUDE.md v4.20 加 5 條禁令 #8-#12、workflow.md v2.22 Adoption-gate + Orientation Phase 1）|
| v7.5 | 2026-04-24 | territory-lint CI 硬化 + lessons schema v2.0 三態（soft / hardened / archived）|
| v7.0 | 2026-04-22 | Orchestrator 完整 + multi-operator + 契約 v1.0 stable |
| v6.3 | 2026-04-20 | /scan 責任區掃描 + Codex 共享契約 |
| v6.x | 2026-04 | Skill thinning + evals 擴充 |
| v5.x | 2026-03 | Skill 系統分層 + 表現模式注入 |
| v4.x | 2026-02 | Control Center + 角色權限 |
| v3.x | 2026-01 | Sheets 雲端看板 |

完整變更見 `07-changelog/CHANGELOG.md`（最新 engine v5.93）。
