#!/bin/bash

# TELEGLAS VPS Setup Script
# This script automates the entire VPS deployment process

set -e

echo "🚀 Starting TELEGLAS VPS Setup..."

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

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons."
   print_warning "Please run as regular user with sudo privileges."
   exit 1
fi

# Get current username
CURRENT_USER=$(whoami)
print_status "Current user: $CURRENT_USER"

# 1. Update System
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 2. Install Required Packages
print_status "Installing required packages..."
sudo apt install -y python3 python3-pip python3-venv git postgresql postgresql-contrib curl wget

# 3. Create Application Directory
print_status "Creating application directory..."
sudo mkdir -p /opt/TELEGLAS
sudo chown $CURRENT_USER:$CURRENT_USER /opt/TELEGLAS

# 4. Clone Repository
print_status "Cloning TELEGLAS repository..."
cd /opt/TELEGLAS
if [ -d ".git" ]; then
    print_status "Repository already exists, pulling latest changes..."
    git pull origin master
else
    git clone https://github.com/rcz87/TELEGLAS.git .
fi

# 5. Setup Python Virtual Environment
print_status "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 6. Install Dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 7. Create Required Directories
print_status "Creating required directories..."
mkdir -p logs data

# 8. Setup Environment Configuration
print_status "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_warning "Please edit .env file with your configuration:"
    print_warning "- BOT_TOKEN: Your Telegram bot token"
    print_warning "- ADMIN_USER_ID: Your Telegram user ID"
    print_warning "- COINGLASS_API_KEY: Your CoinGlass API key"
    print_warning "- DATABASE_URL: Your database connection string"
    echo ""
    read -p "Press Enter to continue after configuring .env file..."
    nano .env
else
    print_status ".env file already exists, skipping configuration..."
fi

# 9. Setup Database (PostgreSQL)
print_status "Setting up PostgreSQL database..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Check if database exists
DB_EXISTS=$(sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -w cryptosatx | wc -l)
if [ $DB_EXISTS -eq 0 ]; then
    print_status "Creating database and user..."
    sudo -u postgres psql << EOF
CREATE DATABASE cryptosatx;
CREATE USER cryptosatx_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE cryptosatx TO cryptosatx_user;
\q
EOF
    print_warning "Please update the password in your .env file to match 'your_secure_password_here'"
else
    print_status "Database already exists, skipping creation..."
fi

# 10. Create Systemd Service
print_status "Creating systemd service..."
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

# 11. Configure Firewall
print_status "Configuring firewall..."
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 12. Enable and Start Service
print_status "Enabling and starting TELEGLAS service..."
sudo systemctl daemon-reload
sudo systemctl enable teleglas.service
sudo systemctl start teleglas.service

# 13. Wait for service to start
print_status "Waiting for service to initialize..."
sleep 10

# 14. Check Service Status
print_status "Checking service status..."
if sudo systemctl is-active --quiet teleglas.service; then
    print_status "✅ TELEGLAS service is running successfully!"
else
    print_error "❌ TELEGLAS service failed to start!"
    print_status "Checking logs for errors:"
    sudo journalctl -u teleglas.service --no-pager -l
    exit 1
fi

# 15. Display Status Information
print_status "🎉 TELEGLAS setup completed successfully!"
echo ""
print_status "Service Information:"
echo "  - Service Name: teleglas.service"
echo "  - Status: $(sudo systemctl is-active teleglas.service)"
echo "  - Application Path: /opt/TELEGLAS"
echo "  - Logs Location: /opt/TELEGLAS/logs/"
echo ""
print_status "Useful Commands:"
echo "  - Check status: sudo systemctl status teleglas.service"
echo "  - View logs: sudo journalctl -u teleglas.service -f"
echo "  - Restart service: sudo systemctl restart teleglas.service"
echo "  - Stop service: sudo systemctl stop teleglas.service"
echo "  - Update app: cd /opt/TELEGLAS && git pull && sudo systemctl restart teleglas.service"
echo ""
print_status "Next Steps:"
echo "  1. Test your Telegram bot with /start command"
echo "  2. Monitor logs: sudo journalctl -u teleglas.service -f"
echo "  3. Configure additional features as needed"
echo ""

# 16. Test Application
print_status "Testing application..."
cd /opt/TELEGLAS
source venv/bin/activate

# Simple connection test
python3 -c "
import asyncio
import os
from aiogram import Bot

async def test_connection():
    try:
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            print('❌ BOT_TOKEN not found in environment')
            return False
            
        bot = Bot(token=bot_token)
        info = await bot.get_me()
        print(f'✅ Bot connection successful: @{info.username}')
        return True
    except Exception as e:
        print(f'❌ Bot connection failed: {e}')
        return False

result = asyncio.run(test_connection())
exit(0 if result else 1)
" || print_warning "Bot connection test failed. Please check your BOT_TOKEN in .env file"

print_status "Setup script completed! 🚀"
