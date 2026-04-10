# PAI Fund — System Specification

> Personal AI Investment Fund. A self-training investment system.
> Any AI reading this file should be able to understand and operate the entire system.

## Quick Start

```bash
# 1. Clone
git clone https://github.com/gutinganthony/PAI-Fund.git
cd PAI-Fund

# 2. Setup credentials
cp .env.example .env
# Fill in OKX + Alpaca API keys

# 3. Install dependencies
pip install python-okx yfinance python-dotenv requests

# 4. Run daily scan
python standalone_scan.py

# 5. View dashboard
# Open dashboard/index.html in browser, or visit GitHub Pages
```

## Architecture

```
PAI-Fund/
├── standalone_scan.py      # ENTRY POINT: daily scan (idempotent, no LLM needed)
├── main.py                 # Legacy controller (scan/review/status commands)
├── SYSTEM.md               # THIS FILE — system spec for AI handoff
├── STRATEGY-OVERVIEW.md    # Complete strategy logic (S1-S5 + Leopold)
├── .env                    # API credentials (NEVER commit)
├── .env.example            # Credential template
│
├── knowledge-base/         # 9 investment masters' wisdom
│   ├── 00-index.md
│   ├── 01-kostolany.md     # André Kostolany — market psychology
│   ├── 02-buffett.md       # Warren Buffett — value investing
│   ├── 03-minervini.md     # Mark Minervini — momentum (SEPA)
│   ├── 04-peter-lynch.md   # Peter Lynch — growth at reasonable price
│   ├── 05-howard-marks.md  # Howard Marks — 2nd level thinking
│   ├── 06-a16z.md          # a16z — tech venture thesis
│   ├── 07-ycombinator.md   # Y Combinator — startup investing
│   ├── 08-duan-yongping.md # 段永平 — value + moat
│   └── 09-leopold-aschenbrenner.md  # AI supply chain thesis
│
├── strategies/             # 5 strategy definitions
│   ├── S1-momentum-breakout.md
│   ├── S2-value-undervalued.md
│   ├── S3-market-cycle.md
│   ├── S4-panic-rebound.md
│   └── S5-trend-following-crypto.md
│
├── exchange/               # Broker API clients
│   ├── okx_client.py       # OKX Demo (crypto) — use functions, not class
│   ├── alpaca_client.py    # Alpaca Paper (US stocks) — urllib REST
│   ├── execute_trade.py    # Generic trade executor
│   └── check_positions.py  # Position checker
│
├── journal/                # Trade journal
│   ├── trade_journal.py    # SQLite CRUD (trades, strategy_stats, market_temperature, reviews)
│   ├── trades.db           # SQLite database (not in git, recreated on init)
│   ├── scans/              # Daily scan outputs
│   │   ├── YYYY-MM-DD.json # Machine-readable scan data
│   │   └── YYYY-MM-DD.md   # Human-readable scan report
│   └── YYYY-MM-DD-*.md     # Trade rationale documents
│
├── review/                 # Analysis engines
│   ├── market_scanner.py   # Market temperature (crypto F&G + VIX + RSI)
│   ├── review_engine.py    # Weekly review, streak detection
│   ├── deep_research.py    # Deep research tool
│   ├── avi_integration.py  # AVI 3.0 (Adjusted Valuation Index)
│   ├── theme_watchlist.py  # Sector theme tracking
│   └── strategy_dialectic.md  # Self-dialectic framework
│
└── dashboard/              # Web dashboard
    ├── index.html          # Single-page dashboard (pure HTML/JS, no deps)
    ├── data.json           # Current positions + market data
    ├── generate_data.py    # Pulls from Alpaca + yfinance → data.json
    └── history.json        # Historical daily snapshots (append-only)
```

## Platforms

| Platform | Type | Account Mode | Notes |
|----------|------|-------------|-------|
| OKX Demo | Crypto | Multi-currency margin (mode=3) | `tdMode="cross"`, `tgtCcy="quote_ccy"` |
| Alpaca Paper | US Stocks | Paper trading | REST API via urllib |

**OKX API is blocked by Cloudflare** (403 error 1010). Workaround: yfinance for prices, journal for position tracking. Trading still works via SDK.

## Current Holdings (as of 2026-04-10)

### Crypto (OKX Demo)
| Asset | Qty | Entry Price | Strategy |
|-------|-----|-------------|----------|
| BTC | 0.044 | $67,975 | S4 Panic Rebound Batch 1 |
| ETH | 0.7342 | $2,037 | S4 Panic Rebound Batch 1 |
| SOL | 6.2436 | $79.84 | S4 Panic Rebound Batch 1 |

### US Stocks (Alpaca Paper)
| Symbol | Shares | Entry Price | Strategy |
|--------|--------|-------------|----------|
| CEG | 10.99 | $272.97 | Leopold AI Energy Layer |
| VST | 13.15 | $152.09 | Leopold AI Energy Layer |
| MSFT | 25.57 | $371.48 | S2 Value Undervalued |

### Capital
- OKX: ~78,097 USDT cash
- Alpaca: ~$85,500 cash
- Total: ~$183,500
- Invested: ~$19,500 (10.6%)

## Strategies Summary

### S1: Momentum Breakout (Minervini SEPA)
- Triggers: New 52w high + volume surge + consolidation breakout
- Stop: -8% from entry

### S2: Value Undervalued (Buffett + 段永平)
- Triggers: Fwd PE < historical, strong moat, temporary setback
- Stop: -15% from entry

### S3: Market Cycle (Kostolany Egg)
- Triggers: Temperature-based allocation (cold=buy, hot=sell)
- Uses Fear & Greed Index + VIX + RSI

### S4: Panic Rebound (Howard Marks 2nd Level)
- Triggers: F&G < 10, or BTC -10% from entry, or RSI < 25 (need 2/3)
- 3 batches: panic → deeper panic → first bounce
- Stop: -15%

### S5: Trend Following Crypto
- Triggers: BTC above 20W MA + golden cross + volume confirmation
- Altcoin allocation follows BTC dominance

### Leopold AI Energy Layer
- Thesis: AI compute demand → energy infrastructure
- Layer 0 (Energy): CEG, VST — nuclear/power
- Layer 1 (Chips): NVDA, AMD, AVGO
- Layer 2 (Infra): MSFT Azure, AMZN AWS, GOOG GCP

## S4 Batch Trigger Rules

### Batch 2 (not yet triggered)
Need 2 of 3:
1. Fear & Greed < 10
2. BTC drops 10% from $67,975 (< $61,177)
3. BTC RSI(14) < 25

### Batch 3
Need 1 of:
1. First bullish daily candle after panic
2. F&G rebounds >10 pts from bottom
3. Daily low stops making new lows

## Stop Loss Rules

| Position | Stop | Rationale |
|----------|------|-----------|
| All positions | -15% | Default hard stop |
| VST | -12% | FCF negative, D/E 400% (tightened) |

## Key Files to Read

If you're a new AI taking over:
1. This file (SYSTEM.md)
2. STRATEGY-OVERVIEW.md — detailed strategy logic
3. journal/scans/[latest].json — most recent market data
4. dashboard/data.json — current positions
5. knowledge-base/00-index.md — master index

## Daily Operations

The system runs autonomously via `standalone_scan.py`:
1. Fetch crypto prices (yfinance)
2. Fetch Alpaca positions (REST API)
3. Check S4 batch triggers
4. Check stop losses
5. Update dashboard/data.json
6. Save to journal/scans/YYYY-MM-DD.json + .md
7. Git commit + push (if configured)

**Trade decisions require human confirmation.** The scan reports signals but does not auto-execute.

## Known Issues

1. OKX REST API blocked by Cloudflare — use yfinance for prices
2. `generate_data.py` has "no such column: date" bug in DB query
3. S1/S5 individual ticker scanning not yet automated
4. S2 fundamental screening not yet automated
5. Historical backtesting not yet implemented
