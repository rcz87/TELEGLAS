#!/bin/bash

echo "🚀 Deploying TELEGLAS Main Bot..."

# Validate environment
./scripts/validate-deployment.sh || exit 1

# Create logs directory
mkdir -p logs

# Install dependencies
pip3 install -r requirements.txt

# Setup systemd service
sudo cp systemd/teleglas-main.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable teleglas-main

# Start service
sudo systemctl restart teleglas-main

echo "✅ Main Bot deployed successfully"
echo "📊 Status: sudo systemctl status teleglas-main"
echo "📝 Logs: tail -f logs/main-bot.log"
