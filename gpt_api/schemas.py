#!/usr/bin/env python3
"""
GPT API Response Schemas
Pydantic models for clean JSON responses
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator


# Base Response Schema
class BaseResponse(BaseModel):
    """Base response schema for all GPT API endpoints"""
    success: bool = Field(..., description="Whether the request was successful")
    timestamp: str = Field(..., description="ISO format timestamp of the response")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseResponse):
    """Error response schema"""
    success: bool = Field(False, description="Always false for error responses")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Optional error code")


class SuccessResponse(BaseResponse):
    """Success response schema with data"""
    success: bool = Field(True, description="Always true for success responses")
    data: Dict[str, Any] = Field(..., description="Response data")


# Raw Data Schemas
class PriceInfo(BaseModel):
    """Price information schema"""
    current: float = Field(..., description="Current price")
    change_24h: float = Field(..., description="24 hour price change")
    change_percent_24h: float = Field(..., description="24 hour price change percentage")
    high_24h: float = Field(..., description="24 hour high price")
    low_24h: float = Field(..., description="24 hour low price")


class VolumeInfo(BaseModel):
    """Volume information schema"""
    spot_24h: float = Field(..., description="24 hour spot volume")
    futures_24h: float = Field(..., description="24 hour futures volume")
    open_interest: Optional[float] = Field(None, description="Open interest")


class LiquidationInfo(BaseModel):
    """Liquidation information schema"""
    total_24h: float = Field(..., description="Total liquidations 24h")
    long_liq: float = Field(..., description="Long liquidations 24h")
    short_liq: float = Field(..., description="Short liquidations 24h")


class MarketStats(BaseModel):
    """Market statistics schema"""
    price: PriceInfo = Field(..., description="Price information")
    volume: VolumeInfo = Field(..., description="Volume information")
    liquidations: LiquidationInfo = Field(..., description="Liquidation information")


class RawSnapshot(BaseModel):
    """Raw market data snapshot schema"""
    symbol: str = Field(..., description="Trading symbol")
    market_stats: MarketStats = Field(..., description="Market statistics")
    funding_rate: Optional[float] = Field(None, description="Current funding rate")
    next_funding_time: Optional[str] = Field(None, description="Next funding time")
    data_sources: List[str] = Field(default_factory=list, description="Data sources used")


# Whale Data Schemas
class WhaleTransaction(BaseModel):
    """Whale transaction schema"""
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="Trade side (buy/sell)")
    amount_usd: float = Field(..., description="Transaction amount in USD")
    price: float = Field(..., description="Transaction price")
    timestamp: str = Field(..., description="Transaction timestamp")
    transaction_hash: str = Field(..., description="Transaction identifier")


class WhaleSnapshot(BaseModel):
    """Whale activity snapshot schema"""
    transactions: List[WhaleTransaction] = Field(..., description="List of whale transactions")
    total_transactions: int = Field(..., description="Total number of transactions")
    total_volume_usd: float = Field(..., description="Total volume in USD")
    symbol: Optional[str] = Field(None, description="Symbol if filtered, None for all")
    time_range: str = Field(..., description="Time range of data")


class WhaleRadarItem(BaseModel):
    """Whale radar item schema"""
    symbol: str = Field(..., description="Trading symbol")
    buy_count: int = Field(..., description="Number of buy transactions")
    sell_count: int = Field(..., description="Number of sell transactions")
    buy_usd: float = Field(..., description="Total buy volume in USD")
    sell_usd: float = Field(..., description="Total sell volume in USD")
    total_usd: float = Field(..., description="Total volume in USD")
    net_usd: float = Field(..., description="Net volume (buy - sell) in USD")
    dominant_side: str = Field(..., description="Dominant trading side")


class WhaleRadarSnapshot(BaseModel):
    """Whale radar snapshot schema"""
    symbols_above_threshold: List[WhaleRadarItem] = Field(..., description="Symbols above threshold")
    symbols_below_threshold: List[WhaleRadarItem] = Field(..., description="Symbols below threshold")
    total_alerts: int = Field(..., description="Total number of alerts")
    threshold_used: Optional[float] = Field(None, description="Threshold used for filtering")


# Liquidation Data Schemas
class LiquidationEvent(BaseModel):
    """Liquidation event schema"""
    symbol: str = Field(..., description="Trading symbol")
    liquidation_usd: float = Field(..., description="Liquidation amount in USD")
    long_liquidation_usd: float = Field(..., description="Long liquidation amount in USD")
    short_liquidation_usd: float = Field(..., description="Short liquidation amount in USD")
    exchange_count: int = Field(..., description="Number of exchanges")
    price_change: float = Field(..., description="Price change percentage")
    volume_24h: float = Field(..., description="24 hour volume")
    last_update: str = Field(..., description="Last update timestamp")


class LiqSnapshot(BaseModel):
    """Liquidation snapshot schema"""
    symbol: str = Field(..., description="Trading symbol")
    liquidation_data: LiquidationEvent = Field(..., description="Liquidation event data")
    dominance_ratio: float = Field(..., description="Long/short dominance ratio")
    significance_level: str = Field(..., description="Significance level (low/medium/high)")


# Orderbook Data Schemas
class OrderbookLevel(BaseModel):
    """Orderbook price level schema"""
    price: float = Field(..., description="Price level")
    amount: float = Field(..., description="Amount at this price level")
    total_usd: float = Field(..., description="Total USD value at this level")


class OrderbookSide(BaseModel):
    """Orderbook side schema"""
    levels: List[OrderbookLevel] = Field(..., description="Price levels")
    total_amount: float = Field(..., description="Total amount on this side")
    total_usd: float = Field(..., description="Total USD value on this side")


class OrderbookSnapshot(BaseModel):
    """Orderbook snapshot schema"""
    symbol: str = Field(..., description="Trading symbol")
    bids: OrderbookSide = Field(..., description="Bid side of orderbook")
    asks: OrderbookSide = Field(..., description="Ask side of orderbook")
    spread: float = Field(..., description="Bid-ask spread")
    spread_percentage: float = Field(..., description="Spread as percentage")
    mid_price: float = Field(..., description="Mid price")
    depth_analysis: Dict[str, Any] = Field(default_factory=dict, description="Depth analysis")
    last_update: str = Field(..., description="Last update timestamp")


# Full Response Models
class RawResponse(BaseResponse):
    """Raw data response model"""
    success: bool = Field(True)
    symbol: str = Field(..., description="Requested symbol")
    data: RawSnapshot = Field(..., description="Raw market data snapshot")


class WhaleResponse(BaseResponse):
    """Whale data response model"""
    success: bool = Field(True)
    symbol: Optional[str] = Field(None, description="Requested symbol or None for all")
    data: Union[WhaleSnapshot, WhaleRadarSnapshot] = Field(..., description="Whale data")


class LiqResponse(BaseResponse):
    """Liquidation data response model"""
    success: bool = Field(True)
    symbol: str = Field(..., description="Requested symbol")
    data: LiqSnapshot = Field(..., description="Liquidation data snapshot")


class OrderbookResponse(BaseResponse):
    """Orderbook data response model"""
    success: bool = Field(True)
    symbol: str = Field(..., description="Requested symbol")
    data: OrderbookSnapshot = Field(..., description="Orderbook data snapshot")


# Health Check Schema
class ServiceHealth(BaseModel):
    """Individual service health schema"""
    status: str = Field(..., description="Service status (healthy/unhealthy/error)")
    last_check: str = Field(..., description="Last check timestamp")
    error: Optional[str] = Field(None, description="Error message if status is error")


class HealthCheckResponse(BaseResponse):
    """Health check response schema"""
    success: bool = Field(True)
    overall_status: str = Field(..., description="Overall system status")
    services: Dict[str, ServiceHealth] = Field(..., description="Individual service health")
    uptime: Optional[str] = Field(None, description="Service uptime")
    version: Optional[str] = Field(None, description="API version")


# Symbol Validation Schema
class SupportedSymbolsResponse(BaseResponse):
    """Supported symbols response schema"""
    success: bool = Field(True)
    symbols: List[str] = Field(..., description="List of supported symbols")
    total_count: int = Field(..., description="Total number of supported symbols")


# Request Validation Schemas
class SymbolRequest(BaseModel):
    """Symbol request validation schema"""
    symbol: str = Field(..., min_length=1, max_length=10, pattern=r'^[A-Z]{2,6}$', 
                       description="Trading symbol (2-6 uppercase letters)")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper()


class WhaleRequest(BaseModel):
    """Whale request validation schema"""
    symbol: Optional[str] = Field(None, pattern=r'^[A-Z]{2,6}$|None$', 
                                 description="Trading symbol or None for all symbols")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Number of results to return")
    threshold: Optional[float] = Field(None, ge=0, description="Minimum threshold for filtering")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper() if v else None


# API Metadata Schema
class APIMetadata(BaseModel):
    """API metadata schema"""
    version: str = Field("1.0.0", description="API version")
    name: str = Field("TELEGLAS GPT API", description="API name")
    description: str = Field("Market data API for GPT Actions", description="API description")
    endpoints: List[str] = Field(..., description="Available endpoints")
    rate_limits: Dict[str, str] = Field(..., description="Rate limit information")


class InfoResponse(BaseResponse):
    """API info response schema"""
    success: bool = Field(True)
    data: APIMetadata = Field(..., description="API metadata")
