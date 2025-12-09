#!/bin/bash

echo "📊 TELEGLAS Services Status"
echo "==========================="

# Check if PM2 is available and running
if command -v pm2 &> /dev/null && pm2 list | grep -q "teleglas"; then
    echo "🚀 Using PM2 Process Manager"
    echo ""
    
    # Show PM2 status
    pm2 status
    
    echo ""
    echo "📊 Detailed Status:"
    
    # Main Bot Status
    echo "🤖 Main Bot (teleglas-bot):"
    if pm2 list | grep -q "teleglas-bot.*online"; then
        echo "  ✅ Running"
        PM2_INFO=$(pm2 show teleglas-bot)
        echo "  📈 Memory: $(echo "$PM2_INFO" | grep "memory usage" | awk '{print $3$4}')"
        echo "  🔄 Restarts: $(echo "$PM2_INFO" | grep "restart time" | awk '{print $4}')"
        echo "  ⏱️ Uptime: $(echo "$PM2_INFO" | grep "restart time" | awk '{print $8}')"
    else
        echo "  ❌ Stopped or Not Found"
    fi
    
    # Alert Bot Status
    echo "🚨 Alert Bot (teleglas-alert):"
    if pm2 list | grep -q "teleglas-alert.*online"; then
        echo "  ✅ Running"
        PM2_INFO=$(pm2 show teleglas-alert)
        echo "  📈 Memory: $(echo "$PM2_INFO" | grep "memory usage" | awk '{print $3$4}')"
        echo "  🔄 Restarts: $(echo "$PM2_INFO" | grep "restart time" | awk '{print $4}')"
        echo "  ⏱️ Uptime: $(echo "$PM2_INFO" | grep "restart time" | awk '{print $8}')"
    else
        echo "  ❌ Stopped or Not Found"
    fi
    
else
    echo "🔧 Using Systemd Services"
    echo ""
    
    # Main Bot Status
    echo "🤖 Main Bot:"
    if systemctl is-active --quiet teleglas-main 2>/dev/null; then
        echo "  ✅ Running (PID: $(systemctl show --property MainPID --value teleglas-main 2>/dev/null))"
        echo "  📈 Memory: $(ps -p $(systemctl show --property MainPID --value teleglas-main 2>/dev/null) -o pid,pmem,pcpu --no-headers 2>/dev/null)"
    else
        echo "  ❌ Stopped"
    fi

    # Alert Bot Status
    echo "🚨 Alert Bot:"
    if systemctl is-active --quiet teleglas-alert 2>/dev/null; then
        echo "  ✅ Running (PID: $(systemctl show --property MainPID --value teleglas-alert 2>/dev/null))"
        echo "  📈 Memory: $(ps -p $(systemctl show --property MainPID --value teleglas-alert 2>/dev/null) -o pid,pmem,pcpu --no-headers 2>/dev/null)"
    else
        echo "  ❌ Stopped"
    fi
fi

# Disk Usage
echo ""
echo "💾 Disk Usage:"
echo "  $(du -sh /opt/TELEGLAS/logs/ 2>/dev/null || du -sh logs/ 2>/dev/null || echo "logs directory not found") in logs"
echo "  $(du -sh /opt/TELEGLAS/data/ 2>/dev/null || du -sh data/ 2>/dev/null || echo "data directory not found") in data"

# Recent Log Errors
echo ""
echo "⚠️ Recent Errors:"
echo "  Main Bot: $(tail -n 100 logs/main-bot.log 2>/dev/null | grep -i error | wc -l) errors"
echo "  Alert Bot: $(tail -n 100 logs/alert-bot.log 2>/dev/null | grep -i error | wc -l) errors"

echo ""
echo "🔍 Quick Commands:"
if command -v pm2 &> /dev/null && pm2 list | grep -q "teleglas"; then
    echo "  pm2 status                    - Show PM2 status"
    echo "  pm2 logs teleglas-bot         - View main bot logs"
    echo "  pm2 logs teleglas-alert       - View alert bot logs"
    echo "  pm2 restart teleglas-bot      - Restart main bot"
    echo "  pm2 restart teleglas-alert    - Restart alert bot"
else
    echo "  sudo systemctl status teleglas-main  - Check main bot service"
    echo "  sudo systemctl status teleglas-alert  - Check alert bot service"
    echo "  sudo systemctl restart teleglas-main - Restart main bot"
    echo "  sudo systemctl restart teleglas-alert - Restart alert bot"
fi
