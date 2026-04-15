#!/bin/bash
#
# Stop Edit Mode — shuts down the background admin server that was
# started by "Edit Holdings.command". Double-click from Finder.
#

PID_FILE="/tmp/city-future-admin.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping admin server (PID $PID)..."
        kill "$PID"
        rm -f "$PID_FILE"
        echo "Stopped."
    else
        echo "Admin server was not running (stale PID file). Cleaning up."
        rm -f "$PID_FILE"
    fi
else
    # Fallback: try to kill any python process running admin.py
    PIDS=$(pgrep -f "python.*admin\.py" || true)
    if [ -n "$PIDS" ]; then
        echo "Stopping admin server(s): $PIDS"
        kill $PIDS
        echo "Stopped."
    else
        echo "Admin server is not running."
    fi
fi

# Auto-close this Terminal window
osascript -e 'tell application "Terminal" to close (every window whose name contains "Stop Edit Mode")' > /dev/null 2>&1 &

sleep 1
exit 0
