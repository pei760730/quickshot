# Claude design × Claude Code 協作憲章

> version: 1.0 | last_updated: 2026-04-19
> 雙方契約：Claude design（UI 產出）+ Claude Code（資料 / build / deploy）
> 觸發方式：Kai 說「dashboard 加 X」「改 dashboard 樣式」「加 Y 指標」→ 依本契約分工

---

## 0. 角色邊界

### Claude design 的地盤

**職責**：UI、樣式、layout、互動設計

**檔案**：
- `dashboard/src/index.html`（HTML 結構 + inline CSS + 少量 UI JS）
- `dashboard/src/design-snapshots/*.html`（export 歷史快照）

**可以做**：
- 改 UI layout、新增 panel、調樣式
- 加 `data-bind`、`data-bind-list`、`data-bind-item`、`data-bind-field` 錨點
- 在 `ui-contract.md` 登記新需要的錨點（讀 `data-schema.json` 知道欄位是否存在）

**不可以做**：
- 改 `build.py`、`vercel.json`、`data/**`、`engine-manifest.json`
- 改 `data-schema.json` 的 schema 定義（可以讀、可以**提議**改，實作由 Claude Code）
- fetch 外部 URL（UI 不 fetch 資料，資料 build 時 inject）

### Claude Code 的地盤

**職責**：資料聚合、build pipeline、deploy、契約維護

**檔案**：
- `dashboard/build.py`（讀 data → 產資料 → inject HTML）
- `dashboard/vercel.json`
- `dashboard/src/data-schema.json`
- `dashboard/src/ui-contract.md`
- `dashboard/README.md`
- `docs/contracts/design-collaboration.md`（本檔）

**可以做**：
- 改 `build.py` 的 `aggregate()` 計算邏輯
- 新增 schema 欄位（含 `_display` 格式化版本）
- 更新 ui-contract 錨點清單
- 調整 Vercel deploy 設定

**不可以做**：
- 改 `index.html` 的樣式 / layout（只能跑 inject）
- 動 SKILL / CLAUDE.md / 任何 02-skill-factory/**

### 共享（雙方都讀）

- `dashboard/src/data-schema.json` — 資料 SSoT
- `dashboard/src/ui-contract.md` — UI 錨點 SSoT

---

## 1. 雙方接口：四個檔案的版本合約

| 檔案 | 變動時雙方誰要配合 |
|------|-------------------|
| `data-schema.json` | Claude design 讀知道能綁什麼、Claude Code 確保 build 產出符合 |
| `ui-contract.md` | Claude design 找錨點清單、Claude Code 確保對應 schema 欄位存在 |
| `index.html` | 僅 Claude design 改，Claude Code 透過 inject 使用不動結構 |
| `build.py` | 僅 Claude Code 改，Claude design 不碰 |

---

## 2. 新增指標流程（五步驟）

以「加一個『本週新增靈感數』KPI」為例：

### Step 1 — Kai 告訴 Claude design：「Dashboard 加一個本週新增靈感數」

### Step 2 — Claude design 改 `src/index.html`

```html
<div class="kpi-card">
  <div class="kpi-label">本週新增靈感</div>
  <div class="kpi-value" data-bind="kpis.ideas_this_week">—</div>
</div>
```

commit 到分支、push，但不 merge。

### Step 3 — Kai 通知 Claude Code：「Claude design 加了 kpis.ideas_this_week 錨點」

### Step 4 — Claude Code 做三件事：

1. `data-schema.json` 的 `fields.kpis` 加：
   ```json
   "ideas_this_week": {"type": "int", "desc": "本週內 created_date 在 last 7 days 的 idea 數"}
   ```
2. `build.py` 的 `aggregate()` 加計算邏輯
3. `ui-contract.md` 錨點清單加一行 `data-bind="kpis.ideas_this_week"`

合進 Claude design 的同一分支（或接續 PR）。

### Step 5 — 本地驗證 → commit → push → Vercel 自動 deploy

```bash
python3 dashboard/build.py
# 預期輸出含新的 ideas_this_week 值
# 開 dist/index.html 確認 KPI 卡顯示正確
```

---

## 3. 改 UI 樣式流程（單方完成）

純樣式改動（顏色、間距、字體）：

- Claude design 改 `src/index.html`
- 不影響 schema、不影響 build.py
- commit + push → 下次 deploy 生效

不需要通知 Claude Code。

---

## 4. 改資料計算流程（單方完成）

純計算邏輯改動（例如 KPI 公式調整）：

- Claude Code 改 `build.py` 的 `aggregate()` 函式
- 不改 schema（還是一樣的欄位名）
- 不改 UI
- commit + push → 下次 deploy 生效

不需要通知 Claude design。

---

## 5. 重構 schema 流程（雙方都要配合）

高槓桿但高風險：例如「retention_3s_pct → 改成 retention_3s（不加 _pct 後綴）」

### 流程

1. Kai 發起討論（要改 schema 的理由）
2. Claude Code 先做 schema + build.py 改動、**保留舊欄位名當 alias**（向後相容）
3. Claude design 改 `index.html` 用新欄位名
4. Claude design commit 後通知 Claude Code
5. Claude Code 移除 alias、清理

中間任一步 merge 都不會破 UI（因為 alias 保留）。

---

## 6. 衝突解決

| 衝突 | 誰贏 |
|------|------|
| Claude design 要新欄位、schema 還沒加 | build 會在 dry-run 警示；等 Claude Code 補齊 |
| Claude Code 改了欄位名、UI 沒跟上 | dist UI 顯示 `—`；Kai 發現後讓 Claude design 補 |
| 雙方同時改 data-schema.json | 以 Claude Code 版本為準（schema SSoT 屬 Code）|
| 雙方同時改 index.html | 以 Claude design 版本為準（UI SSoT 屬 design）|

---

## 7. 觸發關鍵字

Kai 說以下話時，按此契約分工：

| Kai 說 | 哪方動手 |
|--------|---------|
| 「dashboard 加 XYZ 指標」 | 5 步驟流程（design 先、code 補）|
| 「dashboard 改顏色 / 改 layout」 | 只 Claude design |
| 「dashboard 算錯了」 | 只 Claude Code 改 `aggregate()` |
| 「dashboard 新增一個 panel」 | 5 步驟流程 |
| 「dashboard build 壞了」 | Claude Code 先 debug、必要時請 Claude design 配合 |

---

## 8. 隔離原則

**單一 deploy、雙方各自 commit**：

- Vercel watch main → push to main 觸發 deploy
- Claude design 和 Claude Code 各自改自己責任區的檔、各自 commit
- **同一分支併用**：避免互卡，兩方改動可以在同一 PR
- **禁止**：Claude design 改 `build.py`、Claude Code 改 `index.html` 樣式

---

## 9. 與其他協作憲章的關係

| 憲章 | 角色 |
|------|------|
| `docs/contracts/agent-collaboration.md` | Claude Code × Codex（程式層協作） |
| **本檔 design-collaboration.md** | **Claude design × Claude Code（UI/資料協作）** |
| `docs/contracts/sync-protocol.md` | 引擎 repo × 客戶 repo |
| `docs/contracts/headless-tasks.md` | 週期任務規格（Claude headless） |

各憲章管各自疆域，不重疊。

---

## 10. 本契約的變動時機

- 新增一方（例如 Codex 開始碰 dashboard 相關）→ 升 version、加責任區
- 新的協作情境（例如 Figma import、新 data source）→ 升 version、擴 flow
- 踩雷後補坑 → 升 version、補對應 guard

保持簡潔、不擴張成其他職責。
