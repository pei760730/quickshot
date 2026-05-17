---
name: quality
description: 品質 + 修正核心 skill v1.3（vNext 5 核心之一）。整合驗證 + 修正、quality-loop pattern（check ↔ fix、最多 2 round）。phase=fix 跑 24 AI patterns 掃描（shared-references/ai-pattern-detection.md）+ 品牌人格注入；phase=check 跑 5 項驗證（verifier_scores 寫入）+ 引用 hook-templates / title-rules。v1.3 §Output Contract 動詞硬化：把「呼叫 CLI」改為「Bash tool 直接執行 record-verifier-scores、禁止印命令給 Kai 抄」、解 verifier_scores 0/30 行為層失敗（配 generation v1.3 同步）。觸發：Generation 完後自動跑、或 Kai 說「驗證：[腳本]」「humanize：[腳本]」「品質檢查：[腳本]」。
---

Read and follow 02-skill-factory/quality/SKILL.md
