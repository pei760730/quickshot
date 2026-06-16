# performance-patterns.json Schema Contract

> version: 1.2 | last_updated: 2026-06-15
> 角色：Claude (reader/injector) × CLI 層 (writer/computer)
>
> **v1.2**：移除 `skill_effectiveness()` 計算項（producer 有、唯一 consumer 從未被呼叫、零消費假迴圈、整套移除）
> **v1.1**：執行者欄位從「Codex」改稱「CLI 層」(雙 agent 拆分退役後、概念合併、IO 契約不變)

SSoT 檔案：`data/[operator]/performance-patterns.json`

---

## 頂層結構

```json
{
  "_meta": { "version", "last_updated", "description", "source" },
  "proven_openings": [...],
  "proven_ctas": [...],
  "proven_formulas": [...],
  "risk_patterns": [...],
  "unverified_formulas": [...],
  "update_rules": { "add_proven", "add_risk", "min_evidence" }
}
```

---

## proven_openings / proven_ctas 欄位

每個 entry 代表一個已驗證的高表現 pattern。

| 欄位 | 型別 | 寫入者 | 說明 |
|------|------|--------|------|
| `code` | string | extract-learning | pattern 代碼（如 `"B2"`, `"D3"`, `"C3"`） |
| `name` | string | extract-learning | 人類可讀名稱（如 `"好奇缺口"`） |
| `vid_evidence` | string[] | extract-learning | 高表現證據 VID 列表 |
| `last_evidence_date` | string | _add_vid_evidence | `YYYY-MM-DD` 最近加入證據的日期 |
| `low_evidence` | string[] | _check_pattern_decay | 使用此 pattern 的低表現 VID（衰減用） |
| `degraded` | bool | _check_pattern_decay | 是否已衰減 |
| `degraded_date` | string | _check_pattern_decay | 衰減標記日期 |
| `degraded_reason` | string | _check_pattern_decay | 衰減原因 |

### 計算欄位（compute_pattern_stats 寫入，每次回填後更新）

| 欄位 | 型別 | 計算方式 | 說明 |
|------|------|---------|------|
| `sample_size` | int | `len(vid_evidence)` | 高表現證據數 |
| `total_uses` | int | 所有已回填影片中使用此 pattern 的數量 | openings 用 hook_type 匹配，CTAs 用 learning.cta 匹配 |
| `win_rate` | float | `sample_size / total_uses` | 勝率（0-1） |
| `confidence` | string | 見下表 | `"low"` / `"medium"` / `"high"` |

### confidence 計算門檻

| 等級 | 條件 | 定義位置 |
|------|------|---------|
| `low` | total_uses < 3 | `config.py:PATTERN_THRESHOLDS["confidence_medium_min"]` |
| `medium` | 3 <= total_uses < 8 | `config.py:PATTERN_THRESHOLDS["confidence_high_min"]` |
| `high` | total_uses >= 8 | 同上 |

---

## proven_formulas 欄位

| 欄位 | 型別 | 寫入者 | 說明 |
|------|------|--------|------|
| `formula` | string | extract-learning | 自然語言公式描述 |
| `vid_evidence` | string[] | extract-learning | 高表現證據 VID |
| `tags` | string[] | extract-learning | 語意標籤 |
| `added_date` | string | _add_vid_evidence | `YYYY-MM-DD` 首次新增日期 |
| `last_evidence_date` | string | _add_vid_evidence | 最近證據日期 |
| `sample_size` | int | compute_pattern_stats | 同上 |
| `total_uses` | int | compute_pattern_stats | formulas 無法自動匹配，= sample_size |
| `win_rate` | float | compute_pattern_stats | = 1.0（無法計算真實勝率） |
| `confidence` | string | compute_pattern_stats | 基於 sample_size |

---

## risk_patterns 欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `pattern` | string | 失敗模式描述 |
| `vid_evidence` | string[] | 低表現 VID 列表 |
| `description` | string | 詳細說明 |
| `avg_retention` | string | 平均留存率（人類可讀） |
| `avg_completion` | string | 平均完播率（人類可讀） |
| `added_date` | string | `YYYY-MM-DD` |

### 單支低表現 risk（extract-learning 寫入）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `mode` | string | 失敗模式 |
| `detail` | string | 失敗細節 |
| `vid` | string | 對應 VID |
| `date` | string | `YYYY-MM-DD` |

---

## unverified_formulas 欄位

被 `cleanup_unverified_formulas()` 移出的無證據公式。

| 欄位 | 型別 | 說明 |
|------|------|------|
| 同 proven_formulas | — | 原始欄位保留 |
| `moved_date` | string | 移出日期 |
| `moved_reason` | string | 移出原因 |

---

## 衰減機制

| 觸發 | 條件 | 動作 |
|------|------|------|
| 低表現使用 proven pattern | `low_evidence` 累積 >= 2（`decay_low_evidence_trigger`） | 標記 `degraded=true` |
| re-backfill 升級（low→non-low） | VID 從 low_evidence 移除 + 低於門檻 | 撤銷 `degraded` |

---

## 讀寫分工

| 操作 | 執行者 | 函數 |
|------|--------|------|
| 讀取 patterns 做注入 | Claude（Skill prompt） | 讀 JSON 直接引用 |
| 寫入 vid_evidence | CLI 層 | `_add_vid_evidence()` |
| 計算 stats | CLI 層 | `compute_pattern_stats()` |
| 衰減檢查 | CLI 層 | `_check_pattern_decay()` |
| 交叉分析 | CLI 層 | `cross_dimensional_stats()` |

## 修改規則

- **新增計算欄位**：CLI 層實作 + 更新此文件 + 同步 injection protocol
- **修改 pattern 結構**：雙方對齊後才動
- **門檻調整**：改 `config.py:PATTERN_THRESHOLDS` + 更新此文件
