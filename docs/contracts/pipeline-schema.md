# Pipeline Schema Contract

> version: 2.1 | last_updated: 2026-05-15
> 雙方契約：Claude Code (prompt/skill) + Codex (backend/infra)
> 🚨 schema-migration: v2.1（engine v5.97、Issue #438、整層退役 legacy `pipeline.json`、純 sharded SSoT、`.gitignore` 防誤建）
> 🚨 schema-migration（歷史）: v2.0（engine v4.x、pipeline 改為 sharded storage、legacy `pipeline.json` 仍為相容輸出）

SSoT 檔案（**唯一資料來源、v2.1+**）：
- `data/[operator]/pipeline/_meta.json`
- `data/[operator]/pipeline/items/VID-NNN.json`
- `data/[operator]/pipeline/items/IDEA-NNN.json`

**Legacy 已退役**（v2.1 / engine v5.97）：
- ~~`data/[operator]/pipeline.json`~~ — Phase 4 git rm + `.gitignore` `data/*/pipeline.json` 防再建
- `_load_pipeline_sharded()` write-on-load 副作用已移除（解 Issue #438 silent regression）
- `load_pipeline()` 為 backward-compat alias、內部已純走 `get_pipeline_data()`

---

## `_meta` 段（資料驅動設定）

Python 的狀態機、驗證、門檻全部從 `_meta` 讀取，不硬編碼。

### _meta 欄位

| 欄位 | 型別 | 說明 | 消費者 |
|------|------|------|--------|
| `version` | string | schema 版本，目前 `"2.0"` | validate.py |
| `last_updated` | string | `YYYY-MM-DD`（TW UTC+8） | 參考用 |
| `next_idea_id` | int | 下一個 IDEA 編號 | pipeline.py `add_item()` |
| `next_vid` | int | 下一個 VID 編號 | pipeline.py `add_video()` |
| `statuses.idea` | string[] | 合法靈感狀態 | `["inbox", "selected", "cooldown"]` |
| `statuses.video` | string[] | 合法影片狀態 | `["待拍", "剪輯中", "已上線"]` |
| `statuses.terminal` | string[] | 終端狀態 | `["archived"]` |
| `transitions` | dict[str, str[]] | 合法狀態轉移圖 | pipeline.py `transition_item()` |
| `thresholds.stale_days` | dict[str, int] | 各狀態卡關天數 | Claude 提醒用 |
| `thresholds.backfill_due_days` | int | 上線後幾天需回填 | Claude 回填提醒 |
| `thresholds.performance` | dict | 高/低表現門檻 | backfill.py `classify_performance()` |
| `_meta.sedimentation.max_proposals_per_backfill` | int | 每次 backfill 最多提出幾條規則建議（建議值 2） | Claude 主動沉澱 |
| `_meta.sedimentation.fallback_threshold` | int | fallback 規則提案門檻（對齊舊版 3） | sedimentation.py fallback |
| `_meta.quality.levels` | dict | L0/L1/L2 機器可讀品質分級條件 | Claude/Codex 共用 |
| `_meta.verifier.checks` | dict | 5 項 verifier 檢查門檻（衝突感、AI 殘留等） | save/verifier/scoring |
| `thresholds.shelf_life_stale_days` | dict | timely/trending 過期天數 | `classify_idea_freshness()` |
| `thresholds.shelf_life_expire_days` | dict | trending 徹底過期天數 | `classify_idea_freshness()` |
| `valid_title_types` | string[] | 合法標題類型 | `save_script()` 驗證 |
| `valid_hook_types` | string[] | 合法開場類型 | `save_script()` 驗證 |
| `valid_versions` | string[] | 合法腳本版本 | `save_script()` 驗證 |
| `valid_verifier_predictions` | string[] | 合法預測值 | `save_script()` 驗證 |

### transitions 狀態圖

```
inbox → selected / cooldown / archived
selected → 待拍 / cooldown / archived
cooldown → inbox / selected / archived
待拍 → 剪輯中
剪輯中 → 已上線
已上線 → （終端，不可轉移）
archived → inbox
```

### performance 門檻

| 路徑 | 條件 | 結果 |
|------|------|------|
| **unknown** | **retention_3s 或 completion_rate 為 null（來源無資料）且 views 不足 high_B 門檻** | **unknown**（v4.25+ L-0024）|
| high_A | retention_3s >= 70 AND completion_rate >= 40 | high |
| high_B | views >= 300,000 AND completion_rate >= 40 | high（views 路徑、不需 retention）|
| high_AB | 同時滿足 A + B | high (AB) |
| low | retention_3s < 40 OR completion_rate < 15（兩值皆非 null）| low |
| normal | 其餘 | normal |

> ⚠️ **L-0024 hardened**：`retention_3s=0.0` 是「資料未抓到」的 sentinel、不是真值。若 views>0 + retention=0、判定為無效；backfill 寫入端 (Codex) 應 reject 或轉 null；分類器遇 retention=null 必歸 `unknown`、不歸 `low`。事件流見 `data/{operator}/lessons.json` L-0024。

### sedimentation / quality / verifier（中央 rulesheet）

```json
{
  "_meta": {
    "sedimentation": {
      "max_proposals_per_backfill": 2,
      "fallback_threshold": 3
    },
    "quality": {
      "levels": {
        "L0": {"pass_count": "5/5", "max_ai_residue_count": 0, "min_conflict_score": 7},
        "L1": {"pass_count": "4/5", "max_ai_residue_count": 1, "min_conflict_score": 5},
        "L2": {"pass_count": "3/5", "max_ai_residue_count": 2, "min_conflict_score": 4}
      }
    },
    "verifier": {
      "checks": {
        "conflict_score_min": 4,
        "ai_residue_count_min": 1,
        "data_consistency_required": true,
        "format_complete_required": true,
        "pass_count_min_ratio": "3/5"
      }
    }
  }
}
```

---

## items 陣列（影片 + 靈感）

每個 item 代表一個靈感或影片。靈感 `vid=null`，影片 `vid!=null`。

### 必填欄位

| 欄位 | 型別 | 說明 | 寫入者 |
|------|------|------|--------|
| `idea_id` | string | `IDEA-NNN` | add-idea / add |
| `topic` | string | 主題 | add-idea / add |
| `status` | string | 當前狀態（見 _meta.statuses） | transition |
| `created_date` | string | `YYYY-MM-DD` | add-idea / add |
| `status_history` | array | `[{status, date}]` 審計軌跡 | transition |

### 選填欄位（影片階段）

| 欄位 | 型別 | 說明 | 寫入時機 |
|------|------|------|---------|
| `vid` | string \| null | `VID-NNN`，靈感為 null | confirm（IDEA→待拍） |
| `tags` | string | 主題類型標籤 | add / confirm |
| `title` | string | 封面標題 | confirm / save |
| `publish_date` | string | `YYYY-MM-DD` 上線日期 | transition → 已上線 |
| `script_path` | string | 腳本檔案相對路徑 | save |
| `source` | string | `"pipeline"` \| `"quick-shot"` | add |
| `source_inspiration` | string | 原始靈感描述 | add |
| `source_idea_id` | string | 關聯的 IDEA-NNN | confirm |
| `skill_used` | string | 使用的 Skill 名稱 | save |
| `script_status` | string \| null | `"待補"` for quick-shot | add |
| `notes` | string \| null | 備註 | 任意時點 |
| `backfill_due_date` | string | `YYYY-MM-DD` 回填到期日 | transition → 已上線 |
| `shelf_life` | string \| null | `"evergreen"` \| `"timely"` \| `"trending"` | add-idea |

### save 階段欄位

| 欄位 | 型別 | 說明 | 寫入者 |
|------|------|------|--------|
| `title_type` | string | T1-T5（見 _meta.valid_title_types） | save |
| `hook_type` | string | D1-D3, B1-B3（見 _meta.valid_hook_types） | save |
| `version` | string | A1-D5（見 _meta.valid_versions） | save |
| `verifier_prediction` | string | high/normal/low | save |
| `save_date` | string | `YYYY-MM-DD` | save |

### generation_trace（可選，save 時寫入）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `date` | string | `YYYY-MM-DD` |
| `patterns_injected` | string[] | 注入的 proven patterns（如 `["B2", "D3"]`） |
| `risk_patterns_avoided` | string[] | 迴避的 risk patterns |
| `degradation_used` | string \| null | 觸發的降級路徑（如 `"D1→D4"`) |
| `persona_deviation_score` | int \| null | 偏離度分數（0-10+） |

### verifier_scores（save 時自動寫入）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `conflict_score` | int | 0-10 衝突感評分 |
| `retention_prediction` | string | 留存預測等級 |
| `ai_residue_count` | int | AI 味殘留數量 |
| `data_consistency` | bool | 數據一致性 |
| `format_complete` | bool | 格式完整性 |
| `pass_count` | string | 如 `"5/5"` |
| `date` | string | `YYYY-MM-DD` |

### verifier_accuracy（backfill 時自動寫入）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `predicted` | string | save 時的 verifier_prediction |
| `actual` | string | backfill 判定的 performance |
| `match` | bool | predicted == actual |

### backfill 段

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `backfilled_date` | string | Y | `YYYY-MM-DD` |
| `views` | int | Y | 觀看數 |
| `retention_3s` | float \| null | Y | 3 秒留存率 (0-100)。**null 代表「來源無資料」、`0.0` 視為無效 sentinel（views>0 + retention=0 不可能）→ 寫入時應 reject 或自動轉 null**（v4.25 L-0024 hardened）|
| `completion_rate` | float \| null | Y | 完播率 (0-100)；同 retention，null 代表來源無資料 |
| `performance` | string | Y | `"high"` / `"normal"` / `"low"` / `"unknown"`（v4.25+：retention 或 completion 為 null 時必歸 unknown、不歸 low）|
| `data_quality` | string | N | `"incomplete_retention"` / `"incomplete"` 等、標記 backfill 物件可信度（v4.25+） |
| `path` | string | N | `"A"` / `"B"` / `"AB"`（僅 high） |
| `learning_extracted` | bool | Y | 是否已提取學習 |
| `engagement_rate` | float | N | 互動率 (0-100) |
| `profile_clicks` | int | N | 主頁點擊數 |
| `likes` | int | N | 按讚數 |
| `comments` | int | N | 留言數 |
| `shares` | int | N | 分享數 |
| `saves` | int | N | 收藏數 |
| `reposts` | int | N | 轉發數 |
| `new_followers` | int | N | 新增追蹤數 |
| `reached_accounts` | int | N | 觸及帳號數 |
| `video_length_seconds` | float | N | 影片長度(秒) |
| `avg_watch_seconds` | float | N | 平均觀看秒數 |
| `profile_source_pct` | float | N | 主頁來源佔比 |
| `diagnosis` | dict | N | 自動診斷結果（見下） |

### backfill.diagnosis 段

| 欄位 | 型別 | 說明 |
|------|------|------|
| `diagnosed_date` | string | `YYYY-MM-DD` |
| `post_type` | string \| null | 收藏型/分享型/按讚型/均衡型/啞彈 |
| `missing_fields` | string[] | 缺失的互動欄位 |
| `strengths` | string[] | 強項描述 |
| `weaknesses` | string[] | 弱項描述 |
| `prescriptions` | string[] | 改善建議 |

### learning 段（extract-learning 寫入）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `extracted_date` | string | `YYYY-MM-DD` |
| `type` | string | `"high"` / `"low"` / `"normal"` |
| `opening` | string | 開場類型代碼 |
| `cta` | string | CTA 類型代碼 |
| `hook` | string | 開場金句（截取 80 字） |
| `turning_point` | string | 轉折點 |
| `formula` | string | 腳本公式 |
| `failure_mode` | string | 失敗模式（僅 low） |
| `failure_detail` | string | 失敗細節（僅 low） |
| `notes` | string | 備註（僅 normal） |

---

## 修改規則

- **Claude Code**：讀取 `_meta.valid_*` 決定存檔參數，讀取 items 做分析/提醒
- **Codex**：實作所有寫入邏輯（透過 video-ops.py CLI），驗證欄位合法性
- **新增欄位**：雙方先在此文件對齊，再各自實作
- **刪除/改名欄位**：必須通知對方 + 更新此文件 + 更新 `conftest.py:make_video()`
