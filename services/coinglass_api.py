import aiohttp
import asyncio
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
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

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if not self.session or self.session.closed:
            headers = {"CG-API-KEY": self.api_key, "User-Agent": "CryptoSat-Bot/1.0"}
            self.session = aiohttp.ClientSession(headers=headers)

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
                async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
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
        return await self._make_request("/api/futures/liquidation/coin-list", {"exName": ex_name})

    async def get_liquidation_exchange_list(self, symbol: str, range_param: str = "24h") -> Dict[str, Any]:
        """Get liquidation data for specific coin across all exchanges"""
        return await self._make_request(
            "/api/futures/liquidation/exchange-list", {"symbol": symbol, "range": range_param}
        )

    async def get_whale_alert_hyperliquid(self) -> Dict[str, Any]:
        """Get whale alerts from Hyperliquid"""
        result = await self._make_request("/api/hyperliquid/whale-alert")
        # Fallback to alternative endpoint if primary fails
        if not result.get("success"):
            logger.warning("Primary whale alert endpoint failed, trying alternative")
            result = await self._make_request("/api/hyperliquid/whale-position")
        return result

    async def get_whale_position_hyperliquid(self) -> Dict[str, Any]:
        """Get whale positions from Hyperliquid"""
        return await self._make_request("/api/hyperliquid/whale-position")

    async def get_funding_rate_exchange_list(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get funding rates across exchanges"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        result = await self._make_request("/api/futures/fundingRate/exchange-list", params)
        # Fallback to alternative endpoint if primary fails
        if not result.get("success"):
            logger.warning("Primary funding rate endpoint failed, trying alternative")
            result = await self._make_request("/api/futures/fundingRate/accumulated-exchange-list", params)
        return result

    async def get_liquidation_orders(
        self, symbol: Optional[str] = None, ex_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get liquidation order data from past 7 days"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        if ex_name:
            params["exName"] = ex_name
        return await self._make_request("/api/futures/liquidation/order", params)

    # Medium Priority Endpoints (Market Sentiment)

    async def get_fear_greed_history(self) -> Dict[str, Any]:
        """Get Fear & Greed Index history"""
        return await self._make_request("/api/index/fear-greed-history")

    async def get_bitcoin_etf_flow_history(self) -> Dict[str, Any]:
        """Get Bitcoin ETF flow history"""
        return await self._make_request("/api/etf/bitcoin/flow-history")

    async def get_global_long_short_ratio(self, symbol: str, ex_name: str) -> Dict[str, Any]:
        """Get global long/short account ratio history"""
        return await self._make_request(
            "/api/futures/global-long-short-account-ratio/history",
            {"symbol": symbol, "exName": ex_name},
        )

    # Market Data Endpoints

    async def get_supported_coins(self) -> Dict[str, Any]:
        """Get list of supported futures coins"""
        return await self._make_request("/api/futures/supported-coins")

    async def get_supported_exchange_pairs(self) -> Dict[str, Any]:
        """Get supported exchanges and their trading pairs"""
        return await self._make_request("/api/futures/supported-exchange-pairs")

    async def get_futures_pairs_markets(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get futures pair markets"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request("/api/futures/pairs-markets", params)

    async def get_futures_coins_markets(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get futures coin markets"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request("/api/futures/coins-markets", params)

    async def get_price_change_list(self) -> Dict[str, Any]:
        """Get price change list"""
        return await self._make_request("/api/futures/price-change-list")

    async def get_price_ohlc_history(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get price OHLC history"""
        params = {"symbol": symbol, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request("/api/price/ohlc-history", params)

    # Open Interest Endpoints

    async def get_open_interest_ohlc_history(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get OI OHLC history"""
        params = {"symbol": symbol, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request("/api/futures/openInterest/ohlc-history", params)

    async def get_open_interest_aggregated_history(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get aggregated OI OHLC history"""
        params = {"symbol": symbol, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request("/api/futures/openInterest/ohlc-aggregated-history", params)

    async def get_open_interest_exchange_list(self, symbol: str) -> Dict[str, Any]:
        """Get open interest by exchange list"""
        return await self._make_request("/api/futures/openInterest/exchange-list", {"symbol": symbol})

    async def get_open_interest_exchange_history_chart(
        self,
        symbol: str,
        ex_name: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get OI chart by exchange"""
        params = {"symbol": symbol, "exName": ex_name, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request("/api/futures/openInterest/exchange-history-chart", params)

    # Funding Rate Endpoints

    async def get_funding_rate_ohlc_history(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get funding rate OHLC history"""
        params = {"symbol": symbol, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request("/api/futures/fundingRate/ohlc-history", params)

    async def get_funding_rate_oi_weight_ohlc_history(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get OI-weighted funding rate OHLC history"""
        params = {"symbol": symbol, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request("/api/futures/fundingRate/oi-weight-ohlc-history", params)

    async def get_funding_rate_vol_weight_ohlc_history(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get volume-weighted funding rate OHLC history"""
        params = {"symbol": symbol, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request("/api/futures/fundingRate/vol-weight-ohlc-history", params)

    async def get_funding_rate_accumulated_exchange_list(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get cumulative funding rate list"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request("/api/futures/fundingRate/accumulated-exchange-list", params)

    async def get_funding_rate_arbitrage(self) -> Dict[str, Any]:
        """Get funding arbitrage opportunities"""
        return await self._make_request("/api/futures/fundingRate/arbitrage")

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
        params = {"symbol": symbol, "exName": ex_name, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request("/api/futures/top-long-short-account-ratio/history", params)

    async def get_top_long_short_position_ratio_history(
        self,
        symbol: str,
        ex_name: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get top trader position ratio history"""
        params = {"symbol": symbol, "exName": ex_name, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request("/api/futures/top-long-short-position-ratio/history", params)

    async def get_taker_buy_sell_volume_exchange_list(
        self, symbol: str, ex_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get exchange taker buy/sell volume"""
        params = {"symbol": symbol}
        if ex_name:
            params["exName"] = ex_name
        return await self._make_request("/api/futures/taker-buy-sell-volume/exchange-list", params)

    # Additional Utility Endpoints

    async def get_large_limit_orders(self, symbol: str, ex_name: str) -> Dict[str, Any]:
        """Get large limit orders (orderbook walls)"""
        return await self._make_request("/api/futures/orderbook/large-limit-order", {"symbol": symbol, "exName": ex_name})

    async def get_taker_buy_sell_volume_history(
        self,
        symbol: str,
        ex_name: Optional[str] = None,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get taker buy/sell volume history"""
        params = {"symbol": symbol, "interval": interval}
        if ex_name:
            params["exName"] = ex_name
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request("/api/futures/taker-buy-sell-volume/history", params)

    # Bitcoin Indicators

    async def get_bitcoin_rainbow_chart(self) -> Dict[str, Any]:
        """Get Bitcoin Rainbow Chart data"""
        return await self._make_request("/api/index/bitcoin/rainbow-chart")

    async def get_bitcoin_stock_to_flow(self) -> Dict[str, Any]:
        """Get Bitcoin Stock-to-Flow model data"""
        return await self._make_request("/api/index/stock-flow")

    async def get_pi_cycle_indicator(self) -> Dict[str, Any]:
        """Get Pi Cycle Top Indicator data"""
        return await self._make_request("/api/index/pi-cycle-indicator")

    async def get_golden_ratio_multiplier(self) -> Dict[str, Any]:
        """Get Golden Ratio Multiplier data"""
        return await self._make_request("/api/index/golden-ratio-multiplier")

    async def get_bitcoin_profitable_days(self) -> Dict[str, Any]:
        """Get Bitcoin profitable days data"""
        return await self._make_request("/api/index/bitcoin/profitable-days")

    async def get_bitcoin_bubble_index(self) -> Dict[str, Any]:
        """Get Bitcoin Bubble Index data"""
        return await self._make_request("/api/index/bitcoin/bubble-index")

    async def get_two_year_ma_multiplier(self) -> Dict[str, Any]:
        """Get Two Year MA Multiplier data"""
        return await self._make_request("/api/index/2-year-ma-multiplier")

    async def get_200_week_ma_heatmap(self) -> Dict[str, Any]:
        """Get 200-Week MA Heatmap data"""
        return await self._make_request("/api/index/200-week-moving-average-heatmap")

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


# Global instance
coinglass_api = CoinGlassAPI()

# Export safe parsing functions for use in other modules
__all__ = ['CoinGlassAPI', 'coinglass_api', 'safe_float', 'safe_int', 'safe_get', 'safe_list_get']
