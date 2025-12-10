"""
TELEGLAS GPT API - Multi-Exchange Integration
Support for multiple cryptocurrency exchanges
"""

import asyncio
import ccxt
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import aiohttp
from loguru import logger

from .config import settings
from .cache import cache_manager, cached


class ExchangeType(Enum):
    """Supported exchange types"""
    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"
    BYBIT = "bybit"
    OKX = "okx"
    HUOBI = "huobi"
    KUCOIN = "kucoin"


@dataclass
class ExchangeConfig:
    """Exchange configuration"""
    exchange_id: str
    name: str
    api_key: Optional[str] = None
    secret: Optional[str] = None
    passphrase: Optional[str] = None  # For exchanges like Coinbase
    sandbox: bool = False
    rate_limit: int = 1200  # Requests per hour
    enabled: bool = True


@dataclass
class MarketTicker:
    """Market ticker data"""
    symbol: str
    exchange: str
    price: float
    bid: float
    ask: float
    volume_24h: float
    change_24h: float
    high_24h: float
    low_24h: float
    timestamp: datetime


@dataclass
class ExchangeOrderbook:
    """Exchange orderbook data"""
    symbol: str
    exchange: str
    bids: List[List[float]]
    asks: List[List[float]]
    timestamp: datetime


@dataclass
class ExchangeTrade:
    """Exchange trade data"""
    symbol: str
    exchange: str
    id: str
    price: float
    amount: float
    side: str
    timestamp: datetime


class MultiExchangeManager:
    """Manages multiple exchange connections and data aggregation"""
    
    def __init__(self):
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self.exchange_configs: Dict[str, ExchangeConfig] = {}
        self.supported_exchanges = {
            ExchangeType.BINANCE: self._create_binance,
            ExchangeType.COINBASE: self._create_coinbase,
            ExchangeType.KRAKEN: self._create_kraken,
            ExchangeType.BYBIT: self._create_bybit,
            ExchangeType.OKX: self._create_okx,
            ExchangeType.HUOBI: self._create_huobi,
            ExchangeType.KUCOIN: self._create_kucoin
        }
        
        # Symbol mapping between exchanges
        self.symbol_mappings = {
            "BTC": {
                ExchangeType.BINANCE.value: "BTC/USDT",
                ExchangeType.COINBASE.value: "BTC-USD",
                ExchangeType.KRAKEN.value: "XBT/USD",
                ExchangeType.BYBIT.value: "BTCUSDT",
                ExchangeType.OKX.value: "BTC-USDT",
                ExchangeType.HUOBI.value: "btcusdt",
                ExchangeType.KUCOIN.value: "BTC-USDT"
            },
            "ETH": {
                ExchangeType.BINANCE.value: "ETH/USDT",
                ExchangeType.COINBASE.value: "ETH-USD",
                ExchangeType.KRAKEN.value: "ETH/USD",
                ExchangeType.BYBIT.value: "ETHUSDT",
                ExchangeType.OKX.value: "ETH-USDT",
                ExchangeType.HUOBI.value: "ethusdt",
                ExchangeType.KUCOIN.value: "ETH-USDT"
            },
            "SOL": {
                ExchangeType.BINANCE.value: "SOL/USDT",
                ExchangeType.COINBASE.value: "SOL-USD",
                ExchangeType.KRAKEN.value: "SOL/USD",
                ExchangeType.BYBIT.value: "SOLUSDT",
                ExchangeType.OKX.value: "SOL-USDT",
                ExchangeType.HUOBI.value: "solusdt",
                ExchangeType.KUCOIN.value: "SOL-USDT"
            }
        }
        
    async def initialize(self):
        """Initialize all configured exchanges"""
        for exchange_type, creator in self.supported_exchanges.items():
            try:
                config = self._get_exchange_config(exchange_type)
                if config and config.enabled:
                    exchange = await creator(config)
                    if exchange:
                        self.exchanges[exchange_type.value] = exchange
                        self.exchange_configs[exchange_type.value] = config
                        logger.info(f"Initialized {exchange_type.value} exchange")
            except Exception as e:
                logger.error(f"Failed to initialize {exchange_type.value}: {e}")
    
    def _get_exchange_config(self, exchange_type: ExchangeType) -> Optional[ExchangeConfig]:
        """Get configuration for exchange type"""
        # In production, this would load from environment variables or config
        # For now, return basic config without API keys (public data only)
        if exchange_type == ExchangeType.BINANCE:
            return ExchangeConfig(
                exchange_id="binance",
                name="Binance",
                sandbox=False
            )
        elif exchange_type == ExchangeType.COINBASE:
            return ExchangeConfig(
                exchange_id="coinbase",
                name="Coinbase",
                sandbox=False
            )
        elif exchange_type == ExchangeType.KRAKEN:
            return ExchangeConfig(
                exchange_id="kraken",
                name="Kraken",
                sandbox=False
            )
        elif exchange_type == ExchangeType.BYBIT:
            return ExchangeConfig(
                exchange_id="bybit",
                name="Bybit",
                sandbox=False
            )
        elif exchange_type == ExchangeType.OKX:
            return ExchangeConfig(
                exchange_id="okx",
                name="OKX",
                sandbox=False
            )
        elif exchange_type == ExchangeType.HUOBI:
            return ExchangeConfig(
                exchange_id="huobi",
                name="Huobi",
                sandbox=False
            )
        elif exchange_type == ExchangeType.KUCOIN:
            return ExchangeConfig(
                exchange_id="kucoin",
                name="KuCoin",
                sandbox=False
            )
        return None
    
    async def _create_binance(self, config: ExchangeConfig) -> Optional[ccxt.Exchange]:
        """Create Binance exchange instance"""
        try:
            exchange = ccxt.binance({
                'apiKey': config.api_key,
                'secret': config.secret,
                'sandbox': config.sandbox,
                'enableRateLimit': True,
                'rateLimit': config.rate_limit
            })
            await self._test_exchange_connection(exchange)
            return exchange
        except Exception as e:
            logger.error(f"Failed to create Binance exchange: {e}")
            return None
    
    async def _create_coinbase(self, config: ExchangeConfig) -> Optional[ccxt.Exchange]:
        """Create Coinbase exchange instance"""
        try:
            exchange = ccxt.coinbase({
                'apiKey': config.api_key,
                'secret': config.secret,
                'passphrase': config.passphrase,
                'sandbox': config.sandbox,
                'enableRateLimit': True,
                'rateLimit': config.rate_limit
            })
            await self._test_exchange_connection(exchange)
            return exchange
        except Exception as e:
            logger.error(f"Failed to create Coinbase exchange: {e}")
            return None
    
    async def _create_kraken(self, config: ExchangeConfig) -> Optional[ccxt.Exchange]:
        """Create Kraken exchange instance"""
        try:
            exchange = ccxt.kraken({
                'apiKey': config.api_key,
                'secret': config.secret,
                'sandbox': config.sandbox,
                'enableRateLimit': True,
                'rateLimit': config.rate_limit
            })
            await self._test_exchange_connection(exchange)
            return exchange
        except Exception as e:
            logger.error(f"Failed to create Kraken exchange: {e}")
            return None
    
    async def _create_bybit(self, config: ExchangeConfig) -> Optional[ccxt.Exchange]:
        """Create Bybit exchange instance"""
        try:
            exchange = ccxt.bybit({
                'apiKey': config.api_key,
                'secret': config.secret,
                'sandbox': config.sandbox,
                'enableRateLimit': True,
                'rateLimit': config.rate_limit
            })
            await self._test_exchange_connection(exchange)
            return exchange
        except Exception as e:
            logger.error(f"Failed to create Bybit exchange: {e}")
            return None
    
    async def _create_okx(self, config: ExchangeConfig) -> Optional[ccxt.Exchange]:
        """Create OKX exchange instance"""
        try:
            exchange = ccxt.okx({
                'apiKey': config.api_key,
                'secret': config.secret,
                'password': config.passphrase,
                'sandbox': config.sandbox,
                'enableRateLimit': True,
                'rateLimit': config.rate_limit
            })
            await self._test_exchange_connection(exchange)
            return exchange
        except Exception as e:
            logger.error(f"Failed to create OKX exchange: {e}")
            return None
    
    async def _create_huobi(self, config: ExchangeConfig) -> Optional[ccxt.Exchange]:
        """Create Huobi exchange instance"""
        try:
            exchange = ccxt.huobi({
                'apiKey': config.api_key,
                'secret': config.secret,
                'sandbox': config.sandbox,
                'enableRateLimit': True,
                'rateLimit': config.rate_limit
            })
            await self._test_exchange_connection(exchange)
            return exchange
        except Exception as e:
            logger.error(f"Failed to create Huobi exchange: {e}")
            return None
    
    async def _create_kucoin(self, config: ExchangeConfig) -> Optional[ccxt.Exchange]:
        """Create KuCoin exchange instance"""
        try:
            exchange = ccxt.kucoin({
                'apiKey': config.api_key,
                'secret': config.secret,
                'password': config.passphrase,
                'sandbox': config.sandbox,
                'enableRateLimit': True,
                'rateLimit': config.rate_limit
            })
            await self._test_exchange_connection(exchange)
            return exchange
        except Exception as e:
            logger.error(f"Failed to create KuCoin exchange: {e}")
            return None
    
    async def _test_exchange_connection(self, exchange: ccxt.Exchange):
        """Test exchange connection"""
        try:
            await asyncio.to_thread(exchange.fetch_status)
            logger.info(f"Successfully connected to {exchange.id}")
        except Exception as e:
            logger.error(f"Failed to connect to {exchange.id}: {e}")
            raise
    
    def get_exchange_symbol(self, symbol: str, exchange: str) -> str:
        """Get exchange-specific symbol format"""
        symbol = symbol.upper()
        exchange_mappings = self.symbol_mappings.get(symbol, {})
        return exchange_mappings.get(exchange, f"{symbol}/USDT")
    
    @cached("multi_ticker", ttl=30)
    async def get_aggregated_ticker(self, symbol: str) -> MarketTicker:
        """Get aggregated ticker data from all exchanges"""
        tasks = []
        for exchange_name, exchange in self.exchanges.items():
            try:
                exchange_symbol = self.get_exchange_symbol(symbol, exchange_name)
                task = self._get_exchange_ticker(exchange, exchange_symbol, exchange_name)
                tasks.append(task)
            except Exception as e:
                logger.error(f"Error preparing ticker for {exchange_name}: {e}")
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        valid_tickers = [r for r in results if isinstance(r, MarketTicker)]
        
        if not valid_tickers:
            raise Exception(f"No valid ticker data for {symbol}")
        
        # Calculate aggregated values
        total_volume = sum(t.volume_24h for t in valid_tickers)
        weighted_price = sum(t.price * t.volume_24h for t in valid_tickers) / total_volume if total_volume > 0 else 0
        
        avg_change = sum(t.change_24h for t in valid_tickers) / len(valid_tickers)
        highest_bid = max(t.bid for t in valid_tickers if t.bid > 0)
        lowest_ask = min(t.ask for t in valid_tickers if t.ask > 0)
        highest_high = max(t.high_24h for t in valid_tickers if t.high_24h > 0)
        lowest_low = min(t.low_24h for t in valid_tickers if t.low_24h > 0)
        
        return MarketTicker(
            symbol=symbol,
            exchange="aggregated",
            price=weighted_price,
            bid=highest_bid,
            ask=lowest_ask,
            volume_24h=total_volume,
            change_24h=avg_change,
            high_24h=highest_high,
            low_24h=lowest_low,
            timestamp=datetime.utcnow()
        )
    
    async def _get_exchange_ticker(self, exchange: ccxt.Exchange, symbol: str, exchange_name: str) -> MarketTicker:
        """Get ticker from specific exchange"""
        try:
            ticker = await asyncio.to_thread(exchange.fetch_ticker, symbol)
            
            return MarketTicker(
                symbol=symbol.split('/')[0],  # Extract base symbol
                exchange=exchange_name,
                price=ticker.get('last', 0),
                bid=ticker.get('bid', 0),
                ask=ticker.get('ask', 0),
                volume_24h=ticker.get('baseVolume', 0),
                change_24h=ticker.get('percentage', 0),
                high_24h=ticker.get('high', 0),
                low_24h=ticker.get('low', 0),
                timestamp=datetime.fromtimestamp(ticker.get('timestamp', 0) / 1000)
            )
        except Exception as e:
            logger.error(f"Error fetching ticker from {exchange_name}: {e}")
            raise
    
    @cached("multi_orderbook", ttl=10)
    async def get_aggregated_orderbook(self, symbol: str, limit: int = 20) -> ExchangeOrderbook:
        """Get aggregated orderbook from multiple exchanges"""
        tasks = []
        for exchange_name, exchange in self.exchanges.items():
            try:
                exchange_symbol = self.get_exchange_symbol(symbol, exchange_name)
                task = self._get_exchange_orderbook(exchange, exchange_symbol, exchange_name, limit)
                tasks.append(task)
            except Exception as e:
                logger.error(f"Error preparing orderbook for {exchange_name}: {e}")
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate orderbooks
        valid_orderbooks = [r for r in results if isinstance(r, ExchangeOrderbook)]
        
        if not valid_orderbooks:
            raise Exception(f"No valid orderbook data for {symbol}")
        
        # Merge all bids and asks
        all_bids = []
        all_asks = []
        
        for orderbook in valid_orderbooks:
            all_bids.extend(orderbook.bids)
            all_asks.extend(orderbook.asks)
        
        # Sort and aggregate by price
        all_bids.sort(key=lambda x: x[0], reverse=True)  # Highest first
        all_asks.sort(key=lambda x: x[0])  # Lowest first
        
        # Aggregate by price levels (sum amounts at same price)
        aggregated_bids = self._aggregate_price_levels(all_bids[:limit * 2])
        aggregated_asks = self._aggregate_price_levels(all_asks[:limit * 2])
        
        return ExchangeOrderbook(
            symbol=symbol,
            exchange="aggregated",
            bids=aggregated_bids[:limit],
            asks=aggregated_asks[:limit],
            timestamp=datetime.utcnow()
        )
    
    def _aggregate_price_levels(self, price_levels: List[List[float]]) -> List[List[float]]:
        """Aggregate price levels with same price"""
        aggregated = {}
        
        for price, amount in price_levels:
            if price in aggregated:
                aggregated[price] += amount
            else:
                aggregated[price] = amount
        
        # Convert back to list format
        return [[price, amount] for price, amount in sorted(aggregated.items(), reverse=True)]
    
    async def get_exchange_health(self) -> Dict[str, Any]:
        """Get health status of all exchanges"""
        health_status = {}
        
        for exchange_name, exchange in self.exchanges.items():
            try:
                status = await asyncio.to_thread(exchange.fetch_status)
                health_status[exchange_name] = {
                    'status': status.get('status', 'unknown'),
                    'updated': status.get('updated', 0),
                    'eta': status.get('eta', 0),
                    'url': exchange.urls.get('api', ''),
                    'connected': True
                }
            except Exception as e:
                health_status[exchange_name] = {
                    'status': 'error',
                    'error': str(e),
                    'connected': False
                }
        
        return health_status
    
    async def get_supported_symbols(self, exchange: Optional[str] = None) -> Dict[str, List[str]]:
        """Get supported symbols from exchanges"""
        if exchange:
            if exchange not in self.exchanges:
                return {exchange: []}
            
            try:
                markets = await asyncio.to_thread(self.exchanges[exchange].load_markets)
                symbols = list(markets.keys())
                return {exchange: symbols}
            except Exception as e:
                logger.error(f"Error loading markets for {exchange}: {e}")
                return {exchange: []}
        
        # Get symbols from all exchanges
        all_symbols = {}
        for exchange_name, exchange_instance in self.exchanges.items():
            try:
                markets = await asyncio.to_thread(exchange_instance.load_markets)
                all_symbols[exchange_name] = list(markets.keys())
            except Exception as e:
                logger.error(f"Error loading markets for {exchange_name}: {e}")
                all_symbols[exchange_name] = []
        
        return all_symbols
    
    async def get_exchange_trades(self, symbol: str, limit: int = 50, exchange: Optional[str] = None) -> List[ExchangeTrade]:
        """Get recent trades from exchanges"""
        if exchange and exchange not in self.exchanges:
            raise Exception(f"Exchange {exchange} not available")
        
        exchanges_to_query = [exchange] if exchange else list(self.exchanges.keys())
        tasks = []
        
        for exchange_name in exchanges_to_query:
            exchange_instance = self.exchanges[exchange_name]
            exchange_symbol = self.get_exchange_symbol(symbol, exchange_name)
            task = self._get_exchange_trades(exchange_instance, exchange_symbol, exchange_name, limit)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter and flatten results
        all_trades = []
        for result in results:
            if isinstance(result, list):
                all_trades.extend(result)
        
        # Sort by timestamp
        all_trades.sort(key=lambda t: t.timestamp, reverse=True)
        
        return all_trades[:limit]
    
    async def _get_exchange_trades(self, exchange: ccxt.Exchange, symbol: str, exchange_name: str, limit: int) -> List[ExchangeTrade]:
        """Get trades from specific exchange"""
        try:
            trades = await asyncio.to_thread(exchange.fetch_trades, symbol, limit=limit)
            
            exchange_trades = []
            for trade in trades:
                exchange_trades.append(ExchangeTrade(
                    symbol=symbol.split('/')[0],
                    exchange=exchange_name,
                    id=str(trade.get('id', '')),
                    price=trade.get('price', 0),
                    amount=trade.get('amount', 0),
                    side=trade.get('side', ''),
                    timestamp=datetime.fromtimestamp(trade.get('timestamp', 0) / 1000)
                ))
            
            return exchange_trades
        except Exception as e:
            logger.error(f"Error fetching trades from {exchange_name}: {e}")
            return []


# Global multi-exchange manager
multi_exchange_manager = MultiExchangeManager()


async def initialize_multi_exchange():
    """Initialize multi-exchange system"""
    await multi_exchange_manager.initialize()
    logger.info(f"Multi-exchange initialized with {len(multi_exchange_manager.exchanges)} exchanges")


async def cleanup_multi_exchange():
    """Cleanup multi-exchange connections"""
    for exchange in multi_exchange_manager.exchanges.values():
        try:
            await asyncio.to_thread(exchange.close)
        except Exception as e:
            logger.error(f"Error closing exchange connection: {e}")
