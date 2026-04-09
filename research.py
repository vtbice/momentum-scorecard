#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  PROSPER MOMENTUM — Company Research Page Generator
═══════════════════════════════════════════════════════════════
  Generates a standalone HTML research page for any company.

  Usage:
    python3 research.py NVDA          # Public company (auto-pulls data)
    python3 research.py "Acme Corp"   # Private company (blank template)
    python3 research.py --refresh-all # Refresh all previously researched public companies

  Output:
    research/NVDA.html                # Standalone research page
    research/research_index.json      # Registry of all researched companies
═══════════════════════════════════════════════════════════════
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Fix SSL certificates before importing yfinance
# (yfinance uses curl_cffi which needs the macOS system cert bundle)
_MACOS_CERTS = "/etc/ssl/cert.pem"
if os.path.exists(_MACOS_CERTS):
    os.environ.setdefault("SSL_CERT_FILE", _MACOS_CERTS)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _MACOS_CERTS)
    os.environ.setdefault("CURL_CA_BUNDLE", _MACOS_CERTS)

import yfinance as yf
import pandas as pd
import numpy as np

# ─── PATHS ────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
RESEARCH_DIR = SCRIPT_DIR / "research"
INDEX_FILE = RESEARCH_DIR / "research_index.json"

RESEARCH_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════════

def fetch_company_data(ticker):
    """Pull all available data for a public company from yfinance."""
    print(f"\n📡 Fetching data for {ticker}...")
    data = {"ticker": ticker, "type": "public"}

    t = yf.Ticker(ticker)

    # ── Company info ──
    try:
        info = t.info
        data["name"] = info.get("longName", info.get("shortName", ticker))
        data["sector"] = info.get("sector", "Unknown")
        data["industry"] = info.get("industry", "Unknown")
        data["description"] = info.get("longBusinessSummary", "")
        data["price"] = info.get("currentPrice", info.get("regularMarketPrice", 0))
        data["marketCap"] = info.get("marketCap", 0)
        data["enterpriseValue"] = info.get("enterpriseValue", 0)
        data["fiftyTwoWeekHigh"] = info.get("fiftyTwoWeekHigh", 0)
        data["fiftyTwoWeekLow"] = info.get("fiftyTwoWeekLow", 0)
        data["beta"] = info.get("beta", None)
        data["currency"] = info.get("currency", "USD")
        data["exchange"] = info.get("exchange", "")
        data["website"] = info.get("website", "")
        data["employees"] = info.get("fullTimeEmployees", None)
        data["fiscalYearEnd"] = info.get("lastFiscalYearEnd", None)

        # Valuation
        data["trailingPE"] = info.get("trailingPE", None)
        data["forwardPE"] = info.get("forwardPE", None)
        data["pegRatio"] = info.get("pegRatio", None)
        data["priceToBook"] = info.get("priceToBook", None)
        data["evToRevenue"] = info.get("enterpriseToRevenue", None)
        data["evToEbitda"] = info.get("enterpriseToEbitda", None)

        # Profitability
        data["grossMargins"] = info.get("grossMargins", None)
        data["operatingMargins"] = info.get("operatingMargins", None)
        data["profitMargins"] = info.get("profitMargins", None)

        # Growth
        data["revenueGrowth"] = info.get("revenueGrowth", None)
        data["earningsGrowth"] = info.get("earningsGrowth", None)

        # Per share
        data["trailingEps"] = info.get("trailingEps", None)
        data["forwardEps"] = info.get("forwardEps", None)
        data["dividendYield"] = info.get("dividendYield", None)
        data["dividendRate"] = info.get("dividendRate", None)

        # Analyst
        data["targetMean"] = info.get("targetMeanPrice", None)
        data["targetHigh"] = info.get("targetHighPrice", None)
        data["targetLow"] = info.get("targetLowPrice", None)
        data["analystCount"] = info.get("numberOfAnalystOpinions", None)
        data["recommendation"] = info.get("recommendationKey", None)

        # Balance sheet items from info
        data["totalCash"] = info.get("totalCash", None)
        data["totalDebt"] = info.get("totalDebt", None)
        data["freeCashflow"] = info.get("freeCashflow", None)

        print(f"  ✅ Company: {data['name']} ({data['sector']})")
        print(f"  ✅ Price: ${data['price']:.2f} | Market Cap: ${data['marketCap']/1e9:.1f}B")
    except Exception as e:
        print(f"  ⚠️  Info fetch failed: {e}")
        return None

    # ── Income Statement (annual) ──
    try:
        inc = t.income_stmt
        if inc is not None and not inc.empty:
            years = []
            for col in sorted(inc.columns):
                year_data = {}
                year_data["date"] = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
                year_data["label"] = col.strftime("FY%Y") if hasattr(col, "strftime") else str(col)
                for row_name in inc.index:
                    val = inc.loc[row_name, col]
                    if pd.notna(val):
                        year_data[row_name] = float(val)
                years.append(year_data)
            data["incomeStatement"] = years
            print(f"  ✅ Income statement: {len(years)} years")
        else:
            data["incomeStatement"] = []
            print(f"  ⚠️  No income statement data")
    except Exception as e:
        data["incomeStatement"] = []
        print(f"  ⚠️  Income statement: {e}")

    # ── Balance Sheet (latest) ──
    try:
        bs = t.balance_sheet
        if bs is not None and not bs.empty:
            latest = bs.iloc[:, 0]
            data["balanceSheet"] = {
                "date": bs.columns[0].strftime("%Y-%m-%d") if hasattr(bs.columns[0], "strftime") else str(bs.columns[0]),
                "totalAssets": float(latest.get("Total Assets", 0)) if pd.notna(latest.get("Total Assets")) else None,
                "totalDebtBS": float(latest.get("Total Debt", 0)) if pd.notna(latest.get("Total Debt")) else None,
                "cashAndEquivalents": float(latest.get("Cash And Cash Equivalents", 0)) if pd.notna(latest.get("Cash And Cash Equivalents")) else None,
                "stockholdersEquity": float(latest.get("Stockholders Equity", 0)) if pd.notna(latest.get("Stockholders Equity")) else None,
            }
            print(f"  ✅ Balance sheet loaded")
        else:
            data["balanceSheet"] = {}
    except Exception as e:
        data["balanceSheet"] = {}
        print(f"  ⚠️  Balance sheet: {e}")

    # ── Cash Flow (latest 4 years) ──
    try:
        cf = t.cashflow
        if cf is not None and not cf.empty:
            cf_years = []
            for col in sorted(cf.columns):
                cf_data = {
                    "date": col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col),
                    "label": col.strftime("FY%Y") if hasattr(col, "strftime") else str(col),
                }
                for row_name in cf.index:
                    val = cf.loc[row_name, col]
                    if pd.notna(val):
                        cf_data[row_name] = float(val)
                cf_years.append(cf_data)
            data["cashFlow"] = cf_years
            print(f"  ✅ Cash flow: {len(cf_years)} years")
        else:
            data["cashFlow"] = []
    except Exception as e:
        data["cashFlow"] = []
        print(f"  ⚠️  Cash flow: {e}")

    # ── Price History (1 year for chart) ──
    try:
        hist = t.history(period="1y")
        if not hist.empty:
            data["priceHistory"] = {
                "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
                "prices": [round(float(p), 2) for p in hist["Close"]],
            }
            print(f"  ✅ Price history: {len(hist)} days")
        else:
            data["priceHistory"] = {"dates": [], "prices": []}
    except Exception as e:
        data["priceHistory"] = {"dates": [], "prices": []}
        print(f"  ⚠️  Price history: {e}")

    data["fetchedAt"] = datetime.now().isoformat()
    return data


# ═══════════════════════════════════════════════════════════
# HTML GENERATION
# ═══════════════════════════════════════════════════════════

def fmt_num(val, prefix="$", suffix="", decimals=1):
    """Format a number with $ prefix and B/M/K suffix."""
    if val is None:
        return "N/A"
    if abs(val) >= 1e12:
        return f"{prefix}{val/1e12:.{decimals}f}T{suffix}"
    if abs(val) >= 1e9:
        return f"{prefix}{val/1e9:.{decimals}f}B{suffix}"
    if abs(val) >= 1e6:
        return f"{prefix}{val/1e6:.{decimals}f}M{suffix}"
    if abs(val) >= 1e3:
        return f"{prefix}{val/1e3:.{decimals}f}K{suffix}"
    return f"{prefix}{val:.{decimals}f}{suffix}"


def fmt_pct(val, decimals=1):
    """Format a decimal as percentage."""
    if val is None:
        return "N/A"
    return f"{val * 100:.{decimals}f}%"


def fmt_price(val):
    """Format a price value."""
    if val is None or val == 0:
        return "N/A"
    return f"${val:,.2f}"


def pct_color(val):
    """Return CSS color class for a percentage value."""
    if val is None:
        return "#64748b"
    return "#10b981" if val >= 0 else "#ef4444"


def generate_html(data):
    """Generate a standalone HTML research page."""
    ticker = data["ticker"]
    name = data.get("name", ticker)
    is_public = data["type"] == "public"

    # ── Income statement rows ──
    inc_rows = ""
    inc_years = data.get("incomeStatement", [])
    if inc_years:
        # Build header
        inc_header = "<th style='text-align:left;'>Metric</th>"
        for yr in inc_years:
            inc_header += f"<th>{yr['label']}</th>"

        # Revenue row
        inc_rows += "<tr class='row-total'><td>Revenue</td>"
        for yr in inc_years:
            val = yr.get("Total Revenue", yr.get("Revenue", None))
            inc_rows += f"<td>{fmt_num(val)}</td>"
        inc_rows += "</tr>"

        # YoY Revenue Growth
        inc_rows += "<tr style='background:#f0fdf4;'><td style='color:#10b981;font-weight:600;'>YoY Growth</td>"
        prev_rev = None
        for yr in inc_years:
            val = yr.get("Total Revenue", yr.get("Revenue", None))
            if prev_rev and val and prev_rev > 0:
                growth = (val / prev_rev - 1) * 100
                color = "#10b981" if growth >= 0 else "#ef4444"
                inc_rows += f"<td style='color:{color};font-weight:600;'>{'+' if growth >= 0 else ''}{growth:.1f}%</td>"
            else:
                inc_rows += "<td style='color:#64748b;'>—</td>"
            prev_rev = val
        inc_rows += "</tr>"

        # Gross Profit
        inc_rows += "<tr><td>Gross Profit</td>"
        for yr in inc_years:
            val = yr.get("Gross Profit", None)
            inc_rows += f"<td>{fmt_num(val)}</td>"
        inc_rows += "</tr>"

        # Gross Margin
        inc_rows += "<tr style='background:#f8fafc;'><td style='color:#64748b;'>Gross Margin</td>"
        for yr in inc_years:
            gp = yr.get("Gross Profit", None)
            rev = yr.get("Total Revenue", yr.get("Revenue", None))
            if gp and rev and rev > 0:
                inc_rows += f"<td>{gp/rev*100:.1f}%</td>"
            else:
                inc_rows += "<td>—</td>"
        inc_rows += "</tr>"

        # Operating Income
        inc_rows += "<tr><td>Operating Income</td>"
        for yr in inc_years:
            val = yr.get("Operating Income", yr.get("EBIT", None))
            inc_rows += f"<td>{fmt_num(val)}</td>"
        inc_rows += "</tr>"

        # Operating Margin
        inc_rows += "<tr style='background:#f8fafc;'><td style='color:#64748b;'>Operating Margin</td>"
        for yr in inc_years:
            oi = yr.get("Operating Income", yr.get("EBIT", None))
            rev = yr.get("Total Revenue", yr.get("Revenue", None))
            if oi and rev and rev > 0:
                inc_rows += f"<td>{oi/rev*100:.1f}%</td>"
            else:
                inc_rows += "<td>—</td>"
        inc_rows += "</tr>"

        # Net Income
        inc_rows += "<tr class='row-total'><td>Net Income</td>"
        for yr in inc_years:
            val = yr.get("Net Income", yr.get("Net Income Common Stockholders", None))
            inc_rows += f"<td>{fmt_num(val)}</td>"
        inc_rows += "</tr>"

        # EPS
        inc_rows += "<tr><td>Diluted EPS</td>"
        for yr in inc_years:
            val = yr.get("Diluted EPS", yr.get("Basic EPS", None))
            if val is not None:
                inc_rows += f"<td>${val:.2f}</td>"
            else:
                inc_rows += "<td>—</td>"
        inc_rows += "</tr>"
    else:
        inc_header = "<th>No income statement data available</th>"

    # ── Cash flow rows ──
    cf_rows = ""
    cf_years = data.get("cashFlow", [])
    if cf_years:
        cf_header = "<th style='text-align:left;'>Metric</th>"
        for yr in cf_years:
            cf_header += f"<th>{yr['label']}</th>"

        cf_rows += "<tr><td>Operating Cash Flow</td>"
        for yr in cf_years:
            val = yr.get("Operating Cash Flow", yr.get("Cash Flow From Continuing Operating Activities", None))
            cf_rows += f"<td>{fmt_num(val)}</td>"
        cf_rows += "</tr>"

        cf_rows += "<tr><td>Capital Expenditure</td>"
        for yr in cf_years:
            val = yr.get("Capital Expenditure", None)
            cf_rows += f"<td>{fmt_num(val)}</td>"
        cf_rows += "</tr>"

        cf_rows += "<tr class='row-total'><td>Free Cash Flow</td>"
        for yr in cf_years:
            ocf = yr.get("Operating Cash Flow", yr.get("Cash Flow From Continuing Operating Activities", None))
            capex = yr.get("Capital Expenditure", None)
            if ocf is not None and capex is not None:
                fcf = ocf + capex  # capex is negative
                cf_rows += f"<td>{fmt_num(fcf)}</td>"
            else:
                val = yr.get("Free Cash Flow", None)
                cf_rows += f"<td>{fmt_num(val)}</td>"
        cf_rows += "</tr>"
    else:
        cf_header = "<th>No cash flow data available</th>"

    # ── Price chart data ──
    price_dates = json.dumps(data.get("priceHistory", {}).get("dates", []))
    price_vals = json.dumps(data.get("priceHistory", {}).get("prices", []))

    # ── KPI values ──
    price = data.get("price", 0)
    mktcap = data.get("marketCap", 0)
    trailing_pe = data.get("trailingPE")
    forward_pe = data.get("forwardPE")
    target_mean = data.get("targetMean")
    trailing_eps = data.get("trailingEps")
    revenue_growth = data.get("revenueGrowth")
    analyst_count = data.get("analystCount")

    upside = None
    if target_mean and price and price > 0:
        upside = (target_mean / price - 1) * 100

    # ── Balance sheet values ──
    bs = data.get("balanceSheet", {})
    bs_date = bs.get("date", "")

    # ── Build HTML ──
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ticker} — Company Research | Momentum Scorecard</title>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600;700;900&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'DM Sans', sans-serif; background: #f8fafc; color: #0f172a; font-size: 14px; line-height: 1.6; }}

        header {{
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            padding: 28px 32px 24px;
            border-bottom: 3px solid #10b981;
            color: white;
        }}
        .header-content {{
            max-width: 1280px; margin: 0 auto;
            display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 16px;
        }}
        .header-left h1 {{
            font-family: 'Fraunces', serif; font-size: 28px; font-weight: 700;
        }}
        .header-left h1 .ticker {{ color: #10b981; }}
        .header-sub {{ font-size: 13px; color: #94a3b8; margin-top: 4px; }}
        .header-tags {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }}
        .tag {{
            display: inline-block; background: rgba(16,185,129,0.15); color: #10b981;
            border: 1px solid rgba(16,185,129,0.4); border-radius: 4px;
            font-size: 10px; font-weight: 600; padding: 2px 8px;
            text-transform: uppercase; letter-spacing: 0.5px;
        }}
        .header-right {{ text-align: right; }}
        .price-big {{ font-family: 'Fraunces', serif; font-size: 32px; font-weight: 700; color: #10b981; }}
        .price-meta {{ font-size: 11px; color: #94a3b8; margin-top: 2px; }}

        main {{ max-width: 1280px; margin: 28px auto; padding: 0 24px; }}
        .section {{ margin-bottom: 28px; }}
        .section-title {{
            font-family: 'Fraunces', serif; font-size: 18px; font-weight: 700;
            color: #0f172a; margin-bottom: 14px;
            border-left: 3px solid #10b981; padding-left: 12px;
        }}
        .card {{
            background: white; border-radius: 12px; padding: 20px 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;
        }}
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
        .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }}
        .grid-5 {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }}
        .grid-6 {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 14px; }}

        /* KPI Cards */
        .kpi-card {{
            background: white; border-radius: 10px; padding: 16px 18px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;
            border-top: 3px solid #1e293b;
        }}
        .kpi-card.green {{ border-top-color: #10b981; }}
        .kpi-card.amber {{ border-top-color: #f59e0b; }}
        .kpi-label {{
            font-size: 10px; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.6px; color: #64748b; margin-bottom: 6px;
        }}
        .kpi-value {{
            font-family: 'JetBrains Mono', monospace; font-size: 22px; font-weight: 700; color: #0f172a;
        }}
        .kpi-sub {{ font-size: 11px; color: #64748b; margin-top: 4px; }}
        .kpi-badge {{
            display: inline-block; padding: 2px 7px; border-radius: 4px;
            font-size: 10px; font-weight: 600;
        }}
        .badge-up {{ background: #dcfce7; color: #16a34a; }}
        .badge-dn {{ background: #fee2e2; color: #dc2626; }}

        /* Tables */
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        thead tr {{ background: #0f172a; color: white; }}
        thead th {{
            padding: 10px 12px; text-align: right; font-weight: 600;
            font-size: 11px; letter-spacing: 0.4px; white-space: nowrap;
        }}
        thead th:first-child {{ text-align: left; }}
        tbody tr {{ border-bottom: 1px solid #e2e8f0; }}
        tbody tr:hover {{ background: #f8fafc; }}
        tbody td {{ padding: 9px 12px; text-align: right; font-family: 'JetBrains Mono', monospace; font-size: 12px; white-space: nowrap; }}
        tbody td:first-child {{ text-align: left; font-family: 'DM Sans', sans-serif; font-weight: 500; color: #0f172a; }}
        .row-total td {{ background: #f0f4f8; font-weight: 700; color: #0f172a; }}

        /* Valuation rows */
        .val-row {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 10px 0; border-bottom: 1px solid #e2e8f0;
        }}
        .val-row:last-child {{ border-bottom: none; }}
        .val-label {{ font-size: 13px; color: #64748b; }}
        .val-value {{ font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 700; color: #0f172a; }}

        /* Scenario grid */
        .scenario-grid {{
            display: grid; grid-template-columns: 2fr 1fr 1fr 1fr;
            border-radius: 10px; overflow: hidden; border: 1px solid #e2e8f0;
        }}
        .sc-hdr {{ padding: 12px 16px; font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; text-align: center; }}
        .sc-hdr.label {{ background: #0f172a; color: white; text-align: left; }}
        .sc-hdr.bear {{ background: #7f1d1d; color: white; }}
        .sc-hdr.base {{ background: #1e293b; color: white; }}
        .sc-hdr.bull {{ background: #14532d; color: white; }}
        .sc-cell {{ padding: 10px 16px; border-bottom: 1px solid #e2e8f0; font-size: 13px; text-align: center; }}
        .sc-cell.label {{ text-align: left; font-weight: 500; color: #0f172a; background: #fafafa; }}
        .sc-cell.bear {{ color: #ef4444; font-weight: 600; background: #fef2f2; }}
        .sc-cell.base {{ color: #1e293b; font-weight: 600; background: #f0f5ff; }}
        .sc-cell.bull {{ color: #10b981; font-weight: 600; background: #f0fdf4; }}

        /* Chart */
        .chart-wrap {{ position: relative; height: 280px; }}

        /* Notes section */
        .notes-box {{
            background: #f8fafc; border: 2px dashed #e2e8f0; border-radius: 10px;
            padding: 20px; min-height: 100px;
        }}
        .notes-placeholder {{ color: #94a3b8; font-style: italic; font-size: 13px; }}

        /* Footer */
        .footer {{
            background: #0f172a; color: #64748b; font-size: 10px;
            padding: 18px 40px; text-align: center; margin-top: 40px; line-height: 1.8;
        }}
        .footer strong {{ color: #10b981; }}

        /* Back link */
        .back-link {{
            display: inline-block; margin-bottom: 16px; font-size: 13px;
            color: #10b981; text-decoration: none; font-weight: 600;
        }}
        .back-link:hover {{ text-decoration: underline; }}

        @media (max-width: 900px) {{
            .grid-5, .grid-6 {{ grid-template-columns: repeat(3, 1fr); }}
            .grid-4 {{ grid-template-columns: repeat(2, 1fr); }}
            .grid-2, .grid-3 {{ grid-template-columns: 1fr; }}
            .scenario-grid {{ grid-template-columns: 1fr; }}
            .header-content {{ flex-direction: column; text-align: center; }}
            .header-right {{ text-align: center; }}
        }}
    </style>
</head>
<body>

<header>
    <div class="header-content">
        <div class="header-left">
            <h1><span class="ticker">{ticker}</span> &middot; {name}</h1>
            <div class="header-sub">Company Research | Momentum Investor Framework | Generated {datetime.now().strftime("%B %d, %Y")}</div>
            <div class="header-tags">
                <span class="tag">{data.get("exchange", "")} &middot; {ticker}</span>
                <span class="tag">{data.get("sector", "Unknown")} / {data.get("industry", "Unknown")}</span>
                {"<span class='tag'>" + str(f'{data["employees"]:,}') + " employees</span>" if data.get("employees") else ""}
                <span class="tag">{datetime.now().strftime("%B %d, %Y")}</span>
            </div>
        </div>
        <div class="header-right">
            <div class="price-big">{fmt_price(price)}</div>
            <div class="price-meta">Market Cap: {fmt_num(mktcap)}</div>
            <div class="price-meta">52-Week Range: {fmt_price(data.get("fiftyTwoWeekLow"))} &ndash; {fmt_price(data.get("fiftyTwoWeekHigh"))}</div>
        </div>
    </div>
</header>

<main>

<!-- KPI CARDS -->
<div class="section">
    <div class="section-title">Key Metrics</div>
    <div class="grid-6">
        <div class="kpi-card">
            <div class="kpi-label">Trailing P/E</div>
            <div class="kpi-value">{f"{trailing_pe:.1f}x" if trailing_pe else "N/A"}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Forward P/E</div>
            <div class="kpi-value">{f"{forward_pe:.1f}x" if forward_pe else "N/A"}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Trailing EPS</div>
            <div class="kpi-value">{f"${trailing_eps:.2f}" if trailing_eps else "N/A"}</div>
        </div>
        <div class="kpi-card{' green' if revenue_growth and revenue_growth > 0 else ''}">
            <div class="kpi-label">Revenue Growth</div>
            <div class="kpi-value">{fmt_pct(revenue_growth) if revenue_growth else "N/A"}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Gross Margin</div>
            <div class="kpi-value">{fmt_pct(data.get("grossMargins")) if data.get("grossMargins") else "N/A"}</div>
        </div>
        <div class="kpi-card{' green' if upside and upside > 0 else ''}">
            <div class="kpi-label">Analyst Target</div>
            <div class="kpi-value">{fmt_price(target_mean) if target_mean else "N/A"}</div>
            <div class="kpi-sub">{f'<span class="kpi-badge {"badge-up" if upside >= 0 else "badge-dn"}">{("+" if upside >= 0 else "")}{upside:.1f}%</span> ({analyst_count} analysts)' if upside is not None and analyst_count else ""}</div>
        </div>
    </div>
</div>

<!-- PRICE CHART -->
<div class="section">
    <div class="section-title">1-Year Price Chart</div>
    <div class="card">
        <div class="chart-wrap"><canvas id="priceChart"></canvas></div>
    </div>
</div>

<!-- BUSINESS DESCRIPTION -->
{"<div class='section'><div class='section-title'>Business Overview</div><div class='card'><p style='font-size:14px;color:#475569;line-height:1.7;'>" + data.get("description", "")[:800] + ("..." if len(data.get("description", "")) > 800 else "") + "</p></div></div>" if data.get("description") else ""}

<!-- INCOME STATEMENT -->
<div class="section">
    <div class="section-title">Income Statement (Annual)</div>
    <div class="card">
        <div style="overflow-x:auto;">
            <table>
                <thead><tr>{inc_header}</tr></thead>
                <tbody>{inc_rows}</tbody>
            </table>
        </div>
        <div style="margin-top:10px;font-size:11px;color:#94a3b8;">
            Source: Yahoo Finance. All figures in USD.
        </div>
    </div>
</div>

<!-- TWO COLUMN: VALUATION + BALANCE SHEET -->
<div class="section">
    <div class="grid-2">
        <div>
            <div class="section-title">Valuation</div>
            <div class="card">
                <div class="val-row">
                    <div class="val-label">Market Cap</div>
                    <div class="val-value">{fmt_num(mktcap)}</div>
                </div>
                <div class="val-row">
                    <div class="val-label">Enterprise Value</div>
                    <div class="val-value">{fmt_num(data.get("enterpriseValue")) if data.get("enterpriseValue") else "N/A"}</div>
                </div>
                <div class="val-row">
                    <div class="val-label">Trailing P/E</div>
                    <div class="val-value">{f"{trailing_pe:.1f}x" if trailing_pe else "N/A"}</div>
                </div>
                <div class="val-row">
                    <div class="val-label">Forward P/E</div>
                    <div class="val-value">{f"{forward_pe:.1f}x" if forward_pe else "N/A"}</div>
                </div>
                <div class="val-row">
                    <div class="val-label">PEG Ratio</div>
                    <div class="val-value">{f"{data['pegRatio']:.2f}" if data.get("pegRatio") else "N/A"}</div>
                </div>
                <div class="val-row">
                    <div class="val-label">EV / Revenue</div>
                    <div class="val-value">{f"{data['evToRevenue']:.1f}x" if data.get("evToRevenue") else "N/A"}</div>
                </div>
                <div class="val-row">
                    <div class="val-label">EV / EBITDA</div>
                    <div class="val-value">{f"{data['evToEbitda']:.1f}x" if data.get("evToEbitda") else "N/A"}</div>
                </div>
                <div class="val-row">
                    <div class="val-label">Price / Book</div>
                    <div class="val-value">{f"{data['priceToBook']:.1f}x" if data.get("priceToBook") else "N/A"}</div>
                </div>
                <div class="val-row">
                    <div class="val-label">Dividend Yield</div>
                    <div class="val-value">{fmt_pct(data.get("dividendYield")) if data.get("dividendYield") else "N/A"}</div>
                </div>
                <div class="val-row">
                    <div class="val-label">Beta</div>
                    <div class="val-value">{f"{data['beta']:.2f}" if data.get("beta") else "N/A"}</div>
                </div>
            </div>
        </div>
        <div>
            <div class="section-title">Balance Sheet{f" ({bs_date[:4]})" if bs_date else ""}</div>
            <div class="card">
                <div class="val-row">
                    <div class="val-label">Total Assets</div>
                    <div class="val-value">{fmt_num(bs.get("totalAssets"))}</div>
                </div>
                <div class="val-row">
                    <div class="val-label">Total Debt</div>
                    <div class="val-value">{fmt_num(bs.get("totalDebtBS", data.get("totalDebt")))}</div>
                </div>
                <div class="val-row">
                    <div class="val-label">Cash &amp; Equivalents</div>
                    <div class="val-value">{fmt_num(bs.get("cashAndEquivalents", data.get("totalCash")))}</div>
                </div>
                <div class="val-row">
                    <div class="val-label">Stockholders Equity</div>
                    <div class="val-value">{fmt_num(bs.get("stockholdersEquity"))}</div>
                </div>
                <div class="val-row" style="margin-top:8px;padding-top:12px;border-top:2px solid #e2e8f0;">
                    <div class="val-label" style="font-weight:600;color:#0f172a;">Net Cash / (Debt)</div>
                    <div class="val-value" style="color:{"#10b981" if (bs.get("cashAndEquivalents") or 0) > (bs.get("totalDebtBS") or 0) else "#ef4444"};">{fmt_num((bs.get("cashAndEquivalents", data.get("totalCash")) or 0) - (bs.get("totalDebtBS", data.get("totalDebt")) or 0))}</div>
                </div>
            </div>

            <div class="section-title" style="margin-top:20px;">Profitability</div>
            <div class="card">
                <div class="val-row">
                    <div class="val-label">Gross Margin</div>
                    <div class="val-value">{fmt_pct(data.get("grossMargins"))}</div>
                </div>
                <div class="val-row">
                    <div class="val-label">Operating Margin</div>
                    <div class="val-value">{fmt_pct(data.get("operatingMargins"))}</div>
                </div>
                <div class="val-row">
                    <div class="val-label">Net Margin</div>
                    <div class="val-value">{fmt_pct(data.get("profitMargins"))}</div>
                </div>
                <div class="val-row">
                    <div class="val-label">Free Cash Flow (TTM)</div>
                    <div class="val-value">{fmt_num(data.get("freeCashflow"))}</div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- CASH FLOW STATEMENT -->
{"<div class='section'><div class='section-title'>Cash Flow Statement (Annual)</div><div class='card'><div style='overflow-x:auto;'><table><thead><tr>" + cf_header + "</tr></thead><tbody>" + cf_rows + "</tbody></table></div></div></div>" if cf_years else ""}

<!-- SCENARIO ANALYSIS (manual template) -->
<div class="section">
    <div class="section-title">Scenario Analysis (Manual Input)</div>
    <div class="card">
        <div class="scenario-grid">
            <div class="sc-hdr label">METRIC</div>
            <div class="sc-hdr bear">BEAR</div>
            <div class="sc-hdr base">BASE</div>
            <div class="sc-hdr bull">BULL</div>

            <div class="sc-cell label">Revenue Growth</div>
            <div class="sc-cell bear">—</div>
            <div class="sc-cell base">—</div>
            <div class="sc-cell bull">—</div>

            <div class="sc-cell label">EPS Estimate</div>
            <div class="sc-cell bear">—</div>
            <div class="sc-cell base">—</div>
            <div class="sc-cell bull">—</div>

            <div class="sc-cell label">Target Multiple</div>
            <div class="sc-cell bear">—</div>
            <div class="sc-cell base">—</div>
            <div class="sc-cell bull">—</div>

            <div class="sc-cell label" style="font-weight:700;">Price Target</div>
            <div class="sc-cell bear" style="font-size:16px;">—</div>
            <div class="sc-cell base" style="font-size:16px;">—</div>
            <div class="sc-cell bull" style="font-size:16px;">—</div>

            <div class="sc-cell label" style="font-weight:700;">Upside / (Downside)</div>
            <div class="sc-cell bear">—</div>
            <div class="sc-cell base">—</div>
            <div class="sc-cell bull">—</div>
        </div>
        <div style="margin-top:12px;font-size:12px;color:#94a3b8;font-style:italic;">
            Fill in your own bear/base/bull estimates. Re-run research.py to refresh auto-pulled data without losing this section.
        </div>
    </div>
</div>

<!-- INVESTMENT NOTES -->
<div class="section">
    <div class="section-title">Investment Notes</div>
    <div class="card">
        <div class="notes-box">
            <div class="notes-placeholder">Add your investment thesis, key catalysts, risks, and notes here...</div>
        </div>
    </div>
</div>

</main>

<div class="footer">
    <div><strong>{ticker} — Company Research</strong> | Momentum Scorecard</div>
    <div>Generated {datetime.now().strftime("%B %d, %Y at %I:%M %p")} | Data source: Yahoo Finance</div>
    <div style="margin-top:6px;">This page is for research and analytical purposes only. Not investment advice. Forward-looking estimates are subject to change. Verify all data against primary sources.</div>
</div>

<script>
// Price Chart
const priceDates = {price_dates};
const priceVals = {price_vals};

if (priceDates.length > 0) {{
    new Chart(document.getElementById('priceChart'), {{
        type: 'line',
        data: {{
            labels: priceDates.map(function(d) {{
                var parts = d.split('-');
                var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
                return months[parseInt(parts[1],10)-1] + ' ' + parts[2];
            }}),
            datasets: [{{
                label: '{ticker}',
                data: priceVals,
                borderColor: '#10b981',
                backgroundColor: 'rgba(16,185,129,0.08)',
                fill: true,
                tension: 0.3,
                pointRadius: 0,
                pointHitRadius: 10,
                borderWidth: 2
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ display: false }},
                tooltip: {{
                    callbacks: {{
                        label: function(ctx) {{ return '{ticker}: $' + ctx.raw.toFixed(2); }}
                    }}
                }}
            }},
            scales: {{
                x: {{
                    grid: {{ display: false }},
                    ticks: {{ maxTicksLimit: 12, font: {{ size: 10 }}, color: '#94a3b8' }}
                }},
                y: {{
                    grid: {{ color: '#f1f5f9' }},
                    ticks: {{ callback: function(v) {{ return '$' + v.toFixed(0); }}, font: {{ size: 10 }}, color: '#94a3b8' }}
                }}
            }}
        }}
    }});
}}
</script>

</body>
</html>'''

    return html


def generate_private_html(company_name):
    """Generate a blank template for a private company."""
    safe_name = company_name.replace('"', '&quot;').replace('<', '&lt;')
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_name} — Private Company Research</title>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600;700&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'DM Sans', sans-serif; background: #f8fafc; color: #0f172a; font-size: 14px; }}
        header {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 28px 32px; border-bottom: 3px solid #10b981; color: white; }}
        .header-content {{ max-width: 1280px; margin: 0 auto; }}
        h1 {{ font-family: 'Fraunces', serif; font-size: 28px; font-weight: 700; }}
        h1 .green {{ color: #10b981; }}
        .sub {{ font-size: 13px; color: #94a3b8; margin-top: 4px; }}
        main {{ max-width: 1280px; margin: 28px auto; padding: 0 24px; }}
        .section {{ margin-bottom: 28px; }}
        .section-title {{ font-family: 'Fraunces', serif; font-size: 18px; font-weight: 700; margin-bottom: 14px; border-left: 3px solid #10b981; padding-left: 12px; }}
        .card {{ background: white; border-radius: 12px; padding: 20px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }}
        .field {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e2e8f0; }}
        .field:last-child {{ border-bottom: none; }}
        .field-label {{ font-size: 13px; color: #64748b; }}
        .field-value {{ font-family: 'JetBrains Mono', monospace; color: #94a3b8; font-style: italic; }}
        .notes-box {{ background: #f8fafc; border: 2px dashed #e2e8f0; border-radius: 10px; padding: 20px; min-height: 120px; }}
        .notes-placeholder {{ color: #94a3b8; font-style: italic; font-size: 13px; }}
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .footer {{ background: #0f172a; color: #64748b; font-size: 10px; padding: 18px 40px; text-align: center; margin-top: 40px; }}
        .footer strong {{ color: #10b981; }}
    </style>
</head>
<body>
<header><div class="header-content">
    <h1><span class="green">{safe_name}</span></h1>
    <div class="sub">Private Company Research Template | Generated {datetime.now().strftime("%B %d, %Y")}</div>
</div></header>
<main>
    <div class="section"><div class="section-title">Company Overview</div><div class="card">
        <div class="field"><span class="field-label">Industry</span><span class="field-value">Enter manually</span></div>
        <div class="field"><span class="field-label">Founded</span><span class="field-value">Enter manually</span></div>
        <div class="field"><span class="field-label">Headquarters</span><span class="field-value">Enter manually</span></div>
        <div class="field"><span class="field-label">Employees</span><span class="field-value">Enter manually</span></div>
        <div class="field"><span class="field-label">Funding Stage</span><span class="field-value">Enter manually</span></div>
        <div class="field"><span class="field-label">Last Valuation</span><span class="field-value">Enter manually</span></div>
    </div></div>
    <div class="section"><div class="section-title">Key Financials</div><div class="grid-2">
        <div class="card">
            <div class="field"><span class="field-label">Annual Revenue</span><span class="field-value">—</span></div>
            <div class="field"><span class="field-label">Revenue Growth</span><span class="field-value">—</span></div>
            <div class="field"><span class="field-label">Gross Margin</span><span class="field-value">—</span></div>
            <div class="field"><span class="field-label">Net Margin</span><span class="field-value">—</span></div>
        </div>
        <div class="card">
            <div class="field"><span class="field-label">Total Funding</span><span class="field-value">—</span></div>
            <div class="field"><span class="field-label">Burn Rate</span><span class="field-value">—</span></div>
            <div class="field"><span class="field-label">Cash on Hand</span><span class="field-value">—</span></div>
            <div class="field"><span class="field-label">Runway</span><span class="field-value">—</span></div>
        </div>
    </div></div>
    <div class="section"><div class="section-title">Business Description</div><div class="card"><div class="notes-box"><div class="notes-placeholder">What does this company do? What problem do they solve?</div></div></div></div>
    <div class="section"><div class="section-title">Competitive Advantage / Moat</div><div class="card"><div class="notes-box"><div class="notes-placeholder">What makes this company defensible? Why can others not replicate what they do?</div></div></div></div>
    <div class="section"><div class="section-title">Investment Thesis</div><div class="card"><div class="notes-box"><div class="notes-placeholder">Why is this company interesting? Key catalysts, risks, and your overall view...</div></div></div></div>
</main>
<div class="footer"><strong>{safe_name} — Private Company Research</strong> | Momentum Scorecard | {datetime.now().strftime("%B %d, %Y")}</div>
</body></html>'''


# ═══════════════════════════════════════════════════════════
# INDEX MANAGEMENT
# ═══════════════════════════════════════════════════════════

def load_index():
    """Load the research index."""
    if INDEX_FILE.exists():
        with open(INDEX_FILE) as f:
            return json.load(f)
    return {"companies": []}


def save_index(index):
    """Save the research index."""
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)


def update_index(ticker, name, company_type, sector=""):
    """Add or update a company in the index."""
    index = load_index()
    # Remove existing entry for this ticker
    index["companies"] = [c for c in index["companies"] if c["ticker"] != ticker]
    # Add new entry
    index["companies"].append({
        "ticker": ticker,
        "name": name,
        "type": company_type,
        "sector": sector,
        "lastUpdated": datetime.now().isoformat(),
        "file": f"{ticker}.html" if company_type == "public" else f"_private_{ticker}.html",
    })
    # Sort by name
    index["companies"].sort(key=lambda c: c["name"])
    save_index(index)


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def is_valid_ticker(symbol):
    """Check if a symbol is a valid public ticker."""
    try:
        t = yf.Ticker(symbol)
        info = t.info
        # yfinance returns an info dict even for invalid tickers,
        # but valid ones have a market cap or price
        return info.get("marketCap", 0) > 0 or info.get("currentPrice", 0) > 0
    except Exception:
        return False


def research_company(identifier):
    """Generate a research page for the given ticker or company name."""
    identifier = identifier.strip()
    ticker = identifier.upper().replace(" ", "")

    print(f"\n{'='*60}")
    print(f"  PROSPER MOMENTUM — Company Research")
    print(f"  {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
    print(f"{'='*60}")

    # Try as a public ticker first
    print(f"\n🔍 Looking up '{identifier}'...")

    if is_valid_ticker(ticker):
        # Public company
        data = fetch_company_data(ticker)
        if data is None:
            print(f"\n❌ Could not fetch data for {ticker}")
            return

        html = generate_html(data)
        output_file = RESEARCH_DIR / f"{ticker}.html"
        with open(output_file, "w") as f:
            f.write(html)

        update_index(ticker, data.get("name", ticker), "public", data.get("sector", ""))

        print(f"\n{'='*60}")
        print(f"  ✅ Research page generated!")
        print(f"  📁 {output_file}")
        print(f"  🌐 Open in browser to view")
        print(f"{'='*60}")
    else:
        # Private company
        print(f"  ℹ️  '{identifier}' is not a public ticker — generating private template")
        safe_id = "".join(c if c.isalnum() else "_" for c in identifier)
        html = generate_private_html(identifier)
        output_file = RESEARCH_DIR / f"_private_{safe_id}.html"
        with open(output_file, "w") as f:
            f.write(html)

        update_index(safe_id, identifier, "private")

        print(f"\n{'='*60}")
        print(f"  ✅ Private company template generated!")
        print(f"  📁 {output_file}")
        print(f"  🌐 Open in browser and fill in the details")
        print(f"{'='*60}")


def refresh_all():
    """Refresh all public company research pages."""
    index = load_index()
    public = [c for c in index["companies"] if c["type"] == "public"]

    if not public:
        print("No public companies to refresh.")
        return

    print(f"\n🔄 Refreshing {len(public)} public company pages...")
    for company in public:
        try:
            research_company(company["ticker"])
            time.sleep(2)  # Brief pause between companies
        except Exception as e:
            print(f"  ⚠️  Failed to refresh {company['ticker']}: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 research.py NVDA            # Research a public company")
        print('  python3 research.py "Acme Corp"     # Create a private company template')
        print("  python3 research.py --refresh-all   # Refresh all public company pages")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--refresh-all":
        refresh_all()
    else:
        research_company(arg)


if __name__ == "__main__":
    main()
