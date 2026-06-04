# AI System Upgrade Report

> Sleep Mode v3.0 — 第四輪（含「全修」收尾）。本輪經 Kai 授權 commit / push / 開 PR。
> 主題：跨平台（Windows）破壞修復 + 文件 drift 對齊 + 跨平台回歸守衛。
> 前三輪（PR #10 / #15 / #16 / #17）已 merge；其成果（README pipeline 路徑、requirements engine-manifest 指示）已在 main。

## Base

- Branch: `claude/cross-platform-windows-fix`（從 `main` HEAD `ac6131d` 開出）
- Repo root: `C:/Users/user/projects/quickshot`
- Time: 2026-06-04
- Platform: Windows 10（本機 Python 3.14.2；repo CI 用 3.11）
- Working tree before changes: clean（on main）
- Working tree after changes: 22 files changed（已 commit、開 PR）

## Project snapshot

- Project type: AI 驅動短影音生產 template（KaiOS 短期客戶 ≤30 天精簡版）；目前為乾淨 template 狀態（無掛客戶）
- Primary language: Python（CI 3.11 / 本機 3.14.2）
- Package manager: pip + `requirements-dev.txt`（`pytest>=8.0` / `ruff>=0.5`）
- Main entrypoints: `scripts/ops/video-ops.py`（狀態寫入唯一入口）/ `scripts/lint/*.py` / `scripts/utils/{sync-to-sheets,sheets-direct,transcribe}.py` / Claude Code `/init` `/check` `/scan` `/harden`
- Automation: `.github/workflows/{rules-lint,sync-to-sheets,wipe-client}.yml`；`.githooks/pre-commit` + `.pre-commit-config.yaml`；`.claude/hooks/*.sh`
- Validation: `python -m pytest tests/` / `python -m ruff check --select E9,F63,F7,F82 scripts tests` / `rules-lint.py --ci` / `brand_ref_lint.py` / `video-ops.py validate-all` / `compileall scripts tests`
- AI instruction files: `CLAUDE.md` / `CLAUDE.local.md` / `.claude/rules/*` / `.claude/skills/*` / `.claude/commands/*`

## What I inspected

- Git state、218 tracked files、107 Python files、無未追蹤檔
- 全套驗證基線（改動前，Windows）：**pytest 23 collection errors（全壞）**
- 全 repo POSIX-only imports（`fcntl` 等）+ 全 `scripts/` `subprocess.run(text=True)` 無 `encoding=` 之處
- 全 `scripts/` 入口點（有 `__main__` 守衛）是否印 cp950 編不出的 emoji 卻未強制 UTF-8
- `brand_ref_lint.py` 路徑分隔符可攜性；`.gitignore` 是否涵蓋 `*.lock`
- 文件 drift：CLAUDE.md 資料地圖路徑、requirements-dev.txt 標題

## System-level issues found

### High risk

**H1.（已修）`storage.py` 無條件 `import fcntl` → CLI + 測試套件在 Windows 全壞**
- `storage` 被 `video-ops.py`（狀態寫入唯一入口）+ 17 lib + 23 測試模組 import → 全炸。
- 前三輪沒抓到：CI 與前幾輪都跑 Linux，fcntl 永遠存在；bug 只在 Kai 的 Windows 機器爆。典型「Linux-only CI 遮蔽的平台債」。
- 證據：改動前 Windows pytest = 23 errors，均為 `ModuleNotFoundError: No module named 'fcntl'`。

**H2.（已修）CLI / lint 輸出在 Windows 被 pipe / 重導 / 捕捉時 `UnicodeEncodeError` 崩潰**
- 入口全程印中文 + emoji（✓ ⚠️ 📊 ❌ ✅）。Windows 非主控台輸出用 cp950，**cp950 編不出 emoji** → `print` 中途崩潰：半輸出 + 非零 exit（看似失敗、實則操作可能半執行）。
- 也是 Kai 過往要手動設 `PYTHONIOENCODING=utf-8` 的根源。

### Medium risk

**M1.（已修）多處 `subprocess.run(text=True)` 缺 `encoding=` → 讀子程序 UTF-8 輸出時 cp950 解碼崩潰**
- `rules-lint.py`（3×git）、`schema_drift.py`（git show 中文 contract）、`hardening.py`（讀 pytest/lint 輸出）、`cloud_relay.py`（3×git）、2 測試。

**M2.（已修）`brand_ref_lint.py` manifest 路徑用 OS 分隔符 → Windows 反斜線 key**
- `rel` 是 manifest key 且 `--json` 輸出供工具消費 → 反斜線不可攜。改 `.as_posix()`。

### Low risk

**L1.（已修，validation gap）無守衛防止跨平台回歸** — CI Linux-only 是 H1/H2 潛伏主因。新增 `tests/test_cross_platform.py`：
- POSIX-only import AST 掃描（防 H1 回歸）
- fcntl-缺席模擬 + 實際 save（驗 storage 退化路徑）
- **emoji 入口點 cp950-codec 掃描**（防 H2 回歸）— 此守衛在實作中**主動揪出 3 個我原本漏掉的入口**（`ai_patterns_lint.py` / `skill-io-lint.py` / `migrate_todos.py`），證明用 codec 掃描勝過寫死清單。

**L2.（已修）文件 drift**
- `CLAUDE.md` L62 資料地圖 `data/{operator}/pipeline.json`（legacy 單檔）→ `data/{operator}/pipeline/`（sharded 現實）。經 Kai 授權動 deny-protected 檔。
- `requirements-dev.txt` L1 標題 `— KaiOS-ContentSystem` → `quickshot（短期客戶 template）`。

## Changes made

| 類別 | 檔 | 變更 |
|------|----|------|
| H1 核心 | `scripts/ops/lib/storage.py` | `import fcntl` → 跨平台鎖 shim（POSIX=fcntl / Windows=msvcrt / 皆無=no-op）；POSIX 行為不變、原子 replace 仍保證不寫壞檔 |
| H2 入口強制 UTF-8（12 個）| `video-ops.py`、`rules-lint.py`、`brand_ref_lint.py`、`ai_patterns_lint.py`、`skill-io-lint.py`、`sync-to-sheets.py`、`sheets-direct.py`、`transcribe.py`、`wipe_client.py`、`migrate_pipeline_to_sharded.py`、`migrate_reclassify_performance.py`、`migrate_todos.py` | `main()` 起始 `sys.stdout/stderr.reconfigure(encoding="utf-8")`（guarded）；3 檔順帶補 `import sys` |
| M1 subprocess encoding | `rules-lint.py`(3) / `schema_drift.py` / `hardening.py` / `cloud_relay.py`(3) / `test_quick_shot.py` / `test_video_ops_quality_targets.py` | 補 `encoding="utf-8"` |
| M2 路徑可攜 | `brand_ref_lint.py` | manifest + 顯示路徑 `.as_posix()` |
| L1 守衛 | `tests/test_cross_platform.py`（新增、5 測試）| POSIX import 掃描 + fcntl 缺席模擬 + emoji 入口 codec 掃描 |
| L2 文件 | `CLAUDE.md` / `requirements-dev.txt` | 路徑 / 標題對齊現實 |

## Files changed

22 files changed, 400 insertions(+), 89 deletions(-)（含本報告）。詳見 PR diffstat。

## Verification run

| Check | Command | Result | Notes |
|---|---|---|---|
| pytest（改動前 Windows）| `pytest tests/ -q` | **23 collection errors** | 全因 `ModuleNotFoundError: fcntl` |
| pytest（改動後）| `pytest tests/ -q` | **547 passed / 1 skipped** | 前基線 542；+5 守衛 |
| ruff critical | `ruff check --select E9,F63,F7,F82 scripts tests` | All checks passed | |
| rules-lint CI | `rules-lint.py --ci` | 0 issues | 含 CLAUDE.md 版本/日期一致性檢查、本輪 CLAUDE.md 改動通過 |
| brand-ref lint | `brand_ref_lint.py` | 0 issues | |
| validate-all | `video-ops.py validate-all` | 0 errors / 0 warnings / 0 drift | |
| compileall | `compileall -q scripts tests` | exit 0 | |
| piped no-PYTHONIOENCODING | video-ops / rules-lint / brand-ref / validate-all / sheets-direct / ai_patterns_lint / migrate（清 env、pipe）| 全 rc 正常、無 `_readerthread` / Unicode 崩潰 | 直接證明 H2/M1 已解 |
| 鎖 backend | 反射 `storage._acquire_lock` | Windows=`msvcrt`（非 no-op）| 547 save-heavy 測試通過佐證鎖運作 |

## Issues fixed

- H1 storage 跨平台鎖、H2 12 入口強制 UTF-8、M1 8 處 subprocess encoding、M2 路徑 as_posix、L1 守衛測試、L2 文件 drift —— 全數修復並驗證。
- Windows 上整套系統從「CLI + 測試全壞」→ 「全綠、piped 不崩」。

## Existing issues not fixed（保守保留、刪除屬破壞性、留給 Kai 決定）

- `tests/path_bootstrap.py` 的 `ENGINE_LIB_ROOT` + `bootstrap_engine_test_sys_path()`（KaiOS lineage、無測試使用）
- `tests/fixtures/engine-versioning-rules.json`（孤立 fixture、無引用）
- `.githooks/pre-commit` 白名單含 KaiOS-only 路徑（`engine-manifest.json` / `00-control-center/` / `dashboard/` / `HOME.md` / `AGENTS.md`）

## Remaining risks

1. **9 個入口的 UTF-8 reconfigure 為 inline 重複塊**：目前一致、低風險；未來可抽共用 `_force_utf8_stdio()` helper DRY（跨 ops/utils/lint 三目錄，需處理 import path，屬獨立 cleanup）。
2. **KaiOS lineage 死碼三處**：不影響運作；確定永不借屍還魂後可清。
3. **Python 版本落差**（本機 3.14 / CI 3.11）：本輪改動皆 3.7+ 通用 API，無版本相依風險；長期版本不一致仍是潛在 drift 源。

## Branch cleanup candidates

### Possibly safe to delete after human review
（無把握者不列）

### Do not delete yet
- `origin/claude/code-review-high-Ixmsj`（remote）：PR #16 已 merge，但其上仍有未進 main 的 commit `b55cb0a`（補 wipe_client 20 test + 清死碼）。刪前需 Kai 確認是否 cherry-pick。
- `claude/cross-platform-windows-fix`：本輪 PR 來源、merge 後刪。

## Recommended next actions

1. Review 本 PR → merge → 刪 `claude/cross-platform-windows-fix`（依 AV convention）
2. 決定 `origin/claude/code-review-high-Ixmsj` 的 `b55cb0a`：cherry-pick 補進 main 還是丟、然後刪該 remote branch
3. 可選 cleanup：抽 `_force_utf8_stdio()` helper DRY 掉 9 個 inline 塊；清 KaiOS lineage 死碼

## Safe to commit?

- **Yes — 本輪已 commit + push + 開 PR**（Kai 授權）
- 原因：目標單一（修跨平台破壞 + 對齊文件），無新功能 / 無架構重構 / 無 API 變更；POSIX 行為不變；完整驗證鏈全綠（547/1skip、lint 0、drift 0、compile 0、piped 不崩）；新增守衛讓回歸在 Linux CI 也擋得住。
