#!/bin/bash
# Double-click this to generate today's Market Pulse deck with live data.
# Opens the resulting .pptx when done.

set -e
cd "$(dirname "$0")/presentations"

echo "════════════════════════════════════════════════════"
echo "  Momentum Scorecard — Market Pulse Deck Generator"
echo "════════════════════════════════════════════════════"
echo ""

# Make sure pptxgenjs is available (symlink to the /tmp install we already have, or install fresh)
if [ ! -d "node_modules" ]; then
    if [ -d "/tmp/momentum_deck/node_modules" ]; then
        echo "→ Linking pptxgenjs from /tmp/momentum_deck..."
        ln -sf /tmp/momentum_deck/node_modules node_modules
    else
        echo "→ Installing pptxgenjs (first-run only)..."
        npm install --silent pptxgenjs
    fi
fi

python3 build_deck.py
RC=$?

if [ $RC -eq 0 ]; then
    # Open the most recent deck
    LATEST=$(ls -t Market_Pulse_Overview_*.pptx 2>/dev/null | head -1)
    if [ -n "$LATEST" ]; then
        echo ""
        echo "→ Opening $LATEST..."
        open "$LATEST"
    fi
fi

echo ""
echo "Press any key to close this window..."
read -n 1 -s
