# Dashboard

> 龍OS 即時數據儀表板 — Claude design × Claude Code 協作產出

## 架構

```
dashboard/
├── src/                    ← Claude design 的地盤
│   ├── index.html          UI 骨架 + CSS（含 data-bind 錨點）
│   ├── ui-contract.md      UI 必須提供的錨點清單（與 Claude Code 的合約）
│   ├── data-schema.json    資料欄位 SSoT（兩邊都讀）
│   └── design-snapshots/   Claude design export 歷史快照
├── build.py                ← Claude Code 的地盤：讀 data/longbro/*.json → inject → dist/
├── vercel.json             Vercel deploy 設定
└── dist/                   build 產出（.gitignore）
```

## 協作憲章

完整版：`docs/contracts/design-collaboration.md`

三個關鍵檔案是 Claude design 和 Claude Code 的共享合約：

- `data-schema.json` — 資料欄位定義。雙方都讀、任一方改都要升 version
- `ui-contract.md` — UI 要提供哪些 `data-bind` 錨點 + 綁定規則
- `index.html` — Claude design 維護 UI，`build.py` 不動它，只 inject 資料

## 本地跑

```bash
# build + 輸出 dist/index.html + dist/data.json
python3 dashboard/build.py

# 只產 schema 不寫檔（除錯用）
python3 dashboard/build.py --dry-run
```

本地開：瀏覽器打開 `dashboard/dist/index.html`（或跑 `python3 -m http.server` 再訪問）。

## 部署（Vercel）

1. vercel.com 登入 → Import Git Repository → 選 `pei760730/kaios-client-longbroos`
2. Framework Preset: **Other**
3. Root Directory: **dashboard**
4. Build Command: 留空（vercel.json 會自動讀到 `python3 build.py`）
5. Output Directory: 留空（vercel.json 指定 `dist`）
6. Deploy
7. Settings → **Deployment Protection** → Password Protection → 設密碼 → Save

每次 push to main 自動 build + deploy。延遲約 30-60 秒。

## 資料流

```
data/longbro/pipeline.json           ┐
data/longbro/performance-patterns.json  ┼─── build.py 讀
data/longbro/brand-monitor.json       ┘         │
                                             ▼
                                          aggregate()
                                             │
                                             ▼ (符合 data-schema.json)
                                          inject() → dist/index.html
                                                          │
                                                          ▼
                                                     Vercel deploy
                                                          │
                                                          ▼
                                                   https://...vercel.app
```

## 增加新指標的流程

例：加一個「本週新增靈感數」KPI

1. **Claude design**：`src/index.html` 加 `<div data-bind="kpis.ideas_this_week">—</div>`
2. **Claude Code**：
   - `src/data-schema.json` 的 `fields.kpis` 加 `ideas_this_week`
   - `build.py` 的 `aggregate()` 加計算邏輯
   - `src/ui-contract.md` 錨點清單加一行
3. 跑 `python3 dashboard/build.py` 驗證
4. commit + push

缺任一步 → build fail 或 UI 顯示 `—`（build.py 偵測到 schema 有但 HTML 沒綁，會在 dry-run 提示；反之亦然）。

## 範圍（v1.0）

- ✅ Operator：`longbro`（單 operator、本 repo 自用 dashboard）
- ✅ 資料：pipeline + performance-patterns + brand-monitor
- ❌ 多 operator 切換（本 dashboard 屬 operator 自用、跨 operator 切換待引擎升版支援）
- ❌ 活動流 / Skill 使用記錄（之後擴，目前 live feed 屬 runtime 性質）
- ❌ 多分支預覽（只看 main）

## 升級路徑

| 項目 | 時機 |
|------|------|
| 加「本週新增 X」週期指標 | 每週回填流程穩定後 |
| 自訂時間區間（last 7/30/90 days）| 當歷史資料夠 |
| Webhooks / 即時活動流 | v2（runtime fetch 或 Server-Sent Events）|

加東西時走「協作憲章」流程（`docs/contracts/design-collaboration.md` § 4）。
