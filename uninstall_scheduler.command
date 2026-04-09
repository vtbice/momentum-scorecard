#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  UNINSTALL — Momentum Scorecard Daily Scheduler
# ═══════════════════════════════════════════════════════════
#  Double-click this file to stop automatic daily refreshes.
#  You can always turn it back on with install_scheduler.command.
# ═══════════════════════════════════════════════════════════

PLIST_NAME="com.prosper.momentum-refresh.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Removing Momentum Scorecard Daily Scheduler"
echo "═══════════════════════════════════════════════════"
echo ""

if [ -f "$PLIST_DEST" ]; then
    launchctl unload "$PLIST_DEST" 2>/dev/null
    rm "$PLIST_DEST"
    echo "✅ Scheduler has been removed"
    echo "   Automatic refreshes are now OFF."
else
    echo "ℹ️  No scheduler found — it wasn't installed."
fi

echo ""
echo "  To re-enable, double-click install_scheduler.command"
echo ""

read -p "Press Enter to close..."
