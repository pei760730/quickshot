# 短期客戶結束清洗 SOP

> version: 1.0 | last_updated: 2026-05-17
> 對應 `.github/workflows/wipe-client.yml` + `scripts/utils/wipe_client.py`

## 何時用

短期客戶（≤30 天驗證型）結束、repo 要清回 template 狀態、給下個客戶用。

**不適用**：暫停 / 雪藏 / 想保留客戶資料給未來查 — 那種就放著、不要清洗。

## 設計原則

| 原則 | 怎麼做 |
|------|-------|
| **半清不全清** | 保留 git history、清檔案內容、加 git tag 標終點。任何時候可 `git checkout <tag>` 還原 |
| **保留邊用邊優化的功能** | `hardening-archive.json` 完整保留、`lessons.json` 保留 `stage=hardened` 且不含 operator / brand 名的條目 |
| **必清客戶 PII** | 數據大腦 brand.md / cases.md / interview-bank.md / transcripts、CLAUDE.local.md、03-production-line 腳本、00-control-center 待辦 |
| **三層確認** | (1) 表單必填 operator (2) 必輸入 `WIPE <operator>` 字串 (3) dry_run 預設 true、明示 toggle off 才執行 |
| **不 auto-merge** | 清洗開 PR、Kai 看完 diff 才 merge、給逃跑窗口 |

## 執行步驟

### 1. 跑 dry-run 預覽

1. 開 GitHub → Actions → **Wipe client data** workflow
2. 點 **Run workflow**、填表：
   - `operator`：客戶 operator 名（例 `longbro`）
   - `confirmation`：輸入 `WIPE longbro`（注意 case、`WIPE` 全大寫、空格、operator 名小寫）
   - `dry_run`：**保持 true**（預設）
3. 跑完後下載 artifact `wipe-preview-<operator>`、看 JSON 報告：
   - `files_to_clear`：將清的檔案清單 + 大小
   - `lessons_filter`：將保留 / 砍掉的 lessons + 原因
   - `preserved`：將保留的計數

### 2. 確認後執行真清

1. 同 workflow、再點 **Run workflow**、同樣填 operator + confirmation
2. **toggle `dry_run` 為 false**
3. workflow 跑：
   - 建 git tag `client-end-<op>-YYYYMMDD-HHMMSS` + push（備份點）
   - 建分支 `template-reset/YYYYMMDD-HHMMSS`
   - 跑 `wipe_client.py` 清檔案 + filter lessons
   - 追加 CHANGELOG entry
   - commit + push 分支
   - 開 PR `template-reset/...` → `main`

### 3. Review PR + merge

1. 看 PR diff、確認：
   - 引擎層完全沒動（`.claude/` / `02-skill-factory/` / `scripts/` / `docs/` / `tests/` / `.github/`）
   - 數據大腦清空（brand.md / cases.md 回 template、transcripts/ 空）
   - 客戶身份清空（CLAUDE.local.md 回 template、`data/.operators.json` 移除 operator entry）
   - 腳本清空（03-production-line / 02-ready-to-shoot / 03-done 空）
   - 學習資料保留（lessons.json `stage=hardened` 條目、hardening-archive.json 完整）
2. 確認沒問題、merge PR 到 main

### 4. （可選）下個客戶 onboarding

清完後 repo 是空白 template 狀態。下個客戶要開始時：

```bash
# 1. 編輯 data/.operators.json、加入新 operator entry：
#    "operators": {
#      "newclient": {
#        "display_name": "New Client",
#        "brand": "新品牌名",
#        "data_dir_rel": "data/newclient",
#        "production_dir_rel": "03-production-line",
#        "enabled": true,
#        "created_at": "<今天>"
#      }
#    }

# 2. 建客戶資料 dir、從 template 複製
cp -r data/template data/newclient

# 3. 改 CLAUDE.local.md 品牌名（從 template/CLAUDE.local.md 為起點）
# 4. 開拍：跟 Claude 說「冷啟動：[歷史素材]」、進冷啟動萃取流程
```

## 還原（誤清救回）

```bash
# 看所有 wipe tag
git tag -l 'client-end-*'

# 回到清洗前的 state
git checkout client-end-longbro-20260517-143052

# 想完整重來：開新 branch、推 PR 還原 main
git checkout -b restore-longbro client-end-longbro-20260517-143052
git push -u origin restore-longbro
# 然後在 GitHub 開 PR → main
```

## 清洗範圍對照

### 清掉的（檔案 / 內容）

| 路徑 | 動作 |
|------|------|
| `01-data-brain/brand.md` | 回 `01-data-brain/template/brand.md` |
| `01-data-brain/cases.md` | 回 `01-data-brain/template/cases.md` |
| `CLAUDE.local.md` | 回 `01-data-brain/template/CLAUDE.local.md` |
| `01-data-brain/brand-summary.md` | 刪 |
| `01-data-brain/interview-bank.md` | 刪 |
| `01-data-brain/transcripts/*.md` | 清空（dir 保留）|
| `03-production-line/02-ready-to-shoot/*` | 清空 |
| `03-production-line/03-done/*` | 清空 |
| `00-control-center/` | 整 dir 刪（KaiOS 殘留待辦 / 報告）|
| `data/{op}/pipeline/` | 回 `data/template/pipeline/`（sharded SSoT；legacy 單檔 `pipeline.json` 已被 `.gitignore` 防誤建）|
| `data/{op}/todos.json` | 回 `data/template/todos.json` |
| `data/{op}/performance-patterns.json` | 回 template（client-specific 統計、跨客戶污染）|
| `data/{op}/brand-monitor.json` | 回 template |
| `data/{op}/social-followers.json` | 回 template |
| `data/{op}/topic-history.json` | 回 template |
| `data/.operators.json` | 移除該 operator entry |

### 過濾的（保留檔、過濾條目）

| 路徑 | 過濾條件 |
|------|---------|
| `data/{op}/lessons.json` | 保 `stage=hardened` 且 pattern/counter_pattern 不含 operator/brand 名的條目；其餘砍 |

### 完全保留的

| 路徑 | 理由 |
|------|------|
| `data/{op}/hardening-archive.json` | 純引擎層硬化成功紀錄、不含客戶 PII |
| `data/{op}/hardening-queue.json` | 同上（v4.67 後實際 0 entries）|
| `data/skill-memory/` | 跨客戶通用、official MCP 管理 |
| `.claude/` 全部 | 引擎規則、hook、設定 |
| `02-skill-factory/` 全部 | Skill 定義 |
| `scripts/` 全部 | 工具程式 |
| `docs/` 全部 | 文檔 |
| `tests/` 全部 | 測試 |
| `.github/` 全部 | CI |
| `data/template/` | 模板（清洗的還原來源）|
| `01-data-brain/index.md` | 資料地圖 SSoT |
| `01-data-brain/README.md` | 資料夾 README |
| `07-changelog/CHANGELOG.md` | 歷史紀錄 + 加入 wipe entry |

## 失敗處理

workflow 步驟失敗會：
1. 不 auto-rollback（git tag 已 push 不能撤）
2. 留 branch 不刪
3. 自動開 GitHub Issue 通知 Kai
4. Kai 手動：(a) 看 workflow log 找根因 (b) 修 script 或設定 (c) 重跑

## 安全防護總覽

| 層 | 機制 |
|---|------|
| L1 | workflow 只能在 `main` 跑（`if: github.ref == 'refs/heads/main'`）|
| L2 | confirmation 必須等於 `WIPE <operator>` 完整字串、不能省略 / 改大小寫 |
| L3 | dry_run 預設 true、要明示 toggle |
| L4 | 真清前自動 push backup tag（不可逆操作有 fallback）|
| L5 | 不 auto-merge、開 PR 給 Kai 看 diff |
| L6 | 失敗自動開 Issue 通知 |

## 對應規則

- 對應 CLAUDE.md 禁令 #3「不可逆操作強制確認」
- 對應 `.claude/rules/workflow.md` §設計原則 Mode Y（警告 → 自動修復 → 通知 → gate）
- 對應 `data/.operators.json` schema（operator 註冊）
