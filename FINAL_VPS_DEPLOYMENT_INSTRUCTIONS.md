# Final VPS Deployment Instructions

## Overview
This document provides the exact steps to deploy the cleaned TELEGLAS project on your VPS. The project has been completely refactored and is now production-ready.

## Prerequisites
- Ubuntu/Debian-based VPS
- Python 3.8+ installed
- Git installed
- Internet access for package installation

## Step-by-Step Deployment

### 1. Navigate to Project Directory
```bash
cd /opt/TELEGLAS
```

### 2. Pull Latest Changes from GitHub
```bash
git pull origin main
```

### 3. Create Python Virtual Environment
```bash
python3 -m venv venv
```

### 4. Activate Virtual Environment
```bash
source venv/bin/activate
```

### 5. Install Dependencies
```bash
pip install -r requirements.txt
```

### 6. Configure Environment Variables
Copy the example environment file and configure:
```bash
cp .env.example .env
nano .env
```

**Required Configuration:**
```bash
# Core Bot Configuration
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
TELEGRAM_ADMIN_CHAT_ID=your_telegram_user_id
TELEGRAM_ALERT_CHANNEL_ID=your_alert_channel_id

# Access Control
WHITELISTED_USERS=5899681906,your_user_id_here

# Feature Flags
ENABLE_WHALE_ALERTS=true
ENABLE_BROADCAST_ALERTS=true

# API Configuration
COINGLASS_API_KEY=your_coinglass_api_key
API_CALLS_PER_MINUTE=60

# Thresholds (can use defaults)
WHALE_TRANSACTION_THRESHOLD_USD=500000
LIQUIDATION_THRESHOLD_USD=1000000
FUNDING_RATE_THRESHOLD=0.01

# Timing (can use defaults)
WHALE_POLL_INTERVAL=30
LIQUIDATION_POLL_INTERVAL=60
FUNDING_RATE_POLL_INTERVAL=300
```

### 7. Set Proper Permissions
```bash
chmod +x main.py
chmod 755 .
chmod -R 755 config/ core/ handlers/ services/ utils/
```

### 8. Create Logs Directory
```bash
mkdir -p logs
chmod 755 logs
```

### 9. Test the Bot
```bash
python3 main.py
```

**Expected Output:**
```
[STARTUP] CryptoSat Bot - High-Frequency Trading Signals & Market Intelligence
[STARTUP] Powered by CoinGlass API v4
[INIT] Initializing CryptoSat Bot...
[OK] Configuration validated
[OK] Database initialized
[OK] Telegram bot initialized
[OK] Scheduler configured
[DONE] CryptoSat Bot initialization complete!
[START] Starting monitoring services...
[START] Starting whale monitoring (ENABLE_WHALE_ALERTS=true)
[OK] Monitoring services configuration complete
[SCHEDULER] Scheduler started
[OK] Telegram bot task created successfully
[OPERATIONAL] CryptoSat Bot is now fully operational!
```

### 10. Verify Bot is Working
1. Send `/start` to your bot in Telegram
2. Send `/help` to see available commands
3. Send `/status` to check bot status
4. Send `/raw BTC` to test comprehensive data
5. Send `/whale` to test whale transactions

### 11. Stop the Test (Ctrl+C) and Create System Service
Create a systemd service file:
```bash
sudo nano /etc/systemd/system/teleglas.service
```

**Service Configuration:**
```ini
[Unit]
Description=CryptoSat TELEGLAS Bot
After=network.target

[Service]
Type=simple
User=your_username
Group=your_group
WorkingDirectory=/opt/TELEGLAS
Environment=PATH=/opt/TELEGLAS/venv/bin
ExecStart=/opt/TELEGLAS/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 12. Enable and Start the Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable teleglas.service
sudo systemctl start teleglas.service
```

### 13. Verify Service Status
```bash
sudo systemctl status teleglas.service
```

### 14. Check Logs
```bash
sudo journalctl -u teleglas.service -f
```

## Troubleshooting Common Issues

### Issue 1: Bot Won't Start
**Symptoms:** Service fails to start, authentication errors
**Solutions:**
1. Check TELEGRAM_BOT_TOKEN is correct
2. Verify WHITELISTED_USERS includes your user ID
3. Check .env file permissions:
   ```bash
   chmod 600 .env
   ```

### Issue 2: No Whale Alerts
**Symptoms:** Bot runs but no whale alerts are generated
**Solutions:**
1. Ensure ENABLE_WHALE_ALERTS=true
2. Verify COINGLASS_API_KEY is valid
3. Check API quota limits
4. Monitor logs for API errors

### Issue 3: Memory Issues
**Symptoms:** High memory usage, bot crashes
**Solutions:**
1. Check available disk space for database
2. Monitor memory usage with `htop`
3. Reduce retention periods in settings
4. Restart service: `sudo systemctl restart teleglas.service`

### Issue 4: API Rate Limits
**Symptoms:** "Rate limit exceeded" errors
**Solutions:**
1. Reduce API_CALLS_PER_MINUTE to 30 or less
2. Increase poll intervals
3. Check CoinGlass API dashboard for quota

### Issue 5: Database Errors
**Symptoms:** Database connection or corruption errors
**Solutions:**
1. Check permissions on database files
2. Verify disk space availability
3. Backup and recreate database:
   ```bash
   cp teleglas.db teleglas.db.backup
   rm teleglas.db
   sudo systemctl restart teleglas.service
   ```

## Monitoring and Maintenance

### Daily Checks
1. **Service Status:**
   ```bash
   sudo systemctl status teleglas.service
   ```

2. **Bot Responsiveness:**
   - Send `/status` command
   - Check for timely responses

3. **Log Monitoring:**
   ```bash
   sudo journalctl -u teleglas.service --since "1 hour ago"
   ```

4. **Resource Usage:**
   ```bash
   df -h  # Disk space
   free -h  # Memory
   htop  # Process monitoring
   ```

### Weekly Maintenance
1. **Update Dependencies:**
   ```bash
   cd /opt/TELEGLAS
   source venv/bin/activate
   pip install --upgrade -r requirements.txt
   sudo systemctl restart teleglas.service
   ```

2. **Log Rotation:**
   ```bash
   sudo journalctl --vacuum-time=7d
   ```

3. **Database Cleanup:**
   - The bot automatically cleans up old data (24-hour retention)
   - Monitor database file size if needed

### Monthly Maintenance
1. **Security Updates:**
   ```bash
   sudo apt update && sudo apt upgrade
   ```

2. **Backup Configuration:**
   ```bash
   cp /opt/TELEGLAS/.env /opt/TELEGLAS/.env.backup
   ```

3. **Performance Review:**
   - Check whale alert effectiveness
   - Adjust thresholds if needed
   - Review API usage patterns

## Performance Optimization

### For High-Volume Usage
1. **Increase API Limits:**
   ```bash
   # In .env
   API_CALLS_PER_MINUTE=120
   WHALE_POLL_INTERVAL=15
   ```

2. **Enable Logging Rotation:**
   ```bash
   # In .env
   LOG_FILE=/opt/TELEGLAS/logs/teleglas.log
   ```

3. **Monitor System Resources:**
   ```bash
   # Add to crontab for monitoring
   */5 * * * * /opt/TELEGLAS/scripts/health_check.sh
   ```

### For Low-Resource VPS
1. **Reduce Resource Usage:**
   ```bash
   # In .env
   API_CALLS_PER_MINUTE=30
   WHALE_POLL_INTERVAL=60
   LIQUIDATION_POLL_INTERVAL=120
   FUNDING_RATE_POLL_INTERVAL=600
   ```

2. **Disable Non-Essential Features:**
   ```bash
   # In .env
   ENABLE_BROADCAST_ALERTS=false
   ```

## Security Considerations

### File Permissions
```bash
# Secure sensitive files
chmod 600 .env
chmod 755 main.py
chmod -R 644 config/ core/ handlers/ services/ utils/
chmod -R 755 logs/
```

### Network Security
1. **Firewall Rules:**
   ```bash
   sudo ufw allow 22/tcp  # SSH only
   sudo ufw enable
   ```

2. **Fail2Ban:**
   ```bash
   sudo apt install fail2ban
   sudo systemctl enable fail2ban
   ```

### Updates and Patches
1. **Automated Security Updates:**
   ```bash
   sudo apt install unattended-upgrades
   sudo dpkg-reconfigure unattended-upgrades
   ```

## Backup Strategy

### Configuration Backup
```bash
# Create backup script
cat > /opt/TELEGLAS/backup_config.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp /opt/TELEGLAS/.env /opt/TELEGLAS/backups/.env.$DATE
tar -czf /opt/TELEGLAS/backups/config_$DATE.tar.gz config/ core/ handlers/ services/ utils/
find /opt/TELEGLAS/backups/ -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x /opt/TELEGLAS/backup_config.sh
mkdir -p /opt/TELEGLAS/backups

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /opt/TELEGLAS/backup_config.sh" | crontab -
```

### Database Backup
```bash
# Create database backup script
cat > /opt/TELEGLAS/backup_db.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp /opt/TELEGLAS/teleglas.db /opt/TELEGLAS/backups/teleglas_$DATE.db
find /opt/TELEGLAS/backups/ -name "*.db" -mtime +3 -delete
EOF

chmod +x /opt/TELEGLAS/backup_db.sh

# Add to crontab (every 6 hours)
echo "0 */6 * * * /opt/TELEGLAS/backup_db.sh" | crontab -
```

## Emergency Procedures

### Bot Not Responding
1. **Check Service Status:**
   ```bash
   sudo systemctl status teleglas.service
   ```

2. **Restart Service:**
   ```bash
   sudo systemctl restart teleglas.service
   ```

3. **Check Logs:**
   ```bash
   sudo journalctl -u teleglas.service -n 50
   ```

4. **Manual Test:**
   ```bash
   cd /opt/TELEGLAS
   source venv/bin/activate
   python3 main.py
   ```

### API Key Compromised
1. **Revoke Old API Key:**
   - Go to CoinGlass dashboard
   - Revoke compromised API key

2. **Generate New API Key:**
   - Create new API key with required permissions

3. **Update Configuration:**
   ```bash
   nano /opt/TELEGLAS/.env
   # Update COINGLASS_API_KEY
   ```

4. **Restart Service:**
   ```bash
   sudo systemctl restart teleglas.service
   ```

### Complete System Recovery
1. **Pull Latest Code:**
   ```bash
   cd /opt/TELEGLAS
   git pull origin main
   ```

2. **Reinstall Dependencies:**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt --force-reinstall
   ```

3. **Restore Configuration:**
   ```bash
   cp /opt/TELEGLAS/backups/.env.LATEST /opt/TELEGLAS/.env
   ```

4. **Restart Service:**
   ```bash
   sudo systemctl restart teleglas.service
   ```

## Contact and Support

### For Technical Issues
1. Check logs: `sudo journalctl -u teleglas.service -f`
2. Review this document for troubleshooting steps
3. Verify configuration in .env file

### For Feature Requests
1. Create GitHub issue with detailed description
2. Include use case and expected behavior
3. Provide examples if applicable

## Final Verification Checklist

Before considering deployment complete, verify:

- [ ] Service starts without errors
- [ ] Bot responds to `/start` command
- [ ] Bot responds to `/help` command  
- [ ] Bot responds to `/status` command
- [ ] Bot responds to `/raw BTC` command
- [ ] Bot responds to `/whale` command
- [ ] Whale alerts are being generated (if enabled)
- [ ] Logs are being written correctly
- [ ] Service restarts automatically after crash
- [ ] Resource usage is within limits
- [ ] Backups are being created
- [ ] Security measures are in place

## Conclusion

Your TELEGLAS bot is now deployed and ready for production use. The cleaned and refactored codebase provides:

- ✅ **Stability**: Zero-crash design with comprehensive error handling
- ✅ **Performance**: Optimized API usage and resource management  
- ✅ **Security**: Whitelist-based access control and secure configuration
- ✅ **Maintainability**: Clean code structure and extensive documentation
- ✅ **Scalability**: Modular architecture for easy extension

The bot will continuously monitor whale transactions and provide real-time trading signals while requiring minimal maintenance.

**Next Steps:**
1. Monitor bot performance for first 24 hours
2. Adjust thresholds and settings based on your needs
3. Set up monitoring alerts for service status
4. Regular backup and maintenance procedures

Enjoy your cleaned and optimized CryptoSat bot!
