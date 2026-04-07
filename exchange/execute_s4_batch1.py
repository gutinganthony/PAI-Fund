"""S4 Panic Rebound - Batch 1 Execution (fixed)."""
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

from okx import Account, MarketData, Trade, PublicData

flag = "1"
account_api = Account.AccountAPI(config["OKX_API_KEY"], config["OKX_SECRET_KEY"], config["OKX_PASSPHRASE"], flag=flag, debug=False)
market_api = MarketData.MarketAPI(flag=flag)
trade_api = Trade.TradeAPI(config["OKX_API_KEY"], config["OKX_SECRET_KEY"], config["OKX_PASSPHRASE"], flag=flag, debug=False)
public_api = PublicData.PublicAPI(flag=flag)

# Check account mode
print("=== Account Config ===")
acct_config = account_api.get_account_config()
if acct_config and acct_config.get("code") == "0":
    cfg = acct_config["data"][0]
    print(f"  Account mode: {cfg.get('acctLv')} (1=Simple, 2=Single-currency margin, 3=Multi-currency margin, 4=Portfolio margin)")
    print(f"  Position mode: {cfg.get('posMode')}")

# Get instrument info for min sizes
print("\n=== Instrument Info ===")
for inst in ["BTC-USDT", "ETH-USDT", "SOL-USDT"]:
    info = public_api.get_instruments(instType="SPOT", instId=inst)
    if info and info.get("code") == "0" and info["data"]:
        d = info["data"][0]
        print(f"  {inst}: minSz={d.get('minSz')} lotSz={d.get('lotSz')} tickSz={d.get('tickSz')}")

# Get prices
print("\n=== Current Prices ===")
prices = {}
for s in ["BTC-USDT", "ETH-USDT", "SOL-USDT"]:
    ticker = market_api.get_ticker(instId=s)
    if ticker and ticker.get("code") == "0" and ticker["data"]:
        t = ticker["data"][0]
        prices[s] = float(t["last"])
        print(f"  {s}: ${prices[s]:,.2f}")

# Get balance
bal_resp = account_api.get_account_balance()
usdt_bal = 0
if bal_resp and bal_resp.get("code") == "0":
    for d in bal_resp["data"][0].get("details", []):
        if d["ccy"] == "USDT":
            usdt_bal = float(d.get("availBal", 0))
print(f"\n  USDT Available: {usdt_bal:,.2f}")

# Calculate S4 allocation
s4_total = usdt_bal * 0.20  # 20% of capital
batch1 = s4_total * 0.30     # First batch = 30%

btc_budget = batch1 * 0.60
eth_budget = batch1 * 0.30
sol_budget = batch1 * 0.10

# For spot market orders on OKX, we can use tgtCcy="quote_ccy" to specify USDT amount
# This avoids min size issues with base currency
print(f"\n=== S4 Batch 1 Plan ===")
print(f"  Total S4 allocation: {s4_total:,.2f} USDT")
print(f"  Batch 1: {batch1:,.2f} USDT")
print(f"  BTC: ~${btc_budget:,.2f}")
print(f"  ETH: ~${eth_budget:,.2f}")
print(f"  SOL: ~${sol_budget:,.2f}")

print(f"\n=== Executing Orders ===")

# Try using quote currency mode (sz = USDT amount)
orders = [
    ("BTC-USDT", str(round(btc_budget, 2))),
    ("ETH-USDT", str(round(eth_budget, 2))),
    ("SOL-USDT", str(round(sol_budget, 2))),
]

results = []
for inst_id, sz_usdt in orders:
    r = trade_api.place_order(
        instId=inst_id,
        tdMode="cash",
        side="buy",
        ordType="market",
        sz=sz_usdt,
        tgtCcy="quote_ccy",  # size in quote currency (USDT)
    )
    success = r.get("code") == "0"
    ord_id = r["data"][0].get("ordId", "") if r.get("data") else ""
    msg = r["data"][0].get("sMsg", "") if r.get("data") else r.get("msg", "")
    status = "OK" if success else "FAIL"
    print(f"  {inst_id}: {status} | ordId={ord_id} | {msg}")
    results.append({"inst": inst_id, "success": success, "ordId": ord_id, "response": r})

# Verify fills
print(f"\n=== Order Details ===")
for res in results:
    if res["success"] and res["ordId"]:
        detail = trade_api.get_order(instId=res["inst"], ordId=res["ordId"])
        if detail and detail.get("code") == "0" and detail["data"]:
            d = detail["data"][0]
            print(f"  {res['inst']}: filled {d.get('accFillSz')} @ avg ${d.get('avgPx')} | fee={d.get('fee')} {d.get('feeCcy')}")

# Final balance
print(f"\n=== Post-Trade Balances ===")
bal_resp = account_api.get_account_balance()
if bal_resp and bal_resp.get("code") == "0":
    for d in bal_resp["data"][0].get("details", []):
        avail = float(d.get("availBal", 0))
        if avail > 0:
            print(f"  {d['ccy']}: {d['availBal']}")
