import aiohttp
import asyncio
import time
from typing import Dict, List, Optional, Any
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


class CoinGlassAPI:
    """CoinGlass API v4 wrapper with rate limiting and error handling"""

    def __init__(self):
        # Updated base URL according to documentation
        self.base_url = "https://open-api-v4.coinglass.com"
        self.api_key = settings.COINGLASS_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_info: Optional[RateLimitInfo] = None
        self._last_call_time = 0
        self._min_interval = (
            60 / settings.API_CALLS_PER_MINUTE
        )  # Minimum seconds between calls

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
            # Updated header format according to documentation
            headers = {"CG-API-KEY": self.api_key, "User-Agent": "CryptoSat-Bot/1.0"}
            self.session = aiohttp.ClientSession(headers=headers)

    async def _make_request(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to CoinGlass API with rate limiting and error handling

        Args:
            endpoint: API endpoint (e.g., '/api/futures/liquidation/coin-list')
            params: Query parameters

        Returns:
            API response data

        Raises:
            aiohttp.ClientError: For HTTP errors
            ValueError: For API errors
        """
        await self._ensure_session()

        # Rate limiting: ensure minimum interval between calls
        current_time = time.time()
        time_since_last_call = current_time - self._last_call_time
        if time_since_last_call < self._min_interval:
            sleep_time = self._min_interval - time_since_last_call
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)

        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.get(url, params=params) as response:
                self._last_call_time = time.time()

                # Parse rate limit headers
                self._parse_rate_limit_headers(response.headers)

                # Handle different HTTP status codes
                if response.status == 200:
                    data = await response.json()

                    # Check API-specific error code according to documentation
                    if data.get("code") != "0":
                        error_msg = data.get("msg", "Unknown API error")
                        logger.error(f"API Error for {endpoint}: {error_msg}")
                        raise ValueError(error_msg)

                    logger.debug(f"Successfully fetched {endpoint}")
                    # Some endpoints return list directly, others return dict with 'data' key
                    if isinstance(data, list):
                        return data
                    else:
                        return data.get("data", {})

                elif response.status == 401:
                    error_msg = "Invalid API key or unauthorized access"
                    logger.error(f"401 Error for {endpoint}: {error_msg}")
                    raise ValueError(error_msg)

                elif response.status == 429:
                    # Rate limit exceeded
                    error_data = await response.json()
                    error_msg = error_data.get("msg", "Rate limit exceeded")
                    logger.warning(f"429 Error for {endpoint}: {error_msg}")

                    # Back off and retry
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.info(f"Rate limited. Retrying after {retry_after}s")
                    await asyncio.sleep(retry_after)
                    return await self._make_request(endpoint, params)

                elif response.status >= 500:
                    error_msg = f"Server error: {response.status}"
                    logger.error(f"5xx Error for {endpoint}: {error_msg}")
                    raise aiohttp.ClientError(error_msg)

                else:
                    error_data = await response.json()
                    error_msg = error_data.get("msg", f"HTTP {response.status}")
                    logger.error(f"Error {response.status} for {endpoint}: {error_msg}")
                    raise ValueError(error_msg)

        except aiohttp.ClientError as e:
            logger.error(f"Network error for {endpoint}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for {endpoint}: {str(e)}")
            raise

    def _parse_rate_limit_headers(self, headers: Dict[str, str]):
        """Parse rate limit information from response headers"""
        try:
            # Updated header names according to documentation
            self._rate_limit_info = RateLimitInfo(
                calls_used=int(headers.get("API-KEY-USE-LIMIT", "0")),
                calls_remaining=int(headers.get("API-KEY-MAX-LIMIT", "0"))
                - int(headers.get("API-KEY-USE-LIMIT", "0")),
                reset_time=int(headers.get("API-KEY-USE-LIMIT-RESET", "0")),
                limit_per_minute=int(headers.get("API-KEY-MAX-LIMIT", "120")),
                limit_per_hour=int(headers.get("API-KEY-MAX-LIMIT-HOUR", "2000")),
            )

            logger.debug(
                f"Rate limit info: {self._rate_limit_info.calls_remaining}/{self._rate_limit_info.limit_per_minute} remaining (minute)"
            )

        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse rate limit headers: {e}")

    @property
    def rate_limit_info(self) -> Optional[RateLimitInfo]:
        """Get current rate limit information"""
        return self._rate_limit_info

    # High Priority Endpoints (Real-time)

    async def get_liquidation_coin_list(
        self, ex_name: str = "Binance"
    ) -> Dict[str, Any]:
        """
        Get liquidation data for all coins on specific exchange
        Update interval: 10 seconds
        """
        return await self._make_request(
            "/api/futures/liquidation/coin-list", {"exName": ex_name}
        )

    async def get_liquidation_exchange_list(self, symbol: str, range_param: str = "24h") -> Dict[str, Any]:
        """
        Get liquidation data for specific coin across all exchanges
        Update interval: 10 seconds
        """
        return await self._make_request(
            "/api/futures/liquidation/exchange-list", {"symbol": symbol, "range": range_param}
        )

    async def get_whale_alert_hyperliquid(self) -> Dict[str, Any]:
        """
        Get whale alerts from Hyperliquid
        Update interval: Real-time
        """
        return await self._make_request("/api/hyperliquid/whale-alert")

    async def get_whale_position_hyperliquid(self) -> Dict[str, Any]:
        """
        Get whale positions from Hyperliquid
        Update interval: Real-time
        """
        return await self._make_request("/api/hyperliquid/whale-position")

    async def get_funding_rate_exchange_list(
        self, symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get funding rates across exchanges
        Update interval: Real-time
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request(
            "/api/futures/fundingRate/exchange-list", params
        )

    async def get_liquidation_orders(
        self, symbol: Optional[str] = None, ex_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get liquidation order data from past 7 days
        Update interval: 1 second
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        if ex_name:
            params["exName"] = ex_name
        return await self._make_request("/api/futures/liquidation/order", params)

    # Medium Priority Endpoints (Market Sentiment)

    async def get_fear_greed_history(self) -> Dict[str, Any]:
        """
        Get Fear & Greed Index history
        Update interval: Daily
        """
        return await self._make_request("/api/index/fear-greed-history")

    async def get_bitcoin_etf_flow_history(self) -> Dict[str, Any]:
        """
        Get Bitcoin ETF flow history
        Update interval: Real-time
        """
        return await self._make_request("/api/etf/bitcoin/flow-history")

    async def get_global_long_short_ratio(
        self, symbol: str, ex_name: str
    ) -> Dict[str, Any]:
        """
        Get global long/short account ratio history
        Update interval: Real-time
        """
        return await self._make_request(
            "/api/futures/global-long-short-account-ratio/history",
            {"symbol": symbol, "exName": ex_name},
        )

    # Market Data Endpoints

    async def get_supported_coins(self) -> Dict[str, Any]:
        """
        Get list of supported futures coins
        Update interval: 1 minute
        """
        return await self._make_request("/api/futures/supported-coins")

    async def get_supported_exchange_pairs(self) -> Dict[str, Any]:
        """
        Get supported exchanges and their trading pairs
        Update interval: 1 minute
        """
        return await self._make_request("/api/futures/supported-exchange-pairs")

    async def get_futures_pairs_markets(
        self, symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get futures pair markets
        Update interval: Real-time
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request("/api/futures/pairs-markets", params)

    async def get_futures_coins_markets(
        self, symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get futures coin markets
        Update interval: Real-time
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request("/api/futures/coins-markets", params)

    async def get_price_change_list(self) -> Dict[str, Any]:
        """
        Get price change list
        Update interval: Real-time
        """
        return await self._make_request("/api/futures/price-change-list")

    async def get_price_ohlc_history(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get price OHLC history
        Update interval: Real-time
        """
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
        """
        Get OI OHLC history
        Update interval: Real-time
        """
        params = {"symbol": symbol, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request(
            "/api/futures/openInterest/ohlc-history", params
        )

    async def get_open_interest_aggregated_history(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated OI OHLC history
        Update interval: Real-time
        """
        params = {"symbol": symbol, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request(
            "/api/futures/openInterest/ohlc-aggregated-history", params
        )

    async def get_open_interest_exchange_list(self, symbol: str) -> Dict[str, Any]:
        """
        Get open interest by exchange list
        Update interval: Real-time
        """
        return await self._make_request(
            "/api/futures/openInterest/exchange-list", {"symbol": symbol}
        )

    async def get_open_interest_exchange_history_chart(
        self,
        symbol: str,
        ex_name: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get OI chart by exchange
        Update interval: Real-time
        """
        params = {"symbol": symbol, "exName": ex_name, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request(
            "/api/futures/openInterest/exchange-history-chart", params
        )

    # Funding Rate Endpoints

    async def get_funding_rate_ohlc_history(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get funding rate OHLC history
        Update interval: Real-time
        """
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
        """
        Get OI-weighted funding rate OHLC history
        Update interval: Real-time
        """
        params = {"symbol": symbol, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request(
            "/api/futures/fundingRate/oi-weight-ohlc-history", params
        )

    async def get_funding_rate_vol_weight_ohlc_history(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get volume-weighted funding rate OHLC history
        Update interval: Real-time
        """
        params = {"symbol": symbol, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request(
            "/api/futures/fundingRate/vol-weight-ohlc-history", params
        )

    async def get_funding_rate_accumulated_exchange_list(
        self, symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get cumulative funding rate list
        Update interval: Real-time
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request(
            "/api/futures/fundingRate/accumulated-exchange-list", params
        )

    async def get_funding_rate_arbitrage(self) -> Dict[str, Any]:
        """
        Get funding arbitrage opportunities
        Update interval: Real-time
        """
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
        """
        Get top trader long/short account ratio history
        Update interval: Real-time
        """
        params = {"symbol": symbol, "exName": ex_name, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request(
            "/api/futures/top-long-short-account-ratio/history", params
        )

    async def get_top_long_short_position_ratio_history(
        self,
        symbol: str,
        ex_name: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get top trader position ratio history
        Update interval: Real-time
        """
        params = {"symbol": symbol, "exName": ex_name, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request(
            "/api/futures/top-long-short-position-ratio/history", params
        )

    async def get_taker_buy_sell_volume_exchange_list(
        self, symbol: str, ex_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get exchange taker buy/sell volume
        Update interval: Real-time
        """
        params = {"symbol": symbol}
        if ex_name:
            params["exName"] = ex_name
        return await self._make_request(
            "/api/futures/taker-buy-sell-volume/exchange-list", params
        )

    # Taker Buy/Sell Volume Endpoints

    async def get_aggregated_taker_buy_sell_volume_history(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        exchange_list: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get coin taker buy/sell volume history
        Update interval: Real-time
        """
        params = {"symbol": symbol, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        if exchange_list:
            params["exchange_list"] = exchange_list
        return await self._make_request(
            "/api/futures/aggregated-taker-buy-sell-volume/history", params
        )

    # Order Book Endpoints

    async def get_orderbook_ask_bids_history(
        self,
        symbol: str,
        ex_name: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get pair orderbook bid&ask history
        Update interval: Real-time
        """
        params = {"symbol": symbol, "exName": ex_name, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request(
            "/api/futures/orderbook/ask-bids-history", params
        )

    async def get_orderbook_aggregated_ask_bids_history(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get coin orderbook bid&ask history
        Update interval: Real-time
        """
        params = {"symbol": symbol, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request(
            "/api/futures/orderbook/aggregated-ask-bids-history", params
        )

    async def get_orderbook_history(
        self,
        symbol: str,
        ex_name: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get orderbook heatmap history
        Update interval: Real-time
        """
        params = {"symbol": symbol, "exName": ex_name, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request("/api/futures/orderbook/history", params)

    async def get_large_limit_orders_history(
        self,
        symbol: str,
        ex_name: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get large orderbook history
        Update interval: Real-time
        """
        params = {"symbol": symbol, "exName": ex_name, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request(
            "/api/futures/orderbook/large-limit-order-history", params
        )

    # Liquidation Heatmap Endpoints

    async def get_liquidation_heatmap_model1(
        self, symbol: str, ex_name: str
    ) -> Dict[str, Any]:
        """
        Get pair liquidation heatmap model 1
        Update interval: Real-time
        """
        return await self._make_request(
            "/api/futures/liquidation/heatmap/model1",
            {"symbol": symbol, "exName": ex_name},
        )

    async def get_liquidation_heatmap_model2(
        self, symbol: str, ex_name: str
    ) -> Dict[str, Any]:
        """
        Get pair liquidation heatmap model 2
        Update interval: Real-time
        """
        return await self._make_request(
            "/api/futures/liquidation/heatmap/model2",
            {"symbol": symbol, "exName": ex_name},
        )

    async def get_liquidation_heatmap_model3(
        self, symbol: str, ex_name: str
    ) -> Dict[str, Any]:
        """
        Get pair liquidation heatmap model 3
        Update interval: Real-time
        """
        return await self._make_request(
            "/api/futures/liquidation/heatmap/model3",
            {"symbol": symbol, "exName": ex_name},
        )

    async def get_liquidation_aggregated_heatmap_model1(
        self, symbol: str
    ) -> Dict[str, Any]:
        """
        Get coin liquidation heatmap model 1
        Update interval: Real-time
        """
        return await self._make_request(
            "/api/futures/liquidation/aggregated-heatmap/model1", {"symbol": symbol}
        )

    async def get_liquidation_aggregated_heatmap_model2(
        self, symbol: str
    ) -> Dict[str, Any]:
        """
        Get coin liquidation heatmap model 2
        Update interval: Real-time
        """
        return await self._make_request(
            "/api/futures/liquidation/aggregated-heatmap/model2", {"symbol": symbol}
        )

    async def get_liquidation_aggregated_heatmap_model3(
        self, symbol: str
    ) -> Dict[str, Any]:
        """
        Get coin liquidation heatmap model 3
        Update interval: Real-time
        """
        return await self._make_request(
            "/api/futures/liquidation/aggregated-heatmap/model3", {"symbol": symbol}
        )

    # Liquidation Map Endpoints

    async def get_liquidation_map(
        self, symbol: str, ex_name: str, interval: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get pair liquidation map
        Update interval: Real-time
        """
        params = {"symbol": symbol, "exName": ex_name}
        if interval:
            params["interval"] = interval
        return await self._make_request("/api/futures/liquidation/map", params)

    async def get_liquidation_aggregated_map(self, symbol: str) -> Dict[str, Any]:
        """
        Get coin liquidation map
        Update interval: Real-time
        """
        return await self._make_request(
            "/api/futures/liquidation/aggregated-map", {"symbol": symbol}
        )

    # Additional Utility Endpoints

    async def get_large_limit_orders(self, symbol: str, ex_name: str) -> Dict[str, Any]:
        """
        Get large limit orders (orderbook walls)
        Update interval: Real-time
        """
        return await self._make_request(
            "/api/futures/orderbook/large-limit-order",
            {"symbol": symbol, "exName": ex_name},
        )

    async def get_taker_buy_sell_volume_history(
        self,
        symbol: str,
        ex_name: Optional[str] = None,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get taker buy/sell volume history
        Update interval: Real-time
        """
        params = {"symbol": symbol, "interval": interval}
        if ex_name:
            params["exName"] = ex_name
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request(
            "/api/futures/taker-buy-sell-volume/history", params
        )

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

    # Additional Indicators

    async def get_rsi_list(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get RSI list"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request("/api/futures/rsi/list", params)

    async def get_futures_basis_history(
        self,
        symbol: str,
        ex_name: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get futures basis history"""
        params = {"symbol": symbol, "exName": ex_name, "interval": interval}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        return await self._make_request("/api/futures/basis/history", params)

    async def get_coinbase_premium_index(self) -> Dict[str, Any]:
        """Get Coinbase premium index"""
        return await self._make_request("/api/coinbase-premium-index")

    async def get_bitfinex_margin_long_short(self) -> Dict[str, Any]:
        """Get Bitfinex margin long/short ratio"""
        return await self._make_request("/api/bitfinex-margin-long-short")

    async def get_ahr999_index(self) -> Dict[str, Any]:
        """Get AHR999 index"""
        return await self._make_request("/api/index/ahr999")

    async def get_puell_multiple(self) -> Dict[str, Any]:
        """Get Puell Multiple"""
        return await self._make_request("/api/index/puell-multiple")

    async def get_stablecoin_market_cap_history(self) -> Dict[str, Any]:
        """Get Stablecoin market cap history"""
        return await self._make_request("/api/index/stableCoin-marketCap-history")

    async def get_bull_market_peak_indicators(self) -> Dict[str, Any]:
        """Get Bull Market Peak Indicators"""
        return await self._make_request("/api/bull-market-peak-indicator")

    async def get_borrow_interest_rate_history(
        self, symbol: str, ex_name: str
    ) -> Dict[str, Any]:
        """Get borrow interest rate history"""
        return await self._make_request(
            "/api/borrow-interest-rate/history", {"symbol": symbol, "exName": ex_name}
        )

    # Testing endpoints for development

    async def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            await self.get_supported_coins()
            logger.info("CoinGlass API connection test successful")
            return True
        except Exception as e:
            logger.error(f"CoinGlass API connection test failed: {e}")
            return False

    async def get_current_rate_limit_status(self) -> Dict[str, int]:
        """Get current rate limiting status"""
        if self._rate_limit_info:
            return {
                "used": self._rate_limit_info.calls_used,
                "limit": self._rate_limit_info.limit_per_minute,
                "remaining": self._rate_limit_info.calls_remaining,
                "reset_time": self._rate_limit_info.reset_time,
            }
        return {"used": 0, "limit": 0, "remaining": 0, "reset_time": 0}


# Global instance
coinglass_api = CoinGlassAPI()
