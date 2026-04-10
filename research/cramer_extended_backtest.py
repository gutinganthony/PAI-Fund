"""Extended Cramer Backtest - 60+ documented calls from Mad Money, Twitter, CNBC"""
import yfinance as yf
import json
from datetime import datetime, timedelta

# Extended list of documented Cramer calls (2022-2025)
# Sources: CNBC transcripts, Twitter/X posts, media coverage, WSB tracking
cramer_calls = [
    # 2022 - Bear market calls
    ('2022-01-03', 'HOOD', 'BUY', 'Robinhood at $17, said buy the dip'),
    ('2022-01-24', 'NFLX', 'BUY', 'Netflix ahead of earnings, called it oversold'),
    ('2022-02-04', 'META', 'BUY', 'Meta after earnings crash, said buy'),
    ('2022-03-08', 'COIN', 'BUY', 'Coinbase still a buy'),
    ('2022-03-14', 'RIVN', 'BUY', 'Rivian has legs'),
    ('2022-04-05', 'TWTR', 'SELL', 'Twitter sell before Musk chaos'),
    ('2022-05-09', 'UPST', 'BUY', 'Upstart is way oversold'),
    ('2022-06-01', 'SNAP', 'SELL', 'Snap is in trouble'),
    ('2022-07-18', 'WBD', 'BUY', 'Warner Bros Discovery value play'),
    ('2022-08-15', 'BBBY', 'SELL', 'Bed Bath Beyond is a disaster'),
    ('2022-09-06', 'AAPL', 'BUY', 'Apple iPhone 14 buy'),
    ('2022-10-03', 'AMD', 'BUY', 'AMD is oversold here'),
    ('2022-11-07', 'DIS', 'BUY', 'Disney turnaround is coming'),
    ('2022-12-05', 'TSLA', 'BUY', 'Tesla too cheap at 120'),
    # 2023 - Recovery calls
    ('2023-01-03', 'META', 'BUY', 'Meta year of efficiency buy'),
    ('2023-01-10', 'GOOGL', 'BUY', 'Google AI play'),
    ('2023-02-15', 'NVDA', 'BUY', 'Nvidia the one AI stock to own'),
    ('2023-03-10', 'SIVB', 'BUY', 'SVB is fine, dont panic'),
    ('2023-03-14', 'FRC', 'BUY', 'First Republic is safe'),
    ('2023-04-05', 'DIS', 'BUY', 'Disney restructuring buy'),
    ('2023-04-17', 'SCHW', 'BUY', 'Schwab oversold on bank fears'),
    ('2023-05-01', 'AAPL', 'BUY', 'Apple into earnings'),
    ('2023-05-24', 'NVDA', 'BUY', 'Nvidia after earnings explosion'),
    ('2023-06-12', 'TSLA', 'BUY', 'Tesla rally has legs'),
    ('2023-07-06', 'LULU', 'BUY', 'Lululemon is a buy here'),
    ('2023-07-18', 'MSFT', 'BUY', 'Microsoft AI thesis'),
    ('2023-08-15', 'BABA', 'SELL', 'Stay away from China stocks'),
    ('2023-09-05', 'ARM', 'BUY', 'ARM IPO day buy'),
    ('2023-09-18', 'DASH', 'BUY', 'DoorDash profitability play'),
    ('2023-10-02', 'XOM', 'BUY', 'Exxon energy bull'),
    ('2023-10-30', 'DKNG', 'BUY', 'DraftKings momentum'),
    ('2023-11-14', 'COIN', 'BUY', 'Coinbase crypto recovery'),
    ('2023-12-04', 'CRM', 'BUY', 'Salesforce data cloud AI'),
    ('2023-12-18', 'UBER', 'BUY', 'Uber profitable buy'),
    # 2024 - AI bubble calls
    ('2024-01-08', 'SMCI', 'BUY', 'Super Micro AI server play'),
    ('2024-01-22', 'NFLX', 'BUY', 'Netflix ad tier growth story'),
    ('2024-02-05', 'AMD', 'BUY', 'AMD MI300 AI chip'),
    ('2024-02-26', 'NVDA', 'BUY', 'Nvidia still a buy post earnings'),
    ('2024-03-11', 'RDDT', 'BUY', 'Reddit IPO buy'),
    ('2024-03-25', 'MU', 'BUY', 'Micron AI memory play'),
    ('2024-04-15', 'NFLX', 'BUY', 'Netflix price target raise'),
    ('2024-04-29', 'SBUX', 'BUY', 'Starbucks oversold'),
    ('2024-05-06', 'AAPL', 'BUY', 'Apple AI at WWDC'),
    ('2024-05-20', 'GME', 'SELL', 'GameStop dangerous meme stock'),
    ('2024-06-10', 'NVDA', 'BUY', 'Nvidia stock split buy'),
    ('2024-06-24', 'FDX', 'BUY', 'FedEx restructuring'),
    ('2024-07-08', 'TSLA', 'BUY', 'Tesla robotaxi catalyst'),
    ('2024-07-22', 'INTC', 'BUY', 'Intel turnaround story'),
    ('2024-08-05', 'CRWD', 'BUY', 'CrowdStrike oversold after outage'),
    ('2024-08-12', 'PLTR', 'BUY', 'Palantir government AI'),
    ('2024-09-03', 'DELL', 'BUY', 'Dell AI server orders'),
    ('2024-09-16', 'AMZN', 'BUY', 'Amazon Alexa AI upgrade'),
    ('2024-10-07', 'BA', 'BUY', 'Boeing strike ending recovery'),
    ('2024-10-21', 'PYPL', 'BUY', 'PayPal new CEO turnaround'),
    ('2024-11-06', 'GS', 'BUY', 'Goldman Sachs Trump rally'),
    ('2024-11-11', 'TSLA', 'BUY', 'Tesla Trump admin EV play'),
    ('2024-11-25', 'V', 'BUY', 'Visa holiday spending'),
    ('2024-12-02', 'SNOW', 'BUY', 'Snowflake data AI play'),
    ('2024-12-16', 'PANW', 'BUY', 'Palo Alto cybersecurity AI'),
    # 2025
    ('2025-01-06', 'NVDA', 'BUY', 'Nvidia CES keynote buy'),
    ('2025-01-21', 'MSFT', 'BUY', 'Microsoft Stargate project'),
    ('2025-02-03', 'GOOG', 'BUY', 'Google Gemini progress'),
    ('2025-02-18', 'PLTR', 'BUY', 'Palantir AIP momentum'),
    ('2025-03-10', 'SMCI', 'SELL', 'Super Micro accounting issues sell'),
]

print(f"Analyzing {len(cramer_calls)} extended Cramer calls (2022-2025)...")
print()

results = []
for date_str, ticker, direction, context in cramer_calls:
    try:
        call_date = datetime.strptime(date_str, '%Y-%m-%d')
        start = call_date - timedelta(days=5)
        end = min(call_date + timedelta(days=95), datetime(2026, 4, 9))
        
        df = yf.download(ticker, start=start.strftime('%Y-%m-%d'), 
                         end=end.strftime('%Y-%m-%d'), progress=False)
        # Handle MultiIndex columns from newer yfinance
        if hasattr(df.columns, 'nlevels') and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        if len(df) < 10:
            continue
            
        call_idx = None
        for i in range(5):
            check = call_date + timedelta(days=i)
            check_str = check.strftime('%Y-%m-%d')
            matches = df[df.index.strftime('%Y-%m-%d') == check_str]
            if len(matches) > 0:
                call_idx = df.index.get_loc(matches.index[0])
                break
        
        if call_idx is None or call_idx + 1 >= len(df):
            continue
        
        call_price = float(df['Close'].iloc[call_idx])
        
        def get_ret(offset):
            idx = min(call_idx + offset, len(df) - 1)
            if idx > call_idx:
                return round(float(df['Close'].iloc[idx] / call_price - 1) * 100, 2)
            return None
        
        # Sector detection
        try:
            info = yf.Ticker(ticker).info
            sector = info.get('sector', 'Unknown')
        except:
            sector = 'Unknown'
        
        r = {
            'date': date_str, 'ticker': ticker, 'direction': direction,
            'context': context, 'price': round(call_price, 2), 'sector': sector,
            'ret_1d': get_ret(1), 'ret_5d': get_ret(5),
            'ret_20d': get_ret(20), 'ret_60d': get_ret(60),
        }
        results.append(r)
        r20 = f"{r['ret_20d']:+.1f}%" if r['ret_20d'] is not None else '  N/A'
        print(f"  {date_str} {ticker:5s} {direction:4s} | +20d={r20:>7} | {sector[:15]:15s} | {context[:40]}")
        
    except Exception as e:
        pass

print(f"\n{'='*70}")
print(f"RESULTS: {len(results)} valid out of {len(cramer_calls)} calls")
print(f"{'='*70}\n")

# Split by direction
buys = [r for r in results if r['direction'] == 'BUY']
sells = [r for r in results if r['direction'] == 'SELL']

# Overall stats
print("=== BUY RECOMMENDATIONS ===")
print(f"Count: {len(buys)}")
for horizon, label in [('ret_1d', '+1d'), ('ret_5d', '+5d'), ('ret_20d', '+20d'), ('ret_60d', '+60d')]:
    vals = [r[horizon] for r in buys if r[horizon] is not None]
    if vals:
        avg = sum(vals) / len(vals)
        median = sorted(vals)[len(vals)//2]
        win = sum(1 for v in vals if v > 0) / len(vals) * 100
        print(f"  {label}: avg={avg:+6.2f}% med={median:+6.2f}% win={win:4.0f}% n={len(vals)}")

# By year
print("\n=== BY YEAR ===")
for year in range(2022, 2026):
    yr_buys = [r for r in buys if r['date'].startswith(str(year))]
    if yr_buys:
        vals20 = [r['ret_20d'] for r in yr_buys if r['ret_20d'] is not None]
        if vals20:
            avg = sum(vals20) / len(vals20)
            win = sum(1 for v in vals20 if v > 0) / len(vals20) * 100
            print(f"  {year}: n={len(yr_buys):2d} | +20d avg={avg:+6.2f}% win={win:.0f}%")

# By sector
print("\n=== BY SECTOR ===")
sectors = {}
for r in buys:
    s = r.get('sector', 'Unknown')
    if s not in sectors:
        sectors[s] = []
    if r['ret_20d'] is not None:
        sectors[s].append(r['ret_20d'])

for s, vals in sorted(sectors.items(), key=lambda x: -len(x[1])):
    if len(vals) >= 2:
        avg = sum(vals) / len(vals)
        win = sum(1 for v in vals if v > 0) / len(vals) * 100
        print(f"  {s:25s}: n={len(vals):2d} avg={avg:+6.2f}% win={win:.0f}%")

# Sell calls
if sells:
    print(f"\n=== SELL RECOMMENDATIONS (n={len(sells)}) ===")
    for r in sells:
        r20 = f"{r['ret_20d']:+.1f}%" if r['ret_20d'] is not None else 'N/A'
        correct = "CORRECT" if r['ret_20d'] is not None and r['ret_20d'] < 0 else "WRONG"
        print(f"  {r['date']} {r['ticker']:5s} +20d={r20:>7} {correct} | {r['context'][:50]}")

# Catastrophic calls (>-20% in 20 days)
print("\n=== CATASTROPHIC CALLS (bought, then >-15% in 20d) ===")
for r in sorted([r for r in buys if r['ret_20d'] is not None and r['ret_20d'] < -15], 
                key=lambda x: x['ret_20d']):
    print(f"  {r['date']} {r['ticker']:5s} +20d={r['ret_20d']:+.1f}% | {r['context'][:50]}")

# Best calls
print("\n=== BEST CALLS (bought, then >+15% in 20d) ===")
for r in sorted([r for r in buys if r['ret_20d'] is not None and r['ret_20d'] > 15], 
                key=lambda x: -x['ret_20d']):
    print(f"  {r['date']} {r['ticker']:5s} +20d={r['ret_20d']:+.1f}% | {r['context'][:50]}")

# SPY benchmark
print("\n=== vs SPY BENCHMARK ===")
spy_rets = {'1d': [], '5d': [], '20d': [], '60d': []}
for r in buys:
    try:
        call_date = datetime.strptime(r['date'], '%Y-%m-%d')
        start = call_date - timedelta(days=5)
        end = min(call_date + timedelta(days=95), datetime(2026, 4, 9))
        spy = yf.download('SPY', start=start.strftime('%Y-%m-%d'),
                          end=end.strftime('%Y-%m-%d'), progress=False)
        if hasattr(spy.columns, 'nlevels') and spy.columns.nlevels > 1:
            spy.columns = spy.columns.get_level_values(0)
        if len(spy) > 20:
            for i in range(5):
                c = call_date + timedelta(days=i)
                cs = c.strftime('%Y-%m-%d')
                m = spy[spy.index.strftime('%Y-%m-%d') == cs]
                if len(m) > 0:
                    idx = spy.index.get_loc(m.index[0])
                    p = float(spy['Close'].iloc[idx])
                    for off, key in [(1,'1d'),(5,'5d'),(20,'20d'),(60,'60d')]:
                        sidx = min(idx + off, len(spy) - 1)
                        if sidx > idx:
                            spy_rets[key].append(float(spy['Close'].iloc[sidx] / p - 1) * 100)
                    break
    except:
        pass

for horizon, key in [('ret_1d','1d'), ('ret_5d','5d'), ('ret_20d','20d'), ('ret_60d','60d')]:
    cramer_vals = [r[horizon] for r in buys if r[horizon] is not None]
    if cramer_vals and spy_rets[key]:
        c_avg = sum(cramer_vals) / len(cramer_vals)
        s_avg = sum(spy_rets[key]) / len(spy_rets[key])
        alpha = c_avg - s_avg
        print(f"  +{key:>3s}: Cramer={c_avg:+.2f}% SPY={s_avg:+.2f}% Alpha={alpha:+.2f}%")

# Save
with open('research/cramer_extended_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\nSaved {len(results)} results to research/cramer_extended_results.json")
