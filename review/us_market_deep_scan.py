"""
Deep US Market Analysis
Fetches current data for key US stocks/ETFs and evaluates strategy signals.
"""
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
config = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            config[key.strip()] = val.strip()

from urllib.request import Request, urlopen
from urllib.error import HTTPError

def alpaca_get(path):
    headers = {
        "APCA-API-KEY-ID": config["ALPACA_API_KEY"],
        "APCA-API-SECRET-KEY": config["ALPACA_SECRET_KEY"],
        "Accept": "application/json",
    }
    try:
        req = Request(f"https://data.alpaca.markets/v2{path}", headers=headers)
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        return {"error": e.code, "msg": e.read().decode()[:200]}
    except Exception as e:
        return {"error": str(e)}

def get_bars(symbol, timeframe="1Day", limit=50):
    return alpaca_get(f"/stocks/{symbol}/bars?timeframe={timeframe}&limit={limit}&feed=iex")

def get_latest_quote(symbol):
    return alpaca_get(f"/stocks/{symbol}/quotes/latest?feed=iex")

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)

def calc_sma(closes, period):
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 2)

def calc_ema(closes, period):
    if len(closes) < period:
        return None
    ema = sum(closes[:period]) / period
    mult = 2 / (period + 1)
    for c in closes[period:]:
        ema = (c - ema) * mult + ema
    return round(ema, 2)

def analyze_symbol(symbol, bars_data):
    if "bars" not in bars_data or not bars_data["bars"]:
        return {"symbol": symbol, "error": "no data"}
    
    bars = bars_data["bars"]
    closes = [b["c"] for b in bars]
    highs = [b["h"] for b in bars]
    lows = [b["l"] for b in bars]
    volumes = [b["v"] for b in bars]
    
    price = closes[-1]
    high_52w = max(highs) if len(highs) >= 50 else max(highs)
    low_52w = min(lows) if len(lows) >= 50 else min(lows)
    
    sma_20 = calc_sma(closes, 20)
    sma_50 = calc_sma(closes, min(50, len(closes)))
    ema_21 = calc_ema(closes, 21)
    rsi = calc_rsi(closes)
    avg_vol = sum(volumes[-20:]) / min(20, len(volumes)) if volumes else 0
    
    # Distance from 52w high/low
    dist_high = round((price - high_52w) / high_52w * 100, 1) if high_52w else 0
    dist_low = round((price - low_52w) / low_52w * 100, 1) if low_52w else 0
    
    # Trend: price vs moving averages
    above_20 = price > sma_20 if sma_20 else None
    above_50 = price > sma_50 if sma_50 else None
    
    return {
        "symbol": symbol,
        "price": price,
        "rsi14": rsi,
        "sma20": sma_20,
        "sma50": sma_50,
        "ema21": ema_21,
        "above_20ma": above_20,
        "above_50ma": above_50,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "dist_from_high": dist_high,
        "dist_from_low": dist_low,
        "avg_volume_20d": int(avg_vol),
        "last_volume": volumes[-1] if volumes else 0,
    }


# ─── Main Analysis ─────────────────────────────────────────

# Key symbols to analyze
symbols = {
    # Major indices ETFs
    "SPY": "S&P 500",
    "QQQ": "NASDAQ 100",
    "IWM": "Russell 2000",
    # VIX proxy
    "VIXY": "VIX Short-Term",
    # AI supply chain (Leopold framework)
    "NVDA": "NVIDIA",
    "AVGO": "Broadcom",
    "AMD": "AMD",
    "SMCI": "Super Micro",
    # Mag 7
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Google",
    "AMZN": "Amazon",
    "META": "Meta",
    "TSLA": "Tesla",
    # Energy / Power (AI infra Layer 0)
    "CEG": "Constellation Energy",
    "VST": "Vistra Energy",
    # Value plays (Buffett/Lynch/段永平)
    "BRK.B": "Berkshire",
    "COST": "Costco",
}

print("=" * 80)
print("  US MARKET DEEP ANALYSIS")
print("=" * 80)

results = []
for sym, name in symbols.items():
    bars = get_bars(sym, "1Day", 50)
    analysis = analyze_symbol(sym, bars)
    analysis["name"] = name
    results.append(analysis)
    
    if "error" in analysis:
        print(f"\n  {sym} ({name}): ERROR - {analysis['error']}")
        continue
    
    # Determine signal
    signals = []
    rsi = analysis["rsi14"]
    dist_h = analysis["dist_from_high"]
    
    if rsi and rsi < 30:
        signals.append("RSI oversold")
    elif rsi and rsi > 70:
        signals.append("RSI overbought")
    
    if dist_h and dist_h < -25:
        signals.append(f"Down {dist_h}% from high")
    
    if analysis["above_20ma"] is False and analysis["above_50ma"] is False:
        signals.append("Below all MAs")
    elif analysis["above_20ma"] and analysis["above_50ma"]:
        signals.append("Above all MAs")
    
    signal_str = " | ".join(signals) if signals else "neutral"
    
    print(f"\n  {sym:6s} ({name})")
    print(f"    Price: ${analysis['price']:,.2f}  RSI: {rsi}  From High: {dist_h}%  From Low: +{analysis['dist_from_low']}%")
    print(f"    20MA: ${analysis['sma20']}  50MA: ${analysis['sma50']}")
    print(f"    Signal: {signal_str}")

# Summary
print(f"\n{'=' * 80}")
print("  STRATEGY ASSESSMENT SUMMARY")
print(f"{'=' * 80}")

# Count oversold
oversold = [r for r in results if r.get("rsi14") and r["rsi14"] < 30]
overbought = [r for r in results if r.get("rsi14") and r["rsi14"] > 70]
deep_discount = [r for r in results if r.get("dist_from_high") and r["dist_from_high"] < -20]
above_all_ma = [r for r in results if r.get("above_20ma") and r.get("above_50ma")]
below_all_ma = [r for r in results if r.get("above_20ma") is False and r.get("above_50ma") is False]

print(f"\n  Oversold (RSI<30): {len(oversold)} stocks")
for s in oversold:
    print(f"    {s['symbol']}: RSI={s['rsi14']}, price=${s['price']:,.2f}")

print(f"\n  Overbought (RSI>70): {len(overbought)} stocks")
for s in overbought:
    print(f"    {s['symbol']}: RSI={s['rsi14']}, price=${s['price']:,.2f}")

print(f"\n  Deep Discount (>20% from high): {len(deep_discount)} stocks")
for s in deep_discount:
    print(f"    {s['symbol']}: {s['dist_from_high']}% from high, price=${s['price']:,.2f}")

print(f"\n  Above all MAs (bullish): {len(above_all_ma)} stocks")
print(f"  Below all MAs (bearish): {len(below_all_ma)} stocks")

# S4 Panic assessment for US market
print(f"\n  --- S4 PANIC REBOUND ASSESSMENT (US) ---")
vixy = next((r for r in results if r["symbol"] == "VIXY"), None)
spy = next((r for r in results if r["symbol"] == "SPY"), None)

panic_signals = 0
if vixy and vixy.get("price") and vixy["price"] > 25:
    panic_signals += 1
    print(f"  [x] VIXY elevated: ${vixy['price']:,.2f}")
if spy and spy.get("rsi14") and spy["rsi14"] < 30:
    panic_signals += 1
    print(f"  [x] SPY RSI oversold: {spy['rsi14']}")
if spy and spy.get("dist_from_high") and spy["dist_from_high"] < -15:
    panic_signals += 1
    print(f"  [x] SPY deep discount: {spy['dist_from_high']}% from high")
if len(oversold) >= 3:
    panic_signals += 1
    print(f"  [x] Broad oversold: {len(oversold)} stocks RSI<30")
if len(deep_discount) >= 5:
    panic_signals += 1
    print(f"  [x] Broad discount: {len(deep_discount)} stocks >20% from high")

print(f"\n  Panic signals: {panic_signals}/5")
if panic_signals >= 3:
    print(f"  >>> S4 US MARKET: PANIC REBOUND TRIGGERED")
elif panic_signals >= 2:
    print(f"  >>> S4 US MARKET: APPROACHING PANIC ZONE - PREPARE")
else:
    print(f"  >>> S4 US MARKET: No panic signal yet")

print(f"\n{'=' * 80}")
