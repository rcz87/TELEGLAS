# TELEGLAS - CryptoSat Bot

High-Frequency Trading Signals & Market Intelligence Bot for Cryptocurrency Markets

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Telegram](https://img.shields.io/badge/telegram-bot-blue.svg)

## 🚀 Features

### Core Functionality
- **Whale Monitoring**: Track large cryptocurrency transactions in real-time
- **Liquidation Alerts**: Monitor liquidation events across major exchanges
- **Funding Rate Radar**: Track funding rates for perpetual futures
- **Market Intelligence**: Comprehensive market data analysis

### Integration
- **CoinGlass API v4**: Professional market data provider
- **Telegram Bot**: Real-time notifications and commands
- **PostgreSQL/SQLite**: Flexible database options
- **Process Locking**: Prevents duplicate instances

## 📋 Prerequisites

### System Requirements
- **Operating System**: Ubuntu/Debian-based Linux
- **Python**: 3.8 or higher
- **RAM**: Minimum 2GB (recommended 4GB)
- **Storage**: Minimum 10GB available space
- **Network**: Stable internet connection

### Required Services
- PostgreSQL (optional, SQLite supported)
- Telegram Bot Token
- CoinGlass API Key

## 🛠️ Quick Start

### Option 1: Automated VPS Deployment (Recommended)

For fresh VPS deployment, use our automated setup script:

```bash
# Download and run the setup script
cd /opt
wget https://raw.githubusercontent.com/rcz87/TELEGLAS/master/scripts/setup_vps.sh
bash setup_vps.sh
```

### Option 2: Manual Installation

```bash
# Clone repository
git clone https://github.com/rcz87/TELEGLAS.git
cd TELEGLAS

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with your configuration

# Run the bot
python3 main.py
```

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here
ADMIN_USER_ID=your_telegram_user_id
TELEGRAM_ENABLED=true

# Database Configuration
DATABASE_URL=postgresql://cryptosatx_user:password@localhost:5432/cryptosatx
# Or use SQLite: DATABASE_URL=sqlite:///data/cryptosat.db

# CoinGlass API
COINGLASS_API_KEY=your_coinglass_api_key

# Feature Toggles
ENABLE_WHALE_ALERTS=true
ENABLE_LIQUIDATION_ALERTS=false
ENABLE_FUNDING_RATE_ALERTS=false

# Logging
LOG_LEVEL=INFO
```

### Getting Required Credentials

#### 1. Telegram Bot Token
1. Create a bot with [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow instructions to get your bot token

#### 2. Telegram User ID
1. Start a chat with [@userinfobot](https://t.me/userinfobot)
2. Send any message to get your user ID

#### 3. CoinGlass API Key
1. Register at [CoinGlass](https://www.coinglass.com/)
2. Subscribe to API service
3. Get your API key from dashboard

## 🚀 Deployment

### VPS Deployment

For production deployment on VPS:

#### Automated Setup
```bash
cd /opt
wget https://raw.githubusercontent.com/rcz87/TELEGLAS/master/scripts/setup_vps.sh
bash setup_vps.sh
```

#### Manual Service Setup
```bash
# Create systemd service
sudo nano /etc/systemd/system/teleglas.service
```

```ini
[Unit]
Description=CryptoSat Bot - High-Frequency Trading Signals
After=network.target postgresql.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/opt/TELEGLAS
Environment=PATH=/opt/TELEGLAS/venv/bin
ExecStart=/opt/TELEGLAS/venv/bin/python3 /opt/TELEGLAS/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable teleglas.service
sudo systemctl start teleglas.service
```

### Service Management Commands

```bash
# Check status
sudo systemctl status teleglas.service

# View logs
sudo journalctl -u teleglas.service -f

# Restart service
sudo systemctl restart teleglas.service

# Stop service
sudo systemctl stop teleglas.service
```

## 🛠️ Troubleshooting

### Service Issues

If you encounter "Unit teleglas.service not found" error:

```bash
# Run the service fix script
cd /opt/TELEGLAS
bash scripts/fix_service.sh
```

### Bot Responsiveness Issues

If the bot starts but doesn't respond to commands:

1. **Check Logs**:
   ```bash
   sudo journalctl -u teleglas.service -f
   ```

2. **Verify Configuration**:
   ```bash
   nano /opt/TELEGLAS/.env
   # Ensure BOT_TOKEN and ADMIN_USER_ID are correct
   ```

3. **Test Connection**:
   ```bash
   cd /opt/TELEGLAS
   source venv/bin/activate
   python3 -c "
   import asyncio
   from aiogram import Bot
   import os
   
   async def test():
       bot = Bot(token=os.getenv('BOT_TOKEN'))
       info = await bot.get_me()
       print(f'Bot connected: @{info.username}')
   
   asyncio.run(test())
   "
   ```

4. **Update and Restart**:
   ```bash
   cd /opt/TELEGLAS
   git pull origin master
   source venv/bin/activate
   pip install -r requirements.txt
   sudo systemctl restart teleglas.service
   ```

### Common Issues

| Issue | Solution |
|-------|----------|
| `Invalid bot token` | Verify BOT_TOKEN in .env file |
| `Database connection failed` | Check DATABASE_URL and PostgreSQL status |
| `TCPConnector error` | Update to latest code: `git pull origin master` |
| `Permission denied` | Check file ownership: `sudo chown -R user:user /opt/TELEGLAS` |

## 📱 Telegram Bot Commands

### Basic Commands
- `/start` - Initialize bot and show welcome message
- `/help` - Display all available commands
- `/status` - Check bot status and connection info

### Trading Commands
- `/whale` - Get latest whale transactions
- `/liquidations` - View recent liquidation events
- `/funding` - Check current funding rates

### Admin Commands (Admin Only)
- `/restart` - Restart the bot service
- `/logs` - Get recent log entries
- `/config` - View current configuration

## 🔧 Maintenance

### Updates

To update the application:

```bash
cd /opt/TELEGLAS
git pull origin master
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart teleglas.service
```

### Backup

#### SQLite Backup
```bash
cp /opt/TELEGLAS/data/cryptosat.db /opt/TELEGLAS/data/backup_$(date +%Y%m%d_%H%M%S).db
```

#### PostgreSQL Backup
```bash
sudo -u postgres pg_dump cryptosatx > /opt/TELEGLAS/data/backup_$(date +%Y%m%d_%H%M%S).sql
```

### Log Management

Configure log rotation to prevent disk space issues:

```bash
sudo nano /etc/logrotate.d/teleglas
```

```
/opt/TELEGLAS/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    copytruncate
}
```

## 📊 Monitoring

### Health Checks

Monitor these indicators in logs:

- `[OK] Telegram bot connection established` - Successful startup
- `[STARTUP] CryptoSat Bot is now fully operational` - Bot ready
- Command response times (should be < 2 seconds)

### Performance Metrics

- **Memory Usage**: Monitor for memory leaks
- **CPU Usage**: Should be minimal during normal operation
- **Database Connections**: Should not exceed configured limits
- **API Rate Limits**: Respect CoinGlass API limits

## 🔒 Security

### Best Practices

1. **Environment Variables**: Never commit .env file to version control
2. **Database Security**: Use strong database passwords
3. **Firewall**: Configure UFW firewall properly
4. **SSL**: Use HTTPS for webhook mode (if configured)
5. **Regular Updates**: Keep system and dependencies updated

### File Permissions

```bash
# Secure configuration files
chmod 600 /opt/TELEGLAS/.env
chmod 644 /opt/TELEGLAS/*.py
chmod 755 /opt/TELEGLAS/scripts/*.sh
```

## 📚 Documentation

- [VPS Deployment Instructions](VPS_DEPLOYMENT_INSTRUCTIONS.md) - Detailed VPS setup guide
- [Telegram Bot Fix Summary](TELEGRAM_BOT_FIX_SUMMARY.md) - Recent fixes and improvements
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - General deployment information

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter issues:

1. Check the logs for error messages
2. Review this README and documentation
3. Search existing [GitHub Issues](https://github.com/rcz87/TELEGLAS/issues)
4. Create a new issue with detailed error information

## 🔄 Changelog

### Recent Updates (December 2024)
- **Enhanced Telegram Bot Responsiveness**: Fixed connection testing and polling issues
- **Improved Error Handling**: Better retry mechanisms and logging
- **Automated Deployment Scripts**: Added setup and service fix scripts
- **Updated Documentation**: Comprehensive deployment and troubleshooting guides

---

**⚠️ Disclaimer**: This bot is for informational purposes only. Always do your own research before making trading decisions.
