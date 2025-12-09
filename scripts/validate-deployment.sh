#!/bin/bash

echo "🔍 Validating dual bot deployment..."

# Check for required environment variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN not found in .env"
    exit 1
fi

if [ -z "$TELEGRAM_ALERT_TOKEN" ]; then
    echo "❌ TELEGRAM_ALERT_TOKEN not found in ws_alert/.env"
    exit 1
fi

# Ensure tokens are different
if [ "$TELEGRAM_BOT_TOKEN" = "$TELEGRAM_ALERT_TOKEN" ]; then
    echo "❌ Bot tokens must be different!"
    exit 1
fi

# Check for required directories
if [ ! -d "logs" ]; then
    echo "❌ logs directory not found"
    exit 1
fi

if [ ! -d "data" ]; then
    echo "❌ data directory not found"
    exit 1
fi

# Check for required files
if [ ! -f ".env" ]; then
    echo "❌ .env file not found"
    exit 1
fi

if [ ! -f "ws_alert/.env" ]; then
    echo "❌ ws_alert/.env file not found"
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found"
    exit 1
fi

echo "✅ Environment validation passed"
