# Cron 故障復盤

## 故障時間線

| 日期 | 排程時間 | 結果 | 根因 |
|------|---------|------|------|
| 4/7 | 系統建立日 | — | 尚未設 cron |
| 4/8 09:00 | Daily Scan | ✅ LLM 成功，❌ Delivery 失敗 | DingTalk 無 target |
| 4/8 21:00 | Daily Scan | ❌ LLM timeout + ❌ Delivery 失敗 | prompt 太重 + DingTalk |
| 4/9 09:00 | Daily Scan | ❌ LLM timeout | prompt 太重 (consecutive errors=3) |
| 4/10 09:00 | Daily Scan | ⚠️ 未執行？ | nextRunAtMs 指向 4/11，可能跳過 |
| 4/10 17:08 | 手動觸發 | ✅ 成功 (117s) | 精簡 prompt 生效 |
| Weekly Review | 從未執行 | ❌ 0 runs | 尚未到週日，但也未驗證過 |

## 根因分析 (5 Whys)

**問題：每日掃描 4 天只成功 1.5 次（1 次 delivery 失敗但 LLM 成功）**

1. **Why 失敗？** — 3 種不同的失敗模式
2. **Why 有 3 種？** — 從未做過端到端測試就上線
3. **Why 沒測試？** — 建好就直接設 cron，沒有先 dry-run
4. **Why prompt 太重？** — 塞了太多任務（scan + theme + dialectic + trade + dashboard）
5. **Why 沒有備援？** — 完全依賴單一 cron，沒有冗餘機制

## 教訓

1. **新 cron 必須先手動 run 一次確認成功，再設排程**
2. **Cron payload 要極簡，複雜邏輯放在 Python 腳本裡**
3. **不能只有一層保險，需要 heartbeat 作為 fallback**
4. **Delivery 問題和 LLM 問題要分開處理**
5. **連續失敗 5 次會自動停用，需要自我修復機制**
