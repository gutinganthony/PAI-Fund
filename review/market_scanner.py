"""
Market Temperature Scanner
Calculates market temperature based on Kostolany + Howard Marks framework.
Fetches real-time fear/greed, VIX, RSI, and other sentiment indicators.
"""

import json
import os
import sys
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Add parent to path for journal import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def fetch_json(url, headers=None):
    """Fetch JSON from URL."""
    h = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    if headers:
        h.update(headers)
    try:
        req = Request(url, headers=h)
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


# ─── Data Fetchers ─────────────────────────────────────────

def get_crypto_fear_greed():
    """Fetch Crypto Fear & Greed Index (0-100)."""
    data = fetch_json("https://api.alternative.me/fng/?limit=1")
    if "data" in data and data["data"]:
        val = int(data["data"][0]["value"])
        label = data["data"][0]["value_classification"]
        return {"value": val, "label": label}
    return {"value": None, "label": "unavailable"}


def get_btc_price_and_rsi():
    """Get BTC price and calculate RSI from OKX public API."""
    data = fetch_json("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1D&limit=15")
    if data.get("code") != "0" or not data.get("data"):
        return {"price": None, "rsi": None}

    closes = [float(c[4]) for c in reversed(data["data"])]  # OKX: [ts, o, h, l, c, vol, ...]
    price = closes[-1]

    # Calculate RSI(14)
    if len(closes) < 15:
        return {"price": price, "rsi": None}

    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains[:14]) / 14
    avg_loss = sum(losses[:14]) / 14

    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    return {"price": round(price, 2), "rsi": round(rsi, 1)}


def get_spy_data():
    """Get SPY price data from Alpaca."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    config = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip()

    headers = {
        "APCA-API-KEY-ID": config.get("ALPACA_API_KEY", ""),
        "APCA-API-SECRET-KEY": config.get("ALPACA_SECRET_KEY", ""),
    }

    # Get SPY bars for RSI calc
    bars = fetch_json(
        "https://data.alpaca.markets/v2/stocks/SPY/bars?timeframe=1Day&limit=15",
        headers=headers
    )

    if "bars" not in bars or not bars["bars"]:
        return {"price": None, "rsi": None}

    closes = [b["c"] for b in bars["bars"]]
    price = closes[-1]

    if len(closes) < 15:
        return {"price": price, "rsi": None}

    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains[:14]) / 14
    avg_loss = sum(losses[:14]) / 14

    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    return {"price": round(price, 2), "rsi": round(rsi, 1)}


def get_vix():
    """Get VIX from Alpaca."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    config = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip()

    headers = {
        "APCA-API-KEY-ID": config.get("ALPACA_API_KEY", ""),
        "APCA-API-SECRET-KEY": config.get("ALPACA_SECRET_KEY", ""),
    }

    # Try VIXY (VIX ETF) as proxy since VIX index itself may not be available
    quote = fetch_json(
        "https://data.alpaca.markets/v2/stocks/VIXY/quotes/latest",
        headers=headers
    )
    if "quote" in quote:
        mid = (quote["quote"].get("ap", 0) + quote["quote"].get("bp", 0)) / 2
        return {"vixy": round(mid, 2), "source": "VIXY"}

    return {"vixy": None, "source": "unavailable"}


# ─── Temperature Calculator ───────────────────────────────

def normalize_vix_to_temp(vix_proxy):
    """Convert VIX-proxy to temperature (higher = more complacent/hot)."""
    # VIXY moves with VIX. Lower VIXY = lower VIX = more complacent = hotter
    # This is a rough proxy; in production, use actual VIX
    if vix_proxy is None:
        return 50  # neutral default
    # VIXY typically ranges 10-80+
    if vix_proxy < 15:
        return 85  # very complacent
    elif vix_proxy < 20:
        return 70
    elif vix_proxy < 30:
        return 50
    elif vix_proxy < 45:
        return 30
    else:
        return 10  # extreme fear


def normalize_rsi_to_temp(rsi):
    """Convert RSI to temperature component."""
    if rsi is None:
        return 50
    return rsi  # RSI is already 0-100 scale


def calculate_crypto_temperature(crypto_fg, btc_rsi):
    """Calculate crypto market temperature (0=extreme fear, 100=extreme greed)."""
    cfg_val = crypto_fg["value"] if crypto_fg["value"] is not None else 50
    rsi_val = normalize_rsi_to_temp(btc_rsi)

    temp = cfg_val * 0.60 + rsi_val * 0.40
    return round(temp, 1)


def calculate_us_temperature(vix_data, spy_rsi, crypto_fg_as_proxy=None):
    """Calculate US stock market temperature."""
    vix_temp = normalize_vix_to_temp(vix_data.get("vixy"))
    rsi_temp = normalize_rsi_to_temp(spy_rsi)

    temp = vix_temp * 0.45 + rsi_temp * 0.55
    return round(temp, 1)


def temp_to_action(temp):
    """Convert temperature to suggested action."""
    if temp < 20:
        return "🟢 AGGRESSIVE BUY — 極度恐慌，積極買入 (倉位 80-90%)"
    elif temp < 40:
        return "🟢 BUY — 偏冷，逐步加倉 (倉位 60-70%)"
    elif temp < 60:
        return "🟡 HOLD — 中性，維持現有倉位 (倉位 40-50%)"
    elif temp < 80:
        return "🟠 REDUCE — 偏熱，逐步減倉 (倉位 20-30%)"
    else:
        return "🔴 DEFENSIVE — 極度貪婪，防守模式 (倉位 0-10%)"


def scan_market():
    """Run full market temperature scan."""
    print("=" * 60)
    print(f"  MARKET TEMPERATURE SCAN")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # Fetch data
    print("\nFetching data...")
    crypto_fg = get_crypto_fear_greed()
    btc_data = get_btc_price_and_rsi()
    spy_data = get_spy_data()
    vix_data = get_vix()

    # Calculate temperatures
    crypto_temp = calculate_crypto_temperature(crypto_fg, btc_data["rsi"])
    us_temp = calculate_us_temperature(vix_data, spy_data["rsi"])

    # Display results
    print(f"\n{'─' * 60}")
    print(f"  📊 CRYPTO MARKET")
    print(f"{'─' * 60}")
    print(f"  BTC Price:           ${btc_data['price']:,.2f}" if btc_data['price'] else "  BTC Price:           N/A")
    print(f"  BTC RSI(14):         {btc_data['rsi']}" if btc_data['rsi'] else "  BTC RSI(14):         N/A")
    print(f"  Fear & Greed Index:  {crypto_fg['value']} ({crypto_fg['label']})")
    print(f"  🌡️  CRYPTO TEMPERATURE: {crypto_temp}")
    print(f"  📋 Action: {temp_to_action(crypto_temp)}")

    print(f"\n{'─' * 60}")
    print(f"  📊 US STOCK MARKET")
    print(f"{'─' * 60}")
    print(f"  SPY Price:           ${spy_data['price']:,.2f}" if spy_data['price'] else "  SPY Price:           N/A")
    print(f"  SPY RSI(14):         {spy_data['rsi']}" if spy_data['rsi'] else "  SPY RSI(14):         N/A")
    print(f"  VIXY (VIX proxy):    ${vix_data.get('vixy', 'N/A')}")
    print(f"  🌡️  US TEMPERATURE:    {us_temp}")
    print(f"  📋 Action: {temp_to_action(us_temp)}")

    print(f"\n{'─' * 60}")
    print(f"  📊 COMBINED OVERVIEW")
    print(f"{'─' * 60}")
    combined = round(crypto_temp * 0.4 + us_temp * 0.6, 1)
    print(f"  🌡️  OVERALL TEMPERATURE: {combined}")
    print(f"  📋 Action: {temp_to_action(combined)}")
    print(f"\n{'=' * 60}")

    # Store in journal
    try:
        from journal.trade_journal import record_temperature, init_db
        init_db()
        record_temperature(
            market="crypto",
            temperature=crypto_temp,
            crypto_fg=crypto_fg["value"],
            rsi_btc=btc_data["rsi"],
            components=json.dumps({"fear_greed": crypto_fg, "btc": btc_data}),
            action=temp_to_action(crypto_temp),
        )
        record_temperature(
            market="us_stocks",
            temperature=us_temp,
            rsi_spy=spy_data["rsi"],
            components=json.dumps({"vix": vix_data, "spy": spy_data}),
            action=temp_to_action(us_temp),
        )
        print("\n✅ Temperature recorded to journal database.")
    except Exception as e:
        print(f"\n⚠️ Could not save to journal: {e}")

    return {
        "crypto": {"temperature": crypto_temp, "btc_price": btc_data["price"], "fear_greed": crypto_fg},
        "us": {"temperature": us_temp, "spy_price": spy_data["price"]},
        "combined": combined,
    }


if __name__ == "__main__":
    scan_market()
