"""
Liquidation Storm Detector untuk WS Alert Bot - Stage 4 Tahap 2

Modul ini mendeteksi akumulasi liquidation besar dalam window waktu tertentu.
Ini adalah komponen kedua untuk Global Radar Mode.

Author: TELEGLAS Team
Version: Stage 4.2.0
"""

import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from .event_aggregator import get_event_aggregator
from .config import alert_settings

logger = logging.getLogger("ws_alert.storm_detector")


@dataclass
class StormInfo:
    """Data structure untuk liquidation storm information"""
    symbol: str
    total_usd: float
    side: str  # "long_liq" or "short_liq"
    count: int
    window: int
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy serialization"""
        return {
            "symbol": self.symbol,
            "total_usd": self.total_usd,
            "side": self.side,
            "count": self.count,
            "window": self.window,
            "timestamp": self.timestamp
        }


class LiquidationStormDetector:
    """
    Liquidation Storm Detector untuk mendeteksi akumulasi liquidation
    yang signifikan dalam window waktu tertentu.
    
    Fungsi:
    - Menganalisis liquidation events dalam window time
    - Group berdasarkan side (long/short)
    - Deteksi storm berdasarkan threshold dan count
    - Thread-safe operations
    """
    
    def __init__(self, window_seconds: int = 30):
        """
        Initialize Liquidation Storm Detector
        
        Args:
            window_seconds: Window time in seconds (default: 30)
        """
        self.window_seconds = window_seconds
        self.aggregator = get_event_aggregator()
        
        # Storm thresholds per symbol group (bisa di-override dari config)
        self.storm_thresholds = {
            "MAJORS": {
                "threshold_usd": 2000000,    # 2M USD
                "min_count": 3,
                "cooldown_sec": 300         # 5 menit
            },
            "LARGE_CAP": {
                "threshold_usd": 1000000,    # 1M USD
                "min_count": 2,
                "cooldown_sec": 450         # 7.5 menit
            },
            "MID_CAP": {
                "threshold_usd": 500000,     # 500k USD
                "min_count": 2,
                "cooldown_sec": 600         # 10 menit
            }
        }
        
        # Track last storm detection per symbol untuk cooldown
        self.last_storm_detection: Dict[str, float] = {}
        
        logger.info(f"[RADAR] Liquidation Storm Detector initialized with {window_seconds}s window")
    
    def check_storm(self, symbol: str) -> Optional[StormInfo]:
        """
        Check untuk liquidation storm pada symbol tertentu
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            
        Returns:
            StormInfo jika storm terdeteksi, None jika tidak
        """
        try:
            # Check cooldown dulu
            if self._is_in_cooldown(symbol):
                logger.debug(f"[RADAR] {symbol} still in storm cooldown")
                return None
            
            # Get liquidation events dari aggregator
            liquidation_events = self.aggregator.get_liq_window(symbol, self.window_seconds)
            
            if not liquidation_events:
                logger.debug(f"[RADAR] No liquidation events for {symbol}")
                return None
            
            # Group events berdasarkan side
            long_liquidations = []
            short_liquidations = []
            
            for event in liquidation_events:
                side = event.get('side', 0)
                if side == 1:  # Long liquidation (side 1 = buy)
                    long_liquidations.append(event)
                elif side == 2:  # Short liquidation (side 2 = sell)
                    short_liquidations.append(event)
            
            # Analisis long liquidations
            long_storm = self._analyze_side_liquidations(
                symbol, long_liquidations, "long_liq"
            )
            
            # Analisis short liquidations
            short_storm = self._analyze_side_liquidations(
                symbol, short_liquidations, "short_liq"
            )
            
            # Pilih storm yang lebih signifikan (total USD lebih besar)
            storm_info = None
            if long_storm and short_storm:
                storm_info = long_storm if long_storm.total_usd > short_storm.total_usd else short_storm
            elif long_storm:
                storm_info = long_storm
            elif short_storm:
                storm_info = short_storm
            
            # Update cooldown jika storm terdeteksi
            if storm_info:
                self.last_storm_detection[symbol] = storm_info.timestamp
                logger.info(f"[RADAR] Liquidation storm detected: {storm_info.symbol} {storm_info.side} ${storm_info.total_usd:,.0f}")
            
            return storm_info
            
        except Exception as e:
            logger.error(f"[RADAR] Error checking storm for {symbol}: {e}")
            return None
    
    def check_multiple_symbols(self, symbols: List[str]) -> List[StormInfo]:
        """
        Check storm untuk multiple symbols
        
        Args:
            symbols: List of symbols to check
            
        Returns:
            List of detected storms
        """
        detected_storms = []
        
        for symbol in symbols:
            try:
                storm = self.check_storm(symbol)
                if storm:
                    detected_storms.append(storm)
            except Exception as e:
                logger.error(f"[RADAR] Error checking storm for {symbol}: {e}")
                continue
        
        return detected_storms
    
    def get_storm_threshold(self, symbol: str) -> Dict[str, Any]:
        """
        Get storm threshold untuk symbol tertentu
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary dengan threshold configuration
        """
        # Gunakan symbol group dari config
        group = alert_settings.alert_config.get_symbol_group(symbol)
        return self.storm_thresholds.get(group, self.storm_thresholds["MID_CAP"])
    
    def _analyze_side_liquidations(self, symbol: str, events: List[Dict[str, Any]], side: str) -> Optional[StormInfo]:
        """
        Analisis liquidation events untuk satu sisi
        
        Args:
            symbol: Trading symbol
            events: List of liquidation events untuk satu sisi
            side: "long_liq" or "short_liq"
            
        Returns:
            StormInfo jika storm terdeteksi, None jika tidak
        """
        try:
            if not events:
                return None
            
            # Calculate total USD
            total_usd = sum(event.get('volUsd', 0) for event in events)
            count = len(events)
            
            # Get threshold untuk symbol
            threshold_config = self.get_storm_threshold(symbol)
            threshold_usd = threshold_config["threshold_usd"]
            min_count = threshold_config["min_count"]
            
            # Check threshold
            if total_usd >= threshold_usd and count >= min_count:
                storm_info = StormInfo(
                    symbol=symbol,
                    total_usd=total_usd,
                    side=side,
                    count=count,
                    window=self.window_seconds,
                    timestamp=time.time()
                )
                
                logger.debug(f"[RADAR] {side} storm analysis for {symbol}: "
                           f"${total_usd:,.0f} ({count} events) >= ${threshold_usd:,.0f} (min {min_count})")
                
                return storm_info
            else:
                logger.debug(f"[RADAR] {side} storm not detected for {symbol}: "
                           f"${total_usd:,.0f} ({count} events) < ${threshold_usd:,.0f} (min {min_count})")
                return None
                
        except Exception as e:
            logger.error(f"[RADAR] Error analyzing {side} liquidations: {e}")
            return None
    
    def _is_in_cooldown(self, symbol: str) -> bool:
        """
        Check jika symbol masih dalam cooldown period
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if in cooldown, False otherwise
        """
        try:
            if symbol not in self.last_storm_detection:
                return False
            
            last_detection = self.last_storm_detection[symbol]
            threshold_config = self.get_storm_threshold(symbol)
            cooldown_seconds = threshold_config["cooldown_sec"]
            
            current_time = time.time()
            time_since_last = current_time - last_detection
            
            return time_since_last < cooldown_seconds
            
        except Exception as e:
            logger.error(f"[RADAR] Error checking cooldown for {symbol}: {e}")
            return False
    
    def get_cooldown_remaining(self, symbol: str) -> int:
        """
        Get remaining cooldown time dalam seconds
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Remaining cooldown seconds (0 if not in cooldown)
        """
        try:
            if symbol not in self.last_storm_detection:
                return 0
            
            last_detection = self.last_storm_detection[symbol]
            threshold_config = self.get_storm_threshold(symbol)
            cooldown_seconds = threshold_config["cooldown_sec"]
            
            current_time = time.time()
            time_since_last = current_time - last_detection
            remaining = cooldown_seconds - time_since_last
            
            return max(0, int(remaining))
            
        except Exception as e:
            logger.error(f"[RADAR] Error getting cooldown for {symbol}: {e}")
            return 0
    
    def reset_cooldown(self, symbol: str):
        """
        Reset cooldown untuk symbol (untuk testing/debugging)
        
        Args:
            symbol: Trading symbol
        """
        if symbol in self.last_storm_detection:
            del self.last_storm_detection[symbol]
            logger.info(f"[RADAR] Cooldown reset for {symbol}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get detector statistics
        
        Returns:
            Dictionary dengan detector stats
        """
        return {
            "window_seconds": self.window_seconds,
            "tracked_symbols": len(self.last_storm_detection),
            "symbols_in_cooldown": sum(1 for symbol in self.last_storm_detection.keys() 
                                     if self._is_in_cooldown(symbol)),
            "storm_thresholds": self.storm_thresholds
        }


# Global instance
liquidation_storm_detector = LiquidationStormDetector()


def get_liquidation_storm_detector() -> LiquidationStormDetector:
    """Get global liquidation storm detector instance"""
    return liquidation_storm_detector
