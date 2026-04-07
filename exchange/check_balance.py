"""Quick balance check for both platforms."""
import os, json
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
config = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            config[key.strip()] = val.strip()

# OKX
print("=== OKX Demo Balance ===")
from okx import Account
account = Account.AccountAPI(config["OKX_API_KEY"], config["OKX_SECRET_KEY"], config["OKX_PASSPHRASE"], flag="1", debug=False)
balance = account.get_account_balance()
if balance and balance.get("code") == "0":
    for d in balance["data"][0].get("details", []):
        avail = float(d.get("availBal", 0))
        if avail > 0:
            print(f"  {d['ccy']}: {d['availBal']}")
else:
    print(f"  Error: {balance}")

# Alpaca
print("\n=== Alpaca Paper Balance ===")
from urllib.request import Request, urlopen
req = Request(f"{config['ALPACA_BASE_URL']}/account", headers={
    "APCA-API-KEY-ID": config["ALPACA_API_KEY"],
    "APCA-API-SECRET-KEY": config["ALPACA_SECRET_KEY"],
})
with urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode())
    print(f"  Equity: ${data['equity']}")
    print(f"  Cash: ${data['cash']}")
