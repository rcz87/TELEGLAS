#!/usr/bin/env python3
"""
Market Data Core Service
Shared service for market data operations used by both Telegram bot and GPT API
Provides reusable functions for raw, whale, liquidation, and orderbook data
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from loguru import logger

# Import existing services
from services.raw_data_service import RawDataService
from services.whale_watcher import WhaleWatcher
from services.liquidation_monitor import LiquidationMonitor
from services.coinglass_api import coinglass_api


class MarketDataCore:
    """
    Core service for market data operations
    Provides reusable functions that can be used by both Telegram handlers and GPT API
    """

    def __init__(self):
        # Initialize existing service instances
        self.raw_data_service = RawDataService()
        self.whale_watcher = WhaleWatcher()
        self.liquidation_monitor = LiquidationMonitor()
        self.api = coinglass_api

    # RAW DATA METHODS

    async def get_raw(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive raw market data for a symbol
        Same logic as /raw command but returns raw data instead of formatted text
        """
        try:
            logger.info(f"[MARKET_CORE] Getting raw data for {symbol}")
            
            # Use existing raw data service
            raw_data = await self.raw_data_service.get_comprehensive_market_data(symbol)
            
            if not raw_data:
                return {
                    "success": False,
                    "error": f"No raw data available for {symbol}",
                    "symbol": symbol,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            return {
                "success": True,
                "data": raw_data,
                "symbol": symbol,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"[MARKET_CORE] Error getting raw data for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    # WHALE DATA METHODS

    async def get_whale(self, symbol: str = None, limit: int = 10) -> Dict[str, Any]:
        """
        Get whale transaction data
        Same logic as /whale command but returns raw data instead of formatted text
        """
        try:
            logger.info(f"[MARKET_CORE] Getting whale data for {symbol or 'all symbols'}")
            
            # Get recent whale activity
            whale_activity = await self.whale_watcher.get_recent_whale_activity(symbol, limit)
            
            if not whale_activity:
                return {
                    "success": False,
                    "error": f"No whale data available for {symbol or 'any symbol'}",
                    "symbol": symbol,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            return {
                "success": True,
                "data": whale_activity,
                "symbol": symbol,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"[MARKET_CORE] Error getting whale data for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def get_whale_radar(self, user_threshold: float = None) -> Dict[str, Any]:
        """
        Get enhanced whale radar data
        Same logic as whale radar functionality
        """
        try:
            logger.info("[MARKET_CORE] Getting whale radar data")
            
            # Get enhanced whale radar data
            radar_data = await self.whale_watcher.get_enhanced_whale_radar_data(user_threshold)
            
            if not radar_data:
                return {
                    "success": False,
                    "error": "No whale radar data available",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            return {
                "success": True,
                "data": radar_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"[MARKET_CORE] Error getting whale radar data: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    # LIQUIDATION DATA METHODS

    async def get_liq(self, symbol: str) -> Dict[str, Any]:
        """
        Get liquidation data for a symbol
        Same logic as /liq command but returns raw data instead of formatted text
        """
        try:
            logger.info(f"[MARKET_CORE] Getting liquidation data for {symbol}")
            
            # Get symbol liquidation summary
            liquidation_summary = await self.liquidation_monitor.get_symbol_liquidation_summary(symbol)
            
            if not liquidation_summary:
                return {
                    "success": False,
                    "error": f"No liquidation data available for {symbol}",
                    "symbol": symbol,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            return {
                "success": True,
                "data": liquidation_summary,
                "symbol": symbol,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"[MARKET_CORE] Error getting liquidation data for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    # ORDERBOOK DATA METHODS

    async def get_raw_orderbook(self, symbol: str) -> Dict[str, Any]:
        """
        Get raw orderbook data for a symbol
        Same logic as /raw_orderbook command but returns raw data instead of formatted text
        """
        try:
            logger.info(f"[MARKET_CORE] Getting orderbook data for {symbol}")
            
            # Use raw data service to get orderbook snapshot
            orderbook_data = await self.raw_data_service.get_orderbook_snapshot(symbol)
            
            if not orderbook_data:
                return {
                    "success": False,
                    "error": f"No orderbook data available for {symbol}",
                    "symbol": symbol,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            return {
                "success": True,
                "data": orderbook_data,
                "symbol": symbol,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"[MARKET_CORE] Error getting orderbook data for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    # UTILITY METHODS

    async def resolve_symbol(self, symbol: str) -> str:
        """
        Resolve symbol to proper format
        """
        try:
            resolved = await self.api.resolve_symbol(symbol)
            return resolved if resolved else symbol.upper()
        except Exception as e:
            logger.error(f"[MARKET_CORE] Error resolving symbol {symbol}: {e}")
            return symbol.upper()

    async def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if symbol is supported
        """
        try:
            resolved_symbol = await self.resolve_symbol(symbol)
            # Try to get basic market data to validate
            market_data = await self.raw_data_service.get_market(resolved_symbol)
            return market_data.get("success", False) if market_data else False
        except Exception as e:
            logger.error(f"[MARKET_CORE] Error validating symbol {symbol}: {e}")
            return False

    async def get_supported_symbols(self) -> List[str]:
        """
        Get list of commonly supported symbols
        """
        # Return common crypto symbols that are usually supported
        return [
            "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", 
            "DOT", "MATIC", "LINK", "UNI", "LTC", "ATOM", "FIL", "ETC",
            "XLM", "VET", "THETA", "ICP", "TRX", "EOS", "AAVE", "MKR"
        ]

    # HEALTH CHECK METHOD

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for market data services
        """
        try:
            health_status = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "services": {},
                "overall_status": "healthy"
            }
            
            # Check raw data service
            try:
                test_raw = await self.get_raw("BTC")
                health_status["services"]["raw_data"] = {
                    "status": "healthy" if test_raw.get("success") else "unhealthy",
                    "last_check": datetime.now(timezone.utc).isoformat()
                }
            except Exception as e:
                health_status["services"]["raw_data"] = {
                    "status": "error",
                    "error": str(e),
                    "last_check": datetime.now(timezone.utc).isoformat()
                }
            
            # Check whale service
            try:
                test_whale = await self.get_whale("BTC", 1)
                health_status["services"]["whale_data"] = {
                    "status": "healthy" if test_whale.get("success") else "unhealthy",
                    "last_check": datetime.now(timezone.utc).isoformat()
                }
            except Exception as e:
                health_status["services"]["whale_data"] = {
                    "status": "error",
                    "error": str(e),
                    "last_check": datetime.now(timezone.utc).isoformat()
                }
            
            # Check liquidation service
            try:
                test_liq = await self.get_liq("BTC")
                health_status["services"]["liquidation_data"] = {
                    "status": "healthy" if test_liq.get("success") else "unhealthy",
                    "last_check": datetime.now(timezone.utc).isoformat()
                }
            except Exception as e:
                health_status["services"]["liquidation_data"] = {
                    "status": "error",
                    "error": str(e),
                    "last_check": datetime.now(timezone.utc).isoformat()
                }
            
            # Check orderbook service
            try:
                test_orderbook = await self.get_raw_orderbook("BTC")
                health_status["services"]["orderbook_data"] = {
                    "status": "healthy" if test_orderbook.get("success") else "unhealthy",
                    "last_check": datetime.now(timezone.utc).isoformat()
                }
            except Exception as e:
                health_status["services"]["orderbook_data"] = {
                    "status": "error",
                    "error": str(e),
                    "last_check": datetime.now(timezone.utc).isoformat()
                }
            
            # Determine overall status
            service_statuses = [service.get("status") for service in health_status["services"].values()]
            if any(status == "error" for status in service_statuses):
                health_status["overall_status"] = "error"
            elif any(status == "unhealthy" for status in service_statuses):
                health_status["overall_status"] = "degraded"
            
            return health_status
            
        except Exception as e:
            logger.error(f"[MARKET_CORE] Error in health check: {e}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "overall_status": "error",
                "error": str(e)
            }


# Global instance for use across the application
market_data_core = MarketDataCore()
