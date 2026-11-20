#!/bin/bash
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$BASE_DIR/bot.pid"
LOG_FILE="$BASE_DIR/bot.log"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "🟢 Bharat Bazaar Bot is RUNNING (PID: $PID)"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Recent Logs:"
        tail -n 15 "$LOG_FILE"
        exit 0
    fi
fi

PID=$(pgrep -f "python3.*bharat-bazaar-bot/bot.py")
if [ -n "$PID" ]; then
    echo "🟢 Bharat Bazaar Bot is RUNNING (PID: $PID)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Recent Logs:"
    tail -n 15 "$LOG_FILE"
else
    echo "🔴 Bharat Bazaar Bot is STOPPED."
fi
