# AI System Upgrade Report

> Sleep Mode v3.0 一輪、未 commit / 未 push。

## Base

- Branch: `claude/repo-optimization-lWYux`
- HEAD before changes: `7802a89` (`Merge pull request #9 from pei760730/claude/workflow-last-updated`)
- HEAD after changes: `7802a89`（無 commit）
- Repo root: `/home/user/quickshot`
- Time: 2026-05-18
- Working tree before: clean
- Working tree after: 6 files modified（皆未 commit）

## Project snapshot

- Project type: AI 驅動的短影音生產 template（KaiOS-ContentSystem 短期客戶 ≤30 天精簡版）
- Primary language: Python 3.11
- Package manager: pip + `requirements-dev.txt`
- Main entrypoints:
  - `scripts/ops/video-ops.py`（ops CLI、所有狀態寫入唯一入口）
  - `scripts/lint/rules-lint.py` / `brand_ref_lint.py`（lint）
  - `scripts/utils/sync-to-sheets.py`（GH Action 觸發、人工不直接跑）
  - Claude Code slash commands `/init` `/check` `/scan` `/harden`
- Automation:
  - `.github/workflows/rules-lint.yml`（lint + pytest + validate-all、每 PR 跑）
  - `.github/workflows/sync-to-sheets.yml`（push 到 main / claude/* 自動 sync）
  - `.github/workflows/wipe-client.yml`（manual dispatch、三層安全）
  - `.githooks/pre-commit`（本機 territory check，需 `git config core.hooksPath .githooks`）
  - `.pre-commit-config.yaml`（opt-in `pre-commit install` 後啟用）
  - `.claude/hooks/{session-start,post-tool-use,stop}.sh`（Claude Code session）
- Validation commands available: `pytest tests/` / `ruff check --select E9,F63,F7,F82 scripts tests` / `python scripts/lint/rules-lint.py --ci` / `python scripts/lint/brand_ref_lint.py` / `python scripts/ops/video-ops.py validate-all`
- AI instruction files: `CLAUDE.md` / `CLAUDE.local.md` / `.claude/rules/{workflow.md,permissions.md}` / `.claude/skills/*.md` / `.claude/commands/*.md`
- High-risk areas: `.claude/**`（受保護、deny list、需 Kai 確認）/ `CLAUDE.md`（同）/ `data/{operator}/pipeline/` shards

## What I inspected

- Git state + branch + remote
- Top-level dir 結構（19 個 root entries）
- 215 tracked files
- 全套驗證跑通基線：`pytest` (537 passed / 1 skipped) / `ruff` critical / `rules-lint --ci` / `brand_ref_lint` / `validate-all` / `bash -n` 所有 hook / `compileall scripts`
- 4 個 workflow YAML
- 3 個 hook scripts + `.githooks/pre-commit` + `.pre-commit-config.yaml`
- `CLAUDE.md` / `CLAUDE.local.md` / `README.md` / `.claude/rules/workflow.md` / `01-data-brain/index.md` / `01-data-brain/README.md` / `02-skill-factory/README.md`
- `data/.operators.json` + `data/default/*`
- 跨 repo grep：`pre-commit-engine-check` / `engine-manifest` / `agent-collaboration` / `territory-lint` / `禁令 #11/#12/#13` / `codex` 使用情境

## System-level issues found

### High risk

**H1. `.pre-commit-config.yaml` 指到不存在的 script**
- 原本 `entry: python scripts/lint/pre-commit-engine-check.py`、檔案不在 repo。
- 影響：任何人跑 `pre-commit install` 後、commit 會被 KaiOS 殘留的 engine-version-gate 攔下、訊息不知所云。
- 已修：替換為兩個既有的有效 lint（`rules-lint.py --ci` + `brand_ref_lint.py`）、跟 CI 對齊。

### Medium risk

**M1. `.githooks/pre-commit` 錯誤訊息指向已退役的 KaiOS 檔**
- 違規時的解法文字提到 `.github/workflows/territory-lint.yml` + `docs/contracts/agent-collaboration.md §9.3`、兩者都已隨 README 「砍掉的 3 大模組」一同退役、本 template 內並不存在。
- 影響：違規時 Claude / Kai 找不到提示的檔、可能誤判 repo 損壞或誤建假檔。
- 已修：訊息改指本檔內 regex；header / inline 註解更新為 quickshot template 範圍說明。
- 注意：whitelist regex 仍保留 `engine-manifest\.json` / `HOME\.md` / `AGENTS\.md` / `00-control-center/` 等 KaiOS 專屬路徑，這些 regex 在 quickshot 不會匹配任何檔、屬無害死碼、保留為向後相容。

**M2. `02-skill-factory/discovery/SKILL.md` brand-refs 缺 [3]**
- frontmatter 宣告 `brand-refs: [4, 5, 6, 10, 11, 12]`、L58 引用 `brand.md [3] 說話風格`。
- `brand_ref_lint.py` 1 warning（不阻塞、但 CI 噪音）。
- 已修：加入 `[3]`。Lint 現為 0 warnings。

**M3. 禁令編號 drift（部分修、部分文件受保護）**
- `CLAUDE.md` 現存禁令 #1-#9。
- 但多處下游引用沿用 KaiOS 編號 #11 / #12 / #13：
  - 已修（無保護）：
    - `02-skill-factory/README.md` L41：禁令 #12 → 禁令 #8（加註對應 KaiOS #12）
    - `02-skill-factory/shared-references/README.md` L25：同上
  - **未修（受 deny list 保護、需 Kai 確認）**：
    - `.claude/rules/workflow.md` L135, L144, L145, L146, L148, L248, L295：多處引用 #11 / #12 / #13
    - `02-skill-factory/shared-references/skill-design-principles.md` L171, L181, L199, L243, L278, L310（檔案不在 deny、但屬同一份原始引用、未一次到底以免造成檔間不一致；建議和 workflow.md 同時改）
- 影響：未來 Claude Code 看到「禁令 #11 / #12 / #13」會去 CLAUDE.md 找不到。
- 對應動作建議：見「Recommended next actions」。

### Low risk

**L1. README.md 提到「503 cases pytest」、實際 537**
- 已修：改為通用描述「pytest suite」、避免下次 hard-code 數字再 drift。

**L2. `.claude/commands/scan.md` 指向已退役檔（受保護未修）**
- L3 / L7 提到 `docs/contracts/agent-collaboration.md`、本 template 已退役該檔。
- Kai 跑 `/scan` 時、Claude 會去讀不存在的檔。
- 受 `.claude/settings.json` deny list 保護、需 Kai 確認才能改。

**L3. `01-data-brain/README.md` 結構圖列出 `transcripts/`、目錄不存在**
- workflow 內 `語音筆記` / 沉澱流程預設此資料夾。
- `compute_transcripts_health()` 已 graceful handle 不存在情況、首次寫入時自動建立、不會壞。
- 未修：對 KaiOS 行為一致、新客戶第一次跑 `語音筆記` 時自然建立。

**L4. `.github/workflows/sync-to-sheets.yml` 仍含 `00-control-center/**` 在 paths trigger**
- 該目錄不存在於 short-term template、不會匹配任何 push、純死設定。
- 未修：無功能影響。

**L5. `validate-all` schema drift：5 個 NON-BREAKING、4 個 INFO warnings**
- 出處：`docs/contracts/performance-patterns-schema.md` v1.0 → v1.1 type changed Codex → CLI 層（intentional）。
- 屬基線 baseline 已知狀態、不阻塞 CI、保留。

## Changes made

| 檔 | 變更 | 風險 |
|----|------|------|
| `.pre-commit-config.yaml` | 替換掉 KaiOS engine-version-gate 失效 hook、改用既有有效 lint | 行為改變僅在「使用者已跑 `pre-commit install`」時：原本 fail、現在跑兩個 lint；CI 無變 |
| `.githooks/pre-commit` | header / inline 註解 / 違規 footer 訊息改指 quickshot template；whitelist regex **未動** | 行為完全不變、純文字 |
| `02-skill-factory/discovery/SKILL.md` | frontmatter brand-refs 加 `[3]` | 純 metadata 對齊 inline 引用、無功能 |
| `02-skill-factory/README.md` | 禁令 #12 → 禁令 #8（短期 template 編號） | 純文字、無功能 |
| `02-skill-factory/shared-references/README.md` | 同上 | 同上 |
| `README.md` | 移除 hard-coded「503 cases」 | 純文字、無功能 |

## Files changed

```
.githooks/pre-commit                         | 25 +++++++++++++------------
.pre-commit-config.yaml                      | 20 +++++++++++++++++---
02-skill-factory/README.md                   |  2 +-
02-skill-factory/discovery/SKILL.md          |  2 +-
02-skill-factory/shared-references/README.md |  2 +-
README.md                                    |  4 ++--
```

## Verification run

| Check | Command | Result | Notes |
|---|---|---|---|
| pytest | `python -m pytest tests/ -q` | 537 passed / 1 skipped | 改動前後都 pass、跑了兩次 |
| ruff critical | `ruff check --select E9,F63,F7,F82 scripts tests` | All checks passed | |
| rules-lint CI | `python scripts/lint/rules-lint.py --ci` | 0 errors / 0 warnings | 改動前為 0 errors / 1 warning |
| brand-ref lint | `python scripts/lint/brand_ref_lint.py` | 0 errors / 0 warnings | 改動前為 0 errors / 1 warning |
| validate-all | `python scripts/ops/video-ops.py validate-all` | 0 errors / 0 warnings | Schema drift 5 NON-BREAKING + 4 INFO（baseline、不阻塞） |
| hook syntax | `bash -n` × 4 hook + `.githooks/pre-commit` | OK | |
| compile scripts | `python -m compileall scripts -q` | clean | |
| YAML parse | `python -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))"` | OK | 新版 pre-commit-config 結構合法 |

## Issues fixed

- H1：`.pre-commit-config.yaml` 失效 hook
- M1：`.githooks/pre-commit` 錯誤訊息指向已退役 KaiOS 檔
- M2：discovery SKILL.md brand-refs 缺 `[3]`（lint warning → 0）
- M3 部分：02-skill-factory README / shared-references README 的禁令編號 #12 → #8
- L1：README hard-coded 測試數字

## Existing issues not fixed

- M3 剩餘（受保護）：`.claude/rules/workflow.md` 內禁令 #11/#12/#13 引用 — 需 Kai 確認才動
- M3 剩餘（非保護但連動 workflow.md）：`02-skill-factory/shared-references/skill-design-principles.md` 內禁令 #11/#12 引用 — 為了避免和 workflow.md 之間造成新的編號差、留到 Kai 一次到底
- L2：`.claude/commands/scan.md` 內失效檔引用 — 受保護
- L3：`transcripts/` 目錄未建 — 不影響功能、首次使用自動建
- L4：sync-to-sheets.yml 的 `00-control-center/**` paths trigger 死設定
- L5：`performance-patterns-schema.md` v1.0 → v1.1 schema drift（intentional、baseline）

## Remaining risks

1. **禁令編號 drift（最重要）**：未來 Claude Code 跨 session 讀 workflow.md / skill-design-principles.md 時、會去查 CLAUDE.md 找不到 #11/#12/#13。建議下次 Kai 在線時批次改：
   - `.claude/rules/workflow.md`：#11 → 刪除（quickshot 未保留 KaiOS owner 分流禁令）/ #12 → #8 / #13 → #9
   - `02-skill-factory/shared-references/skill-design-principles.md`：同上
2. **`/scan` 失效**：受保護的 `.claude/commands/scan.md` 仍指向不存在的 `docs/contracts/agent-collaboration.md`。Kai 跑 `/scan` 時要意識到 Claude 會找不到該檔。建議改成指向「本檔下列 5 步檢查」內聯版、或刪除該引用。
3. **`pre-commit install` 行為變更**：原本壞、現在會在 commit 時跑 lint（< 5s）。對開發體驗有微小延遲、可接受。沒裝過 `pre-commit` 的人完全無影響。

## Branch cleanup candidates

### Possibly safe to delete after human review

（無、未檢查遠端 / 未取 `git branch -r`、保守不列）

### Do not delete yet

- 當前 branch `claude/repo-optimization-lWYux` — 本輪未 commit、刪除即流失
- 其他分支 — 未檢視

## Recommended next actions

1. **Kai 檢視本檔 + 6 個 staged 修改、決定是否 commit**（Claude 受規則限制未自行 commit）
2. **批次清理禁令編號 drift**（M3 剩餘）— 建議由 Kai 在本對話一次說「修禁令編號 drift」、Claude 一次到底改 `.claude/rules/workflow.md` + `02-skill-factory/shared-references/skill-design-principles.md`，避免後續 AI 誤判
3. **檢視 `.claude/commands/scan.md` 是否需要更新**（L2）— 受保護路徑、需 Kai 顯式授權
4. **可選**：建 `01-data-brain/transcripts/.gitkeep` 對齊 README 結構圖（純文件對齊、無功能影響）

## Safe to commit?

- **Yes**（前提：Kai 看過 diff 確認）
- 原因：
  - 所有改動均通過完整驗證鏈（pytest 537 / lint 0 / validate-all 0）
  - `.pre-commit-config.yaml` 行為改變範圍小且明確（從壞 → 跑既有 lint）
  - 其餘 5 檔皆為文字 / metadata 校正、無功能影響
- Conditions before commit:
  - 確認 `.pre-commit-config.yaml` 新行為（commit 時跑兩個 lint）符合期待
  - 若 Kai 想一次到底解 M3，建議 commit 前先把 workflow.md 和 skill-design-principles.md 也批次改完、一個 commit 進去
