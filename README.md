# 🛸 CryptoSat Bot - High-Frequency Trading Signals & Market Intelligence

**CryptoSat** is a sophisticated Telegram bot that provides real-time cryptocurrency trading signals and market intelligence powered by the CoinGlass API v4. The bot monitors massive liquidations, whale movements, and extreme funding rates to generate actionable trading signals.

## 🎯 Mission Directive

**Target:** High-Frequency Trading Signals & Market Intelligence  
**Source:** CoinGlass API v4  
**Objective:** Real-time detection of pump/dump signals through liquidations, whale movements, and funding rates.

## 🚀 Features

### 📊 Real-Time Monitoring
- **🔥 Liquidation Monitor**: Detects massive liquidations (> $1M) and generates pump/dump signals
- **🐋 Whale Watcher**: Tracks whale transactions (>$500K) from Hyperliquid
- **💰 Funding Rate Radar**: Identifies extreme funding rates for reversal opportunities

### 🤖 Telegram Interface
- **Private Bot**: Whitelist-based access control
- **Rich Commands**: `/liq`, `/sentiment`, `/whale`, `/subscribe`, etc.
- **Smart Alerts**: Channel broadcasting with confidence scores
- **Interactive UI**: Inline keyboards for easy subscription management

### 🛡️ Enterprise Features
- **Rate Limiting**: Intelligent API throttling to prevent 429 errors
- **Error Handling**: Comprehensive error recovery and logging
- **Data Persistence**: SQLite database for user subscriptions and caching
- **Health Monitoring**: Automatic service restart and health checks

## 📋 Quick Start

### 1. 📥 Prerequisites
- Docker & Docker Compose
- CoinGlass API Key
- Telegram Bot Token
- (Optional) Telegram Alert Channel ID

### 2. ⚙️ Configuration
```bash
# Clone the repository
git clone <repository-url>
cd cryptosat-bot

# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required Environment Variables:**
```env
# CoinGlass API
COINGLASS_API_KEY=your_coinglass_api_key

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_ADMIN_CHAT_ID=your_admin_chat_id
TELEGRAM_ALERT_CHANNEL_ID=your_alert_channel_id

# Security
WHITELISTED_USERS=123456789,987654321  # Optional
```

### 3. 🚀 Deployment
```bash
# Make deploy script executable
chmod +x scripts/deploy.sh

# Deploy the bot
./scripts/deploy.sh deploy
```

### 4. 📱 Bot Commands
```bash
/start     - Start bot and show welcome
/liq BTC    - Get liquidation data for Bitcoin
/sentiment  - Show Fear & Greed Index
/whale      - Display recent whale transactions
/subscribe BTC - Subscribe to Bitcoin alerts
/alerts     - View your subscriptions
/status      - Bot status and performance
```

## 🏗️ Architecture

### Phase 1: Architecture & Security ✅
- [x] API Credential Management
- [x] Rate Limit Strategy
- [x] SQLite Database Layer
- [x] Error Handling Framework

### Phase 2: Data Pipeline Integration ✅
- [x] CoinGlass API Wrapper
- [x] Real-time Endpoint Integration
- [x] Market Sentiment Data

### Phase 3: Intelligence & Alert Logic ✅
- [x] Liquidation Monitor (Pump/Dump Detection)
- [x] Whale Watcher (Accumulation/Distribution)
- [x] Funding Rate Radar (Reversal Signals)
- [x] Scheduler System (APScheduler)

### Phase 4: Telegram Interface ✅
- [x] Command Handlers
- [x] User Authentication
- [x] Alert Broadcasting
- [x] Interactive Keyboards

### Phase 5: Testing & Deployment ✅
- [x] Docker Containerization
- [x] Health Checks
- [x] Deployment Scripts
- [x] Logging & Monitoring

## 📁 Project Structure

```
cryptosat-bot/
├── config/
│   └── settings.py          # Configuration management
├── core/
│   └── database.py          # SQLite database layer
├── handlers/
│   └── telegram_bot.py      # Telegram bot interface
├── services/
│   ├── coinglass.py         # CoinGlass API wrapper
│   ├── liquidation_monitor.py  # Liquidation monitoring
│   ├── whale_watcher.py     # Whale transaction tracking
│   └── funding_rate_radar.py # Funding rate analysis
├── scripts/
│   └── deploy.sh           # Deployment automation
├── data/                   # Database storage
├── logs/                   # Log files
├── Dockerfile              # Container configuration
├── docker-compose.yml       # Multi-container setup
├── requirements.txt        # Python dependencies
├── .env.example          # Environment template
└── main.py               # Application entry point
```

## ⚡ Performance Metrics

### Monitoring Intervals
- **Liquidations**: Every 10 seconds (Critical)
- **Whale Alerts**: Every 5 seconds (Critical)
- **Funding Rates**: Every 30 seconds (Important)

### Signal Thresholds
- **Liquidations**: $1,000,000+ (15min: $500,000+)
- **Whale Transactions**: $500,000+
- **Funding Rates**: ±1% (extreme)
- **Confidence Score**: 30%+ minimum

### Rate Limiting
- **API Calls**: 100/minute maximum
- **Auto Retry**: On 429 errors
- **Backoff Strategy**: Exponential delay
- **Header Monitoring**: Real-time limit tracking

## 🔧 Management Commands

### Bot Management
```bash
# Deploy bot
./scripts/deploy.sh deploy

# Stop bot
./scripts/deploy.sh stop

# Restart bot
./scripts/deploy.sh restart

# View logs
./scripts/deploy.sh logs

# Update bot
./scripts/deploy.sh update

# Check status
./scripts/deploy.sh status
```

### Docker Operations
```bash
# Build image
docker build -t cryptosat-bot .

# Run container
docker run -d --name cryptosat-bot \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  cryptosat-bot

# View logs
docker logs -f cryptosat-bot

# Stop container
docker stop cryptosat-bot
```

## 📊 Signal Examples

### 🚨 Liquidation Alert
```
🔴 DUMP ALERT BTC
💰 Total Liquidations: $2,500,000
📉 Long Liquidations: $2,100,000
📈 Short Liquidations: $400,000
⚖️ L/S Ratio: 5.25
🎯 Confidence: 85%
🕐 Time: 14:32:15 UTC
```

### 🐋 Whale Alert
```
🟢 ACCUMULATION ALERT ETH
📈 Whale BUY $1,200,000
💲 Price: $2,234.56
🎯 Confidence: 75%
🕐 Time: 14:28:42 UTC
🏦 Exchange: Hyperliquid
```

### 💰 Funding Rate Alert
```
🔴 SHORT REVERSAL ALERT SOL
📉 Funding Rate: 0.0150 (EXTREME HIGH)
📊 24h Avg: 0.0080
🏦 Exchanges: 5
🎯 Confidence: 70%
🕐 Time: 14:45:30 UTC
⚠️ Potential funding squeeze incoming!
```

## 🛠️ Development

### Local Development
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export COINGLASS_API_KEY=your_key
export TELEGRAM_BOT_TOKEN=your_token

# Run bot
python main.py
```

### Testing
```bash
# Test API connection
python -c "from services.coinglass import CoinGlassAPI; \
  import asyncio; \
  asyncio.run(CoinGlassAPI().get_supported_coins())"

# Test database
python -c "from core.database import db_manager; \
  import asyncio; \
  asyncio.run(db_manager.initialize())"
```

## 🔒 Security Features

- **Whitelist Authentication**: Only authorized users can access the bot
- **API Key Protection**: Environment variable storage, no hardcoding
- **Rate Limiting**: Intelligent throttling prevents API bans
- **Input Validation**: All user inputs are sanitized
- **Error Boundaries**: Comprehensive exception handling
- **Container Security**: Non-root user, minimal attack surface

## 📈 Monitoring & Logging

### Log Levels
- **INFO**: General operational information
- **WARNING**: Non-critical issues
- **ERROR**: Failed operations
- **DEBUG**: Detailed debugging

### Health Checks
- **Database Connectivity**: SQLite connection tests
- **API Status**: CoinGlass endpoint availability
- **Service Monitoring**: Background task health
- **Resource Usage**: Memory and CPU monitoring

## 🚀 Production Deployment

### System Requirements
- **CPU**: 0.5+ cores
- **Memory**: 512MB+ RAM
- **Storage**: 1GB+ disk space
- **Network**: Stable internet connection

### VPS Setup (Ubuntu/Debian)
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone and deploy
git clone <repository-url>
cd cryptosat-bot
chmod +x scripts/deploy.sh
./scripts/deploy.sh deploy
```

## 🔮 Future Enhancements

- [ ] **Multi-Exchange Support**: Binance, Bybit, OKX integration
- [ ] **Machine Learning**: Pattern recognition for signal accuracy
- [ ] **Web Dashboard**: Real-time monitoring interface
- [ ] **Alert Customization**: User-defined thresholds and conditions
- [ ] **Portfolio Integration**: Connect to exchange accounts
- [ ] **Mobile App**: Native iOS/Android applications

## 📞 Support

### Troubleshooting
1. **Bot not responding**: Check API keys in `.env` file
2. **No alerts**: Verify channel ID and permissions
3. **High memory usage**: Restart container with `./scripts/deploy.sh restart`
4. **API errors**: Check CoinGlass API status and rate limits

### Logs
```bash
# View recent logs
./scripts/deploy.sh logs

# Search for errors
docker logs cryptosat-bot 2>&1 | grep ERROR
```

### Health Monitoring
- **Container Status**: `./scripts/deploy.sh status`
- **API Rate Limits**: Check bot logs for "Rate limiting" messages
- **Database Size**: Monitor `/app/data/cryptosat.db` size

## 📜 License

This project is proprietary software. All rights reserved.

---

**⚡ CryptoSat Bot - Your Gateway to High-Frequency Trading Intelligence**

*Powered by CoinGlass API v4 | Built with Python 3.11 | Deployed with Docker*
