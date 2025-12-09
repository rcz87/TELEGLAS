#!/bin/bash

# PM2 Deployment Script for TELEGLAS
# Compatible with existing PM2 setup

echo "🚀 TELEGLAS PM2 Deployment"
echo "=========================="

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

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null; then
    print_error "PM2 is not installed. Please install PM2 first:"
    echo "npm install -g pm2"
    exit 1
fi

# Validate environment
print_status "Validating environment..."

# Check Main Bot .env file
if [ ! -f ".env" ]; then
    print_error ".env file not found. Creating from template..."
    cp .env.example .env
    print_warning "Please edit .env file with your TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_CHAT_ID"
    exit 1
fi

# Check Alert Bot .env file
if [ ! -f "ws_alert/.env" ]; then
    print_error "ws_alert/.env file not found. Creating from template..."
    mkdir -p ws_alert
    cp ws_alert/.env.example ws_alert/.env
    print_warning "Please edit ws_alert/.env file with your TELEGRAM_ALERT_TOKEN and TELEGRAM_ALERT_CHANNEL_ID"
    exit 1
fi

# Validate bot tokens are different
MAIN_TOKEN=$(grep "TELEGRAM_BOT_TOKEN=" .env | cut -d'=' -f2)
ALERT_TOKEN=$(grep "TELEGRAM_ALERT_TOKEN=" ws_alert/.env | cut -d'=' -f2)

if [ "$MAIN_TOKEN" = "$ALERT_TOKEN" ]; then
    print_error "Bot tokens must be different! Please update the tokens in .env files"
    exit 1
fi

# Check required directories
mkdir -p logs
mkdir -p data

print_status "Environment validation passed!"

# Stop existing PM2 processes
print_status "Stopping existing PM2 processes..."
pm2 stop teleglas-bot 2>/dev/null || true
pm2 stop teleglas-alert 2>/dev/null || true

# Start Main Bot with PM2
print_status "Starting Main Bot with PM2..."
pm2 start main.py \
    --name "teleglas-bot" \
    --interpreter /usr/bin/python3 \
    --merge-logs \
    --log-date-format "YYYY-MM-DD HH:mm:ss.SSS" \
    --log logs/main-bot.log \
    --error logs/main-bot-error.log \
    --out logs/main-bot-out.log \
    --time

# Start Alert Bot with PM2
print_status "Starting Alert Bot with PM2..."
pm2 start ws_alert/alert_runner.py \
    --name "teleglas-alert" \
    --interpreter /usr/bin/python3 \
    --merge-logs \
    --log-date-format "YYYY-MM-DD HH:mm:ss.SSS" \
    --log logs/alert-bot.log \
    --error logs/alert-bot-error.log \
    --out logs/alert-bot-out.log \
    --time

# Save PM2 configuration
print_status "Saving PM2 configuration..."
pm2 save

# Setup PM2 startup script
print_status "Setting up PM2 startup script..."
pm2 startup

# Display status
print_status "Deployment completed successfully!"
echo ""
echo "📊 PM2 Process Status:"
pm2 status

echo ""
echo "🔍 Useful PM2 Commands:"
echo "  pm2 status                    - Show all processes"
echo "  pm2 logs teleglas-bot         - View main bot logs"
echo "  pm2 logs teleglas-alert       - View alert bot logs"
echo "  pm2 restart teleglas-bot      - Restart main bot"
echo "  pm2 restart teleglas-alert    - Restart alert bot"
echo "  pm2 stop teleglas-bot         - Stop main bot"
echo "  pm2 stop teleglas-alert       - Stop alert bot"
echo "  pm2 monit                     - Monitor processes"
echo "  pm2 delete teleglas-bot       - Delete main bot process"
echo "  pm2 delete teleglas-alert     - Delete alert bot process"

echo ""
echo "🚀 Quick Update Commands:"
echo "  cd /opt/TELEGLAS"
echo "  git pull origin main"
echo "  pm2 restart teleglas-bot"
echo "  pm2 restart teleglas-alert"

echo ""
echo "✅ Both bots are now running with PM2!"
