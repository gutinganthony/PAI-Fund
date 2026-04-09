"""Check all positions across OKX and Alpaca"""
import sys, json
sys.path.insert(0, '.')
from exchange import okx_client as okx
from exchange import alpaca_client as alp

print('=== OKX BALANCE ===')
bal = okx.get_balance()
if bal:
    for c in bal.get('details', []):
        eq = float(c.get('eq', 0))
        if eq > 0.01:
            print(f"  {c['ccy']}: eq={c['eq']}, availBal={c.get('availBal','?')}")

print()
print('=== OKX TICKERS ===')
for pair in ['BTC-USDT', 'ETH-USDT', 'SOL-USDT']:
    t = okx.get_ticker(pair)
    if t:
        print(f"  {pair}: last={t.get('last','?')}")

print()
print('=== ALPACA POSITIONS ===')
positions = alp.get_positions()
if positions:
    for p in positions:
        sym = p['symbol']
        qty = p['qty']
        avg = p['avg_entry_price']
        cur = p['current_price']
        pnl = p['unrealized_pl']
        pnl_pct = float(p['unrealized_plpc']) * 100
        mv = p['market_value']
        print(f"  {sym}: {qty} shares, avg=${avg}, cur=${cur}, PnL=${pnl} ({pnl_pct:.1f}%), MV=${mv}")
else:
    print("  No positions")

print()
print('=== ALPACA ACCOUNT ===')
acct = alp.get_account()
if acct:
    print(f"  Equity: ${acct['equity']}")
    print(f"  Cash: ${acct['cash']}")
    print(f"  Buying Power: ${acct['buying_power']}")

print()
print('=== ALPACA ORDERS (recent) ===')
orders = alp.get_orders(status='all', limit=10)
if orders:
    for o in orders:
        fp = o.get('filled_avg_price', 'pending')
        print(f"  {o['symbol']} {o['side']} {o['qty']} @ {fp} status={o['status']} id={o['id'][:8]}")
