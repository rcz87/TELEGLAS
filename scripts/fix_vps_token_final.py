#!/usr/bin/env python3
"""
VPS Token Fix Script - Updates VPS with correct Telegram token and settings
"""
import os
import sys
from pathlib import Path

def create_vps_env_file():
    """Create the correct .env file for VPS"""
    env_content = """# Production Configuration - TELEGLAS Bot

# Core Bot Configuration
TELEGRAM_BOT_TOKEN=7659959497:AAGwJJvKRfp44MDZxHcjaJdAwBtnDtmZ8SI
TELEGRAM_ADMIN_CHAT_ID=5899681906
TELEGRAM_ALERT_CHANNEL_ID=5899681906

# Access Control
WHITELISTED_USERS=5899681906

# Feature Flags
ENABLE_WHALE_ALERTS=true
ENABLE_BROADCAST_ALERTS=false
ENABLE_MONITORING=false

# API Configuration
COINGLASS_API_KEY=8794ae1bac584fda9841b5c8bf273d3d
API_CALLS_PER_MINUTE=60

# Thresholds
WHALE_TRANSACTION_THRESHOLD_USD=500000
LIQUIDATION_THRESHOLD_USD=1000000
FUNDING_RATE_THRESHOLD=0.01

# Timing (seconds)
WHALE_POLL_INTERVAL=30
LIQUIDATION_POLL_INTERVAL=60
FUNDING_RATE_POLL_INTERVAL=300

# Database Configuration
DATABASE_URL=sqlite:///data/teleglas.db

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/teleglas.log
"""
    
    # Backup existing .env if it exists
    if os.path.exists('.env'):
        print("Backing up existing .env file...")
        os.rename('.env', '.env.backup.' + str(int(os.path.getmtime('.env'))))
    
    # Write new .env file
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Created new .env file with correct token")

def update_settings_py():
    """Update settings.py with explicit .env loading"""
    settings_content = '''import os
from dotenv import load_dotenv
from typing import List
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Load environment variables from project root with explicit override
env_file = PROJECT_ROOT / '.env'
if env_file.exists():
    load_dotenv(env_file, override=True)
    print(f"Loaded .env from: {env_file}")
else:
    # Fallback to default loading
    load_dotenv()
    print("Loaded .env using default search paths")

class Settings:
    """Application settings and configuration"""
    
    # CoinGlass API
    COINGLASS_API_KEY: str = os.getenv("COINGLASS_API_KEY")
    COINGLASS_BASE_URL: str = os.getenv("COINGLASS_BASE_URL", "https://open-api-v4.coinglass.com")
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_ADMIN_CHAT_ID: str = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
    TELEGRAM_ALERT_CHANNEL_ID: str = os.getenv("TELEGRAM_ALERT_CHANNEL_ID")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/cryptosat.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Rate Limiting
    API_CALLS_PER_MINUTE: int = int(os.getenv("API_CALLS_PER_MINUTE", "120"))
    API_CALLS_PER_HOUR: int = int(os.getenv("API_CALLS_PER_HOUR", "2000"))
    
    # Alert Thresholds
    LIQUIDATION_THRESHOLD_USD: float = float(os.getenv("LIQUIDATION_THRESHOLD_USD", "1000000"))
    WHALE_TRANSACTION_THRESHOLD_USD: float = float(os.getenv("WHALE_TRANSACTION_THRESHOLD_USD", "500000"))
    EXTREME_FUNDING_RATE: float = float(os.getenv("EXTREME_FUNDING_RATE", "0.01"))
    
    # Polling Intervals
    LIQUIDATION_POLL_INTERVAL: int = int(os.getenv("LIQUIDATION_POLL_INTERVAL", "10"))
    WHALE_POLL_INTERVAL: int = int(os.getenv("WHALE_POLL_INTERVAL", "5"))
    FUNDING_RATE_POLL_INTERVAL: int = int(os.getenv("FUNDING_RATE_POLL_INTERVAL", "30"))
    SENTIMENT_POLL_INTERVAL: int = int(os.getenv("SENTIMENT_POLL_INTERVAL", "60"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/cryptosat.log")
    
    # Bot Configuration
    TELEGRAM_OWNER_ID: int = int(os.getenv("TELEGRAM_OWNER_ID", "0"))
    TELEGRAM_ADMIN_CHAT_ID: str = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
    TELEGRAM_ALERT_CHANNEL_ID: str = os.getenv("TELEGRAM_ALERT_CHANNEL_ID")
    TELEGRAM_WHITELIST_IDS: str = os.getenv("TELEGRAM_WHITELIST_IDS", "")
    TELEGRAM_PRIVATE_BOT: bool = os.getenv("TELEGRAM_PRIVATE_BOT", "true").lower() == "true"
    
    # WHITELISTED_USERS - primary whitelist configuration
    @property
    def WHITELISTED_USERS(self):
        """Get WHITELISTED_USERS from environment (supports comma-separated list or single number)"""
        return os.getenv("WHITELISTED_USERS", "")
    
    @property
    def whitelist_ids(self) -> set[int]:
        """Get whitelist as a set for efficient lookup"""
        ids = set()
        if self.TELEGRAM_WHITELIST_IDS:
            for part in self.TELEGRAM_WHITELIST_IDS.split(","):
                part = part.strip()
                if part:
                    try:
                        ids.add(int(part))
                    except ValueError:
                        from loguru import logger
                        logger.warning(f"Invalid user id in TELEGRAM_WHITELIST_IDS: {part!r}")
        return ids
    
    ENABLE_BROADCAST_ALERTS: bool = os.getenv("ENABLE_BROADCAST_ALERTS", "true").lower() == "true"
    ENABLE_WHALE_ALERTS: bool = os.getenv("ENABLE_WHALE_ALERTS", "true").lower() == "true"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate critical configuration settings"""
        required_vars = [
            "COINGLASS_API_KEY",
            "TELEGRAM_BOT_TOKEN"
        ]
        
        for var in required_vars:
            if not getattr(cls, var):
                raise ValueError(f"Missing required environment variable: {var}")
        
        return True

# Global settings instance
settings = Settings()
'''
    
    # Backup existing settings.py if it exists
    if os.path.exists('config/settings.py'):
        print("Backing up existing settings.py...")
        os.rename('config/settings.py', 'config/settings.py.backup.' + str(int(os.path.getmtime('config/settings.py'))))
    
    # Write new settings.py
    os.makedirs('config', exist_ok=True)
    with open('config/settings.py', 'w') as f:
        f.write(settings_content)
    
    print("✅ Updated config/settings.py with explicit .env loading")

def verify_configuration():
    """Verify the configuration is correct"""
    print("\n=== Verifying Configuration ===")
    
    # Load the updated settings
    sys.path.insert(0, '.')
    from config.settings import settings
    
    print(f"✅ Token: {settings.TELEGRAM_BOT_TOKEN[:20]}...{settings.TELEGRAM_BOT_TOKEN[-10:]}")
    print(f"✅ Admin Chat ID: {settings.TELEGRAM_ADMIN_CHAT_ID}")
    print(f"✅ Whitelisted Users: {settings.WHITELISTED_USERS}")
    print(f"✅ Whale Alerts: {settings.ENABLE_WHALE_ALERTS}")
    print(f"✅ API Key: {settings.COINGLASS_API_KEY[:10]}...{settings.COINGLASS_API_KEY[-5:]}")
    
    # Validate critical settings
    try:
        settings.validate()
        print("✅ All required settings validated!")
        return True
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

def main():
    """Main fix function"""
    print("=== VPS Token Fix Script ===")
    print("This script will fix the Telegram bot token issue on VPS")
    
    # Check if we're in the right directory
    if not os.path.exists('main.py'):
        print("❌ Error: main.py not found. Please run this script from the project root.")
        sys.exit(1)
    
    print(f"📍 Working directory: {os.getcwd()}")
    
    try:
        # Step 1: Create correct .env file
        create_vps_env_file()
        
        # Step 2: Update settings.py
        update_settings_py()
        
        # Step 3: Verify configuration
        if verify_configuration():
            print("\n🎉 VPS token fix completed successfully!")
            print("\n📋 Next steps:")
            print("1. Restart the bot: systemctl restart teleglas")
            print("2. Check status: systemctl status teleglas")
            print("3. View logs: journalctl -u teleglas -f")
        else:
            print("\n❌ VPS token fix failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error during fix: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
