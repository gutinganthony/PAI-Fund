"""Test basic connectivity to OKX and Alpaca APIs."""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

def test_okx():
    print("=== OKX Connectivity Test ===")
    
    # Test 1: Public endpoint (no auth needed)
    urls = [
        ("OKX Public Ticker", "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT"),
        ("OKX Public Time", "https://www.okx.com/api/v5/public/time"),
    ]
    
    for name, url in urls:
        try:
            req = Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            })
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                print(f"  {name}: OK - {json.dumps(data)[:150]}")
        except HTTPError as e:
            print(f"  {name}: HTTP {e.code} - {e.read().decode()[:100]}")
        except Exception as e:
            print(f"  {name}: FAIL - {e}")

def test_alpaca():
    print("\n=== Alpaca Paper Trading Test ===")
    
    import os
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    config = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip()
    
    api_key = config.get("ALPACA_API_KEY", "")
    secret_key = config.get("ALPACA_SECRET_KEY", "")
    base_url = config.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets/v2")
    
    # Test 1: Account info
    try:
        req = Request(f"{base_url}/account", headers={
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "Accept": "application/json",
        })
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            print(f"  Account Status: {data.get('status', 'unknown')}")
            print(f"  Equity: ${data.get('equity', '0')}")
            print(f"  Cash: ${data.get('cash', '0')}")
            print(f"  Buying Power: ${data.get('buying_power', '0')}")
            print(f"  Currency: {data.get('currency', 'USD')}")
    except HTTPError as e:
        print(f"  Account: HTTP {e.code} - {e.read().decode()[:200]}")
    except Exception as e:
        print(f"  Account: FAIL - {e}")
    
    # Test 2: Get AAPL quote
    try:
        # Use data API for market data
        data_url = "https://data.alpaca.markets/v2/stocks/AAPL/quotes/latest"
        req = Request(data_url, headers={
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "Accept": "application/json",
        })
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            quote = data.get("quote", data)
            print(f"\n  AAPL Latest Quote:")
            print(f"    Ask: ${quote.get('ap', 'N/A')}  Bid: ${quote.get('bp', 'N/A')}")
    except HTTPError as e:
        print(f"  AAPL Quote: HTTP {e.code} - {e.read().decode()[:200]}")
    except Exception as e:
        print(f"  AAPL Quote: FAIL - {e}")

if __name__ == "__main__":
    test_okx()
    test_alpaca()
