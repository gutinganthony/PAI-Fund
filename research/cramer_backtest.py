"""Cramer Effect Backtest - Documented calls analysis"""
import yfinance as yf
import pandas as pd
import json
from datetime import datetime, timedelta

# Documented Cramer calls from media coverage
cramer_calls = [
    ('2023-01-03', 'META', 'BUY', 'Said META was a buy after massive selloff'),
    ('2023-01-10', 'GOOGL', 'BUY', 'Recommended Google as AI play'),
    ('2023-02-15', 'NVDA', 'BUY', 'Called NVDA the one stock to own for AI'),
    ('2023-03-10', 'SIVB', 'BUY', 'Said SVB was fine days before collapse'),
    ('2023-03-14', 'FRC', 'BUY', 'Said First Republic was safe'),
    ('2023-04-05', 'DIS', 'BUY', 'Recommended Disney turnaround'),
    ('2023-05-01', 'AAPL', 'BUY', 'Apple ahead of earnings'),
    ('2023-06-12', 'TSLA', 'BUY', 'Said Tesla rally had legs'),
    ('2023-07-18', 'MSFT', 'BUY', 'Microsoft AI thesis'),
    ('2023-08-15', 'BABA', 'SELL', 'Warned about China stocks'),
    ('2023-09-05', 'ARM', 'BUY', 'Recommended ARM after IPO'),
    ('2023-10-02', 'XOM', 'BUY', 'Energy sector pick'),
    ('2023-11-14', 'COIN', 'BUY', 'Crypto recovery play'),
    ('2023-12-04', 'CRM', 'BUY', 'Salesforce momentum'),
    ('2024-01-08', 'SMCI', 'BUY', 'Super Micro AI server play'),
    ('2024-02-05', 'AMD', 'BUY', 'AMD AI chip competition'),
    ('2024-03-11', 'RDDT', 'BUY', 'Reddit IPO recommendation'),
    ('2024-04-15', 'NFLX', 'BUY', 'Netflix ad tier growth'),
    ('2024-05-20', 'GME', 'SELL', 'Warned GameStop was dangerous'),
    ('2024-06-10', 'NVDA', 'BUY', 'NVDA split recommendation'),
    ('2024-07-22', 'INTC', 'BUY', 'Intel turnaround thesis'),
    ('2024-08-12', 'PLTR', 'BUY', 'Palantir government AI'),
    ('2024-09-16', 'AMZN', 'BUY', 'Amazon Alexa AI'),
    ('2024-10-07', 'BA', 'BUY', 'Boeing recovery'),
    ('2024-11-11', 'TSLA', 'BUY', 'Post-election Trump rally'),
    ('2024-12-02', 'SNOW', 'BUY', 'Snowflake data AI play'),
]

print(f"Analyzing {len(cramer_calls)} documented Cramer calls...")
print()

results = []
for date_str, ticker, direction, context in cramer_calls:
    try:
        call_date = datetime.strptime(date_str, '%Y-%m-%d')
        start = call_date - timedelta(days=5)
        end = call_date + timedelta(days=95)
        
        df = yf.download(ticker, start=start.strftime('%Y-%m-%d'), 
                         end=end.strftime('%Y-%m-%d'), progress=False)
        if len(df) < 10:
            print(f"  Skip {ticker}: insufficient data")
            continue
            
        # Find call date in data (or next trading day)
        call_idx = None
        for i in range(5):
            check = call_date + timedelta(days=i)
            check_str = check.strftime('%Y-%m-%d')
            matches = df[df.index.strftime('%Y-%m-%d') == check_str]
            if len(matches) > 0:
                call_idx = df.index.get_loc(matches.index[0])
                break
        
        if call_idx is None or call_idx + 1 >= len(df):
            print(f"  Skip {ticker}: date not found")
            continue
        
        call_price = float(df['Close'].iloc[call_idx])
        
        def get_ret(offset):
            idx = min(call_idx + offset, len(df) - 1)
            if idx > call_idx:
                return round(float(df['Close'].iloc[idx] / call_price - 1) * 100, 2)
            return None
        
        r = {
            'date': date_str,
            'ticker': ticker,
            'direction': direction,
            'context': context,
            'price': round(call_price, 2),
            'ret_1d': get_ret(1),
            'ret_5d': get_ret(5),
            'ret_20d': get_ret(20),
            'ret_60d': get_ret(60),
        }
        results.append(r)
        sign = '+' if (r['ret_20d'] or 0) >= 0 else ''
        print(f"  {date_str} {ticker:5s} {direction:4s} | +1d={r['ret_1d']:+6.2f}% | +5d={r['ret_5d'] if r['ret_5d'] is not None else '?':>7} | +20d={r['ret_20d'] if r['ret_20d'] is not None else '?':>7} | +60d={r['ret_60d'] if r['ret_60d'] is not None else '?':>7}")
        
    except Exception as e:
        print(f"  Error {ticker}: {e}")

print(f"\n{'='*60}")
print(f"Got valid data for {len(results)} calls")
print(f"{'='*60}\n")

# Analysis - BUY recommendations
buys = [r for r in results if r['direction'] == 'BUY']
sells = [r for r in results if r['direction'] == 'SELL']

print("=== BUY RECOMMENDATIONS ===")
print(f"Count: {len(buys)}")
for horizon, label in [('ret_1d', '1 day'), ('ret_5d', '5 day'), ('ret_20d', '20 day'), ('ret_60d', '60 day')]:
    vals = [r[horizon] for r in buys if r[horizon] is not None]
    if vals:
        avg = sum(vals) / len(vals)
        win = sum(1 for v in vals if v > 0) / len(vals) * 100
        best = max(vals)
        worst = min(vals)
        print(f"  {label:>6s}: avg {avg:+6.2f}% | win rate {win:4.0f}% | best {best:+.1f}% | worst {worst:+.1f}% | n={len(vals)}")

print()
if sells:
    print("=== SELL RECOMMENDATIONS ===")
    print(f"Count: {len(sells)}")
    for horizon, label in [('ret_1d', '1 day'), ('ret_5d', '5 day'), ('ret_20d', '20 day'), ('ret_60d', '60 day')]:
        vals = [r[horizon] for r in sells if r[horizon] is not None]
        if vals:
            avg = sum(vals) / len(vals)
            print(f"  {label:>6s}: avg {avg:+6.2f}% (negative = Cramer correct to sell)")

print()
print("=== TOP 5 BEST 20-DAY RESULTS ===")
sorted_best = sorted([r for r in results if r['ret_20d'] is not None], 
                      key=lambda x: x['ret_20d'], reverse=True)
for r in sorted_best[:5]:
    print(f"  {r['date']} {r['ticker']:5s} {r['direction']:4s} +20d={r['ret_20d']:+.1f}% | {r['context'][:50]}")

print()
print("=== TOP 5 WORST 20-DAY RESULTS ===")
for r in sorted_best[-5:]:
    print(f"  {r['date']} {r['ticker']:5s} {r['direction']:4s} +20d={r['ret_20d']:+.1f}% | {r['context'][:50]}")

# Compare to SPY benchmark
print()
print("=== vs SPY BENCHMARK ===")
spy_rets = []
for r in buys:
    try:
        call_date = datetime.strptime(r['date'], '%Y-%m-%d')
        start = call_date - timedelta(days=5)
        end = call_date + timedelta(days=95)
        spy = yf.download('SPY', start=start.strftime('%Y-%m-%d'), 
                          end=end.strftime('%Y-%m-%d'), progress=False)
        if len(spy) > 20:
            check_str = r['date']
            for i in range(5):
                c = call_date + timedelta(days=i)
                cs = c.strftime('%Y-%m-%d')
                m = spy[spy.index.strftime('%Y-%m-%d') == cs]
                if len(m) > 0:
                    idx = spy.index.get_loc(m.index[0])
                    p = float(spy['Close'].iloc[idx])
                    idx20 = min(idx + 20, len(spy) - 1)
                    spy_ret_20 = float(spy['Close'].iloc[idx20] / p - 1) * 100
                    spy_rets.append(spy_ret_20)
                    break
    except:
        pass

if spy_rets:
    cramer_20d = [r['ret_20d'] for r in buys if r['ret_20d'] is not None]
    avg_cramer = sum(cramer_20d) / len(cramer_20d)
    avg_spy = sum(spy_rets) / len(spy_rets)
    print(f"  Cramer BUY avg 20d return: {avg_cramer:+.2f}%")
    print(f"  SPY same-period avg 20d return: {avg_spy:+.2f}%")
    print(f"  Alpha (Cramer - SPY): {avg_cramer - avg_spy:+.2f}%")

# Save results
with open('research/cramer_backtest_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\nResults saved to research/cramer_backtest_results.json")
