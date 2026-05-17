# lessons.json Schema Contract

> version: 2.3 | last_updated: 2026-04-23
> 雙方契約：Claude Code (consumer + stage curator) + Codex (writer + migration + stats API)
>
> **v2.0 變更（Opus 4.7 全修 Stage C、engine v4.63）**：schema 降維。
> - stage 5 態 → 3 態：`soft` / `hardened` / `archived`
>   - 原 `observation / candidate / active` → `soft`
>   - 原 `graduated` → `hardened`（名稱更清楚表達意圖）
>   - `archived` 保持
> - 刪 4 個 v1.1 假智能欄位：`hit_count` / `last_hit_at` / `hardening_status` / `confidence`
> - 硬化提議從「hit_count ≥ 3 自動觸發」改為「Claude 在對話中主動判斷提議」
> - Migration：`load_lessons()` lazy 自動映射舊 stage（v4.70 移除 one-shot migrate_lessons_to_v2.py、現僅靠 load-time auto-migration）
>
> 舊 v1.x 變更紀錄見 Appendix A。

SSoT 檔案：`data/[operator]/lessons.json`

---

## 為什麼 v2.0 降維

v1.1 引入 `hit_count` / `hardening_status` 是 Opus 4.6 時期為了補「載入 ≠ 使用」的認知負荷而加的觀測欄位、配合「Hit 決策網格強制」產出。實際結果：
- `hit_count` 長期趨近 0（Claude 判斷 hit 的認知負荷仍落 Kai 身上、Hit 網格流於儀式）
- `hardening_status` 狀態機 4 態 × stage 5 態 = 20 種組合、大部分無意義
- `confidence` 欄位無人手動設、預設 0.5 成了 noop

Opus 4.7 能在對話中直接判斷「這次有沒有用到某條 lesson」並自然用一句話標出（「本次避開了 L-0023 的破折號殘留模式」），不需要計數。真正要緊的是兩態：

- **soft**：預載、可能影響生成
- **hardened**：已寫成 test / lint / CLAUDE.md 禁令 / brand.md、不再預載

加上 `archived`（誤判或被取代、終態、保留歷史）共三態。

---

## 結構

```json
{
  "description": "Unified lessons — soft (預載) / hardened (已轉 test/lint/brand/禁令) / archived",
  "schema_version": "2.0",
  "next_id": 1,
  "lessons": [
    {
      "id": "L-0001",
      "origin": "mistake",
      "stage": "soft",
      "pattern": "問題描述（何時觸發、匹配用）",
      "counter_pattern": "正確做法 / 應該怎麼做",
      "evidence": ["VID-023", "VID-031"],
      "scope": ["flow-operator", "humanizer"],
      "source_note": "來源備註（自由文字）",
      "created_at": "2026-04-20",
      "updated_at": "2026-04-21"
    }
  ]
}
```

---

## 欄位定義

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `id` | string | Y | 唯一識別碼、格式 `L-NNNN`、由 `next_id` 遞增 |
| `origin` | enum | Y | 來源管道、見下方 enum |
| `stage` | enum | Y | 生命週期：`soft` / `hardened` / `archived` |
| `pattern` | string | Y | 問題 / 觀察的 pattern 描述（`(origin, pattern)` 為複合去重鍵） |
| `counter_pattern` | string | N | 正確做法 / 避免方式。soft 階段應盡量填、硬化前必填 |
| `evidence` | string[] | N | 相關 VID-NNN 或事件錨點 |
| `scope` | string[] | N | 適用 skill 名稱（如 `["flow-operator"]`）。空陣列 = 全 skill 適用 |
| `source_note` | string | N | 來源備註 / migration 原 `source` 字串 |
| `created_at` | string | Y | YYYY-MM-DD |
| `updated_at` | string | Y | YYYY-MM-DD、每次 stage / counter_pattern 變動時更新 |

---

## enum: origin

| 值 | 觸發 |
|---|---|
| `mistake` | Kai 說「記錯：XXX」 |
| `verifier` | `record-verifier-scores` 沉澱 |
| `humanizer` | humanizer 高頻觸發 |
| `graduated_mistake` | 從 mistake lesson 畢業、重新 emit（歷史相容） |
| `deviation` | Kai 回填時 `diff-script` |
| `deviation_analysis` | 偏差累積分析提案 |
| `manual` | 對話中直接新增（Kai 確認後） |

---

## enum: stage

| 值 | 語意 | 進入條件 | 退出條件 |
|---|---|---|---|
| `soft` | 預載、可能影響下次生成 | 任何管道首次寫入 | Claude 提議硬化、Kai 確認 → `hardened`；或 Kai 說「刪掉」→ `archived` |
| `hardened` | 已寫成 test / lint / 禁令 / brand.md、不再預載 | 由 soft 升 | 終態、不回退 |
| `archived` | 誤判 / 被取代 / 一次性偶發 | 由 soft 降 或 手動 | 終態、不回退 |

**Stage 轉換規則（v2.0）**：
- `soft` → `hardened`（正向升格、經 `/harden` skill 或手動）
- `soft` → `archived`（歸檔）
- `hardened` / `archived` → 任何狀態：**不允許**（終態）

---

## 寫入管道（未變）

### 管道 A：記錯命令
```
Kai 說「記錯：XXX」→ lessons.add(origin="mistake", stage="soft", pattern=XXX)
```

### 管道 B：verifier 沉澱
```
record-verifier-scores 累積 → sedimentation 掃到同類問題 ≥ 3 支
→ lessons.add(origin="verifier", stage="soft", evidence=[VID...])
```

### 管道 C：humanizer 高頻
```
humanizer 修正過程中同類 AI pattern ≥ 3 次
→ lessons.add(origin="humanizer", stage="soft", counter_pattern=修正做法)
```

### 管道 D：diff-script 偏差
```
Kai 回填時 diff-script → 比對生成 vs 實拍
→ lessons.add(origin="deviation", stage="soft", pattern=偏差描述)
```

### 管道 E：對話中新增
```
Claude 對話中觀察 → 提議 → Kai 確認
→ lessons.add(origin="manual", stage="soft")
```

---

## 消費方式

### flow-operator 步驟 0（v1.41+）
```python
all_lessons = load_lessons()
active_lessons = [l for l in all_lessons
                  if l["stage"] == "soft"
                  and (not l["scope"] or "flow-operator" in l["scope"])]
# active_lessons 分 avoid_patterns（有 counter_pattern）+ observations（僅 pattern）
```

### 其他 skill
相同 pattern、scope filter 改自己的 skill 名。scope 為空陣列 = 所有 skill 適用。

### hardened / archived
**不載入**。hardened 的內容已在 test / lint / 禁令 / brand.md、生成時從那裡自動覆蓋。

---

## 硬化流程（v2.0、對應 `/harden` skill Stage D）

### 觸發（對話中、非門檻）

Claude 觀察到「同一 soft lesson 反覆影響生成、counter_pattern 穩定、值得升硬」→ 主動提：

```
💡 L-XXXX 建議硬化：
  觀察：<反覆觀察到的模式>
  路徑：<prompt | lint | test | brand>
  差異：<軟 → 硬執行力差>
  要不要升？
```

v1.x 的 `hit_count ≥ 3` 自動門檻已移除、改為 Claude 主動判斷。

### 硬化路徑（未變）

| Lesson 類型 | 硬化路徑 |
|------------|---------|
| 程式邏輯錯誤 | `tests/test_xxx.py` or `scripts/lint/rules-lint.py` |
| 對話行為 | `CLAUDE.md` 禁令 or `.claude/rules/workflow.md` |
| 品牌知識 | `01-data-brain/brand.md` 對應 section |
| 一次性偶發 | `stage = "archived"` |

### 執行（Stage D `/harden`）

1. Kai 說「升 L-XXXX」或跑 `/harden L-XXXX`
2. Claude 當場寫對應 test / lint / 禁令 / brand diff（用 Python 繞過 Edit deny、見 `02-skill-factory/harden/SKILL.md` §5 種硬化 path）
3. 驗證通過 → `stage = "hardened"`
4. 驗證失敗 → 保持 soft、報告原因

---

## Python API（`scripts/ops/lib/lessons.py`、v4.63 實作）

| 函式 | 簽章 | 回傳 | 說明 |
|------|------|------|------|
| `load_lessons` | `(operator)` | list | 讀取並 auto-migrate v1.x → v2.0（不寫回） |
| `save_lessons` | `(operator, lessons)` | None | 覆寫 |
| `add_lesson` | `(operator, origin, pattern, counter_pattern=None, evidence=None, scope=None, stage="soft", source_note=None)` | `str` | 回傳 lesson_id。已存在 `(origin, pattern)` → 合併 evidence / 更新欄位 |
| `archive_lesson` | `(operator, lesson_id, reason=None)` | `bool` | 標 archived |
| `promote_stage` | `(operator, lesson_id, new_stage)` | `bool` | 只允許 soft → hardened/archived、終態不可動 |
| `lessons_stats` / `stats` | `(operator)` | `{"total", "by_stage": {"soft", "hardened", "archived"}}` | v2.0 簡化、無 threshold / hot / cold |
| `propose_hardening` | `(operator)` | list | 回傳 `stage == "soft"` 且 `counter_pattern` 非空的 lesson（Kai / Claude 決策候選） |
| `query` | `(operator, origin=None, scope=None, stage=None)` | list | 過濾 |

**已刪除的 v1.x API**：`record_hit()` / `set_hardening_status()`

**CLI 對應**：見 `docs/contracts/video-ops-cli.md` §lessons。

---

## 去重規則（未變）

- 主鍵：`(origin, pattern)` 複合鍵
- 同鍵重複寫入 → 合併 evidence + 更新 counter_pattern / source_note / updated_at + 嘗試升 stage（若合法）

---

## Migration

**v1.1 / v1.2 → v2.0**：v4.69 以降只靠 `load_lessons()` lazy auto-migration（one-shot script `migrate_lessons_to_v2.py` 於 v4.70 退役）

- 自動：stage 映射（observation/candidate/active → soft；graduated → hardened；archived → archived）
- 自動：刪 `hit_count` / `last_hit_at` / `hardening_status` / `confidence` 四欄
- 自動：`schema_version` 1.1 → 2.0
- 備份：`data/<operator>/.cache/lessons_pre_v2_YYYYMMDD.json`

`load_lessons()` 額外有 lazy migration（遇舊 stage 直接映射）、讓未跑 migration script 的客戶 repo 仍能正常讀。

---

## 修改規則

- 新增 origin：改本契約 + `lessons.py VALID_ORIGINS` + bump schema_version minor
- 新增 stage 或轉換規則：改本契約 + `lessons.py _can_promote` + bump major（v2.0 → v3.0）
- Stage 晉升仍經 Kai 確認（CLAUDE.md 禁令 2）

---

## Appendix A：v1.x 歷史變更

- **v1.0（2026-04-20）**：三檔合併（claude-mistakes / generation-rules / script-deviations）為單一 lessons.json、用 `origin` 欄位保留來源、5 態 stage
- **v1.1（2026-04-21）**：新增 observability 三欄位（`hit_count` / `last_hit_at` / `hardening_status`）+ Hit 計數規則 + hit ≥ 3 門檻觸發硬化
- **v1.2（2026-04-21）**：schema 無新增、僅對齊 `lessons.py` 實際行為（`record_hit` 回傳型別、`set_hardening_status` API）
- **v2.0（2026-04-23）**：降維、刪 v1.1 觀測欄位、stage 5 → 3 態、硬化從計數觸發改對話主動
- **v2.1（2026-04-23、v4.70）**：Migration 描述對齊 — 移除 one-shot script、改寫為 `load_lessons()` lazy auto-migration 為唯一路徑
- **v2.2（2026-04-23、v4.71）**：硬化路徑引用改指 `harden/SKILL.md`（原 `hardening-queue-schema.md` 已 v4.67 退役）
- **v2.3（2026-04-23、v4.76）**：修正 factually wrong 語句「老三檔已於 v4.36 後 2 週清除」→「於 v4.76 清除」（migration 驗證後提前刪）

老三檔（`*.legacy.json`）於 v4.76 清除（migration 驗證成功後、比原計畫 2 週提前）。本契約 v2.0 之後不再保留 Appendix B 舊三檔映射（可從 v1.0 契約備份查）。
