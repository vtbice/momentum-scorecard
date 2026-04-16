#!/usr/bin/env python3
"""
Build Prosper Momentum Scorecard Dashboard (MERGED)

Reads scorecard_data.json and generates a standalone HTML dashboard
with tabbed navigation, market pulse analysis, sectors, and stock screener.
All data embedded as JavaScript variables. No React, no build tools.
"""

import json
import math
from datetime import datetime
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
INPUT_JSON = SCRIPT_DIR / 'scorecard_data.json'
OUTPUT_HTML = SCRIPT_DIR.parent / 'Dashboards' / 'Momentum Scorecard' / 'index.html'

# ============================================================================
# Load Data
# ============================================================================
with open(INPUT_JSON, 'r') as f:
    data = json.load(f)

# ============================================================================
# Helper Functions
# ============================================================================

def format_market_cap(mc):
    """Format market cap in millions to B/T/M"""
    if mc >= 1000:
        return '%.1fT' % (mc/1000)
    elif mc >= 1:
        return '%.0fB' % mc
    else:
        return '%.0fM' % (mc*1000)

def calculate_150ma(prices):
    """Calculate 150-day moving average"""
    if len(prices) < 150:
        return None
    return sum(prices[-150:]) / 150

def get_tier_color(tier):
    """Return color class for tier"""
    if tier <= 2:
        return 'tier-dark-green'
    elif tier <= 4:
        return 'tier-green'
    elif tier <= 6:
        return 'tier-amber'
    elif tier <= 8:
        return 'tier-red-orange'
    else:
        return 'tier-dark-red'

def get_trend_badge_color(trend):
    """Return color class for trend badge"""
    if trend == 'Uptrend':
        return 'badge-green'
    elif trend == 'Pullback':
        return 'badge-amber'
    elif trend == 'Downtrend':
        return 'badge-red'
    elif trend == 'Snapback':
        return 'badge-blue'
    return 'badge-gray'

def health_color(score, total):
    """Return color class for health score"""
    pct = (score / total) * 100 if total > 0 else 0
    if pct >= 67:
        return 'health-green'
    elif pct >= 45:
        return 'health-amber'
    else:
        return 'health-red'

def health_status_label(score, total):
    """Get status label for health score"""
    pct = (score / total) * 100 if total > 0 else 0
    if pct >= 67:
        return 'Strong'
    elif pct >= 45:
        return 'Cautious'
    else:
        return 'Challenged'

# ============================================================================
# Generate HTML
# ============================================================================

# Load research index (if any companies have been researched)
RESEARCH_INDEX_FILE = SCRIPT_DIR / 'research' / 'research_index.json'
research_index = {"companies": []}
if RESEARCH_INDEX_FILE.exists():
    try:
        with open(RESEARCH_INDEX_FILE) as f:
            research_index = json.load(f)
    except Exception:
        pass

# Prepare data for JavaScript embedding
js_data = {
    'market': data['market'],
    'sectors': data['sectors'],
    'industries': data.get('industries', []),
    'pendingRemoval': data.get('pendingRemoval', []),
    'stocks': data['stocks'],
    'sp500_daily_dates': data['sp500_daily_dates'],
    'sp500_daily_prices': data['sp500_daily_prices'],
    'generated': data['_generated'],
    'stocks_count': data['_stocks_count'],
    'pullbackStats': data.get('pullbackStats', {}),
}

# Hardcoded breadth historical context
breadth_history = [
    {"range": "Above 90%", "pctTime": 0.8, "fwd": 10.7},
    {"range": "80-90%", "pctTime": 9.3, "fwd": 13.2},
    {"range": "70-80%", "pctTime": 15.2, "fwd": 13.9},
    {"range": "60-70%", "pctTime": 22.3, "fwd": 12.6},
    {"range": "50-60%", "pctTime": 18.9, "fwd": 6.9},
    {"range": "40-50%", "pctTime": 14.9, "fwd": 6.7},
    {"range": "30-40%", "pctTime": 8.7, "fwd": 6.2},
    {"range": "20-30%", "pctTime": 4.7, "fwd": 9.5},
    {"range": "10-20%", "pctTime": 3.8, "fwd": 22.2},
    {"range": "Below 10%", "pctTime": 1.4, "fwd": 44.1},
]

html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Momentum Scorecard</title>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600;700&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'DM Sans', sans-serif;
            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
            color: #0f172a;
            line-height: 1.6;
            font-size: 15px;
        }

        header {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            padding: 20px 32px;
            border-bottom: 3px solid #10b981;
        }

        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }

        .header-title {
            font-family: 'Fraunces', serif;
            font-size: 32px;
            font-weight: 700;
            letter-spacing: 0.02em;
            color: white;
        }

        .header-title .momentum {
            color: #10b981;
        }

        .header-sub {
            font-size: 13px;
            color: #64748b;
            margin-top: 4px;
        }

        .header-right {
            text-align: right;
            color: #64748b;
            font-size: 14px;
        }

        main {
            max-width: 1400px;
            margin: 32px auto;
            padding: 0 24px;
        }

        /* Tabs */
        .tab-nav {
            display: flex;
            gap: 8px;
            margin-bottom: 24px;
            border-bottom: 2px solid #e2e8f0;
        }

        .tab-btn {
            padding: 12px 20px;
            border: none;
            background: none;
            cursor: pointer;
            font-family: 'DM Sans', sans-serif;
            font-size: 15px;
            font-weight: 600;
            color: #64748b;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
            transition: all 0.2s;
            cursor: pointer;
        }

        .tab-btn:hover {
            color: #334155;
        }

        .tab-btn.active {
            color: #10b981;
            border-bottom-color: #10b981;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        /* Sub-tabs */
        .subtab-nav {
            display: flex;
            gap: 8px;
            margin-bottom: 24px;
            padding-left: 0;
            justify-content: center;
            flex-wrap: wrap;
            border-bottom: 2px solid #e2e8f0;
        }

        .subtab-btn {
            padding: 10px 20px;
            border: none;
            background: none;
            cursor: pointer;
            font-family: 'DM Sans', sans-serif;
            font-size: 14px;
            font-weight: 600;
            color: #64748b;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
            transition: all 0.2s;
        }

        .subtab-btn:hover {
            color: #334155;
        }

        .subtab-btn.active {
            color: #10b981;
            border-bottom-color: #10b981;
        }

        .subtab-content {
            display: none;
        }

        .subtab-content.active {
            display: block;
        }

        .card {
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            border: 1px solid #e2e8f0;
        }

        .card-title {
            font-family: 'Fraunces', serif;
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 20px;
            color: #0f172a;
            text-align: center;
            padding-bottom: 14px;
            border-bottom: 2px solid #e2e8f0;
        }

        /* Health Score Banner */
        .health-banner {
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border-radius: 16px;
            padding: 24px;
            color: white;
            margin-bottom: 24px;
            position: relative;
            overflow: hidden;
        }

        .health-banner::before {
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            width: 200px;
            height: 200px;
            background: radial-gradient(circle at top right, #10b98120, transparent 70%);
            pointer-events: none;
        }

        .health-banner-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: relative;
            z-index: 1;
        }

        .health-banner-left {
            display: flex;
            align-items: baseline;
            gap: 8px;
            margin-right: 40px;
        }

        .health-score-pct {
            font-family: 'Fraunces', serif;
            font-size: 52px;
            font-weight: 900;
        }

        .health-score-total {
            font-size: 18px;
            font-weight: 500;
            color: #64748b;
        }

        .health-banner-label {
            font-family: 'DM Sans', sans-serif;
            font-size: 18px;
            font-weight: 700;
            margin-top: 2px;
            letter-spacing: 0.5px;
        }

        .health-banner-right {
            text-align: right;
        }

        .health-counts {
            font-size: 14px;
            color: #64748b;
            margin-bottom: 6px;
        }

        .health-toggle {
            font-size: 12px;
            color: #64748b;
            display: none;
            align-items: center;
            gap: 4px;
            justify-content: flex-end;
        }

        .health-detail-panel {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 32px;
            margin-top: 24px;
            padding-top: 24px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }

        .health-column h3 {
            font-family: 'Fraunces', serif;
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 16px;
            color: white;
        }

        .health-item {
            display: flex;
            gap: 12px;
            margin-bottom: 12px;
            font-size: 14px;
        }

        .health-item-icon {
            flex-shrink: 0;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 14px;
        }

        .health-wins .health-item-icon {
            color: #10b981;
        }

        .health-misses .health-item-icon {
            color: #ef4444;
        }

        .health-item-text {
            flex: 1;
        }

        .health-item-label {
            color: #e2e8f0;
            display: block;
            margin-bottom: 2px;
        }

        .health-item-weight {
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            color: #64748b;
        }

        /* Grid layouts */
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }

        .grid-3 {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 24px;
        }

        .grid-4 {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 24px;
        }

        .grid-2x2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }

        .full-width-card {
            grid-column: 1 / -1;
        }

        /* Indicator cards */
        .indicator-card {
            background: #f8fafc;
            border-radius: 12px;
            padding: 16px;
            border: 1px solid #e2e8f0;
            border-left: 4px solid #cbd5e1;
        }

        .indicator-label {
            font-size: 14px;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }

        .indicator-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 28px;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 8px;
        }

        .indicator-badge {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
        }

        .badge-positive {
            background: #d1fae5;
            color: #065f46;
        }

        .badge-neutral {
            background: #fef3c7;
            color: #92400e;
        }

        .badge-negative {
            background: #fecaca;
            color: #991b1b;
        }

        .badge-green { background: #dcfce7; color: #166534; }
        .badge-amber { background: #fef3c7; color: #92400e; }
        .badge-red { background: #fee2e2; color: #991b1b; }
        .badge-blue { background: #dbeafe; color: #1e40af; }
        .badge-gray { background: #e2e8f0; color: #475569; }

        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
        }

        /* Metric rows */
        .metric-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-top: 1px solid #e2e8f0;
            font-size: 13px;
        }

        .metric-row:first-child {
            border-top: none;
        }

        .metric-label {
            color: #334155;
            font-size: 15px;
            font-weight: 500;
        }

        .metric-value {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            color: #0f172a;
            font-size: 16px;
        }

        /* Progress bar */
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
            margin: 8px 0;
            position: relative;
        }

        .progress-fill {
            height: 100%;
            background: #10b981;
            border-radius: 4px;
            transition: width 0.3s;
        }

        .progress-threshold {
            position: absolute;
            top: 0;
            height: 100%;
            width: 2px;
            background: #64748b;
            z-index: 2;
        }

        /* Chart */
        .chart-container {
            position: relative;
            width: 100%;
            height: 300px;
            margin-top: 16px;
        }

        .chart-legend {
            display: flex;
            gap: 20px;
            margin-bottom: 16px;
            font-size: 14px;
        }

        .chart-legend-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .chart-legend-color {
            width: 12px;
            height: 12px;
            border-radius: 2px;
        }

        /* Sector table */
        .sector-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }

        .sector-table thead {
            background: #f8fafc;
            border-bottom: 2px solid #e2e8f0;
        }

        .sector-table th {
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #475569;
            font-size: 13px;
            cursor: pointer;
            user-select: none;
            transition: background 0.15s;
        }

        .sector-table th:hover {
            background: #e2e8f0;
            color: #0f172a;
        }

        .sector-table th:nth-child(2) {
            text-align: center;
        }

        .sector-table th:nth-child(3),
        .sector-table th:nth-child(4),
        .sector-table th:nth-child(5) {
            text-align: right;
        }

        .sector-table td {
            padding: 12px;
            border-bottom: 1px solid #e2e8f0;
            font-size: 13px;
        }

        .sector-table tbody tr:hover {
            background: #f8fafc;
            cursor: pointer;
        }

        .sector-name {
            font-weight: 600;
            color: #0f172a;
            cursor: pointer;
        }

        .sector-name:hover {
            color: #10b981;
        }

        .pct-cell {
            text-align: right;
            font-family: 'JetBrains Mono', monospace;
        }

        .pct-cell.high { color: #10b981; font-weight: 600; }
        .pct-cell.med { color: #f59e0b; font-weight: 600; }
        .pct-cell.low { color: #ef4444; font-weight: 600; }

        /* Trend bar */
        .trend-bar {
            display: flex;
            height: 24px;
            border-radius: 4px;
            overflow: hidden;
            background: #e2e8f0;
            font-size: 12px;
            font-weight: 600;
            color: white;
        }

        .trend-up { background: #10b981; }
        .trend-pb { background: #f59e0b; }
        .trend-dn { background: #ef4444; }
        .trend-sb { background: #3b82f6; }

        .trend-segment {
            display: flex;
            align-items: center;
            justify-content: center;
            flex-grow: 1;
        }

        /* Stock table */
        .stock-controls {
            display: flex;
            gap: 16px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }

        .search-box {
            flex: 1;
            min-width: 200px;
        }

        .search-box input {
            width: 100%;
            padding: 10px 14px;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            font-family: 'DM Sans', sans-serif;
            font-size: 13px;
        }

        .search-box input:focus {
            outline: none;
            border-color: #10b981;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
        }

        .filter-select {
            padding: 10px 14px;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            background: white;
            font-family: 'DM Sans', sans-serif;
            font-size: 13px;
            cursor: pointer;
        }

        .filter-select:focus {
            outline: none;
            border-color: #10b981;
        }

        .stock-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }

        .stock-table thead {
            background: #f8fafc;
            border-bottom: 2px solid #e2e8f0;
        }

        .stock-table th {
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #475569;
            cursor: pointer;
            user-select: none;
            font-size: 13px;
            transition: background 0.15s;
        }

        .stock-table th:hover {
            background: #e2e8f0;
            color: #0f172a;
        }

        .stock-table td {
            padding: 12px;
            border-bottom: 1px solid #e2e8f0;
            font-size: 13px;
        }

        .stock-table tbody tr:hover {
            background: #f8fafc;
        }

        .stock-ticker {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 900;
            font-size: 14px;
            color: #0f172a;
            cursor: pointer;
        }

        .stock-ticker:hover {
            color: #10b981;
        }

        .stock-company {
            color: #64748b;
        }

        .trend-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 600;
        }

        .trend-up-badge { background: #d1fae5; color: #065f46; }
        .trend-pb-badge { background: #fef3c7; color: #92400e; }
        .trend-dn-badge { background: #fecaca; color: #991b1b; }
        .trend-sb-badge { background: #dbeafe; color: #1e40af; }

        .pagination {
            display: flex;
            justify-content: center;
            gap: 8px;
            margin-top: 20px;
        }

        .page-btn {
            padding: 8px 12px;
            border: 1px solid #e2e8f0;
            background: white;
            cursor: pointer;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
        }

        .page-btn.active {
            background: #10b981;
            color: white;
            border-color: #10b981;
        }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }

        .modal.active {
            display: flex;
        }

        .modal-content {
            background: white;
            border-radius: 16px;
            padding: 32px;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
        }

        .modal-close {
            position: absolute;
            top: 16px;
            right: 16px;
            background: rgba(255, 255, 255, 0.2);
            border: none;
            font-size: 28px;
            cursor: pointer;
            color: white;
            width: 44px;
            height: 44px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }

        .modal-close:hover {
            background: rgba(255, 255, 255, 0.3);
        }

        /* Color classes */
        .color-green { color: #10b981; }
        .color-amber { color: #f59e0b; }
        .color-red { color: #ef4444; }
        .color-blue { color: #3b82f6; }

        /* Synthesis */
        .synthesis-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }

        .synthesis-card {
            background: #f8fafc;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #e2e8f0;
        }

        .synthesis-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
        }

        .synthesis-title {
            font-family: 'Fraunces', serif;
            font-size: 16px;
            font-weight: 700;
            color: #0f172a;
        }

        .synthesis-view {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 700;
        }

        .synthesis-desc {
            font-size: 13px;
            color: #475569;
            line-height: 1.5;
            font-weight: 400;
        }

        /* Breadth detail */
        .breadth-detail {
            margin-top: 16px;
        }

        .breadth-table {
            width: 100%;
            font-size: 12px;
        }

        .breadth-table th,
        .breadth-table td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }

        .breadth-table th {
            background: #f8fafc;
            font-weight: 600;
            color: #475569;
        }

        .breadth-range {
            color: #0f172a;
            font-weight: 500;
        }

        .breadth-num {
            text-align: right;
            font-family: 'JetBrains Mono', monospace;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .card { padding: 16px; }
            .grid-2, .grid-3, .grid-4 {
                grid-template-columns: 1fr;
            }
            .health-detail-panel {
                grid-template-columns: 1fr;
            }
            .synthesis-grid {
                grid-template-columns: 1fr;
            }
            .header-content {
                flex-direction: column;
                text-align: center;
                gap: 12px;
            }
            .header-right {
                text-align: center;
            }
            .sub-tabs { flex-wrap: wrap; }
            .stock-table { font-size: 13px; }
            .stock-table th, .stock-table td { padding: 8px 6px; }
        }
    </style>
</head>
<body>

<header>
    <div class="header-content">
        <div>
            <div class="header-title"><span class="momentum">Momentum</span> Scorecard</div>
        </div>
        <div class="header-right" id="headerDate"></div>
    </div>
</header>

<div style="max-width: 1400px; margin: 8px auto 0; padding: 0 24px;">
    <div style="font-size: 12px; color: #64748b; line-height: 1.5; padding: 8px 16px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; text-align: center;">For educational and analytical purposes only — not investment advice. Past performance does not guarantee future results. All data is sourced from public APIs and may be delayed.</div>
</div>

<main>
    <!-- Tab Navigation -->
    <div class="tab-nav">
        <button class="tab-btn active" onclick="switchTab('pulse')">Market Pulse</button>
        <button class="tab-btn" onclick="switchTab('sectors')">Sectors</button>
        <button class="tab-btn" onclick="switchTab('industries')">Industries</button>
        <button class="tab-btn" onclick="switchTab('screener')">Stock Screener</button>
        <button class="tab-btn" onclick="switchTab('research')">Company Research</button>
        <button class="tab-btn" onclick="switchTab('sources')">Sources &amp; Definitions</button>
    </div>

    <!-- TAB 1: MARKET PULSE -->
    <div id="pulse" class="tab-content active">
        <!-- Sub-tabs — immediately visible below main tabs -->
        <div class="subtab-nav" style="margin-top: 0;">
            <button class="subtab-btn active" onclick="switchSubtab('pulse', 'overview', this)">Overview</button>
            <button class="subtab-btn" onclick="switchSubtab('pulse', 'macro', this)">Macro</button>
            <button class="subtab-btn" onclick="switchSubtab('pulse', 'fundamentals', this)">Fundamentals</button>
            <button class="subtab-btn" onclick="switchSubtab('pulse', 'technicals', this)">Technicals</button>
        </div>

        <!-- Health Score Banner -->
        <div class="health-banner">
            <div class="health-banner-content" style="flex-direction: column; align-items: center; text-align: center; cursor: pointer;" onclick="showExplain('healthScore')" title="Click to learn how this score is calculated">
                <div class="health-banner-label" id="healthScore" style="font-size: 20px; letter-spacing: 1px; text-transform: uppercase;"></div>
                <div class="health-score-pct"><span id="healthPct"></span><span class="health-score-total">/ 100</span></div>
                <div class="health-banner-label" id="healthLabel" style="font-size: 22px; margin-top: 4px;"></div>
                <!-- Spectrum Gauge -->
                <div id="spectrumGauge" style="width: 100%; max-width: 500px; margin: 16px auto 8px;"></div>
                <div class="health-counts" id="healthCounts" style="margin-top: 8px;"></div>
            </div>
        </div>

        <!-- Overview Sub-tab -->
        <div id="pulse-overview" class="subtab-content active">
            <!-- Tailwinds / Headwinds detail (inside Overview so it swaps when tabs change) -->
            <div class="health-banner" style="margin-bottom: 24px;">
                <div id="healthDetail" class="health-detail-panel">
                    <div class="health-column health-wins">
                        <h3>Tailwinds</h3>
                        <div id="tailwindsList"></div>
                    </div>
                    <div class="health-column health-misses">
                        <h3>Headwinds</h3>
                        <div id="headwindsList"></div>
                    </div>
                </div>
            </div>

            <!-- 4 Indicator Summary Cards -->
            <div class="grid-4" style="margin-bottom: 24px;">
                <div class="indicator-card" id="trendCard" onclick="showExplain('trend')" style="cursor:pointer;" title="Click to learn more">
                    <div class="indicator-label">Market Trend <span style="font-size:11px;color:#10b981;">ⓘ</span></div>
                    <div class="indicator-value" id="trendScore"></div>
                </div>
                <div class="indicator-card" id="breadthCard" onclick="showExplain('breadth')" style="cursor:pointer;" title="Click to learn more">
                    <div class="indicator-label">Market Breadth <span style="font-size:11px;color:#10b981;">ⓘ</span></div>
                    <div class="indicator-value" id="breadthValue"></div>
                </div>
                <div class="indicator-card" id="earningsCard" onclick="showExplain('earnings')" style="cursor:pointer;" title="Click to learn more">
                    <div class="indicator-label">Earnings <span style="font-size:11px;color:#10b981;">ⓘ</span></div>
                    <div class="indicator-value" id="earningsValue"></div>
                </div>
                <div class="indicator-card" id="valuationCard" onclick="showExplain('valuation')" style="cursor:pointer;" title="Click to learn more">
                    <div class="indicator-label">Valuation <span style="font-size:11px;color:#10b981;">ⓘ</span></div>
                    <div class="indicator-value" id="valuationValue"></div>
                </div>
            </div>

            <!-- S&P 500 Trend Chart (full width, V1 style) -->
            <div class="card" style="margin-bottom: 24px;">
                <div class="card-title">S&P 500 Trend</div>
                <div class="chart-container" id="sp500Chart" style="height: 320px;"></div>
            </div>

            <!-- Trend & Breadth — right after the chart -->
            <div style="margin-bottom: 24px;">
                <div class="card">
                    <div class="card-title">Market Trend</div>
                    <div id="trendCardContent"></div>
                </div>

                <div class="card">
                    <div class="card-title">Market Breadth</div>
                    <div id="breadthCardContent"></div>
                </div>
            </div>

            <!-- Historical Context -->
            <div id="historicalContextContent" style="margin-bottom: 24px;"></div>
        </div>

        <!-- Macro Sub-tab -->
        <div id="pulse-macro" class="subtab-content">
            <div id="macroContent"></div>
        </div>

        <!-- Fundamentals Sub-tab -->
        <div id="pulse-fundamentals" class="subtab-content">
            <div id="fundamentalsContent"></div>
        </div>

        <!-- Technicals Sub-tab -->
        <div id="pulse-technicals" class="subtab-content">
            <div id="technicalsContent"></div>
        </div>
    </div>

    <!-- TAB 2: SECTORS -->
    <div id="sectors" class="tab-content">
        <div class="card">
            <div class="card-title">Sector Momentum Analysis</div>
            <!-- Trend Mix Color Legend -->
            <div style="display: flex; gap: 16px; margin-bottom: 12px; font-size: 14px; color: #64748b; align-items: center;">
                <span style="font-weight: 600;">Trend Mix:</span>
                <span style="display: flex; align-items: center; gap: 4px;"><span style="width: 12px; height: 12px; border-radius: 2px; background: #10b981; display: inline-block;"></span> Uptrend</span>
                <span style="display: flex; align-items: center; gap: 4px;"><span style="width: 12px; height: 12px; border-radius: 2px; background: #f59e0b; display: inline-block;"></span> Pullback</span>
                <span style="display: flex; align-items: center; gap: 4px;"><span style="width: 12px; height: 12px; border-radius: 2px; background: #ef4444; display: inline-block;"></span> Downtrend</span>
                <span style="display: flex; align-items: center; gap: 4px;"><span style="width: 12px; height: 12px; border-radius: 2px; background: #3b82f6; display: inline-block;"></span> Snapback</span>
            </div>
            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 12px; font-style: italic;">Click any column header to sort. Click a sector row to expand and see individual stocks.</div>
            <table class="sector-table" id="sectorsTable">
                <thead>
                    <tr>
                        <th onclick="sortSectors('name')" style="cursor: pointer;">Sector</th>
                        <th onclick="sortSectors('trend')" style="cursor: pointer; text-align: center;">Trend Mix</th>
                        <th onclick="sortSectors('uptrend')" style="cursor: pointer; text-align: right;">% Uptrend</th>
                        <th onclick="sortSectors('momentum')" style="cursor: pointer; text-align: right;">Rel. Momentum</th>
                        <th onclick="sortSectors('count')" style="cursor: pointer; text-align: right;"># Stocks</th>
                    </tr>
                </thead>
                <tbody id="sectorsTableBody"></tbody>
            </table>
        </div>
        <div id="expandedSector" class="card" style="display: none; margin-top: 24px;">
            <div class="card-title" id="expandedSectorTitle"></div>
            <table class="stock-table" id="expandedStocksTable">
                <thead>
                    <tr>
                        <th onclick="sortExpandedStocks('ticker')" style="cursor:pointer;">Ticker</th>
                        <th onclick="sortExpandedStocks('company')" style="cursor:pointer;">Company</th>
                        <th onclick="sortExpandedStocks('trend')" style="cursor:pointer;">Trend</th>
                        <th onclick="sortExpandedStocks('tr1wk')" style="cursor:pointer;">1 Wk Ago</th>
                        <th onclick="sortExpandedStocks('trChg')" style="cursor:pointer;">Trend Chg</th>
                        <th onclick="sortExpandedStocks('ret1m')" style="cursor:pointer; text-align:right;">1M Ret</th>
                        <th onclick="sortExpandedStocks('ret12m')" style="cursor:pointer; text-align:right;">12M Ret</th>
                    </tr>
                </thead>
                <tbody id="expandedStocksBody"></tbody>
            </table>
        </div>
    </div>

    <!-- TAB 3: INDUSTRIES -->
    <div id="industries" class="tab-content">
        <div class="card">
            <div class="card-title">Industry Momentum Analysis</div>
            <div style="display: flex; gap: 16px; margin-bottom: 12px; font-size: 14px; color: #64748b; align-items: center;">
                <span style="font-weight: 600;">Trend Mix:</span>
                <span style="display: flex; align-items: center; gap: 4px;"><span style="width: 12px; height: 12px; border-radius: 2px; background: #10b981; display: inline-block;"></span> Uptrend</span>
                <span style="display: flex; align-items: center; gap: 4px;"><span style="width: 12px; height: 12px; border-radius: 2px; background: #f59e0b; display: inline-block;"></span> Pullback</span>
                <span style="display: flex; align-items: center; gap: 4px;"><span style="width: 12px; height: 12px; border-radius: 2px; background: #ef4444; display: inline-block;"></span> Downtrend</span>
                <span style="display: flex; align-items: center; gap: 4px;"><span style="width: 12px; height: 12px; border-radius: 2px; background: #3b82f6; display: inline-block;"></span> Snapback</span>
            </div>
            <div style="margin-bottom: 12px;">
                <select class="filter-select" id="industrySectorFilter" onchange="renderIndustries()">
                    <option value="">All Sectors</option>
                </select>
            </div>
            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 12px; font-style: italic;">Click any column header to sort. Click an industry row to expand and see individual stocks.</div>
            <table class="sector-table" id="industriesTable">
                <thead>
                    <tr>
                        <th onclick="sortIndustries('name')" style="cursor: pointer;">Industry</th>
                        <th onclick="sortIndustries('sector')" style="cursor: pointer;">Sector</th>
                        <th onclick="sortIndustries('trend')" style="cursor: pointer; text-align: center;">Trend Mix</th>
                        <th onclick="sortIndustries('uptrend')" style="cursor: pointer; text-align: right;">% Uptrend</th>
                        <th onclick="sortIndustries('momentum')" style="cursor: pointer; text-align: right;">Rel. Mom</th>
                        <th onclick="sortIndustries('count')" style="cursor: pointer; text-align: right;"># Stocks</th>
                    </tr>
                </thead>
                <tbody id="industriesTableBody"></tbody>
            </table>
        </div>
        <div id="expandedIndustry" class="card" style="display: none; margin-top: 24px;">
            <div class="card-title" id="expandedIndustryTitle"></div>
            <table class="stock-table" id="expandedIndustryStocksTable">
                <thead>
                    <tr>
                        <th onclick="sortExpandedIndustryStocks('ticker')" style="cursor:pointer;">Ticker</th>
                        <th onclick="sortExpandedIndustryStocks('company')" style="cursor:pointer;">Company</th>
                        <th onclick="sortExpandedIndustryStocks('trend')" style="cursor:pointer;">Trend</th>
                        <th onclick="sortExpandedIndustryStocks('tr1wk')" style="cursor:pointer;">1 Wk Ago</th>
                        <th onclick="sortExpandedIndustryStocks('trChg')" style="cursor:pointer;">Trend Chg</th>
                        <th onclick="sortExpandedIndustryStocks('ret1m')" style="cursor:pointer; text-align:right;">1M Ret</th>
                        <th onclick="sortExpandedIndustryStocks('ret12m')" style="cursor:pointer; text-align:right;">12M Ret</th>
                    </tr>
                </thead>
                <tbody id="expandedIndustryStocksBody"></tbody>
            </table>
        </div>
    </div>

    <!-- TAB 4: STOCK SCREENER -->
    <div id="screener" class="tab-content">
        <div class="card">
            <div class="card-title">Stock Momentum Screener</div>

            <!-- Controls -->
            <div class="stock-controls">
                <div class="search-box">
                    <input type="text" id="searchInput" placeholder="Search ticker or company..." onkeyup="filterStocks()">
                </div>
                <select class="filter-select" id="sectorFilter" onchange="filterStocks()">
                    <option value="">All Sectors</option>
                </select>
                <select class="filter-select" id="trendFilter" onchange="filterStocks()">
                    <option value="">All Trends</option>
                    <option value="Uptrend">Uptrend</option>
                    <option value="Pullback">Pullback</option>
                    <option value="Downtrend">Downtrend</option>
                    <option value="Snapback">Snapback</option>
                </select>
            </div>

            <!-- Summary Strip -->
            <div id="summaryStrip" style="background: #f8fafc; border-radius: 8px; padding: 10px 16px; margin-bottom: 12px; font-size: 13px; display: flex; gap: 20px; flex-wrap: wrap;"></div>
            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 8px; font-style: italic;">Click any column header to sort. Click a row to see stock details.</div>

            <!-- Stock Table -->
            <table class="stock-table" id="stockTable">
                <thead>
                    <tr>
                        <th style="width:36px;text-align:center;">#</th>
                        <th onclick="sortStocks('ticker')" style="text-align:left;">Ticker</th>
                        <th onclick="sortStocks('sector')" style="text-align:left;">Sector</th>
                        <th onclick="sortStocks('price')" style="text-align:right;">Price</th>
                        <th onclick="sortStocks('ma150')" style="text-align:right;">150d MA</th>
                        <th onclick="sortStocks('trend')" style="text-align:center;">Trend</th>
                        <th onclick="sortStocks('tr1wk')" style="text-align:center;">1 Wk Ago</th>
                        <th onclick="sortStocks('trChg')" style="text-align:center;">Trend Chg</th>
                        <th onclick="sortStocks('momentum')" style="text-align:center;">Rel. Mom</th>
                        <th onclick="sortStocks('vsMa')" style="text-align:right;">vs MA</th>
                        <th onclick="sortStocks('ret1m')" style="text-align:right;">1M Ret</th>
                        <th onclick="sortStocks('ret12m')" style="text-align:right;">12M Ret</th>
                        <th style="text-align:center;">
                            <span onclick="sortStocks('rasr')" style="cursor:pointer;">RASR</span>
                            <span id="rasrToggle" onclick="event.stopPropagation();toggleRASR();" style="display:inline-block;width:22px;height:22px;line-height:20px;text-align:center;background:rgba(255,255,255,0.2);border:1px solid rgba(255,255,255,0.4);border-radius:4px;font-size:14px;font-weight:700;cursor:pointer;margin-left:6px;vertical-align:middle;" title="Expand/collapse RASR components">+</span>
                        </th>
                        <th onclick="sortStocks('step')" class="rasr-detail" style="text-align:center;display:none;">STEP</th>
                        <th onclick="sortStocks('epsRev')" class="rasr-detail" style="text-align:center;display:none;">EPS Rev</th>
                        <th onclick="sortStocks('absMom')" class="rasr-detail" style="text-align:center;display:none;">Abs Mom</th>
                        <th onclick="sortStocks('relMomR')" class="rasr-detail" style="text-align:center;display:none;">Rel Mom</th>
                    </tr>
                </thead>
                <tbody id="stockTableBody"></tbody>
            </table>

            <!-- Pagination -->
            <div class="pagination" id="pagination"></div>
        </div>
    </div>

    <!-- TAB 4: RESEARCH -->
    <div id="research" class="tab-content">
        <div id="researchContent"></div>
    </div>

    <!-- TAB 5: SOURCES & METHODOLOGY -->
    <div id="sources" class="tab-content">
        <div id="sourcesContent"></div>
    </div>
</main>

<!-- Stock Detail Modal -->
<div id="stockModal" class="modal" onclick="closeStockModal(event)">
    <div class="modal-content" onclick="event.stopPropagation()">
        <button class="modal-close" onclick="closeStockModal()">×</button>
        <div id="stockModalBody"></div>
    </div>
</div>

<!-- Explain Modal -->
<div id="explainModal" class="modal" onclick="closeExplain(event)">
    <div class="modal-content" onclick="event.stopPropagation()" style="max-width:550px;">
        <button class="modal-close" onclick="closeExplain()" style="color:#0f172a;background:rgba(0,0,0,0.05);">×</button>
        <div id="explainBody"></div>
    </div>
</div>

<script>
// ============================================================================
// EMBEDDED DATA
// ============================================================================

const DATA = ''' + json.dumps(js_data) + ''';

const MARKET = DATA.market;
const SECTORS = DATA.sectors;
const INDUSTRIES = DATA.industries || [];
const PENDING_REMOVAL = DATA.pendingRemoval || [];
const STOCKS = DATA.stocks;
const SP500_PRICES = DATA.sp500_daily_prices;
const SP500_DATES = DATA.sp500_daily_dates;
const PULLBACK_STATS = DATA.pullbackStats || {};

const BREADTH_HISTORY = ''' + json.dumps(breadth_history) + ''';

const RESEARCH_INDEX = ''' + json.dumps(research_index.get("companies", [])) + ''';

// Colors
const C = {
    emerald: '#10b981', emeraldDark: '#059669', emeraldLight: '#d1fae5',
    red: '#ef4444', redLight: '#fecaca',
    amber: '#f59e0b', amberLight: '#fef3c7',
    indigo: '#6366f1',
    blue: '#3b82f6', blueLight: '#dbeafe',
    purple: '#a855f7',
    s50: '#f8fafc', s100: '#f1f5f9', s200: '#e2e8f0',
    s400: '#94a3b8', s500: '#64748b', s600: '#475569', s700: '#334155', s800: '#1e293b', s900: '#0f172a'
};

// ============================================================================
// STATE
// ============================================================================

let currentTab = 'pulse';
let currentSubtab = {};
let filteredStocks = STOCKS.slice();
let sortColumn = 'momentum';
let sortAsc = false;
let rasrExpanded = false;
let currentPage = 1;
const ITEMS_PER_PAGE = 25;

// ============================================================================
// INIT
// ============================================================================

window.addEventListener('DOMContentLoaded', function() {
    renderHeader();
    renderMarketPulse();
    renderSectors();
    renderStockScreener();
    // Populate industry sector filter and render industries
    var indSectors = [...new Set(INDUSTRIES.map(function(i) { return i.sector; }))].sort();
    var indFilterHtml = '<option value="">All Sectors</option>';
    indSectors.forEach(function(s) { indFilterHtml += '<option value="' + s + '">' + s + '</option>'; });
    if (document.getElementById('industrySectorFilter')) {
        document.getElementById('industrySectorFilter').innerHTML = indFilterHtml;
    }
    renderIndustries();
});

// Plain-English explanations for each health indicator
var INDICATOR_WHY = {
    'Labor Market': 'Low unemployment means people have jobs and spending power — the engine of economic growth.',
    'GDP Growth': 'A growing economy supports corporate profits and stock prices. Below 2% signals a slowdown.',
    'Inflation': 'Stable prices mean the Fed is less likely to raise rates and slow things down.',
    'Credit Spreads': 'Tight spreads mean lenders are confident — companies can borrow cheaply to invest and grow.',
    'Consumer Confidence': 'When people feel good about the economy, they spend more — and spending drives growth.',
    'Mortgage Rates': 'Lower rates boost housing, consumer wealth, and the broader economy. Above 6% starts to pinch.',
    'Yield Curve': 'An inverted yield curve has preceded every recession since the 1960s — one of the most reliable warning signs in finance.',
    'ISM Manufacturing': 'The single best leading indicator of economic turns. Above 50 means factories are expanding; below 50 signals contraction.',
    'Oil Price': 'WTI crude oil price per barrel. High oil prices raise production costs across the economy and push inflation higher, squeezing corporate margins and consumer wallets. Above $90 starts to bite.',
    'Gas Price': 'Average price for a gallon of regular gas. High gas prices hit consumer sentiment hard — people feel it every week at the pump, leaving less money for everything else. Above $4 becomes a real drag on spending.',
    'US Dollar': 'The dollar\\'s value against a basket of major currencies. A strong dollar hurts U.S. multinationals (their foreign earnings translate to fewer dollars) and emerging markets (their dollar-denominated debt gets more expensive). Above 105 is a meaningful headwind.',
    'Initial Jobless Claims': 'Weekly count of people filing for unemployment for the first time. This is one of the earliest warning signs of economic trouble — rising claims show up in the data before they show up in the unemployment rate. Below 250K signals a healthy labor market.',
    'Sales Growth': 'Year-over-year revenue growth for S&P 500 companies. Revenue is the top line — it shows actual demand. Companies can fake earnings growth through cost cuts or buybacks, but they cannot fake sales growth. Above 4% signals genuine business expansion.',
    'AAII Bull Sentiment': 'The AAII weekly survey asks individual investors if they are bullish, bearish, or neutral about the next 6 months. This is used as a contrarian indicator — extreme bullishness (above 45%) often precedes pullbacks, extreme bearishness (below 25%) often precedes rallies. The sweet spot is 25-45% where sentiment is neither euphoric nor panicked.',
    'Real Interest Rate': 'The Fed Funds rate minus inflation. This tells you whether the Fed is actually tightening or not. A real rate above 2% means monetary policy is meaningfully restrictive — it costs real money to borrow, which slows the economy. Below 2% means conditions are more accommodative.',
    'MOVE Index': 'The bond market version of the VIX. It measures expected volatility in Treasury bonds. Below 100 means the bond market is calm and predictable. Above 100 means bond traders are nervous, which often spills into stocks because bonds set the cost of money for everything.',
    'HYG/IEF Ratio': 'High yield bonds (HYG) vs safe Treasury bonds (IEF). When this ratio is rising (above its 150-day average), investors are willing to take on more credit risk for higher returns — that is a risk-on signal. When it is falling, investors are fleeing to safety.',
    'Small Cap / Large Cap': 'Small cap stocks (IWM) vs large cap stocks (SPY). When small caps outperform (ratio above its 150-day average), it signals broad risk appetite — investors are willing to bet on smaller, riskier companies. When large caps dominate, money is hiding in safety.',
    'Discretionary / Staples': 'Consumer discretionary stocks (XLY — things people want) vs consumer staples (XLP — things people need). When discretionary outperforms (ratio above its 150-day average), consumers are confident and spending freely. When staples outperform, consumers are cutting back to essentials.',
    'IPO ETF': 'The Renaissance IPO ETF tracks recently public companies. These are the most speculative, highest-risk stocks in the market. When this ETF is above its 150-day moving average, it tells you investors have a healthy appetite for risk. When it falls below, speculative appetite has dried up.',
    'Bitcoin': 'Bitcoin as a risk appetite indicator. When Bitcoin is above its 150-day moving average, it signals that investors are willing to take on speculative risk across all asset classes. When it drops below, risk appetite is shrinking — money is moving toward safety.',
    'Earnings Growth': 'Companies making more money than last year — the fundamental driver of stock prices.',
    'Profit Margins': 'How much companies keep from each dollar of revenue — a sign of pricing power and efficiency.',
    'Earnings Revisions': 'Whether analysts are raising or cutting estimates — tracks where the trend is heading.',
    'Valuation': 'How expensive stocks are relative to earnings. High P/E means less room for error.',
    'Free Cash Flow': 'Real cash generated after expenses — fuel for dividends, buybacks, and future growth.',
    'Long-Term Trend': 'The S&P 500 vs its 4-year moving average — the big-picture direction of the market.',
    'Medium-Term Trend': 'The S&P 500 vs its 150-day moving average — the intermediate trend direction.',
    'Market Breadth': 'The percentage of stocks trading above their 150-day moving average. Tailwind when above 60% (broad participation, healthy rally) OR below 20% (oversold / capitulation — historically a contrarian buy signal with strong forward returns). The neutral zone between 20-60% is the danger zone where the market is narrow but not yet washed out.',
    'Volatility': 'The VIX fear gauge — low means calm markets, high means uncertainty and hedging activity.',
    'Sentiment': 'Options market positioning — shows whether traders are confident or fearfully hedging.'
};

function getIndicatorWhy(label) {
    for (var key in INDICATOR_WHY) {
        if (label.indexOf(key) !== -1) return INDICATOR_WHY[key];
    }
    return '';
}

// Format an ISO date string (e.g. "2026-03-14") into a readable short date
function fmtAsOf(isoStr) {
    if (!isoStr) return '';
    try {
        var d = new Date(isoStr + 'T00:00:00');
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch(e) { return isoStr; }
}

// Check how many days old a date string is
function daysOld(isoStr) {
    if (!isoStr) return 999;
    try {
        var d = new Date(isoStr + 'T00:00:00');
        var now = new Date();
        return Math.floor((now - d) / (1000 * 60 * 60 * 24));
    } catch(e) { return 999; }
}

// Get the most recent asOf date from a list of FRED keys, with staleness warning
function latestAsOf(keys) {
    var asOf = MARKET.dataAsOf || {};
    var latest = '';
    keys.forEach(function(k) {
        if (asOf[k] && asOf[k] > latest) latest = asOf[k];
    });
    if (!latest) return '';
    var age = daysOld(latest);
    // Manual data thresholds: fundamentals >100 days, weekly data >14 days, FRED >30 days
    var isManualFundamental = keys.some(function(k) { return k === 'fundamentals'; });
    var isManualWeekly = keys.some(function(k) { return k === 'putCall' || k === 'aaii'; });
    var staleThreshold = isManualFundamental ? 100 : isManualWeekly ? 14 : 30;
    var formatted = fmtAsOf(latest);
    if (age > staleThreshold) {
        formatted += ' <span style="color: #f59e0b; font-weight: 600;">(⚠ ' + age + ' days old — may need updating)</span>';
    }
    return formatted;
}

function renderHeader() {
    // Use last S&P 500 trading date as the closing date
    var todayFormatted = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
    var closingDateStr = SP500_DATES.length > 0 ? SP500_DATES[SP500_DATES.length - 1] : '';
    var closingDateFormatted = closingDateStr ? new Date(closingDateStr + 'T00:00:00').toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) : '';

    const health_pct = Math.round((MARKET.healthScore / MARKET.healthTotal) * 100);
    const health_color = health_pct >= 80 ? C.emerald : health_pct >= 60 ? '#f59e0b' : health_pct >= 40 ? '#f97316' : C.red;
    const totalIndicators = MARKET.healthWins.length + MARKET.healthMisses.length;

    document.getElementById('headerDate').innerHTML = todayFormatted + (closingDateFormatted ? ' <span style="color:#94a3b8;">(price data as of ' + closingDateFormatted + ' close)</span>' : '');

    // Health banner
    document.getElementById('healthScore').textContent = 'Market Health Indicators';
    document.getElementById('healthPct').textContent = health_pct;
    document.getElementById('healthLabel').textContent = MARKET.healthLabel;
    document.getElementById('healthLabel').style.color = health_color;
    document.getElementById('healthCounts').textContent = totalIndicators + ' indicators tracked · ' + MARKET.healthWins.length + ' tailwinds · ' + MARKET.healthMisses.length + ' headwinds';

    // Spectrum gauge
    var zones = [
        { label: 'Risk Off', min: 0, max: 25, color: '#ef4444' },
        { label: 'Defensive', min: 25, max: 40, color: '#f97316' },
        { label: 'Cautious', min: 40, max: 60, color: '#f59e0b' },
        { label: 'Optimistic', min: 60, max: 80, color: '#84cc16' },
        { label: 'Bullish', min: 80, max: 100, color: '#10b981' }
    ];
    var gauge_html = '<div style="position: relative; height: 36px; border-radius: 18px; overflow: hidden; display: flex; margin-bottom: 4px;">';
    zones.forEach(function(z) {
        var w = z.max - z.min;
        var isActive = health_pct >= z.min && health_pct < z.max || (z.max === 100 && health_pct === 100);
        gauge_html += '<div style="width: ' + w + '%; background: ' + z.color + '; opacity: ' + (isActive ? '1' : '0.3') + '; display: flex; align-items: center; justify-content: center;' + (isActive ? ' box-shadow: inset 0 0 0 2px white;' : '') + '">';
        gauge_html += '<span style="font-size: 12px; font-weight: 700; color: white; text-transform: uppercase; letter-spacing: 0.5px;">' + z.label + '</span></div>';
    });
    gauge_html += '</div>';
    // Pointer
    var pointerLeft = Math.min(Math.max(health_pct, 2), 98);
    gauge_html += '<div style="position: relative; height: 12px;">';
    gauge_html += '<div style="position: absolute; left: ' + pointerLeft + '%; transform: translateX(-50%); width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent; border-bottom: 8px solid white;"></div>';
    gauge_html += '</div>';
    document.getElementById('spectrumGauge').innerHTML = gauge_html;

    // Health detail with one-liner explanations
    let tailwinds = '';
    MARKET.healthWins.forEach(function(win) {
        var why = getIndicatorWhy(win.label);
        var sinceStr = win.sinceDate ? fmtAsOf(win.sinceDate) : '';
        tailwinds += '<div class="health-item"><div class="health-item-icon">✓</div><div class="health-item-text"><span class="health-item-label">' + win.label + '</span>';
        tailwinds += '<span class="health-item-weight">' + (typeof win.weight === 'number' ? win.weight.toFixed(1) : win.weight) + 'pts';
        if (sinceStr) tailwinds += ' · <span style="color:#10b981;">since ' + sinceStr + '</span>';
        tailwinds += '</span>';
        if (why) tailwinds += '<div style="font-size: 13px; color: #64748b; margin-top: 2px; line-height: 1.4;">' + why + '</div>';
        tailwinds += '</div></div>';
    });
    document.getElementById('tailwindsList').innerHTML = tailwinds;

    let headwinds = '';
    MARKET.healthMisses.forEach(function(miss) {
        var why = getIndicatorWhy(miss.label);
        var sinceStr = miss.sinceDate ? fmtAsOf(miss.sinceDate) : '';
        headwinds += '<div class="health-item"><div class="health-item-icon">✗</div><div class="health-item-text"><span class="health-item-label">' + miss.label + ' — NOT MET</span>';
        headwinds += '<span class="health-item-weight">' + (typeof miss.weight === 'number' ? miss.weight.toFixed(1) : miss.weight) + 'pts';
        if (sinceStr) headwinds += ' · <span style="color:#ef4444;">since ' + sinceStr + '</span>';
        headwinds += '</span>';
        if (why) headwinds += '<div style="font-size: 13px; color: #64748b; margin-top: 2px; line-height: 1.4;">' + why + '</div>';
        headwinds += '</div></div>';
    });
    document.getElementById('headwindsList').innerHTML = headwinds;
}

function renderMarketPulse() {
    // Overview indicators
    const trend_score = MARKET.trend.score || 'Neutral';
    const breadth_pct = Math.round(MARKET.breadth.pctAbove);
    const earnings_growth = MARKET.fundamental.earningsGrowth.toFixed(1);
    const forward_pe = MARKET.fundamental.forwardPE.toFixed(1);

    document.getElementById('trendScore').textContent = trend_score;
    document.getElementById('breadthValue').textContent = breadth_pct + '%';
    document.getElementById('earningsValue').textContent = earnings_growth + '%';
    document.getElementById('valuationValue').textContent = 'P/E ' + forward_pe;

    // Dynamic card colors based on actual data
    function colorCard(id, isGood, isWarn) {
        var card = document.getElementById(id);
        if (!card) return;
        if (isGood) { card.style.borderLeftColor = '#10b981'; card.style.background = '#f0fdf4'; }
        else if (isWarn) { card.style.borderLeftColor = '#f59e0b'; card.style.background = '#fffbeb'; }
        else { card.style.borderLeftColor = '#ef4444'; card.style.background = '#fef2f2'; }
    }
    var trendPos = trend_score === 'Positive';
    var trendWarn = trend_score === 'Neutral';
    colorCard('trendCard', trendPos, trendWarn);
    colorCard('breadthCard', breadth_pct >= 60, breadth_pct >= 40 && breadth_pct < 60);
    colorCard('earningsCard', parseFloat(earnings_growth) > 5, parseFloat(earnings_growth) > 0 && parseFloat(earnings_growth) <= 5);
    colorCard('valuationCard', parseFloat(forward_pe) < 18, parseFloat(forward_pe) >= 18 && parseFloat(forward_pe) < 22);

    // Helper: color a metric value based on bullish/bearish
    function cv(val, isGood) {
        var c = isGood ? '#10b981' : '#ef4444';
        return '<span class="metric-value" style="color:' + c + ';">' + val + '</span>';
    }

    // Trend card (metrics only — chart is now full-width above)
    var sp = MARKET.technical;
    var aboveMA150 = MARKET.trend.r3kVs150MA === 'Above';
    var slopeUp = MARKET.trend.maSlope === 'Rising' || MARKET.trend.maSlope === 'Positive';
    var above4yr = sp.sp500 > sp.sp500MA4yr;
    var above150d = sp.sp500 > sp.sp500MA150;
    var pct4yr = sp.sp500MA4yr > 0 ? ((sp.sp500 / sp.sp500MA4yr - 1) * 100) : 0;
    var pct150 = sp.sp500MA150 > 0 ? ((sp.sp500 / sp.sp500MA150 - 1) * 100) : 0;
    var pct4yrStr = (pct4yr >= 0 ? '+' : '') + pct4yr.toFixed(1) + '%';
    var pct150Str = (pct150 >= 0 ? '+' : '') + pct150.toFixed(1) + '%';

    const trend_html = '<div class="metric-row"><span class="metric-label">S&P 500 vs 150-Day MA</span>' + cv(MARKET.trend.r3kVs150MA, aboveMA150) + '</div>' +
        '<div class="metric-row"><span class="metric-label">MA Slope</span>' + cv(MARKET.trend.maSlope, slopeUp) + '</div>' +
        '<div class="metric-row"><span class="metric-label">S&P 500</span><span class="metric-value">' + sp.sp500.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2}) + '</span></div>' +
        '<div class="metric-row"><span class="metric-label">4-Year MA</span>' + cv(sp.sp500MA4yr.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2}) + ' <span style="font-size:12px;opacity:0.75;">(' + pct4yrStr + ')</span>', above4yr) + '</div>' +
        '<div class="metric-row"><span class="metric-label">150-Day MA</span>' + cv(sp.sp500MA150.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2}) + ' <span style="font-size:12px;opacity:0.75;">(' + pct150Str + ')</span>', above150d) + '</div>';

    document.getElementById('trendCardContent').innerHTML = trend_html;
    setTimeout(function() { drawSP500Chart(); }, 100);

    // Breadth card with spectrum gauge
    var bPct = breadth_pct;
    var bValColor = bPct >= 60 ? '#10b981' : bPct >= 40 ? '#f59e0b' : '#ef4444';

    var breadthZones = [
        { label: 'Oversold', min: 0, max: 20, color: '#991b1b' },
        { label: 'Weak', min: 20, max: 40, color: '#ef4444' },
        { label: 'Narrow', min: 40, max: 60, color: '#f59e0b' },
        { label: 'Healthy', min: 60, max: 80, color: '#84cc16' },
        { label: 'Strong', min: 80, max: 100, color: '#10b981' }
    ];
    var bGauge = '<div style="position: relative; height: 32px; border-radius: 16px; overflow: hidden; display: flex; margin: 12px 0 4px;">';
    breadthZones.forEach(function(z) {
        var w = z.max - z.min;
        var isActive = bPct >= z.min && (bPct < z.max || (z.max === 100 && bPct === 100));
        bGauge += '<div style="width: ' + w + '%; background: ' + z.color + '; opacity: ' + (isActive ? '1' : '0.25') + '; display: flex; align-items: center; justify-content: center;' + (isActive ? ' box-shadow: inset 0 0 0 2px rgba(255,255,255,0.6);' : '') + '">';
        bGauge += '<span style="font-size: 12px; font-weight: 700; color: white; text-transform: uppercase; letter-spacing: 0.3px;">' + z.label + '</span></div>';
    });
    bGauge += '</div>';
    var pointerLeft = Math.min(Math.max(bPct, 2), 98);
    bGauge += '<div style="position: relative; height: 10px;"><div style="position: absolute; left: ' + pointerLeft + '%; transform: translateX(-50%); width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent; border-bottom: 8px solid #1e293b;"></div></div>';

    const breadth_html = '<div class="metric-row"><span class="metric-label">% Above 150-Day MA</span><span class="metric-value" style="color:' + bValColor + '; font-size: 28px;">' + Math.round(parseFloat(breadth_pct)) + '%</span></div>' +
        bGauge +
        '<div class="breadth-detail"><table class="breadth-table"><thead><tr><th>Breadth Range</th><th class="breadth-num">% of Time</th><th class="breadth-num">1yr Fwd %</th></tr></thead><tbody id="breadthHistoryTable"></tbody></table></div>';

    document.getElementById('breadthCardContent').innerHTML = breadth_html;

    let breadth_rows = '';
    BREADTH_HISTORY.forEach(function(row) {
        breadth_rows += '<tr><td class="breadth-range">' + row.range + '</td><td class="breadth-num">' + row.pctTime.toFixed(1) + '%</td><td class="breadth-num">' + row.fwd.toFixed(1) + '%</td></tr>';
    });
    document.getElementById('breadthHistoryTable').innerHTML = breadth_rows;



    // Macro
    const macro_html = renderMacroCards();
    document.getElementById('macroContent').innerHTML = macro_html;

    // Fundamentals
    const fund_html = renderFundamentalsCards();
    document.getElementById('fundamentalsContent').innerHTML = fund_html;

    // Technicals
    const tech_html = renderTechnicalsCards();
    document.getElementById('technicalsContent').innerHTML = tech_html;

    // Historical Context (on overview)
    document.getElementById('historicalContextContent').innerHTML = renderHistoricalContext();
}

function renderSynthesis() {
    const synth = MARKET.synthesis;
    let html = '';

    // Generate dynamic descriptions based on market data
    var m = MARKET.macro;
    var f = MARKET.fundamental;
    var t = MARKET.technical;
    var healthPct = Math.round((MARKET.healthScore / MARKET.healthTotal) * 100);

    // EQUITIES: Regime-based logic
    var eqDesc;
    if (MARKET.breadth.pctAbove < 50 && t.vix > 20 && f.earningsGrowth > 5) {
        eqDesc = 'Markets are in a selective environment — strong earnings support prices but narrow breadth and elevated volatility call for focusing on momentum leaders with proven uptrends.';
    } else if (MARKET.breadth.pctAbove >= 60 && t.vix < 20) {
        eqDesc = 'Broad participation and low volatility create a favorable environment for risk assets. Lean into quality growth and sector leaders.';
    } else if (healthPct < 45) {
        eqDesc = 'Multiple headwinds are stacking up. Reduce exposure, tighten stops, and focus only on the strongest relative momentum names.';
    } else {
        eqDesc = f.earningsGrowth > 5 ? 'Solid earnings growth at +' + f.earningsGrowth.toFixed(1) + '% ' : 'Earnings growth at +' + f.earningsGrowth.toFixed(1) + '% is modest. ';
        eqDesc += MARKET.breadth.pctAbove < 60 ? 'Narrowing breadth calls for selectivity — favor momentum leaders.' : 'Broad participation supports risk-on positioning.';
        eqDesc += t.vix > 20 ? ' VIX above 20 suggests hedging pullback risk.' : '';
    }

    // FIXED INCOME: Regime-based logic
    var fiDesc;
    var ycVal = m.tenYear - m.twoYear;
    if (ycVal < 0) {
        fiDesc = 'An inverted yield curve historically signals economic slowdown within 12-18 months. Favor short duration and high quality. Avoid reaching for yield in lower-quality credit.';
    } else if (ycVal >= 0 && m.hySpread < 4) {
        fiDesc = 'Normal curve with calm credit markets. Attractive entry for quality duration as rates stabilize.';
    } else {
        fiDesc = 'Yields are ' + (m.tenYear > 4 ? 'attractive with the 10-year at ' + m.tenYear.toFixed(2) + '%.' : 'moderate.') + ' ';
        fiDesc += ycVal >= 0 ? 'A normal curve supports duration exposure.' : 'Inverted curve — stay short duration.';
        fiDesc += ' HY spread at ' + m.hySpread.toFixed(2) + '% signals ' + (m.hySpread < 4 ? 'calm credit markets.' : 'caution in lower quality.');
    }

    // CASH: Regime-based logic
    var cashDesc;
    if (healthPct >= 60 && t.vix < 25) {
        cashDesc = 'With a supportive backdrop, excess cash creates drag. Deploy into risk assets during pullbacks but maintain a 5-10% reserve.';
    } else if (healthPct < 45) {
        cashDesc = 'Elevated uncertainty favors higher cash allocation. Keep dry powder ready — the best opportunities emerge when markets are fearful.';
    } else {
        cashDesc = 'With inflation at ' + m.inflation.toFixed(1) + '% and real rates ' + (m.fedFunds - m.inflation > 0 ? 'positive' : 'negative') + ', ';
        cashDesc += healthPct >= 60 ? 'excess cash creates drag. Deploy into risk assets on pullbacks.' : 'keeping dry powder makes sense given elevated uncertainty.';
    }

    const assets = [
        { key: 'equities', label: 'Equities', default_desc: eqDesc },
        { key: 'fixedIncome', label: 'Fixed Income', default_desc: fiDesc },
        { key: 'cash', label: 'Cash', default_desc: cashDesc }
    ];

    assets.forEach(function(asset) {
        const data = synth[asset.key];
        const view = data.view || 'Neutral';
        const view_class = view === 'Positive' ? 'badge-positive' : view === 'Negative' ? 'badge-negative' : 'badge-neutral';
        const desc = data.desc || asset.default_desc;

        html += '<div class="synthesis-card"><div class="synthesis-header"><div class="synthesis-title">' + asset.label + '</div><span class="synthesis-view ' + view_class + '">' + view + '</span></div><div class="synthesis-desc">' + desc + '</div></div>';
    });

    return html;
}

function renderMacroCards() {
    const m = MARKET.macro;
    const cards = [
        {
            title: 'Economic Growth',
            asOf: latestAsOf(['gdp', 'sentiment', 'ismPmi']),
            rows: [
                { label: 'Real GDP Growth', value: '+' + m.gdp.toFixed(1) + '%', color: m.gdp > 2 ? '#10b981' : '#ef4444', sub: (m.gdp > 2 ? 'Healthy: above 2% · ' : 'Weak: below 2% · ') + 'A growing economy supports corporate profits. Below 2% signals a slowdown that can drag stocks lower.' },
                { label: 'Consumer Sentiment', value: m.sentiment.toFixed(1), color: m.sentiment > 70 ? '#10b981' : '#ef4444', sub: (m.sentiment > 70 ? 'Healthy: above 70 · ' : 'Weak: below 70 · ') + 'When people feel good about the economy, they spend more — and spending drives 70% of GDP.' },
                { label: 'ISM Manufacturing PMI', value: (m.ismPmi || 50).toFixed(1), color: (m.ismPmi || 50) >= 50 ? '#10b981' : '#ef4444', sub: ((m.ismPmi || 50) >= 50 ? 'Healthy: above 50 · ' : 'Contracting: below 50 · ') + 'The single best leading indicator of economic turns — above 50 means factories are expanding.' },
                { label: 'Regular Gas Price', value: '$' + (m.gasPrice || 0).toFixed(2), sub: 'Impacts daily budgets — high prices eat into consumer spending and corporate margins.' }
            ],
            desc: (function() {
                var gdpNote = m.gdp < 1 ? 'GDP at just ' + m.gdp.toFixed(1) + '% is flashing a slowdown warning — well below the 2% healthy threshold.' : m.gdp > 3 ? 'GDP at ' + m.gdp.toFixed(1) + '% signals strong expansion.' : 'GDP at ' + m.gdp.toFixed(1) + '% shows moderate growth.';
                var sentNote = m.sentiment < 60 ? ' Consumer sentiment at ' + m.sentiment.toFixed(0) + ' is deeply pessimistic — historically a contrarian buy signal when paired with strong fundamentals.' : '';
                var ismNote = (m.ismPmi || 50) < 50 ? ' ISM Manufacturing at ' + (m.ismPmi || 50).toFixed(1) + ' signals contraction — factories are pulling back.' : '';
                return gdpNote + sentNote + ismNote;
            })()
        },
        {
            title: 'The Dual Mandate',
            asOf: latestAsOf(['employment', 'joblessClaims', 'inflation']),
            rows: [
                { label: 'Unemployment Rate', value: m.employment.toFixed(1) + '%', color: m.employment < 5 ? '#10b981' : '#ef4444', sub: (m.employment < 5 ? 'Healthy: below 5% · ' : 'Elevated: above 5% · ') + 'Low unemployment means jobs and spending power — the engine of economic growth.' },
                { label: 'Initial Jobless Claims', value: (m.joblessClaims / 1000).toFixed(0) + 'K', sub: 'Weekly pulse of layoffs — rising claims are an early warning of economic trouble.' },
                { label: 'CPI Inflation', value: m.inflation.toFixed(1) + '%', color: m.inflation < 3 ? '#10b981' : '#ef4444', sub: (m.inflation < 3 ? 'Healthy: below 3% · ' : 'Elevated: above 3% · ') + 'Stable prices mean the Fed is less likely to raise rates and slow things down.' }
            ],
            desc: 'The Fed targets maximum employment and stable prices. Unemployment at ' + m.employment.toFixed(1) + '%' + (m.employment < 4.5 ? ' is healthy' : ' is rising') + ' and inflation at ' + m.inflation.toFixed(1) + '%' + (m.inflation < 3 ? ' is contained.' : ' remains elevated — watch for policy response.')
        },
        {
            title: 'Cost of Money & Policy',
            asOf: latestAsOf(['fedFunds', 'tenYear', 'twoYear', 'mortgage']),
            rows: [
                { label: 'Fed Funds Rate', value: m.fedFunds.toFixed(2) + '%', sub: 'The rate the Fed controls — higher rates cool the economy, lower rates stimulate it.' },
                { label: '10-Year Yield', value: m.tenYear.toFixed(2) + '%', sub: 'Benchmark for mortgages and corporate borrowing — affects the cost of everything.' },
                { label: '2-Year Yield', value: m.twoYear.toFixed(2) + '%', sub: 'Reflects where markets think the Fed is heading over the next two years.' },
                { label: 'Yield Curve (10Y-2Y)', value: (m.tenYear - m.twoYear > 0 ? '+' : '') + (m.tenYear - m.twoYear).toFixed(2) + '%', color: (m.tenYear - m.twoYear) >= 0 ? '#10b981' : '#ef4444', sub: ((m.tenYear - m.twoYear) >= 0 ? 'Normal (Positive) · ' : 'INVERTED · ') + 'An inverted curve has preceded every recession since the 1960s.' },
                { label: '30Y Mortgage Rate', value: m.mortgage.toFixed(2) + '%', color: m.mortgage < 6 ? '#10b981' : '#ef4444', sub: (m.mortgage < 6 ? 'Healthy: below 6% · ' : 'Elevated: above 6% · ') + 'Lower rates boost housing, consumer wealth, and the broader economy.' },
                { label: 'Monetary Policy', value: m.monetaryPolicy, sub: 'The Fed\\'s current stance on interest rates and money supply.' },
                { label: 'Fiscal Policy', value: m.fiscalPolicy, sub: 'Government spending and tax direction — supportive policy can cushion slowdowns.' }
            ],
            desc: (function() {
                var ycVal = m.tenYear - m.twoYear;
                var desc = ycVal < 0 ? 'Warning: Inverted yield curve at ' + ycVal.toFixed(2) + '% — historically precedes recessions by 12-18 months.' : 'A normal yield curve (+' + ycVal.toFixed(2) + '%) with ' + m.monetaryPolicy.toLowerCase() + ' monetary policy is supportive.';
                desc += m.mortgage >= 6.5 ? ' Mortgage rates at ' + m.mortgage.toFixed(2) + '% are a significant headwind for housing.' : '';
                return desc;
            })()
        },
        {
            title: 'Credit & Risk Signals',
            asOf: latestAsOf(['hySpread']),
            rows: [
                { label: 'High Yield Spread', value: m.hySpread.toFixed(2) + '%', color: m.hySpread < 4 ? '#10b981' : '#ef4444', sub: (m.hySpread < 4 ? 'Healthy: below 4% · ' : 'Stress: above 4% · ') + 'Tight spreads mean lenders are confident — companies can borrow cheaply to grow.' },
                { label: 'IG Spread', value: m.igSpread.toFixed(2) + '%', sub: 'Investment-grade bond risk premium — a widening spread signals growing corporate risk.' },
                { label: 'WTI Crude Oil', value: '$' + (m.oil || 0).toFixed(2), sub: ((m.oil || 0) > 90 ? 'High — pressures inflation and squeezes consumer budgets.' : 'Moderate — supports growth without fueling inflation.') },
                { label: 'US Dollar (DXY)', value: (m.dxy || 0).toFixed(1), sub: ((m.dxy || 0) > 105 ? 'Strong dollar — headwind for multinationals earning abroad.' : 'Moderate — balanced for global trade.') },
                { label: 'Geopolitical Risk', value: m.geopolitical, color: '#f59e0b', sub: 'Wars, tariffs, and trade tensions that can disrupt markets and supply chains.' }
            ],
            desc: 'HY spread at ' + m.hySpread.toFixed(2) + '%' + (m.hySpread < 3.5 ? ' is calm — perhaps too calm. Tight spreads mean risk may be underpriced.' : m.hySpread < 5 ? ' signals normal credit conditions.' : ' is widening — a stress signal worth watching closely.')
        }
    ];

    let html = '';
    cards.forEach(function(card) {
        html += '<div class="card"><div class="card-title">' + card.title + '</div>';
        if (card.asOf && card.asOf.length > 0) html += '<div style="font-size: 12px; color: #64748b; text-align: center; margin-top: -14px; margin-bottom: 12px;">Data as of ' + card.asOf + '</div>';
        card.rows.forEach(function(row) {
            var valStyle = row.color ? 'color:' + row.color + ';' : '';
            html += '<div style="padding: 10px 0; border-top: 1px solid #e2e8f0;">';
            html += '<div style="display: flex; justify-content: space-between; align-items: center;">';
            html += '<span class="metric-label">' + row.label + '</span>';
            html += '<span class="metric-value" style="' + valStyle + '">' + row.value + '</span>';
            html += '</div>';
            if (row.sub) html += '<div style="font-size: 14px; color: #64748b; margin-top: 4px; line-height: 1.5;">' + row.sub + '</div>';
            html += '</div>';
        });
        html += '<p style="font-size: 15px; color: #475569; margin-top: 12px; line-height: 1.6; border-top: 1px solid #e2e8f0; padding-top: 10px;">' + card.desc + '</p></div>';
    });

    return html;
}

function renderFundamentalsCards() {
    const f = MARKET.fundamental;
    const cards = [
        {
            title: 'Growth Engine',
            asOf: latestAsOf(['fundamentals']),
            rows: [
                { label: 'Sales Growth', value: '+' + f.salesGrowth.toFixed(1) + '%', color: f.salesGrowth > 3 ? '#10b981' : '#f59e0b', sub: (f.salesGrowth > 3 ? 'Healthy: above 3% · ' : 'Weak: below 3% · ') + 'Revenue is the top line — growing sales mean companies are selling more, the foundation of profit growth.' },
                { label: 'Earnings Growth', value: '+' + f.earningsGrowth.toFixed(1) + '%', color: f.earningsGrowth > 5 ? '#10b981' : '#ef4444', sub: (f.earningsGrowth > 5 ? 'Healthy: above 5% · ' : 'Weak: below 5% · ') + 'Companies making more money than last year — the fundamental driver of stock prices.' },
                { label: 'Earnings Beat Rate', value: f.earningsBeat + '%', color: f.earningsBeat > 70 ? '#10b981' : '#f59e0b', sub: (f.earningsBeat > 70 ? 'Healthy: above 70% · ' : 'Weak: below 70% · ') + 'How many companies exceeded analyst expectations — a gauge of corporate momentum.' },
                { label: 'Sales Beat Rate', value: f.salesBeat + '%', color: f.salesBeat > 60 ? '#10b981' : '#f59e0b', sub: (f.salesBeat > 60 ? 'Healthy: above 60% · ' : 'Weak: below 60% · ') + 'Revenue surprises show real demand, not just cost-cutting to beat estimates.' },
                { label: 'Analyst Revisions', value: f.revisions.toFixed(2) + 'x', color: f.revisions > 1 ? '#10b981' : '#ef4444', sub: (f.revisions > 1 ? 'Healthy: above 1.0x · ' : 'Negative: below 1.0x · ') + 'Whether analysts are raising or cutting estimates — tracks where the profit trend is heading.' }
            ],
            desc: 'Beat rates above 70% and rising revisions are bullish signals. Earnings growth at +' + f.earningsGrowth.toFixed(1) + '% with sales at +' + f.salesGrowth.toFixed(1) + '% shows ' + (f.earningsGrowth > f.salesGrowth ? 'expanding margins.' : 'revenue-driven growth.')
        },
        {
            title: 'Quality & Profitability',
            asOf: latestAsOf(['fundamentals']),
            rows: [
                { label: 'Net Margin', value: f.netMargin.toFixed(1) + '%', sub: (f.netMargin > 11 ? 'Healthy: above 11% · ' : 'Thin: below 11% · ') + 'How much companies keep from each dollar of revenue — a sign of pricing power.' },
                { label: 'Capex Spending', value: '+' + f.capex.toFixed(1) + '%', sub: 'Companies investing in future growth — a sign of confidence in the business outlook.' },
                { label: 'Shareholder Yield', value: (f.buybackYield + f.divYield).toFixed(1) + '%', color: '#10b981', sub: 'Total cash returned to shareholders through buybacks and dividends — fuel for stock prices.' },
                { label: 'Corporate Leverage', value: f.leverage.toFixed(1) + 'x', sub: (f.leverage < 2 ? 'Healthy: below 2.0x · ' : 'Elevated: above 2.0x · ') + 'How much debt companies carry relative to earnings — lower is safer.' }
            ],
            desc: 'High margins indicate pricing power. Shareholder yield of ' + (f.buybackYield + f.divYield).toFixed(1) + '% reflects strong capital returns. Leverage at ' + f.leverage.toFixed(1) + 'x is ' + (f.leverage < 2 ? 'healthy in any rate environment.' : 'worth monitoring as rates stay elevated.')
        },
        {
            title: 'Valuation',
            asOf: latestAsOf(['fundamentals']),
            rows: [
                { label: 'Forward P/E', value: f.forwardPE.toFixed(1) + 'x', color: f.forwardPE < 20 ? '#10b981' : '#ef4444', sub: (f.forwardPE < 20 ? 'Healthy: below 20x · ' : 'Elevated: above 20x · ') + 'How expensive stocks are relative to future earnings. Higher means less room for error.' },
                { label: '10yr Avg P/E', value: f.historicalPE.toFixed(1) + 'x', sub: 'Historical baseline — the average multiple investors have paid over the past decade.' },
                { label: 'PEG Ratio', value: f.pegRatio.toFixed(2), sub: (f.pegRatio < 1.5 ? 'Reasonable: below 1.5 · ' : 'Premium: above 1.5 · ') + 'Price relative to growth rate — under 1.5 suggests you\\'re not overpaying for growth.' }
            ],
            desc: 'At ' + f.forwardPE.toFixed(1) + 'x vs. the 10-year average of ' + f.historicalPE.toFixed(1) + 'x, markets are ' + (f.forwardPE > f.historicalPE ? 'pricing in continued growth — leaving less room for error.' : 'trading at a discount to historical norms.')
        }
    ];

    let html = '';
    cards.forEach(function(card) {
        html += '<div class="card"><div class="card-title">' + card.title + '</div>';
        if (card.asOf && card.asOf.length > 0) html += '<div style="font-size: 12px; color: #64748b; text-align: center; margin-top: -14px; margin-bottom: 12px;">Data as of ' + card.asOf + '</div>';
        card.rows.forEach(function(row) {
            var valStyle = row.color ? 'color:' + row.color + ';' : '';
            html += '<div style="padding: 10px 0; border-top: 1px solid #e2e8f0;">';
            html += '<div style="display: flex; justify-content: space-between; align-items: center;">';
            html += '<span class="metric-label">' + row.label + '</span>';
            html += '<span class="metric-value" style="' + valStyle + '">' + row.value + '</span>';
            html += '</div>';
            if (row.sub) html += '<div style="font-size: 14px; color: #64748b; margin-top: 4px; line-height: 1.5;">' + row.sub + '</div>';
            html += '</div>';
        });
        html += '<p style="font-size: 15px; color: #475569; margin-top: 12px; line-height: 1.6; border-top: 1px solid #e2e8f0; padding-top: 10px;">' + card.desc + '</p></div>';
    });

    return html;
}

function renderTechnicalsCards() {
    const t = MARKET.technical;
    const cards = [
        {
            title: 'Trend Structure',
            asOf: fmtAsOf((MARKET.dataAsOf || {}).prices || ''),
            rows: (function() {
                var pct4yr = t.sp500MA4yr > 0 ? ((t.sp500 / t.sp500MA4yr - 1) * 100).toFixed(1) : 0;
                var pct150 = t.sp500MA150 > 0 ? ((t.sp500 / t.sp500MA150 - 1) * 100).toFixed(1) : 0;
                var r3kPct = MARKET.breadth.r3kMA150 > 0 ? ((MARKET.breadth.r3kPrice / MARKET.breadth.r3kMA150 - 1) * 100).toFixed(1) : 0;
                return [
                    { label: 'S&P 500 vs 4-Year MA', value: (pct4yr > 0 ? '+' : '') + pct4yr + '%', color: t.sp500 > t.sp500MA4yr ? '#10b981' : '#ef4444', sub: 'S&P ' + t.sp500.toLocaleString() + ' vs MA ' + t.sp500MA4yr.toLocaleString() + ' · ' + (t.sp500 > t.sp500MA4yr ? 'Bull market intact — ' : 'Caution — ') + 'the 4-year MA tracks the full business cycle.' },
                    { label: 'S&P 500 vs 150-Day MA', value: (pct150 > 0 ? '+' : '') + pct150 + '%', color: t.sp500 > t.sp500MA150 ? '#10b981' : '#ef4444', sub: 'S&P ' + t.sp500.toLocaleString() + ' vs MA ' + t.sp500MA150.toLocaleString() + ' · ' + (t.sp500 > t.sp500MA150 ? 'Intermediate uptrend — ' : 'Intermediate downtrend — ') + 'the line in the sand for the medium-term direction.' },
                    { label: 'Russell 3000 vs 150-Day MA', value: (r3kPct > 0 ? '+' : '') + r3kPct + '%', color: MARKET.breadth.r3kPrice > MARKET.breadth.r3kMA150 ? '#10b981' : '#ef4444', sub: 'R3K ' + MARKET.breadth.r3kPrice.toLocaleString() + ' vs MA ' + MARKET.breadth.r3kMA150.toLocaleString() + ' · ' + (MARKET.breadth.r3kPrice > MARKET.breadth.r3kMA150 ? 'Broad market healthy — ' : 'Broad market weak — ') + '98% of the U.S. market in one number.' }
                ];
            })(),
            desc: (function() {
                var pct4yr = t.sp500MA4yr > 0 ? ((t.sp500 / t.sp500MA4yr - 1) * 100).toFixed(1) : 0;
                return t.sp500 > t.sp500MA4yr ? 'The S&P is +' + pct4yr + '% above its 4-year moving average — the long-term bull trend is intact. Historically, as long as price stays above this line, the business cycle is working in your favor.' : 'The S&P has slipped below its 4-year moving average — a signal that the long-term cycle may be turning. This has historically preceded extended periods of weakness.';
            })()
        },
        {
            title: 'Breadth & Participation',
            asOf: fmtAsOf((MARKET.dataAsOf || {}).prices || ''),
            rows: [
                { label: 'Breadth (% > 150d MA)', value: Math.round(MARKET.breadth.pctAbove) + '%', color: MARKET.breadth.pctAbove >= 60 ? '#10b981' : MARKET.breadth.pctAbove >= 40 ? '#f59e0b' : '#ef4444', sub: (MARKET.breadth.pctAbove >= 60 ? 'Healthy: above 60% · ' : 'Narrow: below 60% · ') + 'How many stocks are participating — broad is healthy, narrow is fragile.' },
                { label: 'Russell 3000 Price', value: MARKET.breadth.r3kPrice.toFixed(2), sub: 'Broad market index covering 3,000 stocks — the most complete view of U.S. equities.' },
                { label: 'Russell 3000 150d MA', value: MARKET.breadth.r3kMA150.toFixed(2), sub: 'The intermediate trend line — price above = healthy, below = caution.' }
            ],
            desc: 'Breadth ' + (MARKET.breadth.pctAbove < 60 ? 'below 60% means the rally is narrow — fewer stocks are participating. Watch for improvement above 60% to confirm broad-based strength.' : 'above 60% signals broad participation — a healthy market where many stocks are contributing to the move.')
        },
        {
            title: 'Sentiment, Volatility & Oversold Signals',
            asOf: latestAsOf(['putCall', 'aaii']),
            rows: (function() {
                var rows = [
                    { label: 'VIX Index', value: t.vix.toFixed(2), color: t.vix >= 30 ? '#ef4444' : t.vix < 20 ? '#10b981' : '#f59e0b', sub: t.vix >= 30 ? '⚠ OVERSOLD SIGNAL (>30)' : (t.vix < 20 ? t.vix.toFixed(1) + ' · Healthy: below 20 · Calm markets, low uncertainty.' : t.vix.toFixed(1) + ' · Elevated: 20-30 · Fear is present but not extreme — watch for resolution.'), signal: t.vix >= 30 },
                    { label: 'Put/Call Ratio', value: t.putCall.toFixed(2), color: t.putCall >= 1.2 ? '#ef4444' : t.putCall < 1 ? '#10b981' : '#f59e0b', sub: t.putCall >= 1.2 ? '⚠ OVERSOLD SIGNAL (>1.2)' : (t.putCall < 1 ? 'Healthy: below 1.0 · More calls than puts — traders are positioned for upside.' : 'Hedging elevated · Traders are buying more protection than usual.'), signal: t.putCall >= 1.2 }
                ];
                if (t.pctAbove20sma !== null && t.pctAbove20sma !== undefined) {
                    rows.push({ label: 'Breadth Washout (% > 20d SMA)', value: Math.round(t.pctAbove20sma) + '%', color: t.pctAbove20sma < 20 ? '#ef4444' : t.pctAbove20sma < 40 ? '#f59e0b' : '#10b981', sub: t.pctAbove20sma < 20 ? '⚠ OVERSOLD SIGNAL (<20%)' : (t.pctAbove20sma >= 40 ? 'Normal · Stocks riding above their short-term averages.' : 'Weak · More stocks slipping below their 20-day averages — deteriorating internals.'), signal: t.pctAbove20sma < 20 });
                }
                if (t.pctAt20dayLows !== null && t.pctAt20dayLows !== undefined) {
                    rows.push({ label: 'New Lows Spike (% at 20d Low)', value: Math.round(t.pctAt20dayLows) + '%', color: t.pctAt20dayLows >= 50 ? '#ef4444' : t.pctAt20dayLows >= 30 ? '#f59e0b' : '#10b981', sub: t.pctAt20dayLows >= 50 ? '⚠ OVERSOLD SIGNAL (>50%)' : (t.pctAt20dayLows < 30 ? 'Normal · Few stocks making new lows.' : 'Rising · More stocks hitting 20-day lows — selling pressure building.'), signal: t.pctAt20dayLows >= 50 });
                }
                rows.push({ label: 'AAII Bulls', value: t.aaii.toFixed(1) + '%', color: t.aaii > 40 ? '#10b981' : '#f59e0b', sub: t.aaii > 40 ? 'Optimistic · Individual investors are confident — can be a contrarian warning at extremes.' : 'Cautious · Low bullishness is often a contrarian buy signal — when the crowd is fearful, opportunity may be near.' });
                return rows;
            })(),
            desc: (function() {
                var signals = [];
                if (t.vix >= 30) signals.push('VIX above 30 (panic)');
                if (t.putCall >= 1.2) signals.push('Put/Call above 1.2 (extreme fear)');
                if (t.pctAbove20sma !== null && t.pctAbove20sma < 20) signals.push('Breadth Washout (only ' + t.pctAbove20sma.toFixed(1) + '% above 20d SMA)');
                if (t.pctAt20dayLows !== null && t.pctAt20dayLows >= 50) signals.push('New Lows Spike (' + t.pctAt20dayLows.toFixed(1) + '% at 20d lows)');
                if (signals.length > 0) {
                    return '🔴 ' + signals.length + ' oversold signal' + (signals.length > 1 ? 's' : '') + ' firing: ' + signals.join(', ') + '. Historically, oversold signals mark capitulation zones where sellers are exhausted — often preceding rebounds.';
                }
                return 'No oversold signals firing. VIX at ' + t.vix.toFixed(1) + (t.vix > 20 ? ' is elevated but below the 30 panic threshold.' : ' reflects calm conditions.') + ' Put/Call at ' + t.putCall.toFixed(2) + (t.putCall < 1 ? ' shows bullish positioning.' : ' shows hedging activity.');
            })()
        }
    ];

    let html = '';
    cards.forEach(function(card) {
        html += '<div class="card"><div class="card-title">' + card.title + '</div>';
        if (card.asOf && card.asOf.length > 0) html += '<div style="font-size: 12px; color: #64748b; text-align: center; margin-top: -14px; margin-bottom: 12px;">Data as of ' + card.asOf + '</div>';
        card.rows.forEach(function(row) {
            var valStyle = row.color ? 'color:' + row.color + ';' : '';
            var rowBg = row.signal ? 'background: #fef2f2; border-left: 3px solid #ef4444; padding-left: 8px; border-radius: 4px; margin: 2px 0;' : '';
            html += '<div style="padding: 10px 0; border-top: 1px solid #e2e8f0; ' + rowBg + '">';
            html += '<div style="display: flex; justify-content: space-between; align-items: center;">';
            html += '<span class="metric-label">' + row.label + '</span>';
            html += '<span class="metric-value" style="' + valStyle + '">' + row.value + '</span>';
            html += '</div>';
            if (row.sub) {
                var subColor = row.signal ? '#ef4444' : '#64748b';
                var subWeight = row.signal ? 'font-weight:600;' : '';
                html += '<div style="font-size: 13px; color:' + subColor + '; margin-top: 4px; line-height: 1.4;' + subWeight + '">' + row.sub + '</div>';
            }
            html += '</div>';
        });
        html += '<p style="font-size: 15px; color: #475569; margin-top: 12px; line-height: 1.6; border-top: 1px solid #e2e8f0; padding-top: 10px;">' + card.desc + '</p></div>';
    });

    return html;
}

function renderHistoricalContext() {
    var t = MARKET.technical;
    var pctFrom4yr = t.sp500MA4yr > 0 ? ((t.sp500 / t.sp500MA4yr - 1) * 100).toFixed(1) : 0;
    var pctFrom150 = t.sp500MA150 > 0 ? ((t.sp500 / t.sp500MA150 - 1) * 100).toFixed(1) : 0;
    var totalPullbacks = PULLBACK_STATS.total || 62;
    var startPrice = PULLBACK_STATS.start_price || 44;
    var endPrice = PULLBACK_STATS.end_price || t.sp500;

    // Helper to format duration
    function formatDuration(days) {
        if (!days) return '—';
        var months = Math.round(days / 21);
        if (months < 1) return Math.round(days / 5) + ' weeks';
        return months + ' months';
    }

    // Tier data
    var tiers = PULLBACK_STATS.tiers || {};
    var routineTier = tiers.routine || { count: 39, pct: 62.9, median_duration_days: 19 };
    var meaningfulTier = tiers.meaningful || { count: 8, pct: 12.9, median_duration_days: 111 };
    var beyondTier = tiers.beyond_normal || { count: 4, pct: 6.5, median_duration_days: 130 };
    var bearTier = tiers.bear || { count: 11, pct: 17.7, median_duration_days: 295 };
    var routineDur = routineTier.median_duration_days || 19;
    var meaningfulDur = Math.max(meaningfulTier.median_duration_days || 111, routineDur);
    var beyondDur = Math.max(beyondTier.median_duration_days || 130, meaningfulDur);
    var bearDur = Math.max(bearTier.median_duration_days || 295, beyondDur);

    var html = '<div class="card"><div class="card-title">Market Trend Analysis</div>';

    // ═══ SECULAR TREND — THE BIG PICTURE ═══
    var secularGain = Math.round((t.sp500 / 1810 - 1) * 100);
    var secularYears = new Date().getFullYear() - 2016;

    // Banner
    html += '<div style="background: linear-gradient(135deg, #0f172a, #1e293b); border-radius: 12px; padding: 24px; color: white; margin-bottom: 24px;">';
    html += '<div style="font-size: 12px; text-transform: uppercase; letter-spacing: 1.5px; color: #10b981; font-weight: 700; margin-bottom: 8px;">Secular Trend</div>';
    html += '<div style="font-family: Fraunces, serif; font-size: 22px; font-weight: 700; margin-bottom: 10px;">3rd Generational Bull Market Since 1957</div>';
    html += '<p style="font-size: 14px; color: #cbd5e1; line-height: 1.7; margin-bottom: 16px;">The S&P 500 has moved through generational cycles of expansion and contraction lasting roughly 16-18 years each. We are currently in the third secular bull market since 1957 — a period where the long-term trend favors being invested and cyclical pullbacks are buying opportunities, not the beginning of the end.</p>';

    // Secular stats
    html += '<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 12px; margin-bottom: 16px;">';
    html += '<div style="text-align:center;"><div style="font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Started</div><div style="font-family: JetBrains Mono, monospace; font-size: 20px; font-weight: 700; color: white;">2016</div></div>';
    html += '<div style="text-align:center;"><div style="font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">S&P 500 Then</div><div style="font-family: JetBrains Mono, monospace; font-size: 20px; font-weight: 700; color: white;">1,810</div></div>';
    html += '<div style="text-align:center;"><div style="font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">S&P 500 Now</div><div style="font-family: JetBrains Mono, monospace; font-size: 20px; font-weight: 700; color: #10b981;">' + t.sp500.toLocaleString(undefined, {maximumFractionDigits:0}) + '</div></div>';
    html += '<div style="text-align:center;"><div style="font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Gain</div><div style="font-family: JetBrains Mono, monospace; font-size: 20px; font-weight: 700; color: #10b981;">+' + secularGain + '%</div></div>';
    html += '</div>';

    html += '<p style="font-size: 14px; color: #94a3b8; line-height: 1.7;">If history rhymes, this cycle could last into the <strong style="color:white;">early-mid 2030s</strong> and take the S&P towards <strong style="color:#10b981;">15,000</strong>. The 4-year moving average (currently ' + t.sp500MA4yr.toLocaleString(undefined, {maximumFractionDigits:0}) + ') serves as the structural dividing line — a sustained break below it would signal the secular trend is turning negative.</p>';
    html += '</div>';

    // Secular history table
    html += '<div style="margin-bottom: 24px;">';
    html += '<div style="font-family: Fraunces, serif; font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 6px;">Secular Cycles Since 1957</div>';
    html += '<p style="font-size: 13px; color: #64748b; margin-bottom: 12px;">The market has alternated between generational bull and bear markets, each lasting roughly 16-18 years and driven by major economic forces.</p>';

    html += '<table class="stock-table" style="font-size: 13px;"><thead><tr><th style="text-align:left;">Period</th><th style="text-align:left;">Type</th><th style="text-align:right;">S&P Start</th><th style="text-align:right;">S&P End</th><th style="text-align:right;">Return</th><th style="text-align:left;">What Drove It</th></tr></thead><tbody>';
    html += '<tr style="background:#f0fdf4;"><td style="font-weight:600;">1957 – 1966</td><td><span class="badge badge-green">Secular Bull</span></td><td style="text-align:right;">44</td><td style="text-align:right;">94</td><td style="text-align:right;color:#10b981;font-weight:600;">+114%</td><td style="font-size:12px;color:#475569;">Post-war industrial boom, baby boom consumer spending, space race, rising middle class</td></tr>';
    html += '<tr style="background:#fef2f2;"><td style="font-weight:600;">1966 – 1982</td><td><span class="badge badge-red">Secular Bear</span></td><td style="text-align:right;">94</td><td style="text-align:right;">102</td><td style="text-align:right;color:#ef4444;font-weight:600;">+9%</td><td style="font-size:12px;color:#475569;">Runaway inflation, oil shocks, Vietnam, Watergate, Volcker raising rates to 20% to kill inflation</td></tr>';
    html += '<tr style="background:#f0fdf4;"><td style="font-weight:600;">1982 – 2000</td><td><span class="badge badge-green">Secular Bull</span></td><td style="text-align:right;">102</td><td style="text-align:right;">1,527</td><td style="text-align:right;color:#10b981;font-weight:600;">+1,397%</td><td style="font-size:12px;color:#475569;">Inflation conquered, Reagan tax reform, tech revolution, internet boom, globalization</td></tr>';
    html += '<tr style="background:#fef2f2;"><td style="font-weight:600;">2000 – 2016</td><td><span class="badge badge-red">Secular Bear</span></td><td style="text-align:right;">1,527</td><td style="text-align:right;">1,810</td><td style="text-align:right;color:#ef4444;font-weight:600;">+19%</td><td style="font-size:12px;color:#475569;">Dot-com bust, 9/11, financial crisis, slow recovery, two 50%+ crashes in a decade</td></tr>';
    html += '<tr style="background:#f0fdf4;border-left:3px solid #10b981;"><td style="font-weight:700;">2016 – Present</td><td><span class="badge badge-green">Secular Bull</span></td><td style="text-align:right;">1,810</td><td style="text-align:right;font-weight:700;">' + t.sp500.toLocaleString(undefined, {maximumFractionDigits:0}) + '</td><td style="text-align:right;color:#10b981;font-weight:700;">+' + secularGain + '%</td><td style="font-size:12px;color:#475569;">AI revolution, cloud computing, fiscal stimulus, post-COVID rebound, Mag 7 tech leadership</td></tr>';
    html += '</tbody></table>';

    html += '<div style="margin-top: 12px; padding: 12px 16px; background: #f0fdf4; border-radius: 8px; border-left: 3px solid #10b981;">';
    html += '<div style="font-size: 14px; color: #166534; line-height: 1.6;"><strong>Key takeaway:</strong> During secular bull markets, corrections are buying opportunities. During secular bear markets, rallies are selling opportunities. Knowing which regime you are in changes everything about how you invest. The 4-year moving average is the line in the sand.</div>';
    html += '</div>';
    html += '</div>';

    // ═══ 4-YEAR CYCLE TABLE ═══
    html += '<div style="margin-bottom: 28px;">';
    html += '<div style="font-family: Fraunces, serif; font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 6px;">The 4-Year Cycle</div>';
    html += '<p style="font-size: 13px; color: #64748b; margin-bottom: 12px;">Within secular bull markets, a predictable 3-4 year cycle develops — driven by central bank liquidity and economic growth. A cycle low forms roughly every 4 years near the 4-year moving average, followed by a rally averaging +111%. This table shows every cycle during secular bull markets since 1957.</p>';

    // Current cycle stats (auto-calculated)
    var cycleStartPrice = 3577; // Oct 2022 low
    var cycleGain = Math.round((t.sp500 / cycleStartPrice - 1) * 100);
    var cycleMonths = Math.round((new Date() - new Date('2022-10-12')) / (1000 * 60 * 60 * 24 * 30));

    html += '<table class="stock-table" style="font-size: 13px; margin-bottom: 12px;"><thead><tr><th style="text-align:left;">4-Year Cycle</th><th style="text-align:left;">Secular Period</th><th style="text-align:right;">% Rally</th><th style="text-align:right;">% Correction</th><th style="text-align:right;">Duration</th></tr></thead><tbody>';
    // Secular Bull #1 (1957-1966)
    html += '<tr><td>1957 – 1962</td><td style="color:#10b981;">Bull #1</td><td style="text-align:right;color:#10b981;font-weight:600;">+86%</td><td style="text-align:right;color:#ef4444;">-28%</td><td style="text-align:right;">5 yrs</td></tr>';
    html += '<tr><td>1962 – 1966</td><td style="color:#10b981;">Bull #1</td><td style="text-align:right;color:#10b981;font-weight:600;">+80%</td><td style="text-align:right;color:#ef4444;">-22%</td><td style="text-align:right;">4 yrs</td></tr>';
    // Secular Bull #2 (1982-2000)
    html += '<tr><td>1982 – 1987</td><td style="color:#10b981;">Bull #2</td><td style="text-align:right;color:#10b981;font-weight:600;">+231%</td><td style="text-align:right;color:#ef4444;">-36%</td><td style="text-align:right;">5 yrs</td></tr>';
    html += '<tr><td>1987 – 1990</td><td style="color:#10b981;">Bull #2</td><td style="text-align:right;color:#10b981;font-weight:600;">+71%</td><td style="text-align:right;color:#ef4444;">-20%</td><td style="text-align:right;">3 yrs</td></tr>';
    html += '<tr><td>1990 – 1994</td><td style="color:#10b981;">Bull #2</td><td style="text-align:right;color:#10b981;font-weight:600;">+64%</td><td style="text-align:right;color:#ef4444;">-10%</td><td style="text-align:right;">4 yrs</td></tr>';
    html += '<tr><td>1994 – 1998</td><td style="color:#10b981;">Bull #2</td><td style="text-align:right;color:#10b981;font-weight:600;">+173%</td><td style="text-align:right;color:#ef4444;">-22%</td><td style="text-align:right;">4 yrs</td></tr>';
    // Secular Bull #3 (2016-Present)
    html += '<tr><td>2016 – 2020</td><td style="color:#10b981;">Bull #3</td><td style="text-align:right;color:#10b981;font-weight:600;">+87%</td><td style="text-align:right;color:#ef4444;">-38%</td><td style="text-align:right;">4 yrs</td></tr>';
    html += '<tr><td>2020 – 2022</td><td style="color:#10b981;">Bull #3</td><td style="text-align:right;color:#10b981;font-weight:600;">+120%</td><td style="text-align:right;color:#ef4444;">-27%</td><td style="text-align:right;">2 yrs</td></tr>';
    // Current cycle (auto-updating)
    html += '<tr style="background:#f0fdf4;border-left:3px solid #10b981;"><td style="font-weight:700;">2022 – Present</td><td style="color:#10b981;font-weight:600;">Bull #3</td><td style="text-align:right;color:#10b981;font-weight:700;">+' + cycleGain + '%</td><td style="text-align:right;color:#64748b;">?</td><td style="text-align:right;font-weight:600;">' + cycleMonths + ' mo</td></tr>';
    // Averages
    html += '<tr style="background:#f8fafc;font-weight:700;"><td>Average</td><td></td><td style="text-align:right;color:#10b981;">+111%</td><td style="text-align:right;color:#ef4444;">-23%</td><td style="text-align:right;">~4 yrs</td></tr>';
    html += '</tbody></table>';

    html += '<div style="padding: 12px 16px; background: #fffbeb; border-radius: 8px; border-left: 3px solid #f59e0b;">';
    html += '<div style="font-size: 14px; color: #92400e; line-height: 1.6;"><strong>Where are we in the cycle?</strong> The current 4-year cycle is up <strong>+' + cycleGain + '%</strong> over <strong>' + cycleMonths + ' months</strong> from the October 2022 low. The historical average cycle rally is +111% before a correction averaging -23% develops. With the cycle 3+ years old and gains near the historical average, the risk of a cyclical pullback is elevated — but within a secular bull market, pullbacks are opportunities, not exits.</div>';
    html += '</div>';
    html += '</div>';

    // ═══ SECTION 1: WHERE ARE WE NOW ═══
    html += '<div style="margin-bottom: 28px; padding-top: 24px; border-top: 2px solid #e2e8f0;">';
    html += '<div style="font-family: Fraunces, serif; font-size: 22px; font-weight: 700; color: #0f172a; margin-bottom: 16px;">Where Are We Now</div>';

    // Current bull market highlight
    var bullGain = Math.round((t.sp500 / 3577 - 1) * 100);
    var bullStartDate = 'October 2022';
    var bullMonths = Math.round((new Date() - new Date('2022-10-12')) / (1000 * 60 * 60 * 24 * 30));

    html += '<div style="padding: 20px; background: linear-gradient(135deg, #0f172a, #1e293b); border-radius: 12px; margin-bottom: 20px; color: white;">';
    html += '<div style="font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #10b981; font-weight: 600; margin-bottom: 8px;">Current Bull Market</div>';
    html += '<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 16px;">';
    html += '<div><div style="font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Since</div><div style="font-family: JetBrains Mono, monospace; font-size: 20px; font-weight: 700; color: white;">' + bullStartDate + '</div></div>';
    html += '<div><div style="font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">S&P 500</div><div style="font-family: JetBrains Mono, monospace; font-size: 20px; font-weight: 700; color: #10b981;">' + t.sp500.toLocaleString(undefined, {maximumFractionDigits:0}) + '</div></div>';
    html += '<div><div style="font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Gain</div><div style="font-family: JetBrains Mono, monospace; font-size: 20px; font-weight: 700; color: #10b981;">+' + bullGain + '%</div></div>';
    html += '<div><div style="font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Duration</div><div style="font-family: JetBrains Mono, monospace; font-size: 20px; font-weight: 700; color: white;">' + bullMonths + ' months</div></div>';
    html += '</div></div>';

    // Current position narrative
    var cp = PULLBACK_STATS.current_pullback || null;
    var breadthContext = MARKET.breadth.pctAbove >= 60 ? 'Breadth is healthy with broad participation.' : MARKET.breadth.pctAbove >= 40 ? 'Breadth is narrowing — fewer stocks are participating.' : 'Breadth is weak — the market is being carried by a narrow group of leaders.';

    html += '<div style="font-size: 15px; color: #64748b; line-height: 1.8;">';

    if (cp) {
        var cpMag = cp.magnitude || 0;
        var cpDays = cp.duration || 0;
        var cpWeeks = Math.round(cpDays / 5);
        var cpTier = cpMag > -10 ? 'routine' : cpMag > -15 ? 'meaningful' : cpMag > -20 ? 'beyond normal' : 'bear market';
        var peakPrice = cp.peak_price || 0;
        var peakDate = cp.peak_date || cp.start_date || '';
        var peakDateFormatted = peakDate ? new Date(peakDate + 'T00:00:00').toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) : '';

        // Current gap from peak (different from max drawdown)
        var currentGapPct = peakPrice > 0 ? ((t.sp500 / peakPrice - 1) * 100) : 0;
        var gapColor = currentGapPct < -10 ? '#ef4444' : currentGapPct < -5 ? '#f59e0b' : '#10b981';

        html += 'The S&P 500 is currently at <strong style="color: #0f172a;">' + t.sp500.toLocaleString(undefined, {minimumFractionDigits:0, maximumFractionDigits:0}) + '</strong>, <strong style="color: ' + gapColor + ';">' + currentGapPct.toFixed(1) + '%</strong> from its recent peak';
        if (peakPrice > 0) html += ' of ' + peakPrice.toLocaleString(undefined, {minimumFractionDigits:0, maximumFractionDigits:0});
        if (peakDateFormatted) html += ' reached on ' + peakDateFormatted;
        html += '. ';

        if (t.sp500 > t.sp500MA4yr) {
            html += 'The long-term trend remains intact — price is still ' + ((t.sp500 / t.sp500MA4yr - 1) * 100).toFixed(0) + '% above the 4-year moving average. ';
        } else {
            html += 'The long-term trend is being tested — price has dropped below the 4-year moving average. ';
        }

        var tierColor = cpMag < -20 ? '#ef4444' : cpMag < -15 ? '#f97316' : cpMag < -10 ? '#f59e0b' : '#10b981';
        html += '</div>';
        html += '<div style="margin: 16px 0; padding: 16px 20px; background: linear-gradient(135deg, #fffbeb, #fef3c7); border-radius: 10px; border-left: 4px solid ' + tierColor + ';">';
        html += '<strong style="color: ' + tierColor + '; font-size: 16px;">Active Pullback Episode:</strong> ';
        html += '<span style="color: #334155; font-size: 15px;">Max drawdown of <strong>' + cpMag + '%</strong> over <strong>' + cpDays + ' trading days</strong> (' + cpWeeks + ' weeks) — categorized as <strong style="color: ' + tierColor + ';">' + cpTier + '</strong>. Still open because the S&P has not made a new high above ' + peakPrice.toLocaleString(undefined, {minimumFractionDigits:0, maximumFractionDigits:0}) + ' yet.</span>';
        html += '</div>';
        html += '<div style="font-size: 15px; color: #64748b; line-height: 1.8;">';
    } else {
        var athPrice = 0, athIdx = 0;
        for (var i = 0; i < SP500_PRICES.length; i++) { if (SP500_PRICES[i] > athPrice) { athPrice = SP500_PRICES[i]; athIdx = i; } }
        var athDate = SP500_DATES[athIdx] || '';
        var drawdownPct = athPrice > 0 ? ((t.sp500 / athPrice - 1) * 100).toFixed(1) : 0;
        if (Math.abs(drawdownPct) < 1) {
            html += 'The S&P 500 is near its all-time high. ';
        } else {
            html += 'The S&P 500 is ' + drawdownPct + '% from its high. ';
        }
        html += t.sp500 > t.sp500MA4yr ? 'The long-term trend is up — price is ' + pctFrom4yr + '% above the 4-year moving average. ' : 'The long-term trend is being tested. ';
    }

    html += breadthContext + ' ';
    html += 'VIX at ' + t.vix.toFixed(1) + ' — ' + (t.vix >= 30 ? 'extreme fear, historically a contrarian buy zone.' : t.vix > 20 ? 'elevated but not at panic levels.' : 'calm conditions.') + ' ';
    html += '</div>';
    html += '</div>';

    // ═══ SECTION 2: THE CLIMB IS ALWAYS LONGER THAN THE SLIDE ═══
    html += '<div style="padding: 24px 0; border-top: 2px solid #e2e8f0;">';
    html += '<div style="font-family: Fraunces, serif; font-size: 22px; font-weight: 700; color: #0f172a; margin-bottom: 6px;">The Climb Is Always Longer Than the Slide</div>';
    html += '<p style="font-size: 14px; color: #64748b; margin-bottom: 16px;">Since 1957, the S&P 500 has grown from ' + Math.round(startPrice) + ' to ' + Math.round(endPrice).toLocaleString() + '. Along the way, it stumbled ' + totalPullbacks + ' times — and came back every single time.</p>';

    html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">';
    html += '<div style="padding: 20px; background: linear-gradient(135deg, #f0fdf4, #ecfdf5); border-radius: 12px; border-left: 4px solid #10b981;">';
    html += '<div style="font-family: Fraunces, serif; font-size: 18px; font-weight: 700; color: #10b981; margin-bottom: 12px;">11 Bull Markets</div>';
    html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">';
    html += '<div><div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b;">Median Gain</div><div style="font-family: JetBrains Mono, monospace; font-size: 24px; font-weight: 700; color: #10b981;">+107%</div></div>';
    html += '<div><div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b;">Median Duration</div><div style="font-family: JetBrains Mono, monospace; font-size: 24px; font-weight: 700; color: #0f172a;">50 mo</div></div>';
    html += '</div></div>';

    html += '<div style="padding: 20px; background: linear-gradient(135deg, #fef2f2, #fee2e2); border-radius: 12px; border-left: 4px solid #ef4444;">';
    html += '<div style="font-family: Fraunces, serif; font-size: 18px; font-weight: 700; color: #ef4444; margin-bottom: 12px;">' + (bearTier.count || 11) + ' Bear Markets</div>';
    html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">';
    html += '<div><div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b;">Median Decline</div><div style="font-family: JetBrains Mono, monospace; font-size: 24px; font-weight: 700; color: #ef4444;">-33%</div></div>';
    html += '<div><div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b;">Median Duration</div><div style="font-family: JetBrains Mono, monospace; font-size: 24px; font-weight: 700; color: #0f172a;">' + formatDuration(bearDur) + '</div></div>';
    html += '</div></div>';
    html += '</div>';

    html += '<p style="font-size: 15px; color: #475569; line-height: 1.6;">Bull markets are roughly 4x longer and deliver 3x the magnitude of bear markets. The math overwhelmingly favors staying invested. See Sources &amp; Definitions for the full list.</p>';
    html += '</div>';

    // ═══ SECTION 3: PULLBACKS ARE NORMAL ═══
    html += '<div style="padding: 24px 0; border-top: 2px solid #e2e8f0;">';
    html += '<div style="font-family: Fraunces, serif; font-size: 22px; font-weight: 700; color: #0f172a; margin-bottom: 16px;">Pullbacks Are Normal</div>';
    var frequency = PULLBACK_STATS.frequency || 0.9;
    var medianMag = PULLBACK_STATS.median_magnitude || -8.5;
    var routinePctStat = routineTier.pct || 63;
    var bearPctStat = bearTier.pct || 18;
    var neverReach20 = Math.round(100 - bearPctStat);
    var freqLabel = frequency >= 1.5 ? Math.round(frequency) + 'x per year' : frequency >= 0.75 ? '~1 per year' : 'Every ' + Math.round(1 / frequency) + ' years';

    html += '<div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-bottom: 20px;">';
    html += '<div style="text-align: center; padding: 18px 12px; background: #f0fdf4; border-radius: 10px;"><div style="font-family: JetBrains Mono, monospace; font-size: 28px; font-weight: 700; color: #10b981;">' + totalPullbacks + '</div><div style="font-size: 12px; font-weight: 600; color: #475569; margin-top: 4px;">5%+ Pullbacks</div></div>';
    html += '<div style="text-align: center; padding: 18px 12px; background: #fffbeb; border-radius: 10px;"><div style="font-family: JetBrains Mono, monospace; font-size: 22px; font-weight: 700; color: #f59e0b;">' + freqLabel + '</div><div style="font-size: 12px; font-weight: 600; color: #475569; margin-top: 4px;">Frequency</div></div>';
    html += '<div style="text-align: center; padding: 18px 12px; background: #f0f9ff; border-radius: 10px;"><div style="font-family: JetBrains Mono, monospace; font-size: 28px; font-weight: 700; color: #3b82f6;">' + medianMag + '%</div><div style="font-size: 12px; font-weight: 600; color: #475569; margin-top: 4px;">Median Decline</div></div>';
    html += '<div style="text-align: center; padding: 18px 12px; background: #f0fdf4; border-radius: 10px;"><div style="font-family: JetBrains Mono, monospace; font-size: 28px; font-weight: 700; color: #10b981;">' + Math.round(routinePctStat) + '%</div><div style="font-size: 12px; font-weight: 600; color: #475569; margin-top: 4px;">Never Reach -10%</div></div>';
    html += '<div style="text-align: center; padding: 18px 12px; background: #f0fdf4; border-radius: 10px;"><div style="font-family: JetBrains Mono, monospace; font-size: 28px; font-weight: 700; color: #10b981;">' + neverReach20 + '%</div><div style="font-size: 12px; font-weight: 600; color: #475569; margin-top: 4px;">Never Reach -20%</div></div>';
    html += '</div>';
    html += '</div>';

    // ═══ SECTION 4: NOT EVERY SLIP IS THE SAME ═══
    html += '<div style="padding: 24px 0; border-top: 2px solid #e2e8f0;">';
    html += '<div style="font-family: Fraunces, serif; font-size: 22px; font-weight: 700; color: #0f172a; margin-bottom: 6px;">Not Every Slip Is the Same</div>';
    html += '<p style="font-size: 14px; color: #64748b; margin-bottom: 16px;">Of the ' + totalPullbacks + ' pullbacks since 1957, here is how they break down by severity:</p>';
    html += '<table class="stock-table" style="font-size: 14px; margin-bottom: 10px;"><thead><tr><th>Severity</th><th>Decline</th><th>Count</th><th>Typical Duration</th><th>What It Feels Like</th></tr></thead><tbody>';
    html += '<tr><td style="color: #10b981; font-weight: 600;">Routine</td><td>5-10%</td><td>' + routineTier.count + ' (' + routineTier.pct.toFixed(0) + '%)</td><td>' + formatDuration(routineDur) + '</td><td>A stumble on the trail — over before most notice</td></tr>';
    html += '<tr><td style="color: #f59e0b; font-weight: 600;">Meaningful</td><td>10-15%</td><td>' + meaningfulTier.count + ' (' + meaningfulTier.pct.toFixed(0) + '%)</td><td>' + formatDuration(meaningfulDur) + '</td><td>You feel it — headlines get louder, but it passes</td></tr>';
    html += '<tr><td style="color: #f97316; font-weight: 600;">Beyond Normal</td><td>15-20%</td><td>' + beyondTier.count + ' (' + beyondTier.pct.toFixed(0) + '%)</td><td>' + formatDuration(beyondDur) + '</td><td>Real fear — but technically not a bear market</td></tr>';
    html += '<tr><td style="color: #ef4444; font-weight: 600;">Bear Market</td><td>20%+</td><td>' + bearTier.count + ' (' + bearTier.pct.toFixed(0) + '%)</td><td>' + formatDuration(bearDur) + '</td><td>Deep valley — painful but historically temporary</td></tr>';
    html += '</tbody></table>';
    html += '</div>';

    // Closing quote
    html += '<div style="margin-top: 8px; padding: 16px 20px; background: linear-gradient(135deg, #0f172a, #1e293b); border-radius: 10px;">';
    html += '<div style="font-size: 15px; color: #e2e8f0; line-height: 1.6; font-style: italic; text-align: center;">"The market has stumbled ' + totalPullbacks + ' times since 1957 and has always come back. The next pullback is not a surprise — it is the price of admission to the greatest wealth-building machine in history."</div>';
    html += '</div>';

    html += '</div>';

    return html;
}

function drawSP500Chart() {
    const container = document.getElementById('sp500Chart');
    if (!container) return;

    const prices = SP500_PRICES;
    const dates = SP500_DATES;
    const w = container.offsetWidth;
    const h = container.offsetHeight || 320;
    const padLeft = 55;
    const padRight = 15;
    const padTop = 30;
    const padBottom = 30;

    if (prices.length < 2) return;

    // Safe min/max for large arrays (avoid stack overflow with spread)
    var minPrice = prices[0], maxPrice = prices[0];
    for (var k = 1; k < prices.length; k++) {
        if (prices[k] < minPrice) minPrice = prices[k];
        if (prices[k] > maxPrice) maxPrice = prices[k];
    }
    var range = maxPrice - minPrice || 1;
    // Add 2% padding
    minPrice = minPrice - range * 0.02;
    maxPrice = maxPrice + range * 0.02;
    range = maxPrice - minPrice;

    const chartW = w - padLeft - padRight;
    const chartH = h - padTop - padBottom;

    // Calculate 150-day moving average
    let ma150 = [];
    for (let i = 0; i < prices.length; i++) {
        if (i < 149) {
            ma150.push(null);
        } else {
            let sum = 0;
            for (let j = i - 149; j <= i; j++) {
                sum += prices[j];
            }
            ma150.push(sum / 150);
        }
    }

    let svg = '<svg width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '" style="display: block; width: 100%; height: 100%;">';

    // Legend at top right
    svg += '<text x="' + (w - padRight) + '" y="16" font-size="12" fill="#10b981" font-weight="600" text-anchor="end">— S&P 500</text>';
    svg += '<text x="' + (w - padRight - 100) + '" y="16" font-size="12" fill="#f59e0b" font-weight="600" text-anchor="end">- - 150-day MA</text>';

    // Horizontal grid lines + price labels
    for (let i = 0; i <= 4; i++) {
        const y = padTop + (chartH / 4) * i;
        const price = maxPrice - (range / 4) * i;
        svg += '<line x1="' + padLeft + '" y1="' + y + '" x2="' + (w - padRight) + '" y2="' + y + '" stroke="#f1f5f9" stroke-width="1"/>';
        svg += '<text x="' + (padLeft - 8) + '" y="' + (y + 4) + '" font-size="11" text-anchor="end" fill="#94a3b8" font-family="JetBrains Mono, monospace">' + price.toFixed(0) + '</text>';
    }

    // Date labels along x-axis
    if (dates && dates.length > 0) {
        var dateStep = Math.floor(dates.length / 6);
        for (var d = 0; d < dates.length; d += dateStep) {
            if (d >= dates.length) break;
            var dx = padLeft + (chartW / (prices.length - 1)) * d;
            var dateStr = dates[d];
            // Format: show Mon YYYY from YYYY-MM-DD
            var parts = dateStr.split('-');
            if (parts.length >= 2) {
                var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
                var mIdx = parseInt(parts[1], 10) - 1;
                dateStr = months[mIdx] + ' ' + parts[0].slice(2);
            }
            svg += '<text x="' + dx + '" y="' + (h - 6) + '" font-size="10" text-anchor="middle" fill="#94a3b8" font-family="JetBrains Mono, monospace">' + dateStr + '</text>';
        }
    }

    // S&P 500 price line (solid green, no fill)
    let path = '';
    for (let i = 0; i < prices.length; i++) {
        const x = padLeft + (chartW / (prices.length - 1)) * i;
        const y = padTop + chartH - ((prices[i] - minPrice) / range) * chartH;
        path += (i === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1);
    }
    svg += '<path d="' + path + '" stroke="#10b981" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>';

    // 150-day MA line (dashed amber)
    let maPath = '';
    let firstPoint = true;
    for (let i = 0; i < ma150.length; i++) {
        if (ma150[i] !== null) {
            const x = padLeft + (chartW / (prices.length - 1)) * i;
            const y = padTop + chartH - ((ma150[i] - minPrice) / range) * chartH;
            maPath += (firstPoint ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1);
            firstPoint = false;
        }
    }
    svg += '<path d="' + maPath + '" stroke="#f59e0b" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="8,4"/>';

    // Left axis line
    svg += '<line x1="' + padLeft + '" y1="' + padTop + '" x2="' + padLeft + '" y2="' + (padTop + chartH) + '" stroke="#cbd5e1" stroke-width="1"/>';
    // Bottom axis line
    svg += '<line x1="' + padLeft + '" y1="' + (padTop + chartH) + '" x2="' + (w - padRight) + '" y2="' + (padTop + chartH) + '" stroke="#cbd5e1" stroke-width="1"/>';

    svg += '</svg>';

    container.innerHTML = svg;
}

function renderSectors() {
    let html = '';

    SECTORS.forEach(function(sector) {
        const up_pct = sector.up || 0;
        const pb_pct = sector.pb || 0;
        const dn_pct = sector.dn || 0;
        const sb_pct = sector.sb || 0;
        const stockCount = STOCKS.filter(function(s) { return s.sec === sector.name; }).length;

        html += '<tr onclick="expandSector(&quot;' + sector.name + '&quot;)" style="cursor: pointer;">';
        html += '<td class="sector-name">' + sector.name + '</td>';

        // Trend bar (center-aligned)
        html += '<td style="text-align: center;"><div class="trend-bar" style="margin: 0 auto; width: 120px;">';
        if (up_pct > 0) html += '<div class="trend-segment trend-up" style="width: ' + up_pct + '%"></div>';
        if (pb_pct > 0) html += '<div class="trend-segment trend-pb" style="width: ' + pb_pct + '%"></div>';
        if (dn_pct > 0) html += '<div class="trend-segment trend-dn" style="width: ' + dn_pct + '%"></div>';
        if (sb_pct > 0) html += '<div class="trend-segment trend-sb" style="width: ' + sb_pct + '%"></div>';
        html += '</div></td>';

        // % Uptrend (right-aligned)
        html += '<td style="text-align: right;" class="pct-cell ' + (up_pct >= 60 ? 'high' : up_pct >= 40 ? 'med' : 'low') + '">' + up_pct.toFixed(1) + '%</td>';

        // Rel. Momentum (right-aligned)
        var rm = sector.rm || 0;
        var rmClass = rm >= 55 ? 'high' : rm >= 40 ? 'med' : 'low';
        html += '<td style="text-align: right;" class="pct-cell ' + rmClass + '">' + rm.toFixed(1) + '</td>';

        // # Stocks (right-aligned)
        html += '<td style="text-align: right;">' + stockCount + '</td>';

        html += '</tr>';
    });

    document.getElementById('sectorsTableBody').innerHTML = html;
}

var sectorSortCol = '';
var sectorSortAsc = false;

function sortSectors(column) {
    // Toggle direction if clicking same column
    if (sectorSortCol === column) {
        sectorSortAsc = !sectorSortAsc;
    } else {
        sectorSortCol = column;
        sectorSortAsc = false; // default: high to low for numbers, A-Z for name
    }
    var dir = sectorSortAsc ? 1 : -1;

    if (column === 'name') {
        SECTORS.sort(function(a, b) { return dir * a.name.localeCompare(b.name); });
    } else if (column === 'trend' || column === 'uptrend') {
        SECTORS.sort(function(a, b) { return dir * ((b.up || 0) - (a.up || 0)); });
    } else if (column === 'momentum') {
        SECTORS.sort(function(a, b) { return dir * ((b.rm || 0) - (a.rm || 0)); });
    } else if (column === 'count') {
        SECTORS.sort(function(a, b) {
            const countA = STOCKS.filter(function(s) { return s.sec === a.name; }).length;
            const countB = STOCKS.filter(function(s) { return s.sec === b.name; }).length;
            return dir * (countB - countA);
        });
    }

    // Update header arrows
    var headers = document.querySelectorAll('.sector-table th');
    headers.forEach(function(th) {
        th.textContent = th.textContent.replace(/ [▲▼]/g, '');
    });
    var arrow = sectorSortAsc ? ' ▲' : ' ▼';
    var colMap = { 'name': 0, 'trend': 1, 'uptrend': 2, 'momentum': 3, 'count': 4 };
    var idx = colMap[column];
    if (idx !== undefined && headers[idx]) {
        headers[idx].textContent = headers[idx].textContent + arrow;
    }

    renderSectors();
}

var currentExpandedSector = '';
var expandedSortCol = 'rm';
var expandedSortAsc = false;

function expandSector(sectorName) {
    const sector = SECTORS.find(function(s) { return s.name === sectorName; });
    if (!sector) return;

    currentExpandedSector = sectorName;
    expandedSortCol = 'rm';
    expandedSortAsc = false;
    renderExpandedSector();
    document.getElementById('expandedSector').style.display = 'block';
    document.getElementById('expandedSector').scrollIntoView({ behavior: 'smooth' });
}

function sortExpandedStocks(col) {
    if (expandedSortCol === col) { expandedSortAsc = !expandedSortAsc; }
    else { expandedSortCol = col; expandedSortAsc = col === 'ticker' || col === 'company'; }
    renderExpandedSector();
    var headers = document.querySelectorAll('#expandedStocksTable th');
    headers.forEach(function(th) { th.textContent = th.textContent.replace(/ [▲▼]/g, ''); });
    var colMap = { 'ticker': 0, 'company': 1, 'trend': 2, 'tr1wk': 3, 'trChg': 4, 'ret1m': 5, 'ret12m': 6 };
    var idx = colMap[col];
    if (idx !== undefined && headers[idx]) headers[idx].textContent += (expandedSortAsc ? ' ▲' : ' ▼');
}

function renderExpandedSector() {
    var sectorName = currentExpandedSector;
    var sectorStocks = STOCKS.filter(function(s) { return s.sec === sectorName; }).slice();

    document.getElementById('expandedSectorTitle').textContent = sectorName + ' (' + sectorStocks.length + ' stocks)';

    // Sort
    var col = expandedSortCol;
    var dir = expandedSortAsc ? 1 : -1;
    sectorStocks.sort(function(a, b) {
        var aVal, bVal;
        if (col === 'ticker') { aVal = a.t; bVal = b.t; }
        else if (col === 'company') { aVal = a.co; bVal = b.co; }
        else if (col === 'trend') { aVal = a.tr; bVal = b.tr; }
        else if (col === 'tr1wk') { aVal = a.tr1wk || ''; bVal = b.tr1wk || ''; }
        else if (col === 'trChg') {
            aVal = !a.trChg ? 0 : (a.tr === 'Uptrend' || a.tr === 'Snapback') ? 1 : -1;
            bVal = !b.trChg ? 0 : (b.tr === 'Uptrend' || b.tr === 'Snapback') ? 1 : -1;
        }
        else if (col === 'ret1m') { aVal = a.p1 ? (a.px - a.p1) / a.p1 : -999; bVal = b.p1 ? (b.px - b.p1) / b.p1 : -999; }
        else if (col === 'ret12m') { aVal = a.p12 ? (a.px - a.p12) / a.p12 : -999; bVal = b.p12 ? (b.px - b.p12) / b.p12 : -999; }
        else { aVal = a.rm || 0; bVal = b.rm || 0; }
        if (typeof aVal === 'string') return dir * aVal.localeCompare(bVal);
        return dir * (aVal - bVal);
    });

    let rows = '';
    sectorStocks.forEach(function(stock) {
        var trendClass = 'badge-' + (stock.tr === 'Uptrend' ? 'green' : stock.tr === 'Pullback' ? 'amber' : stock.tr === 'Downtrend' ? 'red' : stock.tr === 'Snapback' ? 'blue' : 'gray');
        var trend1wkClass = 'badge-' + ((stock.tr1wk || '') === 'Uptrend' ? 'green' : (stock.tr1wk || '') === 'Pullback' ? 'amber' : (stock.tr1wk || '') === 'Downtrend' ? 'red' : (stock.tr1wk || '') === 'Snapback' ? 'blue' : 'gray');
        var ret1m = stock.p1 ? ((stock.px - stock.p1) / stock.p1 * 100) : null;
        var ret12m = stock.p12 ? ((stock.px - stock.p12) / stock.p12 * 100) : null;
        var r1str = ret1m !== null ? ((ret1m >= 0 ? '+' : '') + ret1m.toFixed(1) + '%') : '—';
        var r12str = ret12m !== null ? ((ret12m >= 0 ? '+' : '') + ret12m.toFixed(1) + '%') : '—';
        var r1color = ret1m !== null && ret1m >= 0 ? '#10b981' : '#ef4444';
        var r12color = ret12m !== null && ret12m >= 0 ? '#10b981' : '#ef4444';

        var trendChgText = '';
        if (stock.trChg) {
            if (stock.tr === 'Uptrend' || stock.tr === 'Snapback') {
                trendChgText = '<span style="font-weight:700; font-size:18px; color:#10b981;" title="Improved from ' + (stock.tr1wk || '?') + '">+</span>';
            } else {
                trendChgText = '<span style="font-weight:700; font-size:18px; color:#ef4444;" title="Weakened from ' + (stock.tr1wk || '?') + '">−</span>';
            }
        }

        rows += '<tr style="cursor:pointer;" onclick="openStockModal(&quot;' + stock.t + '&quot;)">';
        rows += '<td style="font-weight:700; font-family: JetBrains Mono, monospace;">' + stock.t + '</td>';
        rows += '<td style="color:#475569;">' + stock.co + '</td>';
        rows += '<td><span class="badge ' + trendClass + '">' + stock.tr + '</span></td>';
        rows += '<td><span class="badge ' + trend1wkClass + '">' + (stock.tr1wk || '—') + '</span></td>';
        rows += '<td style="text-align:center;">' + trendChgText + '</td>';
        rows += '<td style="text-align:right; font-family:JetBrains Mono,monospace; font-weight:600; color:' + r1color + ';">' + r1str + '</td>';
        rows += '<td style="text-align:right; font-family:JetBrains Mono,monospace; font-weight:600; color:' + r12color + ';">' + r12str + '</td>';
        rows += '</tr>';
    });

    document.getElementById('expandedStocksBody').innerHTML = rows;
}

// ============================================================================
// INDUSTRIES TAB
// ============================================================================

var industrySortCol = 'uptrend';
var industrySortAsc = false;

function renderIndustries() {
    var sectorFilter = document.getElementById('industrySectorFilter').value;
    var filtered = INDUSTRIES;
    if (sectorFilter) {
        filtered = INDUSTRIES.filter(function(ind) { return ind.sector === sectorFilter; });
    }

    // Sort
    var col = industrySortCol;
    var dir = industrySortAsc ? 1 : -1;
    var sorted = filtered.slice();
    if (col === 'name') { sorted.sort(function(a, b) { return dir * a.name.localeCompare(b.name); }); }
    else if (col === 'sector') { sorted.sort(function(a, b) { return dir * a.sector.localeCompare(b.sector); }); }
    else if (col === 'trend' || col === 'uptrend') { sorted.sort(function(a, b) { return dir * ((b.up || 0) - (a.up || 0)); }); }
    else if (col === 'momentum') { sorted.sort(function(a, b) { return dir * ((b.rm || 0) - (a.rm || 0)); }); }
    else if (col === 'count') { sorted.sort(function(a, b) { return dir * ((b.n || 0) - (a.n || 0)); }); }

    var html = '';
    sorted.forEach(function(ind) {
        var up_pct = ind.up || 0;
        var pb_pct = ind.pb || 0;
        var dn_pct = ind.dn || 0;
        var sb_pct = ind.sb || 0;

        html += '<tr onclick="expandIndustry(&quot;' + ind.name.replace(/'/g, "\\'") + '&quot;)" style="cursor: pointer;">';
        html += '<td class="sector-name">' + ind.name + '</td>';
        html += '<td style="color:#64748b; font-size:12px;">' + (ind.sector || '') + '</td>';
        html += '<td style="text-align: center;"><div class="trend-bar" style="margin: 0 auto; width: 120px;">';
        if (up_pct > 0) html += '<div class="trend-segment trend-up" style="width: ' + up_pct + '%"></div>';
        if (pb_pct > 0) html += '<div class="trend-segment trend-pb" style="width: ' + pb_pct + '%"></div>';
        if (dn_pct > 0) html += '<div class="trend-segment trend-dn" style="width: ' + dn_pct + '%"></div>';
        if (sb_pct > 0) html += '<div class="trend-segment trend-sb" style="width: ' + sb_pct + '%"></div>';
        html += '</div></td>';
        html += '<td style="text-align: right;" class="pct-cell ' + (up_pct >= 60 ? 'high' : up_pct >= 40 ? 'med' : 'low') + '">' + up_pct.toFixed(1) + '%</td>';
        var rmClass = (ind.rm || 0) >= 55 ? 'high' : (ind.rm || 0) >= 40 ? 'med' : 'low';
        html += '<td style="text-align: right;" class="pct-cell ' + rmClass + '">' + (ind.rm || 0).toFixed(1) + '</td>';
        html += '<td style="text-align: right;">' + (ind.n || 0) + '</td>';
        html += '</tr>';
    });

    document.getElementById('industriesTableBody').innerHTML = html;
}

function sortIndustries(column) {
    if (industrySortCol === column) { industrySortAsc = !industrySortAsc; }
    else { industrySortCol = column; industrySortAsc = column === 'name' || column === 'sector'; }
    renderIndustries();

    // Update sort arrows
    var headers = document.querySelectorAll('#industriesTable th');
    headers.forEach(function(th) { th.textContent = th.textContent.replace(/ [▲▼]/g, ''); });
    var colMap = { 'name': 0, 'sector': 1, 'trend': 2, 'uptrend': 3, 'momentum': 4, 'count': 5 };
    var idx = colMap[column];
    if (idx !== undefined && headers[idx]) headers[idx].textContent += (industrySortAsc ? ' ▲' : ' ▼');
}

var currentExpandedIndustry = '';
var expandedIndSortCol = 'rm';
var expandedIndSortAsc = false;

function expandIndustry(industryName) {
    currentExpandedIndustry = industryName;
    expandedIndSortCol = 'rm';
    expandedIndSortAsc = false;
    renderExpandedIndustry();
    document.getElementById('expandedIndustry').style.display = 'block';
    document.getElementById('expandedIndustry').scrollIntoView({ behavior: 'smooth' });
}

function sortExpandedIndustryStocks(col) {
    if (expandedIndSortCol === col) { expandedIndSortAsc = !expandedIndSortAsc; }
    else { expandedIndSortCol = col; expandedIndSortAsc = col === 'ticker' || col === 'company'; }
    renderExpandedIndustry();
    var headers = document.querySelectorAll('#expandedIndustryStocksTable th');
    headers.forEach(function(th) { th.textContent = th.textContent.replace(/ [▲▼]/g, ''); });
    var colMap = { 'ticker': 0, 'company': 1, 'trend': 2, 'tr1wk': 3, 'trChg': 4, 'ret1m': 5, 'ret12m': 6 };
    var idx = colMap[col];
    if (idx !== undefined && headers[idx]) headers[idx].textContent += (expandedIndSortAsc ? ' ▲' : ' ▼');
}

function renderExpandedIndustry() {
    var indName = currentExpandedIndustry;
    var indStocks = STOCKS.filter(function(s) { return s.ind === indName; }).slice();

    document.getElementById('expandedIndustryTitle').textContent = indName + ' (' + indStocks.length + ' stocks)';

    var col = expandedIndSortCol;
    var dir = expandedIndSortAsc ? 1 : -1;
    indStocks.sort(function(a, b) {
        var aVal, bVal;
        if (col === 'ticker') { aVal = a.t; bVal = b.t; }
        else if (col === 'company') { aVal = a.co; bVal = b.co; }
        else if (col === 'trend') { aVal = a.tr; bVal = b.tr; }
        else if (col === 'tr1wk') { aVal = a.tr1wk || ''; bVal = b.tr1wk || ''; }
        else if (col === 'trChg') {
            aVal = !a.trChg ? 0 : (a.tr === 'Uptrend' || a.tr === 'Snapback') ? 1 : -1;
            bVal = !b.trChg ? 0 : (b.tr === 'Uptrend' || b.tr === 'Snapback') ? 1 : -1;
        }
        else if (col === 'ret1m') { aVal = a.p1 ? (a.px - a.p1) / a.p1 : -999; bVal = b.p1 ? (b.px - b.p1) / b.p1 : -999; }
        else if (col === 'ret12m') { aVal = a.p12 ? (a.px - a.p12) / a.p12 : -999; bVal = b.p12 ? (b.px - b.p12) / b.p12 : -999; }
        else { aVal = a.rm || 0; bVal = b.rm || 0; }
        if (typeof aVal === 'string') return dir * aVal.localeCompare(bVal);
        return dir * (aVal - bVal);
    });

    var rows = '';
    indStocks.forEach(function(stock) {
        var trendClass = 'badge-' + (stock.tr === 'Uptrend' ? 'green' : stock.tr === 'Pullback' ? 'amber' : stock.tr === 'Downtrend' ? 'red' : stock.tr === 'Snapback' ? 'blue' : 'gray');
        var trend1wkClass = 'badge-' + ((stock.tr1wk || '') === 'Uptrend' ? 'green' : (stock.tr1wk || '') === 'Pullback' ? 'amber' : (stock.tr1wk || '') === 'Downtrend' ? 'red' : (stock.tr1wk || '') === 'Snapback' ? 'blue' : 'gray');
        var ret1m = stock.p1 ? ((stock.px - stock.p1) / stock.p1 * 100) : null;
        var ret12m = stock.p12 ? ((stock.px - stock.p12) / stock.p12 * 100) : null;
        var r1str = ret1m !== null ? ((ret1m >= 0 ? '+' : '') + ret1m.toFixed(1) + '%') : '—';
        var r12str = ret12m !== null ? ((ret12m >= 0 ? '+' : '') + ret12m.toFixed(1) + '%') : '—';
        var r1color = ret1m !== null && ret1m >= 0 ? '#10b981' : '#ef4444';
        var r12color = ret12m !== null && ret12m >= 0 ? '#10b981' : '#ef4444';
        var trendChgText = '';
        if (stock.trChg) {
            if (stock.tr === 'Uptrend' || stock.tr === 'Snapback') {
                trendChgText = '<span style="font-weight:700; font-size:18px; color:#10b981;">+</span>';
            } else {
                trendChgText = '<span style="font-weight:700; font-size:18px; color:#ef4444;">−</span>';
            }
        }

        rows += '<tr style="cursor:pointer;" onclick="openStockModal(&quot;' + stock.t + '&quot;)">';
        rows += '<td style="font-weight:700; font-family: JetBrains Mono, monospace;">' + stock.t + '</td>';
        rows += '<td style="color:#475569;">' + stock.co + '</td>';
        rows += '<td><span class="badge ' + trendClass + '">' + stock.tr + '</span></td>';
        rows += '<td><span class="badge ' + trend1wkClass + '">' + (stock.tr1wk || '—') + '</span></td>';
        rows += '<td style="text-align:center;">' + trendChgText + '</td>';
        rows += '<td style="text-align:right; font-family:JetBrains Mono,monospace; font-weight:600; color:' + r1color + ';">' + r1str + '</td>';
        rows += '<td style="text-align:right; font-family:JetBrains Mono,monospace; font-weight:600; color:' + r12color + ';">' + r12str + '</td>';
        rows += '</tr>';
    });

    document.getElementById('expandedIndustryStocksBody').innerHTML = rows;
}

function renderStockScreener() {
    // Populate sector filter
    const sectors = [...new Set(STOCKS.map(function(s) { return s.sec; }))].sort();
    let sectorOptions = '';
    sectors.forEach(function(sec) {
        sectorOptions += '<option value="' + sec + '">' + sec + '</option>';
    });
    document.getElementById('sectorFilter').innerHTML = '<option value="">All Sectors</option>' + sectorOptions;

    // Initial render
    filterStocks();
    updateSummaryStrip();
}

function filterStocks() {
    const search = document.getElementById('searchInput').value.toLowerCase();
    const sector = document.getElementById('sectorFilter').value;
    const trend = document.getElementById('trendFilter').value;

    filteredStocks = STOCKS.filter(function(s) {
        const matchSearch = !search || s.t.toLowerCase().includes(search) || s.co.toLowerCase().includes(search);
        const matchSector = !sector || s.sec === sector;
        const matchTrend = !trend || s.tr === trend;
        return matchSearch && matchSector && matchTrend;
    });

    sortStocks(sortColumn, sortAsc);
    updateSummaryStrip();
}

function sortStocks(col, asc) {
    sortColumn = col;

    if (asc !== undefined) {
        sortAsc = asc;
    } else {
        sortAsc = !sortAsc;
    }

    filteredStocks.sort(function(a, b) {
        let aVal, bVal;

        if (col === 'ticker') { aVal = a.t; bVal = b.t; }
        else if (col === 'sector') { aVal = a.sec; bVal = b.sec; }
        else if (col === 'price') { aVal = a.px; bVal = b.px; }
        else if (col === 'ma150') { aVal = a.px / (1 + (a.ov || 0) / 100); bVal = b.px / (1 + (b.ov || 0) / 100); }
        else if (col === 'trend') { aVal = a.tr; bVal = b.tr; }
        else if (col === 'tr1wk') { aVal = a.tr1wk || ''; bVal = b.tr1wk || ''; }
        else if (col === 'momentum') { aVal = a.rm || 0; bVal = b.rm || 0; }
        else if (col === 'vsMa') { aVal = a.ov || 0; bVal = b.ov || 0; }
        else if (col === 'ret1m') { aVal = a.p1 ? (a.px - a.p1) / a.p1 : -999; bVal = b.p1 ? (b.px - b.p1) / b.p1 : -999; }
        else if (col === 'ret12m') { aVal = a.p12 ? (a.px - a.p12) / a.p12 : -999; bVal = b.p12 ? (b.px - b.p12) / b.p12 : -999; }
        else if (col === 'trChg') {
            aVal = !a.trChg ? 0 : (a.tr === 'Uptrend' || a.tr === 'Snapback') ? 1 : -1;
            bVal = !b.trChg ? 0 : (b.tr === 'Uptrend' || b.tr === 'Snapback') ? 1 : -1;
        }

        if (typeof aVal === 'string') {
            return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        } else {
            return sortAsc ? aVal - bVal : bVal - aVal;
        }
    });

    currentPage = 1;
    renderStockTable();

    // Update sort arrows on headers
    var headers = document.querySelectorAll('#stockTable thead th');
    headers.forEach(function(th) {
        th.textContent = th.textContent.replace(/ [▲▼]/g, '');
    });
    var colMap = { 'ticker': 1, 'sector': 2, 'price': 3, 'ma150': 4, 'trend': 5, 'tr1wk': 6, 'trChg': 7, 'momentum': 8, 'vsMa': 9, 'ret1m': 10, 'ret12m': 11, 'rasr': 12 };
    var idx = colMap[col];
    if (idx !== undefined && headers[idx]) {
        headers[idx].textContent = headers[idx].textContent + (sortAsc ? ' ▲' : ' ▼');
    }
}

function toggleRASR() {
    rasrExpanded = !rasrExpanded;
    var details = document.querySelectorAll('.rasr-detail');
    details.forEach(function(el) { el.style.display = rasrExpanded ? '' : 'none'; });
    var toggle = document.getElementById('rasrToggle');
    if (toggle) toggle.textContent = rasrExpanded ? '−' : '+';
}

function renderStockTable() {
    var start = (currentPage - 1) * ITEMS_PER_PAGE;
    var end = start + ITEMS_PER_PAGE;
    var page = filteredStocks.slice(start, end);

    var rows = '';
    page.forEach(function(stock, idx) {
        var num = start + idx + 1;
        var mc_str = stock.mc >= 1000 ? (stock.mc / 1000).toFixed(1) + 'T' : stock.mc >= 1 ? stock.mc.toFixed(0) + 'B' : (stock.mc * 1000).toFixed(0) + 'M';

        // Trend badges
        var trendClass = 'badge-' + (stock.tr === 'Uptrend' ? 'green' : stock.tr === 'Pullback' ? 'amber' : stock.tr === 'Downtrend' ? 'red' : stock.tr === 'Snapback' ? 'blue' : 'gray');
        var trend1wkClass = 'badge-' + (stock.tr1wk === 'Uptrend' ? 'green' : stock.tr1wk === 'Pullback' ? 'amber' : stock.tr1wk === 'Downtrend' ? 'red' : stock.tr1wk === 'Snapback' ? 'blue' : 'gray');

        // Trend change: + for bullish transitions, - for bearish
        var trendChgText = '';
        if (stock.trChg) {
            if (stock.tr === 'Uptrend' || stock.tr === 'Snapback') {
                trendChgText = '<span style="font-weight:700; font-size:18px; color:#10b981;" title="Improved from ' + (stock.tr1wk || '?') + '">+</span>';
            } else {
                trendChgText = '<span style="font-weight:700; font-size:18px; color:#ef4444;" title="Weakened from ' + (stock.tr1wk || '?') + '">−</span>';
            }
        }

        // Returns
        var ret1m = stock.p1 ? ((stock.px - stock.p1) / stock.p1 * 100) : null;
        var ret12m = stock.p12 ? ((stock.px - stock.p12) / stock.p12 * 100) : null;
        var r1str = ret1m !== null ? ((ret1m >= 0 ? '+' : '') + ret1m.toFixed(1) + '%') : '—';
        var r12str = ret12m !== null ? ((ret12m >= 0 ? '+' : '') + ret12m.toFixed(1) + '%') : '—';
        var r1color = ret1m !== null && ret1m >= 0 ? '#10b981' : '#ef4444';
        var r12color = ret12m !== null && ret12m >= 0 ? '#10b981' : '#ef4444';
        var momColor = stock.rm >= 60 ? '#10b981' : stock.rm >= 40 ? '#f59e0b' : '#ef4444';
        var ovColor = (stock.ov || 0) >= 0 ? '#10b981' : '#ef4444';

        rows += '<tr style="cursor:pointer;" onclick="openStockModal(&quot;' + stock.t + '&quot;)">';
        rows += '<td style="text-align:center; color:#64748b;">' + num + '</td>';
        rows += '<td style="font-family:JetBrains Mono,monospace; font-weight:900; font-size:14px;" title="' + stock.co + '">' + stock.t + '</td>';
        rows += '<td>' + stock.sec + '</td>';
        rows += '<td style="text-align:right; font-family:JetBrains Mono,monospace; font-weight:600;">$' + stock.px.toFixed(2) + '</td>';
        // Calculate 150-day MA from price and % over MA: ma150 = price / (1 + ov/100)
        var ma150val = (stock.ov !== null && stock.ov !== undefined && stock.ov !== 0) ? (stock.px / (1 + stock.ov / 100)) : stock.px;
        rows += '<td style="text-align:right; font-family:JetBrains Mono,monospace; font-size:12px; color:#64748b;">$' + ma150val.toFixed(2) + '</td>';
        rows += '<td><span class="badge ' + trendClass + '">' + stock.tr + '</span></td>';
        rows += '<td><span class="badge ' + trend1wkClass + '">' + (stock.tr1wk || '—') + '</span></td>';
        rows += '<td style="text-align:center;">' + trendChgText + '</td>';
        rows += '<td style="text-align:center;"><div style="display:inline-flex; align-items:center; gap:5px;"><div style="width:50px; height:5px; border-radius:3px; background:#e2e8f0;"><div style="width:' + (stock.rm || 0) + '%; height:100%; border-radius:3px; background:' + momColor + ';"></div></div><span style="font-family:JetBrains Mono,monospace; font-weight:600; font-size:12px; color:' + momColor + ';">' + (stock.rm || 0) + '</span></div></td>';
        rows += '<td style="text-align:right; font-family:JetBrains Mono,monospace; font-weight:600; color:' + ovColor + ';">' + ((stock.ov || 0) >= 0 ? '+' : '') + (stock.ov || 0).toFixed(1) + '%</td>';
        rows += '<td style="text-align:right; font-family:JetBrains Mono,monospace; font-weight:600; color:' + r1color + ';">' + r1str + '</td>';
        rows += '<td style="text-align:right; font-family:JetBrains Mono,monospace; font-weight:600; color:' + r12color + ';">' + r12str + '</td>';
        // RASR score (placeholder — no data yet)
        rows += '<td style="text-align:center; font-family:JetBrains Mono,monospace; font-weight:700; color:#94a3b8;">—</td>';
        // RASR detail columns (hidden by default)
        var rasrVis = rasrExpanded ? '' : 'display:none;';
        rows += '<td class="rasr-detail" style="text-align:center; font-family:JetBrains Mono,monospace; color:#94a3b8;' + rasrVis + '">—</td>';
        rows += '<td class="rasr-detail" style="text-align:center; font-family:JetBrains Mono,monospace; color:#94a3b8;' + rasrVis + '">—</td>';
        rows += '<td class="rasr-detail" style="text-align:center; font-family:JetBrains Mono,monospace; color:#94a3b8;' + rasrVis + '">—</td>';
        rows += '<td class="rasr-detail" style="text-align:center; font-family:JetBrains Mono,monospace; color:#94a3b8;' + rasrVis + '">—</td>';
        rows += '</tr>';
    });

    document.getElementById('stockTableBody').innerHTML = rows;

    // Pagination with smart display for 10+ pages
    const totalPages = Math.ceil(filteredStocks.length / ITEMS_PER_PAGE);
    let pageHtml = '';

    if (totalPages <= 10) {
        // Show all pages
        for (let i = 1; i <= totalPages; i++) {
            pageHtml += '<button class="page-btn ' + (i === currentPage ? 'active' : '') + '" onclick="goToPage(' + i + ')">' + i + '</button>';
        }
    } else {
        // Show first 3, ..., last 3, plus current page neighbors
        let pagesToShow = new Set();
        pagesToShow.add(1);
        pagesToShow.add(2);
        pagesToShow.add(3);
        pagesToShow.add(totalPages - 2);
        pagesToShow.add(totalPages - 1);
        pagesToShow.add(totalPages);
        pagesToShow.add(currentPage);
        if (currentPage > 1) pagesToShow.add(currentPage - 1);
        if (currentPage < totalPages) pagesToShow.add(currentPage + 1);

        const sortedPages = Array.from(pagesToShow).sort((a, b) => a - b);
        for (let i = 0; i < sortedPages.length; i++) {
            const p = sortedPages[i];
            if (i > 0 && sortedPages[i - 1] + 1 < p) {
                pageHtml += '<span style="color: #64748b; padding: 8px 4px;">...</span>';
            }
            pageHtml += '<button class="page-btn ' + (p === currentPage ? 'active' : '') + '" onclick="goToPage(' + p + ')">' + p + '</button>';
        }
    }

    document.getElementById('pagination').innerHTML = pageHtml || '<span style="color: #64748b;">No results</span>';
}

function goToPage(page) {
    currentPage = page;
    renderStockTable();
}

function updateSummaryStrip() {
    var total = filteredStocks.length;
    var up = filteredStocks.filter(function(s) { return s.tr === 'Uptrend'; }).length;
    var pb = filteredStocks.filter(function(s) { return s.tr === 'Pullback'; }).length;
    var dn = filteredStocks.filter(function(s) { return s.tr === 'Downtrend'; }).length;
    var sb = filteredStocks.filter(function(s) { return s.tr === 'Snapback'; }).length;
    var changed = filteredStocks.filter(function(s) { return s.trChg; }).length;
    var posChanges = filteredStocks.filter(function(s) { return s.trChg && (s.tr === 'Uptrend' || s.tr === 'Snapback'); }).length;
    var negChanges = filteredStocks.filter(function(s) { return s.trChg && (s.tr === 'Downtrend' || s.tr === 'Pullback'); }).length;

    var html = '<span><strong>Total:</strong> ' + total + '</span>';
    html += '<span style="color:#10b981;"><strong>Uptrend:</strong> ' + up + '</span>';
    html += '<span style="color:#f59e0b;"><strong>Pullback:</strong> ' + pb + '</span>';
    html += '<span style="color:#ef4444;"><strong>Downtrend:</strong> ' + dn + '</span>';
    html += '<span style="color:#3b82f6;"><strong>Snapback:</strong> ' + sb + '</span>';
    if (changed > 0) html += '<span style="color:#6366f1;"><strong>Trend Changes:</strong> ' + changed + ' (<span style="color:#10b981;">+' + posChanges + '</span> / <span style="color:#ef4444;">-' + negChanges + '</span>)</span>';
    document.getElementById('summaryStrip').innerHTML = html;
}

function getTrendClass(trend) {
    if (trend === 'Uptrend') return 'up';
    if (trend === 'Pullback') return 'pb';
    if (trend === 'Downtrend') return 'dn';
    if (trend === 'Snapback') return 'sb';
    return 'gray';
}

function openStockModal(ticker) {
    var stock = STOCKS.find(function(s) { return s.t === ticker; });
    if (!stock) return;

    var mc_str = stock.mc >= 1000 ? (stock.mc / 1000).toFixed(1) + 'T' : stock.mc >= 1 ? stock.mc.toFixed(0) + 'B' : (stock.mc * 1000).toFixed(0) + 'M';
    var ret1m = stock.p1 ? ((stock.px - stock.p1) / stock.p1 * 100) : null;
    var ret12m = stock.p12 ? ((stock.px - stock.p12) / stock.p12 * 100) : null;
    var r1str = ret1m !== null ? ((ret1m >= 0 ? '+' : '') + ret1m.toFixed(1) + '%') : '—';
    var r12str = ret12m !== null ? ((ret12m >= 0 ? '+' : '') + ret12m.toFixed(1) + '%') : '—';
    var r1color = ret1m !== null && ret1m >= 0 ? '#10b981' : '#ef4444';
    var r12color = ret12m !== null && ret12m >= 0 ? '#10b981' : '#ef4444';
    var momColor = stock.rm >= 60 ? '#10b981' : stock.rm >= 40 ? '#f59e0b' : '#ef4444';
    var trendClass = 'badge-' + (stock.tr === 'Uptrend' ? 'green' : stock.tr === 'Pullback' ? 'amber' : stock.tr === 'Downtrend' ? 'red' : stock.tr === 'Snapback' ? 'blue' : 'gray');

    // Signal
    var sig, sigColor, sigBg;
    if (stock.rm >= 70 && (stock.tr === 'Uptrend' || stock.tr === 'Pullback')) { sig = '+ Strong Momentum'; sigColor = '#065f46'; sigBg = '#d1fae5'; }
    else if (stock.rm <= 30 && (stock.tr === 'Downtrend' || stock.tr === 'Snapback')) { sig = '− Weak Momentum'; sigColor = '#991b1b'; sigBg = '#fecaca'; }
    else { sig = '○ Monitor'; sigColor = '#92400e'; sigBg = '#fef3c7'; }

    var html = '';
    // Dark header
    html += '<div style="padding: 24px 28px 18px; background: linear-gradient(135deg, #1e293b, #0f172a); border-radius: 16px 16px 0 0; color: white;">';
    html += '<div style="display: flex; justify-content: space-between; align-items: start;">';
    html += '<div>';
    html += '<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;"><span style="font-family: Fraunces, serif; font-size: 28px; font-weight: 700;">' + stock.t + '</span><span class="badge ' + trendClass + '">' + stock.tr + '</span></div>';
    html += '<div style="font-size: 13px; color: #cbd5e1;">' + stock.co + '</div>';
    html += '<div style="font-size: 13px; color: #64748b; margin-top: 2px;">' + stock.sec + ' · ' + (stock.ind || '') + '</div>';
    html += '</div>';
    html += '<button onclick="closeStockModal()" style="background: rgba(255,255,255,0.2); border: none; border-radius: 8px; padding: 8px 12px; cursor: pointer; color: white; font-size: 24px; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center;">×</button>';
    html += '</div>';
    html += '<div style="display: flex; align-items: baseline; gap: 10px; margin-top: 14px;">';
    html += '<span style="font-size: 30px; font-weight: 700;">$' + stock.px.toFixed(2) + '</span>';
    html += '<span style="font-size: 13px; font-weight: 600; color: ' + r12color + ';">' + r12str + ' (12m)</span>';
    html += '</div>';
    html += '<div style="margin-top: 10px; padding: 5px 12px; border-radius: 8px; background: ' + sigBg + '; color: ' + sigColor + '; font-size: 13px; font-weight: 700; display: inline-block;">' + sig + '</div>';
    html += '</div>';

    // Body
    html += '<div style="padding: 20px 28px 24px;">';

    // Price Momentum
    html += '<div style="margin-bottom: 16px;"><div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px; font-size: 13px; font-weight: 700; color: #1e293b;">Price Momentum</div>';
    html += '<div style="background: #f8fafc; border-radius: 10px; padding: 10px 14px;">';
    html += '<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px;"><span style="color: #64748b;">Trend Stage</span><span class="badge ' + trendClass + '" style="font-size: 13px; padding: 2px 8px;">' + stock.tr + '</span></div>';
    if (stock.tr1wk) html += '<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px;"><span style="color: #64748b;">1 Week Ago</span><span>' + stock.tr1wk + '</span></div>';
    html += '<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px;"><span style="color: #64748b;">Rel. Momentum Rank</span><span style="font-weight: 600; color: ' + momColor + ';">' + stock.rm + 'th pctl</span></div>';
    html += '<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px;"><span style="color: #64748b;">% vs 150 MA</span><span style="font-weight: 600; color: ' + (stock.ov >= 0 ? '#10b981' : '#ef4444') + ';">' + (stock.ov > 0 ? '+' : '') + (stock.ov || 0).toFixed(1) + '%</span></div>';
    html += '<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px;"><span style="color: #64748b;">12-Month Return</span><span style="font-weight: 600; color: ' + r12color + ';">' + r12str + '</span></div>';
    html += '<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px;"><span style="color: #64748b;">1-Month Return</span><span style="font-weight: 600; color: ' + r1color + ';">' + r1str + '</span></div>';
    html += '</div></div>';

    // Company Profile
    html += '<div><div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px; font-size: 13px; font-weight: 700; color: #1e293b;">Company Profile</div>';
    html += '<div style="background: #f8fafc; border-radius: 10px; padding: 10px 14px;">';
    html += '<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px;"><span style="color: #64748b;">Sector</span><span>' + stock.sec + '</span></div>';
    html += '<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px;"><span style="color: #64748b;">Industry</span><span>' + (stock.ind || '—') + '</span></div>';
    html += '<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px;"><span style="color: #64748b;">Market Cap</span><span>$' + mc_str + '</span></div>';
    html += '</div></div>';

    html += '<div style="margin-top: 16px; padding: 8px 12px; background: #fffbeb; border-radius: 8px; border: 1px solid #fde68a; font-size: 12px; color: #92400e; line-height: 1.5; text-align: center;">Educational analysis only — not investment advice. Past performance does not guarantee future results.</div>';
    html += '</div>';

    document.getElementById('stockModalBody').innerHTML = html;
    document.getElementById('stockModal').classList.add('active');
}

function closeStockModal(e) {
    // Only close if clicking the dark background, not the content
    if (e && e.target.id !== 'stockModal') return;
    document.getElementById('stockModal').classList.remove('active');
}

function renderResearchTab() {
    var html = '';

    // Search box
    html += '<div class="card" style="margin-bottom: 24px; border-left: 4px solid #10b981;">';
    html += '<div class="card-title" style="text-align: left; border-bottom: none; padding-bottom: 0;">Company Research</div>';
    html += '<div style="display: flex; align-items: center; gap: 10px; margin-top: 8px; margin-bottom: 12px;"><span style="background: #f59e0b; color: white; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.5px;">Under Construction</span><span style="font-size: 14px; color: #64748b;">Type any ticker to see available data. More features coming soon.</span></div>';
    html += '<div style="display: flex; gap: 12px; max-width: 600px;">';
    html += '<input type="text" id="researchTickerInput" placeholder="Enter ticker (e.g., NVDA, AAPL, TSLA...)" style="flex:1; padding: 12px 16px; font-size: 15px; font-family: JetBrains Mono, monospace; border: 2px solid #e2e8f0; border-radius: 10px; text-transform: uppercase; letter-spacing: 1px;" onkeydown="if(event.key===&quot;Enter&quot;)doResearchSearch();">';
    html += '<button onclick="doResearchSearch()" style="padding: 12px 24px; background: #10b981; color: white; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer; font-family: DM Sans, sans-serif;">Research</button>';
    html += '</div>';
    html += '<div id="researchStatus" style="margin-top: 10px; font-size: 13px; color: #94a3b8;"></div>';
    html += '<div id="researchResult" style="margin-top: 12px;"></div>';
    html += '</div>';

    return html;
}

function doResearchSearch() {
    var input = document.getElementById('researchTickerInput');
    var query = input.value.trim().toUpperCase();
    if (!query) return;

    var status = document.getElementById('researchStatus');
    var result = document.getElementById('researchResult');

    // Search embedded stock data
    var stock = STOCKS.find(function(s) { return s.t === query; });
    if (!stock) {
        // Try partial match on ticker or company name
        var matches = STOCKS.filter(function(s) {
            return s.t.indexOf(query) === 0 || s.co.toUpperCase().indexOf(query) >= 0;
        }).slice(0, 5);
        if (matches.length > 0) {
            status.innerHTML = 'No exact match for "' + query + '". Did you mean:';
            status.style.color = '#64748b';
            var suggestions = '';
            matches.forEach(function(m) {
                suggestions += '<span style="display:inline-block; margin:4px; padding:6px 12px; background:#f0fdf4; border:1px solid #10b981; border-radius:6px; cursor:pointer; font-family:JetBrains Mono,monospace; font-weight:600; font-size:13px;" onclick="document.getElementById(&quot;researchTickerInput&quot;).value=&quot;' + m.t + '&quot;;doResearchSearch();">' + m.t + ' <span style="font-family:DM Sans,sans-serif;font-weight:400;color:#64748b;">(' + m.co + ')</span></span>';
            });
            result.innerHTML = suggestions;
        } else {
            status.innerHTML = 'No stock found for "' + query + '". Try a different ticker.';
            status.style.color = '#dc2626';
            result.innerHTML = '';
        }
        return;
    }

    status.innerHTML = '';
    input.value = '';

    // Build inline research view
    var s = stock;
    var mc_str = (s.mc || 0) >= 1000 ? ((s.mc / 1000).toFixed(1) + 'T') : (s.mc || 0) >= 1 ? ((s.mc).toFixed(0) + 'B') : ((s.mc * 1000).toFixed(0) + 'M');
    var ret12m = s.p12 ? ((s.px - s.p12) / s.p12 * 100) : null;
    var r12str = ret12m !== null ? ((ret12m >= 0 ? '+' : '') + ret12m.toFixed(1) + '%') : '—';
    var r12color = ret12m !== null && ret12m >= 0 ? '#10b981' : '#ef4444';
    var ret1m = s.p1 ? ((s.px - s.p1) / s.p1 * 100) : null;
    var r1str = ret1m !== null ? ((ret1m >= 0 ? '+' : '') + ret1m.toFixed(1) + '%') : '—';
    var r1color = ret1m !== null && ret1m >= 0 ? '#10b981' : '#ef4444';
    var trendClass = 'badge-' + (s.tr === 'Uptrend' ? 'green' : s.tr === 'Pullback' ? 'amber' : s.tr === 'Downtrend' ? 'red' : s.tr === 'Snapback' ? 'blue' : 'gray');
    var upside = s.tgt && s.px ? ((s.tgt / s.px - 1) * 100) : null;
    var upsideStr = upside !== null ? ((upside >= 0 ? '+' : '') + upside.toFixed(1) + '%') : '';

    // Helper for section headers
    function secTitle(title) { return '<div style="font-family:Fraunces,serif;font-size:18px;font-weight:700;color:#0f172a;margin-bottom:14px;border-left:3px solid #10b981;padding-left:12px;">' + title + '</div>'; }
    function valRow(label, value) { return '<div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #f1f5f9;font-size:13px;"><span style="color:#64748b;">' + label + '</span><span style="font-family:JetBrains Mono,monospace;font-weight:600;">' + value + '</span></div>'; }
    function placeholder(text) { return '<div style="background:#f8fafc;border:2px dashed #e2e8f0;border-radius:10px;padding:16px;color:#94a3b8;font-style:italic;font-size:13px;line-height:1.6;">' + text + '</div>'; }

    var html = '';

    // ── HEADER ──
    html += '<div style="background:linear-gradient(135deg,#0f172a,#1e293b);border-radius:12px;padding:20px 24px;color:white;margin-bottom:20px;">';
    html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;">';
    html += '<div><div style="font-family:Fraunces,serif;font-size:24px;font-weight:700;">' + s.t + ' <span style="color:#10b981;">·</span> ' + s.co + '</div>';
    html += '<div style="font-size:12px;color:#94a3b8;margin-top:4px;">' + s.sec + ' · ' + (s.ind || '') + '</div>';
    html += '<div style="margin-top:8px;"><span class="badge ' + trendClass + '">' + s.tr + '</span> <span style="font-size:12px;color:#64748b;margin-left:8px;">Rel. Momentum: ' + (s.rm || 0) + 'th pctl</span></div>';
    html += '</div>';
    html += '<div style="text-align:right;"><div style="font-family:JetBrains Mono,monospace;font-size:28px;font-weight:700;color:#10b981;">$' + s.px.toFixed(2) + '</div>';
    html += '<div style="font-size:12px;color:#94a3b8;">Mkt Cap: $' + mc_str + '</div>';
    if (s.hi52 && s.lo52) html += '<div style="font-size:12px;color:#94a3b8;">52-Wk: $' + s.lo52.toFixed(2) + ' – $' + s.hi52.toFixed(2) + '</div>';
    html += '</div></div></div>';

    // ── 1. COMPANY DESCRIPTION ──
    html += '<div class="card" style="margin-bottom:20px;">';
    html += secTitle('Company Description');
    html += placeholder('What does ' + s.co + ' do? Describe their core business, products/services, and how they make money.');
    html += '</div>';

    // ── 2. HOW PEOPLE USE THE PRODUCT ──
    html += '<div class="card" style="margin-bottom:20px;">';
    html += secTitle('How the Average Person Uses Their Product');
    html += placeholder('How does a typical customer interact with ' + s.co + '? What problem does it solve for them in everyday life?');
    html += '</div>';

    // ── 3. MARKET OPPORTUNITY ──
    html += '<div class="card" style="margin-bottom:20px;">';
    html += secTitle('Market Opportunity');
    html += '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:12px;">';
    html += '<div style="background:#f8fafc;border-radius:8px;padding:14px;text-align:center;border:1px solid #e2e8f0;"><div style="font-size:10px;font-weight:600;text-transform:uppercase;color:#64748b;margin-bottom:6px;">Total Addressable Market</div><div style="font-family:JetBrains Mono,monospace;font-size:20px;font-weight:700;color:#0f172a;">—</div></div>';
    html += '<div style="background:#f8fafc;border-radius:8px;padding:14px;text-align:center;border:1px solid #e2e8f0;"><div style="font-size:10px;font-weight:600;text-transform:uppercase;color:#64748b;margin-bottom:6px;">Market Share</div><div style="font-family:JetBrains Mono,monospace;font-size:20px;font-weight:700;color:#0f172a;">—</div></div>';
    html += '<div style="background:#f8fafc;border-radius:8px;padding:14px;text-align:center;border:1px solid #e2e8f0;"><div style="font-size:10px;font-weight:600;text-transform:uppercase;color:#64748b;margin-bottom:6px;">Market Position</div><div style="font-family:JetBrains Mono,monospace;font-size:20px;font-weight:700;color:#0f172a;">—</div></div>';
    html += '</div>';
    html += placeholder('What is the total addressable market? How much share does ' + s.co + ' have? Who are the top competitors and where does ' + s.co + ' rank?');
    html += '</div>';

    // ── 4. FUNDAMENTALS ──
    html += '<div class="card" style="margin-bottom:20px;">';
    html += secTitle('Fundamentals');
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:16px;">';
    function kpi(label, value, highlight) {
        var border = highlight ? 'border-top:3px solid #10b981;' : 'border-top:3px solid #1e293b;';
        return '<div style="background:white;border-radius:8px;padding:12px 14px;border:1px solid #e2e8f0;' + border + '"><div style="font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:#64748b;margin-bottom:4px;">' + label + '</div><div style="font-family:JetBrains Mono,monospace;font-size:17px;font-weight:700;color:#0f172a;">' + value + '</div></div>';
    }
    html += kpi('Revenue Growth', s.rg !== null && s.rg !== undefined ? s.rg.toFixed(1) + '%' : 'N/A', s.rg > 0);
    html += kpi('Gross Margin', s.gm !== null && s.gm !== undefined ? s.gm.toFixed(1) + '%' : 'N/A');
    html += kpi('Op Margin', s.om !== null && s.om !== undefined ? s.om.toFixed(1) + '%' : 'N/A');
    html += kpi('Net Margin', s.pm !== null && s.pm !== undefined ? s.pm.toFixed(1) + '%' : 'N/A');
    html += kpi('Trailing EPS', s.eps ? '$' + s.eps.toFixed(2) : 'N/A');
    html += kpi('Forward EPS', s.feps ? '$' + s.feps.toFixed(2) : 'N/A');
    html += kpi('Trailing P/E', s.tpe ? s.tpe.toFixed(1) + 'x' : 'N/A');
    html += kpi('Forward P/E', s.fpe ? s.fpe.toFixed(1) + 'x' : 'N/A');
    html += '</div>';

    // Valuation detail
    html += '<div style="margin-top:12px;">';
    html += valRow('Market Cap', '$' + mc_str);
    html += valRow('Enterprise Value', s.ev ? '$' + (s.ev >= 1000 ? (s.ev/1000).toFixed(1) + 'T' : s.ev.toFixed(0) + 'B') : 'N/A');
    html += valRow('EV / Revenue', s.evr ? s.evr.toFixed(1) + 'x' : 'N/A');
    html += valRow('EV / EBITDA', s.eve ? s.eve.toFixed(1) + 'x' : 'N/A');
    html += valRow('Price / Book', s.pb ? s.pb.toFixed(1) + 'x' : 'N/A');
    html += valRow('Dividend Yield', s.dy ? s.dy.toFixed(2) + '%' : 'N/A');
    html += valRow('Analyst Target', s.tgt ? '$' + s.tgt.toFixed(2) + ' (' + upsideStr + ')' : 'N/A');
    html += valRow('Analyst Count', s.nAn ? s.nAn + ' analysts' : 'N/A');
    html += '</div>';

    // Forward expectations placeholder
    html += '<div style="margin-top:16px;">';
    html += '<div style="font-size:14px;font-weight:600;color:#0f172a;margin-bottom:8px;">Forward Expectations</div>';
    html += placeholder('What are the consensus estimates for next year sales and earnings growth? Are estimates being revised up or down?');
    html += '</div>';
    html += '</div>';

    // ── 5. TECHNICAL / MOMENTUM PROFILE ──
    html += '<div class="card" style="margin-bottom:20px;">';
    html += secTitle('Technical / Momentum Profile');

    // Price level visualization
    var ma150val = s.ov !== null && s.ov !== undefined && s.ov !== 0 ? (s.px / (1 + s.ov / 100)) : null;
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:16px;">';
    html += kpi('Price', '$' + s.px.toFixed(2));
    html += kpi('150-Day MA', ma150val ? '$' + ma150val.toFixed(2) : 'N/A');
    html += kpi('vs 150d MA', (s.ov >= 0 ? '+' : '') + (s.ov || 0).toFixed(1) + '%', s.ov > 0);
    html += kpi('1M Return', r1str, ret1m > 0);
    html += kpi('12M Return', r12str, ret12m > 0);
    html += kpi('Beta', s.beta ? s.beta.toFixed(2) : 'N/A');
    html += '</div>';

    html += valRow('Trend Stage', '<span class="badge ' + trendClass + '">' + s.tr + '</span>');
    html += valRow('1 Week Ago', s.tr1wk || '—');
    html += valRow('Trend Changed', s.trChg ? '<span style="color:' + (s.tr === 'Uptrend' || s.tr === 'Snapback' ? '#10b981' : '#ef4444') + ';font-weight:700;">Yes</span>' : 'No');
    html += valRow('Rel. Momentum Rank', (s.rm || 0) + 'th percentile');
    html += valRow('Tier', s.ti || '—');
    if (s.hi52 && s.lo52) {
        var rangePos = s.hi52 > s.lo52 ? Math.round((s.px - s.lo52) / (s.hi52 - s.lo52) * 100) : 50;
        html += '<div style="margin-top:12px;"><div style="font-size:12px;color:#64748b;margin-bottom:4px;">52-Week Range Position</div>';
        html += '<div style="display:flex;align-items:center;gap:8px;"><span style="font-size:11px;color:#64748b;">$' + s.lo52.toFixed(0) + '</span>';
        html += '<div style="flex:1;height:8px;background:#e2e8f0;border-radius:4px;position:relative;"><div style="width:' + rangePos + '%;height:100%;background:#10b981;border-radius:4px;"></div></div>';
        html += '<span style="font-size:11px;color:#64748b;">$' + s.hi52.toFixed(0) + '</span></div></div>';
    }
    html += '</div>';

    // ── 6. INVESTMENT NOTES ──
    html += '<div class="card" style="margin-bottom:20px;">';
    html += secTitle('Investment Notes');
    html += placeholder('What is your thesis for ' + s.co + '? Key catalysts, risks, what would make you buy or sell? What are you watching for?');
    html += '</div>';

    result.innerHTML = html;
}

function renderSourcesTab() {
    let html = '';

    // Card 1: Data Sources
    html += '<div class="card"><div class="card-title">Data Sources</div>';
    html += '<div class="metric-row"><span class="metric-label">yfinance (Yahoo Finance)</span><div style="text-align:right;"><div style="font-size:13px; color:#64748b;">Stock prices, moving averages, VIX, oil, dollar index, sector classification</div></div></div>';
    html += '<div class="metric-row"><span class="metric-label">FRED (Federal Reserve Economic Data)</span><div style="text-align:right;"><div style="font-size:13px; color:#64748b;">GDP, unemployment, inflation, yields, credit spreads, mortgage rates, consumer sentiment, gas prices</div></div></div>';
    html += '<div class="metric-row"><span class="metric-label">CBOE (Chicago Board Options Exchange)</span><div style="text-align:right;"><div style="font-size:13px; color:#64748b;">Put/Call ratio (updated weekly, entered manually)</div></div></div>';
    html += '<div class="metric-row"><span class="metric-label">AAII (American Association of Individual Investors)</span><div style="text-align:right;"><div style="font-size:13px; color:#64748b;">Bull/Bear sentiment survey (updated weekly, entered manually)</div></div></div>';
    html += '<div class="metric-row"><span class="metric-label">FactSet Earnings Insight</span><div style="text-align:right;"><div style="font-size:13px; color:#64748b;">S&P 500 earnings growth, revenue growth, beat rates, profit margins, forward P/E, analyst revisions</div></div></div>';
    html += '<div class="metric-row"><span class="metric-label">Manual Assessment</span><div style="text-align:right;"><div style="font-size:13px; color:#64748b;">Geopolitical risk level, fiscal policy stance, monetary policy stance</div></div></div>';
    html += '</div>';

    // Card 2: Health Score Methodology
    html += '<div class="card"><div class="card-title">Health Score Methodology</div>';
    html += '<p style="font-size: 14px; color: #64748b; line-height: 1.6; margin-bottom: 16px;">The Momentum Scorecard uses an 18-indicator scoring system across three categories. Every indicator gets equal weight — one vote, one voice. No thumb on the scale.</p>';
    html += '<div style="margin-bottom: 12px;"><strong style="color: #0f172a;">18 Binary Indicators (equal weight):</strong><br/><span style="font-size: 14px; color: #64748b;">Macro (8) + Fundamental (5) + Technical (5) — each worth 5 points</span></div>';
    html += '<div style="margin-bottom: 12px;"><strong style="color: #0f172a;">Total Possible:</strong><br/><span style="font-size: 14px; color: #64748b;">90 points (18 indicators &times; 5 points each)</span></div>';
    html += '<div style="margin-bottom: 12px;"><strong style="color: #0f172a;">Why Equal Weight?</strong><br/><span style="font-size: 14px; color: #64748b;">Simplicity and transparency. Each indicator gets an equal say. If one area matters more, it shows up naturally by having more indicators (Macro has 8 votes vs 5 for the others). No hidden biases.</span></div>';
    html += '<div style="margin-bottom: 12px;"><strong style="color: #0f172a;">Health Score Bands:</strong><br/>';
    html += '<div style="font-size: 13px; color: #64748b; margin-top: 8px;"><span style="color: #ef4444; font-weight: 600;">0-25%</span>: Risk Off · <span style="color: #f59e0b; font-weight: 600;">25-40%</span>: Defensive · <span style="color: #ca8a04; font-weight: 600;">40-60%</span>: Cautious · <span style="color: #10b981; font-weight: 600;">60-80%</span>: Optimistic · <span style="color: #059669; font-weight: 600;">80-100%</span>: Bullish</div>';
    html += '</div>';
    html += '</div>';

    // Card 3: Indicator Thresholds
    html += '<div class="card"><div class="card-title">All 18 Health Indicators</div>';
    html += '<table class="stock-table" style="font-size: 13px;"><thead><tr><th>Indicator</th><th>Healthy When</th><th>Category</th><th>Why It Matters</th></tr></thead><tbody>';
    html += '<tr><td>Labor Market</td><td>Below 5%</td><td>Macro</td><td>Jobs = spending power = economic engine</td></tr>';
    html += '<tr><td>GDP Growth</td><td>Above 2%</td><td>Macro</td><td>Growing economy supports corporate profits</td></tr>';
    html += '<tr><td>Inflation</td><td>Below 3%</td><td>Macro</td><td>Stable prices keep the Fed from tightening</td></tr>';
    html += '<tr><td>Credit Spreads</td><td>Below 4%</td><td>Macro</td><td>Tight spreads = confident lenders</td></tr>';
    html += '<tr><td>Consumer Confidence</td><td>Above 70</td><td>Macro</td><td>Confident consumers spend more</td></tr>';
    html += '<tr><td>Mortgage Rates</td><td>Below 6%</td><td>Macro</td><td>Lower rates boost housing and wealth</td></tr>';
    html += '<tr><td>Yield Curve</td><td>Positive (not inverted)</td><td>Macro</td><td>Inverted curve has preceded every recession since 1960s</td></tr>';
    html += '<tr><td>ISM Manufacturing</td><td>Above 50</td><td>Macro</td><td>Best leading indicator of economic turns</td></tr>';
    html += '<tr><td>Earnings Growth</td><td>Above 5%</td><td>Fundamental</td><td>Companies making more money drives stocks</td></tr>';
    html += '<tr><td>Profit Margins</td><td>Above 11%</td><td>Fundamental</td><td>Pricing power and efficiency signal</td></tr>';
    html += '<tr><td>Earnings Revisions</td><td>Above 1.0x</td><td>Fundamental</td><td>Analysts raising estimates = positive trend</td></tr>';
    html += '<tr><td>Valuation (Fwd P/E)</td><td>Below 20x</td><td>Fundamental</td><td>Lower P/E = more room for upside</td></tr>';
    html += '<tr><td>Free Cash Flow Yield</td><td>Above 3.5%</td><td>Fundamental</td><td>Real cash for dividends, buybacks, growth</td></tr>';
    html += '<tr><td>Long-Term Trend</td><td>S&P above 4-Year MA</td><td>Technical</td><td>Big-picture market direction</td></tr>';
    html += '<tr><td>Medium-Term Trend</td><td>S&P above 150-Day MA</td><td>Technical</td><td>Intermediate trend direction</td></tr>';
    html += '<tr><td>Market Breadth</td><td>Above 60%</td><td>Technical</td><td>Broad participation = healthy market</td></tr>';
    html += '<tr><td>Volatility (VIX)</td><td>Below 20</td><td>Technical</td><td>Low fear = stable conditions</td></tr>';
    html += '<tr><td>Sentiment (Put/Call)</td><td>Below 1.0</td><td>Technical</td><td>More calls than puts = bullish positioning</td></tr>';
    html += '</tbody></table>';
    html += '</div>';

    // Card 4: Oversold Indicators
    html += '<div class="card"><div class="card-title">Oversold Indicators & Capitulation Signals</div>';
    html += '<p style="font-size: 14px; color: #64748b; line-height: 1.6; margin-bottom: 16px;">Four key signals that indicate extreme selling and potential market bottoms:</p>';
    html += '<div class="metric-row"><span class="metric-label">Breadth Washout</span><div style="text-align:right;"><div style="font-size:13px; color:#64748b;">% of stocks above 20-day SMA drops below 20%</div></div></div>';
    html += '<div class="metric-row"><span class="metric-label">New Lows Spike</span><div style="text-align:right;"><div style="font-size:13px; color:#64748b;">50%+ of stocks making 20-day lows</div></div></div>';
    html += '<div class="metric-row"><span class="metric-label">Put/Call Spike</span><div style="text-align:right;"><div style="font-size:13px; color:#64748b;">CBOE Put/Call Ratio above 1.2</div></div></div>';
    html += '<div class="metric-row"><span class="metric-label">VIX Spike</span><div style="text-align:right;"><div style="font-size:13px; color:#64748b;">VIX above 30</div></div></div>';
    html += '<p style="font-size: 14px; color: #64748b; margin-top: 16px; line-height: 1.5;">Each signal stands alone — any single signal firing is meaningful. Historically, oversold signals cluster near market bottoms and often precede strong bounces.</p>';
    html += '</div>';

    // Card 5: Stock Screener Methodology
    html += '<div class="card"><div class="card-title">Stock Screener Methodology</div>';
    html += '<div class="metric-row"><span class="metric-label">Trend Stage</span><div style="text-align:right;"><div style="font-size:13px; color:#64748b;">Based on price vs 150-day MA and MA slope direction: Uptrend, Pullback, Downtrend, Snapback</div></div></div>';
    html += '<div class="metric-row"><span class="metric-label">Rel. Momentum</span><div style="text-align:right;"><div style="font-size:13px; color:#64748b;">12-month return percentile rank across full universe (100 = top performer, 1 = bottom)</div></div></div>';
    html += '<div class="metric-row"><span class="metric-label">Tier</span><div style="text-align:right;"><div style="font-size:13px; color:#64748b;">1-10 ranking (1 = strongest, 10 = weakest) derived from relative momentum</div></div></div>';
    html += '<div class="metric-row"><span class="metric-label">% Over/Under 150d MA</span><div style="text-align:right;"><div style="font-size:13px; color:#64748b;">How far price is from its 150-day moving average</div></div></div>';
    html += '</div>';

    // Card 6: Key Definitions & Formulas
    html += '<div class="card"><div class="card-title">Definitions &amp; Formulas</div>';

    // Market Trend
    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Market Trend (Positive / Neutral / Negative)</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">Compares the S&P 500 price to two moving averages. <strong>Positive</strong> = price is above both the 4-year MA and 150-day MA. <strong>Neutral</strong> = above one but below the other. <strong>Negative</strong> = below both. The 4-year MA captures the full business cycle; the 150-day MA captures the intermediate trend.</div>';
    html += '</div>';

    // Breadth
    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Market Breadth</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">Formula: (Number of stocks above their 150-day MA) &divide; (Total stocks tracked) &times; 100. Above 60% = healthy broad participation. Below 40% = weak, narrow market. Below 20% = oversold (capitulation zone).</div>';
    html += '</div>';

    // Trend Stages
    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Trend Stages (Uptrend / Pullback / Downtrend / Snapback)</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">Each stock is classified by two conditions: (1) Is the 150-day MA rising or falling? (compared to its value 42 trading days ago) (2) Is the price above or below the 150-day MA?</div>';
    html += '<div style="font-size: 13px; color: #64748b; margin-top: 6px;"><strong style="color:#10b981;">Uptrend</strong> = MA rising + price above MA (ideal). <strong style="color:#f59e0b;">Pullback</strong> = MA rising + price below MA (temporary dip in a healthy trend). <strong style="color:#ef4444;">Downtrend</strong> = MA falling + price below MA (avoid). <strong style="color:#3b82f6;">Snapback</strong> = MA falling + price above MA (potential reversal, watch closely).</div>';
    html += '</div>';

    // Relative Momentum
    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Relative Momentum Rank</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">Formula: Percentile rank of each stock\\'s 12-month return across the full universe. A rank of 85 means the stock has a higher 12-month return than 85% of all stocks tracked. Above 60 = strong momentum. Below 40 = weak momentum.</div>';
    html += '</div>';

    // Tier
    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Tier (1-10)</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">Derived from relative momentum rank. Tier 1 = top 10% (strongest), Tier 10 = bottom 10% (weakest). Formula: Tier = 11 - floor(rank / 10), clamped to 1-10.</div>';
    html += '</div>';

    // Moving Averages
    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Moving Averages (150-Day, 4-Year)</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">A moving average is the average closing price over the last N trading days. The <strong>150-day MA</strong> (~30 weeks) captures the intermediate trend. The <strong>4-year MA</strong> (~1,000 trading days) captures the full business cycle. When price is above the MA, the trend is considered up. When the MA itself is rising, the trend has momentum.</div>';
    html += '</div>';

    // Yield Curve
    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Yield Curve</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">Formula: 10-Year Treasury Yield minus 2-Year Treasury Yield. A <strong>positive</strong> yield curve is normal and healthy. An <strong>inverted</strong> (negative) yield curve has preceded every U.S. recession since the 1960s, typically by 12-18 months.</div>';
    html += '</div>';

    // P/E Ratio
    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Forward P/E Ratio</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">Formula: Current S&P 500 Price &divide; Estimated Earnings Per Share (next 12 months). Measures how expensive stocks are relative to expected profits. The 10-year average is ~18.9x. Below 18x is historically cheap; above 22x is expensive.</div>';
    html += '</div>';

    // PEG Ratio
    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">PEG Ratio</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">Formula: Forward P/E &divide; Expected EPS Growth Rate. A PEG below 1.0 suggests you are paying less than the growth rate (potentially undervalued). A PEG above 2.0 suggests you are overpaying relative to growth.</div>';
    html += '</div>';

    // VIX
    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">VIX (Volatility Index)</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">Measures expected market volatility over the next 30 days, derived from S&P 500 options prices. Below 20 = calm. 20-30 = elevated uncertainty. Above 30 = panic / fear (historically a contrarian buy signal).</div>';
    html += '</div>';

    // Put/Call Ratio
    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Put/Call Ratio</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">Formula: Total Put Volume &divide; Total Call Volume (from CBOE). Below 1.0 = more calls than puts (bullish positioning). Above 1.0 = more puts (hedging/fear). Above 1.2 = extreme fear (oversold signal).</div>';
    html += '</div>';

    // Oversold Signals
    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Oversold / Capitulation Signals</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">Four independent signals that indicate extreme selling: (1) <strong>Breadth Washout</strong>: less than 20% of stocks above their 20-day SMA. (2) <strong>New Lows Spike</strong>: more than 50% of stocks at 20-day lows. (3) <strong>Put/Call Spike</strong>: CBOE ratio above 1.2. (4) <strong>VIX Spike</strong>: VIX above 30. Any single signal firing is meaningful. Multiple signals together suggest capitulation — historically near market bottoms.</div>';
    html += '</div>';

    // Synthesis
    html += '<div style="padding: 12px 0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Strategic Synthesis (Equities / Fixed Income / Cash)</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">Asset class views are derived from the health score. Equities: <strong>Overweight</strong> when score &ge; 70, <strong>Neutral</strong> at 50-69, <strong>Underweight</strong> below 50. Cash: <strong>Underweight</strong> when score &ge; 60 (deploy into risk assets), <strong>Neutral</strong> otherwise. Fixed Income view considers the yield curve and credit spreads.</div>';
    html += '</div>';

    html += '</div>';

    // Card 7: Bull & Bear Market History
    // Card: Secular & Cyclical Market Definitions
    html += '<div class="card"><div class="card-title">Market Cycle Definitions</div>';

    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Secular (Generational) Bull Market</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">A 16-18 year period where the broad market trends structurally higher. Cyclical bear markets (20%+ declines) still happen during secular bulls, but they are buying opportunities — the market recovers and makes new highs. Defined by the S&P 500 maintaining a long-term uptrend above its multi-year moving averages. Three since 1957: <strong>1957-1966</strong> (post-war boom), <strong>1982-2000</strong> (tech revolution), <strong>2016-present</strong> (AI and digital transformation).</div>';
    html += '</div>';

    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Secular (Generational) Bear Market</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">A 16-18 year period where the broad market moves sideways to down. Cyclical rallies happen but fail to sustain new highs — the market churns in a wide range. Returns over the full period are minimal (often single digits total over 16+ years). Two since 1957: <strong>1966-1982</strong> (inflation and oil shocks, S&P gained only 9% over 16 years) and <strong>2000-2016</strong> (dot-com bust and financial crisis, S&P gained only 19% over 16 years).</div>';
    html += '</div>';

    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Cyclical Bull Market</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">A 3-4 year uptrend within a larger secular cycle. During secular bull markets, cyclical bulls develop from lows near the 4-year moving average with an average rally of +111% and an average correction of -23%. The current cyclical bull began in October 2022.</div>';
    html += '</div>';

    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Bear Market</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">A decline of 20% or more from a peak to a trough. This scorecard tracks bear markets using the traditional peak-to-trough measurement — a new bear market is not counted until the prior high has been recovered. There have been 11 bear markets since 1957 with a median decline of -33% and a median duration of 14 months.</div>';
    html += '</div>';

    html += '<div style="padding: 12px 0; border-bottom: 1px solid #e2e8f0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">4-Year Moving Average (200-Week MA)</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">The average closing price of the S&P 500 over the last ~1,000 trading days (4 years or 200 weeks). This serves as the structural dividing line between secular bull and bear markets. When the S&P is above this line, the long-term cycle favors being invested. When it breaks below, caution is warranted. A sustained break below the 4-year MA has historically signaled that the secular trend is turning negative.</div>';
    html += '</div>';

    html += '<div style="padding: 12px 0;">';
    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">Why This Matters for Investors</div>';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;">Knowing whether you are in a secular bull or bear market is arguably the single most important thing an investor can know. In a secular bull, the default action is to stay invested and use pullbacks to add exposure. In a secular bear, the default action is to be more tactical — sell rallies and wait for better prices. We are currently in a <strong>secular bull market</strong> that began in 2016, and until the S&P sustains a break below the 4-year moving average, the long-term trend favors being invested.</div>';
    html += '</div>';

    html += '</div>';

    html += '<div class="card"><div class="card-title">Bull &amp; Bear Market History (S&amp;P 500, 1957–Present)</div>';
    html += '<p style="font-size: 13px; color: #64748b; margin-bottom: 14px;">All statistics use median values (less skewed by outliers). A bear market is a 20%+ decline from peak. A bull market is the recovery from a bear market trough to the next peak.</p>';

    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 8px;">Bear Markets</div>';
    html += '<table class="stock-table" style="font-size: 12px; margin-bottom: 20px;"><thead><tr><th style="text-align:left;">Period</th><th style="text-align:right;">Peak</th><th style="text-align:right;">Trough</th><th style="text-align:right;">Decline</th><th style="text-align:right;">Duration</th><th style="text-align:left;">Trigger</th></tr></thead><tbody>';
    html += '<tr><td>1957</td><td style="text-align:right;">49</td><td style="text-align:right;">39</td><td style="text-align:right;color:#ef4444;">-21%</td><td style="text-align:right;">3 mo</td><td>Eisenhower recession</td></tr>';
    html += '<tr><td>1961-62</td><td style="text-align:right;">72</td><td style="text-align:right;">52</td><td style="text-align:right;color:#ef4444;">-28%</td><td style="text-align:right;">6 mo</td><td>Flash crash, steel crisis</td></tr>';
    html += '<tr><td>1966</td><td style="text-align:right;">94</td><td style="text-align:right;">73</td><td style="text-align:right;color:#ef4444;">-22%</td><td style="text-align:right;">8 mo</td><td>Credit crunch, Vietnam</td></tr>';
    html += '<tr><td>1968-70</td><td style="text-align:right;">108</td><td style="text-align:right;">69</td><td style="text-align:right;color:#ef4444;">-36%</td><td style="text-align:right;">18 mo</td><td>Inflation, social unrest</td></tr>';
    html += '<tr><td>1973-74</td><td style="text-align:right;">120</td><td style="text-align:right;">62</td><td style="text-align:right;color:#ef4444;">-48%</td><td style="text-align:right;">21 mo</td><td>Oil embargo, Watergate</td></tr>';
    html += '<tr><td>1980-82</td><td style="text-align:right;">141</td><td style="text-align:right;">102</td><td style="text-align:right;color:#ef4444;">-27%</td><td style="text-align:right;">21 mo</td><td>Volcker rate hikes</td></tr>';
    html += '<tr><td>1987</td><td style="text-align:right;">337</td><td style="text-align:right;">224</td><td style="text-align:right;color:#ef4444;">-34%</td><td style="text-align:right;">3 mo</td><td>Black Monday crash</td></tr>';
    html += '<tr><td>2000-02</td><td style="text-align:right;">1,527</td><td style="text-align:right;">777</td><td style="text-align:right;color:#ef4444;">-49%</td><td style="text-align:right;">31 mo</td><td>Dot-com bust</td></tr>';
    html += '<tr><td>2007-09</td><td style="text-align:right;">1,565</td><td style="text-align:right;">677</td><td style="text-align:right;color:#ef4444;">-57%</td><td style="text-align:right;">17 mo</td><td>Financial crisis</td></tr>';
    html += '<tr><td>2020</td><td style="text-align:right;">3,386</td><td style="text-align:right;">2,237</td><td style="text-align:right;color:#ef4444;">-34%</td><td style="text-align:right;">1 mo</td><td>COVID-19</td></tr>';
    html += '<tr><td>2022</td><td style="text-align:right;">4,797</td><td style="text-align:right;">3,577</td><td style="text-align:right;color:#ef4444;">-25%</td><td style="text-align:right;">10 mo</td><td>Inflation, rate hikes</td></tr>';
    html += '<tr style="background:#f8fafc;font-weight:600;"><td>Median</td><td></td><td></td><td style="text-align:right;color:#ef4444;">-33%</td><td style="text-align:right;">14 mo</td><td></td></tr>';
    html += '</tbody></table>';

    html += '<div style="font-weight: 700; color: #0f172a; margin-bottom: 8px;">Bull Markets</div>';
    html += '<table class="stock-table" style="font-size: 12px; margin-bottom: 12px;"><thead><tr><th style="text-align:left;">Period</th><th style="text-align:right;">Start</th><th style="text-align:right;">End</th><th style="text-align:right;">Gain</th><th style="text-align:right;">Duration</th><th style="text-align:left;">Driver</th></tr></thead><tbody>';
    html += '<tr><td>1957-61</td><td style="text-align:right;">39</td><td style="text-align:right;">72</td><td style="text-align:right;color:#10b981;">+86%</td><td style="text-align:right;">50 mo</td><td>Post-recession recovery, space race spending</td></tr>';
    html += '<tr><td>1962-66</td><td style="text-align:right;">52</td><td style="text-align:right;">94</td><td style="text-align:right;color:#10b981;">+80%</td><td style="text-align:right;">44 mo</td><td>Kennedy tax cuts, economic expansion</td></tr>';
    html += '<tr><td>1966-68</td><td style="text-align:right;">73</td><td style="text-align:right;">108</td><td style="text-align:right;color:#10b981;">+48%</td><td style="text-align:right;">26 mo</td><td>Great Society spending, consumer boom</td></tr>';
    html += '<tr><td>1970-73</td><td style="text-align:right;">69</td><td style="text-align:right;">120</td><td style="text-align:right;color:#10b981;">+74%</td><td style="text-align:right;">32 mo</td><td>Nifty Fifty rally, Nixon price controls</td></tr>';
    html += '<tr><td>1974-80</td><td style="text-align:right;">62</td><td style="text-align:right;">141</td><td style="text-align:right;color:#10b981;">+126%</td><td style="text-align:right;">74 mo</td><td>Post-Watergate recovery, energy boom</td></tr>';
    html += '<tr><td>1982-87</td><td style="text-align:right;">102</td><td style="text-align:right;">337</td><td style="text-align:right;color:#10b981;">+229%</td><td style="text-align:right;">60 mo</td><td>Volcker inflation victory, Reagan tax reform</td></tr>';
    html += '<tr><td>1987-00</td><td style="text-align:right;">224</td><td style="text-align:right;">1,527</td><td style="text-align:right;color:#10b981;">+582%</td><td style="text-align:right;">148 mo</td><td>Tech revolution, globalization, dot-com boom</td></tr>';
    html += '<tr><td>2002-07</td><td style="text-align:right;">777</td><td style="text-align:right;">1,565</td><td style="text-align:right;color:#10b981;">+101%</td><td style="text-align:right;">60 mo</td><td>Housing boom, easy credit, global growth</td></tr>';
    html += '<tr><td>2009-20</td><td style="text-align:right;">677</td><td style="text-align:right;">3,386</td><td style="text-align:right;color:#10b981;">+401%</td><td style="text-align:right;">131 mo</td><td>QE, zero rates, FAANG-led tech boom</td></tr>';
    html += '<tr><td>2020-22</td><td style="text-align:right;">2,237</td><td style="text-align:right;">4,797</td><td style="text-align:right;color:#10b981;">+114%</td><td style="text-align:right;">21 mo</td><td>Stimulus, reopening, meme stocks</td></tr>';
    html += '<tr><td>2022-Present</td><td style="text-align:right;">3,577</td><td style="text-align:right;">' + Math.round(MARKET.technical.sp500).toLocaleString() + '</td><td style="text-align:right;color:#10b981;">+' + Math.round((MARKET.technical.sp500 / 3577 - 1) * 100) + '%</td><td style="text-align:right;">Ongoing</td><td>AI revolution, Mag 7, rate cut hopes</td></tr>';
    html += '<tr style="background:#f8fafc;font-weight:600;"><td>Median</td><td></td><td></td><td style="text-align:right;color:#10b981;">+107%</td><td style="text-align:right;">50 mo</td><td></td></tr>';
    html += '</tbody></table>';

    html += '<p style="font-size: 13px; color: #64748b; line-height: 1.6;">Source: S&P 500 price data, 1957-present. Bear market = 20%+ decline from peak to trough. Bull market = trough to next peak. Duration is peak-to-trough for bears, trough-to-peak for bulls. The current bull market (2022-present) is ongoing and included in the tally.</p>';
    html += '</div>';

    // Card 8: Pullback Detail Tables (auto-generated from pullback engine)
    html += '<div class="card"><div class="card-title">Correction History — Meaningful &amp; Beyond Normal (S&amp;P 500, 1957–Present)</div>';
    html += '<p style="font-size: 13px; color: #64748b; margin-bottom: 14px;">These tables are auto-generated from the pullback engine and update with each nightly refresh. Bear markets (20%+) are listed in the table above.</p>';

    // Helper to format pullback duration
    function fmtPbDur(days) {
        if (!days) return '—';
        var months = Math.round(days / 21);
        if (months < 1) return Math.round(days / 5) + ' wks';
        return months + ' mo';
    }

    // Trigger lookup for meaningful and beyond normal corrections
    var correctionTriggers = {
        '1959': 'Steel strike, recession fears',
        '1967': 'Vietnam War costs, rising interest rates',
        '1983': 'Debt crisis in Latin America, Fed raising rates',
        '1989': 'Failed airline buyout triggered a sell-off',
        '1997': 'Currency crisis in Asia spread to U.S. markets',
        '1999': 'Fed raising rates, worries about Y2K computer bug',
        '2015': 'China economy slowing, oil prices crashing, Fed starting to raise rates',
        '2018-01': 'Inflation scare, bets against volatility blew up causing a chain reaction',
        '1990-07': 'Iraq invaded Kuwait, oil prices spiked, savings & loan bank failures',
        '1998': 'Russia defaulted on its debt, a giant hedge fund nearly collapsed',
        '2018-09': 'Fed kept raising rates, U.S.-China trade war escalating',
        '2025': 'Tariff escalation, concerns about AI stock valuations',
    };
    function getTrigger(dateStr) {
        for (var key in correctionTriggers) {
            if (dateStr.indexOf(key) >= 0) return correctionTriggers[key];
        }
        return '';
    }

    // Meaningful (10-15%)
    var meaningfulDetails = (PULLBACK_STATS.tiers && PULLBACK_STATS.tiers.meaningful && PULLBACK_STATS.tiers.meaningful.details) || [];
    html += '<div style="font-weight: 700; color: #f59e0b; margin-bottom: 8px; margin-top: 16px;">Meaningful Corrections (10-15%) — ' + meaningfulDetails.length + ' since 1957</div>';
    html += '<table class="stock-table" style="font-size: 12px; margin-bottom: 20px;"><thead><tr><th style="text-align:left;">Peak Date</th><th style="text-align:left;">Trough Date</th><th style="text-align:right;">Peak</th><th style="text-align:right;">Trough</th><th style="text-align:right;">Decline</th><th style="text-align:right;">Duration</th><th style="text-align:left;">Trigger</th></tr></thead><tbody>';
    meaningfulDetails.forEach(function(pb) {
        html += '<tr><td>' + fmtAsOf(pb.start) + '</td><td>' + fmtAsOf(pb.trough) + '</td><td style="text-align:right;">' + Math.round(pb.peak).toLocaleString() + '</td><td style="text-align:right;">' + Math.round(pb.low).toLocaleString() + '</td><td style="text-align:right;color:#f59e0b;font-weight:600;">' + pb.mag + '%</td><td style="text-align:right;">' + fmtPbDur(pb.dur) + '</td><td>' + getTrigger(pb.start) + '</td></tr>';
    });
    html += '</tbody></table>';

    // Beyond Normal (15-20%)
    var beyondDetails = (PULLBACK_STATS.tiers && PULLBACK_STATS.tiers.beyond_normal && PULLBACK_STATS.tiers.beyond_normal.details) || [];
    html += '<div style="font-weight: 700; color: #f97316; margin-bottom: 8px;">Beyond Normal Corrections (15-20%) — ' + beyondDetails.length + ' since 1957</div>';
    html += '<table class="stock-table" style="font-size: 12px; margin-bottom: 12px;"><thead><tr><th style="text-align:left;">Peak Date</th><th style="text-align:left;">Trough Date</th><th style="text-align:right;">Peak</th><th style="text-align:right;">Trough</th><th style="text-align:right;">Decline</th><th style="text-align:right;">Duration</th><th style="text-align:left;">Trigger</th></tr></thead><tbody>';
    beyondDetails.forEach(function(pb) {
        html += '<tr><td>' + fmtAsOf(pb.start) + '</td><td>' + fmtAsOf(pb.trough) + '</td><td style="text-align:right;">' + Math.round(pb.peak).toLocaleString() + '</td><td style="text-align:right;">' + Math.round(pb.low).toLocaleString() + '</td><td style="text-align:right;color:#f97316;font-weight:600;">' + pb.mag + '%</td><td style="text-align:right;">' + fmtPbDur(pb.dur) + '</td><td>' + getTrigger(pb.start) + '</td></tr>';
    });
    html += '</tbody></table>';

    html += '<p style="font-size: 13px; color: #64748b; line-height: 1.6;">Source: S&P 500 daily price data, 1957-present. These tables auto-update with each nightly pipeline refresh.</p>';
    html += '<div style="margin-top: 12px; padding: 14px 18px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;">';
    html += '<div style="font-size: 13px; color: #64748b; line-height: 1.7;"><strong style="color: #475569;">How we count pullbacks:</strong> This scorecard counts one pullback per peak-to-trough cycle — a new pullback is not counted until the market fully recovers above its prior high. This gives ' + (PULLBACK_STATS.total || 62) + ' distinct 5%+ pullbacks since ' + (PULLBACK_STATS.start_year || 1957) + '. Some studies use a broader method that counts every distinct 5%+ slide, including intermediate dips within larger declines where the market bounces and slides repeatedly. That approach produces 130+ episodes because a single bear market can contain multiple 5%+ drops (for example, the 2022 bear market alone had 7 separate 5%+ slides). Both methods are valid — we use the traditional method here because it produces cleaner per-tier statistics and avoids double-counting declines that are part of the same larger move.</div>';
    html += '</div>';
    html += '</div>';

    // Card 9: Delisting Tracker
    html += '<div class="card"><div class="card-title">Delisting Tracker</div>';
    html += '<p style="font-size: 13px; color: #64748b; margin-bottom: 14px;">Tickers in your universe that have not returned price data for 5+ consecutive days. These may have been acquired, merged, delisted, or renamed. Review weekly and remove any confirmed delistings from <code style="background:#f1f5f9;padding:2px 6px;border-radius:4px;">tickers.csv</code>.</p>';

    if (PENDING_REMOVAL.length === 0) {
        html += '<div style="padding: 16px 20px; background: #f0fdf4; border-radius: 8px; border: 1px solid #a7f3d0;"><div style="font-size: 14px; color: #166534;"><strong>✓ Nothing to review.</strong> All tickers in your universe are returning price data.</div></div>';
    } else {
        html += '<table class="stock-table" style="font-size: 13px;"><thead><tr><th style="text-align:left;">Ticker</th><th style="text-align:right;">Days Missing</th><th style="text-align:left;">First Skipped</th><th style="text-align:left;">Likely Reason</th></tr></thead><tbody>';
        PENDING_REMOVAL.forEach(function(p) {
            var reason = p.daysMissing >= 14 ? 'Likely delisted/acquired' : p.daysMissing >= 10 ? 'Probably delisted' : 'Possibly delisted — verify';
            var reasonColor = p.daysMissing >= 14 ? '#ef4444' : p.daysMissing >= 10 ? '#f97316' : '#f59e0b';
            html += '<tr>';
            html += '<td style="font-family: JetBrains Mono, monospace; font-weight: 700; color: #0f172a;">' + p.ticker + '</td>';
            html += '<td style="text-align:right; font-family: JetBrains Mono, monospace; font-weight: 600;">' + p.daysMissing + '</td>';
            html += '<td>' + fmtAsOf(p.firstSkipped) + '</td>';
            html += '<td style="color:' + reasonColor + '; font-weight:600;">' + reason + '</td>';
            html += '</tr>';
        });
        html += '</tbody></table>';
        html += '<div style="margin-top: 14px; padding: 14px 18px; background: #fffbeb; border-radius: 8px; border: 1px solid #fde68a;">';
        html += '<div style="font-size: 13px; color: #92400e; line-height: 1.6;"><strong>How to remove a ticker:</strong> Open <code>tickers.csv</code> in your project folder, delete the row, and save. The next nightly refresh will skip it automatically. You can verify a ticker is dead by searching it on finance.yahoo.com — if the page shows "Symbol Lookup" or redirects, it has been delisted.</div>';
        html += '</div>';
    }
    html += '</div>';

    // Card 10: Disclaimer
    html += '<div class="card"><div class="card-title">Disclaimer</div>';
    html += '<p style="font-size: 14px; color: #64748b; line-height: 1.6; padding: 12px; background: #fffbeb; border-radius: 8px; border: 1px solid #fde68a;">This dashboard is for educational and informational purposes only. It is not investment advice. Past performance does not guarantee future results. The indicators presented are historical patterns and should never be the sole basis for investment decisions. Always consult with a qualified financial advisor before making investment decisions.</p>';
    html += '</div>';

    return html;
}

// ============================================================================
// EXPLAIN POPUPS
// ============================================================================

var EXPLANATIONS = {
    trend: {
        title: 'Market Trend',
        body: '<p><strong>What it shows:</strong> Whether the stock market is in an uptrend, downtrend, or mixed.</p>' +
            '<p><strong>How it is calculated:</strong></p>' +
            '<ul style="margin:8px 0 8px 20px;">' +
            '<li><strong>Positive</strong> — S&P 500 is above both its 4-year moving average AND 150-day moving average. Both long-term and intermediate trends are up.</li>' +
            '<li><strong>Neutral</strong> — S&P 500 is above one average but below the other. The trend is mixed.</li>' +
            '<li><strong>Negative</strong> — S&P 500 is below both averages. Both long-term and intermediate trends are down.</li>' +
            '</ul>' +
            '<p><strong>Current reading:</strong> S&P 500 at ' + (typeof MARKET !== 'undefined' ? MARKET.technical.sp500.toLocaleString() : '') + ' vs 4-Year MA at ' + (typeof MARKET !== 'undefined' ? MARKET.technical.sp500MA4yr.toLocaleString() : '') + ' and 150-Day MA at ' + (typeof MARKET !== 'undefined' ? MARKET.technical.sp500MA150.toLocaleString() : '') + '.</p>' +
            '<p><strong>Why it matters:</strong> The trend is the single most important factor for momentum investors. When price is above its moving averages, the odds favor being invested. When below, the odds favor caution.</p>'
    },
    breadth: {
        title: 'Market Breadth',
        body: '<p><strong>What it shows:</strong> What percentage of stocks in our universe are trading above their 150-day moving average.</p>' +
            '<p><strong>How it is calculated:</strong> For each of the ~1,200 stocks tracked, we check if the current price is above its individual 150-day moving average. The percentage that are above is the breadth reading.</p>' +
            '<ul style="margin:8px 0 8px 20px;">' +
            '<li><strong>Above 60%</strong> — Healthy. Broad participation, many stocks are in uptrends.</li>' +
            '<li><strong>40-60%</strong> — Narrow. The market rally is being driven by fewer stocks.</li>' +
            '<li><strong>Below 40%</strong> — Weak. Most stocks are in downtrends even if indices look OK.</li>' +
            '<li><strong>Below 20%</strong> — Oversold. Historically a capitulation signal.</li>' +
            '</ul>' +
            '<p><strong>Why it matters:</strong> A rising market with narrow breadth is fragile — it depends on a few leaders. Broad breadth means the rally has wide support and is more durable.</p>'
    },
    earnings: {
        title: 'Earnings Growth',
        body: '<p><strong>What it shows:</strong> The year-over-year earnings growth rate for S&P 500 companies.</p>' +
            '<p><strong>How it is calculated:</strong> This is the blended EPS growth rate — comparing the current quarter earnings to the same quarter one year ago, across all S&P 500 companies that have reported. Data is sourced from SEC EDGAR filings when available, with FactSet manual fallbacks.</p>' +
            '<ul style="margin:8px 0 8px 20px;">' +
            '<li><strong>Above 5%</strong> — Healthy. Companies are growing profits, which supports stock prices.</li>' +
            '<li><strong>0-5%</strong> — Modest. Growth is positive but not strong enough to drive multiple expansion.</li>' +
            '<li><strong>Below 0%</strong> — Contracting. An earnings recession typically weighs on stocks.</li>' +
            '</ul>' +
            '<p><strong>Why it matters:</strong> Over the long run, stock prices follow earnings. When companies are making more money, stocks tend to rise. When earnings contract, stocks typically fall.</p>'
    },
    valuation: {
        title: 'Valuation (Forward P/E)',
        body: '<p><strong>What it shows:</strong> How expensive the stock market is relative to expected future earnings.</p>' +
            '<p><strong>How it is calculated:</strong> Forward P/E = Current S&P 500 price ÷ estimated earnings per share over the next 12 months. This is sourced from FactSet consensus analyst estimates (manual input, updated quarterly).</p>' +
            '<ul style="margin:8px 0 8px 20px;">' +
            '<li><strong>Below 18x</strong> — Cheap. Stocks are priced attractively relative to earnings.</li>' +
            '<li><strong>18-22x</strong> — Fair. Normal range, though on the higher end historically.</li>' +
            '<li><strong>Above 22x</strong> — Expensive. Less margin for error — if earnings disappoint, stocks can drop sharply.</li>' +
            '</ul>' +
            '<p><strong>The 10-year average</strong> is around 18.9x, so anything above that means you are paying a premium.</p>' +
            '<p><strong>Why it matters:</strong> Valuation does not predict short-term moves, but it strongly predicts long-term returns. Buying at low P/E ratios historically produces better 10-year returns than buying at high P/E ratios.</p>'
    },
    healthScore: {
        title: 'Health Score',
        body: '<p><strong>What it shows:</strong> An overall reading of market conditions across 18 indicators.</p>' +
            '<p><strong>How it is calculated:</strong> 18 binary (yes/no) indicators across three categories, each worth 5 points:</p>' +
            '<ul style="margin:8px 0 8px 20px;">' +
            '<li><strong>Macro (8 indicators, 40 pts)</strong> — Labor market, GDP, inflation, credit spreads, consumer confidence, mortgage rates, yield curve, ISM manufacturing</li>' +
            '<li><strong>Fundamental (5 indicators, 25 pts)</strong> — Earnings growth, profit margins, analyst revisions, valuation (P/E), free cash flow yield</li>' +
            '<li><strong>Technical (5 indicators, 25 pts)</strong> — Long-term trend, medium-term trend, breadth, VIX, put/call ratio</li>' +
            '</ul>' +
            '<p><strong>Score bands:</strong></p>' +
            '<ul style="margin:8px 0 8px 20px;">' +
            '<li>80-100% = Bullish</li>' +
            '<li>60-80% = Cautiously Optimistic</li>' +
            '<li>40-60% = Cautious</li>' +
            '<li>25-40% = Defensive</li>' +
            '<li>0-25% = Risk Off</li>' +
            '</ul>' +
            '<p><strong>Why equal weight?</strong> Simplicity and transparency. Each indicator gets an equal vote. No hidden biases.</p>'
    }
};

function showExplain(key) {
    var exp = EXPLANATIONS[key];
    if (!exp) return;
    var html = '<div style="padding: 4px 0;">';
    html += '<div style="font-family: Fraunces, serif; font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 12px;">' + exp.title + '</div>';
    html += '<div style="font-size: 14px; color: #475569; line-height: 1.7;">' + exp.body + '</div>';
    html += '</div>';
    document.getElementById('explainBody').innerHTML = html;
    document.getElementById('explainModal').classList.add('active');
}

function closeExplain(e) {
    if (e && e.target.id !== 'explainModal') return;
    document.getElementById('explainModal').classList.remove('active');
}

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab-content').forEach(function(el) { el.classList.remove('active'); });
    document.querySelectorAll('.tab-btn').forEach(function(el) { el.classList.remove('active'); });
    document.getElementById(tab).classList.add('active');
    // Highlight the clicked button
    var btns = document.querySelectorAll('.tab-btn');
    btns.forEach(function(btn) {
        if (btn.textContent.toLowerCase().indexOf(tab === 'pulse' ? 'market' : tab === 'sectors' ? 'sector' : tab === 'industries' ? 'industr' : tab === 'screener' ? 'stock' : tab === 'research' ? 'company' : 'sources') >= 0) {
            btn.classList.add('active');
        }
    });
    // Render tab content on demand
    if (tab === 'sources') {
        document.getElementById('sourcesContent').innerHTML = renderSourcesTab();
    }
    if (tab === 'research') {
        document.getElementById('researchContent').innerHTML = renderResearchTab();
    }
}

function switchSubtab(parent, subtab, btn) {
    const prefix = parent + '-';
    document.querySelectorAll('.subtab-content').forEach(function(el) {
        if (el.id && el.id.startsWith(prefix)) el.classList.remove('active');
    });
    document.querySelectorAll('.subtab-btn').forEach(function(el) { el.classList.remove('active'); });
    document.getElementById(prefix + subtab).classList.add('active');
    if (btn) btn.classList.add('active');
}

</script>

</body>
</html>
'''

# ============================================================================
# Write Output
# ============================================================================

OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)

with open(OUTPUT_HTML, 'w') as f:
    f.write(html_content)

print('Dashboard built successfully: ' + str(OUTPUT_HTML))
