#!/bin/bash

echo "🔄 Safe update for TELEGLAS services..."

# Validate environment first
./scripts/validate-deployment.sh || exit 1

# Git pull latest changes
git pull origin main

# Install any new dependencies
pip3 install -r requirements.txt

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
