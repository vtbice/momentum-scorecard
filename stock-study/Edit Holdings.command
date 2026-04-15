#!/bin/bash
#
# Edit Holdings — double-click from Finder to enable editing the
# City of the Future site. This:
#
#   1. Starts a local admin server in the background (detached — it
#      keeps running even after this Terminal window closes)
#   2. Opens your browser to the editable version of the site
#   3. Auto-closes this Terminal window
#
# If the admin server is already running, it skips step 1 and just
# opens the browser.
#
# To stop editing later, double-click "Stop Edit Mode.command".
#

cd "$(dirname "$0")"

ADMIN_URL="http://localhost:8765/index.html"
PID_FILE="/tmp/city-future-admin.pid"
LOG_FILE="/tmp/city-future-admin.log"

# Check if server is already running and responsive
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/index.html 2>/dev/null | grep -q "^200$"; then
    echo "Admin server already running — just opening the browser."
else
    echo "Starting admin server in the background..."
    # Detach from the terminal so it survives this window closing
    nohup python3 scripts/admin.py > "$LOG_FILE" 2>&1 &
    SERVER_PID=$!
    echo $SERVER_PID > "$PID_FILE"
    # Give it a moment to start up
    sleep 1.5
fi

# Open the browser
open "$ADMIN_URL"

# Close this Terminal window automatically — the server is detached so it keeps running
osascript -e 'tell application "Terminal" to close (every window whose name contains "Edit Holdings")' > /dev/null 2>&1 &

exit 0
