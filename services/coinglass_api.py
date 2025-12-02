import aiohttp
import asyncio
import time
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
        
        # Try multiple endpoint variations in order of likelihood
        endpoints_to_try = [
            "/api/futures/funding-rate/exchange-list",
            "/api/futures/fundingRate/exchange-list", 
            "/api/v4/funding-rate/exchange-list",
            "/api/v4/fundingRate/exchange-list",
            "/api/futures/funding_rate/exchange-list",
            "/api/futures/fundingRate/accumulated-exchange-list"
        ]
        
        for i, endpoint in enumerate(endpoints_to_try):
            result = await self._make_request(endpoint, params)
            if result.get("success"):
                logger.debug(f"Successfully used funding rate endpoint: {endpoint}")
                return result
            else:
                logger.debug(f"Funding rate endpoint {i+1}/{len(endpoints_to_try)} failed: {endpoint}")
        
        logger.error("All funding rate endpoints failed")
        return {"success": False, "data": [], "error": "All funding rate endpoints failed"}

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
        
        # Try multiple endpoint variations in order of likelihood
        endpoints_to_try = [
            "/api/futures/fundingRate/accumulated-exchange-list",
            "/api/futures/funding-rate/accumulated-exchange-list",
            "/api/v4/fundingRate/accumulated-exchange-list",
            "/api/v4/funding-rate/accumulated-exchange-list",
            "/api/futures/fundingRate/accumulated_exchange_list",
            "/api/futures/funding-rate/accumulated_exchange_list"
        ]
        
        for i, endpoint in enumerate(endpoints_to_try):
            result = await self._make_request(endpoint, params)
            if result.get("success"):
                logger.debug(f"Successfully used accumulated funding rate endpoint: {endpoint}")
                return result
            else:
                logger.debug(f"Accumulated funding rate endpoint {i+1}/{len(endpoints_to_try)} failed: {endpoint}")
        
        logger.error("All accumulated funding rate endpoints failed")
        return {"success": False, "data": [], "error": "All accumulated funding rate endpoints failed"}

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
                        "last_price": safe_float(item.get("lastPrice")),
                        "mark_price": safe_float(item.get("markPrice")),
                        "price_change_1h": safe_float(item.get("priceChange1h")),
                        "price_change_4h": safe_float(item.get("priceChange4h")),
                        "price_change_24h": safe_float(item.get("priceChange24h")),
                        "high_24h": safe_float(item.get("highPrice24h")),
                        "low_24h": safe_float(item.get("lowPrice24h")),
                        "high_7d": safe_float(item.get("highPrice7d")),
                        "low_7d": safe_float(item.get("lowPrice7d")),
                        "volume_24h": safe_float(item.get("volume24h")),
                        "market_cap": safe_float(item.get("marketCap")),
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
            result = await self.get_open_interest_exchange_list(symbol)
            
            if not result.get("success"):
                logger.warning(f"[RAW_DATA] Failed to get OI data for {symbol}: {result.get('error')}")
                return {}
            
            data = result.get("data", [])
            if not isinstance(data, list) or not data:
                return {}
            
            # Aggregate across all exchanges
            total_oi = 0.0
            oi_by_exchange = {}
            exchange_count = 0
            
            for item in data:
                if isinstance(item, dict):
                    exchange = str(item.get("exchange", "")).lower()
                    oi_value = safe_float(item.get("openInterest"))
                    
                    if oi_value > 0:
                        total_oi += oi_value
                        oi_by_exchange[exchange] = oi_value
                        exchange_count += 1
            
            return {
                "total": total_oi,
                "exchange_count": exchange_count,
                "by_exchange": oi_by_exchange,
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
                return {}
            
            data = result.get("data", [])
            if not isinstance(data, list) or not data:
                return {}
            
            # Get most recent data
            latest = data[-1] if data else None
            if not isinstance(latest, dict):
                return {}
            
            account_ratio = safe_float(latest.get("longShortRatio"))
            position_ratio = safe_float(latest.get("positionLongShortRatio"))
            
            return {
                "account_ratio": account_ratio,
                "position_ratio": position_ratio,
                "exchange": "binance",
            }
            
        except Exception as e:
            logger.error(f"[RAW_DATA] Error getting L/S ratio for {symbol}: {e}")
            return {}


# Global instance
coinglass_api = CoinGlassAPI()

# Export safe parsing functions for use in other modules
__all__ = ['CoinGlassAPI', 'coinglass_api', 'safe_float', 'safe_int', 'safe_get', 'safe_list_get']
