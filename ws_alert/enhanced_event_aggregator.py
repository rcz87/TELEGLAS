"""
Enhanced Event Aggregator for WS Alert System - Poin 4

Modul ini menyediakan event aggregator yang dioptimalkan untuk high-frequency data
dengan adaptive window sizing, memory management, dan performance monitoring.

Author: TELEGLAS Team
Version: Poin 4.2.0
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
import asyncio

from .performance_optimizer import get_performance_optimizer, PerformanceMetrics, MemoryPressureLevel
from .event_aggregator import EventAggregator

logger = logging.getLogger("ws_alert.enhanced_aggregator")


@dataclass
class EnhancedBufferStats:
    """Enhanced buffer statistics with performance metrics"""
    symbol: str
    liquidation_count: int = 0
    trade_count: int = 0
    total_events: int = 0
    avg_events_per_second: float = 0.0
    peak_events_per_second: float = 0.0
    memory_usage_mb: float = 0.0
    window_size: int = 30
    last_cleanup: float = 0.0
    buffer_efficiency: float = 0.0  # Hit rate / total requests


@dataclass
class AdaptiveBuffer:
    """Adaptive buffer with performance optimization"""
    symbol: str
    liquidations: deque = field(default_factory=deque)
    trades: deque = field(default_factory=deque)
    window_size: int = 30
    last_access: float = field(default_factory=time.time)
    access_count: int = 0
    frequency: float = 0.0  # events per second
    
    # Performance metrics
    hit_count: int = 0
    miss_count: int = 0
    cleanup_count: int = 0
    
    def update_access(self):
        """Update access statistics"""
        current_time = time.time()
        time_diff = current_time - self.last_access
        
        if time_diff > 0:
            self.frequency = self.access_count / time_diff
        
        self.last_access = current_time
        self.access_count += 1
        self.hit_count += 1
    
    def get_efficiency(self) -> float:
        """Get buffer efficiency (hit rate)"""
        total_requests = self.hit_count + self.miss_count
        if total_requests == 0:
            return 0.0
        return self.hit_count / total_requests
    
    def get_memory_estimate(self) -> float:
        """Estimate memory usage in MB"""
        total_events = len(self.liquidations) + len(self.trades)
        return total_events * 0.001  # Estimate 1KB per event


class EnhancedEventAggregator:
    """
    Enhanced Event Aggregator dengan performance optimization
    
    Fitur:
    - Adaptive window sizing berdasarkan frequency dan memory pressure
    - Advanced memory management dengan automatic cleanup
    - Real-time performance monitoring
    - Efficient buffer management dengan LRU-like access tracking
    """
    
    def __init__(self, base_window_seconds: int = 30, max_memory_mb: float = 512.0):
        self.base_window_seconds = base_window_seconds
        self.lock = threading.RLock()  # Use RLock for nested locking
        
        # Enhanced buffers dengan performance tracking
        self.enhanced_buffers: Dict[str, AdaptiveBuffer] = {}
        
        # Performance optimizer
        self.performance_optimizer = get_performance_optimizer()
        self.performance_optimizer.start()
        
        # Statistics dan monitoring
        self.stats = {
            'events_processed': 0,
            'liquidations_processed': 0,
            'trades_processed': 0,
            'memory_cleanups': 0,
            'window_adjustments': 0,
            'peak_memory_mb': 0.0,
            'avg_processing_time_ms': 0.0
        }
        
        # Performance tracking
        self.performance_history: List[PerformanceMetrics] = []
        self.last_optimization = time.time()
        self.optimization_interval = 30  # seconds
        
        # Adaptive thresholds
        self.adaptive_thresholds = {
            'high_frequency_symbols': 15,  # symbols
            'memory_pressure_threshold': 0.8,
            'cleanup_interval': 60,  # seconds
            'max_events_per_buffer': 1000
        }
        
        logger.info(f"[ENH_AGG] Enhanced Event Aggregator initialized")
        logger.info(f"[ENH_AGG] Base window: {base_window_seconds}s, Max memory: {max_memory_mb}MB")
    
    def add_liquidation_event(self, event: Dict[str, Any]) -> bool:
        """
        Add liquidation event dengan performance optimization
        """
        start_time = time.time()
        
        try:
            with self.lock:
                # Validate event structure
                if not self._validate_liquidation_event(event):
                    logger.warning("[ENH_AGG] Invalid liquidation event structure")
                    return False
                
                symbol = event.get('symbol', '')
                if not symbol:
                    logger.warning("[ENH_AGG] Liquidation event missing symbol")
                    return False
                
                # Get or create enhanced buffer
                buffer = self._get_or_create_buffer(symbol)
                
                # Add timestamp if missing
                if 'timestamp' not in event:
                    event['timestamp'] = time.time()
                
                # Add to buffer with size management
                self._add_to_buffer_with_size_check(buffer.liquidations, event, symbol)
                
                # Update statistics
                buffer.update_access()
                self.stats['liquidations_processed'] += 1
                self.stats['events_processed'] += 1
                
                # Update frequency
                self.performance_optimizer.update_symbol_activity(
                    symbol, len(buffer.liquidations), buffer.window_size
                )
                
                # Periodic optimization
                self._check_and_optimize()
                
                processing_time = (time.time() - start_time) * 1000
                self._update_processing_time(processing_time)
                
                logger.debug(f"[ENH_AGG] Added liquidation: {symbol} ${event.get('volUsd', 0):,.0f} "
                           f"({processing_time:.2f}ms)")
                
                return True
                
        except Exception as e:
            logger.error(f"[ENH_AGG] Error adding liquidation event: {e}")
            return False
    
    def add_trade_event(self, event: Dict[str, Any]) -> bool:
        """
        Add trade event dengan performance optimization
        """
        start_time = time.time()
        
        try:
            with self.lock:
                # Validate event structure
                if not self._validate_trade_event(event):
                    logger.warning("[ENH_AGG] Invalid trade event structure")
                    return False
                
                symbol = event.get('symbol', '')
                if not symbol:
                    logger.warning("[ENH_AGG] Trade event missing symbol")
                    return False
                
                # Get or create enhanced buffer
                buffer = self._get_or_create_buffer(symbol)
                
                # Add timestamp if missing
                if 'timestamp' not in event:
                    event['timestamp'] = time.time()
                
                # Add to buffer with size management
                self._add_to_buffer_with_size_check(buffer.trades, event, symbol)
                
                # Update statistics
                buffer.update_access()
                self.stats['trades_processed'] += 1
                self.stats['events_processed'] += 1
                
                # Update frequency
                self.performance_optimizer.update_symbol_activity(
                    symbol, len(buffer.trades), buffer.window_size
                )
                
                # Periodic optimization
                self._check_and_optimize()
                
                processing_time = (time.time() - start_time) * 1000
                self._update_processing_time(processing_time)
                
                logger.debug(f"[ENH_AGG] Added trade: {symbol} ${event.get('volUsd', 0):,.0f} "
                           f"({processing_time:.2f}ms)")
                
                return True
                
        except Exception as e:
            logger.error(f"[ENH_AGG] Error adding trade event: {e}")
            return False
    
    def get_liq_window(self, symbol: str, window_sec: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get liquidation events dengan adaptive window sizing
        """
        try:
            with self.lock:
                buffer = self.enhanced_buffers.get(symbol)
                if not buffer:
                    buffer.miss_count += 1
                    return []
                
                buffer.update_access()
                
                # Get adaptive window size
                if window_sec is None:
                    window_sec = self.performance_optimizer.get_optimal_window(
                        symbol, self.base_window_seconds
                    )
                    buffer.window_size = window_sec
                
                current_time = time.time()
                cutoff_time = current_time - window_sec
                
                # Filter events by window time
                filtered_events = [
                    event for event in buffer.liquidations
                    if event.get('timestamp', 0) >= cutoff_time
                ]
                
                logger.debug(f"[ENH_AGG] Got {len(filtered_events)} liquidation events for {symbol} "
                           f"in {window_sec}s window (adaptive)")
                
                return filtered_events
                
        except Exception as e:
            logger.error(f"[ENH_AGG] Error getting liquidation window: {e}")
            return []
    
    def get_trade_window(self, symbol: str, window_sec: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get trade events dengan adaptive window sizing
        """
        try:
            with self.lock:
                buffer = self.enhanced_buffers.get(symbol)
                if not buffer:
                    buffer.miss_count += 1
                    return []
                
                buffer.update_access()
                
                # Get adaptive window size
                if window_sec is None:
                    window_sec = self.performance_optimizer.get_optimal_window(
                        symbol, self.base_window_seconds
                    )
                    buffer.window_size = window_sec
                
                current_time = time.time()
                cutoff_time = current_time - window_sec
                
                # Filter events by window time
                filtered_events = [
                    event for event in buffer.trades
                    if event.get('timestamp', 0) >= cutoff_time
                ]
                
                logger.debug(f"[ENH_AGG] Got {len(filtered_events)} trade events for {symbol} "
                           f"in {window_sec}s window (adaptive)")
                
                return filtered_events
                
        except Exception as e:
            logger.error(f"[ENH_AGG] Error getting trade window: {e}")
            return []
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics dengan performance metrics
        """
        try:
            with self.lock:
                # Basic stats
                base_stats = self.stats.copy()
                
                # Buffer statistics
                buffer_stats = {}
                total_memory_mb = 0.0
                total_events = 0
                
                for symbol, buffer in self.enhanced_buffers.items():
                    stats = EnhancedBufferStats(
                        symbol=symbol,
                        liquidation_count=len(buffer.liquidations),
                        trade_count=len(buffer.trades),
                        total_events=len(buffer.liquidations) + len(buffer.trades),
                        avg_events_per_second=buffer.frequency,
                        peak_events_per_second=buffer.frequency,  # Simplified
                        memory_usage_mb=buffer.get_memory_estimate(),
                        window_size=buffer.window_size,
                        last_cleanup=buffer.last_access,
                        buffer_efficiency=buffer.get_efficiency()
                    )
                    
                    buffer_stats[symbol] = stats
                    total_memory_mb += stats.memory_usage_mb
                    total_events += stats.total_events
                
                # Performance dashboard
                performance_dashboard = self.performance_optimizer.get_performance_dashboard()
                
                # System health
                system_health = {
                    'total_buffers': len(self.enhanced_buffers),
                    'total_memory_mb': total_memory_mb,
                    'total_events': total_events,
                    'avg_events_per_buffer': total_events / max(len(self.enhanced_buffers), 1),
                    'memory_pressure': self.performance_optimizer.memory_manager.memory_pressure_level.value,
                    'last_optimization': self.last_optimization
                }
                
                return {
                    'basic_stats': base_stats,
                    'buffer_stats': buffer_stats,
                    'performance_dashboard': performance_dashboard,
                    'system_health': system_health,
                    'adaptive_thresholds': self.adaptive_thresholds
                }
                
        except Exception as e:
            logger.error(f"[ENH_AGG] Error getting enhanced stats: {e}")
            return {}
    
    def _get_or_create_buffer(self, symbol: str) -> AdaptiveBuffer:
        """Get or create enhanced buffer for symbol"""
        if symbol not in self.enhanced_buffers:
            # Get optimal window size
            window_size = self.performance_optimizer.get_optimal_window(
                symbol, self.base_window_seconds
            )
            
            self.enhanced_buffers[symbol] = AdaptiveBuffer(
                symbol=symbol,
                window_size=window_size
            )
        
        return self.enhanced_buffers[symbol]
    
    def _add_to_buffer_with_size_check(self, buffer: deque, event: Dict[str, Any], symbol: str):
        """Add event to buffer with size management"""
        buffer.append(event)
        
        # Check if buffer exceeds maximum size
        max_events = self.adaptive_thresholds['max_events_per_buffer']
        if len(buffer) > max_events:
            # Remove oldest events to maintain size
            events_to_remove = len(buffer) - max_events
            for _ in range(events_to_remove):
                if buffer:
                    buffer.popleft()
            
            logger.debug(f"[ENH_AGG] Buffer size management: removed {events_to_remove} "
                        f"old events for {symbol}")
    
    def _check_and_optimize(self):
        """Check and perform optimization if needed"""
        current_time = time.time()
        
        if current_time - self.last_optimization < self.optimization_interval:
            return
        
        try:
            # Prepare buffers for optimization
            all_buffers = {}
            for symbol, buffer in self.enhanced_buffers.items():
                # Combine liquidations and trades for optimization
                combined_buffer = deque(list(buffer.liquidations) + list(buffer.trades))
                all_buffers[symbol] = combined_buffer
            
            # Perform optimization
            optimization_result = self.performance_optimizer.optimize_buffers(all_buffers)
            
            # Update statistics
            if optimization_result['memory_cleanup']:
                self.stats['memory_cleanups'] += 1
            
            if optimization_result['window_adjustment']:
                self.stats['window_adjustments'] += 1
                # Update window sizes in buffers
                for symbol, new_window in self.performance_optimizer.window_manager.symbol_windows.items():
                    if symbol in self.enhanced_buffers:
                        self.enhanced_buffers[symbol].window_size = new_window
            
            # Update peak memory usage
            current_memory = self.performance_optimizer.memory_manager.current_memory_mb
            if current_memory > self.stats['peak_memory_mb']:
                self.stats['peak_memory_mb'] = current_memory
            
            self.last_optimization = current_time
            
            logger.debug(f"[ENH_AGG] Optimization completed: {optimization_result}")
            
        except Exception as e:
            logger.error(f"[ENH_AGG] Error during optimization: {e}")
    
    def _update_processing_time(self, processing_time_ms: float):
        """Update average processing time"""
        current_avg = self.stats['avg_processing_time_ms']
        count = self.stats['events_processed']
        
        if count == 1:
            self.stats['avg_processing_time_ms'] = processing_time_ms
        else:
            # Rolling average
            self.stats['avg_processing_time_ms'] = (
                (current_avg * (count - 1) + processing_time_ms) / count
            )
    
    def _validate_liquidation_event(self, event: Dict[str, Any]) -> bool:
        """Validate liquidation event structure"""
        required_fields = ['symbol', 'volUsd', 'price', 'side']
        return all(field in event for field in required_fields)
    
    def _validate_trade_event(self, event: Dict[str, Any]) -> bool:
        """Validate trade event structure"""
        required_fields = ['symbol', 'volUsd', 'price', 'side']
        return all(field in event for field in required_fields)
    
    def cleanup_inactive_buffers(self, max_age_hours: int = 1):
        """Clean up inactive buffers to free memory"""
        try:
            with self.lock:
                current_time = time.time()
                cutoff_time = current_time - (max_age_hours * 3600)
                
                inactive_symbols = []
                for symbol, buffer in self.enhanced_buffers.items():
                    if buffer.last_access < cutoff_time:
                        inactive_symbols.append(symbol)
                
                for symbol in inactive_symbols:
                    del self.enhanced_buffers[symbol]
                    logger.info(f"[ENH_AGG] Cleaned up inactive buffer: {symbol}")
                
                if inactive_symbols:
                    logger.info(f"[ENH_AGG] Cleaned up {len(inactive_symbols)} inactive buffers")
                
        except Exception as e:
            logger.error(f"[ENH_AGG] Error cleaning up inactive buffers: {e}")
    
    def get_active_symbols(self, window_seconds: int = 300) -> List[str]:
        """
        Get list of active symbols dalam window waktu tertentu
        """
        try:
            with self.lock:
                current_time = time.time()
                cutoff_time = current_time - window_seconds
                
                active_symbols = []
                for symbol, buffer in self.enhanced_buffers.items():
                    # Check if buffer has recent activity
                    if (buffer.last_access >= cutoff_time and 
                        (len(buffer.liquidations) > 0 or len(buffer.trades) > 0)):
                        active_symbols.append(symbol)
                
                return sorted(active_symbols)
                
        except Exception as e:
            logger.error(f"[ENH_AGG] Error getting active symbols: {e}")
            return []
    
    def force_optimization(self):
        """Force immediate optimization"""
        try:
            with self.lock:
                # Prepare all buffers
                all_buffers = {}
                for symbol, buffer in self.enhanced_buffers.items():
                    combined_buffer = deque(list(buffer.liquidations) + list(buffer.trades))
                    all_buffers[symbol] = combined_buffer
                
                # Force optimization
                result = self.performance_optimizer.optimize_buffers(all_buffers)
                
                logger.info(f"[ENH_AGG] Force optimization completed: {result}")
                return result
                
        except Exception as e:
            logger.error(f"[ENH_AGG] Error during force optimization: {e}")
            return {}
    
    def reset_stats(self):
        """Reset statistics counters"""
        with self.lock:
            self.stats = {
                'events_processed': 0,
                'liquidations_processed': 0,
                'trades_processed': 0,
                'memory_cleanups': 0,
                'window_adjustments': 0,
                'peak_memory_mb': 0.0,
                'avg_processing_time_ms': 0.0
            }
            
            # Reset buffer stats
            for buffer in self.enhanced_buffers.values():
                buffer.hit_count = 0
                buffer.miss_count = 0
                buffer.cleanup_count = 0
            
            logger.info("[ENH_AGG] Enhanced aggregator stats reset")
    
    def shutdown(self):
        """Cleanup and shutdown"""
        try:
            # Stop performance optimizer
            self.performance_optimizer.stop()
            
            # Clear buffers
            with self.lock:
                self.enhanced_buffers.clear()
            
            logger.info("[ENH_AGG] Enhanced Event Aggregator shutdown completed")
            
        except Exception as e:
            logger.error(f"[ENH_AGG] Error during shutdown: {e}")


# Global enhanced event aggregator instance
_enhanced_event_aggregator = None


def get_enhanced_event_aggregator() -> EnhancedEventAggregator:
    """Get global enhanced event aggregator instance"""
    global _enhanced_event_aggregator
    if _enhanced_event_aggregator is None:
        _enhanced_event_aggregator = EnhancedEventAggregator()
    return _enhanced_event_aggregator
