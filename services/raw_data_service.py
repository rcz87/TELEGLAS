import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from loguru import logger
from services.coinglass_api import coinglass_api, safe_float, safe_int, safe_get, safe_list_get
from config.settings import settings


class RawDataService:
    """Service for fetching and formatting raw market data from multiple endpoints"""
    
    def __init__(self):
        # Use the global instance to ensure consistent cache
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
                # Continue with original symbol instead of returning error
                resolved_symbol = symbol.upper()
            
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
        """Get market data - uses futures coins markets endpoint with fallback strategy"""
        try:
            # First try the standard approach
            result = await self.api.get_futures_coins_markets(symbol)
            
            # Check if symbol is found in the response
            if result and result.get("success"):
                data = safe_get(result, "data", [])
                if data:
                    # Look for our symbol in the data
                    for item in data:
                        if isinstance(item, dict) and safe_get(item, "symbol") == symbol:
                            logger.info(f"[RAW] Found {symbol} in standard market data")
                            return result
            
            # If not found in first 100, try to get specific symbol data
            logger.warning(f"[RAW] {symbol} not found in first 100 market symbols, trying alternative approach")
            
            # Try to get market data using a more specific approach
            # We'll use the symbol resolution to get the correct format
            resolved_symbol = await self.api.resolve_symbol(symbol)
            if resolved_symbol:
                # Try with resolved symbol
                result = await self.api.get_futures_coins_markets(resolved_symbol)
                if result and result.get("success"):
                    data = safe_get(result, "data", [])
                    if data:
                        # Look for resolved symbol
                        for item in data:
                            if isinstance(item, dict) and safe_get(item, "symbol") == resolved_symbol:
                                logger.info(f"[RAW] Found {resolved_symbol} in resolved market data")
                                # Add original symbol for compatibility
                                result["symbol"] = symbol
                                return result
            
            # If still not found, create a minimal structure with available data
            logger.warning(f"[RAW] {symbol} not found in market data, using minimal structure")
            
            # Try to get at least basic price data from other endpoints
            try:
                # Get current price from alternative source
                price_data = await self.api.get_current_funding_rate(symbol, "Binance")
                current_price = 0.0
                
                # Create minimal market data structure
                minimal_data = {
                    "success": True,
                    "symbol": symbol,
                    "data": [{
                        "symbol": symbol,
                        "current_price": current_price,
                        "price_change_percent_1h": None,
                        "price_change_percent_4h": None,
                        "price_change_percent_24h": None,
                        "long_volume_usd_24h": None,
                        "short_volume_usd_24h": None,
                        "open_interest_usd": None
                    }]
                }
                logger.info(f"[RAW] Created minimal market data for {symbol}")
                return minimal_data
                
            except Exception as e:
                logger.error(f"[RAW] Failed to create minimal market data for {symbol}: {e}")
                return {"success": False, "symbol": symbol, "data": []}
                
        except Exception as e:
            logger.error(f"[RAW] Error in get_market for {symbol}: {e}")
            return {"success": False, "symbol": symbol, "data": []}
    
    async def get_open_interest(self, symbol: str) -> Dict[str, Any]:
        """Get AGGREGATED open interest data across multiple exchanges - FIX for CoinGlass UI consistency"""
        try:
            # NEW: Get aggregated OI across ALL major exchanges
            # This matches what CoinGlass UI displays (aggregated, not single exchange)
            result = await self.api.get_open_interest_aggregated_history(
                symbol=symbol,
                interval="1h",
                limit=100
            )
            
            if not result or not result.get("success"):
                logger.warning(f"[RAW] Failed to get aggregated OI for {symbol}, trying exchange breakdown")
                # Fallback to exchange list if aggregation fails
                fallback_result = await self.api.get_open_interest_exchange_list(symbol)
                return {
                    "success": True,
                    "data_type": "single_exchange_fallback",
                    "exchange": "Binance",
                    "data": fallback_result.get("data", [])
                }
            
            # Process aggregated OI data
            data = result.get("data", [])
            if not data:
                logger.warning(f"[RAW] No aggregated OI data for {symbol}")
                return {
                    "success": True,
                    "data_type": "multi_exchange_aggregated",
                    "data": [],
                    "total_oi": 0.0,
                    "exchange_count": 0
                }
            
            # Get the most recent OI data
            latest_data = data[-1] if data else None
            if latest_data and isinstance(latest_data, dict):
                total_oi = safe_float(latest_data.get("openInterestSum", 0))
                
                logger.info(f"[RAW] ✓ Aggregated OI for {symbol}: ${total_oi:,.0f}")
                
                return {
                    "success": True,
                    "data_type": "multi_exchange_aggregated",
                    "data": data,
                    "total_oi": total_oi,
                    "latest_timestamp": latest_data.get("time"),
                    "exchange_count": "aggregated"
                }
            
            # Fallback if no valid data
            logger.warning(f"[RAW] No valid aggregated OI data for {symbol}, trying exchange breakdown")
            fallback_result = await self.api.get_open_interest_exchange_list(symbol)
            return {
                "success": True,
                "data_type": "exchange_breakdown_fallback",
                "data": fallback_result.get("data", [])
            }
            
        except Exception as e:
            logger.error(f"[RAW] Error in get_open_interest for {symbol}: {e}")
            # Final fallback to exchange list
            try:
                fallback_result = await self.api.get_open_interest_exchange_list(symbol)
                return {
                    "success": True,
                    "data_type": "exchange_breakdown_fallback",
                    "data": fallback_result.get("data", [])
                }
            except Exception as fallback_error:
                logger.error(f"[RAW] Even OI fallback failed for {symbol}: {fallback_error}")
                return {}
    
    async def get_oi_exchange_breakdown(self, symbol: str) -> Dict[str, Any]:
        """Get OI breakdown by exchange - ENHANCED with multi-exchange support"""
        try:
            # Get OI from multiple exchanges for comprehensive breakdown
            result = await self.api.get_open_interest_exchange_list(symbol)
            
            if not result or not result.get("success"):
                logger.warning(f"[RAW] Failed to get OI breakdown for {symbol}")
                return {
                    "success": False,
                    "data": [],
                    "exchange_breakdown": {}
                }
            
            data = result.get("data", [])
            if not data:
                return {
                    "success": True,
                    "data": [],
                    "exchange_breakdown": {},
                    "total_oi": 0.0,
                    "exchange_count": 0
                }
            
            # Process OI breakdown by exchange
            exchange_oi = {}
            total_oi = 0.0
            
            for item in data:
                if isinstance(item, dict):
                    exchange_name = str(item.get("exchangeName", "")).lower()
                    oi_value = safe_float(item.get("openInterestSum", 0))
                    
                    if oi_value > 0:
                        # Standardize exchange names
                        if "binance" in exchange_name:
                            exchange_oi["Binance"] = oi_value
                        elif "bybit" in exchange_name:
                            exchange_oi["Bybit"] = oi_value
                        elif "okx" in exchange_name or "ok" in exchange_name:
                            exchange_oi["OKX"] = oi_value
                        elif "bitget" in exchange_name:
                            exchange_oi["Bitget"] = oi_value
                        elif "kucoin" in exchange_name:
                            exchange_oi["KuCoin"] = oi_value
                        else:
                            exchange_oi[exchange_name.title()] = oi_value
                        
                        total_oi += oi_value
            
            logger.info(f"[RAW] ✓ OI breakdown for {symbol}: ${total_oi:,.0f} across {len(exchange_oi)} exchanges")
            
            return {
                "success": True,
                "data": data,
                "exchange_breakdown": exchange_oi,
                "total_oi": total_oi,
                "exchange_count": len(exchange_oi),
                "top_exchange": max(exchange_oi.items(), key=lambda x: x[1]) if exchange_oi else None
            }
            
        except Exception as e:
            logger.error(f"[RAW] Error in get_oi_exchange_breakdown for {symbol}: {e}")
            return {
                "success": False,
                "data": [],
                "exchange_breakdown": {},
                "total_oi": 0.0,
                "exchange_count": 0
            }
    
    async def get_liquidations(self, symbol: str) -> Dict[str, Any]:
        """Get AGGREGATED liquidation data across multiple exchanges - FIX for CoinGlass UI consistency"""
        try:
            # NEW: Get aggregated liquidations across ALL major exchanges
            # This matches what CoinGlass UI displays (aggregated, not single exchange)
            result = await self.api.get_liquidation_aggregated_history(
                symbol=symbol,
                exchanges="Binance,Bybit,OKX,Bitget,KuCoin",  # Major exchanges
                interval="1d",  # Use 1d for comprehensive 24h data
                limit=100
            )
            
            if not result or not result.get("success"):
                logger.warning(f"[RAW] Failed to get aggregated liquidations for {symbol}, trying single exchange")
                # Fallback to exchange list if aggregation fails
                fallback_result = await self.api.get_liquidation_exchange_list(symbol, "24h")
                return {
                    "success": True,
                    "data_type": "single_exchange_fallback",
                    "exchange": "Binance",
                    "data": fallback_result.get("data", [])
                }
            
            # Process aggregated liquidation data
            data = result.get("data", [])
            if not data:
                logger.warning(f"[RAW] No aggregated liquidation data for {symbol}")
                return {
                    "success": True,
                    "data_type": "multi_exchange_aggregated",
                    "data": [],
                    "total_liquidations_24h": 0.0,
                    "exchange_count": 0
                }
            
            # Calculate total liquidations across all exchanges
            total_liquidations_24h = 0.0
            total_long_liq = 0.0
            total_short_liq = 0.0
            exchange_liquidations = {}
            
            for item in data:
                if isinstance(item, dict):
                    exchange_name = str(item.get("exchange", "")).lower()
                    amount_usd = safe_float(item.get("amountUsd", 0))
                    side = str(item.get("side", "")).lower()
                    
                    # Skip invalid amounts
                    if amount_usd < 0:
                        continue
                    
                    # Add to totals
                    total_liquidations_24h += amount_usd
                    
                    if "long" in side:
                        total_long_liq += amount_usd
                    elif "short" in side:
                        total_short_liq += amount_usd
                    
                    # Track by exchange
                    if exchange_name not in exchange_liquidations:
                        exchange_liquidations[exchange_name] = 0.0
                    exchange_liquidations[exchange_name] += amount_usd
            
            logger.info(f"[RAW] ✓ Aggregated liquidations for {symbol}: ${total_liquidations_24h:,.0f} ({len(exchange_liquidations)} exchanges)")
            
            return {
                "success": True,
                "data_type": "multi_exchange_aggregated",
                "data": data,
                "total_liquidations_24h": total_liquidations_24h,
                "long_liquidations_24h": total_long_liq,
                "short_liquidations_24h": total_short_liq,
                "exchange_breakdown": exchange_liquidations,
                "exchange_count": len(exchange_liquidations),
                "liquidation_ratio": total_long_liq / max(total_short_liq, 1.0)
            }
            
        except Exception as e:
            logger.error(f"[RAW] Error in get_liquidations for {symbol}: {e}")
            # Final fallback to single exchange
            try:
                fallback_result = await self.api.get_liquidation_exchange_list(symbol, "24h")
                return {
                    "success": True,
                    "data_type": "single_exchange_fallback",
                    "exchange": "Binance",
                    "data": fallback_result.get("data", [])
                }
            except Exception as fallback_error:
                logger.error(f"[RAW] Even liquidation fallback failed for {symbol}: {fallback_error}")
                return {}
    
    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get AGGREGATED funding rate across multiple exchanges - FIX for CoinGlass UI consistency"""
        try:
            # NEW: Get aggregated funding rate across ALL major exchanges
            # This matches what CoinGlass UI displays (aggregated, not single exchange)
            result = await self.api.get_funding_rate_exchange_list(symbol)
            
            if not result or not result.get("success"):
                logger.warning(f"[RAW] Failed to get aggregated funding for {symbol}, falling back to Binance")
                # Fallback to single exchange if aggregation fails
                fallback_result = await self.api.get_current_funding_rate(symbol, "Binance")
                return {
                    "success": True,
                    "data_type": "single_exchange_fallback",
                    "exchange": "Binance",
                    "aggregated_rate": fallback_result,
                    "by_exchange": {"Binance": fallback_result}
                }
            
            # Process aggregated data from multiple exchanges
            data = result.get("data", [])
            if not data:
                logger.warning(f"[RAW] No aggregated funding data for {symbol}, falling back to Binance")
                fallback_result = await self.api.get_current_funding_rate(symbol, "Binance")
                return {
                    "success": True,
                    "data_type": "single_exchange_fallback",
                    "exchange": "Binance",
                    "aggregated_rate": fallback_result,
                    "by_exchange": {"Binance": fallback_result}
                }
            
            # Calculate weighted average funding rate across exchanges
            exchange_rates = {}
            total_weight = 0.0
            weighted_sum = 0.0
            
            # Major exchanges with typical volume weights
            exchange_weights = {
                "Binance": 0.40,
                "Bybit": 0.25, 
                "OKX": 0.15,
                "Bitget": 0.08,
                "KuCoin": 0.07,
                "Others": 0.05
            }
            
            for item in data:
                if isinstance(item, dict):
                    exchange_name = str(item.get("exchange", "")).lower()
                    rate = safe_float(item.get("fundingRate"))
                    
                    # Skip invalid rates
                    if abs(rate) > 0.1:  # Filter unrealistic rates > 10%
                        continue
                    
                    # Map to standard exchange names
                    if "binance" in exchange_name:
                        exchange_rates["Binance"] = rate
                        weighted_sum += rate * exchange_weights["Binance"]
                        total_weight += exchange_weights["Binance"]
                    elif "bybit" in exchange_name:
                        exchange_rates["Bybit"] = rate
                        weighted_sum += rate * exchange_weights["Bybit"]
                        total_weight += exchange_weights["Bybit"]
                    elif "okx" in exchange_name or "ok" in exchange_name:
                        exchange_rates["OKX"] = rate
                        weighted_sum += rate * exchange_weights["OKX"]
                        total_weight += exchange_weights["OKX"]
                    elif "bitget" in exchange_name:
                        exchange_rates["Bitget"] = rate
                        weighted_sum += rate * exchange_weights["Bitget"]
                        total_weight += exchange_weights["Bitget"]
                    elif "kucoin" in exchange_name:
                        exchange_rates["KuCoin"] = rate
                        weighted_sum += rate * exchange_weights["KuCoin"]
                        total_weight += exchange_weights["KuCoin"]
            
            # Calculate weighted average
            if total_weight > 0:
                aggregated_rate = weighted_sum / total_weight
            else:
                # Fallback to simple average if no weights applied
                valid_rates = [r for r in exchange_rates.values() if r != 0]
                aggregated_rate = sum(valid_rates) / len(valid_rates) if valid_rates else 0.0
            
            logger.info(f"[RAW] ✓ Aggregated funding for {symbol}: {aggregated_rate:.6f} ({len(exchange_rates)} exchanges)")
            
            return {
                "success": True,
                "data_type": "multi_exchange_aggregated",
                "aggregated_rate": aggregated_rate * 100.0,  # Convert to percentage
                "by_exchange": {k: v * 100.0 for k, v in exchange_rates.items()},  # Convert to percentage
                "exchange_count": len(exchange_rates),
                "total_weight": total_weight
            }
            
        except Exception as e:
            logger.error(f"[RAW] Error in get_funding_rate for {symbol}: {e}")
            # Final fallback to Binance
            try:
                fallback_result = await self.api.get_current_funding_rate(symbol, "Binance")
                return {
                    "success": True,
                    "data_type": "single_exchange_fallback",
                    "exchange": "Binance",
                    "aggregated_rate": fallback_result,
                    "by_exchange": {"Binance": fallback_result}
                }
            except Exception as fallback_error:
                logger.error(f"[RAW] Even fallback failed for {symbol}: {fallback_error}")
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
            # FIXED: Use base symbol directly, not futures_pair
            # get_global_long_short_ratio expects base symbol (BTC), not futures_pair (BTCUSDT)
            result = await self.api.get_global_long_short_ratio(symbol, "h1", "Binance")
            
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
                        logger.info(f"[RAW] OK RSI {tf} for {normalized_symbol}: {rsi_value:.2f}")
                    else:
                        rsi_data[tf] = None
                        logger.warning(f"[RAW] Invalid RSI value {rsi_value} for {tf}, setting to None")
                else:
                    rsi_data[tf] = None
                    # Only log warning for 4h since it's commonly failing, others are expected to be None
                    if tf == "4h":
                        logger.warning(f"[RAW] RSI {tf} for {normalized_symbol} returned None - API may not have data for this timeframe")

            # DEBUG LOGGING: Log final RSI dict for verification
            # logger.info(f"[DEBUG RSI] Final RSI dict for {symbol}: {rsi_data}")

            return rsi_data

        except Exception as e:
            logger.error(f"[RAW] Error in get_rsi_1h_4h_1d for {symbol}: {e}")
            import traceback
            logger.error(f"[RAW] Traceback: {traceback.format_exc()}")
            # Return None data on error
            return {"1h": None, "4h": None, "1d": None}

    # DATA EXTRACTION METHODS
    
    def _extract_general_info(self, market_data: Dict) -> Dict[str, Any]:
        """Extract general info data"""
        if not market_data or not market_data.get("success"):
            return {"last_price": 0.0, "mark_price": 0.0}
        
        data = safe_get(market_data, "data", [])
        if not data:
            return {"last_price": 0.0, "mark_price": 0.0}
        
        # Find matching symbol in list
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
    
    def _extract_price_change_data(self, market_data: Dict) -> Dict[str, Any]:
        """Extract price change data"""
        if not market_data or not market_data.get("success"):
            return {"change_1h": 0.0, "change_4h": 0.0, "change_24h": 0.0}
        
        data = safe_get(market_data, "data", [])
        if not data:
            return {"change_1h": 0.0, "change_4h": 0.0, "change_24h": 0.0}
        
        # Find matching symbol in list
        for item in data:
            if isinstance(item, dict) and safe_get(item, "symbol") == safe_get(market_data, "symbol", ""):
                return {
                    "change_1h": safe_float(safe_get(item, "price_change_percent_1h")),
                    "change_4h": safe_float(safe_get(item, "price_change_percent_4h")),
                    "change_24h": safe_float(safe_get(item, "price_change_percent_24h"))
                }
        
        # If no matching symbol, use first item
        if data and len(data) > 0:
            first_item = data[0]
            if isinstance(first_item, dict):
                return {
                    "change_1h": safe_float(safe_get(first_item, "price_change_percent_1h")),
                    "change_4h": safe_float(safe_get(first_item, "price_change_percent_4h")),
                    "change_24h": safe_float(safe_get(first_item, "price_change_percent_24h"))
                }
        
        return {"change_1h": 0.0, "change_4h": 0.0, "change_24h": 0.0}
    
    def _extract_oi_data(self, market_data: Dict, oi_exchange_data: Dict) -> Dict[str, Any]:
        """Extract open interest data"""
        # Try to get OI from market data first
        if market_data and market_data.get("success"):
            data = safe_get(market_data, "data", [])
            if data:
                # Find matching symbol in list
                for item in data:
                    if isinstance(item, dict) and safe_get(item, "symbol") == safe_get(market_data, "symbol", ""):
                        oi_value = safe_float(safe_get(item, "open_interest_usd"))
                        if oi_value > 0:
                            return {
                                "total_oi": oi_value,
                                "oi_change": None,
                                "oi_change_pct": None,
                                "exchange_breakdown": {}
                            }
        
        # Fallback to exchange breakdown data
        if oi_exchange_data and oi_exchange_data.get("success"):
            data = safe_get(oi_exchange_data, "data", [])
            if data:
                total_oi = sum(safe_float(item.get("openInterestSum", 0)) for item in data if isinstance(item, dict))
                return {
                    "total_oi": total_oi,
                    "oi_change": None,
                    "oi_change_pct": None,
                    "exchange_breakdown": {
                        item.get("exchangeName", "Unknown"): safe_float(item.get("openInterestSum", 0))
                        for item in data if isinstance(item, dict)
                    }
                }
        
        return {"total_oi": 0.0, "oi_change": None, "oi_change_pct": None, "exchange_breakdown": {}}
    
    def _extract_volume_data(self, market_data: Dict) -> Dict[str, Any]:
        """Extract volume data"""
        if not market_data or not market_data.get("success"):
            return {"volume_24h": 0.0, "buy_volume_24h": 0.0, "sell_volume_24h": 0.0}
        
        data = safe_get(market_data, "data", [])
        if not data:
            return {"volume_24h": 0.0, "buy_volume_24h": 0.0, "sell_volume_24h": 0.0}
        
        # Find matching symbol in list
        for item in data:
            if isinstance(item, dict) and safe_get(item, "symbol") == safe_get(market_data, "symbol", ""):
                buy_vol = safe_float(safe_get(item, "long_volume_usd_24h"))
                sell_vol = safe_float(safe_get(item, "short_volume_usd_24h"))
                total_vol = buy_vol + sell_vol
                return {
                    "volume_24h": total_vol,
                    "buy_volume_24h": buy_vol,
                    "sell_volume_24h": sell_vol
                }
        
        # If no matching symbol, use first item
        if data and len(data) > 0:
            first_item = data[0]
            if isinstance(first_item, dict):
                buy_vol = safe_float(safe_get(first_item, "long_volume_usd_24h"))
                sell_vol = safe_float(safe_get(first_item, "short_volume_usd_24h"))
                total_vol = buy_vol + sell_vol
                return {
                    "volume_24h": total_vol,
                    "buy_volume_24h": buy_vol,
                    "sell_volume_24h": sell_vol
                }
        
        return {"volume_24h": 0.0, "buy_volume_24h": 0.0, "sell_volume_24h": 0.0}
    
    def _extract_funding_data(self, funding_data: Dict, funding_history_data: Dict) -> Dict[str, Any]:
        """Extract funding rate data"""
        if not funding_data or not funding_data.get("success"):
            return {"current_funding": 0.0, "funding_1h": 0.0, "funding_4h": 0.0, "funding_8h": 0.0}
        
        # Get aggregated funding rate
        if safe_get(funding_data, "data_type") == "multi_exchange_aggregated":
            current_funding = safe_float(safe_get(funding_data, "aggregated_rate", 0.0))
        else:
            # Fallback to single exchange
            current_funding = safe_float(safe_get(funding_data, "aggregated_rate", 0.0))
        
        # Try to get historical funding data
        funding_1h = current_funding
        funding_4h = current_funding
        funding_8h = current_funding
        
        if funding_history_data and funding_history_data.get("success"):
            data = safe_get(funding_history_data, "data", [])
            if data and isinstance(data, list) and len(data) > 0:
                # Get the most recent funding rates for different timeframes
                latest = data[0] if isinstance(data[0], dict) else {}
                funding_1h = safe_float(safe_get(latest, "fundingRate"))
                
                # Look for 4h and 8h data in history
                for item in data:
                    if isinstance(item, dict):
                        interval = safe_get(item, "interval", "")
                        if "4h" in interval.lower():
                            funding_4h = safe_float(safe_get(item, "fundingRate"))
                        elif "8h" in interval.lower():
                            funding_8h = safe_float(safe_get(item, "fundingRate"))
        
        return {
            "current_funding": current_funding,
            "funding_1h": funding_1h,
            "funding_4h": funding_4h,
            "funding_8h": funding_8h
        }
    
    def _extract_liquidation_data(self, liquidation_data: Dict) -> Dict[str, Any]:
        """Extract liquidation data"""
        if not liquidation_data or not liquidation_data.get("success"):
            return {
                "liquidations_24h": 0.0,
                "liquidations_1h": 0.0,
                "long_liq_24h": 0.0,
                "short_liq_24h": 0.0
            }
        
        data = safe_get(liquidation_data, "data", [])
        if not data:
            return {
                "liquidations_24h": 0.0,
                "liquidations_1h": 0.0,
                "long_liq_24h": 0.0,
                "short_liq_24h": 0.0
            }
        
        # Calculate liquidations from data
        total_liq_24h = 0.0
        long_liq_24h = 0.0
        short_liq_24h = 0.0
        liquidations_1h = 0.0
        
        for item in data:
            if isinstance(item, dict):
                amount_usd = safe_float(safe_get(item, "amountUsd", 0))
                side = safe_get(item, "side", "").lower()
                timeframe = safe_get(item, "timeFrame", "").lower()
                
                total_liq_24h += amount_usd
                
                if "long" in side:
                    long_liq_24h += amount_usd
                elif "short" in side:
                    short_liq_24h += amount_usd
                
                # Look for 1h data
                if "1h" in timeframe or "60m" in timeframe:
                    liquidations_1h += amount_usd
        
        return {
            "liquidations_24h": total_liq_24h,
            "liquidations_1h": liquidations_1h,
            "long_liq_24h": long_liq_24h,
            "short_liq_24h": short_liq_24h
        }
    
    def _extract_long_short_data(self, ls_data: Dict) -> Dict[str, Any]:
        """Extract long/short ratio data"""
        if not ls_data or not ls_data.get("success"):
            return {"long_short_ratio": 0.5, "long_pct": 50.0, "short_pct": 50.0}
        
        data = safe_get(ls_data, "data", [])
        if not data:
            return {"long_short_ratio": 0.5, "long_pct": 50.0, "short_pct": 50.0}
        
        # Get the most recent data
        if isinstance(data, list) and len(data) > 0:
            latest = data[0]
            if isinstance(latest, dict):
                long_account = safe_float(safe_get(latest, "longAccount"))
                short_account = safe_float(safe_get(latest, "shortAccount"))
                
                if long_account > 0 or short_account > 0:
                    total = long_account + short_account
                    long_pct = (long_account / total) * 100 if total > 0 else 50.0
                    short_pct = (short_account / total) * 100 if total > 0 else 50.0
                    ratio = long_account / short_account if short_account > 0 else 1.0
                    
                    return {
                        "long_short_ratio": ratio,
                        "long_pct": long_pct,
                        "short_pct": short_pct
                    }
        
        return {"long_short_ratio": 0.5, "long_pct": 50.0, "short_pct": 50.0}
    
    def _extract_taker_flow_data(self, taker_data: Dict) -> Dict[str, Any]:
        """Extract taker flow data"""
        if not taker_data or not taker_data.get("success"):
            return {
                "buy_sell_ratio_5m": 0.5,
                "buy_sell_ratio_15m": 0.5,
                "buy_sell_ratio_1h": 0.5,
                "buy_sell_ratio_4h": 0.5
            }
        
        timeframe_data = safe_get(taker_data, "timeframe_data", {})
        ratios = {}
        
        for tf in ["5m", "15m", "1h", "4h"]:
            tf_data = safe_get(timeframe_data, tf, {})
            if tf_data and tf_data.get("success"):
                data = safe_get(tf_data, "data", [])
                if data and isinstance(data, list) and len(data) > 0:
                    # Get the most recent data
                    latest = data[0]
                    if isinstance(latest, dict):
                        buy_volume = safe_float(safe_get(latest, "buyVol", safe_get(latest, "buyVolume", 0)))
                        sell_volume = safe_float(safe_get(latest, "sellVol", safe_get(latest, "sellVolume", 0)))
                        
                        if buy_volume > 0 or sell_volume > 0:
                            total_volume = buy_volume + sell_volume
                            buy_ratio = (buy_volume / total_volume) if total_volume > 0 else 0.5
                            ratios[f"buy_sell_ratio_{tf}"] = buy_ratio
                        else:
                            ratios[f"buy_sell_ratio_{tf}"] = 0.5
                    else:
                        ratios[f"buy_sell_ratio_{tf}"] = 0.5
                else:
                    ratios[f"buy_sell_ratio_{tf}"] = 0.5
            else:
                ratios[f"buy_sell_ratio_{tf}"] = 0.5
        
        return ratios
    
    def _extract_rsi_data(self, rsi_data: Dict) -> Dict[str, Any]:
        """Extract RSI data"""
        if not rsi_data:
            return {
                "rsi_5m": None,
                "rsi_15m": None,
                "rsi_1h": None,
                "rsi_4h": None
            }
        
        return {
            "rsi_5m": rsi_data.get("5m"),
            "rsi_15m": rsi_data.get("15m"),
            "rsi_1h": rsi_data.get("1h"),
            "rsi_4h": rsi_data.get("4h")
        }
    
    def _extract_levels_data(self, levels_data: Dict) -> Dict[str, Any]:
        """Extract support/resistance levels data"""
        if not levels_data:
            return {"support_levels": [], "resistance_levels": []}
        
        # Since support/resistance endpoint may not be available, return empty
        return {"support_levels": [], "resistance_levels": []}

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


# Global instance for use across the application
raw_data_service = RawDataService()
