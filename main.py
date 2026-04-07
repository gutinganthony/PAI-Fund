"""
AI Trading System - Main Controller
Orchestrates market scanning, signal detection, and trade execution.
"""

import os
import sys
import json
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from review.market_scanner import scan_market, get_btc_price_and_rsi, get_crypto_fear_greed
from review.review_engine import (
    generate_weekly_report,
    strategy_performance,
    open_positions_review,
    detect_losing_streak,
    temperature_trend,
)
from journal.trade_journal import init_db, record_entry, get_open_trades


def try_avi():
    """Run AVI 3.0 (may take 1-2 minutes due to data fetching)."""
    try:
        from review.avi_integration import run_avi
        return run_avi()
    except Exception as e:
        print(f"  AVI unavailable: {e}")
        return None


def daily_scan(include_avi=False):
    """Run daily market scan + signal check."""
    init_db()

    steps = 5 if include_avi else 4

    print("=" * 60)
    print("  AI TRADING SYSTEM - DAILY SCAN")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # 1. Market temperature
    print(f"\n[1/{steps}] Market Temperature Scan...")
    result = scan_market()

    # 2. Open positions check
    print(f"\n[2/{steps}] Checking Open Positions...")
    opens = open_positions_review()
    print(f"  Open positions: {opens['open_positions']}")
    if opens.get("positions"):
        for p in opens["positions"]:
            print(f"    {p['symbol']} ({p['strategy']}) - hold {p['hold_days']}d")

    # 3. Losing streak detection
    print(f"\n[3/{steps}] Alert Check...")
    strategies = ["S1-momentum-breakout", "S2-value-undervalued", "S3-market-cycle",
                  "S4-panic-rebound", "S5-trend-following-crypto", "Leopold-AI-Energy"]
    alerts = []
    for s in strategies:
        streak = detect_losing_streak(strategy=s)
        if streak["alert"]:
            alerts.append(streak["action"])
            print(f"  ⚠️  {streak['action']}")
    if not alerts:
        print("  ✅ No alerts.")

    # 4. Signal summary
    print(f"\n[4/{steps}] Strategy Signals...")
    crypto_temp = result["crypto"]["temperature"]

    # S3 Market Cycle signals
    if crypto_temp < 20:
        print("  🟢 S3-CRYPTO: AGGRESSIVE BUY signal (temperature < 20)")
    elif crypto_temp < 40:
        print("  🟢 S3-CRYPTO: BUY signal (temperature < 40)")
    elif crypto_temp > 80:
        print("  🔴 S3-CRYPTO: REDUCE signal (temperature > 80)")
    else:
        print(f"  ⚪ S3-CRYPTO: No signal (temperature = {crypto_temp})")

    # S4 Panic Rebound signals
    fg = result["crypto"]["fear_greed"]
    if fg and fg.get("value") is not None and fg["value"] < 15:
        print(f"  🟢 S4-CRYPTO: PANIC detected! Fear & Greed = {fg['value']} ({fg['label']})")
    else:
        print(f"  ⚪ S4: No panic signal (Fear & Greed = {fg.get('value', 'N/A')})")

    print("  ⚪ S1/S5: Individual ticker scanning not yet automated")
    print("  ⚪ S2: Fundamental screening not yet automated")

    # 5. AVI (optional, slower)
    avi_result = None
    if include_avi:
        print(f"\n[5/{steps}] AVI 3.0 Market Risk Index...")
        avi_result = try_avi()

    print(f"\n{'=' * 60}")
    print("  DAILY SCAN COMPLETE")
    print(f"{'=' * 60}")

    return {"market": result, "avi": avi_result}


def weekly_review():
    """Run weekly review with AVI."""
    init_db()
    report = generate_weekly_report()
    print(report)

    # Also run AVI for weekly context
    print("\n--- AVI 3.0 WEEKLY UPDATE ---")
    try_avi()

    return report


def show_status():
    """Show current system status."""
    init_db()
    print("=" * 60)
    print("  AI TRADING SYSTEM STATUS")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # Account balances
    print("\n--- ACCOUNTS ---")
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    config = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip()

    try:
        from okx import Account
        account = Account.AccountAPI(config["OKX_API_KEY"], config["OKX_SECRET_KEY"],
                                      config["OKX_PASSPHRASE"], flag="1", debug=False)
        balance = account.get_account_balance()
        if balance and balance.get("code") == "0":
            print("  OKX Demo:")
            for d in balance["data"][0].get("details", []):
                avail = float(d.get("availBal", 0))
                if avail > 0:
                    print(f"    {d['ccy']}: {d['availBal']}")
    except Exception as e:
        print(f"  OKX: Error - {e}")

    try:
        from urllib.request import Request, urlopen
        req = Request(f"{config.get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets/v2')}/account", headers={
            "APCA-API-KEY-ID": config.get("ALPACA_API_KEY", ""),
            "APCA-API-SECRET-KEY": config.get("ALPACA_SECRET_KEY", ""),
        })
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            print(f"  Alpaca Paper:")
            print(f"    Equity: ${data['equity']}")
            print(f"    Cash: ${data['cash']}")
    except Exception as e:
        print(f"  Alpaca: Error - {e}")

    # Open positions
    print("\n--- OPEN POSITIONS ---")
    opens = open_positions_review()
    print(f"  Count: {opens['open_positions']}")

    # Recent performance
    print("\n--- 30-DAY PERFORMANCE ---")
    perf = strategy_performance(days=30)
    if perf["total_trades"] > 0:
        print(f"  Trades: {perf['total_trades']} | WR: {perf['win_rate']}% | PnL: ${perf['total_pnl']:,.2f}")
    else:
        print("  No closed trades yet.")

    # Temperature
    print("\n--- LATEST TEMPERATURE ---")
    for m in ["crypto", "us_stocks", "us_stocks_avi"]:
        tt = temperature_trend(market=m, days=7)
        if tt.get("latest") is not None:
            label = "AVI" if "avi" in m else m
            print(f"  {label}: {tt['latest']} (trend: {tt['trend']})")

    print(f"\n{'=' * 60}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "scan":
        daily_scan(include_avi=False)
    elif cmd == "scan-full":
        daily_scan(include_avi=True)
    elif cmd == "avi":
        try_avi()
    elif cmd == "review":
        weekly_review()
    elif cmd == "status":
        show_status()
    else:
        print("Usage: python main.py [scan|scan-full|avi|review|status]")
