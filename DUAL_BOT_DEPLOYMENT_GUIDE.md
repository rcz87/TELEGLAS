# Dual Bot Deployment Guide - TELEGLAS Production Setup

## 🎯 Objective

Setup production deployment yang aman untuk 2 bot dalam 1 repository:
1. **Main Bot** - Manual command-based (existing)
2. **Alert Bot** - WebSocket-based (new)

Dengan jaminan:
- ✅ Tidak ada konflik antar bot
- ✅ Tidak ada proses "jalan sendiri" setelah git pull
- ✅ Deployment yang rapi dan terkontrol
- ✅ Isolasi penuh antar services

---

## 🏗️ Architecture Overview

```
TELEGLAS Repository
├── main.py                    # Main Bot (Manual Commands)
├── ws_alert/alert_runner.py   # Alert Bot (WebSocket)
├── systemd/
│   ├── teleglas-main.service  # Main Bot Service
│   └── teleglas-alert.service # Alert Bot Service
├── scripts/
│   ├── deploy-main.sh         # Main Bot Deployment
│   ├── deploy-alert.sh        # Alert Bot Deployment
│   └── update-services.sh     # Safe Update Script
└── logs/
    ├── main-bot.log           # Main Bot Logs
    └── alert-bot.log          # Alert Bot Logs
```

---

## 🔧 Step 1: Environment Isolation

### 1.1 Separate Configuration Files

**Main Bot Environment** (`config/settings.py` existing):
```bash
# Main Bot Variables
TELEGRAM_BOT_TOKEN=main_bot_token_here
TELEGRAM_ADMIN_CHAT_ID=admin_chat_id_here
COINGLASS_API_KEY=coinglass_key_here
DATABASE_URL=sqlite:///data/teleglas.db
```

**Alert Bot Environment** (`ws_alert/.env`):
```bash
# Alert Bot Variables (UNIQUE!)
TELEGRAM_ALERT_TOKEN=alert_bot_token_here
TELEGRAM_ALERT_CHANNEL_ID=alert_channel_id_here
COINGLASS_API_KEY=coinglass_key_here
COINGLASS_API_KEY_WS=ws_api_key_here
WS_PING_INTERVAL=20
ENABLE_WHALE_ALERTS=true
```

### 1.2 Validation Script

Buat `scripts/validate-deployment.sh`:
```bash
#!/bin/bash

echo "🔍 Validating dual bot deployment..."

# Check for required environment variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN not found"
    exit 1
fi

if [ -z "$TELEGRAM_ALERT_TOKEN" ]; then
    echo "❌ TELEGRAM_ALERT_TOKEN not found"
    exit 1
fi

# Ensure tokens are different
if [ "$TELEGRAM_BOT_TOKEN" = "$TELEGRAM_ALERT_TOKEN" ]; then
    echo "❌ Bot tokens must be different!"
    exit 1
fi

echo "✅ Environment validation passed"
```

---

## 🚀 Step 2: Systemd Services Setup

### 2.1 Main Bot Service

Buat `systemd/teleglas-main.service`:
```ini
[Unit]
Description=TELEGLAS Main Bot (Manual Commands)
After=network.target
Wants=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/TELEGLAS
Environment=PATH=/opt/TELEGLAS/venv/bin
ExecStart=/opt/TELEGLAS/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/TELEGLAS/logs/main-bot.log
StandardError=append:/opt/TELEGLAS/logs/main-bot.log

# Resource Limits
MemoryMax=512M
CPUQuota=50%

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### 2.2 Alert Bot Service

Buat `systemd/teleglas-alert.service`:
```ini
[Unit]
Description=TELEGLAS Alert Bot (WebSocket)
After=network.target
Wants=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/TELEGLAS
Environment=PATH=/opt/TELEGLAS/venv/bin
ExecStart=/opt/TELEGLAS/venv/bin/python -m ws_alert.alert_runner
Restart=always
RestartSec=10
StandardOutput=append:/opt/TELEGLAS/logs/alert-bot.log
StandardError=append:/opt/TELEGLAS/logs/alert-bot.log

# Resource Limits
MemoryMax=256M
CPUQuota=30%

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

---

## 📜 Step 3: Deployment Scripts

### 3.1 Main Bot Deployment

Buat `scripts/deploy-main.sh`:
```bash
#!/bin/bash

echo "🚀 Deploying TELEGLAS Main Bot..."

# Validate environment
./scripts/validate-deployment.sh || exit 1

# Create logs directory
mkdir -p logs

# Install dependencies
/opt/TELEGLAS/venv/bin/pip install -r requirements.txt

# Setup systemd service
sudo cp systemd/teleglas-main.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable teleglas-main

# Start service
sudo systemctl restart teleglas-main

echo "✅ Main Bot deployed successfully"
echo "📊 Status: sudo systemctl status teleglas-main"
echo "📝 Logs: tail -f logs/main-bot.log"
```

### 3.2 Alert Bot Deployment

Buat `scripts/deploy-alert.sh`:
```bash
#!/bin/bash

echo "🚀 Deploying TELEGLAS Alert Bot..."

# Validate environment
./scripts/validate-deployment.sh || exit 1

# Create logs directory
mkdir -p logs

# Install additional dependencies if needed
/opt/TELEGLAS/venv/bin/pip install websockets python-dotenv

# Setup systemd service
sudo cp systemd/teleglas-alert.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable teleglas-alert

# Start service
sudo systemctl restart teleglas-alert

echo "✅ Alert Bot deployed successfully"
echo "📊 Status: sudo systemctl status teleglas-alert"
echo "📝 Logs: tail -f logs/alert-bot.log"
```

### 3.3 Safe Update Script

Buat `scripts/update-services.sh`:
```bash
#!/bin/bash

echo "🔄 Safe update for TELEGLAS services..."

# Validate environment first
./scripts/validate-deployment.sh || exit 1

# Git pull latest changes
git pull origin main

# Install any new dependencies
/opt/TELEGLAS/venv/bin/pip install -r requirements.txt

# Restart services gracefully
echo "🔄 Restarting Main Bot..."
sudo systemctl restart teleglas-main

sleep 5

echo "🔄 Restarting Alert Bot..."
sudo systemctl restart teleglas-alert

# Check status
echo "📊 Checking service status..."
sudo systemctl is-active teleglas-main || echo "❌ Main Bot not running"
sudo systemctl is-active teleglas-alert || echo "❌ Alert Bot not running"

echo "✅ Update completed safely"
```

---

## 🛡️ Step 4: Conflict Prevention Measures

### 4.1 Database Isolation

**Shared Database Strategy** (Recommended):
```python
# Both bots can use same database with different prefixes
MAIN_BOT_TABLE_PREFIX = "main_"
ALERT_BOT_TABLE_PREFIX = "alert_"

# In config/settings.py for main bot
TABLE_PREFIX = "main_"

# In ws_alert/config.py for alert bot  
TABLE_PREFIX = "alert_"
```

### 4.2 Port Isolation

**Main Bot**: Tidak menggunakan port khusus (HTTP polling)
**Alert Bot**: WebSocket connections (outbound only)

### 4.3 Log Rotation

Buat `logrotate.conf`:
```
/home/ubuntu/TELEGLAS/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

Install:
```bash
sudo cp logrotate.conf /etc/logrotate.d/teleglas
```

---

## 🚦 Step 5: Service Management Commands

### Basic Commands
```bash
# Start services
sudo systemctl start teleglas-main
sudo systemctl start teleglas-alert

# Stop services
sudo systemctl stop teleglas-main
sudo systemctl stop teleglas-alert

# Restart services
sudo systemctl restart teleglas-main
sudo systemctl restart teleglas-alert

# Check status
sudo systemctl status teleglas-main
sudo systemctl status teleglas-alert

# View logs
sudo journalctl -u teleglas-main -f
sudo journalctl -u teleglas-alert -f
```

### Quick Status Script

Buat `scripts/status.sh`:
```bash
#!/bin/bash

echo "📊 TELEGLAS Services Status"
echo "==========================="

# Main Bot Status
echo "🤖 Main Bot:"
if systemctl is-active --quiet teleglas-main; then
    echo "  ✅ Running (PID: $(systemctl show --property MainPID --value teleglas-main))"
    echo "  📈 Memory: $(ps -p $(systemctl show --property MainPID --value teleglas-main) -o pid,pmem,pcpu --no-headers)"
else
    echo "  ❌ Stopped"
fi

# Alert Bot Status
echo "🚨 Alert Bot:"
if systemctl is-active --quiet teleglas-alert; then
    echo "  ✅ Running (PID: $(systemctl show --property MainPID --value teleglas-alert))"
    echo "  📈 Memory: $(ps -p $(systemctl show --property MainPID --value teleglas-alert) -o pid,pmem,pcpu --no-headers)"
else
    echo "  ❌ Stopped"
fi

# Disk Usage
echo "💾 Disk Usage:"
echo "  $(du -sh /home/ubuntu/TELEGLAS/logs/) in logs"
echo "  $(du -sh /home/ubuntu/TELEGLAS/data/) in data"

# Recent Log Errors
echo "⚠️ Recent Errors:"
echo "  Main Bot: $(tail -n 100 logs/main-bot.log | grep -i error | wc -l) errors"
echo "  Alert Bot: $(tail -n 100 logs/alert-bot.log | grep -i error | wc -l) errors"
```

---

## 🔍 Step 6: Monitoring & Health Checks

### 6.1 Health Check Script

Buat `scripts/health-check.sh`:
```bash
#!/bin/bash

echo "🏥 TELEGLAS Health Check"
echo "======================"

# Check if services are running
main_running=$(systemctl is-active teleglas-main)
alert_running=$(systemctl is-active teleglas-alert)

if [ "$main_running" != "active" ]; then
    echo "❌ Main Bot is not running! Attempting restart..."
    sudo systemctl restart teleglas-main
    sleep 5
    main_running=$(systemctl is-active teleglas-main)
fi

if [ "$alert_running" != "active" ]; then
    echo "❌ Alert Bot is not running! Attempting restart..."
    sudo systemctl restart teleglas-alert
    sleep 5
    alert_running=$(systemctl is-active teleglas-alert)
fi

# Final status
echo "📊 Final Status:"
echo "  Main Bot: $main_running"
echo "  Alert Bot: $alert_running"

# Check for recent errors
main_errors=$(tail -n 50 logs/main-bot.log | grep -i "error\|exception" | wc -l)
alert_errors=$(tail -n 50 logs/alert-bot.log | grep -i "error\|exception" | wc -l)

echo "🚨 Recent Errors (last 50 lines):"
echo "  Main Bot: $main_errors"
echo "  Alert Bot: $alert_errors"

# Exit with error if any service is down
if [ "$main_running" != "active" ] || [ "$alert_running" != "active" ]; then
    exit 1
fi
```

### 6.2 Cron Job for Health Monitoring

```bash
# Edit crontab
crontab -e

# Add health check every 5 minutes
*/5 * * * * /opt/TELEGLAS/scripts/health-check.sh >/dev/null 2>&1
```

---

## 🚀 Step 7: Initial Deployment

### 7.1 Setup Steps

```bash
# 1. Clone/Update repository
cd /opt/TELEGLAS
git pull origin main

# 2. Make scripts executable
chmod +x scripts/*.sh

# 3. Create required directories
mkdir -p logs data

# 4. Setup environment files
cp .env.example .env
cp ws_alert/.env.example ws_alert/.env

# 5. Edit environment files with your tokens
nano .env
nano ws_alert/.env

# 6. Deploy Main Bot
./scripts/deploy-main.sh

# 7. Deploy Alert Bot (after Main Bot is stable)
./scripts/deploy-alert.sh

# 8. Check status
./scripts/status.sh
```

### 7.2 Validation Steps

```bash
# 1. Check services
sudo systemctl status teleglas-main teleglas-alert

# 2. Check logs
tail -f logs/main-bot.log
tail -f logs/alert-bot.log

# 3. Test main bot
# Send /start command to main bot

# 4. Test alert bot
# Should automatically send startup message

# 5. Verify no conflicts
./scripts/health-check.sh
```

---

## 🔄 Step 8: Safe Git Workflow

### 8.1 Before Git Pull

```bash
# 1. Check current status
./scripts/status.sh

# 2. Stop services (optional but recommended for big changes)
sudo systemctl stop teleglas-main
sudo systemctl stop teleglas-alert

# 3. Pull changes
git pull origin main

# 4. Update dependencies if needed
/opt/TELEGLAS/venv/bin/pip install -r requirements.txt

# 5. Restart services
sudo systemctl start teleglas-main
sudo systemctl start teleglas-alert

# 6. Validate
./scripts/health-check.sh
```

### 8.2 Using Safe Update Script

```bash
# For regular updates, use the safe script
./scripts/update-services.sh
```

---

## 🚨 Troubleshooting

### Common Issues

1. **Bot Tokens Conflict**
   ```bash
   # Check tokens are different
   grep -r "TELEGRAM_" .env ws_alert/.env
   ```

2. **Port Conflicts**
   ```bash
   # Check listening ports
   sudo netstat -tlnp | grep python
   ```

3. **Memory Issues**
   ```bash
   # Check memory usage
   free -h
   ps aux | grep python
   ```

4. **Log Issues**
   ```bash
   # Check log permissions
   ls -la logs/
   tail -f logs/*.log
   ```

### Recovery Commands

```bash
# Emergency stop
sudo systemctl stop teleglas-main teleglas-alert

# Force restart
sudo systemctl restart teleglas-main teleglas-alert

# Clear logs if too large
> logs/main-bot.log
> logs/alert-bot.log

# Reset services
sudo systemctl daemon-reload
```

---

## 📋 Deployment Checklist

### Pre-Deployment Checklist
- [ ] Environment files created with correct tokens
- [ ] Bot tokens are different between bots
- [ ] Required directories exist (logs, data)
- [ ] Scripts are executable
- [ ] Dependencies installed

### Post-Deployment Checklist
- [ ] Both services are running
- [ ] No errors in logs
- [ ] Main bot responds to commands
- [ ] Alert bot sends startup message
- [ ] Health check passes
- [ ] No resource conflicts

### Ongoing Monitoring
- [ ] Daily health check passes
- [ ] Log rotation working
- [ ] Memory usage stable
- [ ] Bot tokens remain secure
- [ ] Services auto-restart on failure

---

## 🎉 Summary

Dengan setup ini, Anda akan memiliki:

✅ **Complete Isolation**: Setiap bot memiliki service, logs, dan config sendiri
✅ **No Auto-Start**: Services hanya restart jika crash, tidak otomatis setelah git pull
✅ **Safe Updates**: Script update yang aman dengan validasi
✅ **Health Monitoring**: Otomatis monitoring dan recovery
✅ **Resource Management**: Memory dan CPU limits per service
✅ **Production Ready**: Log rotation, security limits, proper error handling

Deploy kedua bot dengan confidence tanpa khawatir konflik!
