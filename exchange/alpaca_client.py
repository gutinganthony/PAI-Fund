"""
Alpaca Paper Trading Client
Handles all interactions with Alpaca's paper trading API for US stocks.
"""

import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def _load_config():
    """Load API credentials from .env file."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    config = {}
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
    return config


def _request(method, path, body=None, base_url=None):
    """Make authenticated request to Alpaca API."""
    config = _load_config()
    api_key = config.get("ALPACA_API_KEY", "")
    secret_key = config.get("ALPACA_SECRET_KEY", "")
    if base_url is None:
        base_url = config.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets/v2")

    url = base_url + path
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": secret_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    req = Request(url, method=method, headers=headers)
    if body:
        req.data = json.dumps(body).encode("utf-8")

    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        return {"error": True, "code": e.code, "message": error_body}


def _market_request(method, path):
    """Make request to Alpaca Market Data API."""
    return _request(method, path, base_url="https://data.alpaca.markets/v2")


# ─── Account ───────────────────────────────────────────────

def get_account():
    """Get account info (equity, cash, buying power)."""
    return _request("GET", "/account")


def get_positions():
    """Get all open positions."""
    return _request("GET", "/positions")


def get_position(symbol):
    """Get position for a specific symbol."""
    return _request("GET", f"/positions/{symbol}")


# ─── Market Data ───────────────────────────────────────────

def get_quote(symbol):
    """Get latest quote for a symbol."""
    return _market_request("GET", f"/stocks/{symbol}/quotes/latest")


def get_bars(symbol, timeframe="1Day", limit=100):
    """Get historical bars.
    timeframe: 1Min, 5Min, 15Min, 1Hour, 1Day, 1Week, 1Month
    """
    return _market_request("GET", f"/stocks/{symbol}/bars?timeframe={timeframe}&limit={limit}")


def get_snapshot(symbol):
    """Get latest snapshot (quote + bar + trade) for a symbol."""
    return _market_request("GET", f"/stocks/{symbol}/snapshot")


# ─── Trading ───────────────────────────────────────────────

def place_order(symbol, qty, side, order_type="market", time_in_force="day",
                limit_price=None, stop_price=None):
    """Place an order.
    symbol: e.g. 'AAPL'
    qty: number of shares (or notional for fractional)
    side: 'buy' or 'sell'
    order_type: 'market', 'limit', 'stop', 'stop_limit'
    time_in_force: 'day', 'gtc', 'ioc', 'fok'
    """
    body = {
        "symbol": symbol,
        "qty": str(qty),
        "side": side,
        "type": order_type,
        "time_in_force": time_in_force,
    }
    if limit_price and order_type in ("limit", "stop_limit"):
        body["limit_price"] = str(limit_price)
    if stop_price and order_type in ("stop", "stop_limit"):
        body["stop_price"] = str(stop_price)
    return _request("POST", "/orders", body=body)


def place_bracket_order(symbol, qty, side, take_profit_price, stop_loss_price,
                        order_type="market", time_in_force="day"):
    """Place a bracket order (entry + take profit + stop loss)."""
    body = {
        "symbol": symbol,
        "qty": str(qty),
        "side": side,
        "type": order_type,
        "time_in_force": time_in_force,
        "order_class": "bracket",
        "take_profit": {"limit_price": str(take_profit_price)},
        "stop_loss": {"stop_price": str(stop_loss_price)},
    }
    return _request("POST", "/orders", body=body)


def cancel_order(order_id):
    """Cancel an order."""
    return _request("DELETE", f"/orders/{order_id}")


def cancel_all_orders():
    """Cancel all open orders."""
    return _request("DELETE", "/orders")


def get_orders(status="open", limit=50):
    """Get orders by status: open, closed, all."""
    return _request("GET", f"/orders?status={status}&limit={limit}")


def get_order(order_id):
    """Get a specific order by ID."""
    return _request("GET", f"/orders/{order_id}")


# ─── Portfolio History ─────────────────────────────────────

def get_portfolio_history(period="1M", timeframe="1D"):
    """Get portfolio value history.
    period: 1D, 1W, 1M, 3M, 1A, all
    timeframe: 1Min, 5Min, 15Min, 1H, 1D
    """
    return _request("GET", f"/account/portfolio/history?period={period}&timeframe={timeframe}")


# ─── Quick Test ────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Alpaca Paper Trading Client Test ===\n")

    # Test 1: Account
    print("1. Account info...")
    acct = get_account()
    if not acct.get("error"):
        print(f"   Status: {acct.get('status')}")
        print(f"   Equity: ${acct.get('equity')}")
        print(f"   Cash: ${acct.get('cash')}")
        print(f"   Buying Power: ${acct.get('buying_power')}")
    else:
        print(f"   Error: {acct}")

    # Test 2: Quote
    print("\n2. AAPL quote...")
    quote = get_quote("AAPL")
    if not quote.get("error"):
        q = quote.get("quote", quote)
        print(f"   Ask: ${q.get('ap')}  Bid: ${q.get('bp')}")
    else:
        print(f"   Error: {quote}")

    # Test 3: Positions
    print("\n3. Open positions...")
    positions = get_positions()
    if isinstance(positions, list):
        if positions:
            for p in positions:
                print(f"   {p['symbol']}: {p['qty']} shares @ ${p['avg_entry_price']}")
        else:
            print("   No open positions (clean slate)")
    else:
        print(f"   Error: {positions}")

    print("\n=== Test Complete ===")
