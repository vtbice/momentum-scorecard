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

FUNDS = [
    ("focused-large-cap", "Focused Large Cap"),
    ("large-cap", "Large Cap"),
    ("mid-cap", "Mid Cap"),
    ("small-cap", "Small Cap"),
    ("micro-cap", "Micro Cap"),
]

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
    """active is the page name without .html (e.g. 'small-cap', 'index')."""
    items = [("index", "Overview")]
    for slug, name in FUNDS:
        items.append((slug, name))
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
    """Build a JSON-serializable search index of every company across all funds."""
    fund_chip_label = {
        "focused-large-cap": "FLC",
        "large-cap": "LC",
        "mid-cap": "MID",
        "small-cap": "SC",
        "micro-cap": "MIC",
    }
    ticker_to_funds = {}
    for slug, _ in FUNDS:
        for t in holdings_by_fund[slug]:
            ticker_to_funds.setdefault(t, []).append(fund_chip_label[slug])

    index = []
    for ticker in sorted(ticker_to_funds.keys()):
        entry = study["companies"].get(ticker)
        if not entry:
            continue
        index.append({
            "ticker": ticker,
            "name": entry.get("name", ""),
            "district": entry.get("district", ""),
            "funds": ticker_to_funds[ticker],
        })
    return index


def build_js(search_index: list) -> str:
    """Returns the page-level JavaScript: search + lazy chart loader."""
    index_json = json.dumps(search_index)
    return r"""
<script>
const SEARCH_INDEX = """ + index_json + r""";

// ========== SEARCH ==========
(function() {
  const input = document.getElementById('site-search');
  const results = document.getElementById('search-results');
  if (!input || !results) return;

  function render(matches, query) {
    if (!matches.length) {
      results.innerHTML = '<div class="search-empty">No matches for &ldquo;' + query + '&rdquo;</div>';
      results.style.display = 'block';
      return;
    }
    results.innerHTML = matches.map(function(m) {
      const chips = m.funds.map(function(f) { return '<span class="search-fund-chip">' + f + '</span>'; }).join('');
      return '<a href="index.html#' + m.ticker + '" class="search-result">' +
        '<span class="search-ticker">' + m.ticker + '</span>' +
        '<span class="search-name">' + m.name + '</span>' +
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
             item.name.toLowerCase().indexOf(q) !== -1;
    }).slice(0, 12);
    render(matches, q);
  });

  // Explicit click handler — handles same-page anchors smoothly with highlight,
  // and falls through to cross-page navigation for tickers not on this page.
  results.addEventListener('click', function(e) {
    const link = e.target.closest('.search-result');
    if (!link) return;
    const hashIdx = link.href.indexOf('#');
    if (hashIdx === -1) return;
    const ticker = link.href.substring(hashIdx + 1);
    const card = document.getElementById(ticker);
    if (card) {
      e.preventDefault();
      card.scrollIntoView({ behavior: 'smooth', block: 'start' });
      history.replaceState(null, '', '#' + ticker);
      card.classList.remove('flash');
      void card.offsetWidth; // force reflow so animation restarts
      card.classList.add('flash');
      results.style.display = 'none';
      input.value = '';
    }
    // else: let the browser navigate cross-page normally
  });

  // Flash a card when arriving via #anchor on initial load (e.g. cross-page nav)
  if (window.location.hash) {
    setTimeout(function() {
      const t = window.location.hash.substring(1);
      const card = document.getElementById(t);
      if (card) {
        card.scrollIntoView({ behavior: 'smooth', block: 'start' });
        card.classList.add('flash');
      }
    }, 100);
  }

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
    // Press '/' to focus search
    if (e.key === '/' && document.activeElement !== input) {
      e.preventDefault();
      input.focus();
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


def build_fund_page(fund_slug: str, fund_label: str, study: dict, holdings_by_fund: dict, as_of: str, search_index: list) -> str:
    holdings = holdings_by_fund[fund_slug]
    companies = study["companies"]
    districts = study["districts"]
    district_order = study["district_order"]
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

    # Build district sections
    sections = []
    for d in district_order:
        bucket = by_district[d]
        if not bucket:
            continue
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

    # Universe sections
    universe_sections = []
    for d in district_order:
        bucket = by_district[d]
        if not bucket:
            continue
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=str(date.today()))
    args = parser.parse_args()

    study = load_study()
    holdings_by_fund = {slug: load_holdings(slug) for slug, _ in FUNDS}
    search_index = build_search_index(study, holdings_by_fund)

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


if __name__ == "__main__":
    main()
