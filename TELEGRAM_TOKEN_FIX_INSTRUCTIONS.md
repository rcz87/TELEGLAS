# Telegram Bot Token Fix Instructions

## Problem
Bot di VPS menggunakan token yang salah:
- **Token Salah:** `7983466046:AAEdnC5_6NsmSPCJwvrN6JusysM4ubvNXIg`
- **Token Benar:** `7659959497:AAGwJJvKRfp44MDZxHcjaJdAwBtnDtmZ8SI`

## Quick Fix Steps

### Option 1: Run the Automated Script
```bash
cd /opt/TELEGLAS
chmod +x scripts/fix_telegram_token.sh
./scripts/fix_telegram_token.sh
```

### Option 2: Manual Fix
```bash
cd /opt/TELEGLAS

# 1. Backup current .env
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# 2. Update .env with correct token
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

# 3. Stop running processes
pkill -f "python.*main.py" || true
sleep 2

# 4. Test new token
source venv/bin/activate
python3 -c "
import asyncio
from handlers.telegram_bot import telegram_bot

async def test():
    try:
        info = await telegram_bot.bot.get_me()
        print(f'✅ Success! Bot: @{info.username}')
    except Exception as e:
        print(f'❌ Error: {e}')

asyncio.run(test())
"

# 5. Restart bot
nohup python main.py > logs/bot.log 2>&1 &

# 6. Check status
sleep 3
if pgrep -f 'python.*main.py' > /dev/null; then
    echo "✅ Bot is running!"
    tail -10 logs/bot.log
else
    echo "❌ Bot failed to start"
    tail -20 logs/bot.log
fi
```

## Verification
Setelah fix, cek log untuk memastikan tidak ada token error:
```bash
tail -f logs/cryptosat.log
```

Bot should start successfully and respond to Telegram commands.

## If Still Fails
1. Cek apakah token benar-benar aktif di BotFather
2. Pastikan tidak ada API rate limit
3. Cek koneksi internet ke Telegram API
4. Restart server jika perlu
