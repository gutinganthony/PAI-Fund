"""
Deep Research: Individual stock analysis for QCOM, MSFT, CEG, VST
Fetches fundamentals, recent price action, news catalysts.
"""
import sys, json, warnings
sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")

import yfinance as yf
from datetime import datetime, timedelta

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


def analyze_stock(ticker_str):
    """Full fundamental + technical analysis of a single stock."""
    t = yf.Ticker(ticker_str)
    info = t.info
    hist = t.history(period="1y")
    hist_5y = t.history(period="5y")

    if hist.empty:
        print(f"  ❌ No data for {ticker_str}")
        return None

    closes = hist["Close"].tolist()
    price = closes[-1]

    # 52-week high/low
    high_52w = max(hist["High"].tolist())
    low_52w = min(hist["Low"].tolist())
    dist_52w_high = round((price - high_52w) / high_52w * 100, 1)
    dist_52w_low = round((price - low_52w) / low_52w * 100, 1)

    # RSI
    rsi = calc_rsi(closes)

    # SMA
    sma50 = round(sum(closes[-50:]) / 50, 2) if len(closes) >= 50 else None
    sma200 = round(sum(closes[-200:]) / 200, 2) if len(closes) >= 200 else None

    # Recent performance
    chg_5d = round((closes[-1] / closes[-6] - 1) * 100, 1) if len(closes) >= 6 else None
    chg_20d = round((closes[-1] / closes[-21] - 1) * 100, 1) if len(closes) >= 21 else None
    chg_60d = round((closes[-1] / closes[-61] - 1) * 100, 1) if len(closes) >= 61 else None
    chg_ytd = round((closes[-1] / closes[0] - 1) * 100, 1) if len(closes) > 1 else None

    # Fundamentals
    mcap = info.get("marketCap", 0)
    mcap_str = f"${mcap/1e9:.1f}B" if mcap > 1e9 else f"${mcap/1e6:.0f}M"
    pe_trailing = info.get("trailingPE")
    pe_forward = info.get("forwardPE")
    peg = info.get("pegRatio")
    ps = info.get("priceToSalesTrailing12Months")
    pb = info.get("priceToBook")
    ev_ebitda = info.get("enterpriseToEbitda")
    
    # Profitability
    roe = info.get("returnOnEquity")
    roa = info.get("returnOnAssets")
    profit_margin = info.get("profitMargins")
    op_margin = info.get("operatingMargins")
    gross_margin = info.get("grossMargins")
    
    # Growth
    rev_growth = info.get("revenueGrowth")
    earn_growth = info.get("earningsGrowth")
    earn_qg = info.get("earningsQuarterlyGrowth")
    
    # Balance sheet
    total_cash = info.get("totalCash", 0)
    total_debt = info.get("totalDebt", 0)
    fcf = info.get("freeCashflow", 0)
    debt_to_equity = info.get("debtToEquity")
    current_ratio = info.get("currentRatio")
    
    # Dividend
    div_yield = info.get("dividendYield")
    payout = info.get("payoutRatio")
    
    # Analyst targets
    target_mean = info.get("targetMeanPrice")
    target_low = info.get("targetLowPrice")
    target_high = info.get("targetHighPrice")
    rec = info.get("recommendationKey", "N/A")
    num_analysts = info.get("numberOfAnalystOpinions", 0)

    # Print report
    print(f"\n{'═' * 80}")
    print(f"  {ticker_str} — {info.get('longName', info.get('shortName', ticker_str))}")
    print(f"  Sector: {info.get('sector', 'N/A')} | Industry: {info.get('industry', 'N/A')}")
    print(f"{'═' * 80}")

    print(f"\n  ── PRICE & TECHNICAL ──")
    print(f"  Price: ${price:,.2f}  |  Market Cap: {mcap_str}")
    print(f"  52W High: ${high_52w:,.2f} ({dist_52w_high:+.1f}%)  |  52W Low: ${low_52w:,.2f} ({dist_52w_low:+.1f}%)")
    print(f"  RSI(14): {rsi}  |  SMA50: ${sma50:,.2f}  |  SMA200: ${sma200:,.2f}" if sma50 and sma200 else f"  RSI(14): {rsi}")
    
    above_50 = "✅" if sma50 and price > sma50 else "❌"
    above_200 = "✅" if sma200 and price > sma200 else "❌"
    print(f"  Above SMA50: {above_50}  |  Above SMA200: {above_200}")
    
    print(f"  5D: {chg_5d:+.1f}%  |  20D: {chg_20d:+.1f}%  |  60D: {chg_60d:+.1f}%  |  YTD: {chg_ytd:+.1f}%")

    print(f"\n  ── VALUATION ──")
    print(f"  P/E (TTM): {pe_trailing:.1f}" if pe_trailing else "  P/E (TTM): N/A")
    print(f"  P/E (Fwd): {pe_forward:.1f}" if pe_forward else "  P/E (Fwd): N/A")
    print(f"  PEG: {peg:.2f}" if peg else "  PEG: N/A")
    print(f"  P/S: {ps:.2f}" if ps else "  P/S: N/A")
    print(f"  P/B: {pb:.2f}" if pb else "  P/B: N/A")
    print(f"  EV/EBITDA: {ev_ebitda:.1f}" if ev_ebitda else "  EV/EBITDA: N/A")

    print(f"\n  ── PROFITABILITY ──")
    print(f"  ROE: {roe*100:.1f}%" if roe else "  ROE: N/A")
    print(f"  ROA: {roa*100:.1f}%" if roa else "  ROA: N/A")
    print(f"  Gross Margin: {gross_margin*100:.1f}%" if gross_margin else "  Gross Margin: N/A")
    print(f"  Operating Margin: {op_margin*100:.1f}%" if op_margin else "  Operating Margin: N/A")
    print(f"  Profit Margin: {profit_margin*100:.1f}%" if profit_margin else "  Profit Margin: N/A")

    print(f"\n  ── GROWTH ──")
    print(f"  Revenue Growth: {rev_growth*100:.1f}%" if rev_growth else "  Revenue Growth: N/A")
    print(f"  Earnings Growth: {earn_growth*100:.1f}%" if earn_growth else "  Earnings Growth: N/A")
    print(f"  Earnings QoQ Growth: {earn_qg*100:.1f}%" if earn_qg else "  Earnings QoQ Growth: N/A")

    print(f"\n  ── BALANCE SHEET ──")
    print(f"  Cash: ${total_cash/1e9:.1f}B" if total_cash > 1e9 else f"  Cash: ${total_cash/1e6:.0f}M")
    print(f"  Debt: ${total_debt/1e9:.1f}B" if total_debt > 1e9 else f"  Debt: ${total_debt/1e6:.0f}M")
    print(f"  FCF: ${fcf/1e9:.1f}B" if fcf and abs(fcf) > 1e9 else f"  FCF: ${fcf/1e6:.0f}M" if fcf else "  FCF: N/A")
    print(f"  Debt/Equity: {debt_to_equity:.1f}%" if debt_to_equity else "  Debt/Equity: N/A")
    print(f"  Current Ratio: {current_ratio:.2f}" if current_ratio else "  Current Ratio: N/A")

    if div_yield:
        print(f"\n  ── DIVIDEND ──")
        print(f"  Yield: {div_yield*100:.2f}%  |  Payout: {payout*100:.1f}%" if payout else f"  Yield: {div_yield*100:.2f}%")

    print(f"\n  ── ANALYST CONSENSUS ({num_analysts} analysts) ──")
    print(f"  Recommendation: {rec.upper()}")
    if target_mean:
        upside = round((target_mean - price) / price * 100, 1)
        print(f"  Target: ${target_low:,.0f} / ${target_mean:,.0f} / ${target_high:,.0f}  (upside: {upside:+.1f}%)")

    # Strategy assessment
    print(f"\n  ── STRATEGY ASSESSMENT ──")
    
    # S2 Value check (Buffett / 段永平)
    s2_score = 0
    s2_notes = []
    if pe_forward and pe_forward < 20: s2_score += 1; s2_notes.append(f"Fwd PE {pe_forward:.1f} < 20")
    if peg and peg < 1.5: s2_score += 1; s2_notes.append(f"PEG {peg:.2f} < 1.5")
    if roe and roe > 0.15: s2_score += 1; s2_notes.append(f"ROE {roe*100:.1f}% > 15%")
    if profit_margin and profit_margin > 0.15: s2_score += 1; s2_notes.append(f"Margin {profit_margin*100:.1f}% > 15%")
    if fcf and fcf > 0: s2_score += 1; s2_notes.append(f"FCF positive")
    if dist_52w_high < -25: s2_score += 1; s2_notes.append(f"Deep discount {dist_52w_high:+.1f}%")
    if debt_to_equity and debt_to_equity < 100: s2_score += 1; s2_notes.append(f"Low debt D/E={debt_to_equity:.0f}%")
    
    print(f"  S2 Value Score: {s2_score}/7 — {', '.join(s2_notes)}")
    
    # S1 Momentum check (Minervini)
    s1_score = 0
    s1_notes = []
    if sma50 and price > sma50: s1_score += 1; s1_notes.append("Above SMA50")
    if sma200 and price > sma200: s1_score += 1; s1_notes.append("Above SMA200")
    if sma50 and sma200 and sma50 > sma200: s1_score += 1; s1_notes.append("Golden cross")
    if rsi and 50 < rsi < 70: s1_score += 1; s1_notes.append(f"RSI in sweet spot ({rsi})")
    if dist_52w_high > -25: s1_score += 1; s1_notes.append(f"Within 25% of high")
    if rev_growth and rev_growth > 0.15: s1_score += 1; s1_notes.append(f"Rev growth {rev_growth*100:.1f}%")
    
    print(f"  S1 Momentum Score: {s1_score}/6 — {', '.join(s1_notes)}")
    
    # S4 Panic check
    if rsi and rsi < 30 and dist_52w_high < -30:
        print(f"  🔴 S4 PANIC CANDIDATE: RSI={rsi}, from high={dist_52w_high}%")
    elif rsi and rsi < 35:
        print(f"  🟡 S4 NEAR-PANIC: RSI={rsi}")
    
    print(f"{'═' * 80}")
    
    return {
        "ticker": ticker_str, "price": price, "rsi": rsi,
        "dist_52w_high": dist_52w_high, "pe_forward": pe_forward,
        "s2_score": s2_score, "s1_score": s1_score,
        "target_upside": round((target_mean - price) / price * 100, 1) if target_mean else None,
    }


if __name__ == "__main__":
    targets = ["QCOM", "MSFT", "CEG", "VST"]
    print("=" * 80)
    print("  DEEP RESEARCH — QCOM / MSFT / CEG / VST")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 80)
    
    results = {}
    for tk in targets:
        try:
            results[tk] = analyze_stock(tk)
        except Exception as e:
            print(f"\n  ❌ Error analyzing {tk}: {e}")
    
    # Comparison summary
    print(f"\n{'═' * 80}")
    print(f"  COMPARISON SUMMARY")
    print(f"{'═' * 80}")
    print(f"  {'Ticker':6s} {'Price':>10s} {'RSI':>6s} {'From High':>10s} {'Fwd PE':>8s} {'S2 Val':>7s} {'S1 Mom':>7s} {'Upside':>8s}")
    print(f"  {'─'*6} {'─'*10} {'─'*6} {'─'*10} {'─'*8} {'─'*7} {'─'*7} {'─'*8}")
    for tk in targets:
        r = results.get(tk)
        if r:
            print(f"  {r['ticker']:6s} ${r['price']:>9,.2f} {r['rsi'] or 0:>5.1f} {r['dist_52w_high']:>+9.1f}% "
                  f"{r['pe_forward'] or 0:>7.1f} {r['s2_score']:>5d}/7 {r['s1_score']:>5d}/6 "
                  f"{r['target_upside'] or 0:>+7.1f}%")
    print(f"{'═' * 80}")
