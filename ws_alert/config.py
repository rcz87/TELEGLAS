"""
Configuration untuk WS Alert Module

Modul ini membaca konfigurasi khusus untuk bot alert yang terpisah dari bot utama.
"""

import os
import logging
from typing import List, Dict
from pathlib import Path

# Get project root directory (same as main bot)
PROJECT_ROOT = Path(__file__).parent.parent

# Load environment variables from project root
env_file = PROJECT_ROOT / '.env'
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file, override=True)
    print(f"[WS_ALERT] Loaded .env from: {env_file}")
else:
    from dotenv import load_dotenv
    load_dotenv()
    print("[WS_ALERT] Loaded .env using default search paths")

logger = logging.getLogger("ws_alert.config")


class AlertConfig:
    """Smart Alert Engine Configuration with Thresholds & Cooldowns"""
    
    # Symbol group definitions
    SYMBOL_GROUPS = {
        "MAJORS": {
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "liq_min_usd": 500000,      # 500k
            "whale_min_usd": 1000000,   # 1M
            "cooldown_sec": 300         # 5 menit
        },
        "LARGE_CAP": {
            "symbols": ["BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT"],
            "liq_min_usd": 200000,      # 200k
            "whale_min_usd": 500000,    # 500k
            "cooldown_sec": 450         # 7.5 menit
        },
        "MID_CAP": {
            "symbols": [],  # Default for other coins
            "liq_min_usd": 100000,      # 100k
            "whale_min_usd": 200000,    # 200k
            "cooldown_sec": 600         # 10 menit
        }
    }
    
    @classmethod
    def get_symbol_group(cls, symbol: str) -> str:
        """Get group name for a symbol"""
        for group_name, group_config in cls.SYMBOL_GROUPS.items():
            if symbol in group_config["symbols"]:
                return group_name
        
        # Default to MID_CAP for unknown symbols
        return "MID_CAP"
    
    @classmethod
    def get_liq_threshold(cls, symbol: str) -> float:
        """Get liquidation threshold for symbol"""
        group = cls.get_symbol_group(symbol)
        return cls.SYMBOL_GROUPS[group]["liq_min_usd"]
    
    @classmethod
    def get_whale_threshold(cls, symbol: str) -> float:
        """Get whale trade threshold for symbol"""
        group = cls.get_symbol_group(symbol)
        return cls.SYMBOL_GROUPS[group]["whale_min_usd"]
    
    @classmethod
    def get_cooldown_seconds(cls, symbol: str, alert_type: str) -> int:
        """Get cooldown seconds for symbol and alert type"""
        group = cls.get_symbol_group(symbol)
        return cls.SYMBOL_GROUPS[group]["cooldown_sec"]


class AlertSettings:
    """Settings khusus untuk Alert Bot"""
    
    def __init__(self):
        # Alert Bot Token (BERBEDA dari bot utama)
        self.TELEGRAM_ALERT_TOKEN: str = os.getenv("TELEGRAM_ALERT_TOKEN")
        
        # Default chat/channel untuk testing dan production
        self.DEFAULT_ALERT_CHAT_ID: str = os.getenv("TELEGRAM_ALERT_CHANNEL_ID", "")
        self.DEFAULT_TEST_CHAT_ID: str = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
        
        # CoinGlass API (sama dengan bot utama)
        self.COINGLASS_API_KEY: str = os.getenv("COINGLASS_API_KEY")
        self.COINGLASS_API_KEY_WS: str = os.getenv("COINGLASS_API_KEY_WS", "")
        self.COINGLASS_BASE_URL: str = os.getenv("COINGLASS_BASE_URL", "https://open-api-v4.coinglass.com")
        
        # Alert Thresholds (sama dengan bot utama)
        self.WHALE_TRANSACTION_THRESHOLD_USD: float = float(os.getenv("WHALE_TRANSACTION_THRESHOLD_USD", "500000"))
        self.LIQUIDATION_THRESHOLD_USD: float = float(os.getenv("LIQUIDATION_THRESHOLD_USD", "1000000"))
        self.EXTREME_FUNDING_RATE: float = float(os.getenv("EXTREME_FUNDING_RATE", "0.01"))
        
        # Polling Intervals untuk alert
        self.WHALE_POLL_INTERVAL: int = int(os.getenv("WHALE_POLL_INTERVAL", "30"))
        self.LIQUIDATION_POLL_INTERVAL: int = int(os.getenv("LIQUIDATION_POLL_INTERVAL", "60"))
        
        # Rate Limiting
        self.API_CALLS_PER_MINUTE: int = int(os.getenv("API_CALLS_PER_MINUTE", "120"))
        
        # Logging
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE: str = os.getenv("LOG_FILE", "logs/ws_alert.log")
        
        # Database (sama dengan bot utama untuk shared data)
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/teleglas.db")
        
        # Feature Flags untuk alert bot
        self.ENABLE_WHALE_ALERTS: bool = os.getenv("ENABLE_WHALE_ALERTS", "true").lower() == "true"
        self.ENABLE_LIQUIDATION_ALERTS: bool = os.getenv("ENABLE_LIQUIDATION_ALERTS", "false").lower() == "true"
        self.ENABLE_FUNDING_ALERTS: bool = os.getenv("ENABLE_FUNDING_ALERTS", "false").lower() == "true"
        
        # Alert Debounce settings
        self.WHALE_DEBOUNCE_MINUTES: int = int(os.getenv("WHALE_DEBOUNCE_MINUTES", "5"))
        self.LIQUIDATION_DEBOUNCE_MINUTES: int = int(os.getenv("LIQUIDATION_DEBOUNCE_MINUTES", "2"))
        
        # WebSocket Ping Configuration (Poin 2 - Ping interval configuration)
        self.WS_PING_INTERVAL: int = int(os.getenv("WS_PING_INTERVAL", "20"))  # seconds
        self.WS_PING_TIMEOUT: int = int(os.getenv("WS_PING_TIMEOUT", "60"))  # seconds
        self.WS_MIN_PING_INTERVAL: int = int(os.getenv("WS_MIN_PING_INTERVAL", "10"))  # seconds
        self.WS_MAX_PING_INTERVAL: int = int(os.getenv("WS_MAX_PING_INTERVAL", "120"))  # seconds
        self.WS_ADAPTIVE_PING_ENABLED: bool = os.getenv("WS_ADAPTIVE_PING_ENABLED", "true").lower() == "true"
        
        # Authentication & Privacy Configuration (Poin 3)
        self.API_KEY_ROTATION_ENABLED: bool = os.getenv("API_KEY_ROTATION_ENABLED", "false").lower() == "true"
        self.API_KEY_ROTATION_INTERVAL_HOURS: int = int(os.getenv("API_KEY_ROTATION_INTERVAL_HOURS", "24"))
        self.REQUEST_SIGNING_ENABLED: bool = os.getenv("REQUEST_SIGNING_ENABLED", "true").lower() == "true"
        self.PRIVATE_DATA_MASKING: bool = os.getenv("PRIVATE_DATA_MASKING", "true").lower() == "true"
        self.RATE_LIMIT_PER_AUTH_KEY: int = int(os.getenv("RATE_LIMIT_PER_AUTH_KEY", "60"))  # per minute
        self.AUTH_TOKEN_EXPIRY_HOURS: int = int(os.getenv("AUTH_TOKEN_EXPIRY_HOURS", "12"))
        self.ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
        self.HMAC_SECRET_KEY: str = os.getenv("HMAC_SECRET_KEY", "default-hmac-secret-change-in-production")
        
        # Privacy thresholds
        self.PRIVATE_DATA_THRESHOLD_USD: float = float(os.getenv("PRIVATE_DATA_THRESHOLD_USD", "1000000"))  # 1M
        self.MASK_SENSITIVE_FIELDS: bool = os.getenv("MASK_SENSITIVE_FIELDS", "true").lower() == "true"
        
        # Smart Alert Configuration
        self.alert_config = AlertConfig()
        
        # Default chat IDs (for testing)
        self._alert_chat_ids = None
    
    def validate(self) -> bool:
        """Validasi konfigurasi kritis untuk alert bot"""
        required_vars = [
            "TELEGRAM_ALERT_TOKEN",
            "COINGLASS_API_KEY"
        ]
        
        for var in required_vars:
            if not getattr(self, var):
                raise ValueError(f"[WS_ALERT] Missing required environment variable: {var}")
        
        # Validasi token tidak sama dengan bot utama
        main_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if self.TELEGRAM_ALERT_TOKEN == main_bot_token:
            raise ValueError("[WS_ALERT] ALERT_TOKEN harus berbeda dengan BOT_TOKEN utama!")
        
        return True
    
    @property
    def alert_chat_ids(self) -> List[str]:
        """List of chat IDs untuk mengirim alerts"""
        if self._alert_chat_ids is None:
            self._alert_chat_ids = []
            
            # Priority: Alert channel dulu
            if self.DEFAULT_ALERT_CHAT_ID:
                self._alert_chat_ids.append(self.DEFAULT_ALERT_CHAT_ID)
            
            # Fallback: Admin chat
            if self.DEFAULT_TEST_CHAT_ID and self.DEFAULT_TEST_CHAT_ID not in self._alert_chat_ids:
                self._alert_chat_ids.append(self.DEFAULT_TEST_CHAT_ID)
        
        return self._alert_chat_ids
    
    @property
    def coinglass_api_key_ws(self) -> str:
        """Get WebSocket API key with validation"""
        key = self.COINGLASS_API_KEY_WS
        if not key or key == "YOUR_KEY_HERE":
            logger.warning("[WS_ALERT] COINGLASS_API_KEY_WS not configured - WebSocket features disabled")
        return key


# Global settings instance
alert_settings = AlertSettings()
