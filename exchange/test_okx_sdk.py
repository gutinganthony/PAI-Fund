"""Test OKX using official SDK."""
import os
import sys

# Load env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
config = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            config[key.strip()] = val.strip()

api_key = config["OKX_API_KEY"]
secret_key = config["OKX_SECRET_KEY"]
passphrase = config["OKX_PASSPHRASE"]

try:
    from okx import Account, MarketData, Trade

    # Test with demo flag
    print("=== OKX SDK Test (Demo Trading) ===\n")

    # Market data (public, no auth needed but test SDK path)
    market = MarketData.MarketAPI(flag="1")
    ticker = market.get_ticker(instId="BTC-USDT")
    if ticker and ticker.get("code") == "0":
        t = ticker["data"][0]
        print(f"BTC-USDT: ${t['last']}  (24h: ${t['low24h']} - ${t['high24h']})")
    else:
        print(f"Ticker error: {ticker}")

    # Account (auth required, demo mode)
    account = Account.AccountAPI(api_key, secret_key, passphrase, flag="1", debug=False)
    balance = account.get_account_balance()
    if balance and balance.get("code") == "0":
        print(f"\nDemo Account Balance:")
        for detail in balance["data"][0].get("details", []):
            ccy = detail.get("ccy", "")
            avail = detail.get("availBal", "0")
            if float(avail) > 0:
                print(f"  {ccy}: {avail}")
        if not balance["data"][0].get("details"):
            print("  (empty - may need to add demo funds via OKX app)")
    else:
        print(f"Balance error: {balance}")

except ImportError:
    print("python-okx not installed. Trying pip install...")
    os.system(f"{sys.executable} -m pip install python-okx")
    print("Please re-run this script.")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
