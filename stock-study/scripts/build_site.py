#!/usr/bin/env python3
"""
build_site.py — Generates the full City of the Future multi-page site.

Outputs:
    site/index.html                    -- overview / landing page
    site/focused-large-cap.html
    site/large-cap.html
    site/mid-cap.html
    site/small-cap.html
    site/micro-cap.html

Reads:
    data/holdings/<fund>.csv           -- per-fund ticker lists
    data/study.json                    -- fund intros, district metadata, per-ticker narratives
"""
import argparse
import csv
import html
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = ROOT / "site"
TICKERS_CSV = ROOT.parent / "tickers.csv"  # shared with the Momentum Scorecard repo

FUNDS = [
    ("focused-large-cap", "Focused Large Cap"),
    ("large-cap", "Large Cap"),
    ("mid-cap", "Mid Cap"),
    ("small-cap", "Small Cap"),
    ("micro-cap", "Micro Cap"),
]

FUND_CHIP_LABEL = {
    "focused-large-cap": "FLC",
    "large-cap": "LC",
    "mid-cap": "MID",
    "small-cap": "SC",
    "micro-cap": "MIC",
}

SITE_NAME = "The City of the Future"
SITE_KICKER = "Innovation Growth Funds"


def esc(s) -> str:
    return html.escape(str(s or ""), quote=False)


def load_holdings(fund: str):
    with (DATA / "holdings" / f"{fund}.csv").open() as f:
        return [r["ticker"].strip() for r in csv.DictReader(f) if r["ticker"].strip() and r["ticker"].strip() != "$CASH"]


def load_study():
    with (DATA / "study.json").open() as f:
        return json.load(f)


def load_watchlist():
    """Load the ~1,234 ticker watchlist from the Momentum Scorecard's tickers.csv."""
    if not TICKERS_CSV.exists():
        return []
    with TICKERS_CSV.open() as f:
        reader = csv.DictReader(f)
        # Column header is "Symbol" in the scorecard's format
        return [r["Symbol"].strip() for r in reader if r["Symbol"].strip()]


# ============ SHARED CSS ============
def css() -> str:
    return """
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    font-family: 'DM Sans', sans-serif;
    background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
    color: #0f172a;
    line-height: 1.65;
    font-size: 15px;
  }

  /* SITE HEADER */
  header.site-head {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    padding: 24px 32px 0;
    border-bottom: 3px solid #10b981;
    color: white;
  }
  .header-inner {
    max-width: 1200px;
    margin: 0 auto;
    text-align: center;
  }
  .kicker {
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #10b981;
    margin-bottom: 6px;
    font-weight: 500;
  }
  .header-title {
    font-family: 'Fraunces', serif;
    font-size: 32px;
    font-weight: 700;
    letter-spacing: 0.01em;
    margin-bottom: 4px;
  }
  .header-title .accent { color: #10b981; }
  .header-sub {
    font-size: 13px;
    color: #94a3b8;
    margin-bottom: 18px;
  }

  /* TOP NAV */
  nav.site-nav {
    display: flex;
    justify-content: center;
    gap: 4px;
    flex-wrap: wrap;
    border-top: 1px solid #1e293b;
    padding-top: 12px;
  }
  nav.site-nav a {
    color: #94a3b8;
    text-decoration: none;
    font-size: 13px;
    font-weight: 500;
    padding: 10px 16px;
    border-bottom: 2px solid transparent;
    transition: color 0.15s, border-color 0.15s;
  }
  nav.site-nav a:hover { color: #f1f5f9; }
  nav.site-nav a.active {
    color: #10b981;
    border-bottom-color: #10b981;
  }

  main {
    max-width: 1200px;
    margin: 32px auto 64px;
    padding: 0 24px;
  }

  /* FUND INTRO CARD */
  .fund-intro {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    color: #f1f5f9;
    border-radius: 14px;
    padding: 36px 40px;
    margin-bottom: 36px;
    border: 1px solid #1e293b;
    box-shadow: 0 4px 24px rgba(15, 23, 42, 0.12);
  }
  .fund-intro-tagline {
    font-family: 'Fraunces', serif;
    font-size: 22px;
    font-style: italic;
    color: #10b981;
    margin-bottom: 18px;
    letter-spacing: 0.01em;
  }
  .fund-intro-body p {
    font-size: 15.5px;
    line-height: 1.75;
    margin-bottom: 14px;
    color: #e2e8f0;
  }
  .fund-intro-body p:last-child { margin-bottom: 0; }

  /* SUMMARY STATS */
  .summary {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 32px;
    display: flex;
    gap: 40px;
    flex-wrap: wrap;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  }
  .stat { display: flex; flex-direction: column; }
  .stat-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: #64748b; font-weight: 500; }
  .stat-value { font-family: 'Fraunces', serif; font-size: 32px; font-weight: 600; color: #0f172a; margin-top: 2px; }
  .stat-value.accent { color: #10b981; }
  .stat-value.small { font-size: 20px; padding-top: 8px; }

  /* ACT HEADINGS — visible super-category groupings */
  .act-heading {
    margin: 56px 0 24px;
    padding-bottom: 10px;
    border-bottom: 1px solid #e2e8f0;
  }
  .act-heading:first-of-type { margin-top: 16px; }
  .act-label {
    font-size: 11px;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: #10b981;
    font-weight: 600;
    margin-bottom: 4px;
  }
  .act-title {
    font-family: 'Fraunces', serif;
    font-size: 34px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 4px;
  }
  .act-subtitle {
    font-size: 14px;
    color: #64748b;
    font-style: italic;
  }

  .warning-banner {
    background: #fef3c7;
    border: 1px solid #fbbf24;
    border-radius: 8px;
    padding: 12px 18px;
    margin-bottom: 24px;
    font-size: 13px;
    color: #78350f;
  }
  .warning-banner code { background: rgba(0,0,0,0.08); padding: 1px 5px; border-radius: 3px; font-size: 12px; }

  /* TABLE OF CONTENTS */
  .toc {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 48px;
  }
  .toc h3 {
    font-family: 'Fraunces', serif;
    font-size: 20px;
    margin-bottom: 18px;
    color: #0f172a;
  }
  .toc-district { margin-bottom: 18px; }
  .toc-district:last-child { margin-bottom: 0; }
  .toc-district-title {
    display: block;
    font-family: 'Fraunces', serif;
    font-size: 14px;
    font-weight: 600;
    color: #10b981;
    text-decoration: none;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
  }
  .toc-district-title:hover { color: #059669; }
  .toc-district-items {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 2px 16px;
  }
  .toc-item {
    text-decoration: none;
    color: #0f172a;
    font-size: 12.5px;
    padding: 3px 0;
    display: flex;
    gap: 8px;
  }
  .toc-item:hover .toc-ticker { color: #059669; }
  .toc-ticker { font-weight: 600; color: #10b981; min-width: 52px; }
  .toc-name { color: #475569; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  /* DISTRICT SECTIONS */
  .district { margin-bottom: 64px; }
  .district-header {
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 2px solid #10b981;
  }
  .district-title {
    font-family: 'Fraunces', serif;
    font-size: 32px;
    font-weight: 600;
    color: #0f172a;
    display: flex;
    align-items: baseline;
    gap: 14px;
  }
  .district-subtitle {
    font-size: 14px;
    color: #64748b;
    margin-top: 4px;
    font-style: italic;
  }
  .district-count {
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    font-weight: 500;
    color: #64748b;
    background: #f1f5f9;
    padding: 3px 12px;
    border-radius: 999px;
  }
  .district-intro {
    background: #f8fafc;
    border-left: 3px solid #10b981;
    padding: 18px 22px;
    border-radius: 4px;
    margin-bottom: 24px;
  }
  .district-intro p {
    font-size: 14.5px;
    line-height: 1.75;
    color: #334155;
    margin-bottom: 12px;
  }
  .district-intro p:last-child { margin-bottom: 0; }

  /* CARDS */
  .card-grid { display: flex; flex-direction: column; gap: 14px; }
  .card {
    background: white;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #10b981;
    border-radius: 10px;
    padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  }
  .card-head {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 10px;
    flex-wrap: wrap;
  }
  .ticker {
    font-family: 'Fraunces', serif;
    font-size: 24px;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: 0.02em;
  }
  .company-name {
    font-size: 14px;
    color: #64748b;
    font-weight: 500;
  }
  .fund-chips {
    margin-left: auto;
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
  }
  .fund-chip {
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 999px;
    background: #f1f5f9;
    color: #475569;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  .big-picture {
    font-size: 15px;
    font-weight: 500;
    color: #0f172a;
    margin-bottom: 12px;
    font-style: italic;
  }
  .story {
    font-size: 14.5px;
    color: #334155;
    line-height: 1.75;
  }
  .sound-bite {
    margin-top: 14px;
    padding: 10px 16px;
    background: #ecfdf5;
    border-left: 3px solid #10b981;
    border-radius: 4px;
    font-family: 'Fraunces', serif;
    font-size: 15px;
    font-style: italic;
    color: #065f46;
  }

  /* OVERVIEW PAGE: FUND CARDS */
  .fund-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
    margin-bottom: 48px;
  }
  .fund-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-top: 4px solid #10b981;
    border-radius: 10px;
    padding: 20px 24px;
    text-decoration: none;
    color: #0f172a;
    transition: transform 0.15s, box-shadow 0.15s;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  }
  .fund-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
  }
  .fund-card-name {
    font-family: 'Fraunces', serif;
    font-size: 22px;
    font-weight: 600;
    margin-bottom: 6px;
  }
  .fund-card-tagline {
    font-size: 12px;
    color: #64748b;
    margin-bottom: 14px;
    font-style: italic;
  }
  .fund-card-stats {
    display: flex;
    gap: 16px;
    border-top: 1px solid #f1f5f9;
    padding-top: 12px;
  }
  .fund-card-stat { display: flex; flex-direction: column; }
  .fund-card-stat-num { font-family: 'Fraunces', serif; font-size: 22px; font-weight: 600; color: #10b981; }
  .fund-card-stat-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: #64748b; }

  .overview-section-title {
    font-family: 'Fraunces', serif;
    font-size: 26px;
    font-weight: 600;
    color: #0f172a;
    margin-bottom: 8px;
    padding-bottom: 8px;
    border-bottom: 2px solid #10b981;
  }
  .overview-section-sub {
    font-size: 14px;
    color: #64748b;
    font-style: italic;
    margin-bottom: 28px;
  }

  footer {
    text-align: center;
    padding: 28px;
    color: #64748b;
    font-size: 12px;
  }

  /* SEARCH BAR */
  .site-search-wrapper {
    max-width: 480px;
    margin: 0 auto 16px;
    position: relative;
  }
  .site-search-input {
    width: 100%;
    padding: 10px 14px 10px 38px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(148, 163, 184, 0.3);
    border-radius: 8px;
    color: white;
    font-family: 'DM Sans', sans-serif;
    font-size: 14px;
    outline: none;
    transition: border-color 0.15s, background 0.15s;
  }
  .site-search-input::placeholder { color: #94a3b8; }
  .site-search-input:focus {
    border-color: #10b981;
    background: rgba(255, 255, 255, 0.12);
  }
  .site-search-icon {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: #94a3b8;
    font-size: 14px;
    pointer-events: none;
  }
  #search-results {
    position: absolute;
    top: calc(100% + 6px);
    left: 0;
    right: 0;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.18);
    max-height: 420px;
    overflow-y: auto;
    display: none;
    z-index: 100;
    text-align: left;
  }
  .search-result {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    text-decoration: none;
    color: #0f172a;
    border-bottom: 1px solid #f1f5f9;
    font-size: 13px;
  }
  .search-result:last-child { border-bottom: none; }
  .search-result:hover { background: #f8fafc; }
  .search-ticker {
    font-family: 'Fraunces', serif;
    font-weight: 700;
    color: #10b981;
    min-width: 60px;
  }
  .search-name {
    flex: 1;
    color: #475569;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .search-funds {
    display: flex;
    gap: 3px;
  }
  .search-fund-chip {
    font-size: 9px;
    padding: 1px 6px;
    border-radius: 999px;
    background: #f1f5f9;
    color: #475569;
    font-weight: 600;
    letter-spacing: 0.04em;
  }
  .search-empty {
    padding: 16px;
    color: #64748b;
    text-align: center;
    font-size: 13px;
  }

  /* CHART PLACEHOLDER + STOCKCHARTS LINK */
  .chart-placeholder {
    margin: 16px 0 0;
    height: 360px;
    background: #f8fafc;
    border: 1px dashed #e2e8f0;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #94a3b8;
    font-size: 12px;
  }
  .chart-container {
    margin: 16px 0 0;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    overflow: hidden;
    background: white;
    height: 360px;
    width: 100%;
  }
  .chart-container iframe {
    display: block;
    width: 100% !important;
    height: 360px !important;
    border: none;
  }
  .chart-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 8px;
  }
  .sc-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    background: white;
    border: 1px solid #10b981;
    border-radius: 6px;
    color: #10b981;
    text-decoration: none;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    transition: all 0.15s;
  }
  .sc-link:hover {
    background: #10b981;
    color: white;
  }

  /* Search result highlight when navigated */
  @keyframes flashHighlight {
    0%   { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    20%  { box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.6); }
    100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
  }
  .card.flash { animation: flashHighlight 1.6s ease-out; }

  /* SEARCH MODAL */
  .modal-backdrop {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(15, 23, 42, 0.6);
    z-index: 1000;
    display: none;
    align-items: flex-start;
    justify-content: center;
    padding: 40px 20px;
    overflow-y: auto;
    animation: modalFadeIn 0.18s ease-out;
  }
  .modal-backdrop.show { display: flex; }
  @keyframes modalFadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  .modal-card {
    background: white;
    width: 100%;
    max-width: 820px;
    border-radius: 14px;
    border-left: 4px solid #10b981;
    padding: 28px 32px;
    position: relative;
    box-shadow: 0 20px 60px rgba(15, 23, 42, 0.35);
    animation: modalSlideIn 0.22s ease-out;
  }
  @keyframes modalSlideIn {
    from { transform: translateY(-20px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }
  .modal-close {
    position: absolute;
    top: 16px;
    right: 16px;
    background: #f1f5f9;
    border: none;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    font-size: 18px;
    color: #64748b;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s, color 0.15s;
  }
  .modal-close:hover { background: #10b981; color: white; }
  .modal-ticker {
    font-family: 'Fraunces', serif;
    font-size: 32px;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: 0.02em;
  }
  .modal-name {
    font-size: 16px;
    color: #64748b;
    font-weight: 500;
    margin-top: 2px;
  }
  .modal-meta {
    display: flex;
    gap: 8px;
    margin-top: 10px;
    flex-wrap: wrap;
  }
  .modal-district-chip {
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 999px;
    background: #ecfdf5;
    color: #065f46;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  .modal-fund-chip {
    font-size: 10px;
    padding: 3px 9px;
    border-radius: 999px;
    background: #f1f5f9;
    color: #475569;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .modal-body { margin-top: 20px; }
  .modal-big-picture {
    font-size: 16px;
    font-weight: 500;
    color: #0f172a;
    font-style: italic;
    margin-bottom: 14px;
  }
  .modal-story {
    font-size: 14.5px;
    color: #334155;
    line-height: 1.75;
  }
  .modal-sound-bite {
    margin-top: 16px;
    padding: 12px 18px;
    background: #ecfdf5;
    border-left: 3px solid #10b981;
    border-radius: 4px;
    font-family: 'Fraunces', serif;
    font-size: 16px;
    font-style: italic;
    color: #065f46;
  }
  .modal-chart-container {
    margin-top: 18px;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    overflow: hidden;
    height: 380px;
    width: 100%;
  }
  .modal-chart-container iframe {
    width: 100% !important;
    height: 380px !important;
    border: none;
  }
  .modal-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
  }
  @media (max-width: 640px) {
    .modal-card { padding: 22px 20px; }
    .modal-ticker { font-size: 26px; }
    .modal-chart-container, .modal-chart-container iframe { height: 300px !important; }
  }

  /* WATCHLIST PAGE */
  .watchlist-controls {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 24px;
  }
  .watchlist-filter-input {
    width: 100%;
    padding: 10px 14px;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    font-family: 'DM Sans', sans-serif;
    font-size: 14px;
    outline: none;
    margin-bottom: 14px;
  }
  .watchlist-filter-input:focus { border-color: #10b981; }
  .watchlist-filter-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .wl-chip {
    padding: 6px 14px;
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    color: #475569;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    transition: all 0.15s;
    user-select: none;
  }
  .wl-chip:hover { border-color: #10b981; color: #10b981; }
  .wl-chip.active {
    background: #10b981;
    border-color: #10b981;
    color: white;
  }
  .wl-chip-count {
    margin-left: 6px;
    opacity: 0.7;
    font-weight: 500;
  }

  .watchlist-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  }
  .watchlist-table th {
    background: #f8fafc;
    text-align: left;
    padding: 10px 16px;
    font-size: 11px;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    border-bottom: 1px solid #e2e8f0;
  }
  .watchlist-table td {
    padding: 10px 16px;
    font-size: 13px;
    border-bottom: 1px solid #f1f5f9;
    vertical-align: middle;
  }
  .watchlist-table tr:last-child td { border-bottom: none; }
  .watchlist-table tr:hover td { background: #f8fafc; }
  .watchlist-table tr.hidden { display: none; }
  .wl-ticker {
    font-family: 'Fraunces', serif;
    font-weight: 700;
    color: #0f172a;
    font-size: 15px;
  }
  .wl-ticker a {
    color: #0f172a;
    text-decoration: none;
  }
  .wl-ticker a:hover { color: #10b981; }
  .wl-name {
    color: #475569;
    max-width: 420px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .wl-name-muted { color: #94a3b8; font-style: italic; font-size: 12px; }
  .wl-funds-cell {
    display: flex;
    gap: 3px;
    flex-wrap: wrap;
  }
  .wl-fund-chip {
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 999px;
    background: #ecfdf5;
    color: #065f46;
    font-weight: 600;
    letter-spacing: 0.04em;
  }
  .wl-fund-chip.watchlist-only {
    background: #f1f5f9;
    color: #64748b;
  }
  .wl-district {
    font-size: 11px;
    color: #64748b;
    font-style: italic;
  }
  .wl-actions {
    display: flex;
    gap: 6px;
    justify-content: flex-end;
  }
  .wl-btn {
    padding: 4px 10px;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 5px;
    color: #475569;
    text-decoration: none;
    font-size: 11px;
    font-weight: 600;
    transition: all 0.15s;
    white-space: nowrap;
  }
  .wl-btn:hover {
    background: #10b981;
    border-color: #10b981;
    color: white;
  }
  .wl-empty {
    text-align: center;
    padding: 40px 20px;
    color: #64748b;
    font-size: 14px;
  }
  #wl-match-count {
    font-size: 12px;
    color: #64748b;
    margin-top: 10px;
  }

  /* PRINT / PDF */
  @media print {
    body { background: white; font-size: 11pt; }
    header.site-head, .fund-intro {
      background: #0f172a !important;
      color: white;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    nav.site-nav { display: none; }
    .site-search-wrapper { display: none; }
    main { margin: 16px auto; }
    .toc { page-break-after: always; }
    .district { page-break-before: auto; page-break-inside: auto; }
    .district-intro { page-break-inside: avoid; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .card { page-break-inside: avoid; box-shadow: none; }
    .sound-bite { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .chart-placeholder, .chart-container { display: none; }
    a { color: inherit; text-decoration: none; }
  }
"""


def render_nav(active: str) -> str:
    """active is the page name without .html (e.g. 'small-cap', 'index', 'watchlist')."""
    items = [("index", "Overview")]
    for slug, name in FUNDS:
        items.append((slug, name))
    items.append(("watchlist", "Watchlist"))
    parts = []
    for slug, label in items:
        href = f"{slug}.html"
        cls = "active" if slug == active else ""
        parts.append(f'<a href="{href}" class="{cls}">{esc(label)}</a>')
    return f'<nav class="site-nav">{"".join(parts)}</nav>'


def render_header(active: str, sub: str = "") -> str:
    return f"""
<header class="site-head">
  <div class="header-inner">
    <div class="kicker">{esc(SITE_KICKER)}</div>
    <h1 class="header-title">The City of <span class="accent">the Future</span></h1>
    <div class="header-sub">{esc(sub)}</div>
    <div class="site-search-wrapper">
      <span class="site-search-icon">⌕</span>
      <input id="site-search" class="site-search-input" type="text" placeholder="Search any ticker or company name..." autocomplete="off" />
      <div id="search-results"></div>
    </div>
    {render_nav(active)}
  </div>
</header>
"""


def render_fund_intro(fund_intro: dict) -> str:
    if not fund_intro:
        return ""
    tagline = esc(fund_intro.get("tagline", ""))
    paras = "".join(f"<p>{esc(p)}</p>" for p in fund_intro.get("story", []))
    return f"""
    <section class="fund-intro">
      <div class="fund-intro-tagline">{tagline}</div>
      <div class="fund-intro-body">{paras}</div>
    </section>
    """


def render_card(ticker: str, entry: dict, fund_chips: list = None) -> str:
    sound = entry.get("sound_bite") or ""
    chips_html = ""
    if fund_chips:
        chips = "".join(f'<span class="fund-chip">{esc(c)}</span>' for c in fund_chips)
        chips_html = f'<span class="fund-chips">{chips}</span>'
    sc_url = f"https://stockcharts.com/h-sc/ui?s={esc(ticker)}"
    sc_link = f'<a href="{sc_url}" target="_blank" rel="noopener" class="sc-link" title="Open this ticker in StockCharts in a new tab">📊 Open in StockCharts &rarr;</a>'
    chart_placeholder = f'<div class="chart-placeholder" data-ticker="{esc(ticker)}">Loading chart…</div>'
    return f"""
    <article class="card" id="{esc(ticker)}">
      <header class="card-head">
        <span class="ticker">{esc(ticker)}</span>
        <span class="company-name">{esc(entry.get('name', ''))}</span>
        {chips_html}
      </header>
      <p class="big-picture">{esc(entry.get('big_picture', ''))}</p>
      <div class="story">{esc(entry.get('story', ''))}</div>
      {f'<p class="sound-bite">&ldquo;{esc(sound)}&rdquo;</p>' if sound else ''}
      {chart_placeholder}
      <div class="chart-actions">{sc_link}</div>
    </article>
    """


def build_search_index(study: dict, holdings_by_fund: dict) -> list:
    """Build a JSON-serializable search index of every company across all funds.
    Full narrative content is included so the modal can render without lookups."""
    ticker_to_funds = {}
    for slug, _ in FUNDS:
        for t in holdings_by_fund[slug]:
            ticker_to_funds.setdefault(t, []).append(FUND_CHIP_LABEL[slug])

    districts = study["districts"]
    index = []
    for ticker in sorted(ticker_to_funds.keys()):
        entry = study["companies"].get(ticker)
        if not entry:
            continue
        d_key = entry.get("district", "")
        d_title = districts.get(d_key, {}).get("title", "")
        index.append({
            "ticker": ticker,
            "name": entry.get("name", ""),
            "district": d_key,
            "district_title": d_title,
            "big_picture": entry.get("big_picture", ""),
            "story": entry.get("story", ""),
            "sound_bite": entry.get("sound_bite", ""),
            "funds": ticker_to_funds[ticker],
        })
    return index


def build_js(search_index: list) -> str:
    """Returns page-level JS: modal + search + lazy chart loader."""
    index_json = json.dumps(search_index)
    return r"""
<div class="modal-backdrop" id="modal-backdrop">
  <div class="modal-card" id="modal-card" role="dialog" aria-modal="true">
    <button class="modal-close" id="modal-close" aria-label="Close">&times;</button>
    <div id="modal-content"></div>
  </div>
</div>
<script>
const SEARCH_INDEX = """ + index_json + r""";
const SEARCH_INDEX_BY_TICKER = (function() {
  const map = {};
  SEARCH_INDEX.forEach(function(item) { map[item.ticker] = item; });
  return map;
})();

function cityEsc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, function(c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}

// ========== MODAL ==========
(function() {
  const backdrop = document.getElementById('modal-backdrop');
  const content = document.getElementById('modal-content');
  const closeBtn = document.getElementById('modal-close');
  if (!backdrop || !content) return;

  function openModal(ticker) {
    const item = SEARCH_INDEX_BY_TICKER[ticker];
    if (!item) return;

    const fundChips = (item.funds || []).map(function(f) {
      return '<span class="modal-fund-chip">' + cityEsc(f) + '</span>';
    }).join('');
    const districtChip = item.district_title
      ? '<span class="modal-district-chip">' + cityEsc(item.district_title) + '</span>'
      : '';
    const soundBite = item.sound_bite
      ? '<p class="modal-sound-bite">&ldquo;' + cityEsc(item.sound_bite) + '&rdquo;</p>'
      : '';

    const chartId = 'modal_chart_' + ticker + '_' + Date.now();
    const scUrl = 'https://stockcharts.com/h-sc/ui?s=' + encodeURIComponent(ticker);

    content.innerHTML =
      '<div class="modal-ticker">' + cityEsc(ticker) + '</div>' +
      '<div class="modal-name">' + cityEsc(item.name) + '</div>' +
      '<div class="modal-meta">' + districtChip + fundChips + '</div>' +
      '<div class="modal-body">' +
        '<p class="modal-big-picture">' + cityEsc(item.big_picture) + '</p>' +
        '<div class="modal-story">' + cityEsc(item.story) + '</div>' +
        soundBite +
        '<div id="' + chartId + '" class="modal-chart-container"></div>' +
        '<div class="modal-actions">' +
          '<a href="' + scUrl + '" target="_blank" rel="noopener" class="sc-link">&#128202; Open in StockCharts &rarr;</a>' +
        '</div>' +
      '</div>';

    backdrop.classList.add('show');
    document.body.style.overflow = 'hidden';

    if (typeof TradingView !== 'undefined') {
      new TradingView.widget({
        autosize: true,
        symbol: ticker,
        interval: 'W',
        range: '60M',
        timezone: 'Etc/UTC',
        theme: 'light',
        style: '3',
        locale: 'en',
        enable_publishing: false,
        hide_top_toolbar: true,
        hide_side_toolbar: true,
        hide_legend: false,
        save_image: false,
        studies: ['MASimple@tv-basicstudies'],
        studies_overrides: {
          'Moving Average.length': 30,
          'Moving Average.linewidth': 2,
          'Moving Average.plot.color': 'rgba(16, 185, 129, 1)'
        },
        show_popup_button: false,
        withdateranges: false,
        allow_symbol_change: false,
        calendar: false,
        details: false,
        hotlist: false,
        container_id: chartId
      });
    }
  }

  function closeModal() {
    backdrop.classList.remove('show');
    content.innerHTML = '';
    document.body.style.overflow = '';
  }

  closeBtn.addEventListener('click', closeModal);
  backdrop.addEventListener('click', function(e) {
    if (e.target === backdrop) closeModal();
  });
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && backdrop.classList.contains('show')) closeModal();
  });

  window.__cityModalOpen = openModal;
  window.__cityModalClose = closeModal;
})();

// ========== SEARCH ==========
(function() {
  const input = document.getElementById('site-search');
  const results = document.getElementById('search-results');
  if (!input || !results) return;

  function render(matches, query) {
    if (!matches.length) {
      results.innerHTML = '<div class="search-empty">No matches for &ldquo;' + cityEsc(query) + '&rdquo;</div>';
      results.style.display = 'block';
      return;
    }
    results.innerHTML = matches.map(function(m) {
      const chips = m.funds.map(function(f) { return '<span class="search-fund-chip">' + cityEsc(f) + '</span>'; }).join('');
      return '<a href="#' + cityEsc(m.ticker) + '" class="search-result" data-ticker="' + cityEsc(m.ticker) + '">' +
        '<span class="search-ticker">' + cityEsc(m.ticker) + '</span>' +
        '<span class="search-name">' + cityEsc(m.name) + '</span>' +
        '<span class="search-funds">' + chips + '</span>' +
        '</a>';
    }).join('');
    results.style.display = 'block';
  }

  input.addEventListener('input', function(e) {
    const q = e.target.value.toLowerCase().trim();
    if (!q) { results.style.display = 'none'; return; }
    const matches = SEARCH_INDEX.filter(function(item) {
      return item.ticker.toLowerCase().indexOf(q) !== -1 ||
             (item.name || '').toLowerCase().indexOf(q) !== -1;
    }).slice(0, 12);
    render(matches, q);
  });

  input.addEventListener('focus', function() {
    if (input.value.trim()) results.style.display = 'block';
  });

  document.addEventListener('click', function(e) {
    if (!e.target.closest('.site-search-wrapper')) {
      results.style.display = 'none';
    }
  });

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      results.style.display = 'none';
      input.blur();
    }
    if (e.key === '/' && document.activeElement !== input
        && !document.getElementById('modal-backdrop').classList.contains('show')) {
      e.preventDefault();
      input.focus();
    }
  });

  // Click any result → open modal for that ticker
  results.addEventListener('click', function(e) {
    const link = e.target.closest('.search-result');
    if (!link) return;
    e.preventDefault();
    const ticker = link.dataset.ticker;
    if (ticker && window.__cityModalOpen) {
      window.__cityModalOpen(ticker);
      results.style.display = 'none';
      input.value = '';
      input.blur();
    }
  });
})();

// ========== LAZY CHART LOADER ==========
// Uses TradingView's tv.js Charting Library widget constructor.
// This is the only path that reliably honors studies + studies_overrides.
(function() {
  let chartCounter = 0;

  function loadPlaceholder(placeholder) {
    const ticker = placeholder.dataset.ticker;
    if (!ticker) return;
    if (typeof TradingView === 'undefined') {
      // tv.js not yet loaded — retry shortly
      setTimeout(function() { loadPlaceholder(placeholder); }, 200);
      return;
    }

    chartCounter++;
    const containerId = 'tv_chart_' + ticker + '_' + chartCounter;
    const container = document.createElement('div');
    container.id = containerId;
    container.className = 'chart-container';
    placeholder.replaceWith(container);

    new TradingView.widget({
      autosize: true,
      symbol: ticker,
      interval: 'W',
      range: '60M',
      timezone: 'Etc/UTC',
      theme: 'light',
      style: '3',
      locale: 'en',
      enable_publishing: false,
      hide_top_toolbar: true,
      hide_side_toolbar: true,
      hide_legend: false,
      save_image: false,
      studies: ['MASimple@tv-basicstudies'],
      studies_overrides: {
        'Moving Average.length': 30,
        'Moving Average.linewidth': 2,
        'Moving Average.plot.color': 'rgba(16, 185, 129, 1)'
      },
      overrides: {
        'paneProperties.background': '#ffffff',
        'paneProperties.backgroundType': 'solid'
      },
      show_popup_button: false,
      withdateranges: false,
      allow_symbol_change: false,
      calendar: false,
      details: false,
      hotlist: false,
      container_id: containerId
    });
  }

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          loadPlaceholder(entry.target);
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: '400px 0px' });

    document.querySelectorAll('.chart-placeholder').forEach(function(el) {
      observer.observe(el);
    });
  } else {
    // Fallback: load all charts immediately
    document.querySelectorAll('.chart-placeholder').forEach(loadPlaceholder);
  }
})();
</script>
"""


def render_act_heading(act: dict, index: int) -> str:
    roman = ["I", "II", "III", "IV", "V", "VI", "VII"][index] if index < 7 else str(index + 1)
    return f"""
    <div class="act-heading">
      <div class="act-label">Act {roman}</div>
      <h2 class="act-title">{esc(act.get('title', ''))}</h2>
      <div class="act-subtitle">{esc(act.get('subtitle', ''))}</div>
    </div>
    """


def build_fund_page(fund_slug: str, fund_label: str, study: dict, holdings_by_fund: dict, as_of: str, search_index: list) -> str:
    holdings = holdings_by_fund[fund_slug]
    companies = study["companies"]
    districts = study["districts"]
    district_order = study["district_order"]
    acts = study.get("acts", [])
    fund_intro = study.get("fund_intros", {}).get(fund_slug, {})

    # Group by district
    by_district = {d: [] for d in district_order}
    unassigned = []
    for ticker in holdings:
        entry = companies.get(ticker)
        if not entry:
            unassigned.append(ticker)
            continue
        d = entry.get("district", "")
        if d in by_district:
            by_district[d].append((ticker, entry))
        else:
            unassigned.append(ticker)

    total = len(holdings)
    covered = sum(1 for t in holdings if companies.get(t))
    districts_shown = sum(1 for d in district_order if by_district[d])

    # Map district → act index (for rendering act headings)
    district_to_act = {}
    for act_idx, act in enumerate(acts):
        for d in act.get("districts", []):
            district_to_act[d] = act_idx

    # Build sections, emitting an act heading whenever we enter a new act with visible content
    sections = []
    emitted_acts = set()
    for d in district_order:
        bucket = by_district[d]
        if not bucket:
            continue

        act_idx = district_to_act.get(d)
        if act_idx is not None and act_idx not in emitted_acts:
            sections.append(render_act_heading(acts[act_idx], act_idx))
            emitted_acts.add(act_idx)

        bucket.sort(key=lambda x: x[0])
        dmeta = districts[d]
        intro_paras = "".join(f"<p>{esc(p)}</p>" for p in dmeta.get("intro", []))
        cards = "".join(render_card(t, e) for t, e in bucket)
        sections.append(f"""
        <section class="district" id="district-{d}">
          <div class="district-header">
            <h2 class="district-title">{esc(dmeta['title'])} <span class="district-count">{len(bucket)}</span></h2>
            <div class="district-subtitle">{esc(dmeta.get('subtitle', ''))}</div>
          </div>
          <div class="district-intro">{intro_paras}</div>
          <div class="card-grid">{cards}</div>
        </section>
        """)

    # TOC grouped by district
    toc_sections = []
    for d in district_order:
        bucket = by_district[d]
        if not bucket:
            continue
        items = "".join(
            f'<a href="#{esc(t)}" class="toc-item"><span class="toc-ticker">{esc(t)}</span><span class="toc-name">{esc(e.get("name", ""))}</span></a>'
            for t, e in sorted(bucket, key=lambda x: x[0])
        )
        toc_sections.append(f"""
        <div class="toc-district">
          <a href="#district-{d}" class="toc-district-title">{esc(districts[d]['title'])}</a>
          <div class="toc-district-items">{items}</div>
        </div>
        """)

    unassigned_html = ""
    if unassigned:
        items = ", ".join(esc(t) for t in unassigned)
        unassigned_html = f'<div class="warning-banner"><strong>Heads up:</strong> {len(unassigned)} holding(s) in this fund have no entry in <code>data/study.json</code> yet: {items}.</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(fund_label)} — The City of the Future</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600;700&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://s3.tradingview.com/tv.js"></script>
<style>{css()}</style>
</head>
<body>
{render_header(fund_slug, f"{fund_label} Fund · as of {as_of}")}
<main>
  {render_fund_intro(fund_intro)}
  <section class="summary">
    <div class="stat"><span class="stat-label">Holdings</span><span class="stat-value">{total}</span></div>
    <div class="stat"><span class="stat-label">Written Up</span><span class="stat-value accent">{covered}</span></div>
    <div class="stat"><span class="stat-label">Districts</span><span class="stat-value">{districts_shown}</span></div>
    <div class="stat"><span class="stat-label">As Of</span><span class="stat-value small">{esc(as_of)}</span></div>
  </section>
  {unassigned_html}
  <nav class="toc">
    <h3>Quick Index</h3>
    {''.join(toc_sections)}
  </nav>
  {''.join(sections)}
</main>
<footer>
  Innovation Growth · {esc(fund_label)} · {esc(as_of)} ·
  Cmd+P to save as PDF · Press / to search
</footer>
{build_js(search_index)}
</body>
</html>
"""


def build_overview_page(study: dict, holdings_by_fund: dict, as_of: str, search_index: list) -> str:
    companies = study["companies"]
    districts = study["districts"]
    district_order = study["district_order"]

    # Compute fund_chips for every ticker
    ticker_to_funds = {}
    for fund_slug, _ in FUNDS:
        for t in holdings_by_fund[fund_slug]:
            ticker_to_funds.setdefault(t, []).append(fund_slug)

    fund_chip_label = {
        "focused-large-cap": "FLC",
        "large-cap": "LC",
        "mid-cap": "MID",
        "small-cap": "SC",
        "micro-cap": "MIC",
    }

    # Fund cards
    fund_cards = []
    for fund_slug, fund_label in FUNDS:
        holdings = holdings_by_fund[fund_slug]
        ds = set(companies[t]["district"] for t in holdings if t in companies)
        fund_intro = study.get("fund_intros", {}).get(fund_slug, {})
        tagline = fund_intro.get("tagline", "")
        fund_cards.append(f"""
        <a href="{fund_slug}.html" class="fund-card">
          <div class="fund-card-name">{esc(fund_label)}</div>
          <div class="fund-card-tagline">{esc(tagline)}</div>
          <div class="fund-card-stats">
            <div class="fund-card-stat"><span class="fund-card-stat-num">{len(holdings)}</span><span class="fund-card-stat-label">Holdings</span></div>
            <div class="fund-card-stat"><span class="fund-card-stat-num">{len(ds)}</span><span class="fund-card-stat-label">Districts</span></div>
          </div>
        </a>
        """)

    # Universe stats
    all_tickers = set()
    for fund_slug, _ in FUNDS:
        all_tickers.update(holdings_by_fund[fund_slug])
    total_unique = len(all_tickers)

    # All companies grouped by district (universe view)
    by_district = {d: [] for d in district_order}
    for ticker in sorted(all_tickers):
        entry = companies.get(ticker)
        if not entry:
            continue
        d = entry.get("district", "")
        if d in by_district:
            by_district[d].append((ticker, entry))

    # Universe sections — with act headings
    acts = study.get("acts", [])
    district_to_act = {}
    for act_idx, act in enumerate(acts):
        for dk in act.get("districts", []):
            district_to_act[dk] = act_idx

    universe_sections = []
    emitted_acts = set()
    for d in district_order:
        bucket = by_district[d]
        if not bucket:
            continue

        act_idx = district_to_act.get(d)
        if act_idx is not None and act_idx not in emitted_acts:
            universe_sections.append(render_act_heading(acts[act_idx], act_idx))
            emitted_acts.add(act_idx)

        dmeta = districts[d]
        cards = []
        for ticker, entry in bucket:
            chips = [fund_chip_label[f] for f in ticker_to_funds.get(ticker, [])]
            cards.append(render_card(ticker, entry, chips))
        universe_sections.append(f"""
        <section class="district" id="district-{d}">
          <div class="district-header">
            <h2 class="district-title">{esc(dmeta['title'])} <span class="district-count">{len(bucket)}</span></h2>
            <div class="district-subtitle">{esc(dmeta.get('subtitle', ''))}</div>
          </div>
          <div class="card-grid">{''.join(cards)}</div>
        </section>
        """)

    # Universe TOC
    toc_sections = []
    for d in district_order:
        bucket = by_district[d]
        if not bucket:
            continue
        items = "".join(
            f'<a href="#{esc(t)}" class="toc-item"><span class="toc-ticker">{esc(t)}</span><span class="toc-name">{esc(e.get("name", ""))}</span></a>'
            for t, e in bucket
        )
        toc_sections.append(f"""
        <div class="toc-district">
          <a href="#district-{d}" class="toc-district-title">{esc(districts[d]['title'])}</a>
          <div class="toc-district-items">{items}</div>
        </div>
        """)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The City of the Future — Overview</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600;700&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://s3.tradingview.com/tv.js"></script>
<style>{css()}</style>
</head>
<body>
{render_header("index", f"5 funds · {total_unique} unique companies · as of {as_of}")}
<main>
  <section class="fund-intro">
    <div class="fund-intro-tagline">The City of the Future</div>
    <div class="fund-intro-body">
      <p>Every company in our five innovation growth funds is playing a role in building the city of the future. The Chip Works and The Wires make AI physically possible. The Machine Shop, The Power Plant, and The Construction Yards make AI physically real. The Arsenal defends the city and extends it into space. The Clinic catches disease early and The Research Labs treats what once had no treatment. Main Street feeds, moves, trains, and entertains the people who live in the city, while The Stadium hosts the concerts, fights, and games. The Software Layer runs the code beneath all of it. And The Financial District moves the capital that funds everything else.</p>
      <p>This page is the universe view — every name we own across every fund, organized by district, with little chips showing which funds hold each one. Click any fund above to drill into its full guide.</p>
    </div>
  </section>

  <h2 class="overview-section-title">The Funds</h2>
  <div class="overview-section-sub">Click any fund to see its complete guide</div>
  <div class="fund-grid">
    {''.join(fund_cards)}
  </div>

  <h2 class="overview-section-title">The Universe</h2>
  <div class="overview-section-sub">{total_unique} unique companies across all 5 funds &middot; chips show which funds hold each name</div>

  <nav class="toc">
    <h3>Quick Index</h3>
    {''.join(toc_sections)}
  </nav>

  {''.join(universe_sections)}
</main>
<footer>
  Innovation Growth · The City of the Future · {esc(as_of)} · Press / to search
</footer>
{build_js(search_index)}
</body>
</html>
"""


def build_watchlist_page(study: dict, holdings_by_fund: dict, watchlist: list, as_of: str, search_index: list) -> str:
    companies = study["companies"]
    districts = study["districts"]

    # Build ticker → list of fund slugs (for held names)
    ticker_to_funds = {}
    for fund_slug, _ in FUNDS:
        for t in holdings_by_fund[fund_slug]:
            ticker_to_funds.setdefault(t, []).append(fund_slug)

    # Every ticker we care about: union of watchlist + holdings
    held_tickers = set(ticker_to_funds.keys())
    watchlist_set = set(watchlist)
    all_tickers = sorted(watchlist_set | held_tickers)

    total = len(all_tickers)
    held_count = len(held_tickers)
    watchlist_only = len(all_tickers) - held_count
    with_narrative = sum(1 for t in all_tickers if t in companies)

    # Render table rows
    rows = []
    for ticker in all_tickers:
        entry = companies.get(ticker, {})
        name = entry.get("name", "")
        district = entry.get("district", "")
        district_title = districts.get(district, {}).get("title", "") if district else ""

        funds = ticker_to_funds.get(ticker, [])
        is_held = bool(funds)
        is_on_watchlist = ticker in watchlist_set

        # Fund chips
        if is_held:
            fund_chips_html = "".join(
                f'<span class="wl-fund-chip">{FUND_CHIP_LABEL[f]}</span>' for f in funds
            )
        else:
            fund_chips_html = '<span class="wl-fund-chip watchlist-only">Watch</span>'

        # Status string for data attribute (filters)
        if is_held and is_on_watchlist:
            status = "held watchlist"
        elif is_held:
            status = "held"
        else:
            status = "watchlist"
        if entry:
            status += " narrative"

        # Name cell — link to overview anchor if we have a narrative, else muted
        if name:
            name_cell = f'<a href="index.html#{esc(ticker)}" class="wl-ticker-link">{esc(name)}</a>'
        else:
            name_cell = '<span class="wl-name-muted">No narrative yet</span>'

        ticker_cell = (
            f'<a href="index.html#{esc(ticker)}">{esc(ticker)}</a>'
            if entry else esc(ticker)
        )

        # Actions
        sc_url = f"https://stockcharts.com/h-sc/ui?s={esc(ticker)}"
        actions = [f'<a href="{sc_url}" target="_blank" rel="noopener" class="wl-btn">📊 SC</a>']
        if entry:
            actions.append(f'<a href="index.html#{esc(ticker)}" class="wl-btn">View</a>')

        # Search tokens for filter (ticker + name, lowercased)
        search_tokens = (ticker + " " + name).lower()

        rows.append(f"""
        <tr class="wl-row" data-status="{status}" data-search="{esc(search_tokens)}">
          <td class="wl-ticker">{ticker_cell}</td>
          <td class="wl-name">{name_cell}</td>
          <td><div class="wl-funds-cell">{fund_chips_html}</div></td>
          <td class="wl-district">{esc(district_title)}</td>
          <td><div class="wl-actions">{''.join(actions)}</div></td>
        </tr>
        """)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Watchlist — The City of the Future</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600;700&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://s3.tradingview.com/tv.js"></script>
<style>{css()}</style>
</head>
<body>
{render_header("watchlist", f"Watchlist · {total} names · {held_count} held · {watchlist_only} monitored · as of {as_of}")}
<main>
  <section class="fund-intro">
    <div class="fund-intro-tagline">The Watchlist</div>
    <div class="fund-intro-body">
      <p>This is the full universe the team is monitoring — {total} names — combining every current holding across the five funds with every other ticker flagged as worth watching. Names we already own show their fund-membership chips. Names we are only watching show a neutral "Watch" chip. Click any ticker with a narrative to jump to its card on the Overview page. Click the 📊 SC button to open that name in StockCharts.</p>
      <p>As holdings rotate, names will move between categories automatically. The data comes from <code>tickers.csv</code> in the Momentum Scorecard — so the two tools stay in sync without any manual bookkeeping.</p>
    </div>
  </section>

  <section class="summary">
    <div class="stat"><span class="stat-label">Universe</span><span class="stat-value">{total}</span></div>
    <div class="stat"><span class="stat-label">Currently Held</span><span class="stat-value accent">{held_count}</span></div>
    <div class="stat"><span class="stat-label">Monitored</span><span class="stat-value">{watchlist_only}</span></div>
    <div class="stat"><span class="stat-label">With Narratives</span><span class="stat-value">{with_narrative}</span></div>
  </section>

  <section class="watchlist-controls">
    <input id="wl-filter" class="watchlist-filter-input" type="text" placeholder="Filter by ticker or company name..." autocomplete="off" />
    <div class="watchlist-filter-chips">
      <div class="wl-chip active" data-filter="all">All <span class="wl-chip-count">{total}</span></div>
      <div class="wl-chip" data-filter="held">Currently Held <span class="wl-chip-count">{held_count}</span></div>
      <div class="wl-chip" data-filter="watchlist">Watchlist Only <span class="wl-chip-count">{watchlist_only}</span></div>
      <div class="wl-chip" data-filter="narrative">With Narratives <span class="wl-chip-count">{with_narrative}</span></div>
    </div>
    <div id="wl-match-count">Showing {total} of {total}</div>
  </section>

  <table class="watchlist-table">
    <thead>
      <tr>
        <th>Ticker</th>
        <th>Company</th>
        <th>Status</th>
        <th>District</th>
        <th></th>
      </tr>
    </thead>
    <tbody id="wl-tbody">
      {''.join(rows)}
    </tbody>
  </table>
  <div id="wl-empty" class="wl-empty" style="display:none;">No tickers match the current filters.</div>
</main>
<footer>
  Innovation Growth · Watchlist · {esc(as_of)} · Shared with the Momentum Scorecard via tickers.csv
</footer>
{build_js(search_index)}
<script>
// Watchlist page-local filtering (in addition to the header search bar)
(function() {{
  const input = document.getElementById('wl-filter');
  const chips = document.querySelectorAll('.wl-chip');
  const rows = document.querySelectorAll('.wl-row');
  const matchCount = document.getElementById('wl-match-count');
  const emptyMsg = document.getElementById('wl-empty');
  const total = rows.length;

  let activeFilter = 'all';
  let searchQuery = '';

  function apply() {{
    let visible = 0;
    rows.forEach(function(row) {{
      const status = row.dataset.status || '';
      const search = row.dataset.search || '';

      let statusMatch = true;
      if (activeFilter === 'held') statusMatch = status.indexOf('held') !== -1;
      else if (activeFilter === 'watchlist') statusMatch = status.indexOf('held') === -1;
      else if (activeFilter === 'narrative') statusMatch = status.indexOf('narrative') !== -1;

      const searchMatch = !searchQuery || search.indexOf(searchQuery) !== -1;

      if (statusMatch && searchMatch) {{
        row.classList.remove('hidden');
        visible++;
      }} else {{
        row.classList.add('hidden');
      }}
    }});
    matchCount.textContent = 'Showing ' + visible + ' of ' + total;
    emptyMsg.style.display = visible === 0 ? 'block' : 'none';
  }}

  input.addEventListener('input', function(e) {{
    searchQuery = e.target.value.toLowerCase().trim();
    apply();
  }});

  chips.forEach(function(chip) {{
    chip.addEventListener('click', function() {{
      chips.forEach(function(c) {{ c.classList.remove('active'); }});
      chip.classList.add('active');
      activeFilter = chip.dataset.filter;
      apply();
    }});
  }});
}})();
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=str(date.today()))
    args = parser.parse_args()

    study = load_study()
    holdings_by_fund = {slug: load_holdings(slug) for slug, _ in FUNDS}
    search_index = build_search_index(study, holdings_by_fund)
    watchlist = load_watchlist()

    SITE.mkdir(parents=True, exist_ok=True)

    # Build each fund page
    for slug, label in FUNDS:
        html_out = build_fund_page(slug, label, study, holdings_by_fund, args.date, search_index)
        (SITE / f"{slug}.html").write_text(html_out)
        print(f"Wrote site/{slug}.html")

    # Build overview
    overview = build_overview_page(study, holdings_by_fund, args.date, search_index)
    (SITE / "index.html").write_text(overview)
    print(f"Wrote site/index.html")

    # Build watchlist
    if watchlist:
        wl = build_watchlist_page(study, holdings_by_fund, watchlist, args.date, search_index)
        (SITE / "watchlist.html").write_text(wl)
        print(f"Wrote site/watchlist.html ({len(watchlist)} tickers)")
    else:
        print(f"Skipped watchlist: tickers.csv not found at {TICKERS_CSV}")


if __name__ == "__main__":
    main()
