#!/bin/bash
BASE_DIR="/data/user/0/ai.antigem/files/home/projects/bharat-bazaar-bot"
cd "$BASE_DIR"

# Prevent Android CPU sleep
termux-wake-lock 2>/dev/null || true

# Kill existing instance if any
pkill -9 -f "python3.*bharat-bazaar-bot/bot\.py" 2>/dev/null || true
sleep 1

echo "============================================================"
echo "   🚀 Bharat Bazaar Bot 24/7 Started                        "
echo "============================================================"
echo "⚡ Bot Username: @BharatBazaarBot"
echo "⚡ Log File: $BASE_DIR/bot.log"
echo "============================================================"

nohup python3 -u "$BASE_DIR/bot.py" >> "$BASE_DIR/bot.log" 2>&1 &
disown
sleep 2

PID=$(pgrep -f "python3.*bharat-bazaar-bot/bot\.py")
if [ -n "$PID" ]; then
    echo "✅ Bot is successfully RUNNING in background! (PID: $PID)"
    echo "$PID" > "$BASE_DIR/bot.pid"
else
    echo "❌ Failed to start. Recent logs:"
    tail -n 10 "$BASE_DIR/bot.log"
fi
