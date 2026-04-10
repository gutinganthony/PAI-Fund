"""
Standalone Daily Scanner — 不依賴 LobsterAI 也能運作
可以被以下方式觸發：
  1. LobsterAI cron (主要)
  2. Windows Task Scheduler (備援)
  3. 手動執行: python standalone_scan.py
  4. Heartbeat 檢查時發現今天沒跑過

輸出：
  - dashboard/data.json (dashboard 數據更新)
  - journal/scans/YYYY-MM-DD.json (每日掃描記錄，不可覆蓋)
  - journal/scans/YYYY-MM-DD.md (人類可讀報告)
  - 返回 exit code 0 = 成功
"""
import sys, os, json, sqlite3
from datetime import datetime, timezone, timedelta

# Setup paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
os.chdir(SCRIPT_DIR)

SCAN_DIR = os.path.join(SCRIPT_DIR, 'journal', 'scans')
os.makedirs(SCAN_DIR, exist_ok=True)

TODAY = datetime.now().strftime('%Y-%m-%d')
SCAN_JSON = os.path.join(SCAN_DIR, f'{TODAY}.json')
SCAN_MD = os.path.join(SCAN_DIR, f'{TODAY}.md')

def already_ran_today():
    """Check if scan already completed today"""
    return os.path.exists(SCAN_JSON)

def run_market_scan():
    """Run the market temperature scan"""
    from main import scan_market_temperature
    return scan_market_temperature()

def get_crypto_prices():
    """Get crypto prices via yfinance (OKX API blocked by Cloudflare)"""
    try:
        import yfinance as yf
        prices = {}
        for sym in ['BTC-USD', 'ETH-USD', 'SOL-USD']:
            t = yf.Ticker(sym)
            info = t.info
            p = info.get('regularMarketPrice') or info.get('previousClose', 0)
            prices[sym.replace('-USD', '')] = float(p) if p else 0
        return prices
    except:
        return {'BTC': 0, 'ETH': 0, 'SOL': 0}

def get_alpaca_positions():
    """Get Alpaca positions"""
    try:
        from exchange import alpaca_client as alp
        positions = alp.get_positions() or []
        account = alp.get_account() or {}
        return positions, account
    except Exception as e:
        return [], {'error': str(e)}

def check_s4_triggers(scan_result, crypto_prices):
    """Check S4 Batch 2 trigger conditions"""
    fg = 99
    btc_rsi = 50
    btc_price = crypto_prices.get('BTC', 0)
    btc_entry = 67975  # our entry price

    # Parse from scan result
    if isinstance(scan_result, dict):
        fg = scan_result.get('fear_greed') or 99
        btc_rsi = scan_result.get('btc_rsi') or 50

    conditions = {
        'fg_below_10': fg < 10,
        'btc_drop_10pct': btc_price < btc_entry * 0.9 if btc_price > 0 else False,
        'rsi_below_25': btc_rsi < 25,
    }
    triggered = sum(1 for v in conditions.values() if v)

    return {
        'conditions': conditions,
        'triggered_count': triggered,
        'should_execute': triggered >= 2,
        'fear_greed': fg,
        'btc_rsi': btc_rsi,
        'btc_price': btc_price,
    }

def check_stop_losses(positions, crypto_prices):
    """Check if any position hit stop loss"""
    alerts = []

    # Crypto stop losses (15% for BTC/ETH, 15% for SOL)
    crypto_holdings = {
        'BTC': {'entry': 67975, 'stop_pct': 15},
        'ETH': {'entry': 2037, 'stop_pct': 15},
        'SOL': {'entry': 79.84, 'stop_pct': 15},
    }
    for sym, h in crypto_holdings.items():
        price = crypto_prices.get(sym, 0)
        if price > 0:
            pnl_pct = (price - h['entry']) / h['entry'] * 100
            if pnl_pct <= -h['stop_pct']:
                alerts.append(f"🚨 STOP LOSS: {sym} at ${price:.2f} ({pnl_pct:.1f}%)")

    # Alpaca stop losses
    for p in positions:
        pnl_pct = float(p.get('unrealized_plpc', 0)) * 100
        sym = p['symbol']
        stop = -12 if sym == 'VST' else -15
        if pnl_pct <= stop:
            alerts.append(f"🚨 STOP LOSS: {sym} at ${p['current_price']} ({pnl_pct:.1f}%)")

    return alerts

def generate_report(scan_data):
    """Generate human-readable markdown report"""
    lines = [f"# Daily Scan — {TODAY}\n"]
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    m = scan_data.get('market', {})
    lines.append("## Market Temperature")
    lines.append(f"- Crypto: {m.get('crypto_temp', '?')} | BTC ${m.get('btc_price', '?'):,.0f} | F&G {m.get('fear_greed', '?')}")
    lines.append(f"- US: {m.get('us_temp', '?')} | VIX proxy {m.get('vix_proxy', '?')}")
    lines.append(f"- Overall: {m.get('overall_temp', '?')}\n")

    lines.append("## Positions")
    for p in scan_data.get('positions', []):
        pnl = p.get('pnl_pct', 0)
        sign = '+' if pnl >= 0 else ''
        lines.append(f"- {p['symbol']} ({p['platform']}): ${p.get('current_price', '?')} | {sign}{pnl:.1f}%")

    lines.append(f"\n## S4 Batch 2")
    s4 = scan_data.get('s4_check', {})
    lines.append(f"- Triggered: {s4.get('triggered_count', 0)}/3 conditions → {'⚠️ EXECUTE' if s4.get('should_execute') else '❌ Not triggered'}")

    alerts = scan_data.get('alerts', [])
    if alerts:
        lines.append(f"\n## 🚨 ALERTS")
        for a in alerts:
            lines.append(f"- {a}")
    else:
        lines.append(f"\n## Alerts\n- ✅ None")

    return '\n'.join(lines)

def update_dashboard(scan_data):
    """Update dashboard/data.json"""
    try:
        os.system(f'cd "{SCRIPT_DIR}" && python dashboard/generate_data.py')
    except:
        pass  # Dashboard update is best-effort


def append_history(scan_data):
    """Append today's snapshot to dashboard/history.json for equity curve."""
    history_path = os.path.join(SCRIPT_DIR, 'dashboard', 'history.json')
    try:
        if os.path.exists(history_path):
            with open(history_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []

        # Calculate total equity from positions
        total_value = 0
        total_cost = 0
        for p in scan_data.get('positions', []):
            price = p.get('current_price', 0)
            qty = p.get('qty', 0)
            entry = p.get('entry_price', 0)
            if price and qty:
                total_value += price * qty
                total_cost += entry * qty

        # Read dashboard data.json for total capital
        data_json_path = os.path.join(SCRIPT_DIR, 'dashboard', 'data.json')
        total_capital = 0
        if os.path.exists(data_json_path):
            with open(data_json_path, 'r', encoding='utf-8') as f:
                dj = json.load(f)
                total_capital = dj.get('summary', {}).get('total_capital', 0)

        snapshot = {
            'date': TODAY,
            'total_capital': total_capital,
            'invested_value': round(total_value, 2),
            'invested_cost': round(total_cost, 2),
            'unrealized_pnl': round(total_value - total_cost, 2),
            'position_count': len(scan_data.get('positions', [])),
            'crypto_temp': scan_data.get('market', {}).get('crypto_temp', 0),
            'us_temp': scan_data.get('market', {}).get('us_temp', 0),
            'fear_greed': scan_data.get('market', {}).get('fear_greed', 0),
        }

        # Replace if same date already exists, else append
        history = [h for h in history if h.get('date') != TODAY]
        history.append(snapshot)

        # Keep last 365 days
        history = history[-365:]

        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"  History update failed: {e}")


def git_sync():
    """Commit and push scan results to GitHub (best-effort)."""
    try:
        import subprocess
        os.chdir(SCRIPT_DIR)

        # Only add scan outputs + dashboard data (never add .env)
        subprocess.run(['git', 'add',
                        'journal/scans/',
                        'dashboard/data.json',
                        'dashboard/history.json'],
                       capture_output=True, timeout=10)

        # Commit with today's summary
        result = subprocess.run(
            ['git', 'commit', '-m', f'scan: {TODAY} daily update'],
            capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            # Push
            push = subprocess.run(
                ['git', 'push'],
                capture_output=True, text=True, timeout=30)
            if push.returncode == 0:
                print("  Pushed to GitHub ✅")
            else:
                print(f"  Push failed: {push.stderr[:100]}")
        else:
            if 'nothing to commit' in result.stdout:
                print("  No changes to push")
            else:
                print(f"  Commit failed: {result.stderr[:100]}")

    except Exception as e:
        print(f"  Git sync failed: {e}")

def main():
    """Main scan routine"""
    # Skip if already ran today (idempotent)
    if already_ran_today():
        with open(SCAN_JSON, 'r') as f:
            existing = json.load(f)
        print(f"[SKIP] Already scanned today at {existing.get('timestamp', '?')}")
        print(f"Result: {existing.get('summary', 'no summary')}")
        return 0

    print(f"[START] Daily scan for {TODAY}")

    scan_data = {
        'date': TODAY,
        'timestamp': datetime.now().isoformat(),
        'market': {},
        'positions': [],
        's4_check': {},
        'alerts': [],
        'summary': '',
    }

    # 1. Market scan
    print("[1/5] Market temperature...")
    try:
        # Run the existing scan (suppress S4 errors in main.py)
        os.system(f'cd /d "{SCRIPT_DIR}" && python main.py scan 2>NUL')
        # Read latest from DB — crypto and us_stocks are separate rows
        db_path = os.path.join(SCRIPT_DIR, 'journal', 'trades.db')
        conn = sqlite3.connect(db_path)

        crypto_row = conn.execute(
            "SELECT * FROM market_temperature WHERE market='crypto' ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        us_row = conn.execute(
            "SELECT * FROM market_temperature WHERE market='us_stocks' ORDER BY rowid DESC LIMIT 1"
        ).fetchone()

        cols = [d[0] for d in conn.execute("SELECT * FROM market_temperature LIMIT 0").description]

        crypto_temp = 0
        us_temp = 0
        fg = 0
        btc_rsi = 0
        vix_proxy = 0
        btc_price_db = 0

        if crypto_row:
            ct = dict(zip(cols, crypto_row))
            crypto_temp = ct.get('temperature') or 0
            fg = ct.get('crypto_fear_greed') or ct.get('fear_greed') or 0
            btc_rsi = ct.get('rsi_btc') or 0
            # Parse components for BTC price
            try:
                comp = json.loads(ct.get('components') or '{}')
                btc_price_db = comp.get('btc', {}).get('price', 0) or 0
            except:
                pass

        if us_row:
            ut = dict(zip(cols, us_row))
            us_temp = ut.get('temperature') or 0
            try:
                comp = json.loads(ut.get('components') or '{}')
                vix_proxy = comp.get('vix', {}).get('vixy', 0) or 0
            except:
                pass

        scan_data['market'] = {
            'crypto_temp': crypto_temp,
            'us_temp': us_temp,
            'overall_temp': (crypto_temp + us_temp) / 2,
            'fear_greed': fg,
            'btc_price': btc_price_db,
            'btc_rsi': btc_rsi,
            'vix_proxy': vix_proxy,
        }
        conn.close()
    except Exception as e:
        scan_data['market']['error'] = str(e)
        print(f"  Error: {e}")

    # 2. Crypto prices
    print("[2/5] Crypto prices...")
    crypto_prices = get_crypto_prices()
    scan_data['market']['btc_price'] = scan_data['market'].get('btc_price') or crypto_prices.get('BTC', 0)

    # 3. Alpaca positions
    print("[3/5] Alpaca positions...")
    positions, account = get_alpaca_positions()
    for p in positions:
        scan_data['positions'].append({
            'symbol': p['symbol'],
            'platform': 'Alpaca',
            'qty': float(p.get('qty', 0)),
            'avg_price': float(p.get('avg_entry_price', 0)),
            'current_price': float(p.get('current_price', 0)),
            'pnl_pct': float(p.get('unrealized_plpc', 0)) * 100,
            'market_value': float(p.get('market_value', 0)),
        })

    # Add crypto positions
    crypto_holdings = [
        {'symbol': 'BTC', 'qty': 0.044, 'entry': 67975},
        {'symbol': 'ETH', 'qty': 0.7342, 'entry': 2037},
        {'symbol': 'SOL', 'qty': 6.2436, 'entry': 79.84},
    ]
    for h in crypto_holdings:
        price = crypto_prices.get(h['symbol'], 0)
        pnl_pct = (price - h['entry']) / h['entry'] * 100 if price > 0 and h['entry'] > 0 else 0
        scan_data['positions'].append({
            'symbol': h['symbol'],
            'platform': 'OKX Demo',
            'qty': h['qty'],
            'avg_price': h['entry'],
            'current_price': price,
            'pnl_pct': round(pnl_pct, 1),
            'market_value': round(h['qty'] * price, 2),
        })

    # 4. S4 check
    print("[4/5] S4 trigger check...")
    scan_data['s4_check'] = check_s4_triggers(scan_data['market'], crypto_prices)

    # 5. Stop loss check
    print("[5/5] Stop loss check...")
    scan_data['alerts'] = check_stop_losses(positions, crypto_prices)

    # Summary
    fg = scan_data['market'].get('fear_greed', '?')
    ct = scan_data['market'].get('crypto_temp', '?')
    ut = scan_data['market'].get('us_temp', '?')
    n_pos = len(scan_data['positions'])
    n_alerts = len(scan_data['alerts'])
    s4_count = scan_data['s4_check'].get('triggered_count', 0)

    scan_data['summary'] = (
        f"Crypto:{ct} US:{ut} F&G:{fg} | "
        f"{n_pos} positions | "
        f"S4: {s4_count}/3 | "
        f"Alerts: {n_alerts}"
    )

    # Save JSON (atomic — write to temp then rename)
    tmp_path = SCAN_JSON + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(scan_data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, SCAN_JSON)

    # Save markdown report
    report = generate_report(scan_data)
    with open(SCAN_MD, 'w', encoding='utf-8') as f:
        f.write(report)

    # Update dashboard (best-effort)
    print("[+] Updating dashboard...")
    update_dashboard(scan_data)

    # Append to history.json (for equity curve)
    print("[+] Updating history...")
    append_history(scan_data)

    # Git commit + push (best-effort)
    print("[+] Git sync...")
    git_sync()

    print(f"\n[DONE] {scan_data['summary']}")
    if scan_data['alerts']:
        for a in scan_data['alerts']:
            print(f"  {a}")
    if scan_data['s4_check'].get('should_execute'):
        print("  ⚠️ S4 BATCH 2 TRIGGERED — needs confirmation!")

    return 0

if __name__ == '__main__':
    try:
        code = main()
    except Exception as e:
        print(f"[FATAL] {e}")
        import traceback
        traceback.print_exc()
        code = 1
    sys.exit(code)
