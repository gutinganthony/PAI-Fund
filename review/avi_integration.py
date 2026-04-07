"""
AVI 3.0 Integration for Trading System
Runs AVI engine and feeds results into market temperature + strategy decisions.
"""
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")

# Add AVI project to path
AVI_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "avi-backtest")
sys.path.insert(0, AVI_PATH)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def run_avi():
    """Run AVI 3.0 and return latest score with breakdown."""
    try:
        from avi_data_collector import collect_all_indicators
        from avi_engine import get_latest_avi, interpret_avi, AVI_DIMENSIONS
        
        print("Fetching AVI 3.0 indicators (12 indicators, 5 dimensions)...")
        indicators = collect_all_indicators()
        
        result = get_latest_avi(indicators)
        if not result:
            return {"error": "Could not calculate AVI"}
        
        print(f"\n{'=' * 70}")
        print(f"  AVI 3.0 MARKET RISK INDEX")
        print(f"  Date: {result['date']}  |  Coverage: {result['data_coverage']}%")
        print(f"{'=' * 70}")
        print(f"\n  📊 AVI Score: {result['avi_score']} / 10.0")
        print(f"  📋 {interpret_avi(result['avi_score'])}")
        
        # Dimension breakdown
        print(f"\n  {'─' * 60}")
        print(f"  DIMENSION BREAKDOWN")
        print(f"  {'─' * 60}")
        for dim_name in AVI_DIMENSIONS:
            dim = result["dimensions"].get(dim_name, {})
            score = dim.get("score", 0)
            max_score = dim.get("max_possible", 1)
            pct = dim.get("pct_of_max", 0)
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            color = "🔴" if pct > 70 else "🟡" if pct > 40 else "🟢"
            print(f"  {color} {dim_name:4s}: {score:.2f}/{max_score:.2f} ({pct:.0f}%) {bar}")
        
        # Top risk indicators
        print(f"\n  {'─' * 60}")
        print(f"  TOP RISK CONTRIBUTORS")
        print(f"  {'─' * 60}")
        
        sorted_indicators = sorted(
            result["indicators"].items(),
            key=lambda x: x[1].get("weighted_contribution", 0) or 0,
            reverse=True
        )
        for name, ind in sorted_indicators[:5]:
            pctile = ind.get("percentile")
            raw = ind.get("raw_value")
            contrib = ind.get("weighted_contribution", 0)
            label = ind.get("label", name)
            if pctile is not None:
                print(f"  {label:30s}: pctile={pctile:5.1f}%  raw={raw}  contrib={contrib:.3f}")
        
        # Strategy implications
        print(f"\n  {'─' * 60}")
        print(f"  STRATEGY IMPLICATIONS")
        print(f"  {'─' * 60}")
        
        avi = result["avi_score"]
        val_pct = result["dimensions"].get("估值", {}).get("pct_of_max", 50)
        credit_pct = result["dimensions"].get("信用", {}).get("pct_of_max", 50)
        macro_pct = result["dimensions"].get("宏觀", {}).get("pct_of_max", 50)
        momentum_pct = result["dimensions"].get("動量", {}).get("pct_of_max", 50)
        
        # Overall positioning
        if avi >= 7.0:
            print(f"  🔴 DEFENSIVE: AVI={avi} — 大幅降低風險敞口")
            print(f"     建議總倉位 < 20%，增持現金和防禦性資產")
        elif avi >= 6.0:
            print(f"  🟠 CAUTIOUS: AVI={avi} — 謹慎操作，不追高")
            print(f"     建議總倉位 30-50%，避免加倉高估值資產")
        elif avi >= 5.0:
            print(f"  🟡 NEUTRAL-HIGH: AVI={avi} — 正常配置但留意變化")
            print(f"     建議總倉位 50-70%，關注 AVI 趨勢方向")
        elif avi >= 4.0:
            print(f"  🟢 NEUTRAL: AVI={avi} — 估值合理，正常投資")
            print(f"     建議總倉位 60-80%")
        elif avi >= 3.0:
            print(f"  🟢 FAVORABLE: AVI={avi} — 偏低估，潛在買入機會")
            print(f"     建議總倉位 70-90%，積極尋找標的")
        else:
            print(f"  🔵 STRONG BUY: AVI={avi} — 歷史性低估，積極佈局")
            print(f"     建議總倉位 80-100%")
        
        # Dimension-specific insights
        if val_pct > 80 and credit_pct < 30:
            print(f"\n  ⚠️ 估值高({val_pct:.0f}%) + 信用健康({credit_pct:.0f}%)")
            print(f"     估值有壓力但不是系統性危機，可選擇性佈局低估個股")
        
        if val_pct > 80 and credit_pct > 60:
            print(f"\n  🚨 估值高({val_pct:.0f}%) + 信用惡化({credit_pct:.0f}%)")
            print(f"     多重壓力同時出現，這是 2007 式的危險信號！")
        
        if macro_pct > 60:
            print(f"\n  ⚠️ 宏觀壓力偏高({macro_pct:.0f}%)")
            print(f"     VIX/金融壓力升高，短期波動可能加大")
        
        if momentum_pct < 30:
            print(f"\n  ℹ️ 動量偏低({momentum_pct:.0f}%) — 市場已回調")
            print(f"     部分風險已釋放，如果其他維度健康，可能是好的進場時機")
        
        print(f"\n{'=' * 70}")
        
        return result
        
    except ImportError as e:
        print(f"Cannot import AVI modules: {e}")
        print(f"AVI path: {AVI_PATH}")
        return {"error": str(e)}
    except Exception as e:
        import traceback
        print(f"AVI Error: {e}")
        traceback.print_exc()
        return {"error": str(e)}


if __name__ == "__main__":
    result = run_avi()
    if "error" not in result:
        # Save to journal
        try:
            from journal.trade_journal import init_db, record_temperature
            init_db()
            record_temperature(
                market="us_stocks_avi",
                temperature=result["avi_score"] * 10,  # Convert 0-10 to 0-100 scale
                components=json.dumps({
                    "avi_score": result["avi_score"],
                    "dimensions": result["dimensions"],
                    "date": result["date"],
                }),
                action=f"AVI={result['avi_score']}"
            )
            print("\n✅ AVI score recorded to journal.")
        except Exception as e:
            print(f"\n⚠️ Could not save to journal: {e}")
