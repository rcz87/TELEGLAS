#!/bin/bash

echo "🚀 Deploying TELEGLAS Alert Bot..."

# Validate environment
./scripts/validate-deployment.sh || exit 1

# Create logs directory
mkdir -p logs

# Install additional dependencies if needed
pip3 install websockets python-dotenv

# Setup systemd service
sudo cp systemd/teleglas-alert.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable teleglas-alert

# Start service
sudo systemctl restart teleglas-alert

echo "✅ Alert Bot deployed successfully"
echo "📊 Status: sudo systemctl status teleglas-alert"
echo "📝 Logs: tail -f logs/alert-bot.log"
