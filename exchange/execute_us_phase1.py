"""Execute US Phase 1: Leopold AI Energy Layer (CEG + VST) on Alpaca Paper."""
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

from urllib.request import Request, urlopen
import json

base_url = config["ALPACA_BASE_URL"]
headers = {
    "APCA-API-KEY-ID": config["ALPACA_API_KEY"],
    "APCA-API-SECRET-KEY": config["ALPACA_SECRET_KEY"],
    "Content-Type": "application/json",
}

def alpaca_post(path, body):
    req = Request(f"{base_url}{path}", method="POST", headers=headers)
    req.data = json.dumps(body).encode()
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def alpaca_get(path):
    req = Request(f"{base_url}{path}", headers=headers)
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

# Check account
acct = alpaca_get("/account")
print(f"Account: {acct.get('status')} | Cash: ${acct.get('cash')} | Equity: ${acct.get('equity')}")

# Strategy: Leopold AI Energy Layer
# Using "notional" for dollar-amount orders
trades = [
    {"symbol": "CEG", "notional": "3000", "reason": "Leopold L0-Energy: Nuclear AI power, -33% from high, RSI=38.5"},
    {"symbol": "VST", "notional": "2000", "reason": "Leopold L0-Energy: Power company, -30% from high, RSI=44.4"},
]

print(f"\n=== Executing Leopold AI Energy Layer ===")
for t in trades:
    body = {
        "symbol": t["symbol"],
        "notional": t["notional"],
        "side": "buy",
        "type": "market",
        "time_in_force": "day",
    }
    result = alpaca_post("/orders", body)
    
    if "error" not in result and result.get("id"):
        print(f"\n  {t['symbol']}: ORDER PLACED")
        print(f"    Order ID: {result['id']}")
        print(f"    Status: {result.get('status')}")
        print(f"    Notional: ${t['notional']}")
        print(f"    Reason: {t['reason']}")
        
        # Record to journal
        from journal.trade_journal import init_db, record_entry
        init_db()
        # Approximate price from our scan
        approx_prices = {"CEG": 275.16, "VST": 151.59}
        px = approx_prices.get(t["symbol"], 0)
        qty = float(t["notional"]) / px if px > 0 else 0
        stop_loss = px * 0.85  # -15%
        
        trade_id = record_entry(
            strategy="Leopold-AI-Energy",
            platform="Alpaca-paper",
            symbol=t["symbol"],
            side="buy",
            quantity=round(qty, 4),
            entry_price=px,
            stop_loss=round(stop_loss, 2),
            entry_reason=t["reason"],
            market_context=f"VIX=25.1, SPY RSI=48.5, market in correction not panic, AI energy demand certain",
            order_id=result["id"],
        )
        print(f"    Journal ID: {trade_id}")
    else:
        print(f"\n  {t['symbol']}: FAILED — {result}")

# Check positions
print(f"\n=== Current Positions ===")
positions = alpaca_get("/positions")
if isinstance(positions, list):
    for p in positions:
        print(f"  {p['symbol']}: {p['qty']} shares @ ${p['avg_entry_price']} | MV: ${p['market_value']} | P&L: ${p['unrealized_pl']}")
else:
    print(f"  {positions}")

# Updated account
acct = alpaca_get("/account")
print(f"\nAccount: Cash=${acct.get('cash')} | Equity=${acct.get('equity')}")
