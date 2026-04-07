"""Execute trades on OKX Demo."""
import os
import sys
import json

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

flag = "1"  # demo
account_api = Account.AccountAPI(config["OKX_API_KEY"], config["OKX_SECRET_KEY"], config["OKX_PASSPHRASE"], flag=flag, debug=False)
market_api = MarketData.MarketAPI(flag=flag)
trade_api = Trade.TradeAPI(config["OKX_API_KEY"], config["OKX_SECRET_KEY"], config["OKX_PASSPHRASE"], flag=flag, debug=False)


def get_prices():
    """Get current prices for key assets."""
    symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
    results = {}
    for s in symbols:
        ticker = market_api.get_ticker(instId=s)
        if ticker and ticker.get("code") == "0" and ticker["data"]:
            t = ticker["data"][0]
            results[s] = {
                "last": float(t["last"]),
                "high24h": float(t["high24h"]),
                "low24h": float(t["low24h"]),
                "vol24h": t.get("vol24h", "0"),
            }
    return results


def get_balance():
    """Get USDT balance."""
    bal = account_api.get_account_balance()
    if bal and bal.get("code") == "0":
        for d in bal["data"][0].get("details", []):
            if d["ccy"] == "USDT":
                return float(d.get("availBal", 0))
    return 0


def place_market_buy(inst_id, size):
    """Place market buy order."""
    result = trade_api.place_order(
        instId=inst_id,
        tdMode="cash",
        side="buy",
        ordType="market",
        sz=str(size),
    )
    return result


def place_market_sell(inst_id, size):
    """Place market sell order."""
    result = trade_api.place_order(
        instId=inst_id,
        tdMode="cash",
        side="sell",
        ordType="market",
        sz=str(size),
    )
    return result


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    
    print("=== Current Prices ===")
    prices = get_prices()
    for sym, data in prices.items():
        print(f"  {sym}: ${data['last']:,.2f}  (24h: ${data['low24h']:,.2f} - ${data['high24h']:,.2f})")
    
    print(f"\n=== USDT Balance ===")
    bal = get_balance()
    print(f"  Available: {bal:,.2f} USDT")
    
    # S4 Panic Rebound - Batch 1 (30% of strategy allocation)
    # Strategy S4 gets 20% of total capital = 83,082 * 0.20 = ~16,616 USDT
    # Batch 1 = 30% of strategy allocation = ~4,985 USDT
    # Split: BTC 60%, ETH 30%, SOL 10%
    
    s4_allocation = bal * 0.20  # 20% of total for S4
    batch1 = s4_allocation * 0.30  # 30% first batch
    
    btc_budget = batch1 * 0.60
    eth_budget = batch1 * 0.30
    sol_budget = batch1 * 0.10
    
    btc_price = prices["BTC-USDT"]["last"]
    eth_price = prices["ETH-USDT"]["last"]
    sol_price = prices["SOL-USDT"]["last"]
    
    # Calculate quantities (OKX spot uses base currency size)
    # BTC min size = 0.00001, ETH min = 0.001, SOL min = 0.01
    btc_qty = round(btc_budget / btc_price, 5)
    eth_qty = round(eth_budget / eth_price, 4)
    sol_qty = round(sol_budget / sol_price, 2)
    
    print(f"\n=== S4 Panic Rebound - Batch 1 Plan ===")
    print(f"  S4 Total Allocation: {s4_allocation:,.2f} USDT ({s4_allocation/bal*100:.0f}% of capital)")
    print(f"  Batch 1 (30%): {batch1:,.2f} USDT")
    print(f"  BTC: {btc_qty} BTC (~${btc_budget:,.2f})")
    print(f"  ETH: {eth_qty} ETH (~${eth_budget:,.2f})")
    print(f"  SOL: {sol_qty} SOL (~${sol_budget:,.2f})")
    
    # Execute
    print(f"\n=== Executing Orders ===")
    
    # BTC
    r = place_market_buy("BTC-USDT", btc_qty)
    print(f"  BTC: {json.dumps(r)}")
    
    # ETH
    r = place_market_buy("ETH-USDT", eth_qty)
    print(f"  ETH: {json.dumps(r)}")
    
    # SOL
    r = place_market_buy("SOL-USDT", sol_qty)
    print(f"  SOL: {json.dumps(r)}")
    
    # Check new balance
    print(f"\n=== Post-Trade Balance ===")
    new_bal = get_balance()
    print(f"  USDT: {new_bal:,.2f}")
    
    # Show all balances
    bal_full = account_api.get_account_balance()
    if bal_full and bal_full.get("code") == "0":
        for d in bal_full["data"][0].get("details", []):
            avail = float(d.get("availBal", 0))
            if avail > 0:
                print(f"  {d['ccy']}: {d['availBal']}")
