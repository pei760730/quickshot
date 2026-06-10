# Codex Cloud sandbox 一勞永逸配置

> version: 1.0 | last_updated: 2026-06-10
> 對應 ROADMAP 🟡「Codex sandbox 一勞永逸配置」。repo 側已備（`scripts/codex/setup.sh`）、本檔是 Kai 在 Codex Cloud 平台側的一次性操作步驟。

## 目標

讓 Codex 在 sandbox 內能：裝好依賴跑 lint/test、用 `GITHUB_TOKEN` 自己 push branch / 開 PR / close PR——不用每次派工後 Kai 手動收尾。

## Kai 平台側一次性步驟（~5 分鐘）

### 1. 建 fine-grained PAT

GitHub → Settings → Developer settings → Fine-grained tokens → Generate new token：

| 欄位 | 值 |
|------|-----|
| Repository access | Only select repositories → `pei760730/quickshot` |
| Contents | Read and write（push 用）|
| Pull requests | Read and write（開 / close PR 用）|
| 其他權限 | 全不給（最小權限）|
| Expiration | 90 天（到期 GitHub 會寄信、屆時換新貼回 secret 即可）|

### 2. Codex Cloud environment 設定

Codex 平台 → quickshot 對應的 environment → 設定：

1. **Secrets**：新增 `GITHUB_TOKEN` = 上一步的 PAT
2. **Setup script** 欄位填：
   ```bash
   bash scripts/codex/setup.sh
   ```

### 3. 驗證（第一次派工時順帶）

派一個 trivial 任務（如改 `scripts/` 下某檔一行），確認 Codex：

- [ ] setup script 跑完無錯（log 裡有 `── setup 完成 ──`）
- [ ] 能自己 push `codex/<name>` branch
- [ ] 能自己開 PR（body 標 owner、merge-base = main HEAD）

三項都過 → ROADMAP 該項可打勾。

## setup script 做什麼（repo 側、已完成）

`scripts/codex/setup.sh`：

1. `pip install -r requirements-dev.txt`（與 CI 同一套 lint + pytest）
2. git identity（`codex-agent`、commit 歸屬清楚）
3. `GITHUB_TOKEN` → git credential helper（push / PR 權限；無 token 時降級為唯讀模式並印警告、不 fail）
4. fail-fast 自驗：rules-lint + pytest（環境壞在 setup 階段就炸、不浪費派工）

## 安全邊界

- token 只存在 Codex Cloud secret、不進 repo、不進 log（credential helper 從 env 讀）
- PAT 限定單 repo + 最小兩權限；Codex 越權改檔仍有 `territory-lint` CI 擋（`codex/` 前綴白名單、見 `.github/agent-territory.json`）
- 派工規範不變：見 `AGENTS.md` + `workflow.md` §多代理協作
