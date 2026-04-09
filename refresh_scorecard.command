#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  PROSPER MOMENTUM — One-Click Scorecard Refresh
# ═══════════════════════════════════════════════════════════
#  Double-click this file on your Mac to refresh all 886 stocks.
#  It takes about 15-20 minutes — grab a coffee while it runs.
#
#  What it does:
#    1. Activates the Python virtual environment
#    2. Sets your FRED API key
#    3. Runs the full data pipeline
#    4. Outputs fresh scorecard_data.json
# ═══════════════════════════════════════════════════════════

# Navigate to the StockAnalysis folder
cd "$(dirname "$0")"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  PROSPER MOMENTUM — Scorecard Refresh"
echo "  $(date '+%B %d, %Y at %I:%M %p')"
echo "═══════════════════════════════════════════════════"
echo ""

# Check for virtual environment
if [ -d ".venv" ]; then
    echo "✅ Found virtual environment"
    source .venv/bin/activate
else
    echo "⚠️  No .venv found — using system Python"
    echo "   If you get import errors, run:"
    echo "   pip3 install yfinance fredapi pandas numpy"
    echo ""
fi

# Load API keys from .env file (keeps secrets out of source code)
if [ -f "$(dirname "$0")/.env" ]; then
    export $(grep -v '^#' "$(dirname "$0")/.env" | xargs)
    echo "✅ Loaded API keys from .env"
else
    echo "⚠️  No .env file found — API keys may be missing"
    echo "   Create a .env file with FRED_API_KEY and NASDAQ_DATA_LINK_KEY"
fi

# Fix SSL certificates — tells Python and curl where to find trusted website list
export SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())")
export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
export CURL_CA_BUNDLE="$SSL_CERT_FILE"
echo "🔐 SSL certificates: $SSL_CERT_FILE"

# Run the pipeline
echo "🚀 Starting pipeline — this takes 15-20 minutes for 886 stocks..."
echo "   (You can minimize this window and come back later)"
echo ""

python3 prosper_data_pipeline.py

# Auto-bake fresh data into the dashboard HTML
echo ""
echo "📊 Updating Momentum Scorecard dashboard..."
DASHBOARD_DIR="$(dirname "$0")/../Dashboards/Momentum Scorecard"
if [ -f "$(dirname "$0")/build_dashboard.py" ]; then
    python3 "$(dirname "$0")/build_dashboard.py" && echo "✅ Dashboard updated with fresh data" || echo "⚠️  Dashboard update failed — scorecard_data.json is still fresh"
else
    echo "⚠️  build_dashboard.py not found — dashboard not updated"
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Done! You can close this window."
echo "═══════════════════════════════════════════════════"
echo ""

# Keep the window open so you can see the results
read -p "Press Enter to close..."
