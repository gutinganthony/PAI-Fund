"""
Trade Journal Database
Records all trades, decisions, and review notes for strategy evolution.
"""

import sqlite3
import os
import json
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), "trades.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the trade journal database."""
    conn = _get_conn()
    c = conn.cursor()

    # Main trades table
    c.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        strategy TEXT NOT NULL,
        platform TEXT NOT NULL,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        order_type TEXT,
        quantity REAL NOT NULL,
        entry_price REAL,
        exit_price REAL,
        stop_loss REAL,
        take_profit REAL,
        status TEXT DEFAULT 'open',
        pnl REAL,
        pnl_pct REAL,
        fees REAL DEFAULT 0,
        entry_reason TEXT,
        exit_reason TEXT,
        market_context TEXT,
        indicators_snapshot TEXT,
        notes TEXT,
        order_id TEXT,
        closed_at TEXT,
        hold_days INTEGER
    )""")

    # Strategy performance table
    c.execute("""
    CREATE TABLE IF NOT EXISTS strategy_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        strategy TEXT NOT NULL,
        period TEXT NOT NULL,
        total_trades INTEGER,
        wins INTEGER,
        losses INTEGER,
        win_rate REAL,
        avg_win REAL,
        avg_loss REAL,
        profit_factor REAL,
        sharpe_ratio REAL,
        max_drawdown REAL,
        total_pnl REAL,
        notes TEXT
    )""")

    # Daily market temperature
    c.execute("""
    CREATE TABLE IF NOT EXISTS market_temperature (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        market TEXT NOT NULL,
        temperature REAL,
        vix REAL,
        fear_greed REAL,
        crypto_fear_greed REAL,
        rsi_spy REAL,
        rsi_btc REAL,
        components TEXT,
        action_suggested TEXT
    )""")

    # Review / reflection log
    c.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        review_type TEXT NOT NULL,
        strategy TEXT,
        period_start TEXT,
        period_end TEXT,
        summary TEXT,
        lessons TEXT,
        parameter_changes TEXT,
        action_items TEXT
    )""")

    conn.commit()
    conn.close()
    return True


# ─── Trade CRUD ────────────────────────────────────────────

def record_entry(strategy, platform, symbol, side, quantity, entry_price,
                 stop_loss=None, take_profit=None, entry_reason="",
                 market_context="", indicators="", order_id=""):
    """Record a new trade entry."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
    INSERT INTO trades (timestamp, strategy, platform, symbol, side, quantity,
                        entry_price, stop_loss, take_profit, status,
                        entry_reason, market_context, indicators_snapshot, order_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        strategy, platform, symbol, side, quantity,
        entry_price, stop_loss, take_profit,
        entry_reason, market_context,
        json.dumps(indicators) if isinstance(indicators, dict) else indicators,
        order_id
    ))
    trade_id = c.lastrowid
    conn.commit()
    conn.close()
    return trade_id


def record_exit(trade_id, exit_price, exit_reason="", fees=0):
    """Record a trade exit and calculate P&L."""
    conn = _get_conn()
    c = conn.cursor()

    # Get the trade
    c.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
    trade = c.fetchone()
    if not trade:
        conn.close()
        return None

    entry_price = trade["entry_price"]
    quantity = trade["quantity"]
    side = trade["side"]

    # Calculate P&L
    if side == "buy":
        pnl = (exit_price - entry_price) * quantity - fees
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
    else:
        pnl = (entry_price - exit_price) * quantity - fees
        pnl_pct = ((entry_price - exit_price) / entry_price) * 100

    # Calculate hold days
    entry_time = datetime.fromisoformat(trade["timestamp"])
    hold_days = (datetime.utcnow() - entry_time).days

    c.execute("""
    UPDATE trades SET exit_price = ?, exit_reason = ?, fees = ?,
                      pnl = ?, pnl_pct = ?, status = 'closed',
                      closed_at = ?, hold_days = ?
    WHERE id = ?
    """, (exit_price, exit_reason, fees, pnl, pnl_pct,
          datetime.utcnow().isoformat(), hold_days, trade_id))

    conn.commit()
    conn.close()
    return {"trade_id": trade_id, "pnl": pnl, "pnl_pct": pnl_pct, "hold_days": hold_days}


def get_open_trades(strategy=None):
    """Get all open trades, optionally filtered by strategy."""
    conn = _get_conn()
    c = conn.cursor()
    if strategy:
        c.execute("SELECT * FROM trades WHERE status = 'open' AND strategy = ? ORDER BY timestamp DESC", (strategy,))
    else:
        c.execute("SELECT * FROM trades WHERE status = 'open' ORDER BY timestamp DESC")
    trades = [dict(row) for row in c.fetchall()]
    conn.close()
    return trades


def get_closed_trades(strategy=None, limit=50):
    """Get closed trades."""
    conn = _get_conn()
    c = conn.cursor()
    if strategy:
        c.execute("SELECT * FROM trades WHERE status = 'closed' AND strategy = ? ORDER BY closed_at DESC LIMIT ?",
                  (strategy, limit))
    else:
        c.execute("SELECT * FROM trades WHERE status = 'closed' ORDER BY closed_at DESC LIMIT ?", (limit,))
    trades = [dict(row) for row in c.fetchall()]
    conn.close()
    return trades


def get_strategy_summary(strategy):
    """Get summary statistics for a strategy."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM trades WHERE status = 'closed' AND strategy = ?", (strategy,))
    trades = c.fetchall()
    conn.close()

    if not trades:
        return {"strategy": strategy, "total_trades": 0}

    wins = [t for t in trades if t["pnl"] and t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] and t["pnl"] <= 0]

    total_pnl = sum(t["pnl"] for t in trades if t["pnl"])
    avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0

    return {
        "strategy": strategy,
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(trades) * 100 if trades else 0,
        "total_pnl": total_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": abs(sum(t["pnl"] for t in wins)) / abs(sum(t["pnl"] for t in losses)) if losses and sum(t["pnl"] for t in losses) != 0 else float("inf"),
    }


# ─── Market Temperature ───────────────────────────────────

def record_temperature(market, temperature, vix=None, fear_greed=None,
                       crypto_fg=None, rsi_spy=None, rsi_btc=None,
                       components=None, action=None):
    """Record daily market temperature reading."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
    INSERT INTO market_temperature (timestamp, market, temperature, vix, fear_greed,
                                     crypto_fear_greed, rsi_spy, rsi_btc, components, action_suggested)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(), market, temperature,
        vix, fear_greed, crypto_fg, rsi_spy, rsi_btc,
        json.dumps(components) if components else None, action
    ))
    conn.commit()
    conn.close()


# ─── Reviews ──────────────────────────────────────────────

def record_review(review_type, strategy=None, period_start=None, period_end=None,
                  summary="", lessons="", parameter_changes="", action_items=""):
    """Record a review/reflection entry."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
    INSERT INTO reviews (timestamp, review_type, strategy, period_start, period_end,
                         summary, lessons, parameter_changes, action_items)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(), review_type, strategy,
        period_start, period_end, summary, lessons, parameter_changes, action_items
    ))
    conn.commit()
    conn.close()


# ─── Init ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("Initializing trade journal database...")
    init_db()
    print(f"Database created at: {DB_PATH}")

    # Demo: record a sample trade
    tid = record_entry(
        strategy="S1-momentum-breakout",
        platform="OKX",
        symbol="BTC-USDT",
        side="buy",
        quantity=0.01,
        entry_price=68000,
        stop_loss=63000,
        take_profit=78000,
        entry_reason="SEPA template passed, VCP breakout with volume confirmation",
        market_context="Crypto Fear&Greed=45, BTC above all MAs, Stage 2 confirmed",
    )
    print(f"Sample trade recorded: ID={tid}")

    # Demo: close it
    result = record_exit(tid, exit_price=72000, exit_reason="Take profit 1/3 hit")
    print(f"Trade closed: PnL=${result['pnl']:.2f} ({result['pnl_pct']:.1f}%)")

    # Summary
    summary = get_strategy_summary("S1-momentum-breakout")
    print(f"\nStrategy Summary: {json.dumps(summary, indent=2)}")
