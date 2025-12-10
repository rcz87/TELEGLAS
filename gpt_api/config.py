#!/usr/bin/env python3
"""
GPT API Configuration
Configuration settings for GPT API service
"""

import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class GPTAPISettings(BaseSettings):
    """GPT API Configuration Settings"""
    
    # API Server Settings
    host: str = Field("0.0.0.0", description="API server host")
    port: int = Field(8000, description="API server port")
    debug: bool = Field(False, description="Enable debug mode")
    
    # API Security Settings
    api_keys: List[str] = Field(default_factory=list, description="List of valid API keys")
    require_auth: bool = Field(True, description="Require API key authentication")
    
    # Rate Limiting Settings
    rate_limit_requests: int = Field(100, description="Requests per minute per API key")
    rate_limit_window: int = Field(60, description="Rate limit window in seconds")
    
    # CORS Settings
    cors_origins: List[str] = Field(default_factory=lambda: ["*"], description="CORS allowed origins")
    cors_methods: List[str] = Field(default_factory=lambda: ["GET", "OPTIONS"], description="CORS allowed methods")
    cors_headers: List[str] = Field(default_factory=lambda: ["*"], description="CORS allowed headers")
    
    # IP Allowlist Settings
    ip_allowlist: List[str] = Field(default_factory=list, description="IP addresses that can access the API")
    require_ip_whitelist: bool = Field(False, description="Require IP to be in allowlist")
    
    # Request Settings
    request_timeout: int = Field(30, description="Request timeout in seconds")
    max_request_size: int = Field(1024 * 1024, description="Max request size in bytes (1MB)")
    
    # Logging Settings
    log_level: str = Field("INFO", description="Logging level")
    log_file: Optional[str] = Field(None, description="Log file path")
    
    # Market Data Settings
    default_symbol: str = Field("BTC", description="Default symbol if none provided")
    max_symbol_length: int = Field(10, description="Maximum symbol length")
    supported_symbols: List[str] = Field(
        default_factory=lambda: [
            "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", 
            "DOT", "MATIC", "LINK", "UNI", "LTC", "ATOM", "FIL", "ETC",
            "XLM", "VET", "THETA", "ICP", "TRX", "EOS", "AAVE", "MKR"
        ],
        description="List of supported trading symbols"
    )
    
    # Whale Settings
    whale_default_limit: int = Field(10, description="Default limit for whale transactions")
    whale_max_limit: int = Field(100, description="Maximum limit for whale transactions")
    whale_default_threshold: float = Field(100000, description="Default whale threshold in USD")
    
    # Orderbook Settings
    orderbook_default_depth: int = Field(20, description="Default orderbook depth")
    orderbook_max_depth: int = Field(100, description="Maximum orderbook depth")
    
    # Health Check Settings
    health_check_interval: int = Field(300, description="Health check interval in seconds")
    service_timeout: int = Field(10, description="Service timeout for health checks")
    
    # Caching Settings
    cache_enabled: bool = Field(True, description="Enable Redis caching")
    cache_ttl: int = Field(300, description="Default cache TTL in seconds")
    cache_warming_enabled: bool = Field(True, description="Enable cache warming")
    redis_url: str = Field("redis://localhost:6379/0", description="Redis connection URL")
    
    # Analytics Settings
    analytics_enabled: bool = Field(True, description="Enable analytics tracking")
    analytics_retention_days: int = Field(30, description="Days to retain analytics data")
    analytics_export_format: str = Field("json", description="Default export format (json/csv)")
    
    # Webhooks Settings
    webhooks_enabled: bool = Field(True, description="Enable webhooks system")
    webhook_max_subscriptions: int = Field(100, description="Maximum webhook subscriptions per API key")
    webhook_rate_limit_seconds: int = Field(30, description="Default webhook rate limit in seconds")
    webhook_max_failures: int = Field(5, description="Maximum failures before webhook deactivation")
    
    # Metadata Settings
    api_version: str = Field("1.0.0", description="API version")
    api_name: str = Field("TELEGLAS GPT API", description="API name")
    api_description: str = Field("Market data API for GPT Actions", description="API description")
    
    # Environment-specific settings
    environment: str = Field("production", description="Environment (development/staging/production)")
    
    class Config:
        env_prefix = "GPT_API_"
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = GPTAPISettings()


def get_allowed_origins() -> List[str]:
    """Get allowed CORS origins based on environment"""
    if settings.environment == "development":
        return ["*"]
    elif settings.environment == "staging":
        return ["http://localhost:3000", "http://localhost:8000"]
    else:  # production
        return ["*"]  # Adjust for production security


def get_rate_limit_per_key() -> int:
    """Get rate limit per API key based on environment"""
    if settings.environment == "development":
        return 1000  # Higher limit for development
    elif settings.environment == "staging":
        return 200
    else:  # production
        return settings.rate_limit_requests


def validate_api_key(api_key: str) -> bool:
    """Validate API key"""
    if not settings.require_auth:
        return True
    return api_key in settings.api_keys


def validate_ip_address(client_ip: str) -> bool:
    """Validate client IP address"""
    if not settings.require_ip_whitelist:
        return True
    return client_ip in settings.ip_allowlist


def is_symbol_supported(symbol: str) -> bool:
    """Check if symbol is supported"""
    return symbol.upper() in settings.supported_symbols


def get_whale_limit(limit: Optional[int]) -> int:
    """Get validated whale limit"""
    if limit is None:
        return settings.whale_default_limit
    return min(max(limit, 1), settings.whale_max_limit)


def get_orderbook_depth(depth: Optional[int]) -> int:
    """Get validated orderbook depth"""
    if depth is None:
        return settings.orderbook_default_depth
    return min(max(depth, 1), settings.orderbook_max_depth)
