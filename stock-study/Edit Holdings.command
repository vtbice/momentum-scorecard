#!/bin/bash
#
# Edit Holdings — double-click from Finder to launch the City of the Future
# admin server. A Terminal window will open, the admin server will start, and
# your browser will automatically open to the local admin site where you can
# add/remove tickers from any fund or the watchlist with clickable buttons.
#
# When you're done, just close the Terminal window (or press Ctrl+C) — the
# server stops cleanly and the regular static site is unaffected.
#

# Always run from the directory this file lives in
cd "$(dirname "$0")"

echo ""
echo "  City of the Future — Admin Mode"
echo "  ═══════════════════════════════════"
echo ""
echo "  Starting the local admin server so you can add and remove"
echo "  tickers by clicking buttons on the page."
echo ""
echo "  Your browser will open automatically in a moment."
echo ""
echo "  ▶ When you're done, just close this Terminal window."
echo ""

# Run the admin server — this blocks until Ctrl+C or window close
python3 scripts/admin.py
