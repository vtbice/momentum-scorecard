#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  PROSPER MOMENTUM SCORECARD — Data Pipeline
═══════════════════════════════════════════════════════════════
  Pulls real market data and outputs JSON for the dashboard.
  
  Automated Data Sources:
    • yfinance       — Stock prices, MAs, indices, VIX, oil, DXY, div yield
    • FRED API       — GDP, inflation, employment, yields, spreads, PMI
    • SEC EDGAR      — Trailing fundamentals (earnings/revenue growth, margins, leverage, capex)
    • CBOE CSV       — Put/Call ratio (daily)
    • Nasdaq Data    — AAII sentiment survey (weekly)
    • DataHub.io     — Trailing P/E ratio (monthly)
    • Calculated     — Trend stages, momentum ranks, breadth, pullbacks

  *Manual Inputs (update quarterly or as needed):
    • Forward P/E, PEG ratio, analyst revisions (FactSet)
    • Earnings/sales beat rates (FactSet Earnings Insight)
    • FCF yield, buyback yield (FactSet)
    • Geopolitical risk, fiscal/monetary policy stance
  
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

# Load API keys from .env file (keeps secrets out of the code)
_ENV_FILE = Path(__file__).parent / ".env"
if _ENV_FILE.exists():
    with open(_ENV_FILE) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                os.environ.setdefault(_key.strip(), _val.strip())

# ─── CONFIGURATION ───────────────────────────────────────

# Where to save output
OUTPUT_DIR = Path(__file__).parent
OUTPUT_FILE = OUTPUT_DIR / "scorecard_data.json"
SKIPPED_HISTORY_FILE = OUTPUT_DIR / "skipped_history.json"
REMOVAL_THRESHOLD_DAYS = 5  # Flag for removal after N consecutive skipped days
HISTORICAL_CSV = Path(__file__).parent.parent / "Market Study" / "SP500_Daily_March4_1957_Present.csv"

# How many days of history to pull (need 252+ for 12-month returns)
HISTORY_DAYS = 400

# ─── API KEYS ────────────────────────────────────────────
# Nasdaq Data Link (formerly Quandl) — free tier, used for AAII sentiment
NASDAQ_DATA_LINK_KEY = os.environ.get("NASDAQ_DATA_LINK_KEY", "")

# ─── Tickers to process ─────────────────────────────────
# Option 1: Full R3000 via CSV (slow but comprehensive)
# Option 2: Watch list (fast, good for development)
# Set USE_FULL_UNIVERSE = True once you have tickers.csv ready

USE_FULL_UNIVERSE = True

WATCH_LIST = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO",
    "JPM", "V", "MA", "JNJ", "UNH", "XOM", "HD", "PG", "COST", "PEP",
    "ABBV", "MRK", "AMD", "NFLX", "INTC", "BA", "DIS", "NKE", "CRM",
    "COIN", "PYPL", "XYZ", "PLTR", "UBER", "ABNB", "SNOW", "NET",
    "LLY", "WMT", "KO", "MCD", "CAT", "GS", "MS", "BLK", "SCHW",
    "CVX", "SLB", "EOG", "NEE", "SO", "DUK",
]

TICKERS_CSV = Path(__file__).parent / "tickers.csv"

# ─── OVERSOLD / CAPITULATION INDICATORS ─────────────────
# These are capitulation signals watched during corrections.
# Each indicator stands on its own — any single signal firing
# is meaningful and should be displayed on the dashboard.
#
# 1. Breadth Washout: % of watchlist stocks above their
#    20-day SMA drops below 20% → oversold
# 2. New Lows Spike: 50%+ of watchlist stocks making
#    20-day lows → oversold
# 3. Put/Call Spike: CBOE Composite Put/Call Ratio above
#    1.2 → fear is extreme, oversold
# 4. VIX Spike: VIX above 30 → panic territory, oversold
# ─────────────────────────────────────────────────────────
OVERSOLD_THRESHOLDS = {
    "breadth_washout": 20,   # % above 20-day SMA threshold
    "new_lows_spike": 50,    # % making 20-day lows threshold
    "put_call_spike": 1.2,   # Put/Call ratio threshold
    "vix_spike": 30,         # VIX threshold
}

# ─── MANUAL INPUTS (fallback values) ─────────────────────
# These serve as fallbacks when auto-fetch fails.
#
# NOW AUTO-FETCHED (SEC EDGAR overrides when available):
#   • earningsGrowth, salesGrowth, netMargin, marginTrend, leverage, capex
# NOW AUTO-FETCHED (other sources):
#   • divYield (yfinance), putCall (CBOE), aaii (Nasdaq Data Link)
#
# STILL MANUAL (FactSet / analyst data only):
#   • forwardPE, revisions, pegRatio, earningsBeat, salesBeat,
#     fcfYield, buybackYield, historicalPE
#   • geopolitical, fiscal/monetary policy

MANUAL_INPUTS = {
    # ── Last updated: March 25, 2026 ──
    # Sources: FactSet Earnings Insight, Schwab, FRED, Multpl, S&P Global
    "fundamental": {
        # ── Auto-overridden by EDGAR when available (these are fallbacks) ──
        "salesGrowth": 8.2,       # S&P 500 Q4 2025 blended revenue growth %
        "earningsGrowth": 11.9,   # S&P 500 Q4 2025 blended EPS growth %
        "netMargin": 13.2,        # S&P 500 net margin % (Q1 2026 est, FactSet)
        "marginTrend": "Stable",  # 13.2% vs 13.3% prior Q — essentially flat
        "leverage": 1.7,          # Net Debt / EBITDA (corporate re-leveraging trend)
        "capex": 6.0,             # Capex growth % (accelerating, AI-driven)
        # ── Still manual — requires FactSet / analyst data ──
        "earningsBeat": 76,       # % of S&P companies beating estimates (Q4 2025)
        "salesBeat": 66,          # % beating sales estimates (Q4 2025)
        "revisions": 1.05,        # Up/down revision ratio (Q1 2026 ests down only 1% vs 1.6% avg)
        "forwardPE": 20.3,        # S&P 500 forward 12-mo P/E (FactSet, Mar 2026)
        "historicalPE": 18.9,     # 10-year average P/E (FactSet)
        "pegRatio": 1.2,          # ~20.3 PE / ~16.3% expected growth
        "fcfYield": 3.5,          # S&P 500 free cash flow yield %
        "buybackYield": 2.2,      # % of mkt cap in buybacks ($1T+ annualized)
        "divYield": 1.2,          # S&P 500 dividend yield % — auto-overridden by yfinance
        "_lastUpdated": "2026-03-25",  # Track when fundamentals were last manually updated
    },
    "sentiment": {
        "putCall": 0.90,          # Fallback CBOE Total Put/Call ratio
        "aaii": 30.4,             # Fallback AAII Bull %
    },
    "geopolitical": {
        "level": "Elevated",
        "description": "Tariff escalation (20-32% on China), US-China trade tensions, and global supply-chain disruption.",
    },
    "policy": {
        "fiscal": "Supportive",
        "monetary": "Paused",     # Fed held steady Mar 18, 2026 — projects 1 cut this year
    }
}


# ═══════════════════════════════════════════════════════════
# AUTO-FETCH: SENTIMENT & VALUATION DATA
# ═══════════════════════════════════════════════════════════

def fetch_cboe_putcall():
    """Fetch latest CBOE Total Put/Call ratio from CBOE's free CSV feed."""
    print("\n📡 Fetching CBOE Put/Call ratio...")
    try:
        # CBOE publishes daily total put/call ratios as a CSV
        url = "https://cdn.cboe.com/resources/options/totalpc.csv"
        df = pd.read_csv(url, skiprows=2)
        # Clean column names
        df.columns = [c.strip() for c in df.columns]
        # The CSV has columns: TRADE_DATE, TOTAL_CALL_VOLUME, TOTAL_PUT_VOLUME, TOTAL_PC_RATIO (or similar)
        # Find the ratio column
        ratio_col = [c for c in df.columns if 'ratio' in c.lower() or 'p/c' in c.lower()]
        date_col = [c for c in df.columns if 'date' in c.lower()]

        if ratio_col and date_col:
            latest = df.iloc[-1]
            ratio = float(latest[ratio_col[0]])
            date_str = str(latest[date_col[0]]).strip()
            # Try to parse date into ISO format
            for fmt in ('%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y'):
                try:
                    date_parsed = datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
                    break
                except ValueError:
                    date_parsed = date_str
            print(f"  ✅ CBOE Put/Call: {ratio:.2f} (as of {date_parsed})")
            return {"value": round(ratio, 2), "asOf": date_parsed, "source": "CBOE"}
        else:
            # Try alternative column structure
            # Some CBOE files just have numeric columns
            last_row = df.iloc[-1]
            for col in df.columns:
                try:
                    val = float(last_row[col])
                    if 0.3 < val < 2.5:  # Reasonable put/call range
                        print(f"  ✅ CBOE Put/Call: {val:.2f} (from column '{col}')")
                        return {"value": round(val, 2), "asOf": datetime.today().strftime('%Y-%m-%d'), "source": "CBOE"}
                except (ValueError, TypeError):
                    continue
            print(f"  ⚠️  CBOE CSV columns not recognized: {df.columns.tolist()}")
            return None
    except Exception as e:
        print(f"  ⚠️  CBOE fetch failed: {e}")
        # Try equity put/call as backup
        try:
            url2 = "https://cdn.cboe.com/resources/options/equitypc.csv"
            df2 = pd.read_csv(url2, skiprows=2)
            df2.columns = [c.strip() for c in df2.columns]
            ratio_col = [c for c in df2.columns if 'ratio' in c.lower() or 'p/c' in c.lower()]
            if ratio_col:
                ratio = float(df2.iloc[-1][ratio_col[0]])
                print(f"  ✅ CBOE Equity P/C (backup): {ratio:.2f}")
                return {"value": round(ratio, 2), "asOf": datetime.today().strftime('%Y-%m-%d'), "source": "CBOE-equity"}
        except Exception as e2:
            print(f"  ⚠️  CBOE backup also failed: {e2}")
        return None


def fetch_aaii_sentiment():
    """Fetch latest AAII Bull/Bear sentiment from free sources."""
    print("\n📡 Fetching AAII sentiment...")

    # Method 1: Try Nasdaq Data Link (formerly Quandl) — free with API key
    try:
        ndl_key = NASDAQ_DATA_LINK_KEY
        if ndl_key:
            url = f"https://data.nasdaq.com/api/v3/datasets/AAII/AAII_SENTIMENT.json?api_key={ndl_key}&rows=1"
            import urllib.request
            import json as _json
            req = urllib.request.urlopen(url, timeout=15)
            data = _json.loads(req.read())
            cols = data['dataset']['column_names']
            vals = data['dataset']['data'][0]
            row = dict(zip(cols, vals))
            bull_pct = float(row.get('Bullish', row.get('Bull', 0))) * 100
            date_str = row.get('Date', datetime.today().strftime('%Y-%m-%d'))
            print(f"  ✅ AAII Bull: {bull_pct:.1f}% (as of {date_str}) [Nasdaq Data Link]")
            return {"value": round(bull_pct, 1), "asOf": date_str, "source": "NasdaqDataLink"}
    except Exception as e:
        print(f"  ⚠️  Nasdaq Data Link failed: {e}")

    # Method 2: Try yfinance-based proxy (AAII data sometimes accessible via ticker symbols)
    try:
        # Check if there's a recent cached value we can use
        if OUTPUT_FILE.exists():
            with open(OUTPUT_FILE) as f:
                existing = json.load(f)
            existing_aaii = existing.get("market", {}).get("technical", {}).get("aaii", 0)
            existing_date = existing.get("market", {}).get("dataAsOf", {}).get("aaii", "")
            if existing_aaii > 0 and existing_date:
                days_old = (datetime.today() - datetime.strptime(existing_date, '%Y-%m-%d')).days
                if days_old <= 10:  # AAII updates weekly, keep if less than 10 days old
                    print(f"  ✅ AAII Bull: {existing_aaii:.1f}% (cached, {days_old} days old)")
                    return {"value": existing_aaii, "asOf": existing_date, "source": "cached"}
    except Exception as e:
        print(f"  ⚠️  Cache check failed: {e}")

    print(f"  ⚠️  AAII auto-fetch unavailable — using manual fallback ({MANUAL_INPUTS['sentiment']['aaii']}%)")
    return None


def fetch_trailing_pe():
    """Fetch trailing P/E ratio from DataHub.io's free S&P 500 dataset."""
    print("\n📡 Fetching S&P 500 trailing P/E...")
    try:
        url = "https://datahub.io/core/s-and-p-500/r/data.csv"
        df = pd.read_csv(url)
        # Dataset has columns: Date, SP500, Dividend, Earnings, CPI, etc.
        df = df.dropna(subset=['SP500', 'Earnings'])
        # Trailing PE = Price / (sum of last 4 quarters of earnings)
        # The dataset has monthly earnings, multiply by 12 for annual approximation
        latest = df.iloc[-1]
        price = float(latest['SP500'])
        earnings = float(latest['Earnings'])
        if earnings > 0:
            trailing_pe = round(price / earnings, 1)
            date_str = str(latest['Date'])[:10]
            print(f"  ✅ Trailing P/E: {trailing_pe} (as of {date_str})")
            return {"trailingPE": trailing_pe, "asOf": date_str, "source": "DataHub"}
        else:
            print(f"  ⚠️  Earnings data is zero or negative")
            return None
    except Exception as e:
        print(f"  ⚠️  DataHub fetch failed: {e}")
        return None


def fetch_dividend_yield():
    """Fetch S&P 500 dividend yield from yfinance (already available)."""
    print("\n📡 Fetching S&P 500 dividend yield from yfinance...")
    try:
        spy = yf.Ticker("SPY")
        info = spy.info
        div_yield = info.get("dividendYield", info.get("trailingAnnualDividendYield", None))
        if div_yield and div_yield > 0:
            # yfinance is inconsistent: sometimes returns decimal (0.0114 = 1.14%),
            # sometimes returns percentage already (1.14 = 1.14%). Normalize it.
            div_pct = div_yield * 100 if div_yield < 0.5 else div_yield
            # Sanity check: S&P 500 dividend yield should be 0.5% - 6% historically
            if div_pct < 0.1 or div_pct > 10:
                print(f"  ⚠️  Dividend yield out of range ({div_pct}%), using fallback")
                return None
            div_pct = round(div_pct, 2)
            print(f"  ✅ Dividend Yield: {div_pct}%")
            return {"value": div_pct, "asOf": datetime.today().strftime('%Y-%m-%d'), "source": "yfinance"}
    except Exception as e:
        print(f"  ⚠️  Dividend yield fetch failed: {e}")
    return None


# ═══════════════════════════════════════════════════════════
# AUTO-FETCH: SEC EDGAR TRAILING FUNDAMENTALS
# ═══════════════════════════════════════════════════════════
# Uses the free XBRL Frames API — no API key needed.
# Fetches aggregate S&P 500 fundamentals: earnings growth,
# revenue growth, net margins, leverage, capex growth.
# Cannot provide: forward P/E, analyst revisions, beat rates.
# ═══════════════════════════════════════════════════════════

# SEC requires a User-Agent header identifying the requester
SEC_HEADERS = {
    "User-Agent": "ProsperMomentumScorecard vtbice@gmail.com",
    "Accept-Encoding": "gzip, deflate",
}

# S&P 500 large-cap CIKs we know — used as a quick filter when
# the full ticker→CIK mapping isn't available.  Top ~50 by weight.
SP500_KNOWN_CIKS = None  # Populated lazily by _load_cik_map()

_CIK_MAP_CACHE = None  # ticker → CIK, loaded once


def _load_cik_map():
    """Download SEC's company_tickers.json and build ticker → CIK mapping."""
    global _CIK_MAP_CACHE
    if _CIK_MAP_CACHE is not None:
        return _CIK_MAP_CACHE

    import urllib.request
    import json as _json

    url = "https://www.sec.gov/files/company_tickers.json"
    req = urllib.request.Request(url, headers=SEC_HEADERS)
    resp = urllib.request.urlopen(req, timeout=15)
    data = _json.loads(resp.read())

    # data is {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc"}, ...}
    cik_map = {}
    for entry in data.values():
        ticker = entry.get("ticker", "").upper()
        cik = entry.get("cik_str")
        if ticker and cik:
            cik_map[ticker] = int(cik)

    _CIK_MAP_CACHE = cik_map
    return cik_map


def _get_sp500_ciks():
    """Get CIK numbers for our S&P 500 universe."""
    cik_map = _load_cik_map()

    # Use the full ticker universe if tickers.csv exists, else use watch list
    if USE_FULL_UNIVERSE and TICKERS_CSV.exists():
        try:
            df = pd.read_csv(TICKERS_CSV)
            if 'Symbol' in df.columns:
                tickers = df['Symbol'].tolist()
            else:
                tickers = WATCH_LIST
        except Exception:
            tickers = WATCH_LIST
    else:
        tickers = WATCH_LIST

    ciks = set()
    for t in tickers:
        t_upper = t.upper().strip()
        if t_upper in cik_map:
            ciks.add(cik_map[t_upper])

    return ciks


def _fetch_xbrl_frame(concept, unit="USD", period="CY2025Q4", instant=False):
    """
    Fetch one XBRL frame from SEC EDGAR.

    Args:
        concept: XBRL concept name (e.g., 'Revenues', 'NetIncomeLoss')
        unit: 'USD' or 'USD-per-shares'
        period: e.g. 'CY2025Q4' for Q4 2025
        instant: if True, append 'I' for balance-sheet (point-in-time) items

    Returns:
        list of dicts with 'cik' and 'val' keys, or empty list on failure.
    """
    import urllib.request
    import json as _json

    suffix = "I" if instant else ""
    url = f"https://data.sec.gov/api/xbrl/frames/us-gaap/{concept}/{unit}/{period}{suffix}.json"

    try:
        req = urllib.request.Request(url, headers=SEC_HEADERS)
        resp = urllib.request.urlopen(req, timeout=20)
        data = _json.loads(resp.read())
        return data.get("data", [])
    except Exception as e:
        # Try without 'I' suffix if instant failed (some concepts vary)
        if instant:
            try:
                url2 = f"https://data.sec.gov/api/xbrl/frames/us-gaap/{concept}/{unit}/{period}.json"
                req2 = urllib.request.Request(url2, headers=SEC_HEADERS)
                resp2 = urllib.request.urlopen(req2, timeout=20)
                data2 = _json.loads(resp2.read())
                return data2.get("data", [])
            except Exception:
                pass
        return []


def _aggregate_for_sp500(frame_data, sp500_ciks):
    """Filter frame data to S&P 500 companies and sum their values."""
    total = 0.0
    count = 0
    for row in frame_data:
        cik = row.get("cik")
        val = row.get("val", 0)
        if cik in sp500_ciks and val is not None:
            total += float(val)
            count += 1
    return total, count


def _quarter_str(year, quarter):
    """Build XBRL period string like 'CY2025Q4'."""
    return f"CY{year}Q{quarter}"


def _current_and_prior_quarters():
    """
    Figure out the most recently completed quarter and the year-ago quarter.
    Returns: (current_year, current_q, prior_year, prior_q)

    Example: If today is March 2026, the most recent full quarter is Q4 2025,
    and the year-ago quarter is Q4 2024.
    """
    today = datetime.today()
    month = today.month

    # Most recent completed quarter
    if month <= 3:
        # Q1 not done yet → most recent is Q4 of prior year
        curr_y, curr_q = today.year - 1, 4
    elif month <= 6:
        curr_y, curr_q = today.year, 1
    elif month <= 9:
        curr_y, curr_q = today.year, 2
    else:
        curr_y, curr_q = today.year, 3

    # Year-ago quarter
    prior_y = curr_y - 1
    prior_q = curr_q

    return curr_y, curr_q, prior_y, prior_q


def fetch_edgar_fundamentals():
    """
    Fetch trailing S&P 500 fundamentals from SEC EDGAR's free XBRL Frames API.

    What this automates:
      ✅ Earnings growth (Y/Y aggregate net income)
      ✅ Revenue/sales growth (Y/Y aggregate revenue)
      ✅ Net profit margin (aggregate net income / revenue)
      ✅ Leverage — net debt / equity proxy
      ✅ Capex growth (Y/Y capital expenditure change)

    What still requires manual input (FactSet / analyst data):
      ❌ Forward P/E (needs forward earnings estimates)
      ❌ Analyst revisions (needs estimate revision data)
      ❌ Earnings/sales beat rates (needs estimate vs actual)
      ❌ PEG ratio (needs forward growth estimate)
      ❌ FCF yield, buyback yield (complex, cross-statement calc)

    Returns:
        dict with keys like 'earningsGrowth', 'salesGrowth', 'netMargin',
        'leverage', 'capexGrowth', 'asOf', 'source' — or None on failure.
    """
    print("\n📡 Fetching S&P 500 fundamentals from SEC EDGAR...")
    results = {}

    try:
        # Step 1: Get S&P 500 CIK numbers
        sp500_ciks = _get_sp500_ciks()
        if len(sp500_ciks) < 20:
            print(f"  ⚠️  Only {len(sp500_ciks)} CIKs mapped — too few for reliable aggregation")
            return None
        print(f"  📋 Mapped {len(sp500_ciks)} S&P 500 companies to SEC CIKs")

        # Step 2: Determine quarters
        curr_y, curr_q, prior_y, prior_q = _current_and_prior_quarters()
        curr_period = _quarter_str(curr_y, curr_q)
        prior_period = _quarter_str(prior_y, prior_q)
        print(f"  📅 Comparing {curr_period} vs {prior_period} (year-over-year)")

        # SEC rate limit: max 10 requests/second — add small delays
        import time as _time

        # ── Revenue (current & prior quarter) ──────────────────
        print(f"  📊 Fetching revenue data...")
        rev_curr_data = _fetch_xbrl_frame("Revenues", "USD", curr_period)
        _time.sleep(0.15)

        # Try alternate concept name if Revenues returns sparse data
        rev_curr_sp500, rev_curr_n = _aggregate_for_sp500(rev_curr_data, sp500_ciks)
        if rev_curr_n < 50:
            # Many companies use this longer concept name
            rev_curr_data2 = _fetch_xbrl_frame(
                "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", curr_period
            )
            _time.sleep(0.15)
            # Merge both sources: start with primary, add unique companies from alternate
            seen_ciks = {r["cik"] for r in rev_curr_data if r["cik"] in sp500_ciks}
            for r in rev_curr_data2:
                if r["cik"] in sp500_ciks and r["cik"] not in seen_ciks:
                    rev_curr_sp500 += float(r.get("val", 0))
                    rev_curr_n += 1
                    seen_ciks.add(r["cik"])

        rev_prior_data = _fetch_xbrl_frame("Revenues", "USD", prior_period)
        _time.sleep(0.15)
        rev_prior_sp500, rev_prior_n = _aggregate_for_sp500(rev_prior_data, sp500_ciks)
        if rev_prior_n < 50:
            rev_prior_data2 = _fetch_xbrl_frame(
                "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", prior_period
            )
            _time.sleep(0.15)
            # Merge both sources: start with primary, add unique companies from alternate
            seen_ciks = {r["cik"] for r in rev_prior_data if r["cik"] in sp500_ciks}
            for r in rev_prior_data2:
                if r["cik"] in sp500_ciks and r["cik"] not in seen_ciks:
                    rev_prior_sp500 += float(r.get("val", 0))
                    rev_prior_n += 1
                    seen_ciks.add(r["cik"])

        # ── Net Income (current & prior quarter) ──────────────
        print(f"  📊 Fetching earnings data...")
        ni_curr_data = _fetch_xbrl_frame("NetIncomeLoss", "USD", curr_period)
        _time.sleep(0.15)
        ni_curr_sp500, ni_curr_n = _aggregate_for_sp500(ni_curr_data, sp500_ciks)

        ni_prior_data = _fetch_xbrl_frame("NetIncomeLoss", "USD", prior_period)
        _time.sleep(0.15)
        ni_prior_sp500, ni_prior_n = _aggregate_for_sp500(ni_prior_data, sp500_ciks)

        # ── Long-Term Debt (current quarter, instant) ─────────
        print(f"  📊 Fetching debt data...")
        debt_data = _fetch_xbrl_frame("LongTermDebt", "USD", curr_period, instant=True)
        _time.sleep(0.15)
        debt_sp500, debt_n = _aggregate_for_sp500(debt_data, sp500_ciks)

        # ── Stockholders Equity (current quarter, instant) ────
        equity_data = _fetch_xbrl_frame("StockholdersEquity", "USD", curr_period, instant=True)
        _time.sleep(0.15)
        equity_sp500, equity_n = _aggregate_for_sp500(equity_data, sp500_ciks)

        # ── Capital Expenditure (current & prior quarter) ─────
        print(f"  📊 Fetching capex data...")
        capex_curr_data = _fetch_xbrl_frame(
            "PaymentsToAcquirePropertyPlantAndEquipment", "USD", curr_period
        )
        _time.sleep(0.15)
        capex_curr_sp500, capex_curr_n = _aggregate_for_sp500(capex_curr_data, sp500_ciks)

        capex_prior_data = _fetch_xbrl_frame(
            "PaymentsToAcquirePropertyPlantAndEquipment", "USD", prior_period
        )
        _time.sleep(0.15)
        capex_prior_sp500, capex_prior_n = _aggregate_for_sp500(capex_prior_data, sp500_ciks)

        # ═══ CALCULATE METRICS ════════════════════════════════

        # Sales/Revenue Growth (Y/Y)
        if rev_curr_sp500 > 0 and rev_prior_sp500 > 0 and rev_curr_n >= 50:
            sales_growth = round(((rev_curr_sp500 / rev_prior_sp500) - 1) * 100, 1)
            results["salesGrowth"] = sales_growth
            print(f"  ✅ Revenue Growth: {sales_growth}% Y/Y ({rev_curr_n} companies)")
        else:
            print(f"  ⚠️  Revenue data insufficient (curr: {rev_curr_n}, prior: {rev_prior_n} companies)")

        # Earnings Growth (Y/Y)
        if ni_curr_sp500 != 0 and ni_prior_sp500 > 0 and ni_curr_n >= 50:
            earnings_growth = round(((ni_curr_sp500 / ni_prior_sp500) - 1) * 100, 1)
            results["earningsGrowth"] = earnings_growth
            print(f"  ✅ Earnings Growth: {earnings_growth}% Y/Y ({ni_curr_n} companies)")
        else:
            print(f"  ⚠️  Earnings data insufficient (curr: {ni_curr_n}, prior: {ni_prior_n} companies)")

        # Net Margin
        if rev_curr_sp500 > 0 and ni_curr_sp500 != 0 and rev_curr_n >= 50:
            net_margin = round((ni_curr_sp500 / rev_curr_sp500) * 100, 1)
            results["netMargin"] = net_margin
            # Determine trend vs prior quarter
            if rev_prior_sp500 > 0 and ni_prior_sp500 != 0:
                prior_margin = (ni_prior_sp500 / rev_prior_sp500) * 100
                margin_delta = net_margin - prior_margin
                if abs(margin_delta) < 0.3:
                    results["marginTrend"] = "Stable"
                elif margin_delta > 0:
                    results["marginTrend"] = "Expanding"
                else:
                    results["marginTrend"] = "Contracting"
                print(f"  ✅ Net Margin: {net_margin}% ({results['marginTrend']}, was {round(prior_margin,1)}%)")
            else:
                print(f"  ✅ Net Margin: {net_margin}%")

        # Leverage (Debt / Equity as proxy for Debt / EBITDA)
        if equity_sp500 > 0 and debt_sp500 > 0 and debt_n >= 30:
            # Debt/Equity ratio — different from Debt/EBITDA but still informative
            # We report as Debt/Equity for transparency
            leverage = round(debt_sp500 / equity_sp500, 2)
            results["leverage"] = leverage
            results["leverageType"] = "Debt/Equity"
            print(f"  ✅ Leverage (D/E): {leverage}x ({debt_n} companies)")
        else:
            print(f"  ⚠️  Leverage data insufficient (debt: {debt_n}, equity: {equity_n} companies)")

        # Capex Growth (Y/Y)
        if capex_curr_sp500 > 0 and capex_prior_sp500 > 0 and capex_curr_n >= 30:
            capex_growth = round(((capex_curr_sp500 / capex_prior_sp500) - 1) * 100, 1)
            results["capex"] = capex_growth
            print(f"  ✅ Capex Growth: {capex_growth}% Y/Y ({capex_curr_n} companies)")
        else:
            print(f"  ⚠️  Capex data insufficient (curr: {capex_curr_n}, prior: {capex_prior_n} companies)")

        # ═══ PACKAGE RESULTS ══════════════════════════════════
        if results:
            results["asOf"] = f"{curr_y}-Q{curr_q}"
            results["source"] = "SEC-EDGAR"
            results["companiesMatched"] = max(rev_curr_n, ni_curr_n)
            results["quarter"] = curr_period
            metric_count = len([k for k in results if k not in ("asOf", "source", "companiesMatched", "quarter", "leverageType")])
            print(f"\n  ✅ EDGAR: {metric_count} fundamentals fetched from {results['companiesMatched']} companies")
            return results
        else:
            print(f"\n  ⚠️  EDGAR: No metrics could be calculated — data may not be filed yet for {curr_period}")
            # Try one quarter back
            fallback_q = curr_q - 1 if curr_q > 1 else 4
            fallback_y = curr_y if curr_q > 1 else curr_y - 1
            print(f"  ℹ️  Tip: Try running again after {curr_period} filings are complete (typically 45-60 days after quarter end)")
            return None

    except Exception as e:
        print(f"  ⚠️  EDGAR fetch failed: {e}")
        import traceback
        traceback.print_exc()
        return None


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

    # Download in batches of 50 to avoid overwhelming yfinance's cache
    BATCH_SIZE = 50
    all_prices = []
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(tickers) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  📦 Batch {batch_num}/{total_batches} ({len(batch)} tickers)...")
        try:
            batch_prices = yf.download(batch, start=start_date, end=end_date,
                                       auto_adjust=False, threads=False)['Close']
            if isinstance(batch_prices, pd.Series):
                batch_prices = batch_prices.to_frame(name=batch[0])
            all_prices.append(batch_prices)
        except Exception as e:
            print(f"  ⚠️  Batch {batch_num} failed: {e}")
        time.sleep(1)  # Brief pause between batches

    # Combine all batches
    if all_prices:
        prices = pd.concat(all_prices, axis=1)
        # Remove duplicate columns if any
        prices = prices.loc[:, ~prices.columns.duplicated()]
    else:
        prices = pd.DataFrame()

    print(f"✅ Downloaded {len(prices)} trading days for {len(prices.columns)} stocks")
    
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
            
            # ── Trend 1 week ago (for change detection) ──
            trend_1wk = "Unknown"
            if len(px) > 47 and len(ma) > 6:
                price_1wk = px.iloc[-6]
                ma_1wk = ma.iloc[-6]
                ma_1wk_slope = ma.iloc[-47] if len(ma) > 47 else np.nan
                if not pd.isna(ma_1wk) and not pd.isna(ma_1wk_slope):
                    ma_was_rising = ma_1wk > ma_1wk_slope
                    was_above = price_1wk > ma_1wk
                    if ma_was_rising and was_above:
                        trend_1wk = "Uptrend"
                    elif ma_was_rising and not was_above:
                        trend_1wk = "Pullback"
                    elif not ma_was_rising and was_above:
                        trend_1wk = "Snapback"
                    else:
                        trend_1wk = "Downtrend"

            # ── 20-day SMA & 20-day low (for oversold indicators) ──
            sma20 = px.rolling(20).mean().iloc[-1] if len(px) >= 20 else np.nan
            above_20sma = bool(price_now > sma20) if not pd.isna(sma20) else None
            low_20d = px.iloc[-20:].min() if len(px) >= 20 else np.nan
            at_20day_low = bool(price_now <= low_20d) if not pd.isna(low_20d) else None

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
                # Extra research fields (from the same API call)
                extra = {
                    "tpe": round(info['trailingPE'], 1) if info.get('trailingPE') else None,
                    "fpe": round(info['forwardPE'], 1) if info.get('forwardPE') else None,
                    "eps": round(info['trailingEps'], 2) if info.get('trailingEps') else None,
                    "feps": round(info['forwardEps'], 2) if info.get('forwardEps') else None,
                    "rg": round(info['revenueGrowth'] * 100, 1) if info.get('revenueGrowth') else None,
                    "gm": round(info['grossMargins'] * 100, 1) if info.get('grossMargins') else None,
                    "om": round(info['operatingMargins'] * 100, 1) if info.get('operatingMargins') else None,
                    "pm": round(info['profitMargins'] * 100, 1) if info.get('profitMargins') else None,
                    "dy": round(info['dividendYield'] * 100, 2) if info.get('dividendYield') else None,
                    "beta": round(info['beta'], 2) if info.get('beta') else None,
                    "tgt": round(info['targetMeanPrice'], 2) if info.get('targetMeanPrice') else None,
                    "nAn": info.get('numberOfAnalystOpinions'),
                    "hi52": round(info['fiftyTwoWeekHigh'], 2) if info.get('fiftyTwoWeekHigh') else None,
                    "lo52": round(info['fiftyTwoWeekLow'], 2) if info.get('fiftyTwoWeekLow') else None,
                    "ev": round(info.get('enterpriseValue', 0) / 1e6) if info.get('enterpriseValue') else None,
                    "evr": round(info['enterpriseToRevenue'], 1) if info.get('enterpriseToRevenue') else None,
                    "eve": round(info['enterpriseToEbitda'], 1) if info.get('enterpriseToEbitda') else None,
                    "pb": round(info['priceToBook'], 1) if info.get('priceToBook') else None,
                }
            except Exception:
                company = ticker
                sector = "Unknown"
                industry = "Unknown"
                mktcap = 0
                extra = {}
            
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
                "trend1wk": trend_1wk,
                "trendChanged": trend != trend_1wk and trend_1wk != "Unknown",
                "above20sma": above_20sma,
                "at20dayLow": at_20day_low,
                **extra,
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
    
    # ── S&P 500 (single 5-year pull → price, 150d MA, 4yr MA, chart) ──
    try:
        print(f"  📈 Pulling S&P 500 (5-year history)...")
        sp_hist = yf.Ticker("^GSPC").history(period="5y")
        if not sp_hist.empty:
            px = sp_hist['Close']
            market["sp500"] = {
                "price": round(float(px.iloc[-1]), 2),
                "history": [round(float(v), 2) for v in px.tail(20).values],
            }
            # 150-day MA + slope
            if len(px) >= 150:
                ma = px.rolling(150).mean()
                market["sp500"]["ma150"] = round(float(ma.iloc[-1]), 2)
                if len(ma) > 192:
                    ma_2mo_ago = ma.iloc[-42]
                    if not pd.isna(ma_2mo_ago):
                        ma_now = ma.iloc[-1]
                        if ma_now > ma_2mo_ago * 1.001:
                            market["sp500"]["maSlope"] = "Positive"
                        elif ma_now < ma_2mo_ago * 0.999:
                            market["sp500"]["maSlope"] = "Negative"
                        else:
                            market["sp500"]["maSlope"] = "Neutral"
            # 4-year MA (≈1000 trading days)
            if len(px) >= 1000:
                market["sp500"]["ma4yr"] = round(float(
                    px.rolling(1000).mean().iloc[-1]
                ), 2)
                print(f"  ✅ S&P 500 4yr MA: {market['sp500']['ma4yr']}")
            # 3-year chart data (last ~756 trading days)
            chart_days = min(len(px), 756)
            chart_px = px.iloc[-chart_days:]
            market["sp500_daily_prices"] = [round(float(c), 2) for c in chart_px.values]
            market["sp500_daily_dates"] = [d.strftime("%Y-%m-%d") for d in chart_px.index]
            print(f"  ✅ S&P 500: {market['sp500']['price']}  |  "
                  f"Chart: {len(market['sp500_daily_prices'])} days "
                  f"({market['sp500_daily_dates'][0]} to {market['sp500_daily_dates'][-1]})")
        else:
            print(f"  ❌ S&P 500: No data")
    except Exception as e:
        print(f"  ❌ S&P 500: {e}")

    # ── Other indices (Russell 3000, VIX, Oil, Dollar) ──
    indices = {
        "^RUA": ("r3k", "Russell 3000"),
        "^VIX": ("vix", "VIX"),
        "CL=F": ("oil", "WTI Crude"),
        "DX-Y.NYB": ("dxy", "US Dollar Index"),
    }

    for symbol, (key, label) in indices.items():
        try:
            hist = yf.Ticker(symbol).history(period="2y")
            if not hist.empty:
                px = hist['Close']
                market[key] = {
                    "price": round(float(px.iloc[-1]), 2),
                    "history": [round(float(v), 2) for v in px.tail(20).values],
                }
                # Calculate MAs for indices
                if len(px) >= 150:
                    ma = px.rolling(150).mean()
                    market[key]["ma150"] = round(float(ma.iloc[-1]), 2)
                    if len(ma) > 192:
                        ma_2mo_ago = ma.iloc[-42]
                        if not pd.isna(ma_2mo_ago):
                            ma_now = ma.iloc[-1]
                            if ma_now > ma_2mo_ago * 1.001:
                                market[key]["maSlope"] = "Positive"
                            elif ma_now < ma_2mo_ago * 0.999:
                                market[key]["maSlope"] = "Negative"
                            else:
                                market[key]["maSlope"] = "Neutral"
                print(f"  ✅ {label}: {market[key]['price']}")
            else:
                print(f"  ❌ {label}: No data")
        except Exception as e:
            print(f"  ❌ {label}: {e}")
    
    # ── Risk appetite & sentiment indicators (price vs 150d MA) ──
    risk_tickers = {
        "^MOVE": ("move", "MOVE Index"),
        "HYG":   ("hyg", "High Yield Bond ETF"),
        "IEF":   ("ief", "Treasury Bond ETF"),
        "IWM":   ("iwm", "Small Cap ETF"),
        "SPY":   ("spy_etf", "S&P 500 ETF"),
        "XLY":   ("xly", "Consumer Discretionary"),
        "XLP":   ("xlp", "Consumer Staples"),
        "IPO":   ("ipo", "IPO ETF"),
        "BTC-USD": ("btc", "Bitcoin"),
    }

    for symbol, (key, label) in risk_tickers.items():
        try:
            hist = yf.Ticker(symbol).history(period="1y")
            if not hist.empty:
                px = hist['Close']
                price = float(px.iloc[-1])
                ma150 = float(px.rolling(150).mean().iloc[-1]) if len(px) >= 150 else None
                market[key] = {
                    "price": round(price, 2),
                    "ma150": round(ma150, 2) if ma150 else None,
                    "aboveMa": price > ma150 if ma150 else None,
                }
                status = "above MA" if (ma150 and price > ma150) else "below MA" if ma150 else "no MA"
                print(f"  ✅ {label}: {price:.2f} ({status})")
            else:
                print(f"  ❌ {label}: No data")
        except Exception as e:
            print(f"  ❌ {label}: {e}")

    # Calculate ratios
    if "hyg" in market and "ief" in market:
        hyg_p = market["hyg"]["price"]
        ief_p = market["ief"]["price"]
        market["hygIefRatio"] = round(hyg_p / ief_p, 4) if ief_p > 0 else None
        # Check if ratio is above its own 150d MA
        try:
            hyg_hist = yf.Ticker("HYG").history(period="1y")['Close']
            ief_hist = yf.Ticker("IEF").history(period="1y")['Close']
            ratio_series = hyg_hist / ief_hist
            ratio_ma = ratio_series.rolling(150).mean().iloc[-1] if len(ratio_series) >= 150 else None
            market["hygIefAboveMa"] = float(ratio_series.iloc[-1]) > float(ratio_ma) if ratio_ma else None
        except Exception:
            market["hygIefAboveMa"] = None

    if "iwm" in market and "spy_etf" in market:
        iwm_p = market["iwm"]["price"]
        spy_p = market["spy_etf"]["price"]
        market["iwmSpyRatio"] = round(iwm_p / spy_p, 4) if spy_p > 0 else None
        try:
            iwm_hist = yf.Ticker("IWM").history(period="1y")['Close']
            spy_hist = yf.Ticker("SPY").history(period="1y")['Close']
            ratio_series = iwm_hist / spy_hist
            ratio_ma = ratio_series.rolling(150).mean().iloc[-1] if len(ratio_series) >= 150 else None
            market["iwmSpyAboveMa"] = float(ratio_series.iloc[-1]) > float(ratio_ma) if ratio_ma else None
        except Exception:
            market["iwmSpyAboveMa"] = None

    if "xly" in market and "xlp" in market:
        xly_p = market["xly"]["price"]
        xlp_p = market["xlp"]["price"]
        market["xlyXlpRatio"] = round(xly_p / xlp_p, 4) if xlp_p > 0 else None
        try:
            xly_hist = yf.Ticker("XLY").history(period="1y")['Close']
            xlp_hist = yf.Ticker("XLP").history(period="1y")['Close']
            ratio_series = xly_hist / xlp_hist
            ratio_ma = ratio_series.rolling(150).mean().iloc[-1] if len(ratio_series) >= 150 else None
            market["xlyXlpAboveMa"] = float(ratio_series.iloc[-1]) > float(ratio_ma) if ratio_ma else None
        except Exception:
            market["xlyXlpAboveMa"] = None

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
            "NAPM":            ("ismPmi",         "ISM Manufacturing PMI"),
        }
        
        import time as _time
        for code_str, (key, label) in series.items():
            data = None
            last_err = None
            for attempt in range(3):
                try:
                    data = fred.get_series(code_str).dropna()
                    break
                except Exception as e:
                    last_err = e
                    if attempt < 2:
                        _time.sleep(1.5)  # brief backoff before retry
            if data is None:
                print(f"  ❌ {label} ({code_str}): {last_err} (after 3 attempts)")
                continue
            try:
                if len(data) == 0:
                    print(f"  ❌ {label} ({code_str}): No data")
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
                print(f"  ❌ {label} ({code_str}): {e}")
        
        # Calculate YoY inflation from CPI
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
        print("  Install: pip3 install fredapi --break-system-packages")
        return {}


# ═══════════════════════════════════════════════════════════
# STEP 5: CALCULATE BREADTH AND SECTOR SUMMARIES
# ═══════════════════════════════════════════════════════════

def update_skipped_history(stocks, skipped, all_tickers):
    """
    Track consecutive days each ticker has been skipped (no price data).
    Returns a list of tickers pending removal (5+ consecutive days missing).
    """
    # Load existing history
    history = {}
    if SKIPPED_HISTORY_FILE.exists():
        try:
            with open(SKIPPED_HISTORY_FILE) as f:
                history = json.load(f)
        except Exception:
            history = {}

    today = datetime.today().strftime("%Y-%m-%d")
    got_data = {s["ticker"] for s in stocks}
    skipped_today = {s["ticker"] for s in skipped}

    # For each ticker in the universe, update its counter
    for ticker in all_tickers:
        ticker = ticker.upper().strip()
        if ticker in got_data:
            # Got data — reset counter
            if ticker in history:
                del history[ticker]
        elif ticker in skipped_today:
            # No data — increment counter
            if ticker not in history:
                history[ticker] = {"consecutiveDays": 1, "firstSkipped": today, "lastSkipped": today}
            else:
                history[ticker]["consecutiveDays"] += 1
                history[ticker]["lastSkipped"] = today

    # Save updated history
    with open(SKIPPED_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

    # Build pending removal list (tickers missing for threshold+ days)
    pending = []
    for ticker, data in history.items():
        if data["consecutiveDays"] >= REMOVAL_THRESHOLD_DAYS:
            pending.append({
                "ticker": ticker,
                "daysMissing": data["consecutiveDays"],
                "firstSkipped": data["firstSkipped"],
            })
    pending.sort(key=lambda x: -x["daysMissing"])

    print(f"\n🗑️  Delisting tracker: {len(history)} tickers missing today, "
          f"{len(pending)} flagged for removal ({REMOVAL_THRESHOLD_DAYS}+ days)")
    if pending:
        print(f"  Pending removal: {', '.join(p['ticker'] for p in pending[:10])}{'...' if len(pending) > 10 else ''}")

    return pending


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

    # ── Industry breakdown ──
    industries = {}
    for s in valid:
        ind = s.get("industry", "Unknown")
        if ind == "Unknown":
            continue
        if ind not in industries:
            industries[ind] = {"name": ind, "sector": s["sector"], "n": 0,
                              "Uptrend": 0, "Pullback": 0, "Downtrend": 0, "Snapback": 0}
        industries[ind]["n"] += 1
        if s["trend"] in industries[ind]:
            industries[ind][s["trend"]] += 1

    industry_list = []
    for ind_data in industries.values():
        n = ind_data["n"]
        if n == 0:
            continue
        ind_stocks = [s for s in valid if s.get("industry") == ind_data["name"]]
        avg_mom = np.mean([s["relMomRank"] for s in ind_stocks]) if ind_stocks else 50
        industry_list.append({
            "name": ind_data["name"],
            "sector": ind_data["sector"],
            "n": n,
            "up": round(ind_data["Uptrend"] / n * 100, 1),
            "pb": round(ind_data["Pullback"] / n * 100, 1),
            "dn": round(ind_data["Downtrend"] / n * 100, 1),
            "sb": round(ind_data["Snapback"] / n * 100, 1),
            "rm": round(avg_mom, 1),
        })

    industry_list.sort(key=lambda x: x["up"], reverse=True)

    # ── Oversold indicators (breadth washout & new lows) ──
    stocks_with_20sma = [s for s in valid if s.get("above20sma") is not None]
    stocks_with_20low = [s for s in valid if s.get("at20dayLow") is not None]

    pct_above_20sma = round(
        sum(1 for s in stocks_with_20sma if s["above20sma"]) / len(stocks_with_20sma) * 100, 1
    ) if stocks_with_20sma else None

    pct_at_20day_lows = round(
        sum(1 for s in stocks_with_20low if s["at20dayLow"]) / len(stocks_with_20low) * 100, 1
    ) if stocks_with_20low else None

    breadth = {
        "pctAbove": breadth_pct,
        "totalStocks": total,
        "trends": trend_pcts,
        "pctAbove20sma": pct_above_20sma,
        "pctAt20dayLows": pct_at_20day_lows,
    }
    
    print(f"  Breadth: {breadth_pct}% above 150-day MA")
    print(f"  Uptrend: {trend_pcts.get('Uptrend', 0)}% | "
          f"Pullback: {trend_pcts.get('Pullback', 0)}% | "
          f"Downtrend: {trend_pcts.get('Downtrend', 0)}% | "
          f"Snapback: {trend_pcts.get('Snapback', 0)}%")
    print(f"  Sectors: {len(sector_list)} | Industries: {len(industry_list)}")

    return breadth, sector_list, industry_list


# ═══════════════════════════════════════════════════════════
# STEP 6: DETERMINE OVERALL MARKET SIGNALS
# ═══════════════════════════════════════════════════════════

def calculate_signals(market, breadth, macro, auto_data=None):
    """Compute the Health Score and overall market assessment."""
    if auto_data is None:
        auto_data = {}
    print(f"\n🎯 Calculating Health Score...")

    # Load previous indicator dates from last run (so we can track when each changed)
    prev_indicator_dates = {}
    prev_indicator_status = {}
    if OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE) as _f:
                prev_data = json.load(_f)
            for item in prev_data.get("market", {}).get("healthWins", []):
                key = item["label"].split(" · ")[0]
                prev_indicator_dates[key] = item.get("sinceDate", "")
                prev_indicator_status[key] = True
            for item in prev_data.get("market", {}).get("healthMisses", []):
                key = item["label"].split(" · ")[0]
                prev_indicator_dates[key] = item.get("sinceDate", "")
                prev_indicator_status[key] = False
        except Exception:
            pass

    today_str = datetime.today().strftime("%Y-%m-%d")

    checks = []

    def add(passed, category, label, weight=5):
        # Determine "since" date: if status changed or is new, use today; otherwise keep old date
        key = label.split(" · ")[0]
        prev_status = prev_indicator_status.get(key)
        if prev_status is None or prev_status != passed:
            since = today_str
        else:
            since = prev_indicator_dates.get(key, today_str)
        checks.append({
            "pass": passed,
            "cat": category,
            "label": label,
            "weight": weight,
            "sinceDate": since,
        })
    
    # ── Macro checks ──
    # Read raw values (None if fetch failed — we do NOT silently fall back to hardcoded defaults).
    def _mv(key):
        v = macro.get(key, {})
        return v.get("value") if isinstance(v, dict) else None
    def _mp(side_dict, key):
        v = side_dict.get(key, {})
        return v.get("price") if isinstance(v, dict) else None

    emp     = _mv("employment")
    gdp     = _mv("gdp")
    inf     = _mv("inflation")
    hy      = _mv("hySpread")
    sent    = _mv("sentiment")
    mtg     = _mv("mortgage")
    ten_yr  = _mv("tenYear")
    two_yr  = _mv("twoYear")
    ism     = _mv("ismPmi")
    gas     = _mv("gasPrice")
    jobless = _mv("joblessClaims")
    oil     = _mp(market, "oil")
    dxy     = _mp(market, "dxy")

    def add_skip(category, metric_name, reason=""):
        """Record a scored indicator as skipped because source data was unavailable.
        Skipped indicators do NOT count toward tailwinds, headwinds, or the health score."""
        reason_str = f" ({reason})" if reason else ""
        checks.append({
            "pass": False, "skip": True, "cat": category,
            "label": f"{metric_name} · Data unavailable{reason_str}",
            "weight": 0, "sinceDate": today_str,
        })

    if emp is not None:
        add(emp < 5.0, "Macro", f"Labor Market · Now: {emp}% · Healthy: below 5%")
    else:
        add_skip("Macro", "Labor Market", "FRED fetch failed")

    if gdp is not None:
        add(gdp > 2.0, "Macro", f"GDP Growth · Now: {gdp}% · Healthy: above 2%")
    else:
        add_skip("Macro", "GDP Growth", "FRED fetch failed")

    if inf is not None:
        add(inf < 3.0, "Macro", f"Inflation · Now: {inf}% · Healthy: below 3%")
    else:
        add_skip("Macro", "Inflation", "FRED fetch failed")

    if hy is not None:
        add(hy < 4.0, "Macro", f"Credit Spreads (HY OAS) · Now: {hy}% · Healthy: below 4%")
    else:
        add_skip("Macro", "Credit Spreads (HY OAS)", "FRED fetch failed")

    if sent is not None:
        add(sent > 70, "Macro", f"Consumer Confidence · Now: {sent} · Healthy: above 70")
    else:
        add_skip("Macro", "Consumer Confidence", "FRED fetch failed")

    if mtg is not None:
        add(mtg < 6.0, "Macro", f"Mortgage Rates · Now: {mtg}% · Healthy: below 6%")
    else:
        add_skip("Macro", "Mortgage Rates", "FRED fetch failed")

    if ten_yr is not None and two_yr is not None:
        yc_val = round(ten_yr - two_yr, 2)
        add(yc_val >= 0, "Macro", f"Yield Curve · Now: {yc_val:+.2f}% · Healthy: positive (not inverted)")
    else:
        add_skip("Macro", "Yield Curve", "FRED 10Y/2Y fetch failed")

    if ism is not None:
        add(ism >= 50, "Macro", f"ISM Manufacturing · Now: {ism} · Healthy: above 50")
    else:
        add_skip("Macro", "ISM Manufacturing", "FRED fetch failed")

    if oil is not None:
        add(oil < 90, "Macro", f"Oil Price (WTI) · Now: ${oil:.2f} · Healthy: below $90")
    else:
        add_skip("Macro", "Oil Price (WTI)", "yfinance fetch failed")

    if gas is not None:
        add(gas < 4.0, "Macro", f"Gas Price · Now: ${gas:.2f} · Healthy: below $4.00")
    else:
        add_skip("Macro", "Gas Price", "FRED fetch failed")

    if dxy is not None:
        add(dxy < 105, "Macro", f"US Dollar (DXY) · Now: {dxy:.1f} · Healthy: below 105")
    else:
        add_skip("Macro", "US Dollar (DXY)", "yfinance fetch failed")

    if jobless is not None:
        add(jobless < 250000, "Macro", f"Initial Jobless Claims · Now: {int(jobless/1000)}K · Healthy: below 250K")
    else:
        add_skip("Macro", "Initial Jobless Claims", "FRED fetch failed")

    # ── Fundamental checks ──
    f = MANUAL_INPUTS["fundamental"]
    # Monitored but not scored (manual data, goes stale between quarterly updates):
    # add(f["salesGrowth"] > 4.0, "Fundamental", f"Sales Growth · Now: {f['salesGrowth']}% · Healthy: above 4%")
    # add(f["earningsGrowth"] > 5.0, "Fundamental", f"Earnings Growth · Now: {f['earningsGrowth']}% · Healthy: above 5%")
    # add(f["netMargin"] > 11.0, "Fundamental", f"Profit Margins · Now: {f['netMargin']}% · Healthy: above 11%")
    # add(f["revisions"] > 1.0, "Fundamental", f"Earnings Revisions · Now: {f['revisions']}x · Healthy: above 1.0")
    # add(fcf_ok > 3.5, "Fundamental", f"Free Cash Flow · Now: {fcf_ok}% · Healthy: above 3.5%")

    # Trailing P/E — auto-pulled from SPY (no silent fallback — skip if fetch fails)
    trailing_pe = None
    try:
        import yfinance as _yf
        _spy_info = _yf.Ticker("SPY").info
        trailing_pe = _spy_info.get("trailingPE")
    except Exception:
        pass
    if trailing_pe is not None:
        add(trailing_pe < 22.0, "Fundamental", f"Valuation (Trailing P/E) · Now: {trailing_pe:.1f}x · Healthy: below 22x")
    else:
        add_skip("Fundamental", "Valuation (Trailing P/E)", "yfinance SPY.info fetch failed")

    # ── Technical checks ──
    sp = market.get("sp500", {})
    sp_price = sp.get("price", 0)
    sp_ma4yr = sp.get("ma4yr", 0)
    sp_ma150 = sp.get("ma150", 0)
    b_pct = breadth.get("pctAbove", 58)
    vix_val = market.get("vix", {}).get("price", 15)

    add(sp_price > sp_ma4yr and sp_ma4yr > 0, "Technical",
        f"Long-Term Trend · S&P {sp_price:,.0f} vs 4-Year MA {sp_ma4yr:,.0f}")
    add(sp_price > sp_ma150 and sp_ma150 > 0, "Technical",
        f"Medium-Term Trend · S&P {sp_price:,.0f} vs 150-Day MA {sp_ma150:,.0f}")
    # Market Breadth: tailwind when broadly healthy (>60%) OR deeply oversold (<20% — contrarian)
    add(b_pct > 60 or b_pct < 20, "Technical",
        f"Market Breadth · Now: {round(b_pct)}% · Healthy: above 60% or below 20% (oversold)")
    add(vix_val < 20, "Technical",
        f"Volatility · VIX Now: {vix_val:.1f} · Healthy: below 20")
    pc_auto = auto_data.get("putCall")
    pc = pc_auto["value"] if pc_auto else MANUAL_INPUTS["sentiment"]["putCall"]
    add(pc < 1.0, "Technical",
        f"Sentiment · P/C Now: {pc} · Healthy: below 1.0")
    # AAII sentiment: contrarian when extreme
    aaii_auto = auto_data.get("aaii")
    aaii_val = aaii_auto["value"] if aaii_auto else MANUAL_INPUTS["sentiment"]["aaii"]
    add(25 <= aaii_val <= 45, "Technical",
        f"AAII Bull Sentiment · Now: {aaii_val:.0f}% · Healthy: 25-45% (extremes are contrarian)")

    # ── Risk appetite & cross-asset signals ──
    # Real interest rate (Fed Funds - Inflation) — needs BOTH to be live
    ff = _mv("fedFunds")
    if ff is not None and inf is not None:
        real_rate = round(ff - inf, 2)
        add(real_rate <= 2.0, "Macro",
            f"Real Interest Rate · Now: {real_rate:+.2f}% · Healthy: at or below 2%")
    else:
        add_skip("Macro", "Real Interest Rate", "Fed Funds or Inflation fetch failed")

    # MOVE Index (bond volatility) — lower = calmer, like VIX for bonds
    move_price = market.get("move", {}).get("price", 0)
    if move_price > 0:
        add(move_price < 100, "Technical",
            f"MOVE Index · Now: {move_price:.1f} · Healthy: below 100 (calm bond market)")

    # ── Monitored but not scored (data still pulled, just not in health score) ──
    # HYG/IEF ratio, Small Cap / Large Cap, Discretionary / Staples

    # IPO ETF vs 150d MA — speculative appetite
    ipo_above = market.get("ipo", {}).get("aboveMa")
    if ipo_above is not None:
        ipo_price = market.get("ipo", {}).get("price", 0)
        add(ipo_above, "Technical",
            f"IPO ETF · Now: ${ipo_price:.2f} · Healthy: above 150d MA (risk-on)")

    # Monitored but not scored:
    # Bitcoin vs 150d MA
    
    # Auto-balance: every ACTIVE (non-skipped) indicator gets equal weight so total always = 100.
    # Skipped indicators don't change the score in either direction — they're reported separately.
    active_checks = [c for c in checks if not c.get("skip")]
    skipped_checks = [c for c in checks if c.get("skip")]
    num_indicators = len(active_checks)
    weight_per = 100.0 / num_indicators if num_indicators > 0 else 0
    for c in active_checks:
        c["weight"] = weight_per

    passed_count = sum(1 for c in active_checks if c["pass"])
    score = round(passed_count * weight_per)
    total = 100
    wins = [c for c in active_checks if c["pass"]]
    misses = [c for c in active_checks if not c["pass"]]

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
    print(f"  Tailwinds: {len(wins)} | Headwinds: {len(misses)} | Skipped: {len(skipped_checks)}")
    if skipped_checks:
        print(f"  ⚠️  Skipped due to missing data:")
        for s in skipped_checks:
            print(f"       - {s['label']}")

    return {
        "score": score,
        "total": total,
        "label": label,
        "overall": overall,
        "wins": [{"label": w["label"], "weight": w["weight"], "cat": w["cat"], "sinceDate": w["sinceDate"]} for w in wins],
        "misses": [{"label": m["label"], "weight": m["weight"], "cat": m["cat"], "sinceDate": m["sinceDate"]} for m in misses],
        "skipped": [{"label": s["label"], "cat": s["cat"], "sinceDate": s["sinceDate"]} for s in skipped_checks],
    }


# ═══════════════════════════════════════════════════════════
# STEP 6B: ANALYZE PULLBACKS
# ═══════════════════════════════════════════════════════════

def analyze_pullbacks():
    """Analyze S&P 500 pullback history from 1957 to present."""

    try:
        # Load historical CSV
        if not HISTORICAL_CSV.exists():
            print(f"⚠️  Historical CSV not found: {HISTORICAL_CSV}")
            return {}

        hist_df = pd.read_csv(HISTORICAL_CSV)
        hist_df['Date'] = pd.to_datetime(hist_df['Date'])
        hist_df = hist_df.sort_values('Date')

        print(f"  Loading historical data: {len(hist_df):,} rows ({hist_df['Date'].dt.year.min()}-{hist_df['Date'].dt.year.max()})")

        # Get recent data from yfinance (last 60 days — overwrite to pick up any revisions)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        recent = yf.download("^GSPC", start=start_date, end=end_date, progress=False, auto_adjust=True)
        recent_df = recent[['Close']].reset_index()
        recent_df.columns = ['Date', 'Close']
        recent_df['Date'] = pd.to_datetime(recent_df['Date'])

        # Merge: drop the overlap from CSV and replace with fresh data
        if len(recent_df) > 0:
            cutoff = recent_df['Date'].min()
            hist_old = hist_df[hist_df['Date'] < cutoff]
            merged_df = pd.concat([hist_old, recent_df], ignore_index=True)
            merged_df = merged_df.sort_values('Date').drop_duplicates(subset=['Date'], keep='last')

            # Auto-update the CSV so it stays current for next run
            save_df = merged_df.copy()
            save_df['Date'] = save_df['Date'].dt.strftime('%Y-%m-%d')
            save_df.to_csv(HISTORICAL_CSV, index=False)
            print(f"  Refreshed last {len(recent_df)} trading days from yfinance (CSV updated)")
        else:
            merged_df = hist_df
            print(f"  ⚠️  No recent data from yfinance — using CSV as-is")

        prices = merged_df['Close'].values
        dates = merged_df['Date'].values

        # Detect pullbacks: every distinct 5%+ decline from a running peak
        # This captures "lived experience" of investors (including overlapping dips)
        pullbacks = []
        running_peak = prices[0]
        running_peak_idx = 0
        in_pullback = False
        pullback_start_idx = 0
        trough_price = prices[0]
        trough_idx = 0

        for i in range(1, len(prices)):
            current_price = prices[i]

            # Update running peak if price makes new high
            if current_price > running_peak:
                # If we were in a pullback, close it out first
                if in_pullback:
                    magnitude = (trough_price - running_peak) / running_peak * 100
                    duration = trough_idx - pullback_start_idx
                    pullbacks.append({
                        'start_idx': pullback_start_idx,
                        'end_idx': trough_idx,
                        'start_date': dates[pullback_start_idx],
                        'trough_date': dates[trough_idx],
                        'peak_price': running_peak,
                        'trough_price': trough_price,
                        'magnitude': magnitude,
                        'duration': duration,
                        'open': False,
                    })
                    in_pullback = False

                running_peak = current_price
                running_peak_idx = i
                trough_price = current_price
                trough_idx = i
            else:
                # Track trough
                if current_price < trough_price:
                    trough_price = current_price
                    trough_idx = i

            # Check if we've entered a 5%+ pullback
            decline = (current_price - running_peak) / running_peak
            if decline < -0.05 and not in_pullback:
                in_pullback = True
                pullback_start_idx = running_peak_idx
                trough_price = current_price
                trough_idx = i

        # Handle open pullback at end
        if in_pullback:
            magnitude = (trough_price - running_peak) / running_peak * 100
            duration = trough_idx - pullback_start_idx
            pullbacks.append({
                'start_idx': pullback_start_idx,
                'end_idx': trough_idx,
                'start_date': dates[pullback_start_idx],
                'trough_date': dates[trough_idx],
                'peak_price': running_peak,
                'trough_price': trough_price,
                'magnitude': magnitude,
                'duration': duration,
                'open': True,
            })

        # Categorize by severity
        tiers = {
            'routine': {'pullbacks': [], 'magnitude_range': (-10, -5)},
            'meaningful': {'pullbacks': [], 'magnitude_range': (-15, -10)},
            'beyond_normal': {'pullbacks': [], 'magnitude_range': (-20, -15)},
            'bear': {'pullbacks': [], 'magnitude_range': (-100, -20)},
        }

        for pb in pullbacks:
            mag = pb['magnitude']
            if mag > -10:
                tiers['routine']['pullbacks'].append(pb)
            elif mag > -15:
                tiers['meaningful']['pullbacks'].append(pb)
            elif mag > -20:
                tiers['beyond_normal']['pullbacks'].append(pb)
            else:
                tiers['bear']['pullbacks'].append(pb)

        # Calculate stats per tier
        tier_stats = {}
        for tier_name, tier_data in tiers.items():
            pbs = tier_data['pullbacks']
            if pbs:
                durations = [pb['duration'] for pb in pbs]
                durations_sorted = sorted(durations)
                median_dur = durations_sorted[len(durations_sorted) // 2]
                avg_dur = sum(durations) / len(durations)

                tier_stats[tier_name] = {
                    'count': len(pbs),
                    'pct': round(len(pbs) / len(pullbacks) * 100, 1) if pullbacks else 0,
                    'median_duration_days': int(median_dur),
                    'avg_duration_days': int(avg_dur),
                    'details': [{
                        'start': pd.Timestamp(pb['start_date']).strftime('%Y-%m-%d'),
                        'trough': pd.Timestamp(pb['trough_date']).strftime('%Y-%m-%d'),
                        'peak': round(pb['peak_price'], 2),
                        'low': round(pb['trough_price'], 2),
                        'mag': round(pb['magnitude'], 1),
                        'dur': pb['duration'],
                    } for pb in sorted(pbs, key=lambda x: x['start_date'])],
                }
            else:
                tier_stats[tier_name] = {
                    'count': 0,
                    'pct': 0.0,
                    'median_duration_days': 0,
                    'avg_duration_days': 0,
                }

        # Overall stats
        if pullbacks:
            magnitudes = [pb['magnitude'] for pb in pullbacks]
            magnitudes_sorted = sorted(magnitudes)
            median_mag = magnitudes_sorted[len(magnitudes_sorted) // 2]

            durations = [pb['duration'] for pb in pullbacks]
            durations_sorted = sorted(durations)
            median_dur = durations_sorted[len(durations_sorted) // 2]
            avg_dur = sum(durations) / len(durations)

            start_year = pd.Timestamp(dates[0]).year
            end_year = pd.Timestamp(dates[-1]).year
            years_of_data = end_year - start_year
            frequency = len(pullbacks) / years_of_data if years_of_data > 0 else 0

            bear_count = len(tiers['bear']['pullbacks'])

            # Check for open pullback
            current_pullback = None
            if pullbacks and pullbacks[-1]['open']:
                pb = pullbacks[-1]
                current_pullback = {
                    'magnitude': round(pb['magnitude'], 1),
                    'duration': pb['duration'],
                    'start_date': pd.Timestamp(pb['start_date']).strftime('%Y-%m-%d'),
                    'peak_price': round(pb['peak_price'], 2),
                    'peak_date': pd.Timestamp(pb['start_date']).strftime('%Y-%m-%d'),
                }

            stats = {
                'total': len(pullbacks),
                'median_magnitude': round(median_mag, 1),
                'median_duration_days': int(median_dur),
                'avg_duration_days': int(avg_dur),
                'frequency': round(frequency, 2),
                'bear_count': bear_count,
                'start_year': start_year,
                'end_year': end_year,
                'start_price': round(float(prices[0]), 2),
                'end_price': round(float(prices[-1]), 2),
                'tiers': tier_stats,
                'current_pullback': current_pullback,
            }

            # Print progress
            print(f"  Detected {len(pullbacks)} pullbacks (5%+ declines)")
            print(f"  Routine: {tier_stats['routine']['count']}, Meaningful: {tier_stats['meaningful']['count']}, " +
                  f"Beyond Normal: {tier_stats['beyond_normal']['count']}, Bear: {tier_stats['bear']['count']}")

            return stats
        else:
            print(f"  No pullbacks detected")
            return {}

    except Exception as e:
        print(f"  ⚠️  Error analyzing pullbacks: {e}")
        import traceback
        traceback.print_exc()
        return {}


# ═══════════════════════════════════════════════════════════
# STEP 7: ASSEMBLE AND SAVE
# ═══════════════════════════════════════════════════════════

def assemble_output(stocks, market, macro, breadth, sectors, signals, skipped_count=0, pullback_stats=None, auto_data=None, industries=None):
    """Package everything into the JSON structure the dashboard expects."""
    if auto_data is None:
        auto_data = {}
    
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
            "healthSkipped": signals.get("skipped", []),
            
            "trend": {
                "score": (
                    "Positive" if sp.get("price", 0) > sp.get("ma150", float('inf')) and sp.get("price", 0) > sp.get("ma4yr", float('inf'))
                    else "Negative" if sp.get("price", 0) < sp.get("ma150", float('inf')) and sp.get("price", 0) < sp.get("ma4yr", float('inf'))
                    else "Neutral"
                ),
                "r3kVs150MA": r3k_above,
                "maSlope": r3k.get("maSlope", "Unknown"),
            },
            
            "breadth": {
                "pctAbove": breadth.get("pctAbove", 0),
                "r3kPrice": r3k.get("price", 0),
                "r3kMA150": r3k.get("ma150", 0),
            },
            
            "macro": {
                # Nullable: None if source fetch failed (dashboard renders "—" instead of a stale default).
                "gdp":           (macro.get("gdp", {})           or {}).get("value"),
                "employment":    (macro.get("employment", {})    or {}).get("value"),
                "inflation":     (macro.get("inflation", {})     or {}).get("value"),
                "sentiment":     (macro.get("sentiment", {})     or {}).get("value"),
                "fedFunds":      (macro.get("fedFunds", {})      or {}).get("value"),
                "tenYear":       (macro.get("tenYear", {})       or {}).get("value"),
                "twoYear":       (macro.get("twoYear", {})       or {}).get("value"),
                "hySpread":      (macro.get("hySpread", {})      or {}).get("value"),
                "igSpread":      (macro.get("igSpread", {})      or {}).get("value"),
                "oil":           (market.get("oil", {})          or {}).get("price"),
                "dxy":           (market.get("dxy", {})          or {}).get("price"),
                "mortgage":      (macro.get("mortgage", {})      or {}).get("value"),
                "gasPrice":      (macro.get("gasPrice", {})      or {}).get("value"),
                "joblessClaims": (macro.get("joblessClaims", {}) or {}).get("value"),
                "ismPmi":        (macro.get("ismPmi", {})        or {}).get("value"),
                "fiscalPolicy":  MANUAL_INPUTS["policy"]["fiscal"],
                "monetaryPolicy":MANUAL_INPUTS["policy"]["monetary"],
                "geopolitical":  MANUAL_INPUTS["geopolitical"]["level"],
            },
            
            "fundamental": {
                **MANUAL_INPUTS["fundamental"],
                # Override with live EDGAR data where available
                **({"earningsGrowth": auto_data["edgar"]["earningsGrowth"]} if auto_data.get("edgar") and "earningsGrowth" in auto_data["edgar"] else {}),
                **({"salesGrowth": auto_data["edgar"]["salesGrowth"]} if auto_data.get("edgar") and "salesGrowth" in auto_data["edgar"] else {}),
                **({"netMargin": auto_data["edgar"]["netMargin"]} if auto_data.get("edgar") and "netMargin" in auto_data["edgar"] else {}),
                **({"marginTrend": auto_data["edgar"]["marginTrend"]} if auto_data.get("edgar") and "marginTrend" in auto_data["edgar"] else {}),
                **({"leverage": auto_data["edgar"]["leverage"]} if auto_data.get("edgar") and "leverage" in auto_data["edgar"] else {}),
                **({"capex": auto_data["edgar"]["capex"]} if auto_data.get("edgar") and "capex" in auto_data["edgar"] else {}),
                # Override divYield with live yfinance data if available
                "divYield": auto_data.get("divYield", {}).get("value", MANUAL_INPUTS["fundamental"]["divYield"]) if auto_data.get("divYield") else MANUAL_INPUTS["fundamental"]["divYield"],
            },

            "technical": {
                "sp500": sp.get("price", 0),
                "sp500MA4yr": sp.get("ma4yr", 0),
                "sp500MA150": sp.get("ma150", 0),
                "vix": market.get("vix", {}).get("price", 15),
                # Use auto-fetched put/call and AAII, fall back to manual
                "putCall": auto_data["putCall"]["value"] if auto_data.get("putCall") else MANUAL_INPUTS["sentiment"]["putCall"],
                "aaii": auto_data["aaii"]["value"] if auto_data.get("aaii") else MANUAL_INPUTS["sentiment"]["aaii"],
                "pctAbove20sma": breadth.get("pctAbove20sma"),
                "pctAt20dayLows": breadth.get("pctAt20dayLows"),
            },

            "synthesis": {
                "equities": {"view": "Overweight" if signals["score"] >= 70 else "Neutral" if signals["score"] >= 50 else "Underweight"},
                "fixedIncome": {"view": "Neutral"},
                "cash": {"view": "Underweight" if signals["score"] >= 60 else "Neutral"},
            },

            "dataAsOf": {
                # Macro — from FRED (auto-updated)
                "gdp": macro.get("gdp", {}).get("asOf", ""),
                "employment": macro.get("employment", {}).get("asOf", ""),
                "inflation": macro.get("inflation", {}).get("asOf", ""),
                "sentiment": macro.get("sentiment", {}).get("asOf", ""),
                "fedFunds": macro.get("fedFunds", {}).get("asOf", ""),
                "tenYear": macro.get("tenYear", {}).get("asOf", ""),
                "twoYear": macro.get("twoYear", {}).get("asOf", ""),
                "hySpread": macro.get("hySpread", {}).get("asOf", ""),
                "mortgage": macro.get("mortgage", {}).get("asOf", ""),
                "joblessClaims": macro.get("joblessClaims", {}).get("asOf", ""),
                "ismPmi": macro.get("ismPmi", {}).get("asOf", ""),
                # Prices — from yfinance (closing date)
                "prices": market.get("sp500_daily_dates", [""])[-1] if market.get("sp500_daily_dates") else "",
                # Fundamentals — EDGAR auto-fetch or manual update date
                "fundamentals": auto_data["edgar"]["asOf"] if auto_data.get("edgar") else MANUAL_INPUTS["fundamental"].get("_lastUpdated", "2026-03-25"),
                "fundamentalsSource": auto_data["edgar"]["source"] if auto_data.get("edgar") else "manual",
                # Sentiment — auto-tracked from live feeds or fallback
                "putCall": auto_data["putCall"]["asOf"] if auto_data.get("putCall") else MANUAL_INPUTS["fundamental"].get("_lastUpdated", ""),
                "aaii": auto_data["aaii"]["asOf"] if auto_data.get("aaii") else MANUAL_INPUTS["fundamental"].get("_lastUpdated", ""),
            },
        },
        
        # ── S&P 500 Chart Data (3-year daily) ──
        "sp500_daily_prices": market.get("sp500_daily_prices", []),
        "sp500_daily_dates": market.get("sp500_daily_dates", []),
        
        "sectors": sectors,
        "industries": industries or [],
        
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
            "tr1wk": s.get("trend1wk", "Unknown"),
            "trChg": s.get("trendChanged", False),
            # Research fields
            "tpe": s.get("tpe"), "fpe": s.get("fpe"), "eps": s.get("eps"), "feps": s.get("feps"),
            "rg": s.get("rg"), "gm": s.get("gm"), "om": s.get("om"), "pm": s.get("pm"),
            "dy": s.get("dy"), "beta": s.get("beta"), "tgt": s.get("tgt"), "nAn": s.get("nAn"),
            "hi52": s.get("hi52"), "lo52": s.get("lo52"),
            "ev": s.get("ev"), "evr": s.get("evr"), "eve": s.get("eve"), "pb": s.get("pb"),
        } for s in sorted(stocks, key=lambda x: x.get("mktCap", 0), reverse=True)],

        "skipped": skipped_count,
        "pullbackStats": pullback_stats or {},
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

    # 2. Pull market data FIRST (before rate limits kick in from stock universe)
    market = pull_market_data()

    # 3. Pull stock data (1,200+ individual calls — uses up the API budget)
    stocks, skipped = pull_stock_data(tickers)

    # 3b. Track delisted/acquired tickers (skipped for N+ consecutive days)
    pending_removal = update_skipped_history(stocks, skipped, tickers)
    
    # 4. Pull FRED data
    macro = pull_fred_data()

    # 4b. Analyze pullback history
    pullback_stats = analyze_pullbacks()

    # 4c. Auto-fetch sentiment & valuation data
    auto_putcall = fetch_cboe_putcall()
    auto_aaii = fetch_aaii_sentiment()
    auto_pe = fetch_trailing_pe()
    auto_divyield = fetch_dividend_yield()

    # 4d. Auto-fetch trailing fundamentals from SEC EDGAR
    auto_edgar = fetch_edgar_fundamentals()

    # Merge auto-fetched data into a dict for downstream use
    auto_data = {
        "putCall": auto_putcall,    # {"value": 0.85, "asOf": "2026-03-25", "source": "CBOE"} or None
        "aaii": auto_aaii,          # {"value": 30.4, "asOf": "2026-03-19", "source": "..."} or None
        "trailingPE": auto_pe,      # {"trailingPE": 22.5, "asOf": "...", "source": "DataHub"} or None
        "divYield": auto_divyield,  # {"value": 1.3, "asOf": "...", "source": "yfinance"} or None
        "edgar": auto_edgar,        # {"earningsGrowth": 11.5, "salesGrowth": 8.0, ...} or None
    }

    # 5. Calculate summaries
    breadth, sectors, industries = calculate_summaries(stocks)

    # 6. Calculate signals (pass auto_data so it uses live put/call if available)
    signals = calculate_signals(market, breadth, macro, auto_data=auto_data)

    # 7. Assemble and save
    output = assemble_output(stocks, market, macro, breadth, sectors, signals,
                             skipped_count=len(skipped), pullback_stats=pullback_stats,
                             auto_data=auto_data, industries=industries)
    output["pendingRemoval"] = pending_removal
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    elapsed = time.time() - start_time
    
    print(f"\n{'═'*60}")
    print(f"  ✅ COMPLETE — {elapsed:.0f} seconds")
    print(f"  📁 Saved to: {OUTPUT_FILE}")
    print(f"  📊 Stocks: {len(stocks)} processed, {len(skipped)} skipped")
    print(f"  🎯 Health Score: {signals['score']}/{signals['total']}")
    chart_count = len(output.get('sp500_daily_prices', []))
    if chart_count > 0:
        print(f"  📈 Chart: {chart_count} daily S&P 500 prices")

    # Data source summary
    edgar_ok = auto_data.get("edgar") is not None
    edgar_metrics = list(auto_data["edgar"].keys()) if edgar_ok else []
    print(f"\n  📡 Data Sources:")
    # FRED per-series status (reports missing series loudly instead of blanket ✅ Auto)
    FRED_TRACKED = [
        ("employment",   "Unemployment"),
        ("gdp",          "GDP Growth"),
        ("inflation",    "Inflation"),
        ("hySpread",     "HY Credit Spreads"),
        ("sentiment",    "Consumer Sentiment"),
        ("mortgage",     "Mortgage Rate"),
        ("tenYear",      "10-Year Yield"),
        ("twoYear",      "2-Year Yield"),
        ("ismPmi",       "ISM PMI"),
        ("gasPrice",     "Gas Price"),
        ("joblessClaims","Jobless Claims"),
        ("fedFunds",     "Fed Funds"),
    ]
    fred_ok = [lab for k, lab in FRED_TRACKED if macro.get(k, {}).get("value") is not None]
    fred_missing = [lab for k, lab in FRED_TRACKED if macro.get(k, {}).get("value") is None]
    if not fred_missing:
        print(f"     Macro (FRED):     ✅ Auto — all {len(fred_ok)} series live")
    else:
        print(f"     Macro (FRED):     ⚠️  {len(fred_ok)}/{len(FRED_TRACKED)} live — MISSING: {', '.join(fred_missing)}")
    print(f"     Prices (yfinance):✅ Auto — S&P 500, VIX, oil, DXY, all stocks")
    print(f"     Breadth:          ✅ Auto — calculated from stock universe")
    print(f"     Pullbacks:        ✅ Auto — historical CSV + pullback engine")
    print(f"     Put/Call:         {'✅ Auto — CBOE live (' + str(auto_putcall['value']) + ')' if auto_putcall else '⚠️  Manual fallback (' + str(MANUAL_INPUTS['sentiment']['putCall']) + ')'}")
    print(f"     AAII Sentiment:   {'✅ Auto — Nasdaq Data Link (' + str(auto_aaii['value']) + '%)' if auto_aaii else '⚠️  Manual fallback (' + str(MANUAL_INPUTS['sentiment']['aaii']) + '%)'}")
    print(f"     Trailing P/E:    {'✅ Auto — DataHub (' + str(auto_pe['trailingPE']) + ')' if auto_pe else '⚠️  Not available'}")
    print(f"     Dividend Yield:  {'✅ Auto — yfinance (' + str(auto_divyield['value']) + '%)' if auto_divyield else '⚠️  Manual fallback'}")
    print(f"     ── SEC EDGAR Fundamentals ──")
    print(f"     Earnings Growth:  {'✅ Auto — EDGAR (' + str(auto_data['edgar']['earningsGrowth']) + '%)' if edgar_ok and 'earningsGrowth' in edgar_metrics else '⚠️  Manual fallback (' + str(MANUAL_INPUTS['fundamental']['earningsGrowth']) + '%)'}")
    print(f"     Sales Growth:     {'✅ Auto — EDGAR (' + str(auto_data['edgar']['salesGrowth']) + '%)' if edgar_ok and 'salesGrowth' in edgar_metrics else '⚠️  Manual fallback (' + str(MANUAL_INPUTS['fundamental']['salesGrowth']) + '%)'}")
    print(f"     Net Margin:       {'✅ Auto — EDGAR (' + str(auto_data['edgar']['netMargin']) + '%)' if edgar_ok and 'netMargin' in edgar_metrics else '⚠️  Manual fallback (' + str(MANUAL_INPUTS['fundamental']['netMargin']) + '%)'}")
    print(f"     Leverage:         {'✅ Auto — EDGAR (' + str(auto_data['edgar']['leverage']) + 'x D/E)' if edgar_ok and 'leverage' in edgar_metrics else '⚠️  Manual fallback (' + str(MANUAL_INPUTS['fundamental']['leverage']) + 'x)'}")
    print(f"     Capex Growth:     {'✅ Auto — EDGAR (' + str(auto_data['edgar']['capex']) + '%)' if edgar_ok and 'capex' in edgar_metrics else '⚠️  Manual fallback (' + str(MANUAL_INPUTS['fundamental']['capex']) + '%)'}")
    print(f"     ── Still Manual (FactSet / Analyst Data) ──")
    print(f"   * Beat Rates:       ⚠️  Manual — update quarterly (FactSet Earnings Insight)")
    print(f"   * Forward P/E:      ⚠️  Manual — update quarterly (FactSet)")
    print(f"   * Revisions:        ⚠️  Manual — update quarterly (FactSet)")
    print(f"   * PEG Ratio:        ⚠️  Manual — needs forward growth estimate")
    print(f"   * FCF/Buyback Yld:  ⚠️  Manual — update quarterly")
    print(f"   * Geopolitical:     ⚠️  Manual — update as conditions change")
    print(f"   * Fiscal/Monetary:  ⚠️  Manual — update after Fed meetings")
    print(f"")
    print(f"     * = requires manual update in MANUAL_INPUTS section")
    print(f"{'═'*60}")


if __name__ == "__main__":
    main()
