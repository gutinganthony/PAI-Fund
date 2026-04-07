"""
Review Engine
Automated trade review and strategy performance analysis.
Generates weekly/monthly reports and identifies patterns in wins/losses.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "journal", "trades.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Performance Analysis ─────────────────────────────────

def strategy_performance(strategy=None, days=30):
    """Analyze strategy performance over the last N days."""
    conn = _get_conn()
    c = conn.cursor()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    if strategy:
        c.execute("""
            SELECT * FROM trades
            WHERE status = 'closed' AND strategy = ? AND closed_at > ?
            ORDER BY closed_at DESC
        """, (strategy, cutoff))
    else:
        c.execute("""
            SELECT * FROM trades
            WHERE status = 'closed' AND closed_at > ?
            ORDER BY closed_at DESC
        """, (cutoff,))

    trades = [dict(row) for row in c.fetchall()]
    conn.close()

    if not trades:
        return {"period_days": days, "strategy": strategy or "ALL", "total_trades": 0, "message": "No closed trades in this period."}

    wins = [t for t in trades if t["pnl"] and t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] and t["pnl"] <= 0]

    total_pnl = sum(t["pnl"] for t in trades if t["pnl"])
    gross_profit = sum(t["pnl"] for t in wins) if wins else 0
    gross_loss = abs(sum(t["pnl"] for t in losses)) if losses else 0

    avg_win = gross_profit / len(wins) if wins else 0
    avg_loss = gross_loss / len(losses) if losses else 0
    avg_hold = sum(t["hold_days"] or 0 for t in trades) / len(trades) if trades else 0

    # Max drawdown (sequential)
    running_pnl = 0
    peak = 0
    max_dd = 0
    for t in sorted(trades, key=lambda x: x["closed_at"] or ""):
        running_pnl += t["pnl"] or 0
        peak = max(peak, running_pnl)
        dd = peak - running_pnl
        max_dd = max(max_dd, dd)

    # Profit factor
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Expectancy
    win_rate = len(wins) / len(trades)
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

    return {
        "period_days": days,
        "strategy": strategy or "ALL",
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate * 100, 1),
        "total_pnl": round(total_pnl, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "expectancy": round(expectancy, 2),
        "max_drawdown": round(max_dd, 2),
        "avg_hold_days": round(avg_hold, 1),
        "best_trade": max(trades, key=lambda t: t["pnl"] or 0),
        "worst_trade": min(trades, key=lambda t: t["pnl"] or 0),
    }


def open_positions_review():
    """Review all open positions with current status."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM trades WHERE status = 'open' ORDER BY timestamp DESC")
    trades = [dict(row) for row in c.fetchall()]
    conn.close()

    if not trades:
        return {"open_positions": 0, "message": "No open positions."}

    positions = []
    for t in trades:
        entry_time = datetime.fromisoformat(t["timestamp"])
        hold_days = (datetime.utcnow() - entry_time).days
        positions.append({
            "id": t["id"],
            "strategy": t["strategy"],
            "platform": t["platform"],
            "symbol": t["symbol"],
            "side": t["side"],
            "entry_price": t["entry_price"],
            "stop_loss": t["stop_loss"],
            "take_profit": t["take_profit"],
            "hold_days": hold_days,
            "entry_reason": t["entry_reason"],
        })

    return {"open_positions": len(positions), "positions": positions}


# ─── Pattern Detection ─────────────────────────────────────

def detect_losing_streak(strategy=None, threshold=3):
    """Detect if a strategy is on a losing streak."""
    conn = _get_conn()
    c = conn.cursor()

    if strategy:
        c.execute("""
            SELECT pnl FROM trades
            WHERE status = 'closed' AND strategy = ?
            ORDER BY closed_at DESC LIMIT 10
        """, (strategy,))
    else:
        c.execute("""
            SELECT pnl, strategy FROM trades
            WHERE status = 'closed'
            ORDER BY closed_at DESC LIMIT 10
        """)

    trades = c.fetchall()
    conn.close()

    consecutive_losses = 0
    for t in trades:
        if t["pnl"] and t["pnl"] <= 0:
            consecutive_losses += 1
        else:
            break

    alert = consecutive_losses >= threshold
    return {
        "strategy": strategy or "ALL",
        "consecutive_losses": consecutive_losses,
        "threshold": threshold,
        "alert": alert,
        "action": f"PAUSE {strategy} - {consecutive_losses} consecutive losses" if alert else "OK",
    }


def analyze_by_day_of_week(days=90):
    """Analyze trade performance by day of week."""
    conn = _get_conn()
    c = conn.cursor()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    c.execute("SELECT * FROM trades WHERE status = 'closed' AND closed_at > ?", (cutoff,))
    trades = [dict(row) for row in c.fetchall()]
    conn.close()

    if not trades:
        return {"message": "No data"}

    days_map = {}
    for t in trades:
        try:
            dt = datetime.fromisoformat(t["timestamp"])
            day_name = dt.strftime("%A")
            if day_name not in days_map:
                days_map[day_name] = {"trades": 0, "pnl": 0, "wins": 0}
            days_map[day_name]["trades"] += 1
            days_map[day_name]["pnl"] += t["pnl"] or 0
            if t["pnl"] and t["pnl"] > 0:
                days_map[day_name]["wins"] += 1
        except:
            pass

    return days_map


def analyze_by_symbol(strategy=None, days=90):
    """Analyze performance by trading symbol."""
    conn = _get_conn()
    c = conn.cursor()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    if strategy:
        c.execute("SELECT * FROM trades WHERE status = 'closed' AND strategy = ? AND closed_at > ?",
                  (strategy, cutoff))
    else:
        c.execute("SELECT * FROM trades WHERE status = 'closed' AND closed_at > ?", (cutoff,))

    trades = [dict(row) for row in c.fetchall()]
    conn.close()

    symbols = {}
    for t in trades:
        sym = t["symbol"]
        if sym not in symbols:
            symbols[sym] = {"trades": 0, "pnl": 0, "wins": 0, "losses": 0}
        symbols[sym]["trades"] += 1
        symbols[sym]["pnl"] += t["pnl"] or 0
        if t["pnl"] and t["pnl"] > 0:
            symbols[sym]["wins"] += 1
        else:
            symbols[sym]["losses"] += 1

    # Sort by PnL
    sorted_symbols = dict(sorted(symbols.items(), key=lambda x: x[1]["pnl"], reverse=True))
    return sorted_symbols


# ─── Temperature Trend ─────────────────────────────────────

def temperature_trend(market="crypto", days=30):
    """Get temperature trend over recent period."""
    conn = _get_conn()
    c = conn.cursor()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    c.execute("""
        SELECT timestamp, temperature, action_suggested
        FROM market_temperature
        WHERE market = ? AND timestamp > ?
        ORDER BY timestamp DESC
    """, (market, cutoff))
    readings = [dict(row) for row in c.fetchall()]
    conn.close()

    if not readings:
        return {"market": market, "readings": 0}

    temps = [r["temperature"] for r in readings if r["temperature"]]
    return {
        "market": market,
        "readings": len(readings),
        "latest": temps[0] if temps else None,
        "avg": round(sum(temps) / len(temps), 1) if temps else None,
        "min": min(temps) if temps else None,
        "max": max(temps) if temps else None,
        "trend": "warming" if len(temps) > 1 and temps[0] > temps[-1] else "cooling" if len(temps) > 1 else "stable",
    }


# ─── Weekly Report Generator ──────────────────────────────

def generate_weekly_report():
    """Generate a comprehensive weekly review report."""
    report = []
    report.append("=" * 60)
    report.append("  WEEKLY TRADING REVIEW")
    report.append(f"  Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    report.append("=" * 60)

    # Overall performance
    perf = strategy_performance(days=7)
    report.append(f"\n--- OVERALL (7 DAYS) ---")
    report.append(f"Total Trades: {perf['total_trades']}")
    if perf['total_trades'] > 0:
        report.append(f"Win Rate: {perf['win_rate']}%")
        report.append(f"Total PnL: ${perf['total_pnl']:,.2f}")
        report.append(f"Profit Factor: {perf['profit_factor']}")
        report.append(f"Expectancy: ${perf['expectancy']:,.2f}")
        report.append(f"Max Drawdown: ${perf['max_drawdown']:,.2f}")

    # Per-strategy performance
    strategies = ["S1-momentum-breakout", "S2-value-undervalued", "S3-market-cycle",
                  "S4-panic-rebound", "S5-trend-following-crypto"]
    for s in strategies:
        sp = strategy_performance(strategy=s, days=7)
        if sp["total_trades"] > 0:
            report.append(f"\n--- {s} ---")
            report.append(f"Trades: {sp['total_trades']} | WR: {sp['win_rate']}% | PnL: ${sp['total_pnl']:,.2f}")

    # Open positions
    opens = open_positions_review()
    report.append(f"\n--- OPEN POSITIONS ---")
    report.append(f"Count: {opens['open_positions']}")
    if opens.get("positions"):
        for p in opens["positions"]:
            report.append(f"  {p['symbol']} ({p['strategy']}) - {p['side']} @ ${p['entry_price']:,.2f} - hold {p['hold_days']}d")

    # Losing streaks
    report.append(f"\n--- ALERTS ---")
    for s in strategies:
        streak = detect_losing_streak(strategy=s)
        if streak["alert"]:
            report.append(f"  !! {streak['action']}")

    all_streak = detect_losing_streak()
    if all_streak["consecutive_losses"] > 0:
        report.append(f"  Overall consecutive losses: {all_streak['consecutive_losses']}")

    # Temperature
    report.append(f"\n--- MARKET TEMPERATURE ---")
    for m in ["crypto", "us_stocks"]:
        tt = temperature_trend(market=m, days=7)
        if tt.get("latest") is not None:
            report.append(f"  {m}: latest={tt['latest']} avg={tt['avg']} trend={tt['trend']}")

    report.append(f"\n{'=' * 60}")

    report_text = "\n".join(report)

    # Save review to DB
    try:
        from journal.trade_journal import record_review, init_db
        init_db()
        record_review(
            review_type="weekly",
            period_start=(datetime.utcnow() - timedelta(days=7)).isoformat(),
            period_end=datetime.utcnow().isoformat(),
            summary=report_text,
        )
    except Exception as e:
        report_text += f"\n(Could not save to DB: {e})"

    return report_text


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print(generate_weekly_report())
