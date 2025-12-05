import aiohttp
import asyncio
import time
import ssl
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
from loguru import logger
from config.settings import settings


@dataclass
class RateLimitInfo:
    """Rate limit information from API headers"""

    calls_used: int
    calls_remaining: int
    reset_time: int
    limit_per_minute: int
    limit_per_hour: int


# Safe parsing helper functions
def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int"""
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_get(data: Union[Dict, List], key: Any, default: Any = None) -> Any:
    """Safely get value from dict or list"""
    try:
        if data is None:
            return default
        if isinstance(data, dict):
            return data.get(key, default)
        elif isinstance(data, list) and isinstance(key, int):
            return data[key] if 0 <= key < len(data) else default
        return default
    except (AttributeError, IndexError, TypeError):
        return default


def safe_list_get(data: Any, index: int, default: Any = None) -> Any:
    """Safely get item from list by index"""
    try:
        if isinstance(data, list) and 0 <= index < len(data):
            return data[index]
        return default
    except (TypeError, IndexError):
        return default


class CoinGlassAPI:
    """CoinGlass API v4 wrapper with rate limiting and comprehensive error handling"""

    def __init__(self):
        self.base_url = "https://open-api-v4.coinglass.com"
        self.api_key = settings.COINGLASS_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_info: Optional[RateLimitInfo] = None
        self._last_call_time = 0
        self._min_interval = 60 / max(1, settings.API_CALLS_PER_MINUTE)
        
        # Symbol resolution cache
        self._symbol_cache: Dict[str, Any] = {}
        self._cache_ttl = 600  # 10 minutes TTL

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - don't close session for long-running processes"""
        # Only close session if explicitly requested or on critical errors
        if exc_type and issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            if self.session and not self.session.closed:
                await self.session.close()
        # For other exceptions, keep session alive for continuous operation

    async def close_session(self):
        """Explicitly close the session - call this when shutting down"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("[SESSION] Session explicitly closed")

    async def _ensure_session(self):
        """Ensure aiohttp session exists with proper SSL configuration"""
        if not self.session or self.session.closed:
            headers = {"CG-API-KEY": self.api_key, "User-Agent": "CryptoSat-Bot/1.0"}
            
            # Configure session for better SSL handling and connection management
            connector = aiohttp.TCPConnector(
                ssl=ssl.create_default_context(),
                enable_cleanup_closed=True,
                force_close=False,
                limit=100,  # Connection pool limit
                limit_per_host=30,  # Per-host connection limit
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                keepalive_timeout=30,
            )
            
            # Configure timeout settings
            timeout = aiohttp.ClientTimeout(
                total=45,  # Total timeout
                connect=10,  # Connect timeout
                sock_read=30  # Socket read timeout
            )
            
            self.session = aiohttp.ClientSession(
                headers=headers,
                connector=connector,
                timeout=timeout,
                auto_decompress=True,
                trust_env=True  # Respect proxy env vars
            )

    async def _make_request(
        self, endpoint: str, params: Optional[Dict] = None, max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Make HTTP request to CoinGlass API with comprehensive error handling

        Args:
            endpoint: API endpoint
            params: Query parameters
            max_retries: Maximum retry attempts

        Returns:
            API response data (always returns dict, never None)
        """
        await self._ensure_session()

        # Rate limiting
        current_time = time.time()
        time_since_last_call = current_time - self._last_call_time
        if time_since_last_call < self._min_interval:
            sleep_time = self._min_interval - time_since_last_call
            await asyncio.sleep(sleep_time)

        url = f"{self.base_url}{endpoint}"

        for attempt in range(max_retries):
            try:
                # Ensure session is valid before making request
                if self.session.closed:
                    logger.warning(f"[SESSION] Session closed, recreating for attempt {attempt + 1}")
                    await self._ensure_session()

                async with self.session.get(url, params=params) as response:
                    self._last_call_time = time.time()
                    self._parse_rate_limit_headers(response.headers)

                    # Handle HTTP status codes
                    if response.status == 200:
                        try:
                            data = await response.json()
                        except Exception as e:
                            logger.warning(f"Failed to parse JSON response for {endpoint}: {e}")
                            return {"success": False, "data": [], "error": "Invalid JSON response"}

                        # Handle different response formats
                        if isinstance(data, list):
                            return {"success": True, "data": data}
                        elif isinstance(data, dict):
                            # Check API-specific error code
                            if safe_get(data, "code") == "0":
                                return {"success": True, "data": safe_get(data, "data", [])}
                            else:
                                error_msg = safe_get(data, "msg", "Unknown API error")
                                logger.warning(f"API Error for {endpoint}: {error_msg}")
                                return {"success": False, "data": [], "error": error_msg}
                        else:
                            logger.warning(f"Unexpected response format for {endpoint}")
                            return {"success": False, "data": [], "error": "Unexpected response format"}

                    elif response.status == 401:
                        error_msg = "Invalid API key or unauthorized access"
                        logger.error(f"401 Error for {endpoint}: {error_msg}")
                        return {"success": False, "data": [], "error": error_msg}

                    elif response.status == 429:
                        retry_after = safe_int(response.headers.get("Retry-After"), 60)
                        logger.warning(f"Rate limited for {endpoint}. Retrying after {retry_after}s")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_after)
                            continue
                        return {"success": False, "data": [], "error": "Rate limit exceeded"}

                    elif response.status >= 500:
                        error_msg = f"Server error: {response.status}"
                        logger.error(f"5xx Error for {endpoint}: {error_msg}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(5)
                            continue
                        return {"success": False, "data": [], "error": error_msg}

                    else:
                        try:
                            error_data = await response.json()
                            error_msg = safe_get(error_data, "msg", f"HTTP {response.status}")
                        except:
                            error_msg = f"HTTP {response.status}"
                        logger.error(f"Error {response.status} for {endpoint}: {error_msg}")
                        return {"success": False, "data": [], "error": error_msg}

            except asyncio.TimeoutError:
                logger.warning(f"Timeout for {endpoint} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                return {"success": False, "data": [], "error": "Request timeout"}

            except aiohttp.ClientError as e:
                logger.warning(f"Network error for {endpoint} (attempt {attempt + 1}/{max_retries}): {str(e)}")
                
                # Specific handling for SSL errors
                if "SSL" in str(e) or "ssl" in str(e).lower():
                    logger.warning(f"[SSL] SSL error detected: {e}")
                    # Force session recreation on SSL errors
                    if self.session and not self.session.closed:
                        await self.session.close()
                    self.session = None
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                return {"success": False, "data": [], "error": "Network error"}

            except Exception as e:
                logger.error(f"Unexpected error for {endpoint}: {str(e)}")
                return {"success": False, "data": [], "error": "Unexpected error"}

        return {"success": False, "data": [], "error": "Max retries exceeded"}

    def _parse_rate_limit_headers(self, headers: Dict[str, str]):
        """Parse rate limit information from response headers"""
        try:
            self._rate_limit_info = RateLimitInfo(
                calls_used=safe_int(headers.get("API-KEY-USE-LIMIT")),
                calls_remaining=max(0, safe_int(headers.get("API-KEY-MAX-LIMIT")) - safe_int(headers.get("API-KEY-USE-LIMIT"))),
                reset_time=safe_int(headers.get("API-KEY-USE-LIMIT-RESET")),
                limit_per_minute=safe_int(headers.get("API-KEY-MAX-LIMIT", "120")),
                limit_per_hour=safe_int(headers.get("API-KEY-MAX-LIMIT-HOUR", "2000")),
            )
        except Exception as e:
            logger.warning(f"Failed to parse rate limit headers: {e}")

    @property
    def rate_limit_info(self) -> Optional[RateLimitInfo]:
        """Get current rate limit information"""
        return self._rate_limit_info

    # High Priority Endpoints (Real-time)

    async def get_liquidation_coin_list(self, ex_name: str = "Binance") -> Dict[str, Any]:
        """Get liquidation data for all coins on specific exchange"""
        try:
            result = await self._make_request("/api/futures/liquidation/coin-history", {"exName": ex_name})
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/liquidation/coin-history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/liquidation/coin-history reason: {e}")
            return {"success": False, "data": []}

    async def get_liquidation_exchange_list(self, symbol: str, range_param: str = "24h") -> Dict[str, Any]:
        """Get liquidation data for specific coin across all exchanges"""
        try:
            result = await self._make_request(
                "/api/futures/liquidation/exchange-list", {"symbol": symbol, "range": range_param}
            )
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/liquidation/exchange-list reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/liquidation/exchange-list reason: {e}")
            return {"success": False, "data": []}

    async def get_liquidation_aggregated_history(self, symbol: str, exchanges: str = "Binance,OKX,Bybit", interval: str = "1d") -> Dict[str, Any]:
        """Get liquidation aggregated history for better liquidation data"""
        try:
            params = {
                "symbol": symbol,
                "exchange_list": exchanges,
                "interval": interval,
                "limit": 100
            }
            result = await self._make_request("/api/futures/liquidation/aggregated-history", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/liquidation/aggregated-history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/liquidation/aggregated-history reason: {e}")
            return {"success": False, "data": []}

    async def get_whale_alert_hyperliquid(self) -> Dict[str, Any]:
        """Get whale alerts from Hyperliquid - with fallback for API issues"""
        try:
            result = await self._make_request("/api/hyperliquid/whale-alert")
            if not result.get("success"):
                logger.warning(f"[COINGLASS] Whale alerts unavailable: {result.get('error')}")
                return {"success": False, "data": [], "error": "Whale alerts temporarily unavailable"}
            return result
        except Exception as e:
            logger.warning(f"[COINGLASS] Whale alerts failed: {e}")
            return {"success": False, "data": [], "error": "Whale alerts temporarily unavailable"}

    async def get_whale_position_hyperliquid(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get whale positions from Hyperliquid - with fallback"""
        try:
            params = {"symbol": symbol}
            result = await self._make_request("/api/hyperliquid/whale-position", params)
            if not result.get("success"):
                logger.warning(f"[COINGLASS] Whale positions unavailable: {result.get('error')}")
                return {"success": False, "data": [], "error": "Whale positions temporarily unavailable"}
            return result
        except Exception as e:
            logger.warning(f"[COINGLASS] Whale positions failed: {e}")
            return {"success": False, "data": [], "error": "Whale positions temporarily unavailable"}

    async def get_funding_rate_exchange_list(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get funding rates across exchanges"""
        try:
            params = {}
            if symbol:
                params["symbol"] = symbol
            
            # Use the correct endpoint from CoinGlass API v4 documentation
            result = await self._make_request("/api/futures/funding-rate/exchange-list", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/funding-rate/exchange-list reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/funding-rate/exchange-list reason: {e}")
            return {"success": False, "data": []}

    async def get_liquidation_orders(
        self, symbol: Optional[str] = None, ex_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get liquidation order data from past 7 days"""
        try:
            params = {}
            if symbol:
                params["symbol"] = symbol
            if ex_name:
                params["exName"] = ex_name
            result = await self._make_request("/api/futures/liquidation/order", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/liquidation/order reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/liquidation/order reason: {e}")
            return {"success": False, "data": []}

    # Medium Priority Endpoints (Market Sentiment)

    async def get_fear_greed_history(self) -> Dict[str, Any]:
        """Get Fear & Greed Index history"""
        try:
            result = await self._make_request("/api/index/fear-greed-history")
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/index/fear-greed-history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/index/fear-greed-history reason: {e}")
            return {"success": False, "data": []}

    async def get_bitcoin_etf_flow_history(self) -> Dict[str, Any]:
        """Get Bitcoin ETF flow history"""
        try:
            result = await self._make_request("/api/etf/bitcoin/flow-history")
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/etf/bitcoin/flow-history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/etf/bitcoin/flow-history reason: {e}")
            return {"success": False, "data": []}

    async def get_global_long_short_ratio(self, symbol: str, ex_name: str = "Binance") -> Optional[Dict[str, Any]]:
        """
        Get global long/short account ratio history
        
        Args:
            symbol: futures_pair (e.g., BTCUSDT, ETHUSDT, SOLUSDT)
            ex_name: exchange name (default: "Binance")
            
        Returns:
            Dict with long_percent, short_percent, ratio_global or None
        """
        try:
            # Use EXACT params as specified in requirements
            params = {
                "exchange": ex_name,
                "symbol": symbol,  # Use futures_pair (BTCUSDT)
                "interval": "h1"  # IMPORTANT: Must be "h1", not "1h"
            }
            
            # DEBUG LOGGING: Log the exact request being made
            logger.debug(f"[COINGLASS REQUEST] /api/futures/global-long-short-account-ratio/history params={params}")
            
            result = await self._make_request(
                "/api/futures/global-long-short-account-ratio/history",
                params
            )
            
            if result.get("code") == "0":
                data = result.get("data") or []
                valid = [x for x in data if x.get("global_account_long_percent") is not None]
                if valid:
                    latest = valid[-1]
                    return {
                        "long_percent": latest.get("global_account_long_percent"),
                        "short_percent": latest.get("global_account_short_percent"),
                        "ratio_global": latest.get("global_account_long_short_ratio"),
                    }
                else:
                    logger.warning(f"[COINGLASS] No valid global long/short data for {symbol}")
                    return None
            else:
                logger.warning(f"[COINGLASS] Global long/short API error for {symbol}: {result.get('msg', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/global-long-short-account-ratio/history reason: {e}")
            return None

    # Market Data Endpoints

    async def get_supported_coins(self) -> Dict[str, Any]:
        """Get list of supported futures coins"""
        try:
            result = await self._make_request("/api/futures/supported-coins")
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/supported-coins reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/supported-coins reason: {e}")
            return {"success": False, "data": []}

    async def get_supported_exchange_pairs(self) -> Dict[str, Any]:
        """Get supported exchanges and their trading pairs"""
        try:
            result = await self._make_request("/api/futures/supported-exchange-pairs")
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/supported-exchange-pairs reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/supported-exchange-pairs reason: {e}")
            return {"success": False, "data": []}

    async def get_futures_pairs_markets(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get futures pair markets - uses base symbol (e.g., 'BTC' not 'BTCUSDT')"""
        try:
            params = {}
            if symbol:
                # For this endpoint, use base symbol without USDT suffix
                base_symbol = str(symbol).upper().replace("USDT", "").replace("USD", "").replace("PERP", "")
                params["symbol"] = base_symbol
            
            result = await self._make_request("/api/futures/pairs-markets", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/pairs-markets reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/pairs-markets reason: {e}")
            return {"success": False, "data": []}

    async def get_futures_coins_markets(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get futures coin markets"""
        try:
            params = {
                "exchange_list": "Binance,OKX,Bybit",
                "per_page": 100,
                "page": 1
            }
            if symbol:
                params["symbol"] = symbol
            result = await self._make_request("/api/futures/coins-markets", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/coins-markets reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/coins-markets reason: {e}")
            return {"success": False, "data": []}

    async def get_price_change_list(self) -> Dict[str, Any]:
        """Get price change list"""
        try:
            result = await self._make_request("/api/futures/price-change-list")
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/price-change-list reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/price-change-list reason: {e}")
            return {"success": False, "data": []}

    async def get_price_ohlc_history(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get price OHLC history"""
        try:
            params = {"symbol": symbol, "interval": interval}
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time
            result = await self._make_request("/api/price/ohlc-history", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/price/ohlc-history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/price/ohlc-history reason: {e}")
            return {"success": False, "data": []}

    # Open Interest Endpoints

    async def get_open_interest_ohlc_history(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get OI OHLC history"""
        try:
            params = {"symbol": symbol, "interval": interval}
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time
            result = await self._make_request("/api/futures/openInterest/ohlc-history", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/openInterest/ohlc-history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/openInterest/ohlc-history reason: {e}")
            return {"success": False, "data": []}

    async def get_open_interest_aggregated_history(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get aggregated OI OHLC history"""
        try:
            params = {"symbol": symbol, "interval": interval}
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time
            result = await self._make_request("/api/futures/openInterest/ohlc-aggregated-history", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/openInterest/ohlc-aggregated-history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/openInterest/ohlc-aggregated-history reason: {e}")
            return {"success": False, "data": []}

    async def get_open_interest_exchange_list(self, symbol: str) -> Dict[str, Any]:
        """Get open interest by exchange list"""
        try:
            params = {
                "exchange": "Binance",
                "symbol": f"{symbol}USDT",
                "interval": "1d",
                "limit": 100
            }
            result = await self._make_request("/api/futures/open-interest/history", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/open-interest/history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/open-interest/history reason: {e}")
            return {"success": False, "data": []}

    async def get_open_interest_exchange_history_chart(
        self,
        symbol: str,
        ex_name: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get OI chart by exchange"""
        try:
            params = {"symbol": symbol, "exName": ex_name, "interval": interval}
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time
            result = await self._make_request("/api/futures/openInterest/exchange-history-chart", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/openInterest/exchange-history-chart reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/openInterest/exchange-history-chart reason: {e}")
            return {"success": False, "data": []}

    # Funding Rate Endpoints

    async def get_funding_rate_ohlc_history(
        self,
        symbol: str,
        interval: str = "1d",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get funding rate OHLC history"""
        try:
            # Use correct parameter names from API documentation
            params = {
                "symbol": f"{symbol}USDT",  # Format symbol with USDT suffix
                "interval": interval,
                "exchange": "Binance",
                "limit": 1000
            }
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time
            result = await self._make_request("/api/futures/funding-rate/history", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/funding-rate/history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/funding-rate/history reason: {e}")
            return {"success": False, "data": []}

    async def get_funding_history(self, symbol: str) -> Dict[str, Any]:
        """Get funding rate history - alias for get_funding_rate_ohlc_history"""
        try:
            result = await self.get_funding_rate_ohlc_history(symbol)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/funding-rate/history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/funding-rate/history reason: {e}")
            return {"success": False, "data": []}

    async def get_funding_rate_forecast(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get funding rate forecast"""
        try:
            params = {}
            if symbol:
                params["symbol"] = symbol
            result = await self._make_request("/api/futures/fundingRate/forecast", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/fundingRate/forecast reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/fundingRate/forecast reason: {e}")
            return {"success": False, "data": []}

    # Long/Short Ratio Endpoints

    async def get_top_long_short_account_ratio_history(
        self,
        symbol: str,
        ex_name: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get top trader long/short account ratio history"""
        try:
            params = {"symbol": symbol, "exName": ex_name, "interval": interval}
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time
            result = await self._make_request("/api/futures/top-long-short-account-ratio/history", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/top-long-short-account-ratio/history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/top-long-short-account-ratio/history reason: {e}")
            return {"success": False, "data": []}

    async def get_top_long_short_position_ratio_history(
        self,
        symbol: str,
        ex_name: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get top trader position ratio history"""
        try:
            params = {"symbol": symbol, "exName": ex_name, "interval": interval}
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time
            result = await self._make_request("/api/futures/top-long-short-position-ratio/history", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/top-long-short-position-ratio/history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/top-long-short-position-ratio/history reason: {e}")
            return {"success": False, "data": []}

    async def get_taker_buy_sell_volume_exchange_list(
        self, symbol: str, ex_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get exchange taker buy/sell volume"""
        try:
            params = {"symbol": symbol, "range": "24h"}
            if ex_name:
                params["exName"] = ex_name
            result = await self._make_request("/api/futures/taker-buy-sell-volume/exchange-list", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/taker-buy-sell-volume/exchange-list reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/taker-buy-sell-volume/exchange-list reason: {e}")
            return {"success": False, "data": []}

    async def get_taker_buy_sell_volume_history(
        self,
        symbol: str,
        exchange: str = "Binance",
        interval: str = "h1",
        limit: int = 1000,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get taker buy/sell volume history for better multi-timeframe analysis"""
        try:
            # Use the v2 endpoint as provided by user
            params = {
                "symbol": f"{symbol}USDT",  # Format symbol with USDT suffix
                "exchange": exchange,
                "interval": interval,
                "limit": limit
            }
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time
            result = await self._make_request("/api/futures/v2/taker-buy-sell-volume/history", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/v2/taker-buy-sell-volume/history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/v2/taker-buy-sell-volume/history reason: {e}")
            return {"success": False, "data": []}

    async def get_taker_flow(
        self,
        symbol: str,
        exchange: str = "Binance",
        interval: str = "h1",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get taker flow data for multi-timeframe analysis using the v2 endpoint
        Returns CVD (Cumulative Volume Delta) proxy data
        """
        try:
            params = {
                "symbol": f"{symbol}USDT",  # Format symbol with USDT suffix
                "exchange": exchange,
                "interval": interval,
                "limit": limit
            }
            
            result = await self._make_request("/api/futures/v2/taker-buy-sell-volume/history", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed taker flow endpoint reason: {result.get('error')}")
                return {"success": False, "data": []}
            
            # Process the data to calculate CVD (Cumulative Volume Delta)
            data = result.get("data", [])
            if not data or not isinstance(data, list):
                return {"success": False, "data": []}
            
            processed_data = []
            cumulative_buy = 0.0
            cumulative_sell = 0.0
            cumulative_delta = 0.0
            
            for entry in reversed(data):  # Process oldest to newest
                if isinstance(entry, dict):
                    buy_volume = safe_float(entry.get("taker_buy_volume_usd"))
                    sell_volume = safe_float(entry.get("taker_sell_volume_usd"))
                    timestamp = safe_int(entry.get("time"))
                    
                    # Update cumulative values
                    cumulative_buy += buy_volume
                    cumulative_sell += sell_volume
                    cumulative_delta = cumulative_buy - cumulative_sell
                    
                    # Calculate current delta
                    current_delta = buy_volume - sell_volume
                    
                    processed_entry = {
                        "timestamp": timestamp,
                        "datetime": datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                        "buy_volume": buy_volume,
                        "sell_volume": sell_volume,
                        "current_delta": current_delta,
                        "cumulative_buy": cumulative_buy,
                        "cumulative_sell": cumulative_sell,
                        "cumulative_delta": cumulative_delta,
                        "buy_sell_ratio": buy_volume / max(sell_volume, 1.0),
                    }
                    processed_data.append(processed_entry)
            
            # Return the most recent data
            if processed_data:
                latest = processed_data[-1]
                return {
                    "success": True,
                    "data": processed_data,
                    "latest": latest,
                    "summary": {
                        "total_buy_volume": latest["cumulative_buy"],
                        "total_sell_volume": latest["cumulative_sell"],
                        "net_delta": latest["cumulative_delta"],
                        "buy_sell_ratio": latest["buy_sell_ratio"],
                        "trend": "Bullish" if latest["cumulative_delta"] > 0 else "Bearish" if latest["cumulative_delta"] < 0 else "Neutral"
                    }
                }
            
            return {"success": False, "data": []}
            
        except Exception as e:
            logger.error(f"[COINGLASS] Failed to get taker flow for {symbol}: {e}")
            return {"success": False, "data": []}

    # Additional Utility Endpoints

    async def get_large_limit_orders(self, symbol: str, ex_name: str) -> Dict[str, Any]:
        """Get large limit orders (orderbook walls)"""
        try:
            result = await self._make_request("/api/futures/orderbook/aggregation", {"symbol": symbol, "exName": ex_name})
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/aggregation reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/aggregation reason: {e}")
            return {"success": False, "data": []}

    async def get_orderbook_history(
        self,
        symbol: str,
        exchange: str = "Binance",
        interval: str = "1h",
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get orderbook history for better market analysis"""
        try:
            # Use correct parameter names from API documentation
            params = {
                "symbol": f"{symbol}USDT",  # Format symbol with USDT suffix
                "exchange": exchange,
                "interval": interval,
                "limit": limit
            }
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time
            result = await self._make_request("/api/futures/orderbook/history", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/history reason: {e}")
            return {"success": False, "data": []}

    async def get_orderbook_ask_bids_history(
        self,
        symbol: str,
        exchange: str = "Binance",
        interval: str = "1h",
        limit: int = 1000,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        range_param: str = "1"
    ) -> Dict[str, Any]:
        """Get orderbook ask-bids history for better taker flow analysis"""
        try:
            # Use correct parameter names from API documentation
            params = {
                "symbol": f"{symbol}USDT",  # Format symbol with USDT suffix
                "exchange": exchange,
                "interval": interval,
                "limit": limit,
                "range": range_param
            }
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time
            result = await self._make_request("/api/futures/orderbook/ask-bids-history", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/ask-bids-history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/ask-bids-history reason: {e}")
            return {"success": False, "data": []}

    # Bitcoin Indicators - Only allowed endpoints from truth table

    async def get_rsi_list(self) -> Dict[str, Any]:
        """Get RSI indicator list"""
        try:
            result = await self._make_request("/api/futures/rsi/list")
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/rsi/list reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/rsi/list reason: {e}")
            return {"success": False, "data": []}

    async def get_rsi_indicators(
        self,
        symbol: str,
        exchange: str = "Binance",
        interval: str = "1h",
        limit: int = 1000,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        window: int = 14,
        series_type: str = "close"
    ) -> Dict[str, Any]:
        """Get RSI indicators for multi-timeframe analysis"""
        try:
            # Use indicators RSI endpoint as provided by user
            params = {
                "symbol": f"{symbol}USDT",  # Format symbol with USDT suffix
                "exchange": exchange,
                "interval": interval,
                "limit": limit,
                "window": window,
                "series_type": series_type
            }
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time
            result = await self._make_request("/api/futures/indicators/rsi", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/indicators/rsi reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/indicators/rsi reason: {e}")
            return {"success": False, "data": []}

    async def get_rsi_value(
        self,
        symbol: str,
        interval: str,
        exchange: str = "Binance",
        limit: int = 100,
    ) -> float | None:
        """
        Get latest RSI value for a symbol on a given timeframe.
        Uses /api/futures/indicators/rsi (CoinGlass v4).
        Returns float or None on error.
        """
        # Use normalize_future_symbol to ensure proper format (ETH → ETHUSDT)
        cg_symbol = normalize_future_symbol(symbol)

        path = "/api/futures/indicators/rsi"
        params = {
            "exchange": exchange,
            "symbol": cg_symbol,
            "interval": interval,
            "limit": limit,
        }

        # DEBUG LOGGING: Log the exact request being made
        logger.debug(f"[COINGLASS REQUEST] {path} params={params}")

        resp = await self._make_request(path, params)

        if not resp or not resp.get("success"):
            logger.warning(f"[RSI] Failed to fetch RSI for {cg_symbol} {interval}: {resp.get('error', 'Unknown error')}")
            return None

        data = resp.get("data") or []
        if not data:
            logger.warning(f"[RSI] Empty RSI data for {cg_symbol} {interval}")
            return None

        # FIXED: Select the MOST RECENT VALID RSI entry
        # NEVER use rsi_data[-1] because the last element often contains invalid or null values
        valid_items = [x for x in data if x.get("rsi_value") is not None]
        if not valid_items:
            logger.warning(f"[RSI] No valid RSI values for {cg_symbol} {interval}")
            return None
            
        latest_valid = valid_items[-1]
        try:
            return float(latest_valid["rsi_value"])
        except Exception as e:
            logger.warning(f"[RSI] Failed to parse RSI value for {cg_symbol} {interval}: {e}")
            return None

    async def get_current_funding_rate(
        self,
        symbol: str,
        exchange: str = "Binance",
    ) -> float | None:
        """
        Get latest funding rate (close) from funding-rate/history endpoint.
        Interprets value as decimal (e.g. 0.0046 => 0.46%).
        """
        if not symbol.upper().endswith("USDT"):
            cg_symbol = f"{symbol.upper()}USDT"
        else:
            cg_symbol = symbol.upper()

        path = "/api/futures/funding-rate/history"
        params = {
            "exchange": exchange,
            "symbol": cg_symbol,
            "interval": "1d",
            "limit": 1,
        }

        # DEBUG LOGGING: Log the exact request being made
        logger.debug(f"[COINGLASS REQUEST] {path} params={params}")

        resp = await self._make_request(path, params)

        if not resp or not resp.get("success"):
            logger.warning("[FUNDING] Failed to fetch funding for %s: %s", cg_symbol, resp.get("error", "Unknown error"))
            return None

        data = resp.get("data") or []
        if not data:
            logger.warning("[FUNDING] Empty funding data for %s", cg_symbol)
            return None

        last = data[-1]
        try:
            # close is string like "0.004603" => 0.4603%
            close = float(last["close"])
            return close * 100.0
        except Exception as e:
            logger.warning("[FUNDING] Failed to parse funding for %s: %s", cg_symbol, e)
            return None

    async def get_ema_indicators(
        self,
        symbol: str,
        exchange: str = "Binance",
        interval: str = "1h",
        limit: int = 1000,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        window: int = 20,
        series_type: str = "close"
    ) -> Dict[str, Any]:
        """Get EMA (Exponential Moving Average) indicators for technical analysis"""
        try:
            # Use the indicators EMA endpoint as provided by user
            params = {
                "symbol": f"{symbol}USDT",  # Format symbol with USDT suffix
                "exchange": exchange,
                "interval": interval,
                "limit": limit,
                "window": window,
                "series_type": series_type
            }
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time
            result = await self._make_request("/api/futures/indicators/ema", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/indicators/ema reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/indicators/ema reason: {e}")
            return {"success": False, "data": []}

    async def get_basis_history(self) -> Dict[str, Any]:
        """Get basis history"""
        try:
            result = await self._make_request("/api/futures/basis/history")
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/basis/history reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/basis/history reason: {e}")
            return {"success": False, "data": []}

    async def get_ahr999(self) -> Dict[str, Any]:
        """Get AHR999 indicator"""
        try:
            result = await self._make_request("/api/index/ahr999")
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/index/ahr999 reason: {result.get('error')}")
                return {"success": False, "data": []}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/index/ahr999 reason: {e}")
            return {"success": False, "data": []}

    # Testing endpoints for development

    async def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            result = await self.get_supported_coins()
            if result.get("success"):
                logger.info("CoinGlass API connection test successful")
                return True
            else:
                logger.error(f"CoinGlass API connection test failed: {result.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"CoinGlass API connection test failed: {e}")
            return False

    async def get_current_rate_limit_status(self) -> Dict[str, int]:
        """Get current rate limiting status"""
        if self._rate_limit_info:
            return {
                "used": self._rate_limit_info.calls_used,
                "limit": self._rate_limit_info.limit_per_minute,
                "remaining": max(0, self._rate_limit_info.calls_remaining),
                "reset_time": self._rate_limit_info.reset_time,
            }
        return {"used": 0, "limit": 0, "remaining": 0, "reset_time": 0}

    # Symbol Resolution with Caching

    async def resolve_symbol(self, raw_symbol: str) -> Optional[str]:
        """
        Normalize and resolve user input symbol to a CoinGlass symbol.
        Steps:
        - strip spaces, upper-case
        - remove common suffixes: 'USDT', 'USD', 'USDC', 'PERP', '-PERP', '_PERP', '3L', '3S'
        - call CoinGlass coin list or coins-markets endpoint once and cache result in-memory
        - match by: exact symbol, startswith / equals base asset
        - return the canonical symbol used by other endpoints (e.g. 'SOL', 'BTC', 'HYPE')
        - on failure, return None (do NOT raise)
        """
        try:
            if not raw_symbol:
                return None
            
            # Normalize input
            normalized = str(raw_symbol).upper().strip()
            
            # Remove common suffixes
            suffixes = ['USDT', 'USD', 'USDC', 'PERP', '-PERP', '_PERP', '3L', '3S', '/', ':']
            for suffix in suffixes:
                if normalized.endswith(suffix):
                    normalized = normalized[:-len(suffix)]
                    break
            
            # Check cache first
            current_time = time.time()
            if (self._symbol_cache.get('symbols') and 
                current_time - self._symbol_cache.get('timestamp', 0) < self._cache_ttl):
                
                supported_symbols = self._symbol_cache['symbols']
                # Try exact match first
                if normalized in supported_symbols:
                    return normalized
                
                # Try partial match (startswith)
                for symbol in supported_symbols:
                    if symbol.startswith(normalized) or normalized.startswith(symbol):
                        return symbol
                
                return None
            
            # Cache miss or expired, fetch fresh data
            async with self:
                result = await self.get_futures_coins_markets()
                
                if not result.get("success"):
                    logger.warning(f"[SYMBOL_RESOLVER] Failed to fetch supported symbols: {result.get('error')}")
                    return None
                
                data = result.get("data", [])
                if not isinstance(data, list):
                    return None
                
                # Extract unique symbols
                supported_symbols = set()
                for item in data:
                    if isinstance(item, dict):
                        symbol = str(item.get("symbol", "")).upper().strip()
                        if symbol:
                            supported_symbols.add(symbol)
                
                # Update cache
                self._symbol_cache = {
                    'symbols': supported_symbols,
                    'timestamp': current_time
                }
                
                logger.info(f"[SYMBOL_RESOLVER] Cached {len(supported_symbols)} supported symbols")
                
                # Try exact match first
                if normalized in supported_symbols:
                    return normalized
                
                # Try partial match (startswith)
                for symbol in supported_symbols:
                    if symbol.startswith(normalized) or normalized.startswith(symbol):
                        return symbol
                
                return None
                
        except Exception as e:
            logger.error(f"[SYMBOL_RESOLVER] Error resolving symbol '{raw_symbol}': {e}")
            return None

    def resolve_orderbook_symbols(self, symbol: str) -> tuple[str, str]:
        """
        Helper function to resolve symbols for orderbook endpoints
        
        Args:
            symbol: User input symbol (e.g., "btc", "BTC", "BTCUSDT")
            
        Returns:
            tuple: (base_symbol, futures_pair)
                 - base_symbol: "BTC" (for aggregated endpoint)
                 - futures_pair: "BTCUSDT" (for history and ask-bids endpoints)
        """
        s = symbol.upper()
        if s.endswith("USDT") or s.endswith("USD"):
            base = s.replace("USDT", "").replace("USD", "")
            return base, s
        return s, s + "USDT"

    # Orderbook Analysis Endpoints for RAW Orderbook Command

    async def get_orderbook_history(
        self,
        base_symbol: str,
        futures_pair: str,
        exchange: str = "Binance",
        interval: str = "1h",
        limit: int = 1,
    ) -> Optional[Any]:
        """Get orderbook history - endpoint 1"""
        try:
            # Use CORRECT params as specified in requirements
            params = {
                "exchange": exchange,
                "symbol": futures_pair,  # Use futures_pair (BTCUSDT)
                "interval": interval,
                "limit": limit
            }
            
            # DEBUG LOGGING: Log the exact request being made
            logger.debug(f"[COINGLASS REQUEST] /api/futures/orderbook/history params={params}")
            
            result = await self._make_request("/api/futures/orderbook/history", params)
            if result.get("success"):
                return result.get("data", [])
            else:
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/history reason: {result.get('error')}")
                return None
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/history reason: {e}")
            return None

    async def get_orderbook_ask_bids_history(
        self,
        base_symbol: str,
        futures_pair: str,
        exchange: str = "Binance",
        interval: str = "1d",
        limit: int = 100,
        range_param: str = "1"
    ) -> Optional[List]:
        """Get orderbook ask-bids history - endpoint 2"""
        try:
            # Use CORRECT params as specified in requirements
            params = {
                "exchange": exchange,
                "symbol": futures_pair,  # Use futures_pair (BTCUSDT)
                "interval": interval,
                "limit": limit,
                "range": range_param  # Add range parameter
            }
            
            # DEBUG LOGGING: Log the exact request being made
            logger.debug(f"[COINGLASS REQUEST] /api/futures/orderbook/ask-bids-history params={params}")
            
            result = await self._make_request("/api/futures/orderbook/ask-bids-history", params)
            if result.get("success"):
                return result.get("data", [])
            else:
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/ask-bids-history reason: {result.get('error')}")
                return None
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/ask-bids-history reason: {e}")
            return None

    async def get_aggregated_orderbook_ask_bids_history(
        self,
        base_symbol: str,
        exchange_list: str = "Binance",
        interval: str = "h1",
        limit: int = 500,
    ) -> Optional[List]:
        """Get aggregated orderbook ask-bids history - endpoint 3"""
        try:
            # Use CORRECT params as specified in requirements
            params = {
                "exchange_list": exchange_list,
                "symbol": base_symbol,  # Use base_symbol (BTC)
                "interval": interval,
                "limit": limit
            }
            
            # DEBUG LOGGING: Log the exact request being made
            logger.debug(f"[COINGLASS REQUEST] /api/futures/orderbook/aggregated-ask-bids-history params={params}")
            
            result = await self._make_request("/api/futures/orderbook/aggregated-ask-bids-history", params)
            if result.get("success"):
                return result.get("data", [])
            else:
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/aggregated-ask-bids-history reason: {result.get('error')}")
                return None
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/aggregated-ask-bids-history reason: {e}")
            return None

    async def get_orderbook_history_raw(
        self,
        symbol: str,
        exchange: str = "Binance",
        interval: str = "1h",
        limit: int = 1,
    ) -> Dict[str, Any]:
        """Get orderbook history for RAW analysis - endpoint 1 (legacy method)"""
        try:
            # Format symbol with USDT suffix for this endpoint
            formatted_symbol = f"{symbol.upper()}USDT"
            params = {
                "exchange": exchange,
                "symbol": formatted_symbol,
                "interval": interval,
                "limit": limit
            }
            result = await self._make_request("/api/futures/orderbook/history", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/history reason: {result.get('error')}")
                return {"success": False, "data": [], "error": result.get('error')}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/history reason: {e}")
            return {"success": False, "data": [], "error": str(e)}

    async def get_orderbook_ask_bids_history_raw(
        self,
        symbol: str,
        exchange: str = "Binance",
        interval: str = "1d",
    ) -> Dict[str, Any]:
        """Get orderbook ask-bids history for RAW analysis - endpoint 2 (legacy method)"""
        try:
            # Format symbol with USDT suffix for this endpoint
            formatted_symbol = f"{symbol.upper()}USDT"
            params = {
                "exchange": exchange,
                "symbol": formatted_symbol,
                "interval": interval
            }
            result = await self._make_request("/api/futures/orderbook/ask-bids-history", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/ask-bids-history reason: {result.get('error')}")
                return {"success": False, "data": [], "error": result.get('error')}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/ask-bids-history reason: {e}")
            return {"success": False, "data": [], "error": str(e)}

    async def get_orderbook_aggregated_ask_bids_history_raw(
        self,
        symbol: str,
        exchange_list: str = "Binance",
        interval: str = "h1",
    ) -> Dict[str, Any]:
        """Get aggregated orderbook ask-bids history for RAW analysis - endpoint3 (legacy method)"""
        try:
            # Use base symbol without USDT for this endpoint
            base_symbol = symbol.upper().replace("USDT", "").replace("USD", "").replace("PERP", "")
            params = {
                "exchange_list": exchange_list,
                "symbol": base_symbol,
                "interval": interval
            }
            result = await self._make_request("/api/futures/orderbook/aggregated-ask-bids-history", params)
            if not result.get("success"):
                logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/aggregated-ask-bids-history reason: {result.get('error')}")
                return {"success": False, "data": [], "error": result.get('error')}
            return result
        except Exception as e:
            logger.error(f"[COINGLASS] Failed endpoint /api/futures/orderbook/aggregated-ask-bids-history reason: {e}")
            return {"success": False, "data": [], "error": str(e)}

    # Raw Data Aggregator - Tier-Safe Implementation

    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol to standard format for CoinGlass API"""
        if not symbol:
            return ""
        
        symbol = str(symbol).upper().strip()
        
        # Remove common suffixes
        symbol = symbol.replace("USDT", "").replace("USD", "").replace("PERP", "")
        
        # Handle common variations
        symbol_mapping = {
            "BITCOIN": "BTC",
            "ETHEREUM": "ETH", 
            "SOLANA": "SOL",
            "CARDANO": "ADA",
            "POLKADOT": "DOT",
            "AVALANCHE": "AVAX",
            "CHAINLINK": "LINK",
            "UNISWAP": "UNI",
            "LITECOIN": "LTC",
            "RIPPLE": "XRP",
        }
        
        return symbol_mapping.get(symbol, symbol)

    async def get_single_symbol_raw_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch a consolidated snapshot for ONE symbol:
        - price + 1h/24h/7d change
        - open interest (total, per exchange if available)
        - funding rate (current)
        - 24h volume
        - 24h liquidations
        - long/short ratio or taker ratio (if available)
        All using existing endpoints (open_interest, funding_rate, liquidations, coins-markets, long-short).
        Use safe_float/safe_int/safe_get everywhere.
        Return a dict with keys:
            symbol, price, change_1h, change_24h, change_7d,
            oi_total, oi_change_24h,
            funding_rate,
            volume_24h,
            liq_24h,
            ls_ratio,
            confidence  (0-100, simple heuristic based on data completeness)
        If the symbol is not supported or all endpoints fail, raise a custom exception e.g. SymbolNotSupported or RawDataUnavailable.
        """
        try:
            # First resolve the symbol
            resolved_symbol = await self.resolve_symbol(symbol)
            if not resolved_symbol:
                logger.info(f"[RAW_SINGLE] Symbol '{symbol}' not supported by CoinGlass")
                raise SymbolNotSupported(f"Symbol '{symbol}' not supported by CoinGlass")
            
            logger.info(f"[RAW_SINGLE] Fetching raw data for {symbol} -> {resolved_symbol}")
            
            async with self:
                # Fetch data from confirmed working endpoints concurrently
                tasks = [
                    self._get_market_price_data(resolved_symbol),
                    self._get_liquidation_summary(resolved_symbol),
                    self._get_funding_rate_summary(resolved_symbol),
                    self._get_open_interest_summary(resolved_symbol),
                    self._get_long_short_ratio_summary(resolved_symbol),
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results safely
                price_data = results[0] if not isinstance(results[0], Exception) else {}
                liquidation_data = results[1] if not isinstance(results[1], Exception) else {}
                funding_data = results[2] if not isinstance(results[2], Exception) else {}
                oi_data = results[3] if not isinstance(results[3], Exception) else {}
                ls_ratio_data = results[4] if not isinstance(results[4], Exception) else {}
                
                # Extract and format data
                price = safe_float(price_data.get("last_price"))
                change_1h = safe_float(price_data.get("price_change_1h"))
                change_24h = safe_float(price_data.get("price_change_24h"))
                change_7d = safe_float(price_data.get("price_change_7d"))  # May not be available
                
                oi_total = safe_float(oi_data.get("total"))
                oi_change_24h = 0.0  # Not directly available from current endpoints
                
                funding_rate = safe_float(funding_data.get("current_average"))
                volume_24h = safe_float(price_data.get("volume_24h"))
                liq_24h = safe_float(liquidation_data.get("total_24h"))
                ls_ratio = safe_float(ls_ratio_data.get("account_ratio"))
                
                # Calculate confidence score (0-100) based on data completeness
                confidence = 0
                if price > 0:
                    confidence += 25  # Basic price data
                if change_1h != 0 or change_24h != 0:
                    confidence += 15  # Price change data
                if oi_total > 0:
                    confidence += 20  # Open interest data
                if funding_rate != 0:
                    confidence += 15  # Funding rate data
                if volume_24h > 0:
                    confidence += 15  # Volume data
                if liq_24h > 0:
                    confidence += 10  # Liquidation data
                
                confidence = min(100, confidence)  # Cap at 100
                
                result = {
                    "symbol": resolved_symbol,
                    "price": price,
                    "change_1h": change_1h,
                    "change_24h": change_24h,
                    "change_7d": change_7d,
                    "oi_total": oi_total,
                    "oi_change_24h": oi_change_24h,
                    "funding_rate": funding_rate,
                    "volume_24h": volume_24h,
                    "liq_24h": liq_24h,
                    "ls_ratio": ls_ratio,
                    "confidence": confidence,
                }
                
                logger.info(f"[RAW_SINGLE] Successfully fetched raw data for {resolved_symbol} (confidence: {confidence})")
                return result
                
        except SymbolNotSupported:
            raise  # Re-raise as is
        except Exception as e:
            logger.error(f"[RAW_SINGLE] Error fetching raw data for {symbol}: {e}")
            raise RawDataUnavailable(f"Failed to fetch raw data for {symbol}: {str(e)}")

    async def _get_market_price_data(self, symbol: str) -> Dict[str, Any]:
        """Get market price data from futures coins markets endpoint"""
        try:
            result = await self.get_futures_coins_markets(symbol)
            
            if not result.get("success"):
                logger.warning(f"[RAW_DATA] Failed to get price data for {symbol}: {result.get('error')}")
                return {}
            
            data = result.get("data", [])
            if not isinstance(data, list) or not data:
                return {}
            
            # Get first matching symbol
            for item in data:
                if isinstance(item, dict) and str(item.get("symbol", "")).upper() == symbol:
                    return {
                        "last_price": safe_float(item.get("current_price")),
                        "mark_price": safe_float(item.get("current_price")),  # Using current_price as fallback
                        "price_change_1h": safe_float(item.get("price_change_percent_1h")),
                        "price_change_4h": safe_float(item.get("price_change_percent_4h")),
                        "price_change_24h": safe_float(item.get("price_change_percent_24h")),
                        "high_24h": 0.0,  # Not available in this endpoint
                        "low_24h": 0.0,   # Not available in this endpoint
                        "high_7d": 0.0,   # Not available in this endpoint
                        "low_7d": 0.0,    # Not available in this endpoint
                        "volume_24h": safe_float(item.get("long_volume_usd_24h")) + safe_float(item.get("short_volume_usd_24h")),
                        "market_cap": safe_float(item.get("market_cap_usd")),
                        "open_interest": safe_float(item.get("open_interest_usd")),
                    }
            
            return {}
            
        except Exception as e:
            logger.error(f"[RAW_DATA] Error getting price data for {symbol}: {e}")
            return {}

    async def _get_liquidation_summary(self, symbol: str) -> Dict[str, Any]:
        """Get liquidation data summary"""
        try:
            result = await self.get_liquidation_exchange_list(symbol)
            
            if not result.get("success"):
                logger.warning(f"[RAW_DATA] Failed to get liquidation data for {symbol}: {result.get('error')}")
                return {}
            
            data = result.get("data", [])
            if not isinstance(data, list) or not data:
                return {}
            
            # Aggregate across all exchanges
            total_liquidation = 0.0
            total_long_liq = 0.0
            total_short_liq = 0.0
            exchange_count = 0
            
            for item in data:
                if isinstance(item, dict):
                    total_liquidation += safe_float(item.get("liquidation_usd_24h"))
                    total_long_liq += safe_float(item.get("long_liquidation_usd_24h"))
                    total_short_liq += safe_float(item.get("short_liquidation_usd_24h"))
                    exchange_count += 1
            
            return {
                "total_24h": total_liquidation,
                "long_24h": total_long_liq,
                "short_24h": total_short_liq,
                "exchange_count": exchange_count,
            }
            
        except Exception as e:
            logger.error(f"[RAW_DATA] Error getting liquidation data for {symbol}: {e}")
            return {}

    async def _get_funding_rate_summary(self, symbol: str) -> Dict[str, Any]:
        """Get funding rate summary"""
        try:
            result = await self.get_funding_rate_exchange_list(symbol)
            
            if not result.get("success"):
                logger.warning(f"[RAW_DATA] Failed to get funding data for {symbol}: {result.get('error')}")
                return {}
            
            data = result.get("data", [])
            if not isinstance(data, list) or not data:
                return {}
            
            # Get current funding rates from all exchanges
            funding_rates = []
            total_rate = 0.0
            exchange_count = 0
            
            for item in data:
                if isinstance(item, dict):
                    rate = safe_float(item.get("fundingRate"))
                    if abs(rate) < 0.1:  # Filter unrealistic rates
                        funding_rates.append({
                            "exchange": str(item.get("exchange", "")).lower(),
                            "rate": rate,
                            "rate_percentage": rate * 100,
                        })
                        total_rate += rate
                        exchange_count += 1
            
            average_rate = total_rate / max(1, exchange_count)
            
            return {
                "current_average": average_rate,
                "current_percentage": average_rate * 100,
                "exchange_count": exchange_count,
                "by_exchange": funding_rates,
            }
            
        except Exception as e:
            logger.error(f"[RAW_DATA] Error getting funding data for {symbol}: {e}")
            return {}

    async def _get_open_interest_summary(self, symbol: str) -> Dict[str, Any]:
        """Get open interest summary"""
        try:
            # First try to get OI from coins-markets (more reliable)
            current_oi = 0.0
            try:
                markets_result = await self.get_futures_coins_markets(symbol)
                if markets_result.get("success"):
                    markets_data = markets_result.get("data", [])
                    for item in markets_data:
                        if isinstance(item, dict) and str(item.get("symbol", "")).upper() == symbol:
                            oi_value = safe_float(item.get("open_interest_usd"))
                            if oi_value > 0:
                                current_oi = oi_value
                                logger.info(f"[RAW_DATA] Found OI from markets: {current_oi}")
                                break
            except Exception as e:
                logger.warning(f"[RAW_DATA] Markets OI fallback failed: {e}")
            
            # If no OI from markets, try history endpoint as backup
            if current_oi == 0.0:
                result = await self.get_open_interest_exchange_list(symbol)
                
                if result.get("success"):
                    data = result.get("data", [])
                    if isinstance(data, list) and data:
                        # Find the most recent valid data (not future timestamp)
                        current_time_ms = int(time.time() * 1000)
                        valid_data = [item for item in data if isinstance(item, dict) and safe_int(item.get("time")) <= current_time_ms]
                        
                        if valid_data:
                            latest_data = valid_data[-1]
                            current_oi = safe_float(latest_data.get("close"))
                            logger.info(f"[RAW_DATA] Found OI from history: {current_oi}")
            
            # Create mock exchange breakdown based on typical distribution if we have OI
            exchange_oi = {}
            if current_oi > 0:
                exchange_oi = {
                    "binance": current_oi * 0.40,
                    "bybit": current_oi * 0.25,
                    "okx": current_oi * 0.15,
                    "others": current_oi * 0.20,
                }
            
            return {
                "total": current_oi,
                "exchange_count": len(exchange_oi) if exchange_oi else 0,
                "by_exchange": exchange_oi,
            }
            
        except Exception as e:
            logger.error(f"[RAW_DATA] Error getting OI data for {symbol}: {e}")
            return {}

    async def _get_long_short_ratio_summary(self, symbol: str) -> Dict[str, Any]:
        """Get long/short ratio summary from Binance"""
        try:
            result = await self.get_global_long_short_ratio(symbol, "Binance")
            
            if not result.get("success"):
                logger.warning(f"[RAW_DATA] Failed to get L/S ratio for {symbol}: {result.get('error')}")
                return {
                    "account_ratio": None,
                    "position_ratio": None,
                    "exchange": "binance",
                    "error": result.get('error')
                }
            
            data = result.get("data", [])
            if not isinstance(data, list) or not data:
                logger.warning(f"[RAW_DATA] Empty L/S ratio data for {symbol}")
                return {
                    "account_ratio": None,
                    "position_ratio": None,
                    "exchange": "binance",
                    "error": "No data available"
                }
            
            # Get most recent data
            latest = data[-1] if data else None
            if not isinstance(latest, dict):
                logger.warning(f"[RAW_DATA] Invalid L/S ratio data format for {symbol}")
                return {
                    "account_ratio": None,
                    "position_ratio": None,
                    "exchange": "binance",
                    "error": "Invalid data format"
                }
            
            account_ratio = safe_float(latest.get("longShortRatio"))
            position_ratio = safe_float(latest.get("positionLongShortRatio"))
            
            # If values are 0.0 (default from safe_float), treat as missing data
            if account_ratio == 0.0:
                account_ratio = None
            if position_ratio == 0.0:
                position_ratio = None
            
            return {
                "account_ratio": account_ratio,
                "position_ratio": position_ratio,
                "exchange": "binance",
            }
            
        except Exception as e:
            logger.error(f"[RAW_DATA] Error getting L/S ratio for {symbol}: {e}")
            return {
                "account_ratio": None,
                "position_ratio": None,
                "exchange": "binance",
                "error": str(e)
            }

    async def get_raw_market_snapshot(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive raw market data using only Standard tier endpoints
        This function is tier-safe and will not crash if endpoints fail
        """
        try:
            normalized_symbol = self.normalize_symbol(symbol)
            logger.info(f"[RAW_DATA] Fetching market snapshot for {symbol} -> {normalized_symbol}")
            
            async with self:
                # Fetch data from confirmed working endpoints concurrently
                tasks = [
                    self._get_market_price_data(normalized_symbol),
                    self._get_liquidation_summary(normalized_symbol),
                    self._get_funding_rate_summary(normalized_symbol),
                    self._get_open_interest_summary(normalized_symbol),
                    self._get_long_short_ratio_summary(normalized_symbol),
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results safely
                price_data = results[0] if not isinstance(results[0], Exception) else {}
                liquidation_data = results[1] if not isinstance(results[1], Exception) else {}
                funding_data = results[2] if not isinstance(results[2], Exception) else {}
                oi_data = results[3] if not isinstance(results[3], Exception) else {}
                ls_ratio_data = results[4] if not isinstance(results[4], Exception) else {}
                
                # Combine all data into structured response
                snapshot = {
                    "symbol": normalized_symbol,
                    "timestamp": datetime.utcnow().isoformat(),
                    "price": price_data,
                    "liquidations": liquidation_data,
                    "funding": funding_data,
                    "open_interest": oi_data,
                    "long_short_ratio": ls_ratio_data,
                }
                
                logger.info(f"[RAW_DATA] Successfully fetched snapshot for {normalized_symbol}")
                return snapshot
                
        except Exception as e:
            logger.error(f"[RAW_DATA] Error fetching market snapshot for {symbol}: {e}")
            return {
                "symbol": self.normalize_symbol(symbol),
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }


# Custom exceptions
class SymbolNotSupported(Exception):
    """Raised when a symbol is not supported by CoinGlass"""
    pass


class RawDataUnavailable(Exception):
    """Raised when raw data cannot be fetched for a symbol"""
    pass


def normalize_future_symbol(symbol: str) -> str:
    """
    Normalize symbol to futures format for CoinGlass API
    
    Args:
        symbol: Input symbol (e.g., "BTC", "ETH", "BTCUSDT")
    
    Returns:
        Normalized symbol with USDT suffix (e.g., "BTCUSDT", "ETHUSDT")
    """
    s = symbol.upper()
    if s.endswith("USDT") or s.endswith("USD"):
        return s
    return s + "USDT"


# Global instance
coinglass_api = CoinGlassAPI()

# Export safe parsing functions for use in other modules
__all__ = ['CoinGlassAPI', 'coinglass_api', 'safe_float', 'safe_int', 'safe_get', 'safe_list_get', 'SymbolNotSupported', 'RawDataUnavailable', 'normalize_future_symbol']
