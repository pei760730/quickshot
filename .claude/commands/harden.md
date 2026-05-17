# /harden

對話內一站式硬化：把 soft lesson 或反覆錯誤當場升為 test / lint / 禁令 / workflow / brand。

## 用法

```
/harden L-XXXX [path]
```

- `L-XXXX`：lesson id、必須 stage=soft
- `path`（optional、Claude 會依脈絡推薦）：`test` / `lint` / `claude_md` / `workflow_md` / `brand_md`

## 流程

1. Claude 讀 lesson `pattern` + `counter_pattern`、草擬 artifact 內容
2. 展示 draft + target path 給 Kai 確認
3. 呼叫 `scripts/ops/lib/hardening.harden_from_dialog()` → 寫檔 + validator
4. 成功：lesson stage → hardened、archive 寫一筆（source=dialog）
5. 失敗：lesson 保留 soft、回報原因

完整規格見 `02-skill-factory/harden/SKILL.md` v1.0。
