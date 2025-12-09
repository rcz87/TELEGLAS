"""
Performance Optimizer for WS Alert System - Poin 4

Module ini menyediakan optimasi performa untuk high-frequency data processing
termasuk adaptive window sizing, memory management, dan performance monitoring.

Author: TELEGLAS Team
Version: Poin 4.1.0
"""

import time
import logging
import psutil
import threading
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import gc
import asyncio

logger = logging.getLogger("ws_alert.performance_optimizer")


class MemoryPressureLevel(Enum):
    """Memory pressure levels for adaptive management"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PerformanceLevel(Enum):
    """Performance levels based on system load"""
    HIGH_PERFORMANCE = "high_performance"
    BALANCED = "balanced"
    MEMORY_CONSERVATION = "memory_conservation"
    CRITICAL_MODE = "critical_mode"


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    cpu_usage: float = 0.0
    memory_usage_mb: float = 0.0
    memory_percent: float = 0.0
    active_events: int = 0
    processed_events: int = 0
    events_per_second: float = 0.0
    buffer_hit_rate: float = 0.0
    cleanup_frequency: float = 0.0
    last_update: float = field(default_factory=time.time)


@dataclass
class AdaptiveWindowConfig:
    """Adaptive window configuration"""
    base_window: int = 30  # seconds
    min_window: int = 10   # seconds
    max_window: int = 300  # seconds
    performance_threshold: float = 0.8
    memory_threshold: float = 0.85
    
    # Adaptive factors
    high_frequency_factor: float = 0.5  # Reduce window for high frequency
    low_frequency_factor: float = 2.0  # Extend window for low frequency
    memory_pressure_factor: float = 0.3  # Reduce window under memory pressure


class MemoryManager:
    """Advanced memory management for event buffers"""
    
    def __init__(self, max_memory_mb: float = 512.0):
        self.max_memory_mb = max_memory_mb
        self.current_memory_mb = 0.0
        self.memory_pressure_level = MemoryPressureLevel.LOW
        
        # Memory tracking
        self.buffer_sizes: Dict[str, int] = defaultdict(int)
        self.cleanup_threshold = 0.8  # Start cleanup at 80% memory usage
        self.emergency_threshold = 0.95  # Emergency cleanup at 95%
        
        # Cleanup statistics
        self.cleanup_stats = {
            'total_cleanups': 0,
            'emergency_cleanups': 0,
            'memory_freed_mb': 0.0,
            'last_cleanup_time': 0.0
        }
        
        logger.info(f"[PERF] Memory Manager initialized with {max_memory_mb}MB limit")
    
    def check_memory_pressure(self) -> MemoryPressureLevel:
        """Check current memory pressure level"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            self.current_memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = self.current_memory_mb / self.max_memory_mb
            
            if memory_percent >= self.emergency_threshold:
                self.memory_pressure_level = MemoryPressureLevel.CRITICAL
            elif memory_percent >= self.cleanup_threshold:
                self.memory_pressure_level = MemoryPressureLevel.HIGH
            elif memory_percent >= 0.6:
                self.memory_pressure_level = MemoryPressureLevel.MEDIUM
            else:
                self.memory_pressure_level = MemoryPressureLevel.LOW
            
            return self.memory_pressure_level
            
        except Exception as e:
            logger.error(f"[PERF] Error checking memory pressure: {e}")
            return MemoryPressureLevel.LOW
    
    def should_aggressive_cleanup(self) -> bool:
        """Check if aggressive cleanup is needed"""
        pressure = self.check_memory_pressure()
        return pressure in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL]
    
    def perform_cleanup(self, buffers: Dict[str, deque], force: bool = False) -> float:
        """Perform memory cleanup and return memory freed in MB"""
        memory_freed = 0.0
        
        try:
            pressure = self.check_memory_pressure()
            
            if not force and pressure == MemoryPressureLevel.LOW:
                return memory_freed
            
            # Calculate cleanup aggressiveness
            if pressure == MemoryPressureLevel.CRITICAL or force:
                cleanup_ratio = 0.8  # Remove 80% of old events
                self.cleanup_stats['emergency_cleanups'] += 1
            elif pressure == MemoryPressureLevel.HIGH:
                cleanup_ratio = 0.6  # Remove 60% of old events
            else:
                cleanup_ratio = 0.3  # Remove 30% of old events
            
            total_events_before = sum(len(buffer) for buffer in buffers.values())
            
            # Perform cleanup
            for symbol, buffer in buffers.items():
                if len(buffer) <= 1:
                    continue
                
                # Calculate events to remove
                events_to_remove = int(len(buffer) * cleanup_ratio)
                
                # Remove oldest events
                for _ in range(events_to_remove):
                    if buffer:
                        buffer.popleft()
                        memory_freed += 0.001  # Estimate 1KB per event
            
            total_events_after = sum(len(buffer) for buffer in buffers.values())
            events_removed = total_events_before - total_events_after
            
            # Force garbage collection
            gc.collect()
            
            # Update statistics
            self.cleanup_stats['total_cleanups'] += 1
            self.cleanup_stats['memory_freed_mb'] += memory_freed
            self.cleanup_stats['last_cleanup_time'] = time.time()
            
            logger.info(f"[PERF] Memory cleanup: {events_removed} events removed, "
                       f"{memory_freed:.2f}MB freed (pressure: {pressure.value})")
            
            return memory_freed
            
        except Exception as e:
            logger.error(f"[PERF] Error during memory cleanup: {e}")
            return 0.0
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory management statistics"""
        return {
            'current_memory_mb': self.current_memory_mb,
            'max_memory_mb': self.max_memory_mb,
            'memory_usage_percent': (self.current_memory_mb / self.max_memory_mb) * 100,
            'memory_pressure_level': self.memory_pressure_level.value,
            'buffer_sizes': dict(self.buffer_sizes),
            'cleanup_stats': self.cleanup_stats.copy()
        }


class AdaptiveWindowManager:
    """Manages adaptive window sizing based on performance and data characteristics"""
    
    def __init__(self, config: AdaptiveWindowConfig):
        self.config = config
        self.symbol_windows: Dict[str, int] = {}
        self.symbol_frequencies: Dict[str, float] = defaultdict(float)
        self.last_adjustment = time.time()
        self.adjustment_interval = 60  # Adjust every 60 seconds
        
        logger.info(f"[PERF] Adaptive Window Manager initialized")
    
    def update_symbol_frequency(self, symbol: str, events_count: int, time_window: int):
        """Update event frequency for a symbol"""
        if time_window > 0:
            frequency = events_count / time_window  # events per second
            self.symbol_frequencies[symbol] = frequency
    
    def get_adaptive_window(self, symbol: str, base_window: int = None) -> int:
        """Get adaptive window size for a symbol"""
        if base_window is None:
            base_window = self.config.base_window
        
        # Check if symbol has custom window
        if symbol in self.symbol_windows:
            return self.symbol_windows[symbol]
        
        # Calculate adaptive window based on frequency
        frequency = self.symbol_frequencies.get(symbol, 0.0)
        
        if frequency > 10.0:  # High frequency: > 10 events/sec
            adaptive_window = int(base_window * self.config.high_frequency_factor)
        elif frequency < 0.1:  # Low frequency: < 0.1 events/sec
            adaptive_window = int(base_window * self.config.low_frequency_factor)
        else:
            adaptive_window = base_window
        
        # Apply bounds
        adaptive_window = max(self.config.min_window, 
                             min(self.config.max_window, adaptive_window))
        
        return adaptive_window
    
    def adjust_windows(self, performance_metrics: PerformanceMetrics, 
                      memory_pressure: MemoryPressureLevel):
        """Adjust window sizes based on performance and memory pressure"""
        current_time = time.time()
        
        if current_time - self.last_adjustment < self.adjustment_interval:
            return  # Don't adjust too frequently
        
        try:
            # Determine performance level
            if (memory_pressure in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL] or
                performance_metrics.memory_percent > self.config.memory_threshold):
                performance_level = PerformanceLevel.MEMORY_CONSERVATION
            elif (performance_metrics.cpu_usage < self.config.performance_threshold and
                  performance_metrics.memory_percent < 0.7):
                performance_level = PerformanceLevel.HIGH_PERFORMANCE
            else:
                performance_level = PerformanceLevel.BALANCED
            
            # Adjust windows based on performance level
            for symbol in list(self.symbol_windows.keys()):
                current_window = self.symbol_windows[symbol]
                
                if performance_level == PerformanceLevel.MEMORY_CONSERVATION:
                    # Reduce windows to save memory
                    new_window = int(current_window * 0.7)
                elif performance_level == PerformanceLevel.HIGH_PERFORMANCE:
                    # Can use larger windows for better analysis
                    new_window = int(current_window * 1.2)
                else:
                    # Maintain current windows
                    new_window = current_window
                
                # Apply bounds
                new_window = max(self.config.min_window,
                               min(self.config.max_window, new_window))
                
                self.symbol_windows[symbol] = new_window
            
            self.last_adjustment = current_time
            
            logger.debug(f"[PERF] Window adjustment completed: {performance_level.value}")
            
        except Exception as e:
            logger.error(f"[PERF] Error adjusting windows: {e}")
    
    def get_window_stats(self) -> Dict[str, Any]:
        """Get window management statistics"""
        return {
            'symbol_windows': self.symbol_windows.copy(),
            'symbol_frequencies': self.symbol_frequencies.copy(),
            'last_adjustment': self.last_adjustment,
            'config': {
                'base_window': self.config.base_window,
                'min_window': self.config.min_window,
                'max_window': self.config.max_window
            }
        }


class PerformanceMonitor:
    """Real-time performance monitoring and metrics collection"""
    
    def __init__(self, update_interval: float = 5.0):
        self.update_interval = update_interval
        self.metrics = PerformanceMetrics()
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Performance history
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history_size = 100
        
        # Alerts and thresholds
        self.cpu_threshold = 80.0  # %
        self.memory_threshold = 85.0  # %
        self.events_per_second_threshold = 1000.0
        
        logger.info(f"[PERF] Performance Monitor initialized with {update_interval}s interval")
    
    def start_monitoring(self):
        """Start performance monitoring in background thread"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("[PERF] Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        logger.info("[PERF] Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                self._update_metrics()
                self._check_alerts()
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"[PERF] Error in monitoring loop: {e}")
                time.sleep(self.update_interval)
    
    def _update_metrics(self):
        """Update performance metrics"""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1.0)
            memory = psutil.virtual_memory()
            
            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Update metrics
            self.metrics.cpu_usage = cpu_percent
            self.metrics.memory_usage_mb = process_memory.rss / 1024 / 1024
            self.metrics.memory_percent = memory.percent
            self.metrics.last_update = time.time()
            
            # Add to history
            self.metrics_history.append(PerformanceMetrics(**self.metrics.__dict__))
            
            # Limit history size
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history.pop(0)
            
        except Exception as e:
            logger.error(f"[PERF] Error updating metrics: {e}")
    
    def _check_alerts(self):
        """Check for performance alerts"""
        alerts = []
        
        if self.metrics.cpu_usage > self.cpu_threshold:
            alerts.append(f"High CPU usage: {self.metrics.cpu_usage:.1f}%")
        
        if self.metrics.memory_percent > self.memory_threshold:
            alerts.append(f"High memory usage: {self.metrics.memory_percent:.1f}%")
        
        if self.metrics.events_per_second > self.events_per_second_threshold:
            alerts.append(f"High event rate: {self.metrics.events_per_second:.1f} events/sec")
        
        if alerts:
            logger.warning(f"[PERF] Performance alerts: {'; '.join(alerts)}")
    
    def update_event_metrics(self, active_events: int, processed_events: int):
        """Update event-related metrics"""
        current_time = time.time()
        time_diff = current_time - self.metrics.last_update
        
        if time_diff > 0:
            self.metrics.active_events = active_events
            self.metrics.processed_events = processed_events
            self.metrics.events_per_second = processed_events / time_diff
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics"""
        return PerformanceMetrics(**self.metrics.__dict__)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        if not self.metrics_history:
            return {}
        
        # Calculate averages from history
        cpu_avg = sum(m.cpu_usage for m in self.metrics_history) / len(self.metrics_history)
        memory_avg = sum(m.memory_usage_mb for m in self.metrics_history) / len(self.metrics_history)
        
        return {
            'current': self.metrics.__dict__,
            'averages': {
                'cpu_usage': cpu_avg,
                'memory_usage_mb': memory_avg
            },
            'peak': {
                'cpu_usage': max(m.cpu_usage for m in self.metrics_history),
                'memory_usage_mb': max(m.memory_usage_mb for m in self.metrics_history),
                'events_per_second': max(m.events_per_second for m in self.metrics_history)
            },
            'monitoring_active': self.is_monitoring,
            'history_size': len(self.metrics_history)
        }


class PerformanceOptimizer:
    """Main performance optimizer coordinator"""
    
    def __init__(self, max_memory_mb: float = 512.0):
        self.memory_manager = MemoryManager(max_memory_mb)
        self.window_config = AdaptiveWindowConfig()
        self.window_manager = AdaptiveWindowManager(self.window_config)
        self.performance_monitor = PerformanceMonitor()
        
        # Optimization statistics
        self.optimization_stats = {
            'total_optimizations': 0,
            'memory_optimizations': 0,
            'window_adjustments': 0,
            'last_optimization': 0.0
        }
        
        logger.info("[PERF] Performance Optimizer initialized")
    
    def start(self):
        """Start performance optimization"""
        self.performance_monitor.start_monitoring()
        logger.info("[PERF] Performance optimization started")
    
    def stop(self):
        """Stop performance optimization"""
        self.performance_monitor.stop_monitoring()
        logger.info("[PERF] Performance optimization stopped")
    
    def optimize_buffers(self, buffers: Dict[str, deque]) -> Dict[str, Any]:
        """Perform buffer optimization"""
        optimization_result = {
            'memory_cleanup': False,
            'window_adjustment': False,
            'memory_freed_mb': 0.0,
            'adjusted_symbols': 0
        }
        
        try:
            # Get current performance metrics
            metrics = self.performance_monitor.get_current_metrics()
            memory_pressure = self.memory_manager.check_memory_pressure()
            
            # Memory optimization
            if self.memory_manager.should_aggressive_cleanup():
                memory_freed = self.memory_manager.perform_cleanup(buffers)
                if memory_freed > 0:
                    optimization_result['memory_cleanup'] = True
                    optimization_result['memory_freed_mb'] = memory_freed
                    self.optimization_stats['memory_optimizations'] += 1
            
            # Window adjustment
            old_windows = self.window_manager.symbol_windows.copy()
            self.window_manager.adjust_windows(metrics, memory_pressure)
            
            # Check if windows were adjusted
            if old_windows != self.window_manager.symbol_windows:
                optimization_result['window_adjustment'] = True
                optimization_result['adjusted_symbols'] = len(self.window_manager.symbol_windows)
                self.optimization_stats['window_adjustments'] += 1
            
            # Update statistics
            self.optimization_stats['total_optimizations'] += 1
            self.optimization_stats['last_optimization'] = time.time()
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"[PERF] Error during optimization: {e}")
            return optimization_result
    
    def get_optimal_window(self, symbol: str, base_window: int = None) -> int:
        """Get optimal window size for a symbol"""
        return self.window_manager.get_adaptive_window(symbol, base_window)
    
    def update_symbol_activity(self, symbol: str, events_count: int, time_window: int):
        """Update activity for a symbol"""
        self.window_manager.update_symbol_frequency(symbol, events_count, time_window)
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard"""
        return {
            'performance_metrics': self.performance_monitor.get_performance_summary(),
            'memory_stats': self.memory_manager.get_memory_stats(),
            'window_stats': self.window_manager.get_window_stats(),
            'optimization_stats': self.optimization_stats.copy()
        }


# Global performance optimizer instance
_performance_optimizer = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """Get global performance optimizer instance"""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer
