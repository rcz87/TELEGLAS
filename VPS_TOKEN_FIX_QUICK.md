# VPS Token Fix - Quick Solution

## Masalah
VPS masih menggunakan token lama: `7983466046:AAEdnC5_6NsmSPCJwvrN6JusysM4ubvNXIg`
Padahal token yang benar sudah digunakan di lokal: `7659959497:AAGwJJvKRfp44MDZxHcjaJdAwBtnDtmZ8SI`

## Quick Fix - Jalankan di VPS

```bash
cd /opt/TELEGLAS

# Backup .env lama
cp .env .env.backup.old

# Update .env dengan token yang benar (sudah digunakan di lokal)
cat > .env << 'EOF'
# Production Configuration - TELEGLAS Bot
# Token yang sama dengan yang digunakan di lokal

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

# Stop bot lama
pkill -f "python.*main.py"

# Start bot dengan token baru
source venv/bin/activate
nohup python main.py > logs/bot.log 2>&1 &

# Cek status
sleep 3
if pgrep -f 'python.*main.py' > /dev/null; then
    echo "✅ Bot running dengan token yang benar!"
    tail -10 logs/bot.log
else
    echo "❌ Bot failed, cek logs:"
    tail -20 logs/bot.log
fi
```

## Verification
Setelah fix, cek log:
```bash
tail -f logs/cryptosat.log
```

Bot should start successfully tanpa token error.

## Token Info
- **Token Benar:** `7659959497:AAGwJJvKRfp44MDZxHcjaJdAwBtnDtmZ8SI` (sudah digunakan di lokal)
- **Token Lama:** `7983466046:AAEdnC5_6NsmSPCJwvrN6JusysM4ubvNXIg` (harus diganti)
