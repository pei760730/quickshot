# Skill IO Schema v2.3

> version: 2.3 | last_updated: 2026-06-14 | status: **stable**
> 🚨 v2.3（「縮」）：移除 generation_trace 契約（trace 上線 30 天零消費、整套機器退役）。保留 verifier_scores 契約 + VID Inference Stats 不動。

## 目的

本文件定義 vNext 核心 skill 的 IO 契約，作為 `scripts/lint/skill-io-lint.py` 的 SSoT。

---

## 通用格式

所有輸出腳本使用 frontmatter：

```yaml
---
vid: VID-NNN
skill: generation
skill_version: 1.0
generated_at: 2026-04-25
mode: dual-track
phase: check
---
```

### Frontmatter 必填欄位

| field | type | required |
| --- | --- | --- |
| vid | string | yes |
| skill | string | yes |
| skill_version | string | yes |
| generated_at | string | yes |

---

## 核心 Skill IO（vNext 5）

| skill | output fields |
| --- | --- |
| generation | 核心腳本, 毒舌總結 |
| quality | Verifier 結果, 修正摘要 |
| discovery | 候選選題, 排序理由 |
| orientation | 任務定義, 邊界 |
| distillation | lessons 建議, 證據 |

### 1) generation（5 modes）

- modes：`dual-track` / `variant` / `series` / `interview` / `viral`
- 輸出需包含 `## 核心腳本`
- Output Contract 必須明示 `--skill generation` 與 `--mode`

### 2) quality（2 phases）

- phases：`check` / `fix`
- `phase=check` 需能輸出 `verifier_scores`
- Output Contract 必須明示 `record-verifier-scores`
- script-verifier 舊流程已併入 quality `phase=check`

### 3) discovery

- 輸出候選選題與排序理由
- 不直接產生成品腳本

### 4) orientation

- 輸出 task spec、範圍、風險與不做項
- 提供 generation/quality 的前置約束

### 5) distillation

- 輸出 lessons 候選與 evidence 關聯
- 供後續寫入 lessons/hardening 流程

---

## Quality Feedback Contract

### verifier_scores（quality phase=check）

```yaml
verifier_scores:
  required:
    - conflict_score
    - retention_prediction
    - ai_residue_count
    - data_consistency
    - format_complete
    - pass_count
```


### VID Inference Stats

- collector path: `data/.adoption-stats/vid_inference.jsonl`
- record schema: `{"ts":"ISO8601","had_fenced":bool,"vid_inferred":bool}`
- metric policy: monitor 30-day `miss_rate = (fenced_blocks - vid_inferred)/fenced_blocks`
- alert threshold: `miss_rate > 10%` 時提醒評估是否把 VID 升級為必填
- decision source: PR #369 Q3（2026-04-29）

---

## Human-Layer Presentation Spec（v2.2、配 generation v1.2 / quality v1.2）

> 採用閉環價值-成本不對稱的第二層補正。v1.1 解了 trace 寫入率（Claude 寫不寫）、v1.2 解呈現格式（Kai 看不看得懂）。

### 為什麼

`verifier_scores` 6 欄位是給 `adoption-stats` 累積分析的、對 user 當下決策無 actionable value。把它們當對話主視覺、user 看完不知道要不要改稿、回到 0/61 採用率根因。本 spec 強制：人話層先、機器層後。

### 規範

每支 skill（generation / quality）的 Output Contract **必含人話層 4 句話**、且**順序在機器層之前**：

| skill | 人話層 標題 | 4 句話結構 |
| --- | --- | --- |
| generation | `─── AI 自評 ───` | 👍 結論 / ⚠️ 弱點 / 💡 引用大腦 / 📊 同類預測 |
| quality | `─── 體檢結果 ───` | 👍 結論 / ⚠️ 弱點 / 💡 引用大腦 / 📊 同類對比 |

### 4 句話翻譯規則（共用）

| 句 | 來源 | 強制要求 |
| --- | --- | --- |
| 👍 結論 | Claude 自評 + verifier_prediction / pass_count | 三選一：可拍 / 建議重改 / 棄。**禁套話**（如「品質不錯」「符合調性」） |
| ⚠️ 弱點 | 最弱那一項 | actionable specific（例：「鉤子有破折號殘留、改成短句」），不是技術代號（例：`ai_residue=2`）。5 項全過則省略此行 |
| 💡 引用大腦 | brand-refs / cases-refs（實際讀進來的） | 列具體章節編號（如 `[4]論點2 + [8]案例4`），給 user 反查不虛構。mode=viral 改為 `💡 不綁大腦` |
| 📊 同類預測 | `adoption-stats` 同 hook_type filter | 用近 30 支同類數字、不用空泛 `verifier_prediction: "high"` 套話 |

### 機器層降級規則

v1.1 的「即時回饋」段（fenced JSON + CLI summary + 同類比較）在 v1.2 整體**降為腳註**、寫法：

```
（技術詳情：mode=X / hook=Y / pass=N/5 / 跑 `video-ops.py adoption-stats` 看完整趨勢）
```

一行、加括號、放最後。Kai 不展開可忽略、要展開可跑 `adoption-stats` CLI。

### Validation Rule

```yaml
- id: human_layer_presentation_present
  level: ERROR
  check: "generation/quality Output Contract includes 4-line human summary BEFORE machine-layer details"
```

> **lint 落地策略**：v2.2 為規範定義、實際 lint check 由 Claude 對話中守、不寫 lint code（per CLAUDE.md 禁令 #7「能用 prompt 擋就先用 prompt」）。若觀察到反覆違反、再升級為 `scripts/lint/skill-io-lint.py` 規則。

---

## validation_rules（lint 讀取）

```yaml
validation_rules:
  - id: output_contract_section_present
    level: ERROR
    check: "generation Output Contract includes --skill generation + --mode"

  - id: quality_output_contract_present
    level: ERROR
    check: "quality Output Contract includes record-verifier-scores and phase=check"
```

---

## 歷史 lineage（僅對照，不影響主契約）

| retired skill | now mapped to |
| --- | --- |
| flow-operator | generation (mode=dual-track) |
| flow-maximizer | generation (mode=variant) |
| series-engine | generation (mode=series) |
| interview-navigator | generation (mode=interview) |
| viral-knowledge | generation (mode=viral) |
| humanizer | quality (phase=fix) |
| script-verifier | quality (phase=check) |
| hook-killer / title-generator | quality templates / checks |

