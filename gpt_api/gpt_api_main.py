#!/usr/bin/env python3
"""
TELEGLAS GPT API Main Entry Point
FastAPI service for GPT Actions - provides clean JSON market data
"""

import sys
import os
import time
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, '..')

from fastapi import FastAPI, Request, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from loguru import logger
from datetime import datetime

# Import GPT API modules
try:
    from gpt_api.config import settings, get_allowed_origins
    from gpt_api.auth import (
        api_key_auth, 
        ip_whitelist_auth, 
        security_headers, 
        request_logger, 
        input_validator
    )
    from gpt_api.schemas import (
        BaseResponse, ErrorResponse, SuccessResponse,
        RawResponse, WhaleResponse, LiqResponse, OrderbookResponse,
        HealthCheckResponse, SupportedSymbolsResponse, InfoResponse,
        APIMetadata, SymbolRequest, WhaleRequest
    )
except ImportError:
    # Fallback for direct execution
    from config import settings, get_allowed_origins
    from auth import (
        api_key_auth, 
        ip_whitelist_auth, 
        security_headers, 
        request_logger, 
        input_validator
    )
    from schemas import (
        BaseResponse, ErrorResponse, SuccessResponse,
        RawResponse, WhaleResponse, LiqResponse, OrderbookResponse,
        HealthCheckResponse, SupportedSymbolsResponse, InfoResponse,
        APIMetadata, SymbolRequest, WhaleRequest
    )

# Import market data core
try:
    from services.market_data_core import market_data_core
except ImportError:
    import sys
    sys.path.append('..')
    from services.market_data_core import market_data_core


# Global variables for startup/shutdown
startup_time = datetime.utcnow()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("[GPT_API] Starting GPT API service...")
    
    # Initialize market data services
    try:
        # Test connectivity to market data services
        health_check = await market_data_core.health_check()
        if health_check["overall_status"] != "healthy":
            logger.warning("[GPT_API] Some services may be unhealthy on startup")
        else:
            logger.info("[GPT_API] All services healthy on startup")
    except Exception as e:
        logger.error(f"[GPT_API] Error during startup health check: {e}")
    
    logger.info(f"[GPT_API] GPT API started successfully on port {settings.port}")
    
    yield
    
    # Shutdown
    logger.info("[GPT_API] Shutting down GPT API service...")


# Create FastAPI app
app = FastAPI(
    title=settings.api_name,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)


# Security middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Add security headers
    for header, value in security_headers.get_security_headers().items():
        response.headers[header] = value
    
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()
    
    # Get auth info
    api_key = "anonymous"
    client_ip = "unknown"
    
    try:
        # Try to get API key
        credentials = await api_key_auth.security(request)
        if credentials:
            api_key = await api_key_auth.verify_api_key(credentials)
    except:
        pass
    
    try:
        client_ip = await ip_whitelist_auth.verify_ip_address(request)
    except:
        pass
    
    # Process request
    response = await call_next(request)
    
    # Log request
    processing_time = time.time() - start_time
    await request_logger.log_request(
        request, api_key, client_ip, response.status_code, processing_time
    )
    
    return response


# Authentication dependency
async def get_current_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(api_key_auth.security)
) -> str:
    """Get and validate current API key"""
    return await api_key_auth.verify_api_key(credentials)


async def get_current_client_ip(request: Request) -> str:
    """Get and validate current client IP"""
    return await ip_whitelist_auth.verify_ip_address(request)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            timestamp=datetime.utcnow().isoformat(),
            error=exc.detail,
            error_code=f"HTTP_{exc.status_code}"
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"[GPT_API] Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            timestamp=datetime.utcnow().isoformat(),
            error="Internal server error",
            error_code="INTERNAL_ERROR"
        ).dict()
    )


# Root endpoint
@app.get("/", response_model=InfoResponse)
async def root():
    """Root endpoint with API information"""
    endpoints = [
        "/gpt/raw",
        "/gpt/whale", 
        "/gpt/liq",
        "/gpt/orderbook",
        "/health",
        "/info",
        "/symbols"
    ]
    
    metadata = APIMetadata(
        version=settings.api_version,
        name=settings.api_name,
        description=settings.api_description,
        endpoints=endpoints,
        rate_limits={
            "requests_per_minute": str(settings.rate_limit_requests),
            "window_seconds": str(settings.rate_limit_window)
        }
    )
    
    return InfoResponse(
        success=True,
        timestamp=datetime.utcnow().isoformat(),
        data=metadata
    )


# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint"""
    try:
        health_status = await market_data_core.health_check()
        uptime = str(datetime.utcnow() - startup_time)
        
        return HealthCheckResponse(
            success=True,
            timestamp=datetime.utcnow().isoformat(),
            overall_status=health_status["overall_status"],
            services=health_status["services"],
            uptime=uptime,
            version=settings.api_version
        )
    except Exception as e:
        logger.error(f"[GPT_API] Health check error: {e}")
        return HealthCheckResponse(
            success=True,
            timestamp=datetime.utcnow().isoformat(),
            overall_status="error",
            services={},
            uptime=str(datetime.utcnow() - startup_time),
            version=settings.api_version
        )


# Info endpoint
@app.get("/info", response_model=InfoResponse)
async def info():
    """API information endpoint"""
    endpoints = [
        "/gpt/raw?symbol=BTC",
        "/gpt/whale?symbol=BTC&limit=10",
        "/gpt/liq?symbol=BTC", 
        "/gpt/orderbook?symbol=BTC",
        "/health",
        "/info",
        "/symbols"
    ]
    
    metadata = APIMetadata(
        version=settings.api_version,
        name=settings.api_name,
        description=settings.api_description,
        endpoints=endpoints,
        rate_limits={
            "requests_per_minute": str(settings.rate_limit_requests),
            "window_seconds": str(settings.rate_limit_window)
        }
    )
    
    return InfoResponse(
        success=True,
        timestamp=datetime.utcnow().isoformat(),
        data=metadata
    )


# Supported symbols endpoint
@app.get("/symbols", response_model=SupportedSymbolsResponse)
async def get_supported_symbols():
    """Get list of supported symbols"""
    try:
        symbols = await market_data_core.get_supported_symbols()
        return SupportedSymbolsResponse(
            success=True,
            timestamp=datetime.utcnow().isoformat(),
            symbols=symbols,
            total_count=len(symbols)
        )
    except Exception as e:
        logger.error(f"[GPT_API] Error getting supported symbols: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get supported symbols"
        )


# GPT API Endpoints

@app.get("/gpt/raw", response_model=RawResponse)
async def get_raw_data(
    symbol: str = Query(..., description="Trading symbol (e.g., BTC, ETH)"),
    api_key: str = Depends(get_current_api_key),
    client_ip: str = Depends(get_current_client_ip)
):
    """Get raw market data for a symbol"""
    try:
        # Validate input
        validated_symbol = input_validator.validate_symbol(symbol)
        
        # Get data from market data core
        result = await market_data_core.get_raw(validated_symbol)
        
        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "No data available")
            )
        
        return RawResponse(
            success=True,
            timestamp=datetime.utcnow().isoformat(),
            symbol=validated_symbol,
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GPT_API] Error in /gpt/raw: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch raw data"
        )


@app.get("/gpt/whale", response_model=WhaleResponse)
async def get_whale_data(
    symbol: Optional[str] = Query(None, description="Trading symbol (optional, all symbols if not provided)"),
    limit: Optional[int] = Query(10, ge=1, le=100, description="Number of transactions to return"),
    threshold: Optional[float] = Query(None, ge=0, description="Minimum threshold in USD"),
    radar: bool = Query(False, description="Get whale radar data instead of transactions"),
    api_key: str = Depends(get_current_api_key),
    client_ip: str = Depends(get_current_client_ip)
):
    """Get whale transaction data or whale radar"""
    try:
        if radar:
            # Get whale radar data
            result = await market_data_core.get_whale_radar(threshold)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=404,
                    detail=result.get("error", "No whale radar data available")
                )
            
            return WhaleResponse(
                success=True,
                timestamp=datetime.utcnow().isoformat(),
                symbol=None,
                data=result["data"]
            )
        else:
            # Get whale transactions
            validated_limit = input_validator.validate_limit(limit, settings.whale_default_limit, settings.whale_max_limit)
            validated_threshold = input_validator.validate_threshold(threshold)
            
            validated_symbol = None
            if symbol:
                validated_symbol = input_validator.validate_symbol(symbol)
            
            result = await market_data_core.get_whale(validated_symbol, validated_limit)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=404,
                    detail=result.get("error", "No whale data available")
                )
            
            return WhaleResponse(
                success=True,
                timestamp=datetime.utcnow().isoformat(),
                symbol=validated_symbol,
                data=result["data"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GPT_API] Error in /gpt/whale: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch whale data"
        )


@app.get("/gpt/liq", response_model=LiqResponse)
async def get_liquidation_data(
    symbol: str = Query(..., description="Trading symbol (e.g., BTC, ETH)"),
    api_key: str = Depends(get_current_api_key),
    client_ip: str = Depends(get_current_client_ip)
):
    """Get liquidation data for a symbol"""
    try:
        # Validate input
        validated_symbol = input_validator.validate_symbol(symbol)
        
        # Get data from market data core
        result = await market_data_core.get_liq(validated_symbol)
        
        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "No liquidation data available")
            )
        
        return LiqResponse(
            success=True,
            timestamp=datetime.utcnow().isoformat(),
            symbol=validated_symbol,
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GPT_API] Error in /gpt/liq: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch liquidation data"
        )


@app.get("/gpt/orderbook", response_model=OrderbookResponse)
async def get_orderbook_data(
    symbol: str = Query(..., description="Trading symbol (e.g., BTC, ETH)"),
    depth: Optional[int] = Query(20, ge=1, le=100, description="Orderbook depth"),
    api_key: str = Depends(get_current_api_key),
    client_ip: str = Depends(get_current_client_ip)
):
    """Get orderbook data for a symbol"""
    try:
        # Validate input
        validated_symbol = input_validator.validate_symbol(symbol)
        validated_depth = input_validator.validate_limit(depth, settings.orderbook_default_depth, settings.orderbook_max_depth)
        
        # Get data from market data core
        result = await market_data_core.get_raw_orderbook(validated_symbol)
        
        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "No orderbook data available")
            )
        
        return OrderbookResponse(
            success=True,
            timestamp=datetime.utcnow().isoformat(),
            symbol=validated_symbol,
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GPT_API] Error in /gpt/orderbook: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch orderbook data"
        )


# Run the app
if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    if settings.log_file:
        logger.add(
            settings.log_file,
            level=settings.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="7 days"
        )
    
    # Start server
    uvicorn.run(
        "gpt_api_main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
        use_colors=True
    )
