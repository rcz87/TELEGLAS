"""
TELEGLAS GPT API - Analytics Module
Lightweight analytics tracking for API usage monitoring
"""

import json
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from pathlib import Path
import aiofiles
from loguru import logger
from .config import settings


@dataclass
class RequestRecord:
    """Single request record"""
    timestamp: datetime
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    api_key: Optional[str]
    ip_address: Optional[str]
    symbol: Optional[str]
    user_agent: Optional[str]
    error_message: Optional[str] = None


@dataclass
class AggregatedStats:
    """Aggregated statistics for time period"""
    period_start: datetime
    period_end: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_minute: float
    top_endpoints: List[Dict[str, Any]]
    top_symbols: List[Dict[str, Any]]
    error_rate: float
    unique_api_keys: int
    unique_ips: int


class AnalyticsManager:
    """Analytics tracking and aggregation"""
    
    def __init__(self):
        self.enabled = settings.analytics_enabled if hasattr(settings, 'analytics_enabled') else True
        self.storage_path = Path("logs/analytics")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage for recent requests (last 10000)
        self.recent_requests: deque = deque(maxlen=10000)
        
        # Aggregated stats cache
        self.stats_cache: Dict[str, AggregatedStats] = {}
        self.cache_ttl = 60  # 1 minute
        
        # Performance tracking
        self.endpoint_stats = defaultdict(list)
        self.symbol_stats = defaultdict(list)
        self.error_counts = defaultdict(int)
        
        # File settings
        self.daily_file_format = "analytics_{date}.jsonl"
        self.max_file_size_mb = 100
        
    async def track_request(self, record: RequestRecord):
        """Track a single request"""
        if not self.enabled:
            return
            
        try:
            # Add to in-memory storage
            self.recent_requests.append(record)
            
            # Update stats
            self.endpoint_stats[record.endpoint].append(record.response_time_ms)
            if record.symbol:
                self.symbol_stats[record.symbol].append(record.response_time_ms)
            
            if record.status_code >= 400:
                self.error_counts[f"{record.endpoint}:{record.status_code}"] += 1
            
            # Write to file asynchronously
            await self._write_to_file(record)
            
            logger.debug(f"Tracked request: {record.endpoint} - {record.status_code}")
            
        except Exception as e:
            logger.error(f"Analytics tracking error: {e}")
    
    async def _write_to_file(self, record: RequestRecord):
        """Write record to daily file"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            filename = self.daily_file_format.format(date=today)
            filepath = self.storage_path / filename
            
            # Convert record to dict and serialize
            record_dict = asdict(record)
            record_dict['timestamp'] = record.timestamp.isoformat()
            
            # Append to file
            async with aiofiles.open(filepath, 'a') as f:
                await f.write(json.dumps(record_dict, default=str) + '\n')
                
        except Exception as e:
            logger.error(f"File write error: {e}")
    
    async def get_stats(self, period_hours: int = 24) -> AggregatedStats:
        """Get aggregated statistics for time period"""
        cache_key = f"stats_{period_hours}h"
        
        # Check cache
        if cache_key in self.stats_cache:
            cached_time, cached_stats = self.stats_cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_stats
        
        # Calculate stats
        period_start = datetime.now() - timedelta(hours=period_hours)
        period_requests = [
            r for r in self.recent_requests 
            if r.timestamp >= period_start
        ]
        
        if not period_requests:
            stats = AggregatedStats(
                period_start=period_start,
                period_end=datetime.now(),
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time=0,
                p95_response_time=0,
                p99_response_time=0,
                requests_per_minute=0,
                top_endpoints=[],
                top_symbols=[],
                error_rate=0,
                unique_api_keys=0,
                unique_ips=0
            )
        else:
            # Calculate metrics
            response_times = [r.response_time_ms for r in period_requests]
            successful_requests = [r for r in period_requests if r.status_code < 400]
            failed_requests = [r for r in period_requests if r.status_code >= 400]
            
            # Response time percentiles
            sorted_times = sorted(response_times)
            n = len(sorted_times)
            p95_idx = int(n * 0.95)
            p99_idx = int(n * 0.99)
            
            # Top endpoints
            endpoint_counts = defaultdict(int)
            symbol_counts = defaultdict(int)
            api_keys = set()
            ips = set()
            
            for r in period_requests:
                endpoint_counts[r.endpoint] += 1
                if r.symbol:
                    symbol_counts[r.symbol] += 1
                if r.api_key:
                    api_keys.add(r.api_key[:8] + "...")  # Partial key for privacy
                if r.ip_address:
                    ips.add(r.ip_address)
            
            top_endpoints = [
                {"endpoint": ep, "count": count}
                for ep, count in sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ]
            
            top_symbols = [
                {"symbol": sym, "count": count}
                for sym, count in sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ]
            
            # Calculate requests per minute
            minutes_in_period = period_hours * 60
            requests_per_minute = len(period_requests) / minutes_in_period if minutes_in_period > 0 else 0
            
            stats = AggregatedStats(
                period_start=period_start,
                period_end=datetime.now(),
                total_requests=len(period_requests),
                successful_requests=len(successful_requests),
                failed_requests=len(failed_requests),
                avg_response_time=sum(response_times) / len(response_times),
                p95_response_time=sorted_times[p95_idx] if p95_idx < n else 0,
                p99_response_time=sorted_times[p99_idx] if p99_idx < n else 0,
                requests_per_minute=requests_per_minute,
                top_endpoints=top_endpoints,
                top_symbols=top_symbols,
                error_rate=len(failed_requests) / len(period_requests) * 100,
                unique_api_keys=len(api_keys),
                unique_ips=len(ips)
            )
        
        # Cache results
        self.stats_cache[cache_key] = (time.time(), stats)
        
        return stats
    
    async def get_realtime_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics"""
        if not self.recent_requests:
            return {
                "current_rps": 0,
                "active_endpoints": [],
                "active_symbols": [],
                "recent_errors": [],
                "memory_usage_mb": self._get_memory_usage()
            }
        
        # Last 5 minutes
        five_min_ago = datetime.now() - timedelta(minutes=5)
        recent_requests = [
            r for r in self.recent_requests 
            if r.timestamp >= five_min_ago
        ]
        
        # Calculate RPS
        rps = len(recent_requests) / 300  # 5 minutes = 300 seconds
        
        # Active endpoints (last minute)
        one_min_ago = datetime.now() - timedelta(minutes=1)
        active_endpoints = list(set(
            r.endpoint for r in self.recent_requests 
            if r.timestamp >= one_min_ago
        ))
        
        # Active symbols (last minute)
        active_symbols = list(set(
            r.symbol for r in self.recent_requests 
            if r.timestamp >= one_min_ago and r.symbol
        ))
        
        # Recent errors (last 10 minutes)
        ten_min_ago = datetime.now() - timedelta(minutes=10)
        recent_errors = [
            {
                "timestamp": r.timestamp.isoformat(),
                "endpoint": r.endpoint,
                "status_code": r.status_code,
                "error": r.error_message
            }
            for r in self.recent_requests 
            if r.timestamp >= ten_min_ago and r.status_code >= 400
        ][:10]  # Last 10 errors
        
        return {
            "current_rps": round(rps, 2),
            "active_endpoints": active_endpoints,
            "active_symbols": active_symbols,
            "recent_errors": recent_errors,
            "memory_usage_mb": self._get_memory_usage()
        }
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0
    
    async def export_data(self, 
                        start_date: datetime, 
                        end_date: datetime,
                        format: str = "json") -> str:
        """Export analytics data for date range"""
        try:
            all_records = []
            
            # Read daily files
            current_date = start_date.date()
            end_date_only = end_date.date()
            
            while current_date <= end_date_only:
                filename = self.daily_file_format.format(date=current_date.strftime("%Y-%m-%d"))
                filepath = self.storage_path / filename
                
                if filepath.exists():
                    async with aiofiles.open(filepath, 'r') as f:
                        async for line in f:
                            try:
                                record = json.loads(line.strip())
                                record_datetime = datetime.fromisoformat(record['timestamp'])
                                
                                if start_date <= record_datetime <= end_date:
                                    all_records.append(record)
                            except (json.JSONDecodeError, ValueError):
                                continue
                
                current_date += timedelta(days=1)
            
            # Export in requested format
            if format.lower() == "csv":
                return self._export_csv(all_records)
            else:
                return json.dumps(all_records, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Export error: {e}")
            raise
    
    def _export_csv(self, records: List[Dict]) -> str:
        """Export records as CSV"""
        if not records:
            return "timestamp,endpoint,method,status_code,response_time_ms,symbol,ip_address\n"
        
        # CSV header
        headers = ["timestamp", "endpoint", "method", "status_code", "response_time_ms", "symbol", "ip_address"]
        csv_lines = [",".join(headers)]
        
        # Data rows
        for record in records:
            row = [
                record.get("timestamp", ""),
                record.get("endpoint", ""),
                record.get("method", ""),
                str(record.get("status_code", "")),
                str(record.get("response_time_ms", "")),
                record.get("symbol", ""),
                record.get("ip_address", "")
            ]
            csv_lines.append(",".join(f'"{field}"' for field in row))
        
        return "\n".join(csv_lines)
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old analytics files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            for file_path in self.storage_path.glob("analytics_*.jsonl"):
                try:
                    # Extract date from filename
                    date_str = file_path.stem.split("_")[1]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    if file_date < cutoff_date:
                        file_path.unlink()
                        logger.info(f"Deleted old analytics file: {file_path}")
                        
                except (ValueError, IndexError):
                    continue
                    
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get analytics health status"""
        return {
            "enabled": self.enabled,
            "storage_path": str(self.storage_path),
            "recent_requests_count": len(self.recent_requests),
            "cached_stats_count": len(self.stats_cache),
            "endpoint_stats_count": len(self.endpoint_stats),
            "symbol_stats_count": len(self.symbol_stats),
            "memory_usage_mb": self._get_memory_usage()
        }


# Global analytics instance
analytics_manager = AnalyticsManager()


async def initialize_analytics():
    """Initialize analytics system"""
    if not analytics_manager.enabled:
        logger.info("Analytics disabled by configuration")
        return
    
    logger.info("Analytics initialized")
    
    # Start cleanup task (run daily)
    asyncio.create_task(_daily_cleanup_task())


async def _daily_cleanup_task():
    """Daily cleanup task"""
    while True:
        try:
            await asyncio.sleep(24 * 60 * 60)  # 24 hours
            await analytics_manager.cleanup_old_data()
        except Exception as e:
            logger.error(f"Daily cleanup error: {e}")
            await asyncio.sleep(3600)  # Wait 1 hour on error


class AnalyticsMiddleware:
    """FastAPI middleware for analytics tracking"""
    
    async def __call__(self, request, call_next):
        """Track request through middleware"""
        if not analytics_manager.enabled:
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Extract request info
        endpoint = request.url.path
        method = request.method
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        api_key = None
        
        # Extract API key from header
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:41]  # First 34 characters for privacy
        
        # Extract symbol from query parameters
        symbol = request.query_params.get("symbol")
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Create record
            record = RequestRecord(
                timestamp=datetime.now(),
                endpoint=endpoint,
                method=method,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                api_key=api_key,
                ip_address=client_ip,
                symbol=symbol,
                user_agent=user_agent
            )
            
            # Track asynchronously (don't block response)
            asyncio.create_task(analytics_manager.track_request(record))
            
            return response
            
        except Exception as e:
            # Track error
            response_time_ms = (time.time() - start_time) * 1000
            
            record = RequestRecord(
                timestamp=datetime.now(),
                endpoint=endpoint,
                method=method,
                status_code=500,
                response_time_ms=response_time_ms,
                api_key=api_key,
                ip_address=client_ip,
                symbol=symbol,
                user_agent=user_agent,
                error_message=str(e)
            )
            
            asyncio.create_task(analytics_manager.track_request(record))
            raise
