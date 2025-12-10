"""
TELEGLAS GPT API - Caching Layer
Redis-based caching for improved performance
"""

import json
import asyncio
from typing import Any, Optional, Dict, Union
from datetime import datetime, timedelta
import aioredis
from loguru import logger
from .config import settings


class CacheManager:
    """Redis-based cache manager"""
    
    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.enabled = settings.cache_enabled
        self.default_ttl = settings.cache_ttl
        self.key_prefix = "teleglas:gpt:"
        
    async def initialize(self):
        """Initialize Redis connection"""
        if not self.enabled:
            logger.info("Cache disabled by configuration")
            return
            
        try:
            self.redis_client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Cache initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize cache: {e}")
            self.enabled = False
            self.redis_client = None
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Cache connection closed")
    
    def _make_key(self, category: str, symbol: str, **kwargs) -> str:
        """Generate cache key"""
        key_parts = [self.key_prefix, category, symbol.lower()]
        
        # Add additional parameters to key
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}:{v}")
        
        return ":".join(key_parts)
    
    async def get(self, category: str, symbol: str, **kwargs) -> Optional[Any]:
        """Get cached data"""
        if not self.enabled or not self.redis_client:
            return None
            
        try:
            key = self._make_key(category, symbol, **kwargs)
            cached_data = await self.redis_client.get(key)
            
            if cached_data:
                data = json.loads(cached_data)
                logger.debug(f"Cache hit for {key}")
                return data
            else:
                logger.debug(f"Cache miss for {key}")
                return None
                
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, category: str, symbol: str, data: Any, ttl: Optional[int] = None, **kwargs):
        """Set cached data"""
        if not self.enabled or not self.redis_client:
            return
            
        try:
            key = self._make_key(category, symbol, **kwargs)
            ttl = ttl or self.default_ttl
            
            # Serialize data
            json_data = json.dumps(data, default=str)
            
            await self.redis_client.setex(key, ttl, json_data)
            logger.debug(f"Cached data for {key} (TTL: {ttl}s)")
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def delete(self, category: str, symbol: str, **kwargs):
        """Delete cached data"""
        if not self.enabled or not self.redis_client:
            return
            
        try:
            key = self._make_key(category, symbol, **kwargs)
            await self.redis_client.delete(key)
            logger.debug(f"Deleted cache for {key}")
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
    
    async def clear_category(self, category: str):
        """Clear all cached data for a category"""
        if not self.enabled or not self.redis_client:
            return
            
        try:
            pattern = f"{self.key_prefix}{category}:*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries for category: {category}")
                
        except Exception as e:
            logger.error(f"Cache clear category error: {e}")
    
    async def clear_symbol(self, symbol: str):
        """Clear all cached data for a symbol"""
        if not self.enabled or not self.redis_client:
            return
            
        try:
            pattern = f"{self.key_prefix}*:{symbol.lower()}:*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries for symbol: {symbol}")
                
        except Exception as e:
            logger.error(f"Cache clear symbol error: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enabled or not self.redis_client:
            return {"enabled": False}
            
        try:
            info = await self.redis_client.info()
            
            # Get our keys count
            pattern = f"{self.key_prefix}*"
            keys = await self.redis_client.keys(pattern)
            
            return {
                "enabled": True,
                "connected": True,
                "total_keys": len(keys),
                "memory_used": info.get("used_memory_human", "N/A"),
                "hit_rate": info.get("keyspace_hits", 0),
                "miss_rate": info.get("keyspace_misses", 0),
                "uptime_seconds": info.get("uptime_in_seconds", 0)
            }
            
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"enabled": True, "connected": False, "error": str(e)}


# Global cache instance
cache_manager = CacheManager()


class CacheDecorator:
    """Decorator for caching function results"""
    
    def __init__(self, category: str, ttl: Optional[int] = None, key_params: list = None):
        self.category = category
        self.ttl = ttl
        self.key_params = key_params or ["symbol"]
    
    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            # Extract cache key parameters
            cache_kwargs = {}
            for param in self.key_params:
                if param in kwargs:
                    cache_kwargs[param] = kwargs[param]
            
            # Try to get from cache
            if cache_kwargs:
                cached_result = await cache_manager.get(
                    self.category, 
                    cache_kwargs.get("symbol", ""),
                    **{k: v for k, v in cache_kwargs.items() if k != "symbol"}
                )
                
                if cached_result is not None:
                    return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            if cache_kwargs and result is not None:
                await cache_manager.set(
                    self.category,
                    cache_kwargs.get("symbol", ""),
                    result,
                    self.ttl,
                    **{k: v for k, v in cache_kwargs.items() if k != "symbol"}
                )
            
            return result
        
        return wrapper


def cached(category: str, ttl: Optional[int] = None, key_params: list = None):
    """Decorator factory for caching"""
    return CacheDecorator(category, ttl, key_params)


class CacheWarmer:
    """Cache warming utility"""
    
    def __init__(self):
        self.symbols = ["BTC", "ETH", "SOL", "BNB", "XRP"]
        self.warming_interval = 300  # 5 minutes
    
    async def warm_cache(self):
        """Warm cache with common symbols"""
        if not cache_manager.enabled:
            return
            
        logger.info("Starting cache warming...")
        
        try:
            from services.market_data_core import get_raw, get_whale, get_liq, get_raw_orderbook
            
            tasks = []
            
            for symbol in self.symbols:
                # Add tasks for each data type
                tasks.extend([
                    get_raw(symbol),
                    get_whale(symbol, limit=10),
                    get_liq(symbol),
                    get_raw_orderbook(symbol, depth=20)
                ])
            
            # Execute all tasks concurrently
            await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info(f"Cache warming completed for {len(self.symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Cache warming error: {e}")
    
    async def start_warming_loop(self):
        """Start continuous cache warming"""
        while True:
            try:
                await self.warm_cache()
                await asyncio.sleep(self.warming_interval)
            except Exception as e:
                logger.error(f"Cache warming loop error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error


# Global cache warmer
cache_warmer = CacheWarmer()


async def initialize_cache():
    """Initialize cache system"""
    await cache_manager.initialize()
    
    # Start cache warming if enabled
    if settings.cache_warming_enabled:
        asyncio.create_task(cache_warmer.start_warming_loop())
        logger.info("Cache warming loop started")


async def cleanup_cache():
    """Cleanup cache system"""
    await cache_manager.close()
