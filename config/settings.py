import os
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
    WHALE_TRANSACTION_THRESHOLD_USD: float = float(os.getenv("WHALE_TRANSACTION_THRESHOLD_USD", "100000"))
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
