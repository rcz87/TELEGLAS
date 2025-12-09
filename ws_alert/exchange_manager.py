"""
Exchange Manager - Multi-Exchange Support

Manages multiple cryptocurrency exchanges and provides unified interface
for data aggregation and cross-exchange analysis.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ExchangeType(Enum):
    """Supported exchange types"""
    BINANCE = "binance"
    COINGLASS = "coinglass"
    OKEX = "okex"
    HUOBI = "huobi"
    BYBIT = "bybit"
    KRAKEN = "kraken"

class ExchangeStatus(Enum):
    """Exchange connection status"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"

@dataclass
class ExchangeConfig:
    """Exchange configuration"""
    exchange_id: str
    exchange_type: ExchangeType
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    passphrase: Optional[str] = None  # For exchanges like OKEx
    base_url: Optional[str] = None
    websocket_url: Optional[str] = None
    rate_limit: int = 100  # requests per minute
    timeout: int = 30
    retry_count: int = 3
    retry_delay: int = 5
    enabled: bool = True
    priority: int = 1  # Lower number = higher priority
    features: List[str] = field(default_factory=list)  # Supported features

@dataclass
class ExchangeInfo:
    """Exchange runtime information"""
    exchange_id: str
    status: ExchangeStatus
    last_ping: float
    latency: float
    error_count: int
    success_count: int
    last_error: Optional[str] = None
    uptime_percentage: float = 0.0

@dataclass
class CrossExchangeData:
    """Cross-exchange aggregated data"""
    symbol: str
    timestamp: float
    exchanges_data: Dict[str, Dict[str, Any]]
    aggregated_price: float
    price_variance: float
    volume_total: float
    liquidity_score: float
    arbitrage_opportunities: List[Dict[str, Any]]

class ExchangeConnector:
    """Base class for exchange connectors"""
    
    def __init__(self, config: ExchangeConfig):
        self.config = config
        self.exchange_id = config.exchange_id
        self.logger = logging.getLogger(f"{__name__}.{self.exchange_id}")
        
    async def connect(self) -> bool:
        """Connect to exchange"""
        raise NotImplementedError
        
    async def disconnect(self) -> None:
        """Disconnect from exchange"""
        raise NotImplementedError
        
    async def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data"""
        raise NotImplementedError
        
    async def get_orderbook(self, symbol: str, limit: int = 100) -> Optional[Dict[str, Any]]:
        """Get orderbook data"""
        raise NotImplementedError
        
    async def get_liquidations(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get liquidation data"""
        raise NotImplementedError
        
    async def get_whale_activity(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get whale activity data"""
        raise NotImplementedError
        
    async def ping(self) -> float:
        """Ping exchange to check latency"""
        raise NotImplementedError

class BinanceConnector(ExchangeConnector):
    """Binance exchange connector"""
    
    def __init__(self, config: ExchangeConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://fapi.binance.com"
        self.websocket_url = config.websocket_url or "wss://fstream.binance.com/ws"
        
    async def connect(self) -> bool:
        """Connect to Binance"""
        try:
            # Test connectivity
            await self.ping()
            self.logger.info(f"Connected to Binance (exchange_id: {self.exchange_id})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Binance: {e}")
            return False
            
    async def disconnect(self) -> None:
        """Disconnect from Binance"""
        self.logger.info(f"Disconnected from Binance (exchange_id: {self.exchange_id})")
        
    async def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data from Binance"""
        try:
            # Mock implementation - would use actual API
            return {
                'symbol': symbol,
                'price': 50000.0 + (hash(symbol) % 10000),
                'volume': 1000000.0 + (hash(symbol) % 500000),
                'timestamp': time.time(),
                'exchange': self.exchange_id
            }
        except Exception as e:
            self.logger.error(f"Error getting ticker from Binance: {e}")
            return None
            
    async def get_orderbook(self, symbol: str, limit: int = 100) -> Optional[Dict[str, Any]]:
        """Get orderbook from Binance"""
        try:
            # Mock implementation
            return {
                'symbol': symbol,
                'bids': [[50000.0 - i*10, 100 + i] for i in range(10)],
                'asks': [[50010.0 + i*10, 100 + i] for i in range(10)],
                'timestamp': time.time(),
                'exchange': self.exchange_id
            }
        except Exception as e:
            self.logger.error(f"Error getting orderbook from Binance: {e}")
            return None
            
    async def get_liquidations(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get liquidations from Binance"""
        try:
            # Mock implementation
            return [
                {
                    'symbol': symbol or 'BTCUSDT',
                    'side': 'SELL',
                    'quantity': 100.0,
                    'price': 49500.0,
                    'timestamp': time.time(),
                    'exchange': self.exchange_id
                }
            ]
        except Exception as e:
            self.logger.error(f"Error getting liquidations from Binance: {e}")
            return []
            
    async def get_whale_activity(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get whale activity from Binance"""
        try:
            # Mock implementation
            return [
                {
                    'symbol': symbol or 'BTCUSDT',
                    'side': 'BUY',
                    'quantity': 500.0,
                    'price': 50100.0,
                    'timestamp': time.time(),
                    'exchange': self.exchange_id
                }
            ]
        except Exception as e:
            self.logger.error(f"Error getting whale activity from Binance: {e}")
            return []
            
    async def ping(self) -> float:
        """Ping Binance"""
        start_time = time.time()
        try:
            # Mock ping - would use actual API
            await asyncio.sleep(0.1)  # Simulate network latency
            latency = (time.time() - start_time) * 1000
            return latency
        except Exception as e:
            self.logger.error(f"Error pinging Binance: {e}")
            return -1

class CoinGlassConnector(ExchangeConnector):
    """CoinGlass exchange connector"""
    
    def __init__(self, config: ExchangeConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://www.coinglass.com"
        self.api_key = config.api_key
        
    async def connect(self) -> bool:
        """Connect to CoinGlass"""
        try:
            await self.ping()
            self.logger.info(f"Connected to CoinGlass (exchange_id: {self.exchange_id})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to CoinGlass: {e}")
            return False
            
    async def disconnect(self) -> None:
        """Disconnect from CoinGlass"""
        self.logger.info(f"Disconnected from CoinGlass (exchange_id: {self.exchange_id})")
        
    async def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data from CoinGlass"""
        try:
            # Mock implementation with different pricing
            base_price = 50000.0 + (hash(symbol) % 10000)
            return {
                'symbol': symbol,
                'price': base_price * 1.001,  # Slight price difference
                'volume': 1200000.0 + (hash(symbol) % 600000),
                'timestamp': time.time(),
                'exchange': self.exchange_id
            }
        except Exception as e:
            self.logger.error(f"Error getting ticker from CoinGlass: {e}")
            return None
            
    async def get_orderbook(self, symbol: str, limit: int = 100) -> Optional[Dict[str, Any]]:
        """Get orderbook from CoinGlass"""
        try:
            base_price = 50000.0 + (hash(symbol) % 10000)
            return {
                'symbol': symbol,
                'bids': [[base_price - i*10, 120 + i] for i in range(10)],
                'asks': [[base_price + 10 + i*10, 120 + i] for i in range(10)],
                'timestamp': time.time(),
                'exchange': self.exchange_id
            }
        except Exception as e:
            self.logger.error(f"Error getting orderbook from CoinGlass: {e}")
            return None
            
    async def get_liquidations(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get liquidations from CoinGlass"""
        try:
            return [
                {
                    'symbol': symbol or 'BTCUSDT',
                    'side': 'BUY',
                    'quantity': 150.0,
                    'price': 50500.0,
                    'timestamp': time.time(),
                    'exchange': self.exchange_id
                }
            ]
        except Exception as e:
            self.logger.error(f"Error getting liquidations from CoinGlass: {e}")
            return []
            
    async def get_whale_activity(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get whale activity from CoinGlass"""
        try:
            return [
                {
                    'symbol': symbol or 'BTCUSDT',
                    'side': 'SELL',
                    'quantity': 600.0,
                    'price': 49900.0,
                    'timestamp': time.time(),
                    'exchange': self.exchange_id
                }
            ]
        except Exception as e:
            self.logger.error(f"Error getting whale activity from CoinGlass: {e}")
            return []
            
    async def ping(self) -> float:
        """Ping CoinGlass"""
        start_time = time.time()
        try:
            await asyncio.sleep(0.15)  # Simulate slightly higher latency
            latency = (time.time() - start_time) * 1000
            return latency
        except Exception as e:
            self.logger.error(f"Error pinging CoinGlass: {e}")
            return -1

class ExchangeManager:
    """Main exchange manager for multi-exchange support"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.exchanges: Dict[str, ExchangeConnector] = {}
        self.exchange_configs: Dict[str, ExchangeConfig] = {}
        self.exchange_info: Dict[str, ExchangeInfo] = {}
        self.running = False
        
    def add_exchange(self, config: ExchangeConfig) -> bool:
        """Add an exchange to the manager"""
        try:
            # Create appropriate connector based on exchange type
            if config.exchange_type == ExchangeType.BINANCE:
                connector = BinanceConnector(config)
            elif config.exchange_type == ExchangeType.COINGLASS:
                connector = CoinGlassConnector(config)
            else:
                self.logger.error(f"Unsupported exchange type: {config.exchange_type}")
                return False
                
            self.exchanges[config.exchange_id] = connector
            self.exchange_configs[config.exchange_id] = config
            self.exchange_info[config.exchange_id] = ExchangeInfo(
                exchange_id=config.exchange_id,
                status=ExchangeStatus.OFFLINE,
                last_ping=0,
                latency=0,
                error_count=0,
                success_count=0
            )
            
            self.logger.info(f"Added exchange {config.exchange_id} ({config.exchange_type.value})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding exchange {config.exchange_id}: {e}")
            return False
            
    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all enabled exchanges"""
        results = {}
        
        for exchange_id, config in self.exchange_configs.items():
            if not config.enabled:
                self.logger.info(f"Skipping disabled exchange {exchange_id}")
                continue
                
            connector = self.exchanges.get(exchange_id)
            if connector:
                success = await connector.connect()
                results[exchange_id] = success
                
                # Update exchange info
                info = self.exchange_info[exchange_id]
                info.status = ExchangeStatus.ONLINE if success else ExchangeStatus.OFFLINE
                info.last_ping = time.time()
                
        return results
        
    async def disconnect_all(self) -> None:
        """Disconnect from all exchanges"""
        for exchange_id, connector in self.exchanges.items():
            try:
                await connector.disconnect()
                self.exchange_info[exchange_id].status = ExchangeStatus.OFFLINE
            except Exception as e:
                self.logger.error(f"Error disconnecting from {exchange_id}: {e}")
                
    async def get_cross_exchange_ticker(self, symbol: str) -> CrossExchangeData:
        """Get aggregated ticker data from multiple exchanges"""
        exchanges_data = {}
        prices = []
        volumes = []
        
        # Get data from all online exchanges
        tasks = []
        for exchange_id, connector in self.exchanges.items():
            if self.exchange_info[exchange_id].status == ExchangeStatus.ONLINE:
                tasks.append(self._get_ticker_safe(exchange_id, connector, symbol))
                
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                exchange_id = list(self.exchanges.keys())[i]
                if isinstance(result, dict) and result:
                    exchanges_data[exchange_id] = result
                    prices.append(result['price'])
                    volumes.append(result['volume'])
                elif isinstance(result, Exception):
                    self.logger.error(f"Error getting ticker from {exchange_id}: {result}")
                    
        # Calculate aggregated metrics
        aggregated_price = sum(prices) / len(prices) if prices else 0
        price_variance = max(prices) - min(prices) if len(prices) > 1 else 0
        volume_total = sum(volumes)
        
        # Calculate liquidity score based on volume and price variance
        liquidity_score = min(100, (volume_total / 10000) * (1 - (price_variance / aggregated_price)) * 100) if aggregated_price > 0 else 0
        
        # Find arbitrage opportunities
        arbitrage_opportunities = self._find_arbitrage_opportunities(exchanges_data)
        
        return CrossExchangeData(
            symbol=symbol,
            timestamp=time.time(),
            exchanges_data=exchanges_data,
            aggregated_price=aggregated_price,
            price_variance=price_variance,
            volume_total=volume_total,
            liquidity_score=liquidity_score,
            arbitrage_opportunities=arbitrage_opportunities
        )
        
    async def _get_ticker_safe(self, exchange_id: str, connector: ExchangeConnector, symbol: str) -> Optional[Dict[str, Any]]:
        """Safely get ticker data with error handling"""
        try:
            data = await connector.get_ticker(symbol)
            if data:
                self.exchange_info[exchange_id].success_count += 1
            else:
                self.exchange_info[exchange_id].error_count += 1
            return data
        except Exception as e:
            self.exchange_info[exchange_id].error_count += 1
            self.exchange_info[exchange_id].last_error = str(e)
            return None
            
    def _find_arbitrage_opportunities(self, exchanges_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find arbitrage opportunities between exchanges"""
        opportunities = []
        
        if len(exchanges_data) < 2:
            return opportunities
            
        exchange_list = list(exchanges_data.keys())
        
        for i in range(len(exchange_list)):
            for j in range(i + 1, len(exchange_list)):
                exchange1 = exchange_list[i]
                exchange2 = exchange_list[j]
                
                price1 = exchanges_data[exchange1]['price']
                price2 = exchanges_data[exchange2]['price']
                
                if price1 > 0 and price2 > 0:
                    price_diff = abs(price1 - price2)
                    price_diff_pct = (price_diff / min(price1, price2)) * 100
                    
                    if price_diff_pct > 0.1:  # 0.1% threshold
                        opportunities.append({
                            'exchange_low': exchange2 if price2 < price1 else exchange1,
                            'exchange_high': exchange1 if price1 > price2 else exchange2,
                            'price_low': min(price1, price2),
                            'price_high': max(price1, price2),
                            'price_difference': price_diff,
                            'price_difference_pct': price_diff_pct,
                            'potential_profit': price_diff_pct * 0.8  # Assuming 0.8% fees
                        })
                        
        return opportunities
        
    async def get_cross_exchange_liquidations(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get liquidation data from multiple exchanges"""
        all_liquidations = []
        
        tasks = []
        for exchange_id, connector in self.exchanges.items():
            if self.exchange_info[exchange_id].status == ExchangeStatus.ONLINE:
                tasks.append(self._get_liquidations_safe(exchange_id, connector, symbol))
                
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_liquidations.extend(result)
                    
        # Sort by timestamp (most recent first)
        all_liquidations.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return all_liquidations
        
    async def _get_liquidations_safe(self, exchange_id: str, connector: ExchangeConnector, symbol: str) -> List[Dict[str, Any]]:
        """Safely get liquidation data with error handling"""
        try:
            data = await connector.get_liquidations(symbol)
            if data:
                self.exchange_info[exchange_id].success_count += 1
            else:
                self.exchange_info[exchange_id].error_count += 1
            return data or []
        except Exception as e:
            self.exchange_info[exchange_id].error_count += 1
            self.exchange_info[exchange_id].last_error = str(e)
            return []
            
    async def get_cross_exchange_whale_activity(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get whale activity from multiple exchanges"""
        all_whale_activity = []
        
        tasks = []
        for exchange_id, connector in self.exchanges.items():
            if self.exchange_info[exchange_id].status == ExchangeStatus.ONLINE:
                tasks.append(self._get_whale_activity_safe(exchange_id, connector, symbol))
                
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_whale_activity.extend(result)
                    
        # Sort by timestamp (most recent first)
        all_whale_activity.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return all_whale_activity
        
    async def _get_whale_activity_safe(self, exchange_id: str, connector: ExchangeConnector, symbol: str) -> List[Dict[str, Any]]:
        """Safely get whale activity with error handling"""
        try:
            data = await connector.get_whale_activity(symbol)
            if data:
                self.exchange_info[exchange_id].success_count += 1
            else:
                self.exchange_info[exchange_id].error_count += 1
            return data or []
        except Exception as e:
            self.exchange_info[exchange_id].error_count += 1
            self.exchange_info[exchange_id].last_error = str(e)
            return []
            
    async def health_check(self) -> Dict[str, Dict[str, Any]]:
        """Perform health check on all exchanges"""
        health_status = {}
        
        for exchange_id, connector in self.exchanges.items():
            try:
                latency = await connector.ping()
                info = self.exchange_info[exchange_id]
                info.last_ping = time.time()
                info.latency = latency
                
                # Calculate uptime percentage
                total_requests = info.success_count + info.error_count
                if total_requests > 0:
                    info.uptime_percentage = (info.success_count / total_requests) * 100
                    
                # Determine status
                if latency < 0:
                    info.status = ExchangeStatus.OFFLINE
                elif latency > 5000 or info.uptime_percentage < 90:
                    info.status = ExchangeStatus.DEGRADED
                else:
                    info.status = ExchangeStatus.ONLINE
                    
                health_status[exchange_id] = {
                    'status': info.status.value,
                    'latency': latency,
                    'uptime_percentage': info.uptime_percentage,
                    'error_count': info.error_count,
                    'success_count': info.success_count,
                    'last_error': info.last_error
                }
                
            except Exception as e:
                self.logger.error(f"Health check failed for {exchange_id}: {e}")
                health_status[exchange_id] = {
                    'status': ExchangeStatus.OFFLINE.value,
                    'error': str(e)
                }
                
        return health_status
        
    def get_best_exchange(self, feature: str = None) -> Optional[str]:
        """Get the best exchange for a specific feature"""
        best_exchange = None
        best_score = -1
        
        for exchange_id, config in self.exchange_configs.items():
            if not config.enabled:
                continue
                
            info = self.exchange_info[exchange_id]
            
            # Skip offline exchanges
            if info.status != ExchangeStatus.ONLINE:
                continue
                
            # Calculate score based on priority, latency, and uptime
            score = (100 - config.priority) + (info.uptime_percentage / 10) - (info.latency / 100)
            
            # Boost score if feature is supported
            if feature and feature in config.features:
                score += 20
                
            if score > best_score:
                best_score = score
                best_exchange = exchange_id
                
        return best_exchange
        
    def get_exchange_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all exchanges"""
        status = {}
        
        for exchange_id, info in self.exchange_info.items():
            config = self.exchange_configs[exchange_id]
            
            status[exchange_id] = {
                'status': info.status.value,
                'type': config.exchange_type.value,
                'enabled': config.enabled,
                'priority': config.priority,
                'latency': info.latency,
                'uptime_percentage': info.uptime_percentage,
                'error_count': info.error_count,
                'success_count': info.success_count,
                'last_error': info.last_error,
                'features': config.features
            }
            
        return status

# Global exchange manager instance
exchange_manager = ExchangeManager()

def get_exchange_manager() -> ExchangeManager:
    """Get the global exchange manager instance"""
    return exchange_manager
