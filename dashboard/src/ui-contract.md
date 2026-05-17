# Dashboard UI 合約

> version: 1.6 | last_updated: 2026-04-20
> 讀者：Claude design（改 index.html 時必須遵守）+ Claude Code（build.py 依此 inject）
> 資料 SSoT：`dashboard/src/data-schema.json`
> **v1.1**：Tab 切換機制 + 4 個 nav tab（待拍 / 已上線 / 高表現 / 靈感箱）
> **v1.2**：卡關偵測 card 可點（跳對應 tab）+ stuck_counts / stuck_thresholds dict 綁定模式
> **v1.3**：對齊 Sheets 影片總覽 — views 萬制 + tier_display（4+1 檔細分）+ next_action（行動提示）
> **v1.4**：拆普通 / 低表現為獨立 tab + 全 sidebar/header 中文化
> **v1.5**：4 個表現分級 tab header 統一 8 欄（+ 動作 + 上線日期）+ **視覺設計原則：桌面優先**

---

## 核心機制：`data-bind` 錨點

UI 元素要顯示動態資料時，加 `data-bind="<path>"` 屬性。path 對應 `data-schema.json` 的 fields 層級，用 `.` 分隔。

範例：
```html
<div data-bind="kpis.accumulated_views">—</div>
<div data-bind="kpis.avg_retention_3s_pct">—</div>
```

內容（`—` 或任何 placeholder）在 build 時被 `build.py` 覆蓋成實際值。未 build 時直接開檔顯示 placeholder（設計時好對 layout）。

---

## 規則

### R1. 所有動態資料必須走 `data-bind`

- ❌ `<div>3.1M</div>`（寫死）
- ✅ `<div data-bind="kpis.accumulated_views_display">—</div>`

### R2. 格式化規則

資料在 schema 是 raw 值（int/float）。UI 層面要「顯示格式」時：

| 顯示需求 | 綁法 |
|---------|------|
| 原始數字 | `data-bind="kpis.accumulated_views"` → `3100000` |
| 人類友善（3.1M/697K）| `data-bind="kpis.accumulated_views_display"` → `3.1M` |
| 百分比含符號 | `data-bind="kpis.avg_retention_3s_pct_display"` → `62.5%` |

`_display` 後綴版本由 `build.py` 產出。Claude design 需要哪種就用哪個 suffix。

### R3. List / Array 綁定用 `data-bind-list`

對於清單（Top 5 高/低、卡關偵測），UI 放一個 template 元素 + `data-bind-list`：

```html
<div data-bind-list="top5_high_performers">
  <div data-bind-item class="video-row">
    <span data-bind-field="vid">VID-XXX</span>
    <span data-bind-field="title">（標題）</span>
    <span data-bind-field="views_display">0</span>
    <span data-bind-field="retention_3s_pct_display">0%</span>
  </div>
</div>
```

`build.py` 看到 `data-bind-list` 會以 `data-bind-item` 為 template 複製 N 次、把 `data-bind-field` 替換成 item 的欄位值。

### R4. 條件顯示用 `data-show-if`

某元素要依條件顯示：

```html
<div data-show-if="nav_counts.inbox > 0">有靈感</div>
<div data-show-if="nav_counts.inbox == 0">靈感箱是空的</div>
```

`build.py` 求值後決定要不要保留該元素。v1 支援簡單比較（`>`, `<`, `==`, `!=`）。

### R5. 缺資料怎麼呈現

build.py inject 時若 schema 欄位缺漏：
- 純值 → 顯示 `—`
- list → 顯示空 list（不渲染 item template）
- 顯式用 `data-bind` 但 schema 沒定義 → build.py 拋錯 fail（協助抓漏）

### R6. 樣式與 script 限制

- CSS：可以 inline、可以 `<style>`、**不可外部 URL**（要離線可開 + Vercel deploy 乾淨）
- JS：只能做 UI 行為（hover、tab 切換、動畫），**不可 fetch 外部資料**（資料已在 build 時 inject）
- 字體：可用 system font 或 Google Fonts `<link>`（CDN 不擋）

---

## v1.0 必須的錨點清單

### KPI 區

```
data-bind="kpis.accumulated_views_display"        → 3.1M
data-bind="kpis.sample_size"                      → 28
data-bind="kpis.total_uploaded"                   → 28
data-bind="kpis.avg_retention_3s_pct_display"     → 62.5%
data-bind="kpis.avg_completion_rate_pct_display"  → 49.0%
data-bind="kpis.high_performers_count"            → 9
data-bind="kpis.win_rate_pct_display"             → 32%
data-bind="kpis.thresholds.retention_pass"        → 55
data-bind="kpis.thresholds.retention_high"        → 70
data-bind="kpis.thresholds.completion_pass"       → 40
```

### Nav 計數

```
data-bind="nav_counts.inbox"
data-bind="nav_counts.selected"
data-bind="nav_counts.待拍"
data-bind="nav_counts.剪輯中"
data-bind="nav_counts.已上線"
data-bind="nav_counts.performance_high"
data-bind="nav_counts.performance_normal"
data-bind="nav_counts.performance_low"
```

### Top 5 高表現 / 低表現（左右對稱）

```html
<div data-bind-list="top5_high_performers">
  <div data-bind-item>
    <span data-bind-field="vid"></span>
    <span data-bind-field="title"></span>
    <span data-bind-field="views_display"></span>
    <span data-bind-field="retention_3s_pct_display"></span>
  </div>
</div>

<div data-bind-list="top5_low_performers">
  <div data-bind-item>
    <span data-bind-field="vid"></span>
    <span data-bind-field="title"></span>
    <span data-bind-field="views_display"></span>
    <span data-bind-field="retention_3s_pct_display"></span>
  </div>
</div>
```

兩側同欄位、同排序 key（**views 降冪**）、差別在 `performance` 標籤來源：高=`high` 池、低=`low` 池。v1.6 起對稱化（PR #180 修低門檻後、不再需要「靠 retention 升冪補位」）。容量上限 5、實際不足就顯示實際數量（例如目前 low=4）。

### 卡關偵測

```html
<div data-bind-list="stuck_by_status">
  <div data-bind-item>
    <span data-bind-field="status"></span>
    <span data-bind-field="count"></span>
    <span data-bind-field="stale_days_threshold"></span>
    <span data-bind-field="oldest_days"></span>
  </div>
</div>
```

### Meta 頁腳

```
data-bind="meta.generated_at"
data-bind="meta.source_commit"
data-bind="meta.engine_version"
```

---

## Tab 切換機制（v1.1）

Nav 點擊切換主區顯示內容。純 CSS + 少量 JS（~20 行，放 index.html 底部）。

### HTML 結構

```html
<!-- Sidebar nav：加 data-tab-target -->
<div class="nav-item" data-tab-target="overview">總覽</div>
<div class="nav-item" data-tab-target="backlog">
  待拍 <span data-bind="nav_counts.待拍"></span>
</div>
<div class="nav-item" data-tab-target="online">
  已上線 <span data-bind="nav_counts.已上線"></span>
</div>
<div class="nav-item" data-tab-target="high">
  🏆 高表現 <span data-bind="nav_counts.performance_high"></span>
</div>
<div class="nav-item" data-tab-target="ideas">
  靈感箱 <span data-bind="nav_counts.total_ideas"></span>
</div>

<!-- Main：每個 tab 一個 section -->
<section class="tab-pane active" data-tab="overview">...</section>
<section class="tab-pane" data-tab="backlog">...</section>
<section class="tab-pane" data-tab="online">...</section>
<section class="tab-pane" data-tab="high">...</section>
<section class="tab-pane" data-tab="ideas">...</section>
```

### CSS

```css
.tab-pane { display: none; }
.tab-pane.active { display: block; }
```

### JS（放 body 底部，zero dependency）

```js
document.querySelectorAll('[data-tab-target]').forEach(nav => {
  nav.addEventListener('click', () => {
    const target = nav.dataset.tabTarget;
    document.querySelectorAll('[data-tab-target]').forEach(n => n.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(t => t.classList.remove('active'));
    nav.classList.add('active');
    const tab = document.querySelector(`.tab-pane[data-tab="${target}"]`);
    if (tab) tab.classList.add('active');
  });
});
```

### build.py 對 tab 結構的要求

- Tab section 使用 `<section class="tab-pane" data-tab="NAME">` — 這是 **UI 專用 tag**，`build.py` 看到 `class="tab-pane"` 不應視為 `data-bind-list` 容器
- 實際上 tab section 沒有 `data-bind-list` 屬性、所以自然不會被誤解析
- 禁止在 tab section 外層加 `data-bind-list`（會造成 regex 混淆）

---

## v1.1 新增 tab 的必要錨點

### Tab: 待拍（backlog）

```html
<section class="tab-pane" data-tab="backlog">
  <div class="panel">
    <div class="panel-title">待拍影片（<span data-bind="nav_counts.待拍"></span>）</div>
    <section data-bind-list="lists.backlog">
      <article class="list-row" data-bind-item>
        <span class="list-vid" data-bind-field="vid"></span>
        <span class="list-title" data-bind-field="title"></span>
        <span class="list-tags" data-bind-field="tags_display"></span>
        <span class="list-days" data-bind-field="days_waiting_display"></span>
      </article>
    </section>
  </div>
</section>
```

### Tab: 已上線（online）

欄位：`vid / title / publish_date / views_display / retention_3s_pct_display / completion_rate_pct_display / performance_label`

### Tab: 高表現（high）

資料來源：`lists.high_performers_full`，欄位同 online

### Tab: 靈感箱（ideas）

資料來源：`lists.ideas`，欄位：`idea_id / topic / status_display / tags_display / days_old_display`

---

## v1.2 新增：Clickable 卡片 → 跳 tab

任何 card / panel / kpi-card 加 `data-tab-target` 屬性 + `.clickable` class → 點擊跳對應 tab。既有 tab 切換 JS 通用處理，不用額外 JS。

### 範例：卡關偵測 4 張 card

```html
<section class="stuck-grid">
  <article class="stuck-card clickable" data-tab-target="ideas">
    <div class="stuck-label">靈感 INBOX</div>
    <div class="stuck-count"><span data-bind="stuck_counts.inbox">—</span> 卡關</div>
    <div class="stuck-hint">時限 ≤ <span data-bind="stuck_thresholds.inbox">—</span> 天</div>
  </article>
  <!-- 同類型 3 張... -->
  <article class="stuck-card">  <!-- 沒 clickable/data-tab-target 的，保留不可點 -->
    <div class="stuck-label">剪輯中</div>
    ...
  </article>
</section>
```

### Clickable 樣式慣例

```css
.stuck-card.clickable { cursor: pointer; transition: border-color .15s, background .15s; }
.stuck-card.clickable:hover { border-color: var(--accent); background: #23272d; }
.stuck-card.clickable::after { content: "→"; float: right; color: var(--text-ghost); }
.stuck-card.clickable:hover::after { color: var(--accent); }
```

### 適用範圍

任何區塊都可套同模式。建議：**資料有具體 detail view 的才加 clickable**；沒 tab 對應的（例如 0 支剪輯中）保持不可點。

---

## v1.3 對齊 Sheets 影片總覽

Dashboard 是 Vercel 版的影片管控；Sheets 是手機上的快照公佈欄。兩邊資料對得起來 UX 一致性重要。

### views 顯示採「萬」制（非 K/M）

```
7,706         → 7706        (< 10,000 顯示原值)
69,700        → 69.7萬
310,000       → 31.0萬
3,135,566     → 313.6萬
100,000,000+  → X.X億
```

Claude Code 端：`build.py` 的 `_short_num(n)`。Sheets 端：`scripts/utils/lib/builders.py:_view_str`。兩邊公式相同。

### tier_display（5 檔細分）對齊 Sheets classify_performance_display

| tier_display | 條件（讀 pipeline _meta.thresholds.performance）|
|--------------|-----------------------------------------|
| 🟢 高+觸及 | high_A（留存） + high_B（觸及）都達 |
| 🟡 高留存 | 僅達 high_A（留存高、觸及一般） |
| 🟠 高觸及 | 僅達 high_B（觸及高、留存一般） |
| 🔴 低 | retention_3s_below OR completion_rate_below |
| · 普通 | 其餘 |

**邏輯 SSoT 寫在 `dashboard/build.py:_tier_display()`，讀 pipeline `_meta.thresholds.performance`（不 hardcode 數字）**。跟 `scripts/utils/lib/config.py` 的重複函式獨立（那份屬 Codex 責任區）。

### next_action（下一步行動提示）

對齊 Sheets `builders.py:_next_action` 邏輯：

| status / 條件 | next_action |
|-------------|-------------|
| 待拍 + 無 script_path | 📝 需寫腳本 |
| 待拍 + days > 30 | ⚠️ 卡太久 |
| 待拍 + days > 7 | ⏰ 等 N 天 |
| 待拍 + 其他 | ✅ 可拍 |
| 剪輯中 | ✂️ 剪輯中 |
| 已上線 + 無 backfill | 📊 需回填 |
| 已上線 + 缺 likes/comments/shares/saves | 📌 補 XX/YY |
| 已上線 + 完整 | ✅ 完成 |

目前 v1.3 只在 online tab 顯示。未來可推廣到 backlog tab。

### Online tab 現在 7 欄

```
VID / 標題 / 觀看 / 留存 / 完播 / tier_display / next_action
```

Grid: `70px 1fr 80px 80px 80px 120px 110px`

---

## v1.5 視覺設計原則：桌面優先

Kai 主要以電腦看 dashboard（1440-1920px 螢幕為主）。設計以桌面為 target、手機為次要。

### Target screen

| 螢幕類別 | 寬度 | 狀態 |
|---------|------|------|
| 小桌面 | 1440px | **primary target**、所有元素舒適單行 |
| 大桌面 | 1920px | title 自然吃剩餘寬、不浪費空間 |
| 平板 | 1200-1439px | sidebar 收起、content 全寬 |
| 手機 | < 1200px | sidebar 收起、橫捲動 |

### 字體

- `body` 基準 **15px / line-height 1.55**（數據 table 閱讀用）
- 數值欄位 `13px`（`tabular-nums` variant 對齊數字）
- 標題欄位 `14-15px`
- Header row `12px` uppercase（跟 sidebar nav-title 一致風格）
- KPI 大數 `32px bold`（保留原設計）

### Grid 原則

- **列表寬度不為手機而縮**、以桌面資訊密度為準
- 8 欄 grid：`84px minmax(300px, 1fr) 96px 96px 96px 140px 160px 104px`
- `minmax(300px, 1fr)` 保證 title 最少 300px（約 20 個中文字）、最多彈性吃剩餘
- 數值欄使用固定 px 寬度（避免不同 tab 間欄位對不齊）
- 分級 / 動作欄 140-160px（emoji + 中文 label 最長情境）

### 顏色

- 數值 `--text`（主要色、不再 dim）
- meta 資料（tier、days）`--text-dim`
- 提示/警示（動作未完成）`--yellow`
- 已完成提示 `--text-ghost`（不搶眼）
- Header label `--text-ghost`（視覺層次在數據下）

### 間距

- `.list-row` padding `11px 0`（桌面呼吸空間）
- gap 16px（欄間距）
- panel padding 16-18px

### 退化規則

`@media (max-width: 1200px)`：
- sidebar 隱藏
- 2-col section（KPI, Top5 + 贏家公式）改 1-col
- 8 欄 table 允許橫捲動（不縮欄）

### 判定是否打破原則

新增元素時先問：
1. 桌面 1440px 寬這東西放哪？
2. 打開手機看需要橫捲是否可接受？
3. 字級 < 13px 能看清？> 18px 不會過大？

三題答「不行」才回頭改設計、不要預設為手機縮排。

---

## 升版規則

當需要新增欄位：

1. 在 `data-schema.json` 的 `fields` 加欄位 + 升 `version`
2. 同步更新本檔（ui-contract.md）的錨點清單 + 升 version
3. Claude Code 改 `build.py` 計算該欄位
4. Claude design 改 `index.html` 加對應 `data-bind` 標籤
5. 本地跑 `python3 dashboard/build.py --dry-run` 驗證 schema 完整

四項缺一 → build 會 fail，強制四件同步。
