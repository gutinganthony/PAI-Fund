"""
Dashboard Data Generator
Generates data.json for the live dashboard page.
"""
import os, sys, json, warnings
sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime
import yfinance as yf

def load_env():
    config = {}
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()
    return config

def fetch_okx_positions(config):
    try:
        from okx import Account
        api = Account.AccountAPI(config["OKX_API_KEY"], config["OKX_SECRET_KEY"],
                                  config["OKX_PASSPHRASE"], flag="1", debug=False)
        bal = api.get_account_balance()
        positions = []
        if bal and bal.get("code") == "0":
            for d in bal["data"][0].get("details", []):
                avail = float(d.get("availBal", 0))
                if avail > 0.001 and d["ccy"] != "USDT":
                    positions.append({
                        "symbol": d["ccy"],
                        "quantity": avail,
                        "platform": "OKX Demo",
                    })
            usdt = next((float(d.get("availBal", 0)) for d in bal["data"][0].get("details", []) if d["ccy"] == "USDT"), 0)
        return positions, usdt
    except Exception as e:
        return [], 0

def fetch_alpaca_positions(config):
    from urllib.request import Request, urlopen
    try:
        base = config.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets/v2")
        headers = {
            "APCA-API-KEY-ID": config.get("ALPACA_API_KEY", ""),
            "APCA-API-SECRET-KEY": config.get("ALPACA_SECRET_KEY", ""),
        }
        req = Request(f"{base}/positions", headers=headers)
        with urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode())
        positions = []
        for p in raw:
            positions.append({
                "symbol": p["symbol"],
                "quantity": float(p["qty"]),
                "avg_entry": float(p["avg_entry_price"]),
                "current_price": float(p["current_price"]),
                "market_value": float(p["market_value"]),
                "unrealized_pnl": float(p["unrealized_pl"]),
                "unrealized_pnl_pct": float(p["unrealized_plpc"]) * 100,
                "platform": "Alpaca Paper",
            })
        req2 = Request(f"{base}/account", headers=headers)
        with urlopen(req2, timeout=10) as resp2:
            acct = json.loads(resp2.read().decode())
        return positions, float(acct["equity"]), float(acct["cash"])
    except Exception as e:
        return [], 0, 0

def fetch_crypto_prices():
    try:
        tickers = {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD"}
        prices = {}
        for name, sym in tickers.items():
            t = yf.Ticker(sym)
            h = t.history(period="5d")
            if not h.empty:
                prices[name] = round(h["Close"].iloc[-1], 2)
        return prices
    except:
        return {}

def fetch_market_data():
    data = {}
    for sym, name in [("^GSPC", "SPY"), ("^VIX", "VIX")]:
        try:
            t = yf.Ticker(sym)
            h = t.history(period="5d")
            if not h.empty:
                data[name] = round(h["Close"].iloc[-1], 2)
        except:
            pass
    # Fear & Greed
    try:
        from urllib.request import urlopen
        resp = urlopen("https://api.alternative.me/fng/?limit=1", timeout=10)
        fg = json.loads(resp.read().decode())
        data["crypto_fear_greed"] = int(fg["data"][0]["value"])
        data["crypto_fear_greed_label"] = fg["data"][0]["value_classification"]
    except:
        pass
    return data

def main():
    config = load_env()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Fetch all data
    okx_positions, usdt_cash = fetch_okx_positions(config)
    alpaca_positions, alpaca_equity, alpaca_cash = fetch_alpaca_positions(config)
    crypto_prices = fetch_crypto_prices()
    market = fetch_market_data()
    
    # Enrich OKX positions with prices
    entry_prices = {"BTC": 67975, "ETH": 2036.88, "SOL": 79.84}
    strategies = {"BTC": "S4-panic-rebound", "ETH": "S4-panic-rebound", "SOL": "S4-panic-rebound"}
    for p in okx_positions:
        sym = p["symbol"]
        cur = crypto_prices.get(sym, 0)
        entry = entry_prices.get(sym, 0)
        p["current_price"] = cur
        p["avg_entry"] = entry
        p["market_value"] = round(cur * p["quantity"], 2)
        p["unrealized_pnl"] = round((cur - entry) * p["quantity"], 2)
        p["unrealized_pnl_pct"] = round((cur / entry - 1) * 100, 2) if entry else 0
        p["strategy"] = strategies.get(sym, "unknown")
    
    # Add strategy to alpaca
    alpaca_strategies = {"CEG": "Leopold-AI-Energy", "VST": "Leopold-AI-Energy", "MSFT": "S2-value-undervalued"}
    for p in alpaca_positions:
        p["strategy"] = alpaca_strategies.get(p["symbol"], "unknown")
    
    # Total portfolio value
    crypto_total = sum(p["market_value"] for p in okx_positions) + usdt_cash
    total_value = crypto_total + alpaca_equity
    total_invested = sum(p["avg_entry"] * p["quantity"] for p in okx_positions) + sum(p["avg_entry"] * p["quantity"] for p in alpaca_positions)
    total_pnl = sum(p["unrealized_pnl"] for p in okx_positions) + sum(p["unrealized_pnl"] for p in alpaca_positions)
    
    # Build strategies summary
    strat_map = {}
    for p in okx_positions + alpaca_positions:
        s = p.get("strategy", "unknown")
        if s not in strat_map:
            strat_map[s] = {"positions": [], "total_value": 0, "total_pnl": 0}
        strat_map[s]["positions"].append(p["symbol"])
        strat_map[s]["total_value"] += p.get("market_value", 0)
        strat_map[s]["total_pnl"] += p.get("unrealized_pnl", 0)
    
    dashboard = {
        "updated_at": now,
        "portfolio": {
            "total_value": round(total_value, 2),
            "total_invested": round(total_invested, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl / total_invested * 100, 2) if total_invested else 0,
            "cash": {
                "okx_usdt": round(usdt_cash, 2),
                "alpaca_usd": round(alpaca_cash, 2),
                "total_cash": round(usdt_cash + alpaca_cash, 2),
            },
            "allocation_pct": round(total_invested / total_value * 100, 1) if total_value else 0,
        },
        "positions": {
            "crypto": okx_positions,
            "us_stocks": alpaca_positions,
        },
        "strategies": strat_map,
        "market": {
            "spy": market.get("SPY"),
            "vix": market.get("VIX"),
            "crypto_fear_greed": market.get("crypto_fear_greed"),
            "crypto_fear_greed_label": market.get("crypto_fear_greed_label"),
            "btc": crypto_prices.get("BTC"),
            "eth": crypto_prices.get("ETH"),
            "sol": crypto_prices.get("SOL"),
        },
    }
    
    out_path = os.path.join(os.path.dirname(__file__), "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)
    
    print(f"Dashboard data generated: {out_path}")
    print(json.dumps(dashboard, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
