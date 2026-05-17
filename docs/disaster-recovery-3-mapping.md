# Disaster Recovery 3 — main ← PR #377 data/ 對照表

> **產生日期**：2026-04-30（v2 重寫、v1 是錯方向 title-based mapping）
> **branch**：`claude/data-correction-vid-001-061`
> **階段**：1 / 4（mapping、待 Kai 校對）
> **作者**：Claude（read-only、未動 main 上任何檔）

---

## 真相轉變（v1 → v2）

| | v1 假設（錯）| v2 真相（對）|
|---|------|------|
| Truth source | main pipeline.json | **PR #377 上的 pipeline.json** |
| main 已上線數 | 41 是事實 | 41 是退回前的舊狀態 |
| 缺的 20 支需怎麼處理 | 新建空 entry 給員工回填 | **PR #377 上已回填好、cherry-pick 過來即可** |
| 階段 3 動作 | title-based 重編碼 + 新建空 entry | **cherry-pick PR #377 的 data/ 6 檔到 main** |

PR #377 上 pipeline.json 的 61 已上線 entries 編碼跟 Kai golden source **100% 對齊**（VID-001=賠了3000萬…、VID-060=台中店王逢甲闆娘…、VID-061=紅茶便宜原因薄利多銷）、且 60/61 已有 backfill data（只 VID-003 珍奶對決 沒回填）。

---

## §1 PR #377 vs main 差異一覽（data/ 6 檔）

| 檔案 | main | pr-377 | diff 行數 | 動作 |
|------|------|--------|----------|------|
| `data/kai/pipeline.json` | 61 VID（41 已上線 + 18 待拍 + 缺 026/043）| **79 VID（61 已上線 + 18 待拍）** | +2194 | overwrite |
| `data/kai/lessons.json` | 21 lessons | **28 lessons**（多 L-0022~0028）| +96 | overwrite |
| `data/kai/performance-patterns.json` | risk_patterns=4（含幻影 VID 引用）| **risk_patterns=12**（已清理） | +64 | overwrite |
| `data/kai/todos.json` | 20 todos | **23 todos**（多 T-0021~0023）| +82 | overwrite |
| `data/kai/hardening-archive.json` | 0 entries | 0 entries | +8 | overwrite（schema/timestamp 變動）|
| `data/template/pipeline.json` | engine template 舊版 | engine template 新版 | +126 | overwrite |

> 註：以上「overwrite」= cherry-pick PR #377 上該檔覆蓋 main、不做 entry-level 合併（main 上沒有 PR #377 之後新生的真實資料、無合併必要）。

---

## §2 PR #377 上 pipeline.json 完整 entry 列表（請 Kai 校對）

### 2.1 已上線（61 支）

| VID | publish_date | title | backfill | hook_type | learning |
|-----|--------------|-------|----------|-----------|----------|
| VID-001 | 2025-12-07 | 賠了3000萬才知道的事 | ✓ | D3 | ✓ |
| VID-002 | 2025-12-10 | 一中店面租金大公開 | ✓ | B2 | ✓ |
| VID-003 | 2025-12-13 | 珍奶對決 大陸VS臺灣 | ✗ | - | - |
| VID-004 | 2025-12-14 | 真正奢侈的事 | ✓ | - | ✓ |
| VID-005 | 2025-12-15 | 取「店名」必看!! | ✓ | - | ✓ |
| VID-006 | 2025-12-18 | 企業家不會讀書 | ✓ | - | ✓ |
| VID-007 | 2025-12-20 | 可以一直試喝の飲料店 | ✓ | - | - |
| VID-008 | 2025-12-25 | 巡分店「關心」員工 | ✓ | - | ✓ |
| VID-009 | 2025-12-26 | 全公司都是女生 | ✓ | D3 | ✓ |
| VID-010 | 2025-12-28 | 被鴨屎香檸紅耽誤的品項？ | ✓ | - | ✓ |
| VID-011 | 2026-01-01 | 做人 — 租金十幾萬但我不趕走她 | ✓ | B2 | ✓ |
| VID-012 | 2026-01-04 | 租店面還要注意這點 | ✓ | D1 | ✓ |
| VID-013 | 2026-01-13 | 台中店王月收入公開（加盟主訪談） | ✓ | D3 | ✓ |
| VID-014 | 2026-01-15 | 飲料品牌為什麼超多 | ✓ | - | ✓ |
| VID-015 | 2026-01-16 | 燒仙草在Threads爆了!! | ✓ | - | ✓ |
| VID-016 | 2026-01-19 | 老闆賠錢檸檬挑戰 | ✓ | - | - |
| VID-017 | 2026-01-21 | 八曜和茶內幕公開 | ✓ | - | - |
| VID-018 | 2026-01-22 | 沒特色 | ✓ | - | - |
| VID-019 | 2026-01-24 | 要出新品？你來決定！ | ✓ | - | - |
| VID-020 | 2026-01-28 | 開飲料店好不好賺 | ✓ | - | - |
| VID-021 | 2026-01-30 | 這店員...要到IG了 | ✓ | - | - |
| VID-022 | 2026-02-03 | 沒人說的大實話 | ✓ | - | - |
| VID-023 | 2026-02-05 | 草莓檸檬茶新品 | ✓ | - | - |
| VID-024 | 2026-02-10 | 年貨大街擺兩攤 十天後的數字 | ✓ | D3 | ✓ |
| VID-025 | 2026-02-11 | 桃園中正突襲檢查 | ✓ | - | - |
| VID-026 | 2026-02-14 | 脆上爆紅美食 值得買嗎？ | ✓ | - | - |
| VID-027 | 2026-02-16 | 發年終 財神到 | ✓ | - | ✓ |
| VID-028 | 2026-02-19 | 發年終2 AKA整闆娘 | ✓ | - | - |
| VID-029 | 2026-02-20 | 年貨大街2 擺攤賺多少？ | ✓ | - | - |
| VID-030 | 2026-02-23 | 阿檸一中店的停業危機 | ✓ | B1 | ✓ |
| VID-031 | 2026-02-24 | 千金買房 萬金買鄰居 | ✓ | B1 | ✓ |
| VID-032 | 2026-02-25 | 回頭看五年前 | ✓ | - | - |
| VID-033 | 2026-02-27 | 被00後員工... | ✓ | - | - |
| VID-034 | 2026-02-28 | 加盟割韭菜 | ✓ | - | - |
| VID-035 | 2026-03-01 | 當我追蹤員工IG | ✓ | - | ✓ |
| VID-036 | 2026-03-02 | 逢甲商圈為什麼沒落 | ✓ | B2 | ✓ |
| VID-037 | 2026-03-03 | 桃園阿檸開店花多少 | ✓ | - | - |
| VID-038 | 2026-03-03 | 給小費就要跳舞 | ✓ | - | - |
| VID-039 | 2026-03-04 | 這年頭老闆真難當 | ✓ | - | - |
| VID-040 | 2026-03-05 | 越南要開十間店？ | ✓ | - | - |
| VID-041 | 2026-03-07 | 加盟必做兩件事 | ✓ | - | ✓ |
| VID-042 | 2026-03-09 | 老闆之間不聊工作？ | ✓ | - | - |
| VID-043 | 2026-03-10 | 被迫停業記者都來了 | ✓ | - | - |
| VID-044 | 2026-03-11 | 回應網路惡意攻擊 | ✓ | - | - |
| VID-045 | 2026-03-13 | 一中阿檸賠多少？ | ✓ | - | - |
| VID-046 | 2026-03-16 | 加盟展你不知道的秘密 | ✓ | - | - |
| VID-047 | 2026-03-18 | 傻師傅湯包合拍 | ✓ | - | - |
| VID-048 | 2026-03-20 | 怎麼挑Show Girl | ✓ | - | - |
| VID-049 | 2026-04-08 | 戰爭漲價倉儲的重要性 | ✓ | - | - |
| VID-050 | 2026-04-09 | 老闆員工PK做飲料 | ✓ | - | - |
| VID-051 | 2026-04-10 | 搬家啦新廠辦介紹 ep1 | ✓ | - | ✓ |
| VID-052 | 2026-04-14 | 新廠辦 ep2 辦公區域大升級 | ✓ | - | ✓ |
| VID-053 | 2026-04-15 | 新店面選址還有隱藏成本？！ | ✓ | - | - |
| VID-054 | 2026-04-16 | 西屯阿檸來啦！ | ✓ | - | - |
| VID-055 | 2026-04-17 | 實際走訪松柏嶺茶廠 | ✓ | - | ✓ |
| VID-056 | 2026-04-20 | 生吃茶葉 台灣茶歷史 | ✓ | - | ✓ |
| VID-057 | 2026-04-21 | 飲料店茶葉一天用量？ | ✓ | - | ✓ |
| VID-058 | 2026-04-22 | 為什麼飲料店很難全部使用台灣紅茶 讓我們來告訴你 | ✓ | D2 | ✓ |
| VID-059 | 2026-04-23 | Threads 上說的壞消息： | ✓ | B2 | - |
| VID-060 | 2026-04-24 | 台中店王逢甲闆娘 開第二家了!! | ✓ | D1 | - |
| VID-061 | 2026-04-27 | 紅茶便宜原因薄利多銷 | ✓ | - | - |

**已上線回填統計**：60/61 已回填、48/61 缺 hook_type、27/61 缺 learning。回填動作將是員工後續任務（不在 disaster recovery 3 範圍）。

---

### 2.2 待拍（18 支）

| VID | title | script_path |
|-----|-------|-------------|
| VID-062 | 加盟是割韭菜？ | 2026-02-05_加盟割韭菜_雙軌腳本_V1.md |
| VID-063 | 加盟主半夜打電話求救 | 2026-03-07_加盟主半夜打電話求救_腳本_V1.md |
| VID-064 | 展場攤位的真實花費 | 2026-03-10_展場攤位真實花費_腳本_V1.md |
| VID-065 | placeholder | 2026-03-18_創業自由_腳本_V1.md |
| VID-066 | 加盟不是只給你一家店 是給你整個後勤 | 2026-03-18_搬新辦公室_腳本_V1.md |
| VID-067 | 一個塑膠杯，漲了40% | 2026-03-20_塑膠杯漲價_腳本_V1.md |
| VID-068 | 台中店王要開第二家了 | 2026-03-26_台中店王二店東海_腳本_V1.md |
| VID-069 | 去找加盟主 | (無) |
| VID-070 | 問員工：老闆最討人厭的習慣 | 2026-03-26_問員工老闆習慣_腳本_V1.md |
| VID-071 | 龍老闆是誰：鹹酥雞老闆跨界加盟紅茶巴士 | (無) |
| VID-072 | 為什麼紅茶巴士的茶可以這麼便宜 | 2026-03-26_茶葉產地系列_腳本_V1.md |
| VID-073 | 龍老闆的選擇：為什麼砸 130 萬跨產業加盟 | (無) |
| VID-074 | 老闆面試 Kai：你憑什麼當我總部 | (無) |
| VID-075 | 花生可樂新品 | 2026-04-13_花生可樂_腳本_V1.md |
| VID-076 | 逛加盟展像逛動物園、3 種人一眼就能分 | 2026-04-29_加盟展3種人_腳本_V1.md |
| VID-077 | 加盟展 5 秒識人術 | (無) |
| VID-078 | 加盟展上有 3 種人、最後會買的只有 1 種 | 2026-04-30_加盟展3種人_腳本_V1.md |
| VID-079 | 5 秒內我就知道誰是來開店的 | 2026-04-30_5秒識人_腳本_V1.md |

⚠️ **疑似重複待拍 entry**（請 Kai 確認）：
- **VID-068 ↔ Kai VID-060 已上線**：「台中店王要開第二家了」vs「台中店王逢甲闆娘 開第二家了!!」可能是同題、待拍腳本已被拍出來上線。建議 archive VID-068（script_path 留歷史）。
- **VID-076 ↔ VID-078**：都是「加盟展 3 種人」題目、script_path 不同日期（04-29 vs 04-30）、可能是不同版本。建議擇一保留。
- **VID-077 ↔ VID-079**：都是「加盟展 5 秒識人」題目。建議擇一保留。

---

### 2.3 inbox / selected / archived（13 支、無 VID）

| status | idea_id | source_inspiration |
|--------|---------|--------------------|
| selected | IDEA-001 | 夜市最暴利的攤位是什麼？ |
| inbox | IDEA-002 | 夜市攤位到底誰最賺錢 |
| inbox | IDEA-003 | Kai 體驗 網咖的茶 |
| archived | IDEA-004 | 加盟展：來的人90%不會開店 |
| archived | IDEA-006 | 加盟展現場突發型 |
| archived | IDEA-007 | 加盟展一天日記 |
| archived | IDEA-008 | 幫你問老闆不敢問的 |
| archived | IDEA-009 | 我勸你不要加盟 |
| archived | IDEA-011 | 街訪：加盟展逛一圈你覺得開飲料店要多少錢？ |
| inbox | IDEA-012 | 街訪：路人猜加盟我們一個月賺多少 |
| inbox | IDEA-013 | 街訪：你願意花130萬開一家飲料店嗎？ |
| inbox | IDEA-020 | 老闆的一天 |
| inbox | IDEA-021 | 冰塊減少不等於茶變多 |

---

## §3 lessons.json 新增的 7 條（L-0022~0028）

PR #377 上比 main 多 7 條 lessons（具體內容於 cherry-pick 後可看）。Kai 確認 cherry-pick 方向後、可單獨 dump 出來看。

## §4 todos.json 新增的 3 條（T-0021~0023）

PR #377 上比 main 多 3 條 todos：T-0021 / T-0022 / T-0023。同上、cherry-pick 後可看。

## §5 performance-patterns.json risk_patterns 4 → 12

PR #377 上 risk_patterns 從 4 條擴充到 12 條、且按主任務描述「已清掉幻影 VID-067/068/069/073/076 引用」。

---

## §6 階段 3 執行清單（待 Kai 階段 2 拍板後）

1. **cherry-pick PR #377 上 6 檔到 `claude/data-correction-vid-001-061` branch**：
   ```
   git checkout pr-377 -- \
     data/kai/pipeline.json \
     data/kai/lessons.json \
     data/kai/performance-patterns.json \
     data/kai/todos.json \
     data/kai/hardening-archive.json \
     data/template/pipeline.json
   ```
2. **驗證**：
   - 跑 `python scripts/lint/rules-lint.py`
   - 跑 `python scripts/ops/video-ops.py validate-all`
   - 跑 `pytest tests/test_pipeline_regression_guard.py`
   - 期望全部 pass（PR #377 已驗證過）
3. **CHANGELOG**：07-changelog/CHANGELOG.md 加 v5.72 disaster recovery 3 entry
4. **bump engine-manifest.json**（若 PR #377 已 bump、保留其值；否則 v5.72）
5. **commit + push 到 `claude/data-correction-vid-001-061`**
6. **開 draft PR**（不 auto-merge）、PR body 列：
   - 為什麼 cherry-pick PR #377 部分檔
   - 跟 PR #377 完整 PR 的關係（cherry-pick subset、PR #377 後續可 close 或保留）
   - CI 驗證結果
7. **PR #377 後續處理**（Kai 拍板）：
   - 選項 A：close PR #377（資料部分已合進來、其他 100+ 檔改動已過時）
   - 選項 B：保留 PR #377、後續 rebase 重 base（耗時、不建議）

---

## §7 待 Kai 階段 2 拍板的點

請 Kai 確認以下點、Claude 才動階段 3：

- [ ] §1 6 檔 overwrite 方向正確？（無 entry-level merge 需要）
- [ ] §2.1 61 已上線編碼 + title 是否全部對齊 Kai golden source？（特別 VID-068 桃園阿檸 publish_date 跟 VID-067 重複用 2026-03-03、Kai 確認否）
- [ ] §2.2 18 待拍是否有需要先合併/archive 的疑似重複（VID-068 / VID-076 vs 078 / VID-077 vs 079）？
- [ ] §6 PR #377 的後續處理（A close / B 保留 rebase）？
- [ ] 若 cherry-pick 完成、Kai 是否要連同階段 4「特別編碼清單」（todo + vid-correction-pending.md）一併建？還是回填的事員工自然處理、不需特別清單？

---

> 階段 1 v2 結束。等 Kai 校對。
