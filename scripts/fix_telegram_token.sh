#!/bin/bash

# Script to fix Telegram bot token issue on VPS
# This script updates the .env file with the correct token and restarts the bot

echo "=== TELEGRAM TOKEN FIX SCRIPT ==="
echo "Fixing Telegram bot token configuration..."

# Navigate to project directory
cd /opt/TELEGLAS

# Backup current .env file
if [ -f ".env" ]; then
    echo "Backing up current .env file..."
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
fi

# Update with correct token
echo "Updating .env file with correct Telegram bot token..."

# Create new .env with correct token
cat > .env << 'EOF'
# Production Configuration - TELEGLAS Bot

# Core Bot Configuration
TELEGRAM_BOT_TOKEN=7659959497:AAGwJJvKRfp44MDZxHcjaJdAwBtnDtmZ8SI
TELEGRAM_ADMIN_CHAT_ID=5899681906
TELEGRAM_ALERT_CHANNEL_ID=5899681906

# Access Control
WHITELISTED_USERS=5899681906

# Feature Flags
ENABLE_WHALE_ALERTS=true
ENABLE_BROADCAST_ALERTS=false
ENABLE_MONITORING=false

# API Configuration
COINGLASS_API_KEY=8794ae1bac584fda9841b5c8bf273d3d
API_CALLS_PER_MINUTE=60

# Thresholds
WHALE_TRANSACTION_THRESHOLD_USD=500000
LIQUIDATION_THRESHOLD_USD=1000000
FUNDING_RATE_THRESHOLD=0.01

# Timing (seconds)
WHALE_POLL_INTERVAL=30
LIQUIDATION_POLL_INTERVAL=60
FUNDING_RATE_POLL_INTERVAL=300

# Database Configuration
DATABASE_URL=sqlite:///data/teleglas.db

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/cryptosat.log
EOF

echo "Environment file updated successfully!"

# Stop any running bot processes
echo "Stopping any running bot processes..."
pkill -f "python.*main.py" || true
pkill -f "telegraf" || true

# Wait a moment
sleep 2

# Test the new token
echo "Testing new Telegram bot token..."
python3 -c "
import asyncio
import sys
sys.path.append('/opt/TELEGLAS')
from handlers.telegram_bot import telegram_bot

async def test_token():
    try:
        bot_info = await telegram_bot.bot.get_me()
        print(f'Success! Bot info: @{bot_info.username} ({bot_info.first_name})')
        return True
    except Exception as e:
        print(f'Error testing token: {e}')
        return False

result = asyncio.run(test_token())
sys.exit(0 if result else 1)
"

if [ $? -eq 0 ]; then
    echo "✅ Token test successful! Starting bot..."
    
    # Start the bot
    source venv/bin/activate
    nohup python main.py > logs/bot.log 2>&1 &
    
    echo "Bot started with new token!"
    echo "Checking bot status..."
    sleep 3
    
    # Check if bot is running
    if pgrep -f "python.*main.py" > /dev/null; then
        echo "✅ Bot is running successfully!"
        echo "Process ID: $(pgrep -f 'python.*main.py')"
    else
        echo "❌ Bot failed to start. Check logs:"
        tail -20 logs/bot.log
    fi
else
    echo "❌ Token test failed. Please check:"
    echo "1. Token is correct and active"
    echo "2. Bot is not banned by Telegram"
    echo "3. Network connectivity to Telegram API"
fi

echo "=== TOKEN FIX COMPLETE ==="
