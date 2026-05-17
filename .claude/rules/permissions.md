# 路徑守衛

> version: 7.0 | last_updated: 2026-04-18

受保護路徑透過 `.claude/settings.json` 的 `permissions.deny` 原生機制攔截。

## 受保護路徑

| 路徑 | 說明 |
|------|------|
| `CLAUDE.md` | 系統總指南 |
| `.claude/**` | Hook、規則、設定 |

## 放行方式

Claude Code 原生權限系統攔截 Write/Edit 時，Kai 在 UI 或 CLI 直接授權即可（不再需要手動建 `admin-allow`）。

## 自律規則

- 刪除/改名檔案前列出並等 Kai 確認
- 單次刪除 ≥ 3 個檔案先列出確認
- 不可逆操作額外提醒
