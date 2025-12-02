# Compatibility wrapper for services.coinglass_api
# This module re-exports all the correct, production-ready implementation from coinglass_api
# to maintain backwards compatibility with existing imports.

from services.coinglass_api import (
    CoinGlassAPI,
    coinglass_api,
    safe_float,
    safe_int,
    safe_get,
    safe_list_get,
    RateLimitInfo,
)

# Re-export everything for backwards compatibility
__all__ = [
    "CoinGlassAPI",
    "coinglass_api", 
    "safe_float",
    "safe_int",
    "safe_get",
    "safe_list_get",
    "RateLimitInfo",
]
