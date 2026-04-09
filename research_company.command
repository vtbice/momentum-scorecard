#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  PROSPER MOMENTUM — Research a Company
# ═══════════════════════════════════════════════════════════
#  Double-click this file to research any company.
#  Type a ticker (like NVDA, AAPL) for public companies,
#  or a company name (like "Acme Corp") for private ones.
#
#  The research page will be saved in the research/ folder.
# ═══════════════════════════════════════════════════════════

cd "$(dirname "$0")"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  PROSPER MOMENTUM — Company Research"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  Enter a ticker symbol for a public company (e.g., NVDA)"
echo "  or a company name for a private company (e.g., Acme Corp)"
echo ""
read -p "  Company: " COMPANY

if [ -z "$COMPANY" ]; then
    echo ""
    echo "  ❌ No company entered. Exiting."
    echo ""
    read -p "Press Enter to close..."
    exit 1
fi

echo ""

# Fix SSL certificates
export SSL_CERT_FILE="/etc/ssl/cert.pem"
export REQUESTS_CA_BUNDLE="/etc/ssl/cert.pem"
export CURL_CA_BUNDLE="/etc/ssl/cert.pem"

# Run the research script
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 research.py "$COMPANY"

# Open the generated file in the browser
TICKER=$(echo "$COMPANY" | tr '[:lower:]' '[:upper:]' | tr -d ' ')
if [ -f "research/${TICKER}.html" ]; then
    echo ""
    echo "🌐 Opening in browser..."
    open "research/${TICKER}.html"
elif ls research/_private_*.html 1>/dev/null 2>&1; then
    LATEST=$(ls -t research/_private_*.html | head -1)
    echo ""
    echo "🌐 Opening in browser..."
    open "$LATEST"
fi

echo ""
read -p "Press Enter to close..."
