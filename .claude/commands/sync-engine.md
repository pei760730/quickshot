# /sync-engine — 從主引擎 repo 同步更新（v2）

> 別名：`/sync-engine`、`/sync`、`同步`
> 預設 auto 模式（無人介入、一訊息做完）
> 子命令：`/sync dry`（展示不改）、`/sync pause`（逐步確認）、`/sync cleanup`（同步 + 污染掃描批次）

讀取 `pei760730/KaiOS-ContentSystem` 的最新引擎檔案、與本客戶 repo 比對同步。

**v4.58 升級**：auto 模式 + CI 紅分類 + 污染掃描 + auto-merge 門檻。
**v4.24 骨架**：opt-out blacklist（`_meta.sync_blacklist`）。
**v4.38 骨架**：operator 定義 `data/.operators.json`（blacklist 保護）。

---

## Auto-merge 授權範圍（關鍵）

- ✅ **客戶 repo 端**：sync PR → 客戶 main 可 auto admin merge（見 Q2 門檻）
- ❌ **主引擎 repo**：永遠 Kai 手動、不 auto merge（系統規則）

---

## 前置設定（一次性）

```bash
git remote -v | grep engine || git remote add engine https://github.com/pei760730/KaiOS-ContentSystem.git
```

---

## Auto 模式流程（預設 `/sync` `/同步`）

### Step 0. Sanity check（v4.38、必跑）

```bash
python3 -c "
from scripts.ops.lib import config
current = config.DEFAULT_OPERATOR
if current not in config.OPERATORS:
    import sys
    print(f'❌ operator={current} 不在 OPERATORS={list(config.OPERATORS.keys())}')
    sys.exit(1)
print(f'✅ operator={current} 註冊正確')
"
```

Fail → 停、回報「請先跑 bootstrap-client.sh」。

### Step 1. fetch engine main

```bash
git fetch engine main -q
```

### Step 2. 讀版本、對比

- 本地：`jq '._meta.engine_version' engine-manifest.json`
- 引擎：`git show engine/main:engine-manifest.json | jq '._meta.engine_version'`

**若相等** → 回一行「✅ 已最新 v4.X」、結束。

### Step 3. Diff + blacklist filter

```bash
git diff <local_engine_version>..engine/main --name-only
```

對每 path 跑 `is_blacklisted(path, engine_sync_blacklist)`（見下方邏輯）、過濾掉 blacklist。

### Step 4. 輕量污染掃描（見 Q5）

Auto 模式自動啟動條件：`_meta.client.name != "kai"`（客戶 repo）。掃到污染 → 停、列給 Kai 批次 approve。無污染 → silent pass。

### Step 5. CHANGELOG 摘要（本地拼、不展示）

`git show engine/main:07-changelog/CHANGELOG.md` 取 🔧 條目、拼成 PR body 用的短摘要。

### Step 5.5. Schema-migration 偵測（v4.24+、L-0022 第四層防護）

從 Step 5 取得的 CHANGELOG 文本跑 `has_schema_migration_marker`：

```python
from scripts.engine.schema_migration_detector import (
    has_schema_migration_marker,
    detect_schema_migration_marker,
)

if has_schema_migration_marker(changelog_text):
    hits = detect_schema_migration_marker(changelog_text)
    print("🚨 偵測到資料層 schema migration、強制停下、不 auto-merge：")
    for line in hits:
        print(f"  • {line}")
    print("\n處理方式：")
    print("  1. 看引擎側 CHANGELOG 對應 v{X} 條目的 migration 步驟")
    print("  2. 客戶端手動執行 migration（資料層 schema 對齊）")
    print("  3. 完成後再跑 /sync pause 逐步確認")
    sys.exit(0)  # 不是錯、是設計上要求人工介入
```

無 🚨 marker → 直接進 Step 6。

### Step 6. 覆蓋檔案（含客戶禁區 sha 校驗、v4.24+ L-0022 第二層防護）

```python
from scripts.engine.client_territory_guard import (
    snapshot_client_territory,
    verify_client_territory_unchanged,
    restore_client_territory,
)

# 6.1 sync 前 snapshot
snapshot = snapshot_client_territory(repo_root)
```

```bash
# 6.2 覆蓋（同舊版）
for path in <同步清單>; do
  git checkout engine/main -- "$path"
done
```

```python
# 6.3 sync 後驗證（L-0022 第二層）
ok, changed = verify_client_territory_unchanged(snapshot, repo_root)
if not ok:
    print(f"🚨 客戶禁區檔被覆蓋（{len(changed)} 檔）：")
    for p in changed:
        print(f"  • {p}")
    restored = restore_client_territory(snapshot, repo_root)
    print(f"✅ 已自動 restore {len(restored)} 檔回 sync 前狀態")
    print("→ abort sync、回報 Kai 檢查 _meta.sync_blacklist 是否漏寫")
    sys.exit(1)
```

更新本地 `engine-manifest.json`：
- `_meta.engine_version` 對齊引擎
- `_meta.sync_blacklist` 對齊引擎（blacklist 本身也是引擎規則）
- `_meta.files` 對齊引擎
- **保留客戶本地 `_meta.client` 欄位**

### Step 7. 本地驗證

```bash
ruff check --select E9,F63,F7,F82 scripts tests
python -m pytest tests/ -q
python scripts/lint/rules-lint.py --ci
python scripts/ops/video-ops.py validate-all
python scripts/engine/engine_version_check.py --base engine/main --head HEAD
```

任一 fail → 進 Step 8（CI 紅分類、見 Q3）。

### Step 8. CI 紅分類（Q3）

見下方分類表、按表行動。

### Step 9. commit + push 到 sync branch

Branch name: `sync/engine-v<new_version>`（若不存在建）。

```bash
git checkout -b sync/engine-v4.X 2>/dev/null || git checkout sync/engine-v4.X
git add -A
git commit -m "chore: sync engine v4.X → v4.Y"
git push -u origin sync/engine-v4.X
```

### Step 10. 開 PR（若不存在）

PR body 含：
- diff 摘要（N 檔、哪些）
- CHANGELOG 節選（🔧 條目）
- 本地驗證結果表（ruff / pytest / rules-lint / validate-all / engine-version-check）

### Step 11. Monitor PR CI（polling、timeout 600s）

```bash
timeout=600
interval=15
elapsed=0
while [ $elapsed -lt $timeout ]; do
  status=$(gh pr checks <PR_NUM> --json conclusion -q '[.[].conclusion] | all(. == "success")')
  if [ "$status" = "true" ]; then break; fi
  sleep $interval
  elapsed=$((elapsed + interval))
done
```

### Step 12. 混合 auto-merge 判斷（Q2）

```python
diff_count = <Step 3 過濾後的檔數>
pollution_count = <Step 4 掃到的檔數>
threshold = config.get("sync_engine.auto_merge_diff_threshold", 20)

if ci_all_green and diff_count < threshold and pollution_count == 0:
    gh pr merge <PR_NUM> --admin --squash --delete-branch
    git checkout main && git pull && git fetch --prune
    print(f"✅ v4.X → v4.Y done、<N>/<F>/<S> pytest、合 PR #<NUM>")
else:
    print(f"⚠️ diff {diff_count} 檔 / 污染 {pollution_count} 項、等 Kai 看 PR #<NUM>")
```

Threshold 可透過客戶 repo 的 `.claude/settings.local.json` 調整：

```json
{
  "sync_engine": {
    "auto_merge_diff_threshold": 30
  }
}
```

---

## Q3. CI 紅自動分類表

| 徵兆 | 判定 | 動作 |
|------|------|------|
| `engine_version_check` fail、訊息含 `manifest 未記錄版本` | 引擎層 | 停、push 當前狀態到 PR body、寫「請 engine 端補 manifest entry」提示詞 |
| `pytest` fail、traceback 停 `scripts/ops/lib/` or `scripts/engine/` | 引擎層 | 停、完整 traceback 寫 PR body、產 surgical 提示詞給 Kai 貼主 repo |
| `rules-lint` 只有 warn（0 errors） | non-block | 忽略、繼續 Step 9 |
| `validate-all` Schema drift breaking > 0 | 引擎 contract snapshot 未 bump | 停、列 breaking 項給 Kai |
| diff 只涉 `tests/*.py` + fail 明確指向 v4.X CHANGELOG 分類原則的漏改 | 客戶層可 surgical | Surgical fix（限制見下）、commit 進 PR |
| 其他 | 未知 | 停、完整 output 給 Kai、不猜 |

### Surgical fix 限制（嚴格）

- **只動** `tests/*.py` 或 `01-data-brain/*.md` 內的 non-structural 文案
- **絕不動** `scripts/`、`.claude/`、`docs/contracts/`、`engine-manifest.json`、`CHANGELOG.md`
- **1 commit ≤ 5 行**變動
- commit msg **必含**「請 engine 端 v4.X+1 照修」標記

---

## Q5. 輕量污染掃描

### Patterns（v4.24+、L-0022 第三層：通用化）

引擎不寫死客戶字樣。改為從客戶 `CLAUDE.local.md` 的 marker block 載入：

```python
from scripts.engine.client_pollution_scanner import load_forbidden_terms, scan_pollution

POLLUTION_PATTERNS = load_forbidden_terms(repo_root / "CLAUDE.local.md")
# 客戶在 CLAUDE.local.md 的 <!-- POLLUTION_PATTERNS_START/END --> block 自填、不在 → 回 []
# Kai 主 repo CLAUDE.local.md 已含紅茶巴士字樣、其他客戶 fork 引擎時自填自家品牌
```

NOTE: 未替換 `{{...}}` placeholder 不列進 patterns、整檔 skip（v4.59 exclude 邏輯保留、由 scan_pollution 內部處理）。

### Scan paths

```python
SCAN_PATHS = [
    "01-data-brain/**/*.md",
    "00-control-center/**/*.md",
    "CLAUDE.local.md",
]
```

### Exclude

```python
EXCLUDE = [
    "01-data-brain/index.md",  # engine schema 文件
    "CLAUDE.local.md",          # v4.59: 客戶在共識段 narrative 引用 Q5 patterns 會自身命中、整檔 exclude
]
```

### 觸發邏輯（v4.24+、用 client_pollution_scanner 模組）

```python
hits = scan_pollution(repo_root, POLLUTION_PATTERNS)

if hits and client_name != "kai":
    print_hits_table(hits)
    ask_batch_approve()
else:
    silent_pass()
```

`scan_pollution` 內部已含 placeholder skip + EXCLUDE filter（見 `scripts/engine/client_pollution_scanner.py`）。

---

## 子命令變體

### `/sync dry`

展示計畫不改檔（= v1 行為）。適合重大 sync（如跨大版本）預覽。

### `/sync pause`

每步等 Kai 確認。適合偵錯或高風險同步。降級 v1 互動式行為。

### `/sync cleanup`

同步 + 強制跑 Q5 污染掃描（不管 `_meta.client.name`）。用於新客戶 onboarding 初期污染清理。

---

## Blacklist 判斷邏輯

```python
from fnmatch import fnmatchcase

def is_blacklisted(path, blacklist):
    for rule in blacklist:
        if rule.startswith("!") and fnmatchcase(path, rule[1:]):
            return False
    for rule in blacklist:
        if not rule.startswith("!") and fnmatchcase(path, rule):
            return True
    return False
```

或直接 import 引擎的 `scripts/engine/engine_version_utils.py:is_blacklisted`。

---

## 衝突處理（客戶改過引擎檔）

本地版本 ≠ 上次 sync 的引擎版本：

- 預設：標註「客戶客製化」、問 Kai 保留本地或用引擎新版
- 「保留本地」→ engine-manifest 註記 `"custom": true` 避免下次覆蓋
- 「用引擎新版」→ 照引擎覆寫

---

## 觸發時機

- Session 開頭 hook 提示「engine 落後 v{local} → v{remote}」時（見 `.claude/hooks/session-start.sh` 第 7 類）
- 引擎 CHANGELOG 有 🚨 記號時立刻跑
- 跨大版本 sync 先 `/sync dry` 預覽
