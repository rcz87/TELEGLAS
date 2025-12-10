#!/usr/bin/env python3
"""
TELEGLAS GPT API Module
GPT Actions API for clean JSON market data
"""

__version__ = "1.0.0"
__name__ = "teleglas_gpt_api"
__description__ = "Market data API for GPT Actions"

# Export main components
from .gpt_api_main import app
from .config import settings
from .schemas import *
from .auth import *

__all__ = [
    "app",
    "settings",
    # Schema exports
    "BaseResponse",
    "ErrorResponse", 
    "SuccessResponse",
    "RawResponse",
    "WhaleResponse",
    "LiqResponse", 
    "OrderbookResponse",
    "HealthCheckResponse",
    "SupportedSymbolsResponse",
    "InfoResponse",
    # Auth exports
    "api_key_auth",
    "ip_whitelist_auth", 
    "security_headers",
    "request_logger",
    "input_validator"
]
