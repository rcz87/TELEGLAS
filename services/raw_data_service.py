import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
from services.coinglass import coinglass_api
from config.settings import settings


class RawDataService:
    """Service for fetching and formatting raw market data from multiple endpoints"""
    
    def __init__(self):
        self.api = coinglass_api
        
    async def get_comprehensive_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch comprehensive market data from multiple endpoints
        Returns formatted data ready for Telegram display
        """
        try:
            async with self.api:
                # Fetch data from multiple endpoints concurrently
                tasks = [
                    self._get_price_data(symbol),
                    self._get_oi_data(symbol),
                    self._get_volume_data(symbol),
                    self._get_funding_data(symbol),
                    self._get_liquidation_data(symbol),
                    self._get_long_short_ratio_data(symbol),
                    self._get_taker_flow_data(symbol),
                    self._get_rsi_data(symbol),
                    self._get_cg_levels_data(symbol)
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                price_data = results[0] if not isinstance(results[0], Exception) else {}
                oi_data = results[1] if not isinstance(results[1], Exception) else {}
                volume_data = results[2] if not isinstance(results[2], Exception) else {}
                funding_data = results[3] if not isinstance(results[3], Exception) else {}
                liquidation_data = results[4] if not isinstance(results[4], Exception) else {}
                ls_ratio_data = results[5] if not isinstance(results[5], Exception) else {}
                taker_flow_data = results[6] if not isinstance(results[6], Exception) else {}
                rsi_data = results[7] if not isinstance(results[7], Exception) else {}
                cg_levels_data = results[8] if not isinstance(results[8], Exception) else {}
                
                # Format data
                formatted_data = self._format_market_data(
                    symbol=symbol,
                    price_data=price_data,
                    oi_data=oi_data,
                    volume_data=volume_data,
                    funding_data=funding_data,
                    liquidation_data=liquidation_data,
                    ls_ratio_data=ls_ratio_data,
                    taker_flow_data=taker_flow_data,
                    rsi_data=rsi_data,
                    cg_levels_data=cg_levels_data
                )
                
                return formatted_data
                
        except Exception as e:
            logger.error(f"Error fetching comprehensive data for {symbol}: {e}")
            return self._get_error_response(symbol, str(e))
    
    async def _get_price_data(self, symbol: str) -> Dict[str, Any]:
        """Get price and price change data"""
        try:
            # Get futures coin markets for price data
            markets_data = await self.api.get_futures_coins_markets(symbol)
            return markets_data
        except Exception as e:
            logger.error(f"Error getting price data for {symbol}: {e}")
            return {}
    
    async def _get_oi_data(self, symbol: str) -> Dict[str, Any]:
        """Get open interest data"""
        try:
            # Get OI by exchange list
            oi_data = await self.api.get_open_interest_exchange_list(symbol)
            return oi_data
        except Exception as e:
            logger.error(f"Error getting OI data for {symbol}: {e}")
            return {}
    
    async def _get_volume_data(self, symbol: str) -> Dict[str, Any]:
        """Get volume data"""
        try:
            # Get taker buy/sell volume for volume analysis - add required exchange_list parameter
            volume_data = await self.api.get_aggregated_taker_buy_sell_volume_history(
                symbol=symbol,
                interval="1h",
                exchange_list="Binance,Bybit,OKX"
            )
            return volume_data
        except Exception as e:
            logger.error(f"Error getting volume data for {symbol}: {e}")
            return {}
    
    async def _get_funding_data(self, symbol: str) -> Dict[str, Any]:
        """Get funding rate data"""
        try:
            # Get funding rate by exchange
            funding_data = await self.api.get_funding_rate_exchange_list(symbol)
            return funding_data
        except Exception as e:
            logger.error(f"Error getting funding data for {symbol}: {e}")
            return {}
    
    async def _get_liquidation_data(self, symbol: str) -> Dict[str, Any]:
        """Get liquidation data"""
        try:
            # Get liquidation data across exchanges
            liq_data = await self.api.get_liquidation_exchange_list(symbol)
            return liq_data
        except Exception as e:
            logger.error(f"Error getting liquidation data for {symbol}: {e}")
            return {}
    
    async def _get_long_short_ratio_data(self, symbol: str) -> Dict[str, Any]:
        """Get long/short ratio data"""
        try:
            # Get global L/S ratio (use Binance as default exchange)
            ls_data = await self.api.get_global_long_short_ratio(symbol, "Binance")
            return ls_data
        except Exception as e:
            logger.error(f"Error getting L/S ratio data for {symbol}: {e}")
            return {}
    
    async def _get_taker_flow_data(self, symbol: str) -> Dict[str, Any]:
        """Get taker flow data for multiple timeframes"""
        try:
            # Get aggregated taker flow data
            taker_data = await self.api.get_aggregated_taker_buy_sell_volume_history(symbol)
            return taker_data
        except Exception as e:
            logger.error(f"Error getting taker flow data for {symbol}: {e}")
            return {}
    
    async def _get_rsi_data(self, symbol: str) -> Dict[str, Any]:
        """Get RSI data"""
        try:
            # Get RSI list
            rsi_data = await self.api.get_rsi_list(symbol)
            return rsi_data
        except Exception as e:
            logger.error(f"Error getting RSI data for {symbol}: {e}")
            return {}
    
    async def _get_cg_levels_data(self, symbol: str) -> Dict[str, Any]:
        """Get CoinGlass levels (support/resistance)"""
        try:
            # For now, we'll use liquidation heatmap as proxy for levels
            # In a real implementation, this might be a specific CG levels endpoint
            heatmap_data = await self.api.get_liquidation_aggregated_map(symbol)
            return heatmap_data
        except Exception as e:
            logger.error(f"Error getting CG levels data for {symbol}: {e}")
            return {}
    
    def _format_market_data(
        self,
        symbol: str,
        price_data: Dict,
        oi_data: Dict,
        volume_data: Dict,
        funding_data: Dict,
        liquidation_data: Dict,
        ls_ratio_data: Dict,
        taker_flow_data: Dict,
        rsi_data: Dict,
        cg_levels_data: Dict
    ) -> Dict[str, Any]:
        """Format all market data into comprehensive response"""
        
        current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
        
        # Extract price information
        price_info = self._extract_price_info(price_data, symbol)
        
        # Extract OI information
        oi_info = self._extract_oi_info(oi_data)
        
        # Extract volume information
        volume_info = self._extract_volume_info(volume_data)
        
        # Extract funding information
        funding_info = self._extract_funding_info(funding_data)
        
        # Extract liquidation information
        liquidation_info = self._extract_liquidation_info(liquidation_data)
        
        # Extract L/S ratio information
        ls_ratio_info = self._extract_ls_ratio_info(ls_ratio_data)
        
        # Extract taker flow information
        taker_flow_info = self._extract_taker_flow_info(taker_flow_data)
        
        # Extract RSI information
        rsi_info = self._extract_rsi_info(rsi_data, symbol)
        
        # Extract CG levels information
        cg_levels_info = self._extract_cg_levels_info(cg_levels_data)
        
        return {
            "symbol": symbol,
            "timestamp": current_time,
            "general_info": price_info,
            "price_change": price_info.get("price_change", {}),
            "open_interest": oi_info,
            "volume": volume_info,
            "funding": funding_info,
            "liquidations": liquidation_info,
            "long_short_ratio": ls_ratio_info,
            "taker_flow": taker_flow_info,
            "rsi": rsi_info,
            "cg_levels": cg_levels_info
        }
    
    def _extract_price_info(self, price_data: Dict, symbol: str) -> Dict[str, Any]:
        """Extract price information from markets data"""
        if not price_data:
            return {
                "symbol": symbol,
                "timeframe": "1H",
                "last_price": 0.0,
                "mark_price": 0.0,
                "price_source": "coinglass_futures",
                "price_change": {
                    "1h": 0.0,
                    "4h": 0.0,
                    "24h": 0.0,
                    "high_24h": 0.0,
                    "low_24h": 0.0,
                    "high_7d": 0.0,
                    "low_7d": 0.0
                }
            }
        
        # Extract first item from data array (assuming single symbol data)
        if isinstance(price_data, list) and price_data:
            item = price_data[0]
            return {
                "symbol": item.get("symbol", symbol),
                "timeframe": "1H",
                "last_price": float(item.get("lastPrice", 0)),
                "mark_price": float(item.get("markPrice", 0)),
                "price_source": "coinglass_futures",
                "price_change": {
                    "1h": float(item.get("priceChange1h", 0)),
                    "4h": float(item.get("priceChange4h", 0)),
                    "24h": float(item.get("priceChange24h", 0)),
                    "high_24h": float(item.get("highPrice24h", 0)),
                    "low_24h": float(item.get("lowPrice24h", 0)),
                    "high_7d": float(item.get("highPrice7d", 0)),
                    "low_7d": float(item.get("lowPrice7d", 0))
                }
            }
        
        return {"symbol": symbol, "last_price": 0.0, "mark_price": 0.0}
    
    def _extract_oi_info(self, oi_data: Dict) -> Dict[str, Any]:
        """Extract open interest information"""
        if not oi_data:
            return {
                "total_oi": 0.0,
                "oi_1h": 0.0,
                "oi_24h": 0.0,
                "per_exchange": {
                    "Binance": 0.0,
                    "Bybit": 0.0,
                    "OKX": 0.0,
                    "Others": 0.0
                }
            }
        
        total_oi = 0.0
        per_exchange = {"Binance": 0.0, "Bybit": 0.0, "OKX": 0.0, "Others": 0.0}
        
        if isinstance(oi_data, list):
            for item in oi_data:
                exchange = item.get("exchange", "Others")
                oi_value = float(item.get("openInterest", 0))
                total_oi += oi_value
                
                if exchange in per_exchange:
                    per_exchange[exchange] = oi_value
                else:
                    per_exchange["Others"] += oi_value
        
        return {
            "total_oi": total_oi,
            "oi_1h": 0.0,  # Would need historical data for this
            "oi_24h": 0.0,  # Would need historical data for this
            "per_exchange": per_exchange
        }
    
    def _extract_volume_info(self, volume_data: Dict) -> Dict[str, Any]:
        """Extract volume information"""
        if not volume_data:
            return {
                "futures_24h": 0.0,
                "perp_24h": 0.0,
                "spot_24h": 0.0
            }
        
        # This is a simplified extraction - real implementation would parse volume data
        return {
            "futures_24h": 0.0,
            "perp_24h": 0.0,
            "spot_24h": 0.0
        }
    
    def _extract_funding_info(self, funding_data: Dict) -> Dict[str, Any]:
        """Extract funding rate information"""
        if not funding_data:
            return {
                "current_funding": 0.0,
                "next_funding": "00:00 UTC",
                "funding_history": []
            }
        
        if isinstance(funding_data, list) and funding_data:
            # Get most recent funding data
            latest = funding_data[0]
            current_rate = float(latest.get("fundingRate", 0))
            
            return {
                "current_funding": current_rate,
                "next_funding": "00:00 UTC",  # Would need to calculate next funding time
                "funding_history": funding_data[:5]  # Last 5 entries
            }
        
        return {"current_funding": 0.0, "next_funding": "00:00 UTC", "funding_history": []}
    
    def _extract_liquidation_info(self, liquidation_data: Dict) -> Dict[str, Any]:
        """Extract liquidation information"""
        if not liquidation_data:
            return {
                "total_24h": 0.0,
                "long_liq": 0.0,
                "short_liq": 0.0
            }
        
        total_liq = 0.0
        long_liq = 0.0
        short_liq = 0.0
        
        if isinstance(liquidation_data, list):
            for item in liquidation_data:
                total_liq += float(item.get("liquidation_usd_24h", 0))
                long_liq += float(item.get("long_liquidation_usd_24h", 0))
                short_liq += float(item.get("short_liquidation_usd_24h", 0))
        
        return {
            "total_24h": total_liq,
            "long_liq": long_liq,
            "short_liq": short_liq
        }
    
    def _extract_ls_ratio_info(self, ls_ratio_data: Dict) -> Dict[str, Any]:
        """Extract long/short ratio information"""
        if not ls_ratio_data:
            return {
                "account_ratio_global": 1.0,
                "position_ratio_global": 1.0,
                "by_exchange": {
                    "Binance": 1.0,
                    "Bybit": 1.0,
                    "OKX": 1.0
                }
            }
        
        # This is simplified - real implementation would parse actual L/S ratio data
        return {
            "account_ratio_global": 1.0,
            "position_ratio_global": 1.0,
            "by_exchange": {
                "Binance": 1.0,
                "Bybit": 1.0,
                "OKX": 1.0
            }
        }
    
    def _extract_taker_flow_info(self, taker_flow_data: Dict) -> Dict[str, Any]:
        """Extract taker flow information for multiple timeframes"""
        if not taker_flow_data:
            return {
                "5m": {"buy": 0.0, "sell": 0.0, "net": 0.0},
                "15m": {"buy": 0.0, "sell": 0.0, "net": 0.0},
                "1h": {"buy": 0.0, "sell": 0.0, "net": 0.0},
                "4h": {"buy": 0.0, "sell": 0.0, "net": 0.0}
            }
        
        # This is simplified - real implementation would parse taker flow data by timeframe
        return {
            "5m": {"buy": 0.0, "sell": 0.0, "net": 0.0},
            "15m": {"buy": 0.0, "sell": 0.0, "net": 0.0},
            "1h": {"buy": 0.0, "sell": 0.0, "net": 0.0},
            "4h": {"buy": 0.0, "sell": 0.0, "net": 0.0}
        }
    
    def _extract_rsi_info(self, rsi_data: Dict, symbol: str) -> Dict[str, Any]:
        """Extract RSI information for multiple timeframes"""
        if not rsi_data:
            return {
                "5m": 0.0,
                "15m": 0.0,
                "1h": 0.0,
                "4h": 0.0
            }
        
        if isinstance(rsi_data, list):
            for item in rsi_data:
                if item.get("symbol") == symbol:
                    return {
                        "5m": float(item.get("rsi5m", 0)),
                        "15m": float(item.get("rsi15m", 0)),
                        "1h": float(item.get("rsi1h", 0)),
                        "4h": float(item.get("rsi4h", 0))
                    }
        
        return {"5m": 0.0, "15m": 0.0, "1h": 0.0, "4h": 0.0}
    
    def _extract_cg_levels_info(self, cg_levels_data: Dict) -> Dict[str, Any]:
        """Extract CoinGlass levels (support/resistance)"""
        if not cg_levels_data:
            return {
                "support": [0.0, 0.0, 0.0],
                "resistance": [0.0, 0.0, 0.0]
            }
        
        # This is simplified - real implementation would parse actual CG levels
        return {
            "support": [0.0, 0.0, 0.0],
            "resistance": [0.0, 0.0, 0.0]
        }
    
    def _get_error_response(self, symbol: str, error_msg: str) -> Dict[str, Any]:
        """Return error response"""
        return {
            "symbol": symbol,
            "error": error_msg,
            "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
        }
    
    def format_for_telegram(self, data: Dict[str, Any]) -> str:
        """Format comprehensive data for Telegram display"""
        if "error" in data:
            return f"❌ Error fetching data for {data['symbol']}: {data['error']}"
        
        general = data.get("general_info", {})
        price_change = data.get("price_change", {})
        oi = data.get("open_interest", {})
        volume = data.get("volume", {})
        funding = data.get("funding", {})
        liquidations = data.get("liquidations", {})
        ls_ratio = data.get("long_short_ratio", {})
        taker_flow = data.get("taker_flow", {})
        rsi = data.get("rsi", {})
        cg_levels = data.get("cg_levels", {})
        
        # Prepare CG levels strings separately to avoid f-string issues
        support_levels = cg_levels.get('support', [0, 0, 0])
        resistance_levels = cg_levels.get('resistance', [0, 0, 0])
        support_str = ', '.join([f'{x:.2f}' for x in support_levels])
        resistance_str = ', '.join([f'{x:.2f}' for x in resistance_levels])
        
        # Format message
        message = f"""📊 **RAW DATA - {data['symbol'].upper()} - REAL PRICE MULTI-TF**

**Info Umum**
Symbol : {data['symbol']}
Timeframe : {general.get('timeframe', '1H')}
Timestamp : {data['timestamp']}
Last Price: {general.get('last_price', 0):.2f}
Mark Price: {general.get('mark_price', 0):.2f}
Price Source: {general.get('price_source', 'coinglass_futures')}

**Price Change**
1H : {price_change.get('1h', 0):+.2f}%
4H : {price_change.get('4h', 0):+.2f}%
24H : {price_change.get('24h', 0):+.2f}%
High/Low 24H: ${price_change.get('low_24h', 0):.4f} / ${price_change.get('high_24h', 0):.4f}
High/Low 7D : ${price_change.get('low_7d', 0):.4f} / ${price_change.get('high_7d', 0):.4f}

**Open Interest**
Total OI : ${oi.get('total_oi', 0):.2f}B
OI 1H : {oi.get('oi_1h', 0):+.1f}%
OI 24H : {oi.get('oi_24h', 0):+.1f}%

**OI per Exchange**
Binance : ${oi.get('per_exchange', {}).get('Binance', 0):.2f}B
Bybit : ${oi.get('per_exchange', {}).get('Bybit', 0):.2f}B
OKX : ${oi.get('per_exchange', {}).get('OKX', 0):.2f}B
Others : ${oi.get('per_exchange', {}).get('Others', 0):.2f}B

**Volume**
Futures 24H: ${volume.get('futures_24h', 0):.2f}B
Perp 24H : ${volume.get('perp_24h', 0):.2f}B
Spot 24H : ${volume.get('spot_24h', 0):.2f}B

**Funding**
Current Funding: {funding.get('current_funding', 0):+.4f}%
Next Funding : {funding.get('next_funding', '00:00 UTC')}
Funding History:
No history available

**Liquidations**
Total 24H : ${liquidations.get('total_24h', 0):.2f}M
Long Liq : ${liquidations.get('long_liq', 0):.2f}M
Short Liq : ${liquidations.get('short_liq', 0):.2f}M

**Long/Short Ratio**
Account Ratio (Global) : {ls_ratio.get('account_ratio_global', 1.00):.2f}
Position Ratio (Global): {ls_ratio.get('position_ratio_global', 1.00):.2f}
By Exchange:
Binance: {ls_ratio.get('by_exchange', {}).get('Binance', 1.00):.2f}
Bybit : {ls_ratio.get('by_exchange', {}).get('Bybit', 1.00):.2f}
OKX : {ls_ratio.get('by_exchange', {}).get('OKX', 1.00):.2f}

**Taker Flow Multi-Timeframe (CVD Proxy)**
5M: Buy ${taker_flow.get('5m', {}).get('buy', 0):.0f}M | Sell ${taker_flow.get('5m', {}).get('sell', 0):.0f}M | Net ${taker_flow.get('5m', {}).get('net', 0):+.0f}M
15M: Buy ${taker_flow.get('15m', {}).get('buy', 0):.0f}M | Sell ${taker_flow.get('15m', {}).get('sell', 0):.0f}M | Net ${taker_flow.get('15m', {}).get('net', 0):+.0f}M
1H: Buy ${taker_flow.get('1h', {}).get('buy', 0):.0f}M | Sell ${taker_flow.get('1h', {}).get('sell', 0):.0f}M | Net ${taker_flow.get('1h', {}).get('net', 0):+.0f}M
4H: Buy ${taker_flow.get('4h', {}).get('buy', 0):.0f}M | Sell ${taker_flow.get('4h', {}).get('sell', 0):.0f}M | Net ${taker_flow.get('4h', {}).get('net', 0):+.0f}M

**RSI Multi-Timeframe (14)**
5M : {rsi.get('5m', 0):.2f}
15M: {rsi.get('15m', 0):.2f}
1H : {rsi.get('1h', 0):.2f}
4H : {rsi.get('4h', 0):.2f}

**CG Levels**
Support : ${support_str}
Resistance: ${resistance_str}"""
        
        return message


# Global instance
raw_data_service = RawDataService()
