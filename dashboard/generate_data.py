"""
Generate dashboard data JSON from all sources.
Run: python dashboard/generate_data.py
Output: dashboard/data.json
"""
import sys, json, sqlite3, os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Helpers ──
def safe_float(v, default=0.0):
    try: return float(v)
    except: return default

# ── 1. Alpaca positions ──
from exchange import alpaca_client as alp

alpaca_positions = []
try:
    positions = alp.get_positions() or []
    for p in positions:
        alpaca_positions.append({
            'symbol': p['symbol'],
            'qty': safe_float(p['qty']),
            'avg_price': safe_float(p['avg_entry_price']),
            'current_price': safe_float(p['current_price']),
            'market_value': safe_float(p['market_value']),
            'unrealized_pnl': safe_float(p['unrealized_pl']),
            'unrealized_pnl_pct': safe_float(p['unrealized_plpc']) * 100,
            'platform': 'Alpaca',
        })
except Exception as e:
    print(f"Alpaca positions error: {e}")

# Alpaca account
alpaca_account = {}
try:
    acct = alp.get_account()
    if acct:
        alpaca_account = {
            'equity': safe_float(acct['equity']),
            'cash': safe_float(acct['cash']),
            'buying_power': safe_float(acct['buying_power']),
        }
except Exception as e:
    print(f"Alpaca account error: {e}")

# Alpaca pending orders
alpaca_pending = []
try:
    orders = alp.get_orders(status='open', limit=10) or []
    for o in orders:
        alpaca_pending.append({
            'symbol': o['symbol'],
            'side': o['side'],
            'qty': o.get('qty'),
            'status': o['status'],
            'id': o['id'][:8],
        })
except:
    pass

# ── 2. OKX positions (from known entries, OKX API blocked by Cloudflare) ──
# Use yfinance for crypto prices
try:
    import yfinance as yf
    crypto_prices = {}
    for sym in ['BTC-USD', 'ETH-USD', 'SOL-USD']:
        t = yf.Ticker(sym)
        info = t.info
        p = info.get('regularMarketPrice') or info.get('previousClose', 0)
        crypto_prices[sym.replace('-USD', '')] = safe_float(p)
except:
    crypto_prices = {'BTC': 71000, 'ETH': 2180, 'SOL': 82}

# Known OKX holdings from trade journal
okx_holdings = [
    {'symbol': 'BTC', 'qty': 0.044, 'avg_price': 67975, 'instId': 'BTC-USDT'},
    {'symbol': 'ETH', 'qty': 0.7342, 'avg_price': 2037, 'instId': 'ETH-USDT'},
    {'symbol': 'SOL', 'qty': 6.2436, 'avg_price': 79.84, 'instId': 'SOL-USDT'},
]
okx_usdt = 78097  # approximate from last balance check

okx_positions = []
for h in okx_holdings:
    cur = crypto_prices.get(h['symbol'], h['avg_price'])
    mv = h['qty'] * cur
    cost = h['qty'] * h['avg_price']
    pnl = mv - cost
    pnl_pct = (pnl / cost * 100) if cost > 0 else 0
    okx_positions.append({
        'symbol': h['symbol'],
        'instId': h['instId'],
        'qty': h['qty'],
        'avg_price': h['avg_price'],
        'current_price': round(cur, 2),
        'market_value': round(mv, 2),
        'unrealized_pnl': round(pnl, 2),
        'unrealized_pnl_pct': round(pnl_pct, 1),
        'platform': 'OKX Demo',
    })

okx_total_value = sum(p['market_value'] for p in okx_positions) + okx_usdt

# ── 3. Market temperature from DB ──
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'journal', 'trades.db')
market_temp = {}
try:
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT * FROM market_temperature ORDER BY date DESC LIMIT 1").fetchone()
    if row:
        cols = [d[0] for d in conn.execute("SELECT * FROM market_temperature LIMIT 0").description]
        market_temp = dict(zip(cols, row))
    conn.close()
except Exception as e:
    print(f"DB error: {e}")

# ── 4. Strategy signals ──
fg = market_temp.get('fear_greed', 14)
btc_rsi = market_temp.get('btc_rsi', 55)
crypto_temp = market_temp.get('crypto_temperature', 30)
us_temp = market_temp.get('us_temperature', 41)

strategies = [
    {
        'id': 'S1',
        'name': '動能突破 (Momentum Breakout)',
        'master': 'Minervini',
        'status': 'monitoring',
        'signal': 'neutral',
        'note': 'VCP+RS Screener 就緒，等待突破信號',
    },
    {
        'id': 'S2',
        'name': '價值低估 (Value Undervalued)',
        'master': 'Buffett + 段永平 + Marks',
        'status': 'active',
        'signal': 'buy',
        'note': 'MSFT 半倉已建，QCOM 持續觀察 (moat 風險)',
    },
    {
        'id': 'S3',
        'name': '週期輪動 (Cycle Rotation)',
        'master': 'Kostolany + Lynch + Leopold',
        'status': 'active',
        'signal': 'buy' if crypto_temp < 40 else 'hold',
        'note': f'Crypto 溫度 {crypto_temp:.0f} (偏冷)，US 溫度 {us_temp:.0f} (中性)',
    },
    {
        'id': 'S4',
        'name': '恐慌反彈 (Panic Rebound)',
        'master': 'Marks + Kostolany',
        'status': 'active',
        'signal': 'hold',
        'note': f'Batch 1 已執行。Batch 2 觸發：F&G<10(now={fg}), BTC跌10%, RSI<25 → 0/3',
    },
    {
        'id': 'S5',
        'name': '趨勢追蹤 (Trend Following)',
        'master': 'Minervini + Kostolany',
        'status': 'monitoring',
        'signal': 'neutral',
        'note': '等待確認上升趨勢後啟動',
    },
    {
        'id': 'Leopold',
        'name': 'AI 供應鏈分層 (Leopold Layers)',
        'master': 'Leopold Aschenbrenner',
        'status': 'active',
        'signal': 'hold',
        'note': 'L0 能源 (CEG+VST) 已建倉，L2 雲端 (MSFT) 半倉',
    },
]

# ── 5. Watchlist ──
watchlist = [
    {'symbol': 'QCOM', 'theme': 'CPU', 'status': 'research', 'note': 'Fwd PE 11.5，但 moat 風險 (Apple 自研基帶)'},
    {'symbol': 'LITE', 'theme': '光通訊', 'status': 'watch', 'note': '太貴 (PE 238)，等回撤'},
    {'symbol': 'CIEN', 'theme': '光通訊', 'status': 'watch', 'note': '接近高點，RSI 69'},
    {'symbol': 'RKLB', 'theme': '太空', 'status': 'watch', 'note': '-30% from high，等 S1 突破信號'},
]

# ── 6. Combine all ──
all_positions = okx_positions + alpaca_positions

# Add MSFT pending
msft_pending = False
for o in alpaca_pending:
    if o['symbol'] == 'MSFT':
        msft_pending = True
        msft_price = crypto_prices.get('MSFT', 374.33)
        # get real price
        try:
            t = yf.Ticker('MSFT')
            msft_price = t.info.get('regularMarketPrice') or 374.33
        except:
            msft_price = 374.33
        all_positions.append({
            'symbol': 'MSFT',
            'qty': 25,  # approximate
            'avg_price': 374.33,
            'current_price': msft_price,
            'market_value': 25 * msft_price,
            'unrealized_pnl': 0,
            'unrealized_pnl_pct': 0,
            'platform': 'Alpaca (pending)',
            'note': 'Order accepted, awaiting market open',
        })

total_invested_crypto = sum(p['qty'] * p['avg_price'] for p in okx_holdings)
total_invested_alpaca = sum(p['qty'] * p['avg_price'] for p in alpaca_positions)
total_market_value = sum(p['market_value'] for p in all_positions)
total_pnl = sum(p['unrealized_pnl'] for p in all_positions)

data = {
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'generated_at_local': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),

    'summary': {
        'total_capital': round(okx_total_value + alpaca_account.get('equity', 100000), 2),
        'total_invested': round(total_invested_crypto + total_invested_alpaca + (9500 if msft_pending else 0), 2),
        'total_market_value': round(total_market_value, 2),
        'total_unrealized_pnl': round(total_pnl, 2),
        'okx_equity': round(okx_total_value, 2),
        'alpaca_equity': alpaca_account.get('equity', 0),
        'alpaca_cash': alpaca_account.get('cash', 0),
        'okx_usdt': okx_usdt,
        'position_count': len(all_positions),
    },

    'market': {
        'crypto_temperature': round(crypto_temp, 1),
        'us_temperature': round(us_temp, 1),
        'overall_temperature': round((crypto_temp + us_temp) / 2, 1),
        'fear_greed': fg,
        'btc_price': crypto_prices.get('BTC', 0),
        'btc_rsi': btc_rsi,
        'spy_price': 676.01,
        'vix_proxy': 30.64,
        'avi_score': 5.67,
        'avi_interpretation': '貴但不危險',
    },

    'positions': all_positions,
    'strategies': strategies,
    'watchlist': watchlist,
    'pending_orders': alpaca_pending,
}

# Write JSON
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Dashboard data written to {out_path}")
print(f"Total capital: ${data['summary']['total_capital']:,.2f}")
print(f"Total positions: {data['summary']['position_count']}")
print(f"Total PnL: ${data['summary']['total_unrealized_pnl']:,.2f}")
