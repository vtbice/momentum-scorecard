#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  PROSPER MOMENTUM — Automated Daily Refresh
# ═══════════════════════════════════════════════════════════
#  This script runs automatically each night via macOS launchd.
#  It does the same thing as refresh_scorecard.command but
#  is designed to run unattended (no user interaction needed).
#
#  Logs are saved to: ~/Documents/momentum-scorecard/logs/
#  To check if it ran:  cat logs/refresh_latest.log
# ═══════════════════════════════════════════════════════════

# Navigate to the project folder
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Create logs folder if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Log file — keep the latest run plus a dated archive
LOG_FILE="$PROJECT_DIR/logs/refresh_latest.log"
ARCHIVE_LOG="$PROJECT_DIR/logs/refresh_$(date '+%Y-%m-%d').log"

# Start logging (everything printed goes to both screen and file)
exec > >(tee "$LOG_FILE") 2>&1

echo ""
echo "═══════════════════════════════════════════════════"
echo "  PROSPER MOMENTUM — Automated Daily Refresh"
echo "  $(date '+%B %d, %Y at %I:%M %p')"
echo "═══════════════════════════════════════════════════"
echo ""

# Load API keys from .env file
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
    echo "✅ Loaded API keys from .env"
else
    echo "❌ No .env file found — API keys missing, some data will use fallbacks"
fi

# Fix SSL certificates (use macOS system certs — the Python certifi bundle doesn't work with curl_cffi)
export SSL_CERT_FILE="/etc/ssl/cert.pem"
export REQUESTS_CA_BUNDLE="/etc/ssl/cert.pem"
export CURL_CA_BUNDLE="/etc/ssl/cert.pem"
echo "🔐 SSL certificates configured"

# Run the data pipeline
echo ""
echo "🚀 Starting data pipeline..."
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 "$PROJECT_DIR/prosper_data_pipeline.py"
PIPELINE_STATUS=$?

if [ $PIPELINE_STATUS -eq 0 ]; then
    echo ""
    echo "✅ Pipeline completed successfully"
else
    echo ""
    echo "❌ Pipeline failed with exit code $PIPELINE_STATUS"
fi

# Build the dashboard HTML
echo ""
echo "📊 Updating dashboard..."
if [ -f "$PROJECT_DIR/build_dashboard.py" ]; then
    /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 "$PROJECT_DIR/build_dashboard.py"
    if [ $? -eq 0 ]; then
        echo "✅ Dashboard updated"

        # Copy to root for GitHub Pages and push
        DASHBOARD_HTML="$PROJECT_DIR/../Dashboards/Momentum Scorecard/index.html"
        if [ -f "$DASHBOARD_HTML" ]; then
            cp "$DASHBOARD_HTML" "$PROJECT_DIR/index.html"
            cd "$PROJECT_DIR"
            git add index.html
            git commit -m "Auto-update dashboard $(date '+%Y-%m-%d')" 2>/dev/null
            git push origin main 2>/dev/null
            if [ $? -eq 0 ]; then
                echo "✅ GitHub Pages updated — live link refreshed"
            else
                echo "⚠️  Git push failed — dashboard is fresh locally but GitHub Pages not updated"
            fi
        fi
    else
        echo "⚠️  Dashboard update failed — scorecard_data.json is still fresh"
    fi
fi

# Clean up old logs (keep last 30 days)
find "$PROJECT_DIR/logs" -name "refresh_20*.log" -mtime +30 -delete 2>/dev/null

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Finished at $(date '+%I:%M %p')"
echo "═══════════════════════════════════════════════════"

# Copy to dated archive
cp "$LOG_FILE" "$ARCHIVE_LOG" 2>/dev/null
