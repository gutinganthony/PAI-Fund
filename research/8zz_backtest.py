"""巴逆逆 (8zz / 吃土鋁繩-巴逆逆 / DieWithoutBang) 反指標回測
資料來源：新聞報導中的已知公開發言及交易記錄
"""
import yfinance as yf
import json
from datetime import datetime, timedelta

# 巴逆逆已知公開發言/交易記錄（從新聞報導中提取）
# 格式: (日期, 台股代號, 方向, 來源/說明)
# BUY = 她買進或看多
# SELL = 她賣出或停損
# BEARISH = 她公開表示看空/停損（反指標信號 = 可能是底部）

eight_zz_calls = [
    # K-Media 專訪中提到的交易歷史
    # "投入股市2年，把500萬虧剩220萬"
    # "從早期的長榮航空、高端疫苗、陽明海運"
    
    # 已知的具體案例（從新聞報導提取日期和個股）
    
    # 2024 年
    ('2024-07-15', '2408.TW', 'BUY', '南亞科追高買進，後跌5%停損', '南亞科'),
    ('2024-08-01', '6919.TWO', 'BUY', '康霈 追高買進 苦吞2根跌停', '康霈'),
    ('2024-08-05', '6919.TWO', 'SELL', '康霈 停損賣出 → 後來狂拉33%', '康霈停損後反彈'),
    ('2024-09-15', '00632R.TW', 'BUY', '買進台灣50反1(做空ETF) 看空台股', '台灣50反1'),
    
    # 2025年 關稅風暴期間
    ('2025-03-18', '2330.TW', 'BEARISH', '台積電失守1000元 她被指為元凶(網友戲稱)', '台積電'),
    ('2025-04-07', None, 'BEARISH', '台股連崩3天跌4000點期間 持續持有', '大盤'),
    ('2025-04-09', None, 'BEARISH', '發文「這波可能要把個股類全部停損了」→ 川普立即宣布暫緩關稅 → 台股史上最大漲點', '大盤全部停損'),
]

print("=== 巴逆逆 (8zz) 反指標回測 ===")
print("資料來源：新聞報導中的公開發言")
print()

results = []

# 回測個股案例
stock_calls = [c for c in eight_zz_calls if c[1] is not None]
for date_str, ticker, direction, context, name in stock_calls:
    try:
        call_date = datetime.strptime(date_str, '%Y-%m-%d')
        start = call_date - timedelta(days=5)
        end = min(call_date + timedelta(days=65), datetime(2026, 4, 9))
        
        df = yf.download(ticker, start=start.strftime('%Y-%m-%d'),
                         end=end.strftime('%Y-%m-%d'), progress=False)
        if hasattr(df.columns, 'nlevels') and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        
        if len(df) < 5:
            print(f"  Skip {ticker} ({name}): insufficient data")
            continue
        
        # Find call date
        call_idx = None
        for i in range(5):
            check = call_date + timedelta(days=i)
            check_str = check.strftime('%Y-%m-%d')
            matches = df[df.index.strftime('%Y-%m-%d') == check_str]
            if len(matches) > 0:
                call_idx = df.index.get_loc(matches.index[0])
                break
        
        if call_idx is None:
            print(f"  Skip {ticker} ({name}): date not found")
            continue
        
        call_price = float(df['Close'].iloc[call_idx])
        
        def get_ret(offset):
            idx = min(call_idx + offset, len(df) - 1)
            if idx > call_idx:
                return round(float(df['Close'].iloc[idx] / call_price - 1) * 100, 2)
            return None
        
        r = {
            'date': date_str, 'ticker': ticker, 'name': name,
            'direction': direction, 'context': context,
            'price': round(call_price, 2),
            'ret_1d': get_ret(1), 'ret_5d': get_ret(5),
            'ret_20d': get_ret(20), 'ret_60d': get_ret(60),
        }
        results.append(r)
        
        r5 = f"{r['ret_5d']:+.1f}%" if r['ret_5d'] is not None else 'N/A'
        r20 = f"{r['ret_20d']:+.1f}%" if r['ret_20d'] is not None else 'N/A'
        print(f"  {date_str} {name:8s} {direction:7s} | +5d={r5:>7} +20d={r20:>7} | {context[:40]}")
        
    except Exception as e:
        print(f"  Error {ticker}: {e}")

# 大盤案例（台灣加權指數）
print()
print("=== 大盤案例（台灣加權指數 ^TWII）===")
taiex_calls = [
    ('2025-04-09', '^TWII', 'BEARISH', '發文要全部停損 → 隔天台股史上最大漲點'),
]

for date_str, ticker, direction, context in taiex_calls:
    try:
        call_date = datetime.strptime(date_str, '%Y-%m-%d')
        start = call_date - timedelta(days=5)
        end = min(call_date + timedelta(days=30), datetime(2026, 4, 10))
        
        df = yf.download(ticker, start=start.strftime('%Y-%m-%d'),
                         end=end.strftime('%Y-%m-%d'), progress=False)
        if hasattr(df.columns, 'nlevels') and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        
        if len(df) > 3:
            call_idx = None
            for i in range(5):
                check = call_date + timedelta(days=i)
                check_str = check.strftime('%Y-%m-%d')
                matches = df[df.index.strftime('%Y-%m-%d') == check_str]
                if len(matches) > 0:
                    call_idx = df.index.get_loc(matches.index[0])
                    break
            
            if call_idx and call_idx + 1 < len(df):
                price = float(df['Close'].iloc[call_idx])
                next_price = float(df['Close'].iloc[call_idx + 1])
                ret = (next_price / price - 1) * 100
                print(f"  {date_str} TAIEX BEARISH(停損) → 次日: {ret:+.2f}% (從 {price:.0f} 到 {next_price:.0f})")
                print(f"  → 台股史上最大漲點 (+2,070點)")
    except Exception as e:
        print(f"  Error: {e}")

# 總結
print()
print("=" * 60)
print("=== 巴逆逆反指標分析總結 ===")
print("=" * 60)
print()
print("背景：")
print("  - 本名未公開，暱稱「巴逆逆」/「8zz」")
print("  - Facebook 粉專「吃土鋁繩-巴逆逆」(DieWithoutBang)")
print("  - 投入股市約2年，500萬虧到剩220萬（虧損56%）")
print("  - 被網友封為「反指標女神」「股海冥燈」")
print("  - 她自嘲式地公開每筆虧損交易，形成網路迷因文化")
print()
print("已知交易模式：")
print("  1. 追高買進熱門股 → 立即套牢")
print("  2. 停損後股價立即反彈（康霈案例：停損後拉33%）")
print("  3. 看空/停損時機 = 市場底部信號")
print("  4. 2025/4/9 全部停損 → 隔天台股史上最大漲點")
print()
print("反指標強度評估：")
print("  - 她的 BUY = 短期可能是頂部（追高特性）")
print("  - 她的 SELL/停損 = 可能是底部（最經典的反指標信號）")
print("  - 4/9 停損案例被全國媒體報導，已成為台灣股市迷因")
print()
print("數據限制：")
print("  - 公開資料來源僅有新聞報導（非完整交易記錄）")
print("  - 樣本量過小（<10 筆可追溯案例）")
print("  - 大部分交易細節在 Facebook 粉專（需登入）")
print("  - 無法做統計顯著的量化回測")
print()
print("策略可行性：⭐⭐ (2/5)")
print("  - 定性上是強反指標（停損=底部）")
print("  - 但樣本太少，無法量化")
print("  - 建議：追蹤她的 Facebook 發文作為定性散戶情緒參考")

# Save
with open('research/8zz_backtest_results.json', 'w', encoding='utf-8') as f:
    json.dump({
        'subject': '巴逆逆 (8zz / 吃土鋁繩-巴逆逆)',
        'facebook': 'https://www.facebook.com/DieWithoutBang/',
        'nickname': '反指標女神 / 股海冥燈',
        'known_trades': results,
        'notable_events': [
            {
                'date': '2025-04-09',
                'event': '發文要全部停損',
                'result': '隔天台股史上最大漲點 (+2070點)',
                'media_coverage': '全國主要媒體報導'
            },
            {
                'date': '2024-08',
                'event': '康霈停損',
                'result': '停損後股價反彈33%'
            }
        ],
        'assessment': {
            'contrarian_strength': 'STRONG (qualitative)',
            'data_quality': 'LOW (news reports only)',
            'sample_size': 'INSUFFICIENT (<10)',
            'recommendation': 'Monitor as qualitative sentiment indicator, not quantitative signal'
        }
    }, f, ensure_ascii=False, indent=2)
print("\nSaved to research/8zz_backtest_results.json")
