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
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

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

#### 1. TCPConnector Error
**Issue:** `TypeError: TCPConnector.__init__() got an unexpected keyword argument 'connector_timeout'`

**Solution:** Update to latest code from repository
```bash
cd /opt/TELEGLAS
git pull origin master
sudo systemctl restart teleglas.service
```

#### 2. Database Connection Error
**Issue:** Connection to PostgreSQL fails

**Solution:** Check database configuration and restart PostgreSQL
```bash
sudo systemctl status postgresql
sudo systemctl restart postgresql
```

#### 3. Bot Token Error
**Issue:** Invalid bot token

**Solution:** Verify bot token in .env file
```bash
nano .env
# Check TELEGRAM_BOT_TOKEN value
```

#### 4. Permission Denied
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

## Contact Support

If you encounter issues not covered in this guide:

1. Check the logs for error messages
2. Review the GitHub repository for known issues
3. Create an issue on GitHub with detailed error information

## Latest Updates

### Recent Fix Applied
- **TCPConnector Parameter Error Fixed:** Removed invalid `connector_timeout` parameter from aiohttp TCPConnector configuration
- **SSL Configuration Improved:** Enhanced SSL context and connection pooling for better security
- **Compatibility:** Updated to work with latest aiohttp versions

The fix has been committed to the repository and should be automatically applied when updating the application.
