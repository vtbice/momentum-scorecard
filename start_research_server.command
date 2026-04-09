#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  PROSPER MOMENTUM — Start Research Server
# ═══════════════════════════════════════════════════════════
#  Double-click this file to start the research server.
#  Then open http://localhost:8765 in your browser.
#
#  Type any ticker and hit Enter to pull live data.
#  Press Ctrl+C or close this window to stop.
# ═══════════════════════════════════════════════════════════

cd "$(dirname "$0")"

# Fix SSL certificates
export SSL_CERT_FILE="/etc/ssl/cert.pem"
export REQUESTS_CA_BUNDLE="/etc/ssl/cert.pem"
export CURL_CA_BUNDLE="/etc/ssl/cert.pem"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Starting Research Server..."
echo "═══════════════════════════════════════════════════"
echo ""

# Open the browser automatically after a short delay
(sleep 2 && open "http://localhost:8765") &

# Start the server
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 research_server.py
