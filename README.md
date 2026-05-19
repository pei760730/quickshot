# quickshot — 短期客戶短影音生產 template

> AI 驅動的短影音內容生產系統、**短期客戶（≤30 天驗證型）精簡版**。
> version: 1.0 (short-term template) | last_updated: 2026-05-17

## 用途

給需要在 30 天內驗證的短影音內容客戶用。從 KaiOS 完整版（KaiOS-ContentSystem）砍掉長期客戶才需要的基礎建設、留下短期客戶開拍即用的核心。

**不適用**：長期經營（≥90 天）、多客戶併行管理、需要引擎升級同步流的場景 — 那種請用 KaiOS-ContentSystem 主 repo。

## 從 KaiOS 砍掉的 3 大模組

| 模組 | 為何砍 |
|------|-------|
| **sync-engine 整套**（commands / scripts / workflows / docs） | 短期客戶不需要從主引擎拉同步、用什麼就是什麼 |
| **雙 agent 協作**（Claude × Codex、territory-lint） | 短期客戶一個 Claude 跑通即可、不需員工分工 |
| **Adoption-gate hook** | gate 化是為了解「警告衰退」、≤30 天客戶不會累積到那階段 |

砍掉的細節見 PR #1 的 Stage 1 / Stage 2 commits。

## 為短期客戶新增的

| 項目 | 內容 |
|------|------|
| **brand.md [2.5] 高流量素材庫** | 個人故事 / 行業誤會 / 圈內事、附 Hook 適用 + 可拍嗎 兩 tag — 短期客戶開拍主彈藥 |
| **brand.md sections 瘦身** | [10] 長期目標 → §90 天里程碑、[11] 季節性 → optional、[12] 其他 → 結構化 FAQ |
| **冷啟動萃取 workflow** | `.claude/rules/workflow.md` §冷啟動萃取、Claude 幫客戶從歷史素材一次性盤點候選清單、Kai 三色標記後寫入 brand.md |

## 核心架構

```
quickshot/
├── CLAUDE.md                   # AI 開機記憶（9 條禁令 + 資料地圖）
├── CLAUDE.local.md             # 此 repo 品牌身份（短期客戶可自填）
├── .claude/
│   ├── rules/workflow.md       # 對話開頭檢查 + 設計原則 + 冷啟動萃取
│   ├── rules/permissions.md    # 受保護路徑
│   ├── hooks/session-start.sh  # 品牌速查注入
│   ├── commands/{harden,scan}.md
│   └── settings.json           # deny list 保護 CLAUDE.md / .claude/**
│
├── 01-data-brain/              # 品牌知識
│   ├── index.md                # 資料地圖
│   ├── brand.md                # 14 sections schema（MVP 5 個：[0][1][2.5][3][5]、客戶 onboarding 時填）
│   ├── cases.md                # 真實案例庫
│   └── transcripts/            # 語音 / 訪談原文
│
├── data/
│   ├── .operators.json         # operator 註冊
│   ├── {operator}/             # 每 operator 一個 dir（在 data/.operators.json 註冊後建立）
│   │   ├── pipeline.json       # 狀態 SSoT
│   │   ├── lessons.json        # 學習 lessons
│   │   ├── todos.json          # 待辦
│   │   └── hardening-archive.json
│   └── template/               # 新客戶 bootstrap 模板
│
├── 02-skill-factory/           # 8 個 Skill（generation / quality / discovery / harden / ...）
├── 03-production-line/         # 腳本（ready-to-shoot / done）
├── docs/contracts/             # 共享 schema（pipeline / lessons / todos / ...）
├── scripts/                    # ops CLI + utils + lint
├── tests/                      # pytest suite（lint + JSON 一致性 + e2e、跑 `pytest tests/`）
└── .github/workflows/rules-lint.yml   # Lint + pytest + validate-all
```

## 使用方式

所有操作透過 Claude Code 對話完成。

### 生產指令

| 輸入 | 動作 |
|------|------|
| `丟靈感：XXX` | 進 inbox |
| `確認要拍：XXX` | 分配 VID → 標題 → 腳本 → 品質 |
| `補登：XXX` | 已拍完路線（quick-shot）|
| `上線：VID-NNN` | 狀態 → 已上線 |
| `回填` + IG 截圖 | 讀數字 → 分類 → 回填 → 洞察 |

### 短期客戶 onboarding（day-1）

新 clone 第一次跑：

| 輸入 | 動作 |
|------|------|
| `/init` / `新客戶開始` / `onboarding` | 5-step bootstrap：品牌名 → operator 註冊 → persona → brand.md MVP → 歷史素材冷啟動 |
| `冷啟動：[音檔/文章/連結]` | Claude 一次轉譯、跨篇盤點、出候選清單供 Kai 三色標記（也可在 `/init` Step 5 觸發）|

完成後跑 `/check` 看大腦健康度、再走 `確認要拍：[第一支主題]` 開拍。
詳見 `.claude/commands/init.md`、`.claude/rules/workflow.md` §冷啟動萃取。

### 系統指令

| 輸入 | 動作 |
|------|------|
| `記錯：XXX` | lessons.json（origin=mistake）|
| `/harden L-XXXX <path>` | 對話內一站式硬化 |
| `待辦：XXX` | todos.json |
| `掃描` / `/scan` | 責任區深度掃描 |
| `語音筆記` + 音檔 | 轉譯 + 自動分流 |

## 測試 + CI

```bash
pytest tests/                                # 全部 pytest（lint + JSON + e2e）
python scripts/lint/rules-lint.py --ci       # 跨檔 lint
python scripts/lint/brand_ref_lint.py        # brand.md section 引用
python scripts/ops/video-ops.py validate-all # JSON 一致性
```

GitHub Actions：`rules-lint.yml`（lint + pytest + validate-all）— 每 PR / push 跑。

## 關聯

- **上游**：KaiOS-ContentSystem（長期經營版本、本 template 從中精簡而來）
- **客戶身份**：`CLAUDE.local.md` + `data/.operators.json`
