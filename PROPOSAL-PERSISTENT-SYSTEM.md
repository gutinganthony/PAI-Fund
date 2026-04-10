# 提案：持久化投資系統架構

> 2026-04-10 | 回應用戶對過去一週可靠性的不滿

---

## 問題診斷

過去一週（4/7-4/10）的可靠性記錄：

| 日期 | 該發生的事 | 實際結果 | 根因 |
|------|-----------|---------|------|
| 4/7 | 系統建立 | ✅ 手動完成 | — |
| 4/8 09:00 | Cron scan | ⚠️ LLM 成功，delivery 失敗 | DingTalk 配置錯誤 |
| 4/8 21:00 | Cron scan | ❌ LLM timeout | Prompt 太重 |
| 4/9 09:00 | Cron scan | ❌ LLM timeout | Prompt 太重 |
| 4/10 09:00 | Cron scan | ❌ 未執行 | Consecutive errors 導致跳過 |
| 4/10 17:08 | 手動觸發 | ✅ 成功 | 精簡後的 prompt |
| Weekly review | 從未觸發 | ❌ 0 runs | 未驗證就上線 |

**成功率：1/5 = 20%。不可接受。**

核心問題不是 cron 設定，而是**整個系統過度依賴 LobsterAI 在線**。

---

## 當前架構的脆弱點

```
         LobsterAI (單點故障)
              │
    ┌─────────┼─────────┐
    │         │         │
  Cron     Session   Dashboard
  (失敗4次)  (需在線)   (需啟server)
```

1. **Cron 依賴 LLM**：每次觸發要呼叫 Claude，任何 timeout/auth/model 問題都會失敗
2. **Dashboard 需要啟 HTTP server**：`python -m http.server` 死了就看不到
3. **交易日誌只在 SQLite**：只能本機存取，沒有遠端查看方式
4. **策略文件是 markdown**：沒有結構化的方式讓其他 AI 讀取接手
5. **沒有歷史趨勢**：只有每日快照，沒有損益曲線

---

## 提案：三個方案比較

### 方案 A：GitHub Pages（推薦）

```
standalone_scan.py → data.json → git push → GitHub Pages
     (本機)           (本機)      (自動)      (全球可存取)
```

**優點**：
- **零依賴**：不需要 LobsterAI、不需要 server、不需要 Notion API
- **永久可存取**：`https://jakechien.github.io/trading-system/` 隨時打開
- **Git = 時間機器**：每次 push 都是快照，可以 diff 看任何一天的變化
- **Claude Code / 其他 AI 可讀**：clone repo 就能接手整個系統
- **免費**：GitHub Pages 完全免費
- **CI/CD ready**：未來可加 GitHub Actions 自動跑 scan

**缺點**：
- Repo 需要 public（或付費 private pages）
- 需要先移除 .env 裡的 API keys（改用 GitHub Secrets）

**實作**：
1. 建 `jakechien/trading-system` repo（private + GitHub Pages）
2. `standalone_scan.py` 跑完後自動 `git push`
3. Dashboard HTML 直接從 GitHub Pages serve
4. 每日 scan JSON 存在 `journal/scans/` 目錄，自動累積歷史

**時間**：30 分鐘

---

### 方案 B：Notion Database

**優點**：
- UI 漂亮，手機也好看
- 可以分享連結給別人看

**缺點**：
- 依賴 Notion API（又一個可以壞的東西）
- 結構化資料 → Notion → 讀回來，轉換損耗大
- 其他 AI 讀 Notion 很麻煩（需要 API key + 理解 block 結構）
- 不是 code-first，版本控制差
- Notion 免費版有 API rate limit

**結論**：增加複雜度但不增加可靠性。❌ 不推薦。

---

### 方案 C：Local Site + 自動開機啟動

**優點**：
- 最簡單，目前已有 dashboard/index.html
- 不需要上傳任何東西

**缺點**：
- 只能在這台電腦看
- 電腦關機就看不到
- 其他 AI 無法遠端接手
- 沒有歷史版本

**結論**：目前的做法。不夠好。❌ 不推薦作為最終方案。

---

## 推薦：方案 A（GitHub Pages）+ 強化版

### 完整架構

```
┌──────────────────────────────────────────────────────────┐
│                    DATA LAYER (本機)                      │
│                                                          │
│  standalone_scan.py ──→ journal/scans/YYYY-MM-DD.json    │
│                    ──→ dashboard/data.json                │
│                    ──→ dashboard/history.json (累積)       │
│                    ──→ git commit + push (自動)            │
├──────────────────────────────────────────────────────────┤
│                    TRIGGER LAYER (三層冗餘)                │
│                                                          │
│  L1: Windows Task Scheduler (09:05, 12:00) ← 不需要 AI   │
│  L2: LobsterAI Cron (09:00) ← 有 AI 分析能力            │
│  L3: LobsterAI Heartbeat ← 補漏                         │
├──────────────────────────────────────────────────────────┤
│                    VIEW LAYER (隨時可看)                   │
│                                                          │
│  GitHub Pages: https://[user].github.io/trading-system/  │
│  ├── Dashboard (持倉、市場、策略)                          │
│  ├── 交易日誌 (每筆交易記錄)                               │
│  ├── 策略說明 (S1-S5 + Leopold)                           │
│  └── 損益曲線 (歷史趨勢圖)                                │
├──────────────────────────────────────────────────────────┤
│                    HANDOFF LAYER (AI 可接手)               │
│                                                          │
│  SYSTEM.md ── 系統規格書（任何 AI 讀完就能操作）            │
│  trading-system.schema.json ── 結構化資料格式定義          │
│  .env.example ── 需要哪些 credentials                     │
│  README.md ── 人類可讀的操作手冊                           │
└──────────────────────────────────────────────────────────┘
```

### 關鍵設計原則

1. **Python 是唯一依賴**：scan、dashboard、push 全部用 Python，不需要 Node/LLM/API
2. **冪等**：跑 10 次和跑 1 次結果一樣
3. **漸進式**：每天只 append，永遠不覆蓋歷史
4. **可讀**：JSON + Markdown，人類和 AI 都能讀
5. **可交接**：新的 AI 只需要讀 SYSTEM.md 就能接手操作

### 需要你做的事

1. **創建 GitHub repo**：`trading-system`（可以 private）
2. **啟用 GitHub Pages**：Settings → Pages → Deploy from branch
3. **確認 Windows 已登錄 git credentials**：`git push` 能正常運作
4. **執行 setup_windows_scheduler.bat**（已完成 ✅）

### 我會做的事

1. 建立 `dashboard/history.json` 累積每日損益數據
2. Dashboard 加上損益曲線圖（用純 JS，不需要任何套件）
3. 建立 `SYSTEM.md` — AI 交接文件
4. 修改 `standalone_scan.py` 掃描後自動 `git add + commit + push`
5. 確保 .env 不會被 push（已在 .gitignore）

---

## 未來可擴展

| 功能 | 難度 | 依賴 |
|------|------|------|
| GitHub Actions 自動 scan | M | GitHub Secrets for API keys |
| Telegram Bot 推送警報 | S | Telegram Bot Token |
| 損益曲線對比 S&P 500 | S | yfinance |
| 多策略 backtest 自動化 | L | 已有 backtest-expert skill |
| 手機 PWA 版 dashboard | M | 純前端 |

---

## 對你的承諾

過去一週 20% 的成功率是我的失敗。我建了東西但沒有測試就上線，沒有備援機制，出了問題也沒有及時修復。

新的架構設計原則：
- **先測試再上線**（standalone_scan.py 已通過完整測試 ✅）
- **不依賴單一系統**（三層冗餘觸發）
- **數據永遠可存取**（GitHub Pages，不需要本機在線）
- **可交接**（SYSTEM.md 讓任何 AI 能接手）
