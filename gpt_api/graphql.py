"""
TELEGLAS GPT API - GraphQL Endpoint
GraphQL schema and resolvers for flexible data queries
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import strawberry
from strawberry.types import Info
from loguru import logger

from .config import settings
from .auth import get_api_key_from_context, validate_api_key
from .cache import cache_manager, cached
from services.market_data_core import get_raw, get_whale, get_liq, get_raw_orderbook


# GraphQL Types
@strawberry.type
class PriceData:
    """Price information"""
    price: float
    change_24h: float
    volume_24h: float
    timestamp: datetime


@strawberry.type
class WhaleTransaction:
    """Whale transaction data"""
    id: str
    symbol: str
    side: str
    amount: float
    price: float
    usd_value: float
    timestamp: datetime
    exchange: str


@strawberry.type
class Liquidation:
    """Liquidation data"""
    id: str
    symbol: str
    side: str
    amount: float
    price: float
    usd_value: float
    timestamp: datetime
    exchange: str


@strawberry.type
class OrderbookLevel:
    """Orderbook price level"""
    price: float
    amount: float
    total: float


@strawberry.type
class Orderbook:
    """Orderbook data"""
    symbol: str
    bids: List[OrderbookLevel]
    asks: List[OrderbookLevel]
    spread: float
    timestamp: datetime


@strawberry.type
class MarketData:
    """Complete market data for a symbol"""
    symbol: str
    price: Optional[PriceData]
    whale_transactions: List[WhaleTransaction]
    liquidations: List[Liquidation]
    orderbook: Optional[Orderbook]
    timestamp: datetime


@strawberry.type
class QueryStats:
    """Query statistics"""
    total_requests: int
    cache_hits: int
    avg_response_time: float
    symbols_queried: List[str]


# Input Types
@strawberry.input
class SymbolFilter:
    """Symbol filter input"""
    symbols: Optional[List[str]] = None
    exclude_symbols: Optional[List[str]] = None


@strawberry.input
class WhaleFilter:
    """Whale transaction filter"""
    min_usd_value: Optional[float] = None
    side: Optional[str] = None
    limit: Optional[int] = 50


@strawberry.input
class LiquidationFilter:
    """Liquidation filter"""
    min_usd_value: Optional[float] = None
    side: Optional[str] = None
    limit: Optional[int] = 50


@strawberry.input
class OrderbookFilter:
    """Orderbook filter"""
    depth: Optional[int] = 20
    min_spread: Optional[float] = None


# Resolvers
async def resolve_price_data(symbol: str) -> Optional[PriceData]:
    """Resolve price data for symbol"""
    try:
        # Use cached raw data to get price information
        cache_key = f"price:{symbol}"
        
        # Check cache first
        cached_price = await cache_manager.get("price", symbol)
        if cached_price:
            return PriceData(**cached_price)
        
        # Get fresh data
        raw_data = await get_raw(symbol)
        if not raw_data:
            return None
            
        price_data = PriceData(
            price=raw_data.get('price', 0),
            change_24h=raw_data.get('change_24h', 0),
            volume_24h=raw_data.get('volume_24h', 0),
            timestamp=datetime.utcnow()
        )
        
        # Cache result
        await cache_manager.set("price", symbol, price_data.__dict__, ttl=60)
        
        return price_data
        
    except Exception as e:
        logger.error(f"Error resolving price data for {symbol}: {e}")
        return None


async def resolve_whale_transactions(symbol: str, filter: Optional[WhaleFilter] = None) -> List[WhaleTransaction]:
    """Resolve whale transactions for symbol"""
    try:
        limit = filter.limit if filter else 50
        min_value = filter.min_usd_value if filter else None
        side = filter.side if filter else None
        
        whale_data = await get_whale(symbol, limit=limit * 2)  # Get more for filtering
        
        transactions = []
        for item in whale_data:
            # Apply filters
            if min_value and item.get('usd_value', 0) < min_value:
                continue
            if side and item.get('side', '').lower() != side.lower():
                continue
                
            transactions.append(WhaleTransaction(
                id=item.get('id', f"{symbol}_{item.get('timestamp', '')}"),
                symbol=symbol,
                side=item.get('side', ''),
                amount=item.get('amount', 0),
                price=item.get('price', 0),
                usd_value=item.get('usd_value', 0),
                timestamp=item.get('timestamp', datetime.utcnow()),
                exchange=item.get('exchange', 'unknown')
            ))
            
            if len(transactions) >= limit:
                break
                
        return transactions
        
    except Exception as e:
        logger.error(f"Error resolving whale transactions for {symbol}: {e}")
        return []


async def resolve_liquidations(symbol: str, filter: Optional[LiquidationFilter] = None) -> List[Liquidation]:
    """Resolve liquidations for symbol"""
    try:
        limit = filter.limit if filter else 50
        min_value = filter.min_usd_value if filter else None
        side = filter.side if filter else None
        
        liq_data = await get_liq(symbol)
        
        liquidations = []
        for item in liq_data:
            # Apply filters
            if min_value and item.get('usd_value', 0) < min_value:
                continue
            if side and item.get('side', '').lower() != side.lower():
                continue
                
            liquidations.append(Liquidation(
                id=item.get('id', f"{symbol}_{item.get('timestamp', '')}"),
                symbol=symbol,
                side=item.get('side', ''),
                amount=item.get('amount', 0),
                price=item.get('price', 0),
                usd_value=item.get('usd_value', 0),
                timestamp=item.get('timestamp', datetime.utcnow()),
                exchange=item.get('exchange', 'unknown')
            ))
            
            if len(liquidations) >= limit:
                break
                
        return liquidations
        
    except Exception as e:
        logger.error(f"Error resolving liquidations for {symbol}: {e}")
        return []


async def resolve_orderbook(symbol: str, filter: Optional[OrderbookFilter] = None) -> Optional[Orderbook]:
    """Resolve orderbook for symbol"""
    try:
        depth = filter.depth if filter else 20
        min_spread = filter.min_spread if filter else None
        
        orderbook_data = await get_raw_orderbook(symbol, depth=depth)
        
        if not orderbook_data:
            return None
            
        bids = [
            OrderbookLevel(
                price=bid[0],
                amount=bid[1],
                total=bid[0] * bid[1]
            )
            for bid in orderbook_data.get('bids', [])[:depth]
        ]
        
        asks = [
            OrderbookLevel(
                price=ask[0],
                amount=ask[1],
                total=ask[0] * ask[1]
            )
            for ask in orderbook_data.get('asks', [])[:depth]
        ]
        
        # Calculate spread
        spread = 0
        if bids and asks:
            spread = asks[0].price - bids[0].price
            
        # Check min spread filter
        if min_spread and spread < min_spread:
            return None
            
        return Orderbook(
            symbol=symbol,
            bids=bids,
            asks=asks,
            spread=spread,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error resolving orderbook for {symbol}: {e}")
        return None


@strawberry.type
class Query:
    """GraphQL Query root"""
    
    @strawberry.field
    async def price(self, symbol: str, info: Info) -> Optional[PriceData]:
        """Get price data for a symbol"""
        # Validate API key
        api_key = get_api_key_from_context(info.context)
        if not validate_api_key(api_key):
            raise Exception("Invalid API key")
            
        # Validate symbol
        if not settings.is_symbol_supported(symbol.upper()):
            raise Exception(f"Symbol {symbol} not supported")
            
        return await resolve_price_data(symbol.upper())
    
    @strawberry.field
    async def whale_transactions(
        self, 
        symbol: str, 
        filter: Optional[WhaleFilter] = None,
        info: Info = None
    ) -> List[WhaleTransaction]:
        """Get whale transactions for a symbol"""
        # Validate API key
        api_key = get_api_key_from_context(info.context)
        if not validate_api_key(api_key):
            raise Exception("Invalid API key")
            
        # Validate symbol
        if not settings.is_symbol_supported(symbol.upper()):
            raise Exception(f"Symbol {symbol} not supported")
            
        return await resolve_whale_transactions(symbol.upper(), filter)
    
    @strawberry.field
    async def liquidations(
        self, 
        symbol: str, 
        filter: Optional[LiquidationFilter] = None,
        info: Info = None
    ) -> List[Liquidation]:
        """Get liquidations for a symbol"""
        # Validate API key
        api_key = get_api_key_from_context(info.context)
        if not validate_api_key(api_key):
            raise Exception("Invalid API key")
            
        # Validate symbol
        if not settings.is_symbol_supported(symbol.upper()):
            raise Exception(f"Symbol {symbol} not supported")
            
        return await resolve_liquidations(symbol.upper(), filter)
    
    @strawberry.field
    async def orderbook(
        self, 
        symbol: str, 
        filter: Optional[OrderbookFilter] = None,
        info: Info = None
    ) -> Optional[Orderbook]:
        """Get orderbook for a symbol"""
        # Validate API key
        api_key = get_api_key_from_context(info.context)
        if not validate_api_key(api_key):
            raise Exception("Invalid API key")
            
        # Validate symbol
        if not settings.is_symbol_supported(symbol.upper()):
            raise Exception(f"Symbol {symbol} not supported")
            
        return await resolve_orderbook(symbol.upper(), filter)
    
    @strawberry.field
    async def market_data(
        self, 
        symbol: str,
        whale_filter: Optional[WhaleFilter] = None,
        liquidation_filter: Optional[LiquidationFilter] = None,
        orderbook_filter: Optional[OrderbookFilter] = None,
        info: Info = None
    ) -> MarketData:
        """Get complete market data for a symbol"""
        # Validate API key
        api_key = get_api_key_from_context(info.context)
        if not validate_api_key(api_key):
            raise Exception("Invalid API key")
            
        # Validate symbol
        if not settings.is_symbol_supported(symbol.upper()):
            raise Exception(f"Symbol {symbol} not supported")
        
        # Fetch all data concurrently
        symbol_upper = symbol.upper()
        
        price_task = resolve_price_data(symbol_upper)
        whale_task = resolve_whale_transactions(symbol_upper, whale_filter)
        liquidation_task = resolve_liquidations(symbol_upper, liquidation_filter)
        orderbook_task = resolve_orderbook(symbol_upper, orderbook_filter)
        
        price, whale_transactions, liquidations, orderbook = await asyncio.gather(
            price_task,
            whale_task,
            liquidation_task,
            orderbook_task,
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(price, Exception):
            logger.error(f"Price data error: {price}")
            price = None
            
        if isinstance(whale_transactions, Exception):
            logger.error(f"Whale data error: {whale_transactions}")
            whale_transactions = []
            
        if isinstance(liquidations, Exception):
            logger.error(f"Liquidation data error: {liquidations}")
            liquidations = []
            
        if isinstance(orderbook, Exception):
            logger.error(f"Orderbook data error: {orderbook}")
            orderbook = None
        
        return MarketData(
            symbol=symbol_upper,
            price=price,
            whale_transactions=whale_transactions,
            liquidations=liquidations,
            orderbook=orderbook,
            timestamp=datetime.utcnow()
        )
    
    @strawberry.field
    async def supported_symbols(self, info: Info) -> List[str]:
        """Get list of supported symbols"""
        # Validate API key
        api_key = get_api_key_from_context(info.context)
        if not validate_api_key(api_key):
            raise Exception("Invalid API key")
            
        return settings.supported_symbols
    
    @strawberry.field
    async def query_stats(self, info: Info) -> QueryStats:
        """Get query statistics (admin only)"""
        # Validate API key
        api_key = get_api_key_from_context(info.context)
        if not validate_api_key(api_key):
            raise Exception("Invalid API key")
        
        # This would normally connect to analytics
        # For now, return mock data
        return QueryStats(
            total_requests=1000,
            cache_hits=750,
            avg_response_time=125.5,
            symbols_queried=["BTC", "ETH", "SOL"]
        )


# Subscription types for real-time updates
@strawberry.type
class Subscription:
    """GraphQL Subscription root"""
    
    @strawberry.subscription
    async def price_updates(self, symbols: List[str], info: Info) -> PriceData:
        """Subscribe to price updates for symbols"""
        # Validate API key
        api_key = get_api_key_from_context(info.context)
        if not validate_api_key(api_key):
            raise Exception("Invalid API key")
            
        # This would normally connect to WebSocket for real-time updates
        # For now, just return static data
        while True:
            for symbol in symbols:
                if settings.is_symbol_supported(symbol.upper()):
                    price_data = await resolve_price_data(symbol.upper())
                    if price_data:
                        yield price_data
            await asyncio.sleep(30)  # Update every 30 seconds


# Create GraphQL schema
schema = strawberry.Schema(query=Query, subscription=Subscription)


# GraphQL Context
async def get_context(request):
    """Get GraphQL context"""
    return {
        "request": request,
        "headers": dict(request.headers)
    }


# GraphQL middleware for authentication
class GraphQLAuthMiddleware:
    """Authentication middleware for GraphQL"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Extract API key from headers
            headers = dict(scope.get("headers", []))
            api_key = headers.get(b"authorization", b"").decode()
            
            if api_key.startswith("Bearer "):
                api_key = api_key[7:]
            
            # Add to scope
            scope["api_key"] = api_key
        
        await self.app(scope, receive, send)


# Helper function to create FastAPI GraphQL app
def create_graphql_app():
    """Create FastAPI GraphQL application"""
    from strawberry.fastapi import GraphQLRouter
    
    return GraphQLRouter(
        schema,
        context_getter=get_context,
        graphiql=settings.environment == "development"
    )
