# VPS Deployment Instructions

## Prerequisites
- Ubuntu/Debian-based VPS with at least 2GB RAM
- Python 3.8+ installed
- Git installed
- PostgreSQL installed (if using PostgreSQL)
- Domain name (optional, for webhook)

## Quick Deployment Commands

### 1. Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Required Packages
```bash
sudo apt install -y python3 python3-pip python3-venv git postgresql postgresql-contrib
```

### 3. Create Application Directory
```bash
sudo mkdir -p /opt/TELEGLAS
sudo chown $USER:$USER /opt/TELEGLAS
cd /opt/TELEGLAS
```

### 4. Clone Repository
```bash
git clone https://github.com/rcz87/TELEGLAS.git .
```

### 5. Setup Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 6. Install Dependencies
```bash
pip install -r requirements.txt
```

### 7. Configure Environment
```bash
cp .env.example .env
nano .env
```

**Required Configuration:**
```env
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here
ADMIN_USER_ID=your_telegram_user_id
TELEGRAM_ENABLED=true

# Database Configuration (choose one)
# Option 1: SQLite (default, easier for development)
DATABASE_URL=sqlite:///data/cryptosat.db

# Option 2: PostgreSQL (recommended for production)
DATABASE_URL=postgresql://cryptosatx_user:your_password@localhost:5432/cryptosatx

# CoinGlass API (get from coinglass.com)
COINGLASS_API_KEY=your_coinglass_api_key

# Other Settings
LOG_LEVEL=INFO
ENABLE_WHALE_ALERTS=true
ENABLE_LIQUIDATION_ALERTS=false
ENABLE_FUNDING_RATE_ALERTS=false
```

### 8. Create Required Directories
```bash
mkdir -p logs data
```

### 9. Setup Database (PostgreSQL only)
```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE cryptosatx;
CREATE USER cryptosatx_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE cryptosatx TO cryptosatx_user;
\q
```

### 10. Test the Application
```bash
python3 main.py
```

Press `Ctrl+C` to stop after confirming it works.

### 11. Create Systemd Service
```bash
sudo nano /etc/systemd/system/teleglas.service
```

**Service Configuration:**
```ini
[Unit]
Description=CryptoSat Bot - High-Frequency Trading Signals
After=network.target postgresql.service
Wants=postgresql.service

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

### 12. Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable teleglas.service
sudo systemctl start teleglas.service
```

### 13. Monitor Service Status
```bash
# Check service status
sudo systemctl status teleglas.service

# View logs
sudo journalctl -u teleglas.service -f

# Check application logs
tail -f /opt/TELEGLAS/logs/app.log
```

## SSL Certificate Setup (Optional)

If using webhook mode with a domain:

### 1. Install Certbot
```bash
sudo apt install certbot
```

### 2. Generate SSL Certificate
```bash
sudo certbot certonly --standalone -d your-domain.com
```

### 3. Update .env with SSL paths
```env
WEBHOOK_SSL_CERT=/etc/letsencrypt/live/your-domain.com/fullchain.pem
WEBHOOK_SSL_PRIV=/etc/letsencrypt/live/your-domain.com/privkey.pem
WEBHOOK_URL=https://your-domain.com:8443/your-bot-token
```

## Firewall Configuration

### 1. Configure UFW Firewall
```bash
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Telegram Bot Responsiveness Issues
**Issue:** Bot starts but doesn't respond to commands immediately

**Solution:** The latest update includes comprehensive fixes for bot responsiveness:
- Enhanced connection testing with retry mechanism
- Optimized polling configuration
- Automatic stale update cleanup
- Startup notification system

**Commands to fix:**
```bash
cd /opt/TELEGLAS
git pull origin master
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart teleglas.service
```

#### 2. TCPConnector Error
**Issue:** `TypeError: TCPConnector.__init__() got an unexpected keyword argument 'connector_timeout'`

**Solution:** This has been fixed in the latest update
```bash
cd /opt/TELEGLAS
git pull origin master
sudo systemctl restart teleglas.service
```

#### 3. Database Connection Error
**Issue:** Connection to PostgreSQL fails

**Solution:** Check database configuration and restart PostgreSQL
```bash
sudo systemctl status postgresql
sudo systemctl restart postgresql
```

#### 4. Bot Token Error
**Issue:** Invalid bot token or connection issues

**Solution:** Verify bot configuration in .env file
```bash
nano .env
# Check BOT_TOKEN and ADMIN_USER_ID values
```

#### 5. Permission Denied
**Issue:** Service fails to start due to permissions

**Solution:** Check file ownership
```bash
sudo chown -R your_username:your_username /opt/TELEGLAS
sudo systemctl restart teleglas.service
```

### Log Locations
- Application logs: `/opt/TELEGLAS/logs/`
- System service logs: `sudo journalctl -u teleglas.service`

### Maintenance Commands

#### Update Application
```bash
cd /opt/TELEGLAS
git pull origin master
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart teleglas.service
```

#### Update Dependencies
```bash
cd /opt/TELEGLAS
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart teleglas.service
```

#### Backup Data
```bash
# SQLite backup
cp /opt/TELEGLAS/data/cryptosat.db /opt/TELEGLAS/data/backup_$(date +%Y%m%d_%H%M%S).db

# PostgreSQL backup
sudo -u postgres pg_dump cryptosatx > /opt/TELEGLAS/data/backup_$(date +%Y%m%d_%H%M%S).sql
```

## Performance Optimization

### 1. System Resources
- Minimum 2GB RAM recommended
- Minimum 1 CPU core
- At least 10GB storage

### 2. Database Optimization
For PostgreSQL, consider these optimizations:
```sql
-- Connect to database
sudo -u postgres psql cryptosatx

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_whale_alerts_timestamp ON whale_alerts(timestamp);
CREATE INDEX IF NOT EXISTS idx_liquidations_timestamp ON liquidations(timestamp);
CREATE INDEX IF NOT EXISTS idx_funding_rates_timestamp ON funding_rates(timestamp);
```

### 3. Log Rotation
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

## Security Best Practices

1. **Regular Updates:** Keep system and dependencies updated
2. **Firewall:** Configure UFW firewall properly
3. **SSL:** Use HTTPS for webhook mode
4. **Database Security:** Use strong database passwords
5. **File Permissions:** Restrict access to configuration files
6. **Monitoring:** Monitor logs for suspicious activity

## Telegram Bot Testing

### Testing Commands
After deployment, test the bot with these commands:
- `/start` - Should work immediately after startup
- `/status` - Should return bot status and connection information
- `/help` - Should show all available commands
- `/whale` - Test whale alert functionality

### Expected Behavior
1. **Immediate Response:** Bot should respond to commands within 1-2 seconds
2. **Startup Notification:** Admin should receive notification when bot starts
3. **Connection Status:** Bot logs should show successful connection establishment
4. **Error Recovery:** Bot should automatically retry on connection failures

### Troubleshooting Bot Issues
```bash
# Check real-time logs
sudo journalctl -u teleglas.service -f

# Check application logs
tail -f /opt/TELEGLAS/logs/app.log

# Test connection manually
cd /opt/TELEGLAS
source venv/bin/activate
python3 -c "
import asyncio
from aiogram import Bot
async def test():
    bot = Bot(token='YOUR_BOT_TOKEN')
    info = await bot.get_me()
    print(f'Bot connected: @{info.username}')
asyncio.run(test())
"
```

## Contact Support

If you encounter issues not covered in this guide:

1. Check the logs for error messages
2. Review the GitHub repository for known issues
3. Create an issue on GitHub with detailed error information

## Latest Updates

### Recent Fixes Applied (December 2024)
- **Telegram Bot Responsiveness:** Enhanced connection testing, optimized polling, and startup notifications
- **TCPConnector Parameter Error:** Fixed aiohttp compatibility issues
- **SSL Configuration:** Improved SSL context and connection pooling
- **Error Handling:** Better retry mechanisms and detailed logging
- **Process Management:** Enhanced process locking and cleanup procedures

The fixes have been committed to the repository and should be automatically applied when updating the application using the standard update commands above.

### Configuration Notes
- Ensure `BOT_TOKEN` is correctly set in `.env`
- Set `ADMIN_USER_ID` to receive startup notifications
- Verify `TELEGRAM_ENABLED=true` for bot functionality
- Check network connectivity to Telegram API endpoints

### Monitoring Bot Health
Monitor these key indicators in logs:
- `[OK] Telegram bot connection established` - Successful startup
- `[STARTUP] CryptoSat Bot is now fully operational` - Bot ready
- Connection retry attempts (normal on network issues)
- Command response times (should be < 2 seconds)
