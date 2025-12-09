"""
Event Aggregator untuk WS Alert Bot - Stage 4 Tahap 1

Modul ini menyediakan layer untuk mengumpulkan event WebSocket dalam window waktu pendek.
Ini adalah komponen dasar untuk Global Radar Mode.

Author: TELEGLAS Team
Version: Stage 4.1.0
"""

import time
import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from threading import Lock

logger = logging.getLogger("ws_alert.aggregator")


class EventAggregator:
    """
    Event Aggregator untuk mengumpulkan dan mengelola event WebSocket
    dalam window waktu tertentu (default 30 detik)
    
    Fungsi:
    - Buffer liquidation events per symbol
    - Buffer whale trade events per symbol  
    - Otomatis cleanup event lama
    - Thread-safe operations
    """
    
    def __init__(self, window_seconds: int = 30):
        """
        Initialize Event Aggregator
        
        Args:
            window_seconds: Window time in seconds (default: 30)
        """
        self.window_seconds = window_seconds
        self.lock = Lock()
        
        # Buffer storage per symbol
        self.buffer_liquidations: Dict[str, deque] = defaultdict(deque)
        self.buffer_trades: Dict[str, deque] = defaultdict(deque)
        
        # Statistics
        self.stats = {
            'liquidations_received': 0,
            'trades_received': 0,
            'liquidations_cleaned': 0,
            'trades_cleaned': 0
        }
        
        logger.info(f"[RADAR] Event Aggregator initialized with {window_seconds}s window")
    
    def add_liquidation_event(self, event: Dict[str, Any]) -> bool:
        """
        Add liquidation event to buffer
        
        Args:
            event: Liquidation event data
            
        Returns:
            True if event added successfully, False if invalid
        """
        try:
            with self.lock:
                # Validate event structure
                if not self._validate_liquidation_event(event):
                    logger.warning("[RADAR] Invalid liquidation event structure")
                    return False
                
                symbol = event.get('symbol', '')
                if not symbol:
                    logger.warning("[RADAR] Liquidation event missing symbol")
                    return False
                
                # Add timestamp if missing
                if 'timestamp' not in event:
                    event['timestamp'] = time.time()
                
                # Add to buffer
                self.buffer_liquidations[symbol].append(event)
                self.stats['liquidations_received'] += 1
                
                logger.debug(f"[RADAR] Added liquidation event: {symbol} ${event.get('volUsd', 0):,.0f}")
                
                # Cleanup old events
                self._cleanup_liquidation_events(symbol)
                
                return True
                
        except Exception as e:
            logger.error(f"[RADAR] Error adding liquidation event: {e}")
            return False
    
    def add_trade_event(self, event: Dict[str, Any]) -> bool:
        """
        Add futures trade event to buffer
        
        Args:
            event: Trade event data
            
        Returns:
            True if event added successfully, False if invalid
        """
        try:
            with self.lock:
                # Validate event structure
                if not self._validate_trade_event(event):
                    logger.warning("[RADAR] Invalid trade event structure")
                    return False
                
                symbol = event.get('symbol', '')
                if not symbol:
                    logger.warning("[RADAR] Trade event missing symbol")
                    return False
                
                # Add timestamp if missing
                if 'timestamp' not in event:
                    event['timestamp'] = time.time()
                
                # Add to buffer
                self.buffer_trades[symbol].append(event)
                self.stats['trades_received'] += 1
                
                logger.debug(f"[RADAR] Added trade event: {symbol} ${event.get('volUsd', 0):,.0f}")
                
                # Cleanup old events
                self._cleanup_trade_events(symbol)
                
                return True
                
        except Exception as e:
            logger.error(f"[RADAR] Error adding trade event: {e}")
            return False
    
    def get_liq_window(self, symbol: str, window_sec: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get liquidation events dalam window waktu tertentu
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            window_sec: Window seconds (default: use instance window)
            
        Returns:
            List of liquidation events dalam window
        """
        try:
            with self.lock:
                if window_sec is None:
                    window_sec = self.window_seconds
                
                current_time = time.time()
                cutoff_time = current_time - window_sec
                
                # Get events for symbol
                events = list(self.buffer_liquidations.get(symbol, []))
                
                # Filter by window time
                filtered_events = [
                    event for event in events
                    if event.get('timestamp', 0) >= cutoff_time
                ]
                
                logger.debug(f"[RADAR] Got {len(filtered_events)} liquidation events for {symbol} in {window_sec}s window")
                
                return filtered_events
                
        except Exception as e:
            logger.error(f"[RADAR] Error getting liquidation window: {e}")
            return []
    
    def get_trade_window(self, symbol: str, window_sec: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get trade events dalam window waktu tertentu
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            window_sec: Window seconds (default: use instance window)
            
        Returns:
            List of trade events dalam window
        """
        try:
            with self.lock:
                if window_sec is None:
                    window_sec = self.window_seconds
                
                current_time = time.time()
                cutoff_time = current_time - window_sec
                
                # Get events for symbol
                events = list(self.buffer_trades.get(symbol, []))
                
                # Filter by window time
                filtered_events = [
                    event for event in events
                    if event.get('timestamp', 0) >= cutoff_time
                ]
                
                logger.debug(f"[RADAR] Got {len(filtered_events)} trade events for {symbol} in {window_sec}s window")
                
                return filtered_events
                
        except Exception as e:
            logger.error(f"[RADAR] Error getting trade window: {e}")
            return []
    
    def clear_old_events(self, max_age_seconds: Optional[int] = None):
        """
        Clean up old events dari semua buffer
        
        Args:
            max_age_seconds: Maximum age for events (default: 2 * window_seconds)
        """
        try:
            with self.lock:
                if max_age_seconds is None:
                    max_age_seconds = self.window_seconds * 2
                
                current_time = time.time()
                cutoff_time = current_time - max_age_seconds
                
                # Cleanup liquidation events
                total_liq_cleaned = 0
                for symbol, events in self.buffer_liquidations.items():
                    original_count = len(events)
                    
                    # Remove old events
                    while events and events[0].get('timestamp', 0) < cutoff_time:
                        events.popleft()
                        total_liq_cleaned += 1
                    
                    # Clean empty buffers
                    if len(events) == 0:
                        del self.buffer_liquidations[symbol]
                
                # Cleanup trade events
                total_trade_cleaned = 0
                for symbol, events in self.buffer_trades.items():
                    original_count = len(events)
                    
                    # Remove old events
                    while events and events[0].get('timestamp', 0) < cutoff_time:
                        events.popleft()
                        total_trade_cleaned += 1
                    
                    # Clean empty buffers
                    if len(events) == 0:
                        del self.buffer_trades[symbol]
                
                self.stats['liquidations_cleaned'] += total_liq_cleaned
                self.stats['trades_cleaned'] += total_trade_cleaned
                
                if total_liq_cleaned > 0 or total_trade_cleaned > 0:
                    logger.info(f"[RADAR] Cleaned up {total_liq_cleaned} liquidations, {total_trade_cleaned} trades")
                
        except Exception as e:
            logger.error(f"[RADAR] Error in clear_old_events: {e}")
    
    def get_active_symbols(self) -> List[str]:
        """
        Get list of symbols yang memiliki events aktif
        
        Returns:
            List of active symbols
        """
        try:
            with self.lock:
                symbols = set()
                symbols.update(self.buffer_liquidations.keys())
                symbols.update(self.buffer_trades.keys())
                return list(symbols)
                
        except Exception as e:
            logger.error(f"[RADAR] Error getting active symbols: {e}")
            return []
    
    def get_buffer_stats(self) -> Dict[str, Any]:
        """
        Get statistics tentang buffer aggregator
        
        Returns:
            Dictionary dengan buffer statistics
        """
        try:
            with self.lock:
                stats = self.stats.copy()
                
                # Count active events per symbol
                liq_per_symbol = {symbol: len(events) for symbol, events in self.buffer_liquidations.items()}
                trade_per_symbol = {symbol: len(events) for symbol, events in self.buffer_trades.items()}
                
                stats.update({
                    'active_symbols': len(self.get_active_symbols()),
                    'symbols_with_liquidations': len(self.buffer_liquidations),
                    'symbols_with_trades': len(self.buffer_trades),
                    'total_liquidation_events': sum(len(events) for events in self.buffer_liquidations.values()),
                    'total_trade_events': sum(len(events) for events in self.buffer_trades.values()),
                    'liquidations_per_symbol': liq_per_symbol,
                    'trades_per_symbol': trade_per_symbol
                })
                
                return stats
                
        except Exception as e:
            logger.error(f"[RADAR] Error getting buffer stats: {e}")
            return {}
    
    def _validate_liquidation_event(self, event: Dict[str, Any]) -> bool:
        """Validate liquidation event structure"""
        required_fields = ['symbol', 'volUsd', 'price', 'side']
        return all(field in event for field in required_fields)
    
    def _validate_trade_event(self, event: Dict[str, Any]) -> bool:
        """Validate trade event structure"""
        required_fields = ['symbol', 'volUsd', 'price', 'side']
        return all(field in event for field in required_fields)
    
    def _cleanup_liquidation_events(self, symbol: str):
        """Cleanup old liquidation events untuk specific symbol"""
        try:
            current_time = time.time()
            cutoff_time = current_time - self.window_seconds
            
            events = self.buffer_liquidations.get(symbol, deque())
            original_count = len(events)
            
            # Remove old events
            while events and events[0].get('timestamp', 0) < cutoff_time:
                events.popleft()
                self.stats['liquidations_cleaned'] += 1
            
            cleaned = original_count - len(events)
            if cleaned > 0:
                logger.debug(f"[RADAR] Cleaned {cleaned} old liquidation events for {symbol}")
                
        except Exception as e:
            logger.error(f"[RADAR] Error in _cleanup_liquidation_events: {e}")
    
    def _cleanup_trade_events(self, symbol: str):
        """Cleanup old trade events untuk specific symbol"""
        try:
            current_time = time.time()
            cutoff_time = current_time - self.window_seconds
            
            events = self.buffer_trades.get(symbol, deque())
            original_count = len(events)
            
            # Remove old events
            while events and events[0].get('timestamp', 0) < cutoff_time:
                events.popleft()
                self.stats['trades_cleaned'] += 1
            
            cleaned = original_count - len(events)
            if cleaned > 0:
                logger.debug(f"[RADAR] Cleaned {cleaned} old trade events for {symbol}")
                
        except Exception as e:
            logger.error(f"[RADAR] Error in _cleanup_trade_events: {e}")
    
    def reset_stats(self):
        """Reset statistics counters"""
        with self.lock:
            self.stats = {
                'liquidations_received': 0,
                'trades_received': 0,
                'liquidations_cleaned': 0,
                'trades_cleaned': 0
            }
            logger.info("[RADAR] Event aggregator stats reset")


# Global instance
event_aggregator = EventAggregator()


def get_event_aggregator() -> EventAggregator:
    """Get global event aggregator instance"""
    return event_aggregator
