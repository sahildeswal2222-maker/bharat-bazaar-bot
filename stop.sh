#!/bin/bash
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$BASE_DIR/bot.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "🛑 Stopping Bharat Bazaar Bot (PID: $PID)..."
        kill "$PID"
        sleep 1
        kill -9 "$PID" 2>/dev/null
        rm -f "$PID_FILE"
        echo "✅ Bot stopped."
        exit 0
    fi
fi

# Fallback check
PID=$(pgrep -f "python3.*bharat-bazaar-bot/bot.py")
if [ -n "$PID" ]; then
    echo "🛑 Killing stray bot process (PID: $PID)..."
    kill -9 $PID 2>/dev/null
    rm -f "$PID_FILE"
    echo "✅ Bot stopped."
else
    echo "ℹ️ Bot is not running."
    rm -f "$PID_FILE"
fi
