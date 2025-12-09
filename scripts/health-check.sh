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
main_errors=$(tail -n 50 logs/main-bot.log 2>/dev/null | grep -i "error\|exception" | wc -l)
alert_errors=$(tail -n 50 logs/alert-bot.log 2>/dev/null | grep -i "error\|exception" | wc -l)

echo "🚨 Recent Errors (last 50 lines):"
echo "  Main Bot: $main_errors"
echo "  Alert Bot: $alert_errors"

# Exit with error if any service is down
if [ "$main_running" != "active" ] || [ "$alert_running" != "active" ]; then
    exit 1
fi
