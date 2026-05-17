# 人設偏離度計分（SSoT）

> version: 1.0 | last_updated: 2026-04-25
> 從 flow-operator v1.50 §人設偏離度計分 抽出。Phase 5 退役 flow-operator 後改放此處。
> 下游 skill：`generation/SKILL.md` mode=dual-track / variant / series / interview。

## 公式

**基礎分 = 0**、逐項加總：

| 違規項目 | 來源 | 加分 |
|----------|------|------|
| 使用絕對不會說的話 | personas/kai.md [1] | +3 |
| 違反不可妥協原則 | brand.md [0]+[5] | **+5 淘汰** |
| 違反品牌不能做 | brand.md [0]+[1] | **+5 淘汰** |
| 攻擊目標客群 | brand.md [2] | +5 |
| 攻擊最不能被質疑的點 | brand.md [5] | +4 |
| 觸碰刻意迴避話題 | brand.md [5] | +3 |
| 強迫灰色地帶站隊 | brand.md [5] | +2 |
| 價值立場與 [5] 矛盾 | brand.md [5] | +2 |
| 缺少高頻詞彙 | personas/kai.md [1] | +1 |
| 語氣與偏好不符 | personas/kai.md [1] | +1 |
| 資格數字無來源（D 版）| 彈藥庫 | +2 |
| 資格數字捏造（D 版）| — | **+5 淘汰** |
| 給值不符四條任一（D 版）| — | +2 |
| 使用禁用詞 | banned-words.md | +1 重寫 |

## 評級

- **0-3 GREEN**：A 版標準
- **4-6 YELLOW**：C/D 版標準
- **7-8 ORANGE**：B 版上限
- **9+ RED**：淘汰

## 歷史

> 兩個歷史 skill 皆已退役、目錄不存在於 `02-skill-factory/`、僅作來源敘事保留。

- 公式歷史上由 `brain-interface` skill v2.2 維護（engine v5.27、Phase 3 退役）
- 退役後公式內嵌於 `flow-operator` v1.50 SKILL.md（engine v5.42、Phase 5 退役）
- 公式現位於本檔為 SSoT（不再依賴任何 skill 目錄）
