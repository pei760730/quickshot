# video-ops.py CLI Contract

> version: 1.16 | last_updated: 2026-05-08
> 角色：Claude (caller) × CLI 層 (implementer)

入口：`python scripts/ops/video-ops.py [--operator <代號>] <command> [args]`

**注意**：合法 operator 由 `data/.operators.json` 動態決定（每個 repo 在 onboarding 時自己註冊）。

---

## 全域規則

| 規則 | 定義 |
|------|------|
| 成功 | exit code 0 + stdout 以 `✅` 開頭 |
| 失敗 | exit code 1 + stdout 以 `❌` 開頭 |
| 操作員 | `--operator <代號>`（預設 `kai`、合法值讀 `data/.operators.json`）|
| Claude 側依賴 | **只看 exit code**，不 parse stdout 內容做邏輯判斷 |

---

## 命令列表

### 靈感操作

| 命令 | 用法 | 說明 |
|------|------|------|
| `add-idea` | `add-idea --title "標題" [--shelf-life evergreen\|timely\|trending]` | 新增靈感到 inbox |
| `list-ideas` | `list-ideas [--status inbox\|selected\|cooldown]` | 列出靈感 |
| `transition-idea` | `transition-idea IDEA-NNN --to STATUS` | 靈感狀態轉移 |
| `confirm` | `confirm IDEA-NNN --title "標題"` | 靈感→待拍（分配 VID） |

### 影片操作

| 命令 | 用法 | 說明 |
|------|------|------|
| `list` | `list [--status STATUS]` | 列出影片 |
| `get` | `get VID-NNN` | 查詢單支影片 |
| `next-vid` | `next-vid` | 查詢下一個可用 VID 編號 |
| `add` | `add --topic "主題" [--tag "標籤"] --title "標題" [--source pipeline\|quick-shot] [--initial-status STATUS]` | 新增影片（未帶 tag 會警告並用預設值） |
| `transition` | `transition VID-NNN STATUS / transition VID-NNN --to STATUS` | 影片狀態轉移（相容位置參數 + flag 形式） |
| `update-date` | `update-date VID-NNN --publish-date YYYY-MM-DD` | 更新上線日期 |
| `set-hook-type` | `set-hook-type VID-NNN --hook-type B1\|B2\|B3\|D1\|D2\|D3\|D4\|D5` | 回填既有影片的 hook_type（v1.11+、Wave 2 存量補齊用；合法值讀 `_meta.valid_hook_types`） |
| `set-trace` | `set-trace VID-NNN --trace '{...}' [--no-overwrite]` | 回填既有影片的 generation_trace（v1.12+、Learning-loop 契約；`--no-overwrite` 在既有 trace 時會拒絕覆寫並 exit 1；schema 見 `docs/contracts/skill-io-schema.md §Learning Loop Contract`） |
| `add-transcript` | `add-transcript VID-NNN --text "逐字稿"` | 新增逐字稿 |

### Quick-shot

| 命令 | 用法 | 說明 |
|------|------|------|
| `quick-add` | `quick-add --topic "主題" --title "標題" [--status 剪輯中\|已上線] [--initial-status 剪輯中\|已上線] [--hook-type B1\|B2\|B3\|D1\|D2\|D3\|D4\|D5]` | 補登影片（兩種 flag 皆支援，優先建議 `--initial-status`；`--hook-type` v1.10+ 可選、合法值讀 `_meta.valid_hook_types`；workflow.md 要求 Claude 每次補登前先問） |
| `batch-quick-add` | `batch-quick-add --items '[{...}]'` | 批次補登（item 可帶 `hook_type` 欄位、同 `--hook-type` 規則） |
| `query-pending-scripts` | `query-pending-scripts` | 查詢待補腳本的影片 |

### 腳本存檔

| 命令 | 用法 | 說明 |
|------|------|------|
| `save` | `save VID-NNN --script-path "路徑" --title-type T? --hook-type B?/D? --version V? --verifier-prediction high/normal/low --trace '{...}' [--verifier-scores '{"conflict_score":8,"retention_prediction":"A","ai_residue_count":0,"data_consistency":true,"format_complete":true,"pass_count":"5/5"}'] [--patterns-injected "B2,D3"] [--risk-patterns-avoided "開場太慢"] [--persona-deviation-score N]` | 存檔（必填前 6 項；§10.1 規格要求 `--trace` 永遠必填，CLI 會在缺少時 exit 1；`--trace` 接受完整 generation_trace JSON 並依 Learning-loop schema 驗證；若提供 `--verifier-scores` 會同回合記錄，否則在缺少時提示補記） |
| `record-verifier-scores` | `record-verifier-scores VID-NNN --conflict-score N --retention-prediction LEVEL --ai-residue-count N --data-consistency true/false --format-complete true/false --pass-count "N/5"` | 記錄品質細項（六欄皆必填；`conflict-score` 0~10、`ai-residue-count` ≥0、`pass-count` 需符合 `N/5` 且 N=0~5） |

### 回填 + 學習

| 命令 | 用法 | 說明 |
|------|------|------|
| `backfill` | `backfill VID-NNN --views N --retention-3s N --completion-rate N [--engagement-rate N] [--likes N] [--comments N] [--shares N] [--saves N] [--profile-clicks N] [--reposts N] [--new-followers N] [--reached-accounts N] [--video-length-seconds N] [--avg-watch-seconds N] [--profile-source-pct N]` | 回填表現數據 |
| `extract-learning` | `extract-learning VID-NNN [--opening CODE] [--cta CODE] [--hook "金句"] [--formula "公式"] [--failure-mode "模式"] [--failure-detail "細節"]` | 手動提取學習 |
| `cleanup-formulas` | `cleanup-formulas` | 清理無證據公式 |

### lessons 管理

| 命令 | 用法 | 說明 |
|------|------|------|
| `lessons list` | `lessons list [--origin ORIGIN] [--stage STAGE]` | 列出 lessons（stage: soft / hardened / archived） |
| `lessons add` | `lessons add --pattern "..." --origin <mistake\|humanizer\|quality\|verifier\|deviation\|manual> [--stage soft] [--scope "generation"] [--counter-pattern "..."] [--evidence-vid VID-001] [--notes "..."]` | 正式新增 lesson（重複 key 會合併 evidence） |
| `lessons add-evidence` | `lessons add-evidence L-XXXX --vid VID-NNN` | 把 VID 加入既有 lesson 的 evidence list（v1.15+、P2 lesson-pressure hook 配套；idempotent、重複 no-op；不存在 lesson exit 1）|
| `lessons stats` | `lessons stats` | 列出 stage 分佈（soft / hardened / archived） |
| `lessons propose-hardening` | `lessons propose-hardening` | 列出 soft 且有 counter_pattern 的候選（v4.63+ 不靠 hit_count 門檻） |
| `lessons archive` | `lessons archive L-XXXX [--reason "..."]` | 歸檔 lesson（stage → archived） |

### 偏差追蹤

| 命令 | 用法 | 說明 |
|------|------|------|
| `record-deviation` | `record-deviation VID-NNN --level minimal/moderate/significant [--changes '[...]']` | 記錄拍攝偏差 |
| `diff-script` | `diff-script VID-NNN --subtitle '字幕全文'` | 腳本 vs 字幕比對 |
| `analyze-deviations` | `analyze-deviations` | 偏差分析報告 |

### 維護

| 命令 | 用法 | 說明 |
|------|------|------|
| `list-topics` | `list-topics` | 列出已佔用主題（去重用） |
| `validate` | `validate` | 驗證 pipeline.json schema |
| `validate-all` | `validate-all` | 跨檔驗證（含 performance-patterns） |
| `migrate` | `migrate` | 自動補齊缺失欄位 |
| `renumber` | `renumber` | 重新編號 VID |
| `pipeline-stats` | `pipeline-stats` | 轉化漏斗統計 |

> **v4.67 退役**：原 `hardening list/add/approve/reject/defer/execute/observe` 5 個 queue-based CLI 已整層退役（queue 從 v4.8 建到 v4.67 從未產出 proposal、實證失效）。硬化主線改 `/harden` 對話內 skill（見 `02-skill-factory/harden/SKILL.md`）。

---

## 修改規則

- **新增命令**：CLI 層實作 + 更新此文件 + 同步 workflow.md
- **修改參數**：更新此文件 + 確認 Claude 側 workflow.md 同步
- **刪除命令**：必須先確認 Claude 側無引用
- **exit code / stdout 格式**：不可變更（✅/❌ + exit 0/1）
