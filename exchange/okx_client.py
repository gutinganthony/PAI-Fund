"""
OKX Demo Trading Client
Handles all interactions with OKX's demo trading API.
"""

import hmac
import hashlib
import base64
import json
import time
import os
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode

# Demo trading base URL
BASE_URL = "https://www.okx.com"
DEMO_FLAG = "1"  # 1 = demo trading


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


def _get_timestamp():
    """Get ISO 8601 timestamp for OKX API."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _sign(timestamp, method, path, body="", secret_key=""):
    """Create HMAC SHA256 signature for OKX API."""
    message = timestamp + method.upper() + path + (body if body else "")
    mac = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    )
    return base64.b64encode(mac.digest()).decode("utf-8")


def _request(method, path, body=None, params=None):
    """Make authenticated request to OKX API."""
    config = _load_config()
    api_key = config.get("OKX_API_KEY", "")
    secret_key = config.get("OKX_SECRET_KEY", "")
    passphrase = config.get("OKX_PASSPHRASE", "")

    if params:
        path = path + "?" + urlencode(params)

    timestamp = _get_timestamp()
    body_str = json.dumps(body) if body else ""
    signature = _sign(timestamp, method, path, body_str, secret_key)

    url = BASE_URL + path
    headers = {
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "x-simulated-trading": DEMO_FLAG,
        "Content-Type": "application/json",
    }

    req = Request(url, method=method, headers=headers)
    if body_str and method in ("POST",):
        req.data = body_str.encode("utf-8")

    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        return {"error": True, "code": e.code, "message": error_body}


# ─── Account ───────────────────────────────────────────────

def get_balance(ccy=None):
    """Get account balance. ccy: e.g. 'USDT' or None for all."""
    params = {}
    if ccy:
        params["ccy"] = ccy
    return _request("GET", "/api/v5/account/balance", params=params)


def get_positions(inst_type=None):
    """Get current positions."""
    params = {}
    if inst_type:
        params["instType"] = inst_type
    return _request("GET", "/api/v5/account/positions", params=params)


# ─── Market Data ───────────────────────────────────────────

def get_ticker(inst_id):
    """Get ticker for an instrument. e.g. 'BTC-USDT'"""
    return _request("GET", "/api/v5/market/ticker", params={"instId": inst_id})


def get_candles(inst_id, bar="1D", limit=100):
    """Get candlestick data.
    bar: 1m/5m/15m/1H/4H/1D/1W/1M
    """
    params = {"instId": inst_id, "bar": bar, "limit": str(limit)}
    return _request("GET", "/api/v5/market/candles", params=params)


def get_orderbook(inst_id, sz=5):
    """Get order book."""
    return _request("GET", "/api/v5/market/books", params={"instId": inst_id, "sz": str(sz)})


# ─── Trading ───────────────────────────────────────────────

def place_order(inst_id, side, sz, ord_type="market", px=None, td_mode="cash"):
    """Place an order.
    inst_id: e.g. 'BTC-USDT'
    side: 'buy' or 'sell'
    sz: size (quantity)
    ord_type: 'market', 'limit', 'post_only'
    px: price (required for limit orders)
    td_mode: 'cash' (spot), 'cross', 'isolated'
    """
    body = {
        "instId": inst_id,
        "tdMode": td_mode,
        "side": side,
        "ordType": ord_type,
        "sz": str(sz),
    }
    if px and ord_type != "market":
        body["px"] = str(px)
    return _request("POST", "/api/v5/trade/order", body=body)


def cancel_order(inst_id, ord_id):
    """Cancel an order."""
    return _request("POST", "/api/v5/trade/cancel-order", body={
        "instId": inst_id,
        "ordId": ord_id,
    })


def get_order(inst_id, ord_id):
    """Get order details."""
    return _request("GET", "/api/v5/trade/order", params={
        "instId": inst_id,
        "ordId": ord_id,
    })


def get_open_orders(inst_type=None):
    """Get all open orders."""
    params = {}
    if inst_type:
        params["instType"] = inst_type
    return _request("GET", "/api/v5/trade/orders-pending", params=params)


def get_order_history(inst_type="SPOT", limit=20):
    """Get recent order history."""
    return _request("GET", "/api/v5/trade/orders-history-archive", params={
        "instType": inst_type,
        "limit": str(limit),
    })


# ─── Algo Orders (Stop Loss / Take Profit) ─────────────────

def place_stop_loss(inst_id, side, sz, sl_trigger_px, sl_ord_px="-1", td_mode="cash"):
    """Place a stop-loss order.
    sl_ord_px: '-1' for market price execution.
    """
    body = {
        "instId": inst_id,
        "tdMode": td_mode,
        "side": side,
        "ordType": "conditional",
        "sz": str(sz),
        "slTriggerPx": str(sl_trigger_px),
        "slOrdPx": str(sl_ord_px),
    }
    return _request("POST", "/api/v5/trade/order-algo", body=body)


# ─── Quick Test ────────────────────────────────────────────

if __name__ == "__main__":
    print("=== OKX Demo Trading Client Test ===\n")

    # Test 1: Get balance
    print("1. Fetching balance...")
    result = get_balance()
    if "data" in result and result["data"]:
        for detail in result["data"][0].get("details", []):
            ccy = detail.get("ccy", "")
            avail = detail.get("availBal", "0")
            if float(avail) > 0:
                print(f"   {ccy}: {avail}")
    else:
        print(f"   Error: {result}")

    # Test 2: Get BTC ticker
    print("\n2. BTC-USDT ticker...")
    ticker = get_ticker("BTC-USDT")
    if "data" in ticker and ticker["data"]:
        t = ticker["data"][0]
        print(f"   Last: {t.get('last')}  24h High: {t.get('high24h')}  24h Low: {t.get('low24h')}")
    else:
        print(f"   Error: {ticker}")

    print("\n=== Test Complete ===")
