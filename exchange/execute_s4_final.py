"""S4 Panic Rebound - Batch 1 (account mode 3 = multi-currency margin, use cross)."""
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
config = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            config[key.strip()] = val.strip()

from okx import Account, MarketData, Trade

flag = "1"
account_api = Account.AccountAPI(config["OKX_API_KEY"], config["OKX_SECRET_KEY"], config["OKX_PASSPHRASE"], flag=flag, debug=False)
market_api = MarketData.MarketAPI(flag=flag)
trade_api = Trade.TradeAPI(config["OKX_API_KEY"], config["OKX_SECRET_KEY"], config["OKX_PASSPHRASE"], flag=flag, debug=False)

# Get prices
prices = {}
for s in ["BTC-USDT", "ETH-USDT", "SOL-USDT"]:
    ticker = market_api.get_ticker(instId=s)
    if ticker and ticker.get("code") == "0" and ticker["data"]:
        prices[s] = float(ticker["data"][0]["last"])
        print(f"{s}: ${prices[s]:,.2f}")

# Balance
bal_resp = account_api.get_account_balance()
usdt_bal = 0
if bal_resp and bal_resp.get("code") == "0":
    for d in bal_resp["data"][0].get("details", []):
        if d["ccy"] == "USDT":
            usdt_bal = float(d.get("availBal", 0))
print(f"\nUSDT: {usdt_bal:,.2f}")

# S4 allocation
s4_total = usdt_bal * 0.20
batch1 = s4_total * 0.30

btc_usdt = round(batch1 * 0.60, 2)
eth_usdt = round(batch1 * 0.30, 2)
sol_usdt = round(batch1 * 0.10, 2)

print(f"\nBatch 1 total: {batch1:,.2f} USDT")
print(f"  BTC: {btc_usdt} USDT")
print(f"  ETH: {eth_usdt} USDT")
print(f"  SOL: {sol_usdt} USDT")

# Execute with tdMode=cross (required for multi-currency margin account)
print(f"\n=== Executing ===")
orders = [
    ("BTC-USDT", str(btc_usdt)),
    ("ETH-USDT", str(eth_usdt)),
    ("SOL-USDT", str(sol_usdt)),
]

filled = []
for inst_id, sz in orders:
    r = trade_api.place_order(
        instId=inst_id,
        tdMode="cross",
        side="buy",
        ordType="market",
        sz=sz,
        tgtCcy="quote_ccy",
    )
    ok = r.get("code") == "0"
    oid = r["data"][0].get("ordId", "") if r.get("data") else ""
    msg = r["data"][0].get("sMsg", "") if r.get("data") else r.get("msg", "")
    print(f"  {inst_id}: {'OK' if ok else 'FAIL'} | ordId={oid} | {msg}")
    if ok and oid:
        filled.append((inst_id, oid))

# Get fill details
print(f"\n=== Fill Details ===")
for inst_id, oid in filled:
    detail = trade_api.get_order(instId=inst_id, ordId=oid)
    if detail and detail.get("code") == "0" and detail["data"]:
        d = detail["data"][0]
        qty = d.get("accFillSz", "0")
        avg_px = d.get("avgPx", "0")
        fee = d.get("fee", "0")
        fee_ccy = d.get("feeCcy", "")
        print(f"  {inst_id}: {qty} @ ${avg_px} | fee: {fee} {fee_ccy}")
        
        # Record to journal
        from journal.trade_journal import init_db, record_entry
        init_db()
        stop_loss = float(avg_px) * 0.85  # S4: -15% hard stop
        trade_id = record_entry(
            strategy="S4-panic-rebound",
            platform="OKX-demo",
            symbol=inst_id,
            side="buy",
            quantity=float(qty),
            entry_price=float(avg_px),
            stop_loss=round(stop_loss, 2),
            entry_reason=f"S4 Batch 1: Crypto Fear&Greed=11 (Extreme Fear), BTC RSI=46.6, temperature=25.2",
            market_context="Extreme Fear zone, BTC at $68k, market panic but price holding above 200MA",
            order_id=oid,
        )
        print(f"    -> Journal ID: {trade_id}")

# Final balances
print(f"\n=== Final Balances ===")
bal_resp = account_api.get_account_balance()
if bal_resp and bal_resp.get("code") == "0":
    for d in bal_resp["data"][0].get("details", []):
        avail = float(d.get("availBal", 0))
        if avail > 0:
            print(f"  {d['ccy']}: {d['availBal']}")
