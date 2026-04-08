#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  PROSPER MOMENTUM SCORECARD — Data Feed Diagnostic
═══════════════════════════════════════════════════════════════
  Run this FIRST to see which feeds work on your machine.
  
  What it tests:
    1. yfinance — stock prices, moving averages, VIX, oil, etc.
    2. FRED API — GDP, inflation, employment, yields, spreads
    3. iShares CSVs — R3000 universe constituents
  
  How to run:
    Option A: Double-click this file (if .command version exists)
    Option B: Open Terminal, type: python3 test_feeds.py
    
  No API keys needed for yfinance.
  FRED requires a free key — get one at https://fred.stlouisfed.org/docs/api/api_key.html
  (takes 30 seconds, completely free)
═══════════════════════════════════════════════════════════════
"""

import sys
import time
from datetime import datetime, timedelta

# ─── Helper ───
def test(name, func):
    """Run a test and report pass/fail with timing."""
    print(f"\n{'─'*60}")
    print(f"  Testing: {name}")
    print(f"{'─'*60}")
    start = time.time()
    try:
        result = func()
        elapsed = time.time() - start
        print(f"  ✅ PASS  ({elapsed:.1f}s)")
        return {"name": name, "status": "PASS", "time": elapsed, "data": result}
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ❌ FAIL  ({elapsed:.1f}s)")
        print(f"  Error: {e}")
        return {"name": name, "status": "FAIL", "time": elapsed, "error": str(e)}

results = []

# ═══════════════════════════════════════════════════════════
# TEST 1: yfinance — Can we import it?
# ═══════════════════════════════════════════════════════════
def test_yfinance_import():
    import yfinance as yf
    print(f"  yfinance version: {yf.__version__}")
    return True

results.append(test("yfinance import", test_yfinance_import))

# ═══════════════════════════════════════════════════════════
# TEST 2: yfinance — Single stock price + moving average
# ═══════════════════════════════════════════════════════════
def test_single_stock():
    import yfinance as yf
    import pandas as pd
    
    ticker = yf.Ticker("AAPL")
    hist = ticker.history(period="1y")
    
    if hist.empty:
        raise Exception("No price data returned for AAPL")
    
    price = hist['Close'].iloc[-1]
    ma150 = hist['Close'].rolling(150).mean().iloc[-1]
    
    print(f"  AAPL Last Close: ${price:.2f}")
    print(f"  AAPL 150-day MA: ${ma150:.2f}")
    print(f"  Above MA: {'Yes ✓' if price > ma150 else 'No ✗'}")
    print(f"  Data points: {len(hist)}")
    
    return {"price": price, "ma150": ma150}

results.append(test("Single stock (AAPL)", test_single_stock))

# ═══════════════════════════════════════════════════════════
# TEST 3: yfinance — Batch download (10 stocks)
# ═══════════════════════════════════════════════════════════
def test_batch_download():
    import yfinance as yf
    
    tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", 
               "META", "TSLA", "JPM", "JNJ", "XOM"]
    
    end = datetime.today().strftime('%Y-%m-%d')
    start = (datetime.today() - timedelta(days=400)).strftime('%Y-%m-%d')
    
    data = yf.download(tickers, start=start, end=end, 
                       auto_adjust=False, threads=True)['Close']
    
    print(f"  Downloaded {len(data.columns)} tickers")
    print(f"  Date range: {data.index[0].date()} to {data.index[-1].date()}")
    print(f"  Trading days: {len(data)}")
    
    # Check for gaps
    for t in tickers:
        valid = data[t].dropna()
        print(f"  {t}: {len(valid)} days, last=${valid.iloc[-1]:.2f}")
    
    return {"tickers": len(data.columns), "days": len(data)}

results.append(test("Batch download (10 stocks)", test_batch_download))

# ═══════════════════════════════════════════════════════════
# TEST 4: yfinance — Stock info (sector, industry, name)
# ═══════════════════════════════════════════════════════════
def test_stock_info():
    import yfinance as yf
    
    ticker = yf.Ticker("NVDA")
    info = ticker.info
    
    name = info.get('longName', 'Unknown')
    sector = info.get('sector', 'Unknown')
    industry = info.get('industry', 'Unknown')
    mktcap = info.get('marketCap', 0)
    
    print(f"  Name: {name}")
    print(f"  Sector: {sector}")
    print(f"  Industry: {industry}")
    print(f"  Market Cap: ${mktcap/1e9:.1f}B")
    
    if name == 'Unknown' or sector == 'Unknown':
        raise Exception("Info fields returned Unknown — may be rate-limited")
    
    return {"name": name, "sector": sector}

results.append(test("Stock info (NVDA)", test_stock_info))

# ═══════════════════════════════════════════════════════════
# TEST 5: yfinance — Market indices and indicators
# ═══════════════════════════════════════════════════════════
def test_market_data():
    import yfinance as yf
    
    tests = {
        "^GSPC": "S&P 500",
        "^VIX": "VIX",
        "^RUA": "Russell 3000",
        "CL=F": "WTI Crude Oil",
        "DX-Y.NYB": "US Dollar Index",
        "^TNX": "10-Year Yield",
        "^IRX": "13-Week T-Bill",
        "^FVX": "5-Year Yield",
        "^TYX": "30-Year Yield",
    }
    
    successes = 0
    for symbol, label in tests.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="5d")
            if not hist.empty:
                val = hist['Close'].iloc[-1]
                print(f"  ✅ {label} ({symbol}): {val:.2f}")
                successes += 1
            else:
                print(f"  ❌ {label} ({symbol}): No data")
        except Exception as e:
            print(f"  ❌ {label} ({symbol}): {e}")
    
    print(f"\n  {successes}/{len(tests)} market feeds working")
    return {"working": successes, "total": len(tests)}

results.append(test("Market indices & indicators", test_market_data))

# ═══════════════════════════════════════════════════════════
# TEST 6: yfinance — Put/Call and sentiment proxies
# ═══════════════════════════════════════════════════════════
def test_sentiment():
    import yfinance as yf
    
    # CBOE Put/Call ratio isn't directly in yfinance
    # But we can get VIX and use AAII as manual input
    vix = yf.Ticker("^VIX").history(period="5d")
    
    if vix.empty:
        raise Exception("VIX data unavailable")
    
    vix_val = vix['Close'].iloc[-1]
    print(f"  VIX: {vix_val:.2f}")
    print(f"  Note: Put/Call ratio not available via yfinance")
    print(f"  Note: AAII sentiment requires manual input or scraping")
    print(f"  Recommendation: VIX available ✓, Put/Call and AAII = manual")
    
    return {"vix": vix_val}

results.append(test("Sentiment data", test_sentiment))

# ═══════════════════════════════════════════════════════════
# TEST 7: FRED API — Macro economic data
# ═══════════════════════════════════════════════════════════
def test_fred():
    """
    FRED is the Federal Reserve Economic Data portal.
    It requires a free API key. Get one here:
    https://fred.stlouisfed.org/docs/api/api_key.html
    
    For this test, we try pandas_datareader first (no key needed
    for some access), then fall back to fredapi.
    """
    # Try pandas_datareader (simpler, sometimes works without key)
    try:
        import pandas_datareader.data as web
        
        end = datetime.today()
        start = end - timedelta(days=365*2)
        
        series = {
            "GDP": "Real GDP (Quarterly)",
            "UNRATE": "Unemployment Rate",
            "CPIAUCSL": "CPI (All Urban)",
            "DFF": "Fed Funds Rate",
            "DGS10": "10-Year Treasury",
            "DGS2": "2-Year Treasury",
            "BAMLH0A0HYM2": "HY OAS Spread",
            "UMCSENT": "Consumer Sentiment",
            "MORTGAGE30US": "30Y Mortgage Rate",
        }
        
        successes = 0
        for code, label in series.items():
            try:
                df = web.DataReader(code, "fred", start, end)
                val = df.dropna().iloc[-1, 0]
                print(f"  ✅ {label} ({code}): {val:.2f}")
                successes += 1
            except Exception as e:
                print(f"  ❌ {label} ({code}): {e}")
        
        print(f"\n  {successes}/{len(series)} FRED series working")
        return {"method": "pandas_datareader", "working": successes}
        
    except ImportError:
        print("  pandas_datareader not installed.")
        print("  Install with: pip3 install pandas-datareader")
        print("")
        
        # Try fredapi
        try:
            from fredapi import Fred
            print("  fredapi is installed. Checking for API key...")
            print("  ⚠️  FRED requires a free API key.")
            print("  Get one at: https://fred.stlouisfed.org/docs/api/api_key.html")
            print("  Then set: export FRED_API_KEY=your_key_here")
            
            import os
            key = os.environ.get("FRED_API_KEY", "")
            if key:
                fred = Fred(api_key=key)
                gdp = fred.get_series("GDP")
                print(f"  ✅ GDP latest: {gdp.dropna().iloc[-1]:.1f}")
                return {"method": "fredapi", "working": True}
            else:
                print("  No FRED_API_KEY found in environment.")
                return {"method": "fredapi", "working": False, "note": "Need API key"}
                
        except ImportError:
            print("  fredapi not installed either.")
            print("  Install with: pip3 install fredapi")
            raise Exception("Neither pandas_datareader nor fredapi available")

results.append(test("FRED macro data", test_fred))

# ═══════════════════════════════════════════════════════════
# TEST 8: iShares ETF Holdings (R3000 universe proxy)
# ═══════════════════════════════════════════════════════════
def test_ishares():
    """
    iShares publishes daily holdings CSVs for their ETFs.
    IWV = iShares Russell 3000 ETF (our universe proxy).
    
    This tests if we can download the holdings file.
    """
    import urllib.request
    import csv
    import io
    
    url = "https://www.ishares.com/us/products/239714/ishares-russell-3000-etf/1467271812596.ajax?fileType=csv&fileName=IWV_holdings&dataType=fund"
    
    print(f"  Attempting to download IWV holdings...")
    
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
    })
    
    response = urllib.request.urlopen(req, timeout=15)
    content = response.read().decode('utf-8')
    
    # iShares CSVs have header rows before the actual data
    lines = content.split('\n')
    
    # Find the header row (usually contains "Ticker" or "Name")
    data_start = 0
    for i, line in enumerate(lines):
        if 'Ticker' in line or 'ticker' in line.lower():
            data_start = i
            break
    
    if data_start == 0:
        # Try to count non-empty lines
        non_empty = [l for l in lines if l.strip()]
        print(f"  Downloaded {len(non_empty)} lines")
        print(f"  First 3 lines: {lines[:3]}")
        print(f"  ⚠️  Couldn't parse structure — may need manual inspection")
        return {"lines": len(non_empty), "parsed": False}
    
    reader = csv.DictReader(lines[data_start:])
    tickers = []
    for row in reader:
        t = row.get('Ticker', row.get('ticker', ''))
        if t and t != '-' and len(t) < 8:
            tickers.append(t)
    
    print(f"  ✅ Found {len(tickers)} tickers in IWV holdings")
    if tickers:
        print(f"  Sample: {', '.join(tickers[:10])}...")
    
    return {"tickers": len(tickers)}

results.append(test("iShares ETF holdings (IWV)", test_ishares))

# ═══════════════════════════════════════════════════════════
# TEST 9: Trend Classification (the math)
# ═══════════════════════════════════════════════════════════
def test_trend_calc():
    """
    Test the four-stage trend classification on real data.
    This is Vernon's core methodology — we need this to be right.
    """
    import yfinance as yf
    import pandas as pd
    
    tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "COIN"]
    
    end = datetime.today().strftime('%Y-%m-%d')
    start = (datetime.today() - timedelta(days=400)).strftime('%Y-%m-%d')
    
    data = yf.download(tickers, start=start, end=end,
                       auto_adjust=False, threads=True)['Close']
    
    for t in tickers:
        prices = data[t].dropna()
        if len(prices) < 192:  # 150 + 42 days
            print(f"  {t}: Not enough data ({len(prices)} days)")
            continue
        
        ma = prices.rolling(150).mean()
        ma_current = ma.iloc[-1]
        ma_2mo_ago = ma.iloc[-42]
        price = prices.iloc[-1]
        
        # Four-stage classification
        ma_rising = ma_current > ma_2mo_ago
        above_ma = price > ma_current
        
        if ma_rising and above_ma:
            stage = "Uptrend"
        elif ma_rising and not above_ma:
            stage = "Pullback"
        elif not ma_rising and above_ma:
            stage = "Snapback"
        else:
            stage = "Downtrend"
        
        pct_vs_ma = (price / ma_current - 1) * 100
        
        print(f"  {t}: ${price:.2f} | MA150=${ma_current:.2f} | "
              f"{'↑' if ma_rising else '↓'} slope | "
              f"{pct_vs_ma:+.1f}% vs MA | → {stage}")
    
    return True

results.append(test("Trend classification (math)", test_trend_calc))

# ═══════════════════════════════════════════════════════════
# TEST 10: Full momentum rank (percentile ranking)
# ═══════════════════════════════════════════════════════════
def test_momentum_rank():
    """
    Test the 12-minus-1 month return calculation and percentile ranking.
    """
    import yfinance as yf
    import pandas as pd
    
    tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN",
               "META", "TSLA", "JPM", "JNJ", "XOM"]
    
    end = datetime.today().strftime('%Y-%m-%d')
    start = (datetime.today() - timedelta(days=400)).strftime('%Y-%m-%d')
    
    data = yf.download(tickers, start=start, end=end,
                       auto_adjust=False, threads=True)['Close']
    
    returns = {}
    for t in tickers:
        prices = data[t].dropna()
        if len(prices) >= 252:
            ret_12m = (prices.iloc[-1] / prices.iloc[-252] - 1) * 100
            returns[t] = ret_12m
    
    # Percentile rank
    import numpy as np
    vals = list(returns.values())
    for t, ret in sorted(returns.items(), key=lambda x: x[1], reverse=True):
        rank = sum(1 for v in vals if v <= ret) / len(vals) * 100
        tier = min(10, max(1, 11 - int(rank / 10)))
        print(f"  {t}: {ret:+.1f}% (12m) | Rank: {rank:.0f}th pctl | Tier: {tier}")
    
    return {"ranked": len(returns)}

results.append(test("Momentum ranking", test_momentum_rank))


# ═══════════════════════════════════════════════════════════
# RESULTS SUMMARY
# ═══════════════════════════════════════════════════════════

print(f"\n{'═'*60}")
print(f"  DIAGNOSTIC RESULTS SUMMARY")
print(f"{'═'*60}")

passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")

for r in results:
    icon = "✅" if r["status"] == "PASS" else "❌"
    print(f"  {icon} {r['name']} ({r['time']:.1f}s)")

print(f"\n  {passed} passed, {failed} failed out of {len(results)} tests")
print(f"{'═'*60}")

if failed > 0:
    print(f"\n  FAILED TESTS — What to do:")
    for r in results:
        if r["status"] == "FAIL":
            name = r["name"]
            if "yfinance" in name.lower():
                print(f"  • {name}: Run 'pip3 install yfinance'")
            elif "fred" in name.lower():
                print(f"  • {name}: Run 'pip3 install pandas-datareader fredapi'")
                print(f"    Then get a free API key at https://fred.stlouisfed.org/docs/api/api_key.html")
            elif "ishares" in name.lower():
                print(f"  • {name}: May be blocked by firewall or iShares changed URL")
            else:
                print(f"  • {name}: {r.get('error', 'Unknown error')}")

print(f"\n  Next step: Run prosper_data_pipeline.py to generate dashboard data")
print(f"{'═'*60}")
