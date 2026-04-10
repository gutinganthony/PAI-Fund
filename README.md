# PAI Fund 🤖💰

> **Personal AI Investment Fund** — A self-training investment system powered by the wisdom of 9 investment masters.

## What is this?

An AI-driven quantitative trading system that:
- Synthesizes wisdom from Kostolany, Buffett, Minervini, Peter Lynch, Howard Marks, a16z, YC, 段永平, and Leopold Aschenbrenner
- Runs 5+1 trading strategies across crypto (OKX Demo) and US stocks (Alpaca Paper)
- Continuously scans markets, tracks positions, and monitors risk
- Self-evolves through weekly reviews and strategy dialectics

## Dashboard

👉 **[Live Dashboard](https://gutinganthony.github.io/PAI-Fund/dashboard/)** (GitHub Pages)

## Quick Start

```bash
git clone https://github.com/gutinganthony/PAI-Fund.git
cd PAI-Fund
pip install python-okx yfinance python-dotenv requests
cp .env.example .env  # Fill in your API keys
python standalone_scan.py
```

## Strategies

| ID | Name | Master | Market |
|----|------|--------|--------|
| S1 | Momentum Breakout | Minervini (SEPA) | US Stocks |
| S2 | Value Undervalued | Buffett + 段永平 | US Stocks |
| S3 | Market Cycle | Kostolany Egg | Both |
| S4 | Panic Rebound | Howard Marks | Both |
| S5 | Trend Following | Multiple | Crypto |
| L0 | AI Energy Layer | Leopold | US Stocks |

## Architecture

```
standalone_scan.py  →  daily scan (no LLM needed)
        ↓
  journal/scans/    →  historical data
  dashboard/        →  web dashboard
        ↓
  git push          →  GitHub Pages (always accessible)
```

## For AI Agents

If you're an AI taking over this system, read **[SYSTEM.md](SYSTEM.md)** first. It contains everything you need to operate.

## ⚠️ Disclaimer

This is a **paper trading / demo trading** system. No real money is at risk. This is an educational project exploring AI-assisted investment decision making.
