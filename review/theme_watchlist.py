"""
Theme Watchlist Scanner
Monitors emerging sector themes: optical networking, space, CPU/processors.
"""
import sys, json
sys.stdout.reconfigure(encoding="utf-8")

import yfinance as yf
import warnings
warnings.filterwarnings("ignore")

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_g / avg_l)), 1)

def calc_sma(closes, period):
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 2)


# ═══════════════════════════════════════════════════════════
#  THEME DEFINITIONS
# ═══════════════════════════════════════════════════════════

THEMES = {
    "光通訊 (Optical Networking)": {
        "thesis": "AI 數據中心之間需要高速互連，800G/1.6T 光模組需求爆發。Leopold L1.5 層：連接 GPU 集群的管道。",
        "tickers": {
            "LITE": "Lumentum (光模組/雷射)",
            "COHR": "Coherent (光通訊元件)",
            "IIVI": "II-VI / Coherent (合併後)",
            "CIEN": "Ciena (光網路設備)",
            "FNSR": "Finisar (被 II-VI 收購，檢查是否還交易)",
            "AAOI": "Applied Optoelectronics (光收發模組)",
            "INFN": "Infinera (光傳輸)",
            "CALX": "Calix (光纖網路)",
        },
        "catalysts": [
            "AI 訓練集群規模擴大 → 800G/1.6T 光模組需求",
            "Meta/Google/Microsoft capex 持續增加",
            "CPO (Co-Packaged Optics) 技術成熟",
            "數據中心互連從電訊號轉光訊號",
        ],
        "risks": [
            "如果 AI capex 放緩，光通訊訂單會最先被砍",
            "中國光模組廠商（中際旭創等）低價競爭",
            "技術轉型風險：CPO 可能淘汰現有插拔式光模組",
        ],
    },
    "太空 (Space Economy)": {
        "thesis": "衛星通訊（Starlink 效應）、太空發射成本下降、國防太空需求增長。長期主題但商業化加速中。",
        "tickers": {
            "RKLB": "Rocket Lab (火箭發射+太空系統)",
            "ASTS": "AST SpaceMobile (衛星直連手機)",
            "LUNR": "Intuitive Machines (月球登陸)",
            "RDW":  "Redwire (太空基礎設施)",
            "SPIR": "Spire Global (衛星數據分析)",
            "BKSY": "BlackSky (地球觀測衛星)",
            "PL":   "Planet Labs (衛星影像)",
            "MNTS": "Momentus (太空運輸)",
            "LMT":  "Lockheed Martin (國防太空)",
            "NOC":  "Northrop Grumman (太空系統)",
            "BA":   "Boeing (太空+衛星)",
            "LHX":  "L3Harris (太空感測器)",
        },
        "catalysts": [
            "Starlink IPO 預期帶動整個板塊",
            "NASA Artemis 計畫推進月球經濟",
            "國防太空預算持續增加",
            "衛星直連手機技術突破（AST, T-Mobile 合作）",
            "太空製造和太空旅遊商業化",
        ],
        "risks": [
            "多數太空公司尚未盈利，燒錢速度快",
            "技術風險高（發射失敗、衛星故障）",
            "Starlink 壟斷效應可能擠壓其他衛星公司",
            "估值泡沫風險 — 太空主題容易過度炒作",
        ],
    },
    "CPU/處理器 (Processors)": {
        "thesis": "AI 推論需求從 GPU 擴展到 CPU 和專用加速器。ARM 架構崛起挑戰 x86。邊緣 AI 需要高效能低功耗晶片。",
        "tickers": {
            "INTC": "Intel (x86 龍頭，轉型中)",
            "AMD":  "AMD (CPU+GPU 雙線)",
            "ARM":  "ARM Holdings (架構授權，手機+數據中心)",
            "QCOM": "Qualcomm (手機+邊緣AI)",
            "MRVL": "Marvell (數據中心晶片/DPU)",
            "AVGO": "Broadcom (定製AI晶片/網路)",
            "NVDA": "NVIDIA (GPU+CPU Grace)",
            "TSM":  "TSMC (代工龍頭)",
            "ASML": "ASML (光刻機壟斷)",
            "MU":   "Micron (HBM 記憶體)",
        },
        "catalysts": [
            "AI 推論成本壓力 → CPU/DPU 協處理器需求",
            "ARM 在數據中心市佔率從 5% → 20%+",
            "Intel 18A/14A 製程若成功 → 估值重估",
            "邊緣 AI（手機、PC、汽車）爆發",
            "HBM (高頻寬記憶體) 供不應求",
        ],
        "risks": [
            "Intel 轉型可能持續失敗 → 價值陷阱",
            "AMD 被 NVIDIA 在 AI 領域持續壓制",
            "ARM 估值太高（P/S > 40x）",
            "半導體週期性下行風險",
            "中美晶片戰升級影響供應鏈",
        ],
    },
}


def scan_theme(theme_name, theme_data):
    """Scan all tickers in a theme."""
    print(f"\n{'═' * 80}")
    print(f"  {theme_name}")
    print(f"  Thesis: {theme_data['thesis'][:80]}...")
    print(f"{'═' * 80}")
    
    results = []
    for ticker, name in theme_data["tickers"].items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="6mo")
            
            if hist.empty or len(hist) < 10:
                print(f"  {ticker:6s} ({name}): no data")
                continue
            
            closes = hist["Close"].tolist()
            highs = hist["High"].tolist()
            lows = hist["Low"].tolist()
            volumes = hist["Volume"].tolist()
            
            price = closes[-1]
            high_6m = max(highs)
            low_6m = min(lows)
            
            rsi = calc_rsi(closes)
            sma20 = calc_sma(closes, 20)
            sma50 = calc_sma(closes, 50)
            
            dist_high = round((price - high_6m) / high_6m * 100, 1)
            dist_low = round((price - low_6m) / low_6m * 100, 1)
            
            chg_5d = round((closes[-1] / closes[-6] - 1) * 100, 1) if len(closes) >= 6 else 0
            chg_20d = round((closes[-1] / closes[-21] - 1) * 100, 1) if len(closes) >= 21 else 0
            chg_60d = round((closes[-1] / closes[-61] - 1) * 100, 1) if len(closes) >= 61 else 0
            
            above_20 = price > sma20 if sma20 else None
            above_50 = price > sma50 if sma50 else None
            
            # Market cap
            info = t.info
            mcap = info.get("marketCap", 0)
            mcap_str = f"${mcap/1e9:.1f}B" if mcap > 1e9 else f"${mcap/1e6:.0f}M" if mcap > 1e6 else "N/A"
            pe = info.get("trailingPE", None)
            pe_str = f"{pe:.1f}" if pe else "N/A"
            
            # Signals
            signals = []
            if rsi and rsi < 30: signals.append("RSI超賣")
            elif rsi and rsi > 70: signals.append("RSI過熱")
            if dist_high > -5 and rsi and rsi > 50: signals.append("接近高點")
            if dist_high < -30: signals.append("深跌")
            elif dist_high < -20: signals.append("大幅回調")
            if above_20 and above_50: signals.append("趨勢強")
            elif above_20 is False and above_50 is False: signals.append("趨勢弱")
            if chg_20d > 15: signals.append("20日強勢")
            
            sig_str = " | ".join(signals) if signals else ""
            
            r = {
                "ticker": ticker, "name": name, "price": price, "mcap": mcap_str,
                "pe": pe_str, "rsi": rsi, "dist_high": dist_high, "dist_low": dist_low,
                "chg_5d": chg_5d, "chg_20d": chg_20d, "chg_60d": chg_60d,
                "above_20": above_20, "above_50": above_50, "signals": signals,
            }
            results.append(r)
            
            print(f"  {ticker:6s} ${price:>10,.2f}  MCap:{mcap_str:>8s}  PE:{pe_str:>6s}  RSI:{rsi or 0:>5.1f}  "
                  f"5d:{chg_5d:>+6.1f}%  20d:{chg_20d:>+6.1f}%  60d:{chg_60d:>+6.1f}%  High:{dist_high:>+6.1f}%  "
                  f"{sig_str}")
            
        except Exception as e:
            print(f"  {ticker:6s} ({name}): ERROR - {e}")
    
    # Theme summary
    if results:
        strong = [r for r in results if r.get("above_20") and r.get("above_50")]
        oversold = [r for r in results if r.get("rsi") and r["rsi"] < 35]
        deep_disc = [r for r in results if r["dist_high"] < -25]
        hot = [r for r in results if r.get("rsi") and r["rsi"] > 65]
        
        print(f"\n  ── Theme Summary ──")
        print(f"  趨勢強勢: {len(strong)}/{len(results)} — {', '.join(r['ticker'] for r in strong)}" if strong else f"  趨勢強勢: 0/{len(results)}")
        print(f"  接近超賣: {len(oversold)} — {', '.join(r['ticker'] for r in oversold)}" if oversold else f"  接近超賣: 0")
        print(f"  深跌>25%: {len(deep_disc)} — {', '.join(r['ticker'] + '(' + str(r['dist_high']) + '%)' for r in deep_disc)}" if deep_disc else f"  深跌>25%: 0")
        print(f"  偏熱RSI>65: {len(hot)} — {', '.join(r['ticker'] for r in hot)}" if hot else f"  偏熱RSI>65: 0")
    
    return results


if __name__ == "__main__":
    print("=" * 80)
    print("  THEME WATCHLIST SCAN")
    print("=" * 80)
    
    all_results = {}
    for theme_name, theme_data in THEMES.items():
        all_results[theme_name] = scan_theme(theme_name, theme_data)
    
    # Cross-theme opportunities
    print(f"\n{'═' * 80}")
    print(f"  CROSS-THEME OPPORTUNITIES")
    print(f"{'═' * 80}")
    
    all_tickers = []
    for theme, results in all_results.items():
        for r in results:
            r["theme"] = theme
            all_tickers.append(r)
    
    # Best setups: above MAs + RSI 50-65 + not too far from high
    momentum = [r for r in all_tickers if r.get("above_20") and r.get("above_50") 
                and r.get("rsi") and 45 < r["rsi"] < 70 and r["dist_high"] > -15]
    if momentum:
        print(f"\n  🟢 MOMENTUM CANDIDATES (Minervini S1 potential):")
        for r in sorted(momentum, key=lambda x: x["chg_20d"], reverse=True):
            print(f"    {r['ticker']:6s} ({r['theme'][:8]}) ${r['price']:,.2f} RSI:{r['rsi']} 20d:{r['chg_20d']:+.1f}% from high:{r['dist_high']:+.1f}%")
    
    # Value: deep discount + improving
    value = [r for r in all_tickers if r["dist_high"] < -25 and r.get("chg_5d") and r["chg_5d"] > 0]
    if value:
        print(f"\n  🟡 VALUE DISCOUNT + IMPROVING:")
        for r in sorted(value, key=lambda x: x["dist_high"]):
            print(f"    {r['ticker']:6s} ({r['theme'][:8]}) ${r['price']:,.2f} RSI:{r['rsi']} from high:{r['dist_high']:+.1f}% 5d:{r['chg_5d']:+.1f}%")
    
    # Oversold bounce candidates
    bounce = [r for r in all_tickers if r.get("rsi") and r["rsi"] < 35]
    if bounce:
        print(f"\n  🔴 OVERSOLD (potential bounce):")
        for r in sorted(bounce, key=lambda x: x["rsi"]):
            print(f"    {r['ticker']:6s} ({r['theme'][:8]}) ${r['price']:,.2f} RSI:{r['rsi']} from high:{r['dist_high']:+.1f}%")
    
    print(f"\n{'═' * 80}")
