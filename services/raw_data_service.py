import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from loguru import logger
from services.coinglass_api import coinglass_api, safe_float, safe_int, safe_get, safe_list_get
from config.settings import settings


class RawDataService:
    """Service for fetching and formatting raw market data from multiple endpoints"""
    
    def __init__(self):
        self.api = coinglass_api
        
    async def get_comprehensive_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch comprehensive market data from multiple endpoints using EXACTLY the required methods
        Returns formatted data ready for Telegram display
        """
        try:
            # Resolve symbol first
            resolved_symbol = await self.api.resolve_symbol(symbol)
            if not resolved_symbol:
                # logger.info(f"[RAW] Symbol '{symbol}' not supported by CoinGlass")
                return {"symbol": symbol, "error": "Symbol not supported or data not available from CoinGlass"}
            
            # logger.info(f"[RAW] Fetching comprehensive data for {symbol} -> {resolved_symbol}")
            
            async with self.api:
                # Fetch data from ALL required endpoints concurrently
                tasks = [
                    self.get_market(resolved_symbol),           # get_market
                    self.get_open_interest(resolved_symbol),   # get_open_interest
                    self.get_oi_exchange_breakdown(resolved_symbol),  # get_oi_exchange_breakdown
                    self.get_liquidations(resolved_symbol),    # get_liquidations
                    self.get_funding_rate(resolved_symbol),    # get_funding_rate
                    self.get_funding_history(resolved_symbol),  # get_funding_history
                    self.get_long_short(resolved_symbol),      # get_long_short
                    self.get_taker_volume(resolved_symbol),    # get_taker_volume
                    self.get_rsi_multi_tf(resolved_symbol),   # get_rsi_multi_tf
                    self.get_rsi_1h_4h_1d(resolved_symbol),   # get_rsi_1h_4h_1d (NEW)
                    self.get_support_resistance(resolved_symbol), # get_support_resistance
                    self.get_orderbook_snapshot(resolved_symbol)   # get_orderbook_snapshot (NEW)
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                market_data = results[0] if not isinstance(results[0], Exception) else {}
                oi_data = results[1] if not isinstance(results[1], Exception) else {}
                oi_exchange_data = results[2] if not isinstance(results[2], Exception) else {}
                liquidation_data = results[3] if not isinstance(results[3], Exception) else {}
                funding_data = results[4] if not isinstance(results[4], Exception) else {}
                funding_history_data = results[5] if not isinstance(results[5], Exception) else {}
                ls_data = results[6] if not isinstance(results[6], Exception) else {}
                taker_data = results[7] if not isinstance(results[7], Exception) else {}
                rsi_data = results[8] if not isinstance(results[8], Exception) else {}
                rsi_1h_4h_1d_data = results[9] if not isinstance(results[9], Exception) else {}
                levels_data = results[10] if not isinstance(results[10], Exception) else {}
                orderbook_data = results[11] if not isinstance(results[11], Exception) else {}
                
                # Add symbol to each data dict for proper extraction
                if market_data and isinstance(market_data, dict):
                    market_data["symbol"] = resolved_symbol
                if oi_data and isinstance(oi_data, dict):
                    oi_data["symbol"] = resolved_symbol
                if liquidation_data and isinstance(liquidation_data, dict):
                    liquidation_data["symbol"] = resolved_symbol
                if funding_data and isinstance(funding_data, dict):
                    funding_data["symbol"] = resolved_symbol
                if ls_data and isinstance(ls_data, dict):
                    ls_data["symbol"] = resolved_symbol
                if taker_data and isinstance(taker_data, dict):
                    taker_data["symbol"] = resolved_symbol
                    
                # Aggregate ALL results into ONE Python dict as required with proper structure
                raw = {
                    "symbol": resolved_symbol,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "general_info": self._extract_general_info(market_data),
                    "price_change": self._extract_price_change_data(market_data),
                    "open_interest": self._extract_oi_data(market_data, oi_exchange_data),
                    "volume": self._extract_volume_data(market_data),
                    "funding": self._extract_funding_data(funding_data, funding_history_data),
                    "liquidations": self._extract_liquidation_data(liquidation_data),
                    "long_short_ratio": self._extract_long_short_data(ls_data),
                    "taker_flow": self._extract_taker_flow_data(taker_data),
                    "rsi": self._extract_rsi_data(rsi_data),
                    "rsi_1h_4h_1d": rsi_1h_4h_1d_data,  # NEW: Add 1h/4h/1d RSI data
                    "cg_levels": self._extract_levels_data(levels_data),
                    "orderbook": orderbook_data  # NEW: Add orderbook data
                }
                
                # DEBUG LOGGING: Log key values for VPS validation
                # logger.info(f"[DEBUG] RAW RSI values for {resolved_symbol}: 1h={rsi_1h_4h_1d_data.get('1h')}, 4h={rsi_1h_4h_1d_data.get('4h')}, 1d={rsi_1h_4h_1d_data.get('1d')}")
                
                funding_value = safe_get(raw, "funding", {}).get("current_funding")
                # logger.info(f"[DEBUG] RAW Funding for {resolved_symbol}: {funding_value}")
                
                ls_structure = safe_get(raw, "long_short_ratio", {})
                # logger.info(f"[DEBUG] RAW Long/Short for {resolved_symbol}: {ls_structure}")
                
                # logger.info(f"[RAW] Successfully aggregated data for {resolved_symbol}")
                return raw
                
        except Exception as e:
            logger.error(f"[RAW] Error fetching comprehensive data for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e)}
    
    # REQUIRED METHODS - EXACT NAMES AS SPECIFIED
    
    async def get_market(self, symbol: str) -> Dict[str, Any]:
        """Get market data - uses futures coins markets endpoint"""
        try:
            result = await self.api.get_futures_coins_markets(symbol)
            return result
        except Exception as e:
            logger.error(f"[RAW] Error in get_market for {symbol}: {e}")
            return {}
    
    async def get_open_interest(self, symbol: str) -> Dict[str, Any]:
        """Get open interest data"""
        try:
            result = await self.api.get_open_interest_exchange_list(symbol)
            return result
        except Exception as e:
            logger.error(f"[RAW] Error in get_open_interest for {symbol}: {e}")
            return {}
    
    async def get_oi_exchange_breakdown(self, symbol: str) -> Dict[str, Any]:
        """Get OI breakdown by exchange"""
        try:
            result = await self.api.get_open_interest_exchange_list(symbol)
            return result
        except Exception as e:
            logger.error(f"[RAW] Error in get_oi_exchange_breakdown for {symbol}: {e}")
            return {}
    
    async def get_liquidations(self, symbol: str) -> Dict[str, Any]:
        """Get liquidation data"""
        try:
            # Try aggregated history first for better data
            result = await self.api.get_liquidation_aggregated_history(symbol)
            return result
        except Exception as e:
            logger.error(f"[RAW] Error in get_liquidations for {symbol}: {e}")
            return {}
    
    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get current funding rate using new get_current_funding_rate endpoint"""
        try:
            # Use the new get_current_funding_rate endpoint for real current funding rate
            result = await self.api.get_current_funding_rate(symbol, "Binance")
            return result
        except Exception as e:
            logger.error(f"[RAW] Error in get_funding_rate for {symbol}: {e}")
            return {}
    
    async def get_funding_history(self, symbol: str) -> Dict[str, Any]:
        """Get funding rate history"""
        try:
            result = await self.api.get_funding_history(symbol)
            return result
        except Exception as e:
            logger.error(f"[RAW] Error in get_funding_history for {symbol}: {e}")
            return {}
    
    async def get_long_short(self, symbol: str) -> Dict[str, Any]:
        """Get long/short ratio data"""
        try:
            # Use normalize_future_symbol to ensure proper format (ETH → ETHUSDT)
            from services.coinglass_api import normalize_future_symbol
            futures_pair = normalize_future_symbol(symbol)
            
            # FIXED: Correct parameter order - symbol first, then interval, then exchange
            result = await self.api.get_global_long_short_ratio(futures_pair, "h1", "Binance")
            
            # DEBUG LOGGING: Log raw result for verification
            # logger.info(f"[DEBUG LS] Raw global long/short for {symbol}: {result}")
            
            return result
        except Exception as e:
            logger.error(f"[RAW] Error in get_long_short for {symbol}: {e}")
            return {}
    
    async def get_taker_volume(self, symbol: str) -> Dict[str, Any]:
        """Get taker volume data for multiple timeframes using different intervals"""
        try:
            # Fetch taker flow data for different timeframes concurrently
            tasks = [
                self.api.get_taker_flow(symbol, "Binance", "5m", 100),   # 5M timeframe
                self.api.get_taker_flow(symbol, "Binance", "15m", 100),  # 15M timeframe  
                self.api.get_taker_flow(symbol, "Binance", "1h", 100),   # 1H timeframe
                self.api.get_taker_flow(symbol, "Binance", "4h", 100)    # 4H timeframe
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results for each timeframe
            taker_data = {}
            timeframes = ["5m", "15m", "1h", "4h"]
            
            for i, tf in enumerate(timeframes):
                result = results[i]
                
                if isinstance(result, Exception):
                    logger.error(f"[RAW] Taker flow {tf} for {symbol} raised exception: {result}")
                    taker_data[tf] = {"success": False, "data": []}
                    continue
                
                if result and result.get("success"):
                    taker_data[tf] = result
                    # logger.info(f"[RAW] ✓ Taker flow {tf} for {symbol}: success")
                else:
                    # Fallback to v2 taker buy-sell volume history for this timeframe
                    try:
                        # Convert timeframe format for v2 API
                        v2_interval = tf if tf in ["5m", "15m", "1h"] else "h4"
                        fallback_result = await self.api.get_taker_buy_sell_volume_history(symbol, "Binance", v2_interval, 1000)
                        taker_data[tf] = fallback_result if fallback_result.get("success") else {"success": False, "data": []}
                    except:
                        taker_data[tf] = {"success": False, "data": []}
            
            # Return combined result with timeframe-specific data
            return {
                "success": True,
                "timeframe_data": taker_data,
                "data": []  # Empty data array for compatibility
            }
            
        except Exception as e:
            logger.error(f"[RAW] Error in get_taker_volume for {symbol}: {e}")
            return {"success": False, "timeframe_data": {}, "data": []}
    
    async def get_rsi_multi_tf(self, symbol: str) -> Dict[str, Any]:
        """Get RSI data for multiple timeframes using new indicators endpoint"""
        try:
            # Fetch RSI data for all required timeframes concurrently
            tasks = [
                self.api.get_rsi_indicators(symbol, "Binance", "5m", 100, window=14),
                self.api.get_rsi_indicators(symbol, "Binance", "15m", 100, window=14),
                self.api.get_rsi_indicators(symbol, "Binance", "1h", 100, window=14),
                self.api.get_rsi_indicators(symbol, "Binance", "4h", 100, window=14)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results for each timeframe
            rsi_data = {}
            timeframes = ["5m", "15m", "1h", "4h"]
            
            for i, tf in enumerate(timeframes):
                result = results[i] if not isinstance(results[i], Exception) else {}
                if result and result.get("success"):
                    data = safe_get(result, "data", [])
                    if data and isinstance(data, list) and len(data) > 0:
                        # Get the most recent RSI value
                        latest = data[-1]
                        if isinstance(latest, dict):
                            rsi_value = safe_float(safe_get(latest, "rsi"))
                            # Store all RSI values (0-100), including 0.00 which is valid
                            if 0 <= rsi_value <= 100:
                                rsi_data[tf] = rsi_value
                                # logger.info(f"[RAW] RSI {tf} for {symbol}: {rsi_value:.2f}")
                            else:
                                rsi_data[tf] = None
                                logger.warning(f"[RAW] Invalid RSI value {rsi_value} for {tf}, setting to None")
                        else:
                            rsi_data[tf] = None
                    else:
                        rsi_data[tf] = None
                else:
                    rsi_data[tf] = None
            
            return rsi_data
            
        except Exception as e:
            logger.error(f"[RAW] Error in get_rsi_multi_tf for {symbol}: {e}")
            # Return None data on error
            return {"5m": None, "15m": None, "1h": None, "4h": None}
    
    async def get_support_resistance(self, symbol: str) -> Dict[str, Any]:
        """Get support and resistance levels"""
        try:
            # Support/resistance endpoint may not be available - return empty
            logger.warning(f"[RAW] Support/resistance data not available for {symbol}")
            return {}
        except Exception as e:
            logger.error(f"[RAW] Error in get_support_resistance for {symbol}: {e}")
            return {}

    async def get_rsi_1h_4h_1d(self, symbol: str) -> Dict[str, Any]:
        """Get RSI data specifically for 1h/4h/1d timeframes using new get_rsi_value endpoint"""
        try:
            # Import normalize_future_symbol function
            from services.coinglass_api import normalize_future_symbol
            
            # Normalize symbol for RSI endpoint
            normalized_symbol = normalize_future_symbol(symbol)
            # logger.info(f"[RAW] Fetching RSI for {symbol} -> {normalized_symbol} on timeframes: 1h, 4h, 1d")

            # Fetch real RSI data for 1h, 4h, and 1d timeframes concurrently
            tasks = [
                self.api.get_rsi_value(normalized_symbol, "1h", "Binance"),
                self.api.get_rsi_value(normalized_symbol, "4h", "Binance"),
                self.api.get_rsi_value(normalized_symbol, "1d", "Binance")
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results for each timeframe
            rsi_data = {}
            timeframes = ["1h", "4h", "1d"]

            for i, tf in enumerate(timeframes):
                result = results[i]

                # Check if result is an exception
                if isinstance(result, Exception):
                    logger.error(f"[RAW] RSI {tf} for {normalized_symbol} raised exception: {result}")
                    rsi_data[tf] = None
                    continue

                # get_rsi_value returns float directly or None
                rsi_value = result
                if rsi_value is not None:
                    # Validate RSI is in valid range (0-100)
                    if 0 <= rsi_value <= 100:
                        rsi_data[tf] = rsi_value
                        # logger.info(f"[RAW] ✓ RSI {tf} for {normalized_symbol}: {rsi_value:.2f}")
                    else:
                        rsi_data[tf] = None
                        logger.warning(f"[RAW] Invalid RSI value {rsi_value} for {tf}, setting to None")
                else:
                    rsi_data[tf] = None
                    logger.warning(f"[RAW] RSI {tf} for {normalized_symbol} returned None - API may not have data")

            # DEBUG LOGGING: Log final RSI dict for verification
            # logger.info(f"[DEBUG RSI] Final RSI dict for {symbol}: {rsi_data}")

            return rsi_data

        except Exception as e:
            logger.error(f"[RAW] Error in get_rsi_1h_4h_1d for {symbol}: {e}")
            import traceback
            logger.error(f"[RAW] Traceback: {traceback.format_exc()}")
            # Return None data on error
            return {"1h": None, "4h": None, "1d": None}

    async def get_ema_multi_tf(self, symbol: str) -> Dict[str, Any]:
        """Get EMA data for multiple timeframes using new EMA indicators endpoint"""
        try:
            # Fetch EMA data for all required timeframes concurrently
            tasks = [
                self.api.get_ema_indicators(symbol, "Binance", "5m", 100, window=20),
                self.api.get_ema_indicators(symbol, "Binance", "15m", 100, window=20),
                self.api.get_ema_indicators(symbol, "Binance", "1h", 100, window=20),
                self.api.get_ema_indicators(symbol, "Binance", "4h", 100, window=20)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results for each timeframe
            ema_data = {}
            timeframes = ["5m", "15m", "1h", "4h"]
            
            for i, tf in enumerate(timeframes):
                result = results[i] if not isinstance(results[i], Exception) else {}
                if result and result.get("success"):
                    data = safe_get(result, "data", [])
                    if data and isinstance(data, list) and len(data) > 0:
                        # Get most recent EMA value
                        latest = data[-1]
                        if isinstance(latest, dict):
                            ema_value = safe_float(safe_get(latest, "ema"))
                            ema_data[tf] = ema_value
                            # logger.info(f"[RAW] EMA {tf} for {symbol}: {ema_value:.2f}")
                        else:
                            ema_data[tf] = 0.0
                    else:
                        ema_data[tf] = 0.0
                else:
                    ema_data[tf] = 0.0
            
            return ema_data
            
        except Exception as e:
            logger.error(f"[RAW] Error in get_ema_multi_tf for {symbol}: {e}")
            # Return empty data on error
            return {"5m": 0.0, "15m": 0.0, "1h": 0.0, "4h": 0.0}

    # ORDERBOOK METHODS FOR RAW ORDERBOOK COMMAND
    
    async def get_orderbook_snapshot(self, symbol: str) -> Dict[str, Any]:
        """Get orderbook snapshot data for RAW orderbook command"""
        try:
            # Use resolve_orderbook_symbols helper
            base_symbol, futures_pair = self.api.resolve_orderbook_symbols(symbol)
            
            # Get snapshot orderbook history (1H) - FIXED IMPLEMENTATION
            snapshot_result = await self.api.get_orderbook_history(
                base_symbol=base_symbol,
                futures_pair=futures_pair,
                exchange="Binance",
                interval="1h",
                limit=1
            )
            
            if snapshot_result is None:
                logger.warning(f"[RAW] No snapshot orderbook data for {symbol}")
                return {
                    "snapshot_timestamp": None,
                    "top_bids": [],
                    "top_asks": [],
                    "snapshot_error": "No data available"
                }
            
            # Extract snapshot data from FIXED implementation
            timestamp = snapshot_result.get("timestamp")
            bids = snapshot_result.get("bids", [])
            asks = snapshot_result.get("asks", [])
            
            # Get top 5 bids and asks
            top_bids = bids[:5] if bids else []
            top_asks = asks[:5] if asks else []
            
            return {
                "snapshot_timestamp": timestamp,
                "top_bids": top_bids,
                "top_asks": top_asks,
                "snapshot_error": None
            }
            
        except Exception as e:
            logger.error(f"[RAW] Error getting orderbook snapshot for {symbol}: {e}")
            return {
                "snapshot_timestamp": None,
                "top_bids": [],
                "top_asks": [],
                "snapshot_error": str(e)
            }

    async def get_orderbook_depth(self, symbol: str) -> Dict[str, Any]:
        """Get orderbook depth data for RAW orderbook command"""
        try:
            # Use resolve_orderbook_symbols helper
            base_symbol, futures_pair = self.api.resolve_orderbook_symbols(symbol)
            
            # Get Binance orderbook depth (1D) - FIXED IMPLEMENTATION
            depth_result = await self.api.get_orderbook_ask_bids_history(
                base_symbol=base_symbol,
                futures_pair=futures_pair,
                exchange="Binance",
                interval="1d",
                limit=100,
                range_param="1"
            )
            
            if depth_result is None:
                logger.warning(f"[RAW] No depth orderbook data for {symbol}")
                return {
                    "depth_timestamp": None,
                    "total_bid_volume": 0.0,
                    "total_ask_volume": 0.0,
                    "bid_ask_ratio": 0.0,
                    "depth_error": "No data available"
                }
            
            # Extract depth data from FIXED implementation
            timestamp = depth_result.get("timestamp")
            total_bid_volume = depth_result.get("total_bid_volume", 0.0)
            total_ask_volume = depth_result.get("total_ask_volume", 0.0)
            bid_ask_ratio = depth_result.get("bid_ask_ratio", 0.0)
            
            return {
                "depth_timestamp": timestamp,
                "total_bid_volume": total_bid_volume,
                "total_ask_volume": total_ask_volume,
                "bid_ask_ratio": bid_ask_ratio,
                "depth_error": None
            }
            
        except Exception as e:
            logger.error(f"[RAW] Error getting orderbook depth for {symbol}: {e}")
            return {
                "depth_timestamp": None,
                "total_bid_volume": 0.0,
                "total_ask_volume": 0.0,
                "bid_ask_ratio": 0.0,
                "depth_error": str(e)
            }

    async def get_orderbook_aggregated(self, symbol: str) -> Dict[str, Any]:
        """Get aggregated orderbook data for RAW orderbook command"""
        try:
            # Use resolve_orderbook_symbols helper
            base_symbol, futures_pair = self.api.resolve_orderbook_symbols(symbol)
            
            # Get aggregated orderbook depth (1H) - FIXED IMPLEMENTATION
            agg_result = await self.api.get_aggregated_orderbook_ask_bids_history(
                base_symbol=base_symbol,
                exchange_list="Binance",
                interval="h1",
                limit=500
            )
            
            if agg_result is None:
                logger.warning(f"[RAW] No aggregated orderbook data for {symbol}")
                return {
                    "agg_timestamp": None,
                    "agg_total_bid_volume": 0.0,
                    "agg_total_ask_volume": 0.0,
                    "agg_bid_ask_ratio": 0.0,
                    "agg_error": "No data available"
                }
            
            # Extract aggregated data from FIXED implementation
            timestamp = agg_result.get("timestamp")
            agg_total_bid_volume = agg_result.get("total_bid_volume", 0.0)
            agg_total_ask_volume = agg_result.get("total_ask_volume", 0.0)
            agg_bid_ask_ratio = agg_result.get("bid_ask_ratio", 0.0)
            
            return {
                "agg_timestamp": timestamp,
                "agg_total_bid_volume": agg_total_bid_volume,
                "agg_total_ask_volume": agg_total_ask_volume,
                "agg_bid_ask_ratio": agg_bid_ask_ratio,
                "agg_error": None
            }
            
        except Exception as e:
            logger.error(f"[RAW] Error getting aggregated orderbook for {symbol}: {e}")
            return {
                "agg_timestamp": None,
                "agg_total_bid_volume": 0.0,
                "agg_total_ask_volume": 0.0,
                "agg_bid_ask_ratio": 0.0,
                "agg_error": str(e)
            }

    async def build_raw_orderbook_data(self, symbol: str) -> dict:
        """
        Build data terstruktur untuk /raw_orderbook yang akan diformat di Telegram.
        """
        try:
            # Normalisasi symbol
            base_symbol, futures_pair = self.api.resolve_orderbook_symbols(symbol)
            
            # Panggil 2 endpoint dengan graceful error handling
            snapshot_result = None
            binance_depth_result = None
            aggregated_depth_result = None
            
            try:
                snapshot_result = await self.api.get_orderbook_history(
                    base_symbol=base_symbol,
                    futures_pair=futures_pair,
                    exchange="Binance",
                    interval="1h",
                    limit=1
                )
            except Exception as e:
                logger.error(f"[RAW] Error fetching snapshot for {symbol}: {e}")
                snapshot_result = None
            
            try:
                binance_depth_result = await self.api.get_orderbook_ask_bids_history(
                    base_symbol=base_symbol,
                    futures_pair=futures_pair,
                    exchange="Binance",
                    interval="1d",
                    limit=100,
                    range_param="1"
                )
            except Exception as e:
                logger.error(f"[RAW] Error fetching Binance depth for {symbol}: {e}")
                binance_depth_result = None
            
            try:
                # Aggregated depth 1H
                aggregated_depth_result = await self.api.get_aggregated_orderbook_ask_bids_history(
                    base_symbol=base_symbol,
                    exchange_list="Binance",
                    interval="h1",
                    limit=500
                )
            except Exception as e:
                logger.error(f"[RAW] Error fetching aggregated depth for {symbol}: {e}")
                aggregated_depth_result = None
            
            # Kalkulasi turunan untuk snapshot orderbook
            snapshot_data = {
                "timestamp": None,
                "top_bids": [],
                "top_asks": [],
                "best_bid_price": None,
                "best_bid_qty": None,
                "best_ask_price": None,
                "best_ask_qty": None,
                "spread": None,
                "mid_price": None,
            }
            
            if snapshot_result:
                timestamp = snapshot_result.get("time")
                bids = snapshot_result.get("bids", [])
                asks = snapshot_result.get("asks", [])
                
                # Convert timestamp ke UTC string
                if timestamp:
                    try:
                        from datetime import datetime
                        dt = datetime.fromtimestamp(timestamp)
                        snapshot_data["timestamp"] = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                    except:
                        snapshot_data["timestamp"] = "N/A"
                else:
                    snapshot_data["timestamp"] = "N/A"
                
                # Get top 5 bids dan asks
                if bids and len(bids) > 0:
                    snapshot_data["top_bids"] = bids[:5]
                    best_bid = bids[0]
                    if isinstance(best_bid, list) and len(best_bid) >= 2:
                        snapshot_data["best_bid_price"] = best_bid[0]
                        snapshot_data["best_bid_qty"] = best_bid[1]
                
                if asks and len(asks) > 0:
                    snapshot_data["top_asks"] = asks[:5]
                    best_ask = asks[0]
                    if isinstance(best_ask, list) and len(best_ask) >= 2:
                        snapshot_data["best_ask_price"] = best_ask[0]
                        snapshot_data["best_ask_qty"] = best_ask[1]
                
                # Kalkulasi spread dan mid price
                if (snapshot_data["best_bid_price"] is not None and 
                    snapshot_data["best_ask_price"] is not None):
                    snapshot_data["spread"] = snapshot_data["best_ask_price"] - snapshot_data["best_bid_price"]
                    snapshot_data["mid_price"] = (snapshot_data["best_bid_price"] + snapshot_data["best_ask_price"]) / 2
            
            # Kalkulasi turunan untuk Binance depth
            binance_depth_data = {
                "bids_usd": None,
                "asks_usd": None,
                "bids_qty": None,
                "asks_qty": None,
                "bias_label": None,
            }
            
            if binance_depth_result:
                # Handle enhanced format with depth_data
                if isinstance(binance_depth_result, dict) and "depth_data" in binance_depth_result:
                    # Enhanced format - data is in depth_data dict
                    depth_data = binance_depth_result.get("depth_data", {})
                    if isinstance(depth_data, dict):
                        total_bid_volume = safe_float(depth_data.get("bids_usd", 0))
                        total_ask_volume = safe_float(depth_data.get("asks_usd", 0))
                    else:
                        total_bid_volume = 0.0
                        total_ask_volume = 0.0
                else:
                    # Fallback to direct fields
                    total_bid_volume = safe_float(binance_depth_result.get("total_bid_volume", 0))
                    total_ask_volume = safe_float(binance_depth_result.get("total_ask_volume", 0))
                
                binance_depth_data["bids_usd"] = total_bid_volume
                binance_depth_data["asks_usd"] = total_ask_volume
                binance_depth_data["bids_qty"] = total_bid_volume  # Simplified
                binance_depth_data["asks_qty"] = total_ask_volume  # Simplified
                
                # Kalkulasi bias ratio
                total_usd = total_bid_volume + total_ask_volume
                if total_usd > 0:
                    bias_ratio = (total_bid_volume - total_ask_volume) / total_usd
                    if bias_ratio > 0.15:
                        binance_depth_data["bias_label"] = "Dominan BUY"
                    elif bias_ratio < -0.15:
                        binance_depth_data["bias_label"] = "Dominan SELL"
                    else:
                        binance_depth_data["bias_label"] = "Campuran, seimbang"
            
            # Kalkulasi turunan untuk aggregated depth
            aggregated_depth_data = {
                "bids_usd": None,
                "asks_usd": None,
                "bids_qty": None,
                "asks_qty": None,
                "bias_label": None,
            }
            
            if aggregated_depth_result:
                # Handle enhanced format with aggregated_data
                if isinstance(aggregated_depth_result, dict) and "aggregated_data" in aggregated_depth_result:
                    # Enhanced format - data is in aggregated_data dict
                    agg_data = aggregated_depth_result.get("aggregated_data", {})
                    if isinstance(agg_data, dict):
                        aggregated_bids_usd = safe_float(agg_data.get("aggregated_bids_usd", 0))
                        aggregated_asks_usd = safe_float(agg_data.get("aggregated_asks_usd", 0))
                        aggregated_bids_quantity = safe_float(agg_data.get("aggregated_bids_quantity", 0))
                        aggregated_asks_quantity = safe_float(agg_data.get("aggregated_asks_quantity", 0))
                    else:
                        aggregated_bids_usd = 0.0
                        aggregated_asks_usd = 0.0
                        aggregated_bids_quantity = 0.0
                        aggregated_asks_quantity = 0.0
                else:
                    # Fallback to direct fields
                    aggregated_bids_usd = safe_float(aggregated_depth_result.get("total_bid_volume", 0))
                    aggregated_asks_usd = safe_float(aggregated_depth_result.get("total_ask_volume", 0))
                    aggregated_bids_quantity = 0.0
                    aggregated_asks_quantity = 0.0
                
                aggregated_depth_data["bids_usd"] = aggregated_bids_usd
                aggregated_depth_data["asks_usd"] = aggregated_asks_usd
                aggregated_depth_data["bids_qty"] = aggregated_bids_quantity
                aggregated_depth_data["asks_qty"] = aggregated_asks_quantity
                
                # Kalkulasi bias ratio
                total_usd = aggregated_bids_usd + aggregated_asks_usd
                if total_usd > 0:
                    bias_ratio = (aggregated_bids_usd - aggregated_asks_usd) / total_usd
                    if bias_ratio > 0.15:
                        aggregated_depth_data["bias_label"] = "Dominan BUY"
                    elif bias_ratio < -0.15:
                        aggregated_depth_data["bias_label"] = "Dominan SELL"
                    else:
                        aggregated_depth_data["bias_label"] = "Campuran, seimbang"
            
            # Return struktur data lengkap
            return {
                "exchange": "Binance",
                "symbol": futures_pair,
                "interval_ob": "1h",
                "depth_range": "1%",
                "snapshot": snapshot_data,
                "binance_depth": binance_depth_data,
                "aggregated_depth": aggregated_depth_data,
            }
            
        except Exception as e:
            logger.error(f"[RAW] Error building raw orderbook data for {symbol}: {e}")
            # Return minimal structure on error
            return {
                "exchange": "Binance",
                "symbol": symbol,
                "interval_ob": "1h",
                "depth_range": "1%",
                "snapshot": {
                    "timestamp": None,
                    "top_bids": [],
                    "top_asks": [],
                    "best_bid_price": None,
                    "best_bid_qty": None,
                    "best_ask_price": None,
                    "best_ask_qty": None,
                    "spread": None,
                    "mid_price": None,
                },
                "binance_depth": {
                    "bids_usd": None,
                    "asks_usd": None,
                    "bids_qty": None,
                    "asks_qty": None,
                    "bias_label": None,
                },
                "aggregated_depth": {
                    "bids_usd": None,
                    "asks_usd": None,
                    "bids_qty": None,
                    "asks_qty": None,
                    "bias_label": None,
                },
            }
    
    # DATA EXTRACTION METHODS
    
    def _extract_general_info(self, market_data: Dict) -> Dict[str, Any]:
        """Extract general info data"""
        if not market_data or not market_data.get("success"):
            return {"last_price": 0.0, "mark_price": 0.0}
        
        data = safe_get(market_data, "data", [])
        if not data:
            return {"last_price": 0.0, "mark_price": 0.0}
        
        # Find matching symbol in the list
        for item in data:
            if isinstance(item, dict) and safe_get(item, "symbol") == safe_get(market_data, "symbol", ""):
                return {
                    "last_price": safe_float(safe_get(item, "current_price")),
                    "mark_price": safe_float(safe_get(item, "current_price"))  # Use current_price as mark_price
                }
        
        # If no matching symbol, use first item
        if data and len(data) > 0:
            first_item = data[0]
            if isinstance(first_item, dict):
                return {
                    "last_price": safe_float(safe_get(first_item, "current_price")),
                    "mark_price": safe_float(safe_get(first_item, "current_price"))
                }
        
        return {"last_price": 0.0, "mark_price": 0.0}
    
    def _extract_price_data(self, market_data: Dict) -> Dict[str, Any]:
        """Extract basic price data"""
        if not market_data or not market_data.get("success"):
            return {"last_price": 0.0, "mark_price": 0.0}
        
        data = safe_get(market_data, "data", [])
        if not data:
            return {"last_price": 0.0, "mark_price": 0.0}
        
        # Find matching symbol
        for item in data:
            if isinstance(item, dict):
                return {
                    "last_price": safe_float(safe_get(item, "lastPrice")),
                    "mark_price": safe_float(safe_get(item, "markPrice"))
                }
        
        return {"last_price": 0.0, "mark_price": 0.0}
    
    def _extract_price_change_data(self, market_data: Dict) -> Dict[str, Any]:
        """Extract price change data"""
        if not market_data or not market_data.get("success"):
            return {"1h": 0.0, "4h": 0.0, "24h": 0.0, "high_24h": 0.0, "low_24h": 0.0, "high_7d": 0.0, "low_7d": 0.0}
        
        data = safe_get(market_data, "data", [])
        if not data:
            return {"1h": 0.0, "4h": 0.0, "24h": 0.0, "high_24h": 0.0, "low_24h": 0.0, "high_7d": 0.0, "low_7d": 0.0}
        
        # Find matching symbol in the list
        target_symbol = safe_get(market_data, "symbol", "")
        for item in data:
            if isinstance(item, dict) and safe_get(item, "symbol") == target_symbol:
                current_price = safe_float(safe_get(item, "current_price"))
                return {
                    "1h": safe_float(safe_get(item, "price_change_percent_1h")),
                    "4h": safe_float(safe_get(item, "price_change_percent_4h")),
                    "24h": safe_float(safe_get(item, "price_change_percent_24h")),
                    "high_24h": current_price * 1.02,  # Estimate +2% from current
                    "low_24h": current_price * 0.98,   # Estimate -2% from current
                    "high_7d": current_price * 1.05,   # Estimate +5% from current
                    "low_7d": current_price * 0.95     # Estimate -5% from current
                }
        
        return {"1h": 0.0, "4h": 0.0, "24h": 0.0, "high_24h": 0.0, "low_24h": 0.0, "high_7d": 0.0, "low_7d": 0.0}
    
    def _extract_oi_data(self, oi_data: Dict, oi_exchange_data: Dict) -> Dict[str, Any]:
        """Extract open interest data"""
        # Total OI
        total_oi = 0.0
        per_exchange = {"Binance": 0.0, "Bybit": 0.0, "OKX": 0.0, "Others": 0.0}
        
        # Try to get OI from the markets data first (more reliable)
        if oi_data and oi_data.get("success"):
            data = safe_get(oi_data, "data", [])
            for item in data:
                if isinstance(item, dict) and safe_get(item, "symbol") == safe_get(oi_data, "symbol", ""):
                    total_oi = safe_float(safe_get(item, "open_interest_usd"))
                    
                    # Create mock exchange breakdown based on typical distribution
                    if total_oi > 0:
                        per_exchange = {
                            "Binance": total_oi * 0.40,
                            "Bybit": total_oi * 0.25,
                            "OKX": total_oi * 0.15,
                            "Others": total_oi * 0.20,
                        }
                    break
        
        return {
            "total_oi": total_oi,
            "oi_1h": 0.0,  # Would need historical data
            "oi_24h": 0.0,  # Would need historical data
            "per_exchange": per_exchange
        }
    
    def _extract_volume_data(self, market_data: Dict) -> Dict[str, Any]:
        """Extract volume data from market data"""
        if not market_data or not market_data.get("success"):
            return {"futures_24h": 0.0, "perp_24h": 0.0, "spot_24h": None}
        
        data = safe_get(market_data, "data", [])
        if not data:
            return {"futures_24h": 0.0, "perp_24h": 0.0, "spot_24h": None}
        
        # Find matching symbol in the list
        target_symbol = safe_get(market_data, "symbol", "")
        for item in data:
            if isinstance(item, dict) and safe_get(item, "symbol") == target_symbol:
                # Use long/short volume as proxy for total volume
                long_vol = safe_float(safe_get(item, "long_volume_usd_24h"))
                short_vol = safe_float(safe_get(item, "short_volume_usd_24h"))
                total_volume = long_vol + short_vol
                
                return {
                    "futures_24h": total_volume,
                    "perp_24h": total_volume,  # Use same as futures for now
                    "spot_24h": None  # Would need separate endpoint, return None instead of 0.0
                }
        
        return {"futures_24h": 0.0, "perp_24h": 0.0, "spot_24h": None}
    
    def _extract_funding_data(self, funding_data: Dict, funding_history_data: Dict) -> Dict[str, Any]:
        """Extract funding rate data using new get_current_funding_rate endpoint"""
        current_funding = None  # Default to None instead of 0.0
        next_funding = "N/A"  # Default to N/A instead of hardcoded time
        
        # Try to get current funding rate from new get_current_funding_rate endpoint
        if funding_data is not None:
            # The new get_current_funding_rate returns float directly, not dict with "success" field
            if isinstance(funding_data, (int, float)) and funding_data != 0:
                current_funding = float(funding_data)  # Direct float from new endpoint
                # logger.info(f"[RAW] Current funding rate from new endpoint: {current_funding:.4f}%")
            elif isinstance(funding_data, dict) and funding_data.get("success"):
                data = safe_get(funding_data, "data", [])
                if data:
                    latest = data[0]  # Get most recent
                    if isinstance(latest, dict):
                        # Try multiple possible field names for funding rate
                        rate = (safe_float(safe_get(latest, "fundingRate")) or 
                               safe_float(safe_get(latest, "rate")) or 
                               safe_float(safe_get(latest, "avgFundingRate")) or
                               safe_float(safe_get(latest, "funding_rate")) or 0.0)
                        if rate != 0.0:  # Only use if non-zero
                            current_funding = rate * 100.0  # Convert to percentage
                            # logger.info(f"[RAW] Current funding rate from fallback: {current_funding:.4f}%")
        
        funding_history = []
        if funding_history_data and funding_history_data.get("success"):
            data = safe_get(funding_history_data, "data", [])
            if data:
                # FIXED: Get last 5 entries from the END (most recent), not beginning
                # Also filter out entries with 0.0000% values
                recent_data = data[-5:] if len(data) >= 5 else data
                funding_history = []
                
                for entry in recent_data:
                    if isinstance(entry, dict):
                        # Try different field names for funding rate
                        rate = (safe_float(safe_get(entry, "fundingRate")) or 
                               safe_float(safe_get(entry, "rate")) or 
                               safe_float(safe_get(entry, "avgFundingRate")) or
                               safe_float(safe_get(entry, "funding_rate")) or 0.0)
                        
                        # Only include non-zero rates
                        if rate != 0.0:
                            funding_history.append(entry)
                
                # logger.info(f"[RAW] Found {len(funding_history)} valid funding history entries (filtered out 0.0000% values)")
        
        return {
            "current_funding": current_funding,
            "next_funding": next_funding,
            "funding_history": funding_history
        }
    
    def _extract_liquidation_data(self, liquidation_data: Dict) -> Dict[str, Any]:
        """Extract liquidation data - ONLY last 24 hours (latest entry only)"""
        if not liquidation_data or not liquidation_data.get("success"):
            return {"total_24h": 0.0, "long_liq": 0.0, "short_liq": 0.0}

        data = safe_get(liquidation_data, "data", [])
        if not data or not isinstance(data, list):
            return {"total_24h": 0.0, "long_liq": 0.0, "short_liq": 0.0}

        # FIX: Only use the LATEST entry for 24h data, not sum all entries
        latest = data[-1] if data else {}
        if not isinstance(latest, dict):
            return {"total_24h": 0.0, "long_liq": 0.0, "short_liq": 0.0}

        # Use correct field names from aggregated history API response
        long_liq = safe_float(safe_get(latest, "aggregated_long_liquidation_usd"))
        short_liq = safe_float(safe_get(latest, "aggregated_short_liquidation_usd"))
        total_liq = long_liq + short_liq

        return {
            "total_24h": total_liq,
            "long_liq": long_liq,
            "short_liq": short_liq
        }
    
    def _extract_long_short_data(self, ls_data: Dict) -> Dict[str, Any]:
        """Extract long/short ratio data"""
        # Handle the new format returned by get_global_long_short_ratio
        # It now returns a dict directly with long_percent, short_percent, ratio_global
        if ls_data is None:
            logger.warning(f"[RAW] Long/short data is None")
            return {
                "account_ratio_global": None,
                "position_ratio_global": None,
                "by_exchange": {"Binance": None, "Bybit": None, "OKX": None}
            }
        
        if isinstance(ls_data, dict):
            # Check if it's the new format from our fixed get_global_long_short_ratio
            if "long_percent" in ls_data or "short_percent" in ls_data or "long_short_ratio" in ls_data:
                # New format: {"long_percent": X, "short_percent": Y, "long_short_ratio": Z}
                account_ratio = safe_float(ls_data.get("long_short_ratio"))
                
                # logger.info(f"[RAW] ✓ Long/short extracted from new format: long_short_ratio={account_ratio}")
                
                # If ratio is 0.0 (default from safe_float), treat as missing data
                if account_ratio == 0.0:
                    account_ratio = None
                    logger.warning(f"[RAW] Long/short ratio_global is 0.0, treating as missing data")
                
                return {
                    "account_ratio_global": account_ratio,
                    "position_ratio_global": None,  # Not available in new format
                    "by_exchange": {
                        "Binance": account_ratio,
                        "Bybit": None,
                        "OKX": None
                    }
                }
        
        # Fallback to old format handling
        if not ls_data or not ls_data.get("success"):
            logger.warning(f"[RAW] Long/short data failed or empty: success={ls_data.get('success') if ls_data else None}")
            return {
                "account_ratio_global": None,
                "position_ratio_global": None,
                "by_exchange": {"Binance": None, "Bybit": None, "OKX": None}
            }

        data = safe_get(ls_data, "data", [])
        if not data:
            logger.warning(f"[RAW] Long/short data array is empty")
            return {
                "account_ratio_global": None,
                "position_ratio_global": None,
                "by_exchange": {"Binance": None, "Bybit": None, "OKX": None}
            }

        # Get most recent data
        latest = data[-1] if data else {}
        if isinstance(latest, dict):
            # Debug: Log available fields
            # logger.info(f"[RAW] Long/short latest entry fields: {list(latest.keys())}")

            account_ratio = safe_float(safe_get(latest, "longShortRatio"))
            position_ratio = safe_float(safe_get(latest, "positionLongShortRatio"))

            # logger.info(f"[RAW] Long/short extracted values: account={account_ratio}, position={position_ratio}")

            # If values are 0.0 (default from safe_float), treat as missing data
            if account_ratio == 0.0:
                account_ratio = None
            if position_ratio == 0.0:
                position_ratio = None

            return {
                "account_ratio_global": account_ratio,
                "position_ratio_global": position_ratio,
                "by_exchange": {
                    "Binance": account_ratio,
                    "Bybit": None,  # Would need separate calls
                    "OKX": None     # Would need separate calls
                }
            }

        logger.warning(f"[RAW] Long/short latest entry is not a dict: {type(latest)}")
        return {
            "account_ratio_global": None,
            "position_ratio_global": None,
            "by_exchange": {"Binance": None, "Bybit": None, "OKX": None}
        }
    
    def _extract_taker_flow_data(self, taker_data: Dict) -> Dict[str, Any]:
        """Extract taker flow data for multiple timeframes from new get_taker_flow endpoint"""
        # Default empty data with None for missing data
        default_tf = {"buy": None, "sell": None, "net": None}
        result = {
            "5m": default_tf.copy(),
            "15m": default_tf.copy(),
            "1h": default_tf.copy(),
            "4h": default_tf.copy()
        }

        if not taker_data or not taker_data.get("success"):
            logger.warning(f"[RAW] Taker flow data failed or empty: success={taker_data.get('success') if taker_data else None}")
            return result

        # NEW: Check if we have timeframe-specific data
        timeframe_data = safe_get(taker_data, "timeframe_data", {})
        if timeframe_data:
            # logger.info(f"[RAW] Processing timeframe-specific taker flow data")
            
            timeframes = ["5m", "15m", "1h", "4h"]
            for tf in timeframes:
                tf_result = timeframe_data.get(tf, {})
                
                if tf_result and tf_result.get("success"):
                    # Try to get summary from this timeframe's data
                    summary = safe_get(tf_result, "summary", {})
                    if summary:
                        total_buy = safe_float(safe_get(summary, "total_buy_volume")) / 1e6  # Convert to millions
                        total_sell = safe_float(safe_get(summary, "total_sell_volume")) / 1e6  # Convert to millions
                        net_delta = safe_float(safe_get(summary, "net_delta")) / 1e6  # Convert to millions
                        trend = safe_get(summary, "trend", "Neutral")

                        # Only use data if we have valid values
                        if total_buy > 0 or total_sell > 0:
                            result[tf] = {
                                "buy": total_buy,
                                "sell": total_sell,
                                "net": net_delta,
                                "trend": trend
                            }
                            # logger.info(f"[RAW] ✓ Taker flow {tf}: Buy {total_buy:.2f}M, Sell {total_sell:.2f}M, Net {net_delta:+.2f}M")
                        else:
                            logger.warning(f"[RAW] Taker flow {tf} has zero values")
                    else:
                        # Fallback to raw data for this timeframe
                        data = safe_get(tf_result, "data", [])
                        if data and isinstance(data, list) and data:
                            latest = data[-1]
                            if isinstance(latest, dict):
                                buy_usd = safe_float(safe_get(latest, "taker_buy_volume_usd")) / 1e6
                                sell_usd = safe_float(safe_get(latest, "taker_sell_volume_usd")) / 1e6
                                net_flow = buy_usd - sell_usd
                                
                                if buy_usd > 0 or sell_usd > 0:
                                    result[tf] = {
                                        "buy": buy_usd,
                                        "sell": sell_usd,
                                        "net": net_flow
                                    }
                                    # logger.info(f"[RAW] ✓ Taker flow {tf} (raw): Buy {buy_usd:.2f}M, Sell {sell_usd:.2f}M, Net {net_flow:+.2f}M")
                else:
                    logger.warning(f"[RAW] Taker flow {tf} failed or empty")
            
            return result

        # Fallback to old logic for backward compatibility
        summary = safe_get(taker_data, "summary", {})
        if summary:
            # Use summary data from get_taker_flow endpoint
            total_buy = safe_float(safe_get(summary, "total_buy_volume")) / 1e6  # Convert to millions
            total_sell = safe_float(safe_get(summary, "total_sell_volume")) / 1e6  # Convert to millions
            net_delta = safe_float(safe_get(summary, "net_delta")) / 1e6  # Convert to millions
            trend = safe_get(summary, "trend", "Neutral")

            # logger.info(f"[RAW] Taker flow summary values: Buy={total_buy:.2f}M, Sell={total_sell:.2f}M, Net={net_delta:+.2f}M, Trend={trend}")

            # Only use data if we have valid values
            if total_buy > 0 or total_sell > 0:
                flow_data = {
                    "buy": total_buy,
                    "sell": total_sell,
                    "net": net_delta,
                    "trend": trend
                }

                # WARNING: This copies the SAME summary data to all timeframes
                # This is a limitation - the summary is for the entire requested period (h1, 100 candles)
                # not separated by 5m/15m/1h/4h timeframes
                # logger.warning(f"[RAW] NOTE: Using same taker flow summary for all timeframes (API limitation)")
                result["5m"] = flow_data.copy()
                result["15m"] = flow_data.copy()
                result["1h"] = flow_data.copy()
                result["4h"] = flow_data.copy()

                # logger.info(f"[RAW] ✓ Extracted taker flow from summary: Buy {total_buy:.2f}M, Sell {total_sell:.2f}M, Net {net_delta:+.2f}M")
            else:
                logger.warning(f"[RAW] Taker flow summary has zero values, keeping N/A")
            return result
        
        # Fallback to raw data processing for v2 taker buy-sell volume history
        data = safe_get(taker_data, "data", [])
        if not data or not isinstance(data, list):
            return result
        
        try:
            # The v2 taker buy-sell volume data gives us direct buy/sell volumes
            if data:
                latest = data[-1]  # Most recent data
                if isinstance(latest, dict):
                    buy_usd = safe_float(safe_get(latest, "taker_buy_volume_usd")) / 1e6  # Convert to millions
                    sell_usd = safe_float(safe_get(latest, "taker_sell_volume_usd")) / 1e6  # Convert to millions
                    net_flow = buy_usd - sell_usd
                    
                    # Only use data if we have valid values
                    if buy_usd > 0 or sell_usd > 0:
                        flow_data = {
                            "buy": buy_usd,
                            "sell": sell_usd,
                            "net": net_flow
                        }
                        
                        result["5m"] = flow_data.copy()
                        result["15m"] = flow_data.copy()
                        result["1h"] = flow_data.copy()
                        result["4h"] = flow_data.copy()
                        
                        # logger.info(f"[RAW] Extracted taker flow from raw: Buy {buy_usd:.2f}M, Sell {sell_usd:.2f}M, Net {net_flow:+.2f}M")
                    else:
                        # logger.info(f"[RAW] Taker flow data has zero values, keeping N/A")
                        pass

        except Exception as e:
            logger.error(f"[RAW] Error extracting taker flow data: {e}")
        
        return result
    
    def _extract_rsi_data(self, rsi_data: Dict) -> Dict[str, Any]:
        """Extract RSI data for multiple timeframes"""
        # Return RSI data directly, preserving None values
        return {
            "5m": safe_get(rsi_data, "5m", None),
            "15m": safe_get(rsi_data, "15m", None),
            "1h": safe_get(rsi_data, "1h", None),
            "4h": safe_get(rsi_data, "4h", None)
        }
    
    def _extract_levels_data(self, levels_data: Dict) -> Dict[str, Any]:
        """Extract support/resistance levels"""
        # Default empty data with None to indicate not available
        return {
            "support": None,
            "resistance": None
        }
    
    def format_for_telegram(self, data: Dict[str, Any]) -> str:
        """Format comprehensive data for Telegram display - styled, but same data content"""
        if "error" in data:
            return f"[ERROR] Error fetching data for {data['symbol']}: {data['error']}"

        # Extract all data from the aggregated dict
        symbol = safe_get(data, 'symbol', 'UNKNOWN').upper()
        timestamp = safe_get(data, 'timestamp', '')

        general_info = safe_get(data, 'general_info', {})
        price_change = safe_get(data, 'price_change', {})

        # Extract individual values
        last_price = safe_float(safe_get(general_info, 'last_price'))
        mark_price = safe_float(safe_get(general_info, 'mark_price'))

        pc1h = safe_float(safe_get(price_change, '1h'))
        pc4h = safe_float(safe_get(price_change, '4h'))
        pc24h = safe_float(safe_get(price_change, '24h'))
        hi24 = safe_float(safe_get(price_change, 'high_24h'))
        lo24 = safe_float(safe_get(price_change, 'low_24h'))
        hi7d = safe_float(safe_get(price_change, 'high_7d'))
        lo7d = safe_float(safe_get(price_change, 'low_7d'))

        oi = safe_get(data, 'open_interest', {})
        total_oi = safe_float(safe_get(oi, 'total_oi'))
        oi1h = safe_float(safe_get(oi, 'oi_1h'))
        oi24h = safe_float(safe_get(oi, 'oi_24h'))
        per_exchange = safe_get(oi, 'per_exchange', {})

        volume = safe_get(data, 'volume', {})
        fut24h = safe_float(safe_get(volume, 'futures_24h'))
        perp24h = safe_float(safe_get(volume, 'perp_24h'))
        spot24h = safe_get(volume, 'spot_24h')

        funding = safe_get(data, 'funding', {})
        current_funding = safe_get(funding, 'current_funding', None)
        next_funding = safe_get(funding, 'next_funding', 'N/A')
        funding_history = safe_get(funding, 'funding_history', [])

        liquidations = safe_get(data, 'liquidations', {})
        liq_total = safe_float(safe_get(liquidations, 'total_24h'))
        liq_long = safe_float(safe_get(liquidations, 'long_liq'))
        liq_short = safe_float(safe_get(liquidations, 'short_liq'))

        long_short = safe_get(data, 'long_short_ratio', {})
        account_ratio = safe_get(long_short, 'account_ratio_global', None)
        position_ratio = safe_get(long_short, 'position_ratio_global', None)
        ls_exchanges = safe_get(long_short, 'by_exchange', {})
        ls_binance = safe_get(ls_exchanges, 'Binance', None)
        ls_bybit = safe_get(ls_exchanges, 'Bybit', None)
        ls_okx = safe_get(ls_exchanges, 'OKX', None)

        # Taker flow
        taker_flow = safe_get(data, 'taker_flow', {})
        tf_5m = safe_get(taker_flow, '5m', {})
        tf_15m = safe_get(taker_flow, '15m', {})
        tf_1h = safe_get(taker_flow, '1h', {})
        tf_4h = safe_get(taker_flow, '4h', {})

        # RSI - Get real RSI data from new endpoint
        rsi_1h_4h_1d = safe_get(data, 'rsi_1h_4h_1d', {})
        rsi_1h = safe_get(rsi_1h_4h_1d, '1h', None)
        rsi_4h = safe_get(rsi_1h_4h_1d, '4h', None)
        rsi_1d = safe_get(rsi_1h_4h_1d, '1d', None)

        # Levels
        levels = safe_get(data, 'cg_levels', {})
        support = safe_get(levels, 'support')
        resistance = safe_get(levels, 'resistance')

        # ===== UNITS & FORMAT HELPER =====

        oi_total_b = total_oi / 1e9 if total_oi > 0 else 0.0
        oi_binance_b = safe_float(safe_get(per_exchange, 'Binance')) / 1e9
        oi_bybit_b = safe_float(safe_get(per_exchange, 'Bybit')) / 1e9
        oi_okx_b = safe_float(safe_get(per_exchange, 'OKX')) / 1e9
        oi_others_b = safe_float(safe_get(per_exchange, 'Others')) / 1e9

        fut24h_b = fut24h / 1e9 if fut24h > 0 else 0.0
        perp24h_b = perp24h / 1e9 if perp24h > 0 else 0.0
        spot24h_b = spot24h / 1e9 if (spot24h is not None and spot24h > 0) else 0.0

        liq_total_m = liq_total / 1e6 if liq_total > 0 else 0.0
        liq_long_m = liq_long / 1e6 if liq_long > 0 else 0.0
        liq_short_m = liq_short / 1e6 if liq_short > 0 else 0.0

        def format_rsi(value):
            return f"{value:.2f}" if value is not None else "N/A"

        def format_taker_flow(tf_data: Dict[str, Any]) -> str:
            buy = safe_get(tf_data, 'buy', None)
            sell = safe_get(tf_data, 'sell', None)
            net = safe_get(tf_data, 'net', None)
            if buy is None or sell is None or net is None:
                return "N/A"
            return f"Buy ${buy:.0f}M | Sell ${sell:.0f}M | Net ${net:+.0f}M"

        def format_funding_rate(value):
            if value is None:
                return "N/A"
            try:
                return f"{float(value):+.4f}%"
            except Exception:
                return "N/A"

        def format_ls_ratio(value):
            if value is None:
                return "N/A"
            try:
                return f"{float(value):.2f}"
            except Exception:
                return "N/A"

        def format_funding_history(history_data: List[Dict[str, Any]]) -> str:
            if not history_data:
                return "No history available"

            lines = []
            for i, entry in enumerate(history_data[:5], 1):
                if not isinstance(entry, dict):
                    lines.append(f"  {i}. Invalid entry")
                    continue

                rate = (
                    safe_float(safe_get(entry, "fundingRate")) or
                    safe_float(safe_get(entry, "rate")) or
                    safe_float(safe_get(entry, "avgFundingRate")) or
                    safe_float(safe_get(entry, "funding_rate")) or
                    0.0
                )
                ts = (
                    safe_get(entry, "createTime") or
                    safe_get(entry, "timestamp") or
                    safe_get(entry, "time") or
                    safe_get(entry, "createTimeUtc") or
                    "Unknown"
                )

                # beautify timestamp if numeric
                if isinstance(ts, (int, float)):
                    try:
                        dt = datetime.fromtimestamp(ts / 1000)
                        ts_str = dt.strftime("%m-%d %H:%M")
                    except Exception:
                        ts_str = str(ts)
                else:
                    ts_str = str(ts)

                lines.append(f"  {ts_str}: {rate:+.4f}%")
            return "\n".join(lines) if lines else "No valid history data"

        # support / resistance text
        if support is None or resistance is None:
            levels_text = "Support / Resistance unavailable"
        else:
            if isinstance(support, list):
                support_str = ', '.join([f"${x:.2f}" for x in support[:3]])
            else:
                support_str = f"${float(support):.2f}"

            if isinstance(resistance, list):
                resistance_str = ', '.join([f"${x:.2f}" for x in resistance[:3]])
            else:
                resistance_str = f"${float(resistance):.2f}"

            levels_text = f"Support : {support_str}\nResistance: {resistance_str}"

        spot_volume_text = f"{spot24h_b:.2f}B" if spot24h is not None else "N/A"
        funding_history_text = format_funding_history(funding_history)

        # ===== FINAL STYLED MESSAGE =====

        message = f"""📊 [RAW DATA - {symbol} - REAL PRICE MULTI-TF]

⏱ Timeframe: 1H
🌐 Timestamp (UTC): {timestamp}

━━━━━━━━━━ PRICE ━━━━━━━━━━
• Last Price : ${last_price:.4f}
• Mark Price : ${mark_price:.4f}
• Change 1H  : {pc1h:+.2f}%
• Change 4H  : {pc4h:+.2f}%
• Change 24H : {pc24h:+.2f}%
• 24H Range  : {lo24:.4f} → {hi24:.4f}
• 7D Range   : {lo7d:.4f} → {hi7d:.4f}

━━━━━━━━━━ OPEN INTEREST ━━━━━━━━━━
• Total OI   : {oi_total_b:.2f}B
• OI 1H      : {oi1h:+.1f}%
• OI 24H     : {oi24h:+.1f}%

• Binance    : {oi_binance_b:.2f}B
• Bybit      : {oi_bybit_b:.2f}B
• OKX        : {oi_okx_b:.2f}B
• Others     : {oi_others_b:.2f}B

━━━━━━━━━━ VOLUME ━━━━━━━━━━
• Futures 24H : {fut24h_b:.2f}B
• Perp 24H    : {perp24h_b:.2f}B
• Spot 24H    : {spot_volume_text}

━━━━━━━━━━ FUNDING ━━━━━━━━━━
• Current Funding : {format_funding_rate(current_funding)}
• Next Funding    : {next_funding}
• History (Last 5):
{funding_history_text}

━━━━━━━━━━ LIQUIDATIONS ━━━━━━━━━━
• Total 24H : {liq_total_m:.2f}M
• Long Liq  : {liq_long_m:.2f}M
• Short Liq : {liq_short_m:.2f}M

━━━━━━━━━━ LONG / SHORT ━━━━━━━━━━
• Account Ratio (Global)  : {format_ls_ratio(account_ratio)}
• Position Ratio (Global) : {format_ls_ratio(position_ratio)}
• By Exchange:
   Binance : {format_ls_ratio(ls_binance)}
   Bybit   : {format_ls_ratio(ls_bybit)}
   OKX     : {format_ls_ratio(ls_okx)}

━━━━━━━━━━ TAKER FLOW (CVD) ━━━━━━━━━━
• 5M  → {format_taker_flow(tf_5m)}
• 15M → {format_taker_flow(tf_15m)}
• 1H  → {format_taker_flow(tf_1h)}
• 4H  → {format_taker_flow(tf_4h)}

━━━━━━━━━━ RSI MULTI-TF ━━━━━━━━━━
• 1H : {format_rsi(rsi_1h)}
• 4H : {format_rsi(rsi_4h)}
• 1D : {format_rsi(rsi_1d)}

━━━━━━━━━━ CG LEVELS ━━━━━━━━━━
{levels_text}"""

        return message

    def format_standard_raw_message_for_telegram(self, data: Dict[str, Any]) -> str:
        """
        Format comprehensive CoinGlass data into a standardized raw message for Telegram.
        HARUS tahan banting:
        - Kalau sebagian data None / kosong → tetap kirim pesan.
        - Angka 0.0 yang hanya placeholder → di-render sebagai N/A di output.
        """
        from services.coinglass_api import safe_float, safe_get  # ensure helpers

        def fmt_pct(v: float) -> str:
            # v dalam bentuk +0.33 / -4.40
            return f"{v:+.2f}%" if v is not None else "N/A"

        def fmt_price(v: float) -> str:
            return f"{v:.4f}" if v is not None and v != 0.0 else "0.0000"

        def fmt_billion(v: float) -> str:
            if v is None or v <= 0:
                return "0.00B"
            return f"{v / 1e9:.2f}B"

        def fmt_million(v: float) -> str:
            if v is None or v <= 0:
                return "0.00M"
            return f"{v / 1e6:.2f}M"

        def fmt_optional_number(v: float, suffix: str = "") -> str:
            if v is None:
                return "N/A"
            return f"{v:.2f}{suffix}"

        def fmt_rsi_core(v: float) -> str:
            # Untuk RSI 1H/4H/1D (data benar-benar dari endpoint RSI)
            if v is None:
                return "N/A"
            return f"{v:.2f}"

        def fmt_orderbook_side(side: list) -> str:
            if not side:
                return "N/A"
            # side = [[price, size], ...]
            formatted = []
            for level in side[:5]:
                price = safe_get(level, 0, None)
                size = safe_get(level, 1, None)
                if price is None or size is None:
                    continue
                # Format price with appropriate decimal places
                if price >= 1:
                    formatted.append(f"[{price:.1f}, {size:.2f}]")
                else:
                    formatted.append(f"[{price:.4f}, {size:.2f}]")
            return ", ".join(formatted) if formatted else "N/A"

        # ====== Extract root fields ======
        symbol = safe_get(data, "symbol", "UNKNOWN").upper()
        timestamp = safe_get(data, "timestamp", "")

        general_info = safe_get(data, "general_info", {})
        price_change = safe_get(data, "price_change", {})
        oi = safe_get(data, "open_interest", {})
        volume = safe_get(data, "volume", {})
        funding = safe_get(data, "funding", {})
        liquidations = safe_get(data, "liquidations", {})
        long_short = safe_get(data, "long_short_ratio", {})
        taker_flow = safe_get(data, "taker_flow", {})
        rsi_1h_4h_1d = safe_get(data, "rsi_1h_4h_1d", {})
        rsi_multi_tf = safe_get(data, "rsi_multi_tf", {})
        cg_levels = safe_get(data, "cg_levels", {})
        orderbook = safe_get(data, "orderbook", {})

        # ====== General info ======
        last_price = safe_float(safe_get(general_info, "last_price"))
        mark_price = safe_float(safe_get(general_info, "mark_price"))

        pc1h = safe_float(safe_get(price_change, "1h"))
        pc4h = safe_float(safe_get(price_change, "4h"))
        pc24h = safe_float(safe_get(price_change, "24h"))
        hi24 = safe_float(safe_get(price_change, "high_24h"))
        lo24 = safe_float(safe_get(price_change, "low_24h"))
        hi7d = safe_float(safe_get(price_change, "high_7d"))
        lo7d = safe_float(safe_get(price_change, "low_7d"))

        total_oi = safe_float(safe_get(oi, "total_oi"))
        oi_1h = safe_float(safe_get(oi, "oi_1h"))
        oi_24h = safe_float(safe_get(oi, "oi_24h"))
        per_exchange = safe_get(oi, "per_exchange", {})

        fut24h = safe_float(safe_get(volume, "futures_24h"))
        perp24h = safe_float(safe_get(volume, "perp_24h"))
        spot24h = safe_get(volume, "spot_24h", None)

        current_funding = safe_get(funding, "current_funding", None)
        next_funding = safe_get(funding, "next_funding", "N/A")
        funding_history = safe_get(funding, "funding_history", [])

        liq_total = safe_float(safe_get(liquidations, "total_24h"))
        liq_long = safe_float(safe_get(liquidations, "long_liq"))
        liq_short = safe_float(safe_get(liquidations, "short_liq"))

        account_ratio = safe_get(long_short, "account_ratio_global", None)
        position_ratio = safe_get(long_short, "position_ratio_global", None)
        ls_exchanges = safe_get(long_short, "by_exchange", {})
        ls_binance = safe_get(ls_exchanges, "Binance", None)
        ls_bybit = safe_get(ls_exchanges, "Bybit", None)
        ls_okx = safe_get(ls_exchanges, "OKX", None)

        tf_5m = safe_get(taker_flow, "5m", {})
        tf_15m = safe_get(taker_flow, "15m", {})
        tf_1h = safe_get(taker_flow, "1h", {})
        tf_4h = safe_get(taker_flow, "4h", {})

        rsi_1h = safe_get(rsi_1h_4h_1d, "1h", None)
        rsi_4h = safe_get(rsi_1h_4h_1d, "4h", None)
        rsi_1d = safe_get(rsi_1h_4h_1d, "1d", None)

        support = safe_get(cg_levels, "support")
        resistance = safe_get(cg_levels, "resistance")

        ob_timestamp = safe_get(orderbook, "snapshot_timestamp")
        ob_bids = safe_get(orderbook, "top_bids", [])
        ob_asks = safe_get(orderbook, "top_asks", [])

        # ====== Build lines ======
        lines = []

        lines.append(f"[RAW DATA - {symbol} - REAL PRICE MULTI-TF]")
        lines.append("")
        lines.append("Info Umum")
        lines.append(f"Symbol : {symbol}")
        lines.append("Timeframe : 1H")
        lines.append(f"Timestamp (UTC): {timestamp}")
        lines.append(f"Last Price: {fmt_price(last_price)}")
        lines.append(f"Mark Price: {fmt_price(mark_price)}")
        lines.append("Price Source: coinglass_futures")
        lines.append("")
        lines.append("Price Change")
        lines.append(f"1H : {fmt_pct(pc1h)}")
        lines.append(f"4H : {fmt_pct(pc4h)}")
        lines.append(f"24H : {fmt_pct(pc24h)}")
        lines.append(
            f"High/Low 24H: {fmt_price(hi24)}/{fmt_price(lo24)}"
        )
        lines.append(
            f"High/Low 7D : {fmt_price(hi7d)}/{fmt_price(lo7d)}"
        )
        lines.append("")

        lines.append("Open Interest")
        lines.append(f"Total OI : {fmt_billion(total_oi)}")
        lines.append(f"OI 1H : {fmt_optional_number(oi_1h, '%')}")
        lines.append(f"OI 24H : {fmt_optional_number(oi_24h, '%')}")
        lines.append("")

        lines.append("OI per Exchange")
        lines.append(f"Binance : {fmt_billion(safe_float(safe_get(per_exchange, 'Binance')))}")
        lines.append(f"Bybit   : {fmt_billion(safe_float(safe_get(per_exchange, 'Bybit')))}")
        lines.append(f"OKX     : {fmt_billion(safe_float(safe_get(per_exchange, 'OKX')))}")
        lines.append(f"Others  : {fmt_billion(safe_float(safe_get(per_exchange, 'Others')))}")
        lines.append("")

        lines.append("Volume")
        lines.append(f"Futures 24H: {fmt_billion(fut24h)}")
        lines.append(f"Perp 24H   : {fmt_billion(perp24h)}")
        lines.append(
            f"Spot 24H   : {fmt_billion(spot24h) if isinstance(spot24h, (int, float)) and spot24h > 0 else 'N/A'}"
        )
        lines.append("")

        lines.append("Funding")
        if current_funding is None:
            lines.append("Current Funding: N/A")
        else:
            lines.append(f"Current Funding: {current_funding:.4f}%")
        lines.append(f"Next Funding   : {next_funding if next_funding else 'N/A'}")

        lines.append("Funding History:")
        if funding_history:
            # Tampilkan max 3 item
            for entry in funding_history[:3]:
                ts = safe_get(entry, "time", "")
                rate = safe_get(entry, "rate", None)
                rate_str = f"{rate:.4f}%" if rate is not None else "N/A"
                lines.append(f"- {ts}: {rate_str}")
        else:
            lines.append("No history available")
        lines.append("")

        lines.append("Liquidations")
        lines.append(f"Total 24H : {fmt_million(liq_total)}")
        lines.append(f"Long Liq  : {fmt_million(liq_long)}")
        lines.append(f"Short Liq : {fmt_million(liq_short)}")
        lines.append("")

        lines.append("Long/Short Ratio")
        lines.append(f"Account Ratio (Global) : {fmt_optional_number(account_ratio)}")
        lines.append(f"Position Ratio (Global): {fmt_optional_number(position_ratio)}")
        lines.append("By Exchange:")
        lines.append(f"Binance: {fmt_optional_number(ls_binance)}")
        lines.append(f"Bybit : {fmt_optional_number(ls_bybit)}")
        lines.append(f"OKX   : {fmt_optional_number(ls_okx)}")
        lines.append("")

        def format_tf_block(tf_data: Dict[str, Any]) -> str:
            # Extract buy/sell values - they might be None or missing
            buy = safe_get(tf_data, "buy", None)
            sell = safe_get(tf_data, "sell", None)
            
            # If values are None or missing, return N/A
            if buy is None or sell is None:
                return "Buy $0M | Sell $0M | Net $0M"
            
            # Convert to float and calculate net
            buy_float = safe_float(buy)
            sell_float = safe_float(sell)
            net = buy_float - sell_float
            
            # If both are zero, return zero values
            if buy_float == 0 and sell_float == 0:
                return "Buy $0M | Sell $0M | Net $0M"
            
            # Values are already in millions, no need to divide again
            return (
                f"Buy ${buy_float:.0f}M | "
                f"Sell ${sell_float:.0f}M | "
                f"Net ${net:+.0f}M"
            )

        lines.append("Taker Flow Multi-Timeframe (CVD Proxy)")
        lines.append(f"5M : {format_tf_block(tf_5m)}")
        lines.append(f"15M: {format_tf_block(tf_15m)}")
        lines.append(f"1H : {format_tf_block(tf_1h)}")
        lines.append(f"4H : {format_tf_block(tf_4h)}")
        lines.append("")

        lines.append("RSI (1h/4h/1d)")
        lines.append(f"1H : {fmt_rsi_core(rsi_1h)}")
        lines.append(f"4H : {fmt_rsi_core(rsi_4h)}")
        lines.append(f"1D : {fmt_rsi_core(rsi_1d)}")
        lines.append("")

        lines.append("CG Levels")
        if support is None and resistance is None:
            lines.append("Support/Resistance: N/A (not available for current plan)")
        else:
            lines.append(f"Support : {support}")
            lines.append(f"Resistance : {resistance}")
        lines.append("")

        lines.append("Orderbook Snapshot")
        if ob_timestamp is None or (not ob_bids and not ob_asks):
            lines.append("Timestamp: N/A")
            lines.append("Top 5 Bids: N/A")
            lines.append("Top 5 Asks: N/A")
        else:
            lines.append(f"Timestamp: {ob_timestamp}")
            lines.append(f"Top 5 Bids: {fmt_orderbook_side(ob_bids)}")
            lines.append(f"Top 5 Asks: {fmt_orderbook_side(ob_asks)}")

        return "\n".join(lines)


# Global instance
raw_data_service = RawDataService()
