#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  PROSPER MOMENTUM SCORECARD — Data Pipeline
═══════════════════════════════════════════════════════════════
  Pulls real market data and outputs JSON for the dashboard.
  
  Data Sources:
    • yfinance  — Stock prices, MAs, indices, VIX, oil, DXY
    • FRED API  — GDP, inflation, employment, yields, spreads
    • Calculated — Trend stages, momentum ranks, breadth
  
  Manual Inputs (update quarterly or as needed):
    • S&P 500 earnings growth, beat rates, margins
    • Put/Call ratio, AAII sentiment
    • Geopolitical risk assessment
  
  Output:
    • scorecard_data.json — Drop-in data file for the React app
  
  How to run:
    python3 prosper_data_pipeline.py
    
  First run takes ~15-20 min for full R3000 universe.
  Subsequent runs with smaller watch list take ~2-3 min.
═══════════════════════════════════════════════════════════════
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf
import pandas as pd
import numpy as np

# ─── CONFIGURATION ───────────────────────────────────────

# Where to save output
OUTPUT_DIR = Path.home() / "StockAnalysis"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "scorecard_data.json"

# How many days of history to pull (need 252+ for 12-month returns)
HISTORY_DAYS = 400

# ─── Tickers to process ─────────────────────────────────
# Option 1: Full R3000 via CSV (slow but comprehensive)
# Option 2: Watch list (fast, good for development)
# Set USE_FULL_UNIVERSE = True once you have tickers.csv ready

USE_FULL_UNIVERSE = False

WATCH_LIST = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO",
    "JPM", "V", "MA", "JNJ", "UNH", "XOM", "HD", "PG", "COST", "PEP",
    "ABBV", "MRK", "AMD", "NFLX", "INTC", "BA", "DIS", "NKE", "CRM",
    "COIN", "PYPL", "SQ", "PLTR", "UBER", "ABNB", "SNOW", "NET",
    "LLY", "WMT", "KO", "MCD", "CAT", "GS", "MS", "BLK", "SCHW",
    "CVX", "SLB", "EOG", "NEE", "SO", "DUK",
]

TICKERS_CSV = Path.home() / "StockAnalysis" / "tickers.csv"

# ─── MANUAL INPUTS (update these periodically) ──────────
# These aren't available via free data feeds.
# Update quarterly after earnings season or as data changes.

MANUAL_INPUTS = {
    "fundamental": {
        "salesGrowth": 4.1,       # S&P 500 YoY sales growth %
        "earningsGrowth": 8.5,    # S&P 500 YoY earnings growth %
        "earningsBeat": 72,       # % of S&P companies beating estimates
        "salesBeat": 64,          # % beating sales estimates
        "revisions": 1.15,        # Up/down revision ratio
        "netMargin": 12.2,        # S&P 500 net margin %
        "marginTrend": "Stable",  # Expanding / Stable / Compressing
        "forwardPE": 21.5,        # S&P 500 forward P/E
        "historicalPE": 17.8,     # 10-year average P/E
        "pegRatio": 1.4,          # Price/Earnings-to-Growth
        "capex": 4.7,             # Capex growth %
        "buybackYield": 2.1,      # % of mkt cap in buybacks
        "divYield": 1.4,          # S&P 500 dividend yield %
        "leverage": 1.6,          # Net Debt / EBITDA
    },
    "sentiment": {
        "putCall": 0.75,          # CBOE Put/Call ratio
        "aaii": 42.5,             # AAII Bull % (weekly survey)
    },
    "geopolitical": {
        "level": "Moderate",
        "description": "Trade policy uncertainty & regional conflicts.",
    },
    "policy": {
        "fiscal": "Supportive",
        "monetary": "Easing",
    }
}


# ═══════════════════════════════════════════════════════════
# STEP 1: LOAD TICKER UNIVERSE
# ═══════════════════════════════════════════════════════════

def load_tickers():
    """Load tickers from CSV or use watch list."""
    if USE_FULL_UNIVERSE and TICKERS_CSV.exists():
        df = pd.read_csv(TICKERS_CSV)
        if 'Symbol' in df.columns:
            tickers = df['Symbol'].tolist()
            print(f"📋 Loaded {len(tickers)} tickers from {TICKERS_CSV}")
            return tickers
        else:
            print(f"⚠️  CSV missing 'Symbol' column, using watch list")
    
    print(f"📋 Using watch list ({len(WATCH_LIST)} tickers)")
    return WATCH_LIST


# ═══════════════════════════════════════════════════════════
# STEP 2: PULL STOCK PRICE DATA (yfinance)
# ═══════════════════════════════════════════════════════════

def pull_stock_data(tickers):
    """Download price history and calculate momentum metrics."""
    print(f"\n📡 Downloading price data for {len(tickers)} stocks...")
    
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=HISTORY_DAYS)).strftime('%Y-%m-%d')
    
    # Batch download (much faster than one-by-one)
    prices = yf.download(tickers, start=start_date, end=end_date,
                         auto_adjust=False, threads=True)['Close']
    
    # Handle single ticker edge case
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(name=tickers[0])
    
    print(f"✅ Downloaded {len(prices)} trading days")
    
    stocks = []
    skipped = []
    
    for i, ticker in enumerate(tickers):
        if (i + 1) % 50 == 0:
            print(f"   Processing {i+1}/{len(tickers)}...")
        
        try:
            if ticker not in prices.columns:
                skipped.append({"ticker": ticker, "reason": "No price data"})
                continue
            
            px = prices[ticker].dropna()
            
            if len(px) < 252:
                skipped.append({"ticker": ticker, "reason": f"Only {len(px)} days"})
                continue
            
            # ── Core calculations ──
            ma = px.rolling(150).mean()
            ma_current = ma.iloc[-1]
            ma_2mo_ago = ma.iloc[-42] if len(px) > 42 else np.nan
            price_now = px.iloc[-1]
            price_12m = px.iloc[-252]
            price_1m = px.iloc[-21] if len(px) > 21 else np.nan
            
            # Trend classification (Vernon's methodology)
            if pd.isna(ma_2mo_ago) or pd.isna(ma_current):
                trend = "Unknown"
            else:
                ma_rising = ma_current > ma_2mo_ago
                above_ma = price_now > ma_current
                
                if ma_rising and above_ma:
                    trend = "Uptrend"
                elif ma_rising and not above_ma:
                    trend = "Pullback"
                elif not ma_rising and above_ma:
                    trend = "Snapback"
                else:
                    trend = "Downtrend"
            
            # 12-month return (momentum factor)
            ret_12m = (price_now / price_12m - 1) * 100
            
            # % over/under 150-day MA
            pct_vs_ma = (price_now / ma_current - 1) * 100 if not pd.isna(ma_current) else 0
            
            # Get company info (sector, industry, name, market cap)
            # Note: This is the slowest part — yfinance makes individual API calls
            try:
                info = yf.Ticker(ticker).info
                company = info.get('longName', info.get('shortName', ticker))
                sector = info.get('sector', 'Unknown')
                industry = info.get('industry', 'Unknown')
                mktcap = info.get('marketCap', 0)
            except:
                company = ticker
                sector = "Unknown"
                industry = "Unknown"
                mktcap = 0
            
            stocks.append({
                "ticker": ticker,
                "company": company,
                "sector": sector,
                "industry": industry,
                "price": round(float(price_now), 2),
                "mktCap": round(mktcap / 1e6),  # in millions
                "trend": trend,
                "pctOver150": round(float(pct_vs_ma), 1),
                "ret12m": round(float(ret_12m), 1),
                "price12m": round(float(price_12m), 2),
                "price1m": round(float(price_1m), 2) if not pd.isna(price_1m) else None,
                "ma150": round(float(ma_current), 2),
                "ma150_2mo": round(float(ma_2mo_ago), 2) if not pd.isna(ma_2mo_ago) else None,
                "maRising": bool(ma_current > ma_2mo_ago) if not pd.isna(ma_2mo_ago) else None,
            })
            
        except Exception as e:
            skipped.append({"ticker": ticker, "reason": str(e)})
    
    # ── Percentile ranking across universe ──
    if stocks:
        returns = [s["ret12m"] for s in stocks if s["ret12m"] is not None]
        for s in stocks:
            if s["ret12m"] is not None:
                rank = sum(1 for r in returns if r <= s["ret12m"]) / len(returns) * 100
                s["relMomRank"] = round(rank)
                s["tier"] = min(10, max(1, 11 - int(rank / 10)))
            else:
                s["relMomRank"] = 0
                s["tier"] = 10
    
    print(f"✅ Processed {len(stocks)} stocks, skipped {len(skipped)}")
    return stocks, skipped


# ═══════════════════════════════════════════════════════════
# STEP 3: PULL MARKET-LEVEL DATA (yfinance)
# ═══════════════════════════════════════════════════════════

def pull_market_data():
    """Pull index prices, VIX, oil, yields from yfinance."""
    print(f"\n📡 Pulling market-level data...")
    
    market = {}
    
    # ── Indices ──
    indices = {
        "^GSPC": ("sp500", "S&P 500"),
        "^RUA": ("r3k", "Russell 3000"),
        "^VIX": ("vix", "VIX"),
        "CL=F": ("oil", "WTI Crude"),
        "DX-Y.NYB": ("dxy", "US Dollar Index"),
    }
    
    for symbol, (key, label) in indices.items():
        try:
            hist = yf.Ticker(symbol).history(period="1y")
            if not hist.empty:
                px = hist['Close']
                market[key] = {
                    "price": round(float(px.iloc[-1]), 2),
                    "history": [round(float(v), 2) for v in px.tail(20).values],
                }
                
                # Calculate MAs for indices
                if len(px) >= 150:
                    market[key]["ma150"] = round(float(px.rolling(150).mean().iloc[-1]), 2)
                
                print(f"  ✅ {label}: {market[key]['price']}")
            else:
                print(f"  ❌ {label}: No data")
        except Exception as e:
            print(f"  ❌ {label}: {e}")
    
    # ── S&P 500 long-term MA (need more history) ──
    try:
        sp_long = yf.Ticker("^GSPC").history(period="5y")
        if not sp_long.empty and len(sp_long) >= 1000:
            # 4-year MA ≈ 1000 trading days
            market["sp500"]["ma4yr"] = round(float(
                sp_long['Close'].rolling(1000).mean().iloc[-1]
            ), 2)
            print(f"  ✅ S&P 500 4yr MA: {market['sp500']['ma4yr']}")
    except Exception as e:
        print(f"  ❌ S&P 500 4yr MA: {e}")
    
    return market


# ═══════════════════════════════════════════════════════════
# STEP 4: PULL MACRO DATA (FRED)
# ═══════════════════════════════════════════════════════════

def pull_fred_data():
    """Pull macro economic data from FRED using fredapi."""
    print(f"\n📡 Pulling FRED macro data...")
    
    macro = {}
    
    try:
        from fredapi import Fred
        
        api_key = os.environ.get("FRED_API_KEY", "")
        if not api_key:
            print("  ⚠️  No FRED_API_KEY found.")
            print("  FRED data will use fallback values from manual inputs.")
            return {}
        
        fred = Fred(api_key=api_key)
        print(f"  ✅ FRED API connected")
        
        series = {
            "UNRATE":          ("employment",    "Unemployment Rate"),
            "CPIAUCSL":        ("cpi_index",     "CPI Index"),
            "DFF":             ("fedFunds",      "Fed Funds Rate"),
            "DGS10":           ("tenYear",       "10-Year Yield"),
            "DGS2":            ("twoYear",       "2-Year Yield"),
            "BAMLH0A0HYM2":   ("hySpread",      "HY OAS Spread"),
            "BAMLC0A4CBBB":   ("igSpread",      "IG Spread"),
            "UMCSENT":         ("sentiment",     "Consumer Sentiment"),
            "MORTGAGE30US":    ("mortgage",       "30Y Mortgage Rate"),
            "ICSA":            ("joblessClaims",  "Initial Claims"),
            "A191RL1Q225SBEA": ("gdp",           "Real GDP Growth"),
            "CES0500000003":   ("wageGrowth_raw","Avg Hourly Earnings"),
            "GASREGW":         ("gasPrice",      "Regular Gas Price"),
        }
        
        for code, (key, label) in series.items():
            try:
                data = fred.get_series(code).dropna()
                if len(data) == 0:
                    print(f"  ❌ {label} ({code}): No data")
                    continue
                val = data.iloc[-1]
                history = [round(float(v), 2) for v in data.tail(7).values]
                macro[key] = {
                    "value": round(float(val), 2),
                    "history": history,
                    "asOf": str(data.index[-1].date()),
                }
                print(f"  ✅ {label}: {macro[key]['value']}")
            except Exception as e:
                print(f"  ❌ {label} ({code}): {e}")
        
        if "cpi_index" in macro:
            try:
                cpi = fred.get_series("CPIAUCSL").dropna()
                if len(cpi) >= 13:
                    latest = cpi.iloc[-1]
                    year_ago = cpi.iloc[-13]
                    inflation = (latest / year_ago - 1) * 100
                    macro["inflation"] = {
                        "value": round(inflation, 1),
                        "history": [],
                        "asOf": str(cpi.index[-1].date()),
                    }
                    print(f"  ✅ CPI Inflation (YoY): {macro['inflation']['value']}%")
            except Exception as e:
                print(f"  ❌ Inflation calc: {e}")
        
        return macro
        
    except ImportError:
        print("  ⚠️  fredapi not installed")
        print("  Install: pip3 install fredapi")
        return {}


# ═══════════════════════════════════════════════════════════
# STEP 5: CALCULATE BREADTH AND SECTOR SUMMARIES
# ═══════════════════════════════════════════════════════════

def calculate_summaries(stocks):
    """Calculate breadth, sector breakdowns, and market signals."""
    print(f"\n📊 Calculating summaries...")
    
    valid = [s for s in stocks if s["trend"] != "Unknown"]
    total = len(valid)
    
    if total == 0:
        return {}, []
    
    # ── Breadth ──
    above_ma = sum(1 for s in valid if s["pctOver150"] > 0)
    breadth_pct = round(above_ma / total * 100, 1)
    
    # ── Trend distribution ──
    trends = {"Uptrend": 0, "Pullback": 0, "Downtrend": 0, "Snapback": 0}
    for s in valid:
        if s["trend"] in trends:
            trends[s["trend"]] += 1
    
    trend_pcts = {k: round(v / total * 100, 1) for k, v in trends.items()}
    
    # ── Sector breakdown ──
    sectors = {}
    for s in valid:
        sec = s["sector"]
        if sec == "Unknown":
            continue
        if sec not in sectors:
            sectors[sec] = {"name": sec, "stocks": [], "n": 0,
                           "Uptrend": 0, "Pullback": 0, "Downtrend": 0, "Snapback": 0}
        sectors[sec]["stocks"].append(s["ticker"])
        sectors[sec]["n"] += 1
        if s["trend"] in sectors[sec]:
            sectors[sec][s["trend"]] += 1
    
    sector_list = []
    for sec_data in sectors.values():
        n = sec_data["n"]
        if n == 0:
            continue
        
        # Calculate relative momentum (avg rank for sector)
        sec_stocks = [s for s in valid if s["sector"] == sec_data["name"]]
        avg_mom = np.mean([s["relMomRank"] for s in sec_stocks]) if sec_stocks else 50
        
        sector_list.append({
            "name": sec_data["name"],
            "n": n,
            "up": round(sec_data["Uptrend"] / n * 100, 1),
            "pb": round(sec_data["Pullback"] / n * 100, 1),
            "dn": round(sec_data["Downtrend"] / n * 100, 1),
            "sb": round(sec_data["Snapback"] / n * 100, 1),
            "rm": round(avg_mom, 1),
        })
    
    sector_list.sort(key=lambda x: x["up"], reverse=True)
    
    breadth = {
        "pctAbove": breadth_pct,
        "totalStocks": total,
        "trends": trend_pcts,
    }
    
    print(f"  Breadth: {breadth_pct}% above 150-day MA")
    print(f"  Uptrend: {trend_pcts.get('Uptrend', 0)}% | "
          f"Pullback: {trend_pcts.get('Pullback', 0)}% | "
          f"Downtrend: {trend_pcts.get('Downtrend', 0)}% | "
          f"Snapback: {trend_pcts.get('Snapback', 0)}%")
    print(f"  Sectors: {len(sector_list)}")
    
    return breadth, sector_list


# ═══════════════════════════════════════════════════════════
# STEP 6: DETERMINE OVERALL MARKET SIGNALS
# ═══════════════════════════════════════════════════════════

def calculate_signals(market, breadth, macro):
    """Compute the Health Score and overall market assessment."""
    print(f"\n🎯 Calculating Health Score...")
    
    checks = []
    
    def add(passed, category, label, weight=5):
        checks.append({
            "pass": passed,
            "cat": category,
            "label": label,
            "weight": weight
        })
    
    # ── Macro checks ──
    emp = macro.get("employment", {}).get("value", 4.4)
    gdp = macro.get("gdp", {}).get("value", 2.9)
    inf = macro.get("inflation", {}).get("value", 2.7)
    hy = macro.get("hySpread", {}).get("value", 3.15)
    sent = macro.get("sentiment", {}).get("value", 74.5)
    mtg = macro.get("mortgage", {}).get("value", 6.65)
    
    add(emp < 5.0, "Macro", f"Labor Market Strong (Unemp {emp}% < 5%)")
    add(gdp > 2.0, "Macro", f"GDP Growth Solid ({gdp}% > 2%)")
    add(inf < 3.0, "Macro", f"Inflation Contained ({inf}% < 3%)")
    add(hy < 4.0, "Macro", f"Credit Markets Calm (HY {hy}% < 4%)")
    add(sent > 70, "Macro", f"Consumer Confident ({sent} > 70)")
    add(mtg < 6.0, "Macro", f"Mortgage Rates Affordable ({mtg}% < 6%)")
    
    # ── Fundamental checks ──
    f = MANUAL_INPUTS["fundamental"]
    add(f["earningsGrowth"] > 5.0, "Fundamental", f"Earnings Growing ({f['earningsGrowth']}% > 5%)")
    add(f["netMargin"] > 11.0, "Fundamental", f"Margins Healthy ({f['netMargin']}% > 11%)")
    add(f["revisions"] > 1.0, "Fundamental", f"Revisions Positive ({f['revisions']}x > 1.0)")
    add(f["forwardPE"] < 20.0, "Fundamental", f"Valuation Reasonable (P/E {f['forwardPE']} < 20)")
    fcf_ok = f.get("fcfYield", 3.8) if isinstance(f.get("fcfYield"), (int, float)) else 3.8
    add(fcf_ok > 3.5, "Fundamental", f"Free Cash Flow Healthy ({fcf_ok}% > 3.5%)")
    
    # ── Technical checks ──
    sp = market.get("sp500", {})
    sp_price = sp.get("price", 0)
    sp_ma4yr = sp.get("ma4yr", 0)
    sp_ma150 = sp.get("ma150", 0)
    b_pct = breadth.get("pctAbove", 58)
    vix_val = market.get("vix", {}).get("price", 15)
    
    add(sp_price > sp_ma4yr and sp_ma4yr > 0, "Technical",
        f"Long-Term Uptrend (S&P {sp_price} > 4yr MA {sp_ma4yr})", weight=10)
    add(sp_price > sp_ma150 and sp_ma150 > 0, "Technical",
        f"Medium-Term Uptrend (S&P {sp_price} > 150d MA {sp_ma150})")
    add(b_pct > 60, "Technical",
        f"Broad Participation (Breadth {b_pct}% > 60%)", weight=10)
    add(vix_val < 20, "Technical",
        f"Low Volatility (VIX {vix_val} < 20)")
    pc = MANUAL_INPUTS["sentiment"]["putCall"]
    add(pc < 1.0, "Technical",
        f"Sentiment Supportive (P/C {pc} < 1.0)")
    
    score = sum(c["weight"] for c in checks if c["pass"])
    total = sum(c["weight"] for c in checks)
    wins = [c for c in checks if c["pass"]]
    misses = [c for c in checks if not c["pass"]]
    
    pct = score / total * 100 if total > 0 else 0
    if pct >= 80:
        label = "Bullish"
        overall = "Positive"
    elif pct >= 60:
        label = "Cautiously Optimistic"
        overall = "Neutral"
    elif pct >= 40:
        label = "Cautious"
        overall = "Neutral"
    else:
        label = "Defensive"
        overall = "Negative"
    
    print(f"  Health Score: {score}/{total} ({pct:.0f}%) — {label}")
    print(f"  Tailwinds: {len(wins)} | Headwinds: {len(misses)}")
    
    return {
        "score": score,
        "total": total,
        "label": label,
        "overall": overall,
        "wins": [{"label": w["label"], "weight": w["weight"], "cat": w["cat"]} for w in wins],
        "misses": [{"label": m["label"], "weight": m["weight"], "cat": m["cat"]} for m in misses],
    }


# ═══════════════════════════════════════════════════════════
# STEP 7: ASSEMBLE AND SAVE
# ═══════════════════════════════════════════════════════════

def assemble_output(stocks, market, macro, breadth, sectors, signals):
    """Package everything into the JSON structure the dashboard expects."""
    
    # Determine trend status
    sp = market.get("sp500", {})
    r3k = market.get("r3k", {})
    
    r3k_above = "Above" if r3k.get("price", 0) > r3k.get("ma150", float('inf')) else "Below"
    
    ten_yr = macro.get("tenYear", {}).get("value", MANUAL_INPUTS.get("tenYear", 4.45))
    two_yr = macro.get("twoYear", {}).get("value", MANUAL_INPUTS.get("twoYear", 3.90))
    if isinstance(ten_yr, dict): ten_yr = ten_yr.get("value", 4.45)
    if isinstance(two_yr, dict): two_yr = two_yr.get("value", 3.90)
    
    output = {
        "_generated": datetime.now().isoformat(),
        "_source": "Prosper Momentum Scorecard Data Pipeline",
        "_stocks_count": len(stocks),
        
        "market": {
            "date": datetime.today().strftime("%-m/%-d/%y"),
            "overallScore": signals["overall"],
            "healthScore": signals["score"],
            "healthTotal": signals["total"],
            "healthLabel": signals["label"],
            "healthWins": signals["wins"],
            "healthMisses": signals["misses"],
            
            "trend": {
                "score": signals["overall"],
                "r3kVs150MA": r3k_above,
                "maSlope": "Positive" if r3k.get("price", 0) > r3k.get("ma150", 0) else "Negative",
            },
            
            "breadth": {
                "pctAbove": breadth.get("pctAbove", 0),
                "r3kPrice": r3k.get("price", 0),
                "r3kMA150": r3k.get("ma150", 0),
            },
            
            "macro": {
                "gdp": macro.get("gdp", {}).get("value", MANUAL_INPUTS.get("gdp", 2.9)),
                "employment": macro.get("employment", {}).get("value", 4.4),
                "inflation": macro.get("inflation", {}).get("value", 2.7),
                "sentiment": macro.get("sentiment", {}).get("value", 74.5),
                "fedFunds": macro.get("fedFunds", {}).get("value", 3.64),
                "tenYear": ten_yr if isinstance(ten_yr, (int, float)) else 4.45,
                "twoYear": two_yr if isinstance(two_yr, (int, float)) else 3.90,
                "hySpread": macro.get("hySpread", {}).get("value", 3.15),
                "igSpread": macro.get("igSpread", {}).get("value", 0.92),
                "oil": market.get("oil", {}).get("price", 71.50),
                "dxy": market.get("dxy", {}).get("price", 102.4),
                "mortgage": macro.get("mortgage", {}).get("value", 6.65),
                "gasPrice": macro.get("gasPrice", {}).get("value", 3.12),
                "joblessClaims": macro.get("joblessClaims", {}).get("value", 218),
                "fiscalPolicy": MANUAL_INPUTS["policy"]["fiscal"],
                "monetaryPolicy": MANUAL_INPUTS["policy"]["monetary"],
                "geopolitical": MANUAL_INPUTS["geopolitical"]["level"],
            },
            
            "fundamental": MANUAL_INPUTS["fundamental"],
            
            "technical": {
                "sp500": sp.get("price", 0),
                "sp500MA4yr": sp.get("ma4yr", 0),
                "sp500MA150": sp.get("ma150", 0),
                "vix": market.get("vix", {}).get("price", 15),
                "putCall": MANUAL_INPUTS["sentiment"]["putCall"],
                "aaii": MANUAL_INPUTS["sentiment"]["aaii"],
            },
            
            "synthesis": {
                "equities": {"view": "Overweight" if signals["score"] >= 70 else "Neutral" if signals["score"] >= 50 else "Underweight"},
                "fixedIncome": {"view": "Neutral"},
                "cash": {"view": "Underweight" if signals["score"] >= 60 else "Neutral"},
            },
        },
        
        "sectors": sectors,
        
        "stocks": [{
            "t": s["ticker"],
            "co": s["company"],
            "sec": s["sector"],
            "ind": s["industry"],
            "px": s["price"],
            "mc": s["mktCap"],
            "tr": s["trend"],
            "rm": s["relMomRank"],
            "ti": s["tier"],
            "ov": s["pctOver150"],
            "p12": s["price12m"],
            "p1": s["price1m"],
        } for s in sorted(stocks, key=lambda x: x.get("mktCap", 0), reverse=True)],
        
        "skipped": len([s for s in stocks if s["trend"] == "Unknown"]),
    }
    
    return output


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    print("═" * 60)
    print("  PROSPER MOMENTUM SCORECARD — Data Pipeline")
    print(f"  {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
    print("═" * 60)
    
    start_time = time.time()
    
    # 1. Load tickers
    tickers = load_tickers()
    
    # 2. Pull stock data
    stocks, skipped = pull_stock_data(tickers)
    
    # 3. Pull market data
    market = pull_market_data()
    
    # 4. Pull FRED data
    macro = pull_fred_data()
    
    # 5. Calculate summaries
    breadth, sectors = calculate_summaries(stocks)
    
    # 6. Calculate signals
    signals = calculate_signals(market, breadth, macro)
    
    # 7. Assemble and save
    output = assemble_output(stocks, market, macro, breadth, sectors, signals)
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    elapsed = time.time() - start_time
    
    print(f"\n{'═'*60}")
    print(f"  ✅ COMPLETE — {elapsed:.0f} seconds")
    print(f"  📁 Saved to: {OUTPUT_FILE}")
    print(f"  📊 Stocks: {len(stocks)} processed, {len(skipped)} skipped")
    print(f"  🎯 Health Score: {signals['score']}/{signals['total']}")
    print(f"{'═'*60}")
    print(f"\n  Next: Copy scorecard_data.json into your React app")


if __name__ == "__main__":
    main()
