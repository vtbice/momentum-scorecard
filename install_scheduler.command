#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  INSTALL — Momentum Scorecard Daily Scheduler
# ═══════════════════════════════════════════════════════════
#  Double-click this file to set up automatic daily refreshes.
#  Your scorecard will update every night at 1:15 AM.
#
#  To stop it later, double-click uninstall_scheduler.command.
# ═══════════════════════════════════════════════════════════

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.prosper.momentum-refresh.plist"
PLIST_SOURCE="$PROJECT_DIR/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Installing Momentum Scorecard Daily Scheduler"
echo "═══════════════════════════════════════════════════"
echo ""

# Check that the plist file exists
if [ ! -f "$PLIST_SOURCE" ]; then
    echo "❌ Could not find $PLIST_NAME in the project folder."
    echo "   Make sure this script is in the same folder as the plist file."
    echo ""
    read -p "Press Enter to close..."
    exit 1
fi

# Create LaunchAgents folder if needed
mkdir -p "$HOME/Library/LaunchAgents"

# Create logs folder
mkdir -p "$PROJECT_DIR/logs"

# Unload old version if it exists
launchctl unload "$PLIST_DEST" 2>/dev/null

# Copy the plist to the LaunchAgents folder
cp "$PLIST_SOURCE" "$PLIST_DEST"
echo "✅ Copied scheduler config to ~/Library/LaunchAgents/"

# Load it
launchctl load "$PLIST_DEST"
echo "✅ Scheduler is now active"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  All set! Your scorecard will refresh every night"
echo "  at 1:15 AM automatically."
echo ""
echo "  To check if it's running:"
echo "    launchctl list | grep prosper"
echo ""
echo "  To see the last run's log:"
echo "    cat $PROJECT_DIR/logs/refresh_latest.log"
echo ""
echo "  To stop automatic refreshes:"
echo "    Double-click uninstall_scheduler.command"
echo "═══════════════════════════════════════════════════"
echo ""

read -p "Press Enter to close..."
