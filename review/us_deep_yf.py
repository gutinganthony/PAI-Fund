"""US Market Deep Analysis using Yahoo Finance."""
import sys, json
sys.stdout.reconfigure(encoding="utf-8")

import yfinance as yf
import warnings
warnings.filterwarnings("ignore")

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_g / avg_l)), 1)

def calc_sma(closes, period):
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 2)

symbols = {
    # Indices
    "SPY": "S&P 500 ETF",
    "QQQ": "NASDAQ 100 ETF",
    "IWM": "Russell 2000 ETF",
    # VIX
    "^VIX": "VIX Index",
    # AI Supply Chain (Leopold Layer 0-2)
    "NVDA": "NVIDIA (GPU)",
    "AVGO": "Broadcom (AI chips)",
    "AMD": "AMD (GPU)",
    "SMCI": "Super Micro (servers)",
    "TSM": "TSMC (foundry)",
    # Mag 7
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Google",
    "AMZN": "Amazon",
    "META": "Meta",
    "TSLA": "Tesla",
    # AI Energy (Layer 0)
    "CEG": "Constellation Energy",
    "VST": "Vistra Energy",
    # Value / Quality
    "BRK-B": "Berkshire Hathaway",
    "COST": "Costco",
    "V": "Visa",
}

print("=" * 90)
print("  US MARKET DEEP ANALYSIS (Yahoo Finance)")
print("=" * 90)

results = []
vix_value = None

for sym, name in symbols.items():
    try:
        ticker = yf.Ticker(sym)
        hist = ticker.history(period="6mo")
        
        if hist.empty or len(hist) < 10:
            print(f"\n  {sym:6s} ({name}): insufficient data")
            continue
        
        closes = hist["Close"].tolist()
        highs = hist["High"].tolist()
        lows = hist["Low"].tolist()
        volumes = hist["Volume"].tolist()
        
        price = closes[-1]
        high_6m = max(highs)
        low_6m = min(lows)
        
        rsi = calc_rsi(closes)
        sma20 = calc_sma(closes, 20)
        sma50 = calc_sma(closes, 50)
        sma150 = calc_sma(closes, min(150, len(closes)))
        sma200 = calc_sma(closes, min(200, len(closes)))
        
        dist_high = round((price - high_6m) / high_6m * 100, 1)
        dist_low = round((price - low_6m) / low_6m * 100, 1)
        
        # 20-day average volume
        avg_vol = sum(volumes[-20:]) / min(20, len(volumes))
        vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1
        
        # Change calculations
        chg_1d = round((closes[-1] / closes[-2] - 1) * 100, 2) if len(closes) >= 2 else 0
        chg_5d = round((closes[-1] / closes[-6] - 1) * 100, 2) if len(closes) >= 6 else 0
        chg_20d = round((closes[-1] / closes[-21] - 1) * 100, 2) if len(closes) >= 21 else 0
        
        if sym == "^VIX":
            vix_value = price
        
        r = {
            "symbol": sym, "name": name, "price": round(price, 2),
            "rsi14": rsi, "sma20": sma20, "sma50": sma50,
            "sma150": sma150, "sma200": sma200,
            "high_6m": round(high_6m, 2), "low_6m": round(low_6m, 2),
            "dist_high": dist_high, "dist_low": dist_low,
            "chg_1d": chg_1d, "chg_5d": chg_5d, "chg_20d": chg_20d,
            "vol_ratio": round(vol_ratio, 2),
            "above_20": price > sma20 if sma20 else None,
            "above_50": price > sma50 if sma50 else None,
            "above_200": price > sma200 if sma200 else None,
        }
        results.append(r)
        
        # Signals
        signals = []
        if rsi and rsi < 30: signals.append("🔴 RSI oversold")
        elif rsi and rsi < 40: signals.append("🟡 RSI weak")
        elif rsi and rsi > 70: signals.append("🔴 RSI overbought")
        
        if dist_high < -30: signals.append(f"💥 Crashed {dist_high}%")
        elif dist_high < -20: signals.append(f"📉 Deep discount {dist_high}%")
        elif dist_high < -10: signals.append(f"📉 Pullback {dist_high}%")
        
        if r["above_20"] is False and r["above_50"] is False:
            signals.append("⬇ Below MAs")
        elif r["above_20"] and r["above_50"]:
            signals.append("⬆ Above MAs")
        
        sig_str = " | ".join(signals) if signals else "neutral"
        
        print(f"\n  {sym:6s} ({name})")
        print(f"    ${price:>10,.2f}  RSI:{rsi:>5}  1d:{chg_1d:>+6.1f}%  5d:{chg_5d:>+6.1f}%  20d:{chg_20d:>+6.1f}%")
        print(f"    From High:{dist_high:>+6.1f}%  20MA:${sma20}  50MA:${sma50}  Vol:{vol_ratio:.1f}x")
        print(f"    {sig_str}")
        
    except Exception as e:
        print(f"\n  {sym:6s} ({name}): ERROR - {e}")

# ─── Summary ───────────────────────────────────────────────
print(f"\n{'=' * 90}")
print("  COMPREHENSIVE STRATEGY ASSESSMENT")
print(f"{'=' * 90}")

non_vix = [r for r in results if r["symbol"] != "^VIX"]
oversold = [r for r in non_vix if r.get("rsi14") and r["rsi14"] < 30]
weak = [r for r in non_vix if r.get("rsi14") and 30 <= r["rsi14"] < 40]
overbought = [r for r in non_vix if r.get("rsi14") and r["rsi14"] > 70]
deep_disc = [r for r in non_vix if r.get("dist_high") and r["dist_high"] < -20]
pullback = [r for r in non_vix if r.get("dist_high") and -20 <= r["dist_high"] < -10]
below_all = [r for r in non_vix if r.get("above_20") is False and r.get("above_50") is False]

print(f"\n  VIX: {vix_value}" if vix_value else "\n  VIX: N/A")

print(f"\n  📊 MARKET BREADTH:")
print(f"    RSI Oversold (<30): {len(oversold)} — {', '.join(r['symbol'] for r in oversold)}" if oversold else "    RSI Oversold (<30): 0")
print(f"    RSI Weak (30-40):   {len(weak)} — {', '.join(r['symbol'] for r in weak)}" if weak else "    RSI Weak (30-40):   0")
print(f"    RSI Overbought:     {len(overbought)} — {', '.join(r['symbol'] for r in overbought)}" if overbought else "    RSI Overbought:     0")
dd_str = ', '.join(r["symbol"] + "(" + str(r["dist_high"]) + "%)" for r in deep_disc)
print(f"    Deep Discount >20%: {len(deep_disc)} — {dd_str}" if deep_disc else "    Deep Discount >20%: 0")
pb_str = ', '.join(r["symbol"] + "(" + str(r["dist_high"]) + "%)" for r in pullback)
print(f"    Pullback 10-20%:    {len(pullback)} — {pb_str}" if pullback else "    Pullback 10-20%:    0")
print(f"    Below all MAs:      {len(below_all)} — {', '.join(r['symbol'] for r in below_all)}" if below_all else "    Below all MAs:      0")

# S4 US Panic Assessment
print(f"\n  --- S4 PANIC REBOUND (US MARKET) ---")
panic_score = 0
panic_details = []
if vix_value and vix_value > 35:
    panic_score += 2
    panic_details.append(f"VIX={vix_value:.1f} (extreme)")
elif vix_value and vix_value > 25:
    panic_score += 1
    panic_details.append(f"VIX={vix_value:.1f} (elevated)")

spy = next((r for r in results if r["symbol"] == "SPY"), None)
if spy:
    if spy.get("rsi14") and spy["rsi14"] < 25:
        panic_score += 2
        panic_details.append(f"SPY RSI={spy['rsi14']} (extreme oversold)")
    elif spy.get("rsi14") and spy["rsi14"] < 35:
        panic_score += 1
        panic_details.append(f"SPY RSI={spy['rsi14']} (weak)")
    if spy.get("dist_high") and spy["dist_high"] < -15:
        panic_score += 1
        panic_details.append(f"SPY {spy['dist_high']}% from high")

if len(oversold) >= 5:
    panic_score += 2
    panic_details.append(f"{len(oversold)} stocks oversold")
elif len(oversold) >= 3:
    panic_score += 1
    panic_details.append(f"{len(oversold)} stocks oversold")

if len(deep_disc) >= 5:
    panic_score += 1
    panic_details.append(f"{len(deep_disc)} stocks >20% off")

for d in panic_details:
    print(f"    {d}")
print(f"    Panic Score: {panic_score}/7")

if panic_score >= 5:
    print(f"    >>> VERDICT: FULL PANIC — S4 TRIGGERED, deploy Batch 1+2")
elif panic_score >= 3:
    print(f"    >>> VERDICT: ELEVATED FEAR — S4 Batch 1 warranted")
elif panic_score >= 2:
    print(f"    >>> VERDICT: CAUTIOUS — prepare but don't deploy yet")
else:
    print(f"    >>> VERDICT: NO PANIC — wait for better setup")

# S1 Momentum opportunities
print(f"\n  --- S1 MOMENTUM BREAKOUT OPPORTUNITIES ---")
for r in non_vix:
    if (r.get("above_20") and r.get("above_50") and 
        r.get("rsi14") and 50 < r["rsi14"] < 70 and
        r.get("dist_high") and r["dist_high"] > -10):
        print(f"    {r['symbol']:6s}: STRONG trend, RSI={r['rsi14']}, {r['dist_high']}% from high — watch for VCP")

# S2 Value opportunities  
print(f"\n  --- S2 VALUE OPPORTUNITIES ---")
for r in non_vix:
    if (r.get("dist_high") and r["dist_high"] < -20 and
        r.get("rsi14") and r["rsi14"] < 40 and
        r["symbol"] in ("AAPL", "MSFT", "GOOGL", "AMZN", "META", "V", "COST", "BRK-B")):
        print(f"    {r['symbol']:6s}: Quality name at discount, {r['dist_high']}% off, RSI={r['rsi14']} — evaluate fundamentals")

# Leopold AI supply chain
print(f"\n  --- LEOPOLD AI SUPPLY CHAIN ---")
ai_names = ["NVDA", "AVGO", "AMD", "SMCI", "TSM", "CEG", "VST"]
for r in [x for x in results if x["symbol"] in ai_names]:
    layer = "L1-GPU" if r["symbol"] in ("NVDA", "AMD", "AVGO", "TSM") else "L0-Energy" if r["symbol"] in ("CEG", "VST") else "L2-Infra"
    print(f"    {r['symbol']:6s} [{layer}]: ${r['price']:,.2f}  RSI:{r['rsi14']}  from high:{r['dist_high']}%  20d:{r['chg_20d']:+.1f}%")

print(f"\n{'=' * 90}")
