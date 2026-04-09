"""
Execute S2 Value Trade: MSFT (Half Position)
Strategy: S2 Value Undervalued (Buffett + 段永平 + Lynch)
"""
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from urllib.request import Request, urlopen

# Load config
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
config = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            config[key.strip()] = val.strip()

BASE = config["ALPACA_BASE_URL"]
HEADERS = {
    "APCA-API-KEY-ID": config["ALPACA_API_KEY"],
    "APCA-API-SECRET-KEY": config["ALPACA_SECRET_KEY"],
    "Content-Type": "application/json",
}

def alpaca_request(method, path, data=None):
    body = json.dumps(data).encode() if data else None
    req = Request(f"{BASE}{path}", data=body, headers=HEADERS, method=method)
    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main():
    print("=" * 60)
    print("  S2 VALUE TRADE: MSFT")
    print("=" * 60)

    # Check account
    acct = alpaca_request("GET", "/account")
    cash = float(acct["cash"])
    equity = float(acct["equity"])
    print(f"\n  Account Equity: ${equity:,.2f}")
    print(f"  Available Cash: ${cash:,.2f}")

    # S2 allocation: 20% of equity = strategy budget
    # Half position for initial entry
    s2_budget = equity * 0.20
    half_position = s2_budget * 0.50
    print(f"\n  S2 Budget (20%): ${s2_budget:,.2f}")
    print(f"  Half Position (50%): ${half_position:,.2f}")

    # Cap at $9,500 for MSFT initial
    trade_amount = min(half_position, 9500)
    print(f"  Trade Amount: ${trade_amount:,.2f}")

    # Place market order (notional = dollar amount)
    print(f"\n  Placing MSFT market order for ${trade_amount:,.2f}...")
    order = alpaca_request("POST", "/orders", {
        "symbol": "MSFT",
        "notional": str(round(trade_amount, 2)),
        "side": "buy",
        "type": "market",
        "time_in_force": "day",
    })

    print(f"\n  ✅ Order Placed!")
    print(f"  Order ID: {order['id']}")
    print(f"  Symbol: {order['symbol']}")
    print(f"  Notional: ${float(order.get('notional', 0)):,.2f}")
    print(f"  Status: {order['status']}")
    print(f"  Side: {order['side']}")
    print(f"  Type: {order['type']}")

    # Record in journal
    try:
        from journal.trade_journal import init_db, record_entry
        init_db()
        record_entry(
            symbol="MSFT",
            side="buy",
            strategy="S2-value-undervalued",
            exchange="alpaca_paper",
            entry_price=374.33,  # Will be updated after fill
            quantity=round(trade_amount / 374.33, 4),
            notional=trade_amount,
            notes=(
                "S2 Value Trade (Half Position). "
                "段永平三問全過: 好生意(OP Margin 47%, FCF $53.6B) + 好文化(Nadella) + 好價格(Fwd PE 19.9). "
                "Buffett: ROE 34.4%, Gross Margin 68.6%, 護城河(轉換成本+網路效應+品牌). "
                "Marks 第二層: Earnings +60% 但股價 -32%, 恐懼 > 實際基本面惡化. "
                f"AVI=5.67 估值高但信用健康. 54 analysts Strong Buy, target $587 (+57%)."
            ),
            stop_loss=374.33 * 0.85,  # -15% hard stop
        )
        print(f"\n  ✅ Recorded in trade journal")
    except Exception as e:
        print(f"\n  ⚠️ Journal error: {e}")

    # 2-minute story (Lynch/S2 requirement)
    print(f"\n{'─' * 60}")
    print(f"  📖 2-MINUTE STORY")
    print(f"{'─' * 60}")
    print(f"  標的：MSFT")
    print(f"  分類：穩定成長（Stalwart）")
    print(f"  一句話：地球上最好的軟體生意之一，被 AI capex 焦慮打了七折")
    print(f"  護城河：轉換成本(Office/Azure) + 網路效應(GitHub/LinkedIn) + 品牌")
    print(f"  Fwd PE：19.9 vs 歷史均值 ~30")
    print(f"  最大風險：AI 資本支出持續擴大但變現不及預期，壓縮利潤率")
    print(f"  加倉條件：下季財報確認 Azure AI 營收加速 → 加到全倉")
    print(f"  停損：-15% hard stop ($318) 或 ROE < 12% 連續兩季")
    print(f"{'─' * 60}")


if __name__ == "__main__":
    main()
