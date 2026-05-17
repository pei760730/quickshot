# 表現模式注入協議（所有生成型 Skills 統一）

> version: 3.0 | last_updated: 2026-04-26
> 自動執行，不需 Kai 觸發。數據不足 → 跳過，不阻塞。
>
> **v3.0**：從 aggregate-only 改 **aggregate（背景）+ case-based retrieval（前景）** 雙軌注入。4.7 推理力下、5 個具體歷史案例 > 全局統計表、解 v1.0 死角 #1（Reading loop 讀取端）。

---

## 兩軌注入設計（v3.0）

| 軌 | 內容 | 來源 | 用途 |
|---|------|------|------|
| **背景**（aggregate）| 全局勝率統計（hook 勝率 / cta 勝率 / formula 勝率）| `data/[operator]/performance-patterns.json` | 給 LLM 整體分布感、知道哪些 pattern 高勝率 |
| **前景**（cases）| 上 5 支同類 VID 的具體 metadata（hook_type / verifier_scores / actual_views / 偏離度）| `scripts/utils/lessons_retrieval.py similar-vids` + `scripts/utils/lib/performance_injection.py:get_similar_cases()` | 給 LLM 具體案例做 RAG-style decision |

**為什麼雙軌**：4.6 時代只塞 aggregate（統計）、因為塞 5 個 case 容易讓 LLM 飄；4.7 推理力下、5 個 case 比統計表更有資訊密度（你看 5 支實際影片數據比看「平均 60%」有用得多）。但 aggregate 提供 baseline、case 提供 ground truth、兩者互補。

## 資料來源

| 來源 | 用途 | 提供函式 |
|------|------|---------|
| `data/[operator]/performance-patterns.json` | aggregate 統計 | （直接讀檔）|
| `data/[operator]/pipeline.json` items | similar VIDs 來源 | `lessons_retrieval.similar_vids(vid, by, limit)` |
| `scripts/utils/lib/performance_injection.py` | 整合 + 注入 payload | `get_similar_cases(vid, n=5)` + `build_injection_payload(vid)` |

## 注入欄位

| 欄位 | 內容 | 注入門檻 |
|------|------|---------|
| proven_openings | 已驗證高表現的開場類型 | ≥ 2 支影片驗證 |
| proven_ctas | 已驗證高表現的 CTA 類型 | ≥ 2 支影片驗證 |
| proven_formulas | 已驗證的腳本公式結構 | ≥ 2 支影片驗證 |
| risk_patterns | 已知失敗模式 | 有記錄即迴避 |

## 計算指標（每次回填後自動更新）

每個 proven pattern 自動攜帶以下指標：

| 欄位 | 計算方式 | 用途 |
|------|---------|------|
| `sample_size` | len(vid_evidence) | 高表現證據數 |
| `total_uses` | 所有已回填影片中使用此 pattern 的數量 | 分母（含高/普/低） |
| `win_rate` | sample_size / total_uses | 勝率 |
| `confidence` | low（<3 次使用）/ medium（3-7）/ high（≥8） | 信心等級 |
| `last_evidence_date` | 最近一次加入證據的日期 | 時效性判斷 |

## 信心等級與注入力度

| 信心等級 | 條件 | 注入方式 |
|----------|------|---------|
| **high** | total_uses ≥ 8 | **強烈推薦**：「📊 此類型勝率 N%（8+ 次驗證）」，優先選用 |
| **medium** | 3 ≤ total_uses < 8 | **建議參考**：「📊 此類型 N 次高表現（勝率 N%）」 |
| **low** | total_uses < 3 | **僅供參考**：照舊邏輯，不額外強調 |
| **degraded** | 有 degraded 旗標 | **降級警告**：「⚠️ 此模式近期表現下滑」 |

## 核心規則

1. 成功模式（proven_*）→ 作為**額外範例**，注入力度隨 confidence 調整
2. 失敗模式（risk_patterns）→ 生成時**主動迴避**
3. 資料為空或欄位不足門檻 → **跳過**，不影響流程
4. win_rate < 30% 的 proven pattern → 降為「僅供參考」，不主動推薦

## 多維度交叉分析

回填 ≥ 10 筆後，Claude 可透過 `cross_dimensional_stats()` 取得：
- **by_hook_type**：各開場類型的平均留存/完播/勝率
- **by_version**：各腳本版本的表現比較
- **by_topic_type**：各主題類型的表現比較
- **by_skill**：各 Skill 產出的影片表現比較
- **combinations**：hook × version 的勝率排行（僅列 ≥ 2 筆的組合）

生成時依 topic_type + version 篩選最相關的 pattern 推薦，而非給全部列表。

## Case-based retrieval（v3.0 前景軌）

### 呼叫流程

generation skill（5 modes）+ quality skill phase=check 跑時、stage 0 載入後額外呼叫：

```python
from scripts.utils.lib.performance_injection import build_injection_payload

payload = build_injection_payload(
    vid="VID-NNN",         # 當前生成的 VID（含 topic_tags）
    n_cases=5,             # 拉幾支歷史案例（預設 5）
    include_aggregate=True # 是否含背景 aggregate（預設 True）
)
# payload = {
#   "background": {"proven_openings": [...], "proven_ctas": [...], ...},
#   "foreground": [
#     {"vid": "VID-040", "hook_type": "D3", "verifier_scores": {...},
#      "actual_views": 8200, "deviation_score": 0.7, "publish_date": "..."},
#     ... up to 4 more
#   ]
# }
```

底層相似度（per `scripts/utils/lessons_retrieval.py`）：topic_tags overlap 50% + performance tier 30% + time decay 20%。

### Prompt 注入範例

```
## 表現模式參考（自動注入）

### 背景（全局統計、4.6 慣性 aggregate）
- 已驗證 hook：D3 勝率 60%（5 次驗證）、B2 勝率 75%（4 次）
- 已驗證 CTA：C3 勝率 55%（3 次）
- 風險模式：開場太慢（迴避）

### 前景（上 5 支同類選題、4.7 case-based ground truth）
| VID | 日期 | hook | 衝突 | AI 殘 | 偏離度 | 觀看 |
|-----|------|------|------|------|--------|------|
| VID-040 | 2026-04-01 | D3 | 8 | 1 | 0.7 | 8,200 |
| VID-035 | 2026-03-22 | B2 | 7 | 2 | 0.4 | 12,400 |
| ...     | ...        | ... | ...| ... | ...    | ...    |

→ 選 hook 時、優先參考前景具體案例（哪個在這類題實際 work）、aggregate 為輔助。
```

## 各 mode 注入重點（generation skill 5 modes）

| mode | 背景注入（aggregate）| 前景注入（cases、n=5）|
|------|---------|---------------|
| dual-track | proven_openings + proven_formulas + risk_patterns | similar VIDs by topic_tags |
| variant | proven_openings → 各變體開場、proven_ctas → 收尾 | similar VIDs（同 topic）逐版本對比 |
| series | proven_openings → 第 1 集 + 高潮集 | similar series VIDs（過去同類系列首尾集表現）|
| interview | proven_openings → 第一個 Q 字卡、proven_ctas → 結尾 A 爆點 | similar interview VIDs（血包三件套表現對照）|
| viral | 不綁背景（per brain-loading.md：viral 不綁大腦）| 不拉前景（不綁品牌、無同類可比）|

quality skill phase=check 也可呼叫 `get_similar_cases()`、用前景案例校準 verifier_prediction。

## 與 v2.0 的相容

- v2.0 aggregate-only 邏輯保留為 v3.0「背景軌」、不刪
- 新增「前景軌」是 additive、舊呼叫端（不知道 case retrieval）仍 work、只是少拿前景
- pipeline.json schema 不變、case retrieval 從現有 items 計算

## 失敗 fallback

- pipeline.json 未有同類 VID（topic_tags overlap = 0）→ 前景空、只用 aggregate
- performance-patterns.json 不存在 → aggregate 空、只用前景
- 兩者皆空 → 純 LLM 從 brand.md 推理、不阻塞
