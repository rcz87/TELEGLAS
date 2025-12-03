#!/bin/bash

# TELEGLAS Service Fix Script
# This script fixes the systemd service if it's not found or has issues

set -e

echo "🔧 Fixing TELEGLAS Service..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get current username
CURRENT_USER=$(whoami)
print_status "Current user: $CURRENT_USER"

# Check if service exists
if systemctl list-unit-files | grep -q "teleglas.service"; then
    print_status "Service file found, checking status..."
    
    # Stop existing service
    sudo systemctl stop teleglas.service 2>/dev/null || true
    print_status "Stopped existing service"
    
    # Remove existing service file
    sudo rm -f /etc/systemd/system/teleglas.service
    print_status "Removed existing service file"
else
    print_status "Service file not found, creating new one..."
fi

# Reload systemd to clear cache
sudo systemctl daemon-reload

# Create new service file
print_status "Creating new systemd service..."
sudo tee /etc/systemd/system/teleglas.service > /dev/null << EOF
[Unit]
Description=CryptoSat Bot - High-Frequency Trading Signals
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=/opt/TELEGLAS
Environment=PATH=/opt/TELEGLAS/venv/bin
ExecStart=/opt/TELEGLAS/venv/bin/python3 /opt/TELEGLAS/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Set proper permissions
sudo chmod 644 /etc/systemd/system/teleglas.service

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable teleglas.service

print_status "Service file created and enabled successfully!"

# Check if application directory exists
if [ ! -d "/opt/TELEGLAS" ]; then
    print_error "Application directory /opt/TELEGLAS not found!"
    print_status "Please run the setup script first: bash scripts/setup_vps.sh"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "/opt/TELEGLAS/venv" ]; then
    print_error "Virtual environment not found!"
    print_status "Creating virtual environment..."
    cd /opt/TELEGLAS
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Check if .env file exists
if [ ! -f "/opt/TELEGLAS/.env" ]; then
    print_warning ".env file not found! Creating from template..."
    cd /opt/TELEGLAS
    cp .env.example .env
    print_warning "Please edit /opt/TELEGLAS/.env with your configuration!"
    nano /opt/TELEGLAS/.env
fi

# Start the service
print_status "Starting TELEGLAS service..."
sudo systemctl start teleglas.service

# Wait for service to start
sleep 5

# Check service status
if sudo systemctl is-active --quiet teleglas.service; then
    print_status "✅ TELEGLAS service is running successfully!"
else
    print_error "❌ TELEGLAS service failed to start!"
    print_status "Checking logs for errors:"
    sudo journalctl -u teleglas.service --no-pager -l -n 20
    
    # Try to get more detailed error info
    print_status "Checking service status details:"
    sudo systemctl status teleglas.service --no-pager -l
    
    exit 1
fi

# Display useful information
print_status "🎉 Service fix completed!"
echo ""
print_status "Service Information:"
echo "  - Service Name: teleglas.service"
echo "  - Status: $(sudo systemctl is-active teleglas.service)"
echo "  - Enabled: $(sudo systemctl is-enabled teleglas.service)"
echo "  - Application Path: /opt/TELEGLAS"
echo ""
print_status "Useful Commands:"
echo "  - Check status: sudo systemctl status teleglas.service"
echo "  - View logs: sudo journalctl -u teleglas.service -f"
echo "  - Restart service: sudo systemctl restart teleglas.service"
echo "  - Stop service: sudo systemctl stop teleglas.service"
echo ""

# Test bot connection if possible
print_status "Testing bot connection..."
cd /opt/TELEGLAS
source venv/bin/activate

# Extract bot token from .env for testing
BOT_TOKEN=$(grep "^BOT_TOKEN=" /opt/TELEGLAS/.env | cut -d'=' -f2)

if [ ! -z "$BOT_TOKEN" ] && [ "$BOT_TOKEN" != "your_bot_token_here" ]; then
    python3 -c "
import asyncio
from aiogram import Bot

async def test_connection():
    try:
        bot = Bot(token='$BOT_TOKEN')
        info = await bot.get_me()
        print(f'✅ Bot connection successful: @{info.username}')
        return True
    except Exception as e:
        print(f'❌ Bot connection failed: {e}')
        return False

result = asyncio.run(test_connection())
exit(0 if result else 1)
" && print_status "Bot connection test passed!" || print_warning "Bot connection test failed. Please check your BOT_TOKEN in .env file"
else
    print_warning "BOT_TOKEN not configured. Please edit /opt/TELEGLAS/.env file"
fi

print_status "Service fix script completed! 🚀"
