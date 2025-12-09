"""
Whale Cluster Detector untuk WS Alert Bot - Stage 4 Tahap 3

Modul ini mendeteksi cluster whale buy/sell yang signifikan dalam window waktu.
Ini adalah komponen ketiga untuk Global Radar Mode.

Author: TELEGLAS Team
Version: Stage 4.3.0
"""

import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from .event_aggregator import get_event_aggregator
from .config import alert_settings

logger = logging.getLogger("ws_alert.whale_detector")


@dataclass
class ClusterInfo:
    """Data structure untuk whale cluster information"""
    symbol: str
    cluster_type: str  # "buy_cluster" or "sell_cluster"
    total_buy_usd: float
    total_sell_usd: float
    buy_count: int
    sell_count: int
    dominant_side: str  # "BUY" or "SELL"
    dominance_ratio: float  # Ratio of dominant side vs total
    window: int
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy serialization"""
        return {
            "symbol": self.symbol,
            "cluster_type": self.cluster_type,
            "total_buy_usd": self.total_buy_usd,
            "total_sell_usd": self.total_sell_usd,
            "buy_count": self.buy_count,
            "sell_count": self.sell_count,
            "dominant_side": self.dominant_side,
            "dominance_ratio": self.dominance_ratio,
            "window": self.window,
            "timestamp": self.timestamp
        }


class WhaleClusterDetector:
    """
    Whale Cluster Detector untuk mendeteksi akumulasi whale trades
    yang signifikan dalam window waktu tertentu.
    
    Fungsi:
    - Menganalisis futures trades dalam window time
    - Group berdasarkan sisi (BUY/SELL)
    - Deteksi cluster berdasarkan threshold dan dominasi
    - Filter balanced clusters (tidak signifikan)
    - Thread-safe operations
    """
    
    def __init__(self, window_seconds: int = 30):
        """
        Initialize Whale Cluster Detector
        
        Args:
            window_seconds: Window time in seconds (default: 30)
        """
        self.window_seconds = window_seconds
        self.aggregator = get_event_aggregator()
        
        # Whale cluster thresholds per symbol group
        self.cluster_thresholds = {
            "MAJORS": {
                "threshold_usd": 3000000,    # 3M USD minimum cluster
                "dominance_ratio": 0.7,       # 70% dominance required
                "min_count": 3,              # Minimum 3 trades
                "cooldown_sec": 600          # 10 menit cooldown
            },
            "LARGE_CAP": {
                "threshold_usd": 1500000,    # 1.5M USD
                "dominance_ratio": 0.65,      # 65% dominance
                "min_count": 2,               # Minimum 2 trades
                "cooldown_sec": 900          # 15 menit cooldown
            },
            "MID_CAP": {
                "threshold_usd": 500000,      # 500k USD
                "dominance_ratio": 0.6,       # 60% dominance
                "min_count": 2,               # Minimum 2 trades
                "cooldown_sec": 1200         # 20 menit cooldown
            }
        }
        
        # Track last cluster detection per symbol untuk cooldown
        self.last_cluster_detection: Dict[str, float] = {}
        
        logger.info(f"[RADAR] Whale Cluster Detector initialized with {window_seconds}s window")
    
    def check_cluster(self, symbol: str) -> Optional[ClusterInfo]:
        """
        Check untuk whale cluster pada symbol tertentu
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            
        Returns:
            ClusterInfo jika cluster terdeteksi, None jika tidak
        """
        try:
            # Check cooldown dulu
            if self._is_in_cooldown(symbol):
                logger.debug(f"[RADAR] {symbol} still in whale cluster cooldown")
                return None
            
            # Get trade events dari aggregator
            trade_events = self.aggregator.get_trade_window(symbol, self.window_seconds)
            
            if not trade_events:
                logger.debug(f"[RADAR] No trade events for {symbol}")
                return None
            
            # Group events berdasarkan side
            buy_trades = []
            sell_trades = []
            
            for event in trade_events:
                side = event.get('side', 0)
                if side == 1:  # BUY trades
                    buy_trades.append(event)
                elif side == 2:  # SELL trades
                    sell_trades.append(event)
            
            # Calculate metrics
            total_buy_usd = sum(event.get('volUsd', 0) for event in buy_trades)
            total_sell_usd = sum(event.get('volUsd', 0) for event in sell_trades)
            buy_count = len(buy_trades)
            sell_count = len(sell_trades)
            total_usd = total_buy_usd + total_sell_usd
            total_count = buy_count + sell_count
            
            # Get threshold untuk symbol
            threshold_config = self.get_cluster_threshold(symbol)
            threshold_usd = threshold_config["threshold_usd"]
            min_count = threshold_config["min_count"]
            dominance_ratio = threshold_config["dominance_ratio"]
            
            logger.debug(f"[RADAR] {symbol} cluster analysis: "
                        f"BUY ${total_buy_usd:,.0f} ({buy_count}), "
                        f"SELL ${total_sell_usd:,.0f} ({sell_count}), "
                        f"TOTAL ${total_usd:,.0f}")
            
            # Check minimum requirements
            if total_usd < threshold_usd or total_count < min_count:
                logger.debug(f"[RADAR] {symbol} cluster below threshold: "
                           f"${total_usd:,.0f} < ${threshold_usd:,.0f} or {total_count} < {min_count}")
                return None
            
            # Determine dominant side
            if total_buy_usd > total_sell_usd:
                dominant_side = "BUY"
                dominant_usd = total_buy_usd
                dominance_calc = total_buy_usd / total_usd if total_usd > 0 else 0
            else:
                dominant_side = "SELL"
                dominant_usd = total_sell_usd
                dominance_calc = total_sell_usd / total_usd if total_usd > 0 else 0
            
            # Check dominance ratio (filter balanced clusters)
            if dominance_calc < dominance_ratio:
                logger.debug(f"[RADAR] {symbol} cluster too balanced: "
                           f"{dominant_side} dominance {dominance_calc:.2%} < {dominance_ratio:.2%}")
                return None
            
            # Create cluster info
            cluster_type = f"{dominant_side.lower()}_cluster"
            cluster_info = ClusterInfo(
                symbol=symbol,
                cluster_type=cluster_type,
                total_buy_usd=total_buy_usd,
                total_sell_usd=total_sell_usd,
                buy_count=buy_count,
                sell_count=sell_count,
                dominant_side=dominant_side,
                dominance_ratio=dominance_calc,
                window=self.window_seconds,
                timestamp=time.time()
            )
            
            # Update cooldown
            self.last_cluster_detection[symbol] = cluster_info.timestamp
            
            logger.info(f"[RADAR] Whale cluster detected: {cluster_info.symbol} "
                       f"{cluster_info.dominant_side} ${dominant_usd:,.0f} "
                       f"({cluster_info.dominance_ratio:.1%} dominance)")
            
            return cluster_info
            
        except Exception as e:
            logger.error(f"[RADAR] Error checking whale cluster for {symbol}: {e}")
            return None
    
    def check_multiple_symbols(self, symbols: List[str]) -> List[ClusterInfo]:
        """
        Check cluster untuk multiple symbols
        
        Args:
            symbols: List of symbols to check
            
        Returns:
            List of detected clusters
        """
        detected_clusters = []
        
        for symbol in symbols:
            try:
                cluster = self.check_cluster(symbol)
                if cluster:
                    detected_clusters.append(cluster)
            except Exception as e:
                logger.error(f"[RADAR] Error checking cluster for {symbol}: {e}")
                continue
        
        return detected_clusters
    
    def get_cluster_threshold(self, symbol: str) -> Dict[str, Any]:
        """
        Get cluster threshold untuk symbol tertentu
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary dengan threshold configuration
        """
        # Gunakan symbol group dari config
        group = alert_settings.alert_config.get_symbol_group(symbol)
        return self.cluster_thresholds.get(group, self.cluster_thresholds["MID_CAP"])
    
    def _is_in_cooldown(self, symbol: str) -> bool:
        """
        Check jika symbol masih dalam cooldown period
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if in cooldown, False otherwise
        """
        try:
            if symbol not in self.last_cluster_detection:
                return False
            
            last_detection = self.last_cluster_detection[symbol]
            threshold_config = self.get_cluster_threshold(symbol)
            cooldown_seconds = threshold_config["cooldown_sec"]
            
            current_time = time.time()
            time_since_last = current_time - last_detection
            
            return time_since_last < cooldown_seconds
            
        except Exception as e:
            logger.error(f"[RADAR] Error checking whale cluster cooldown for {symbol}: {e}")
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
            if symbol not in self.last_cluster_detection:
                return 0
            
            last_detection = self.last_cluster_detection[symbol]
            threshold_config = self.get_cluster_threshold(symbol)
            cooldown_seconds = threshold_config["cooldown_sec"]
            
            current_time = time.time()
            time_since_last = current_time - last_detection
            remaining = cooldown_seconds - time_since_last
            
            return max(0, int(remaining))
            
        except Exception as e:
            logger.error(f"[RADAR] Error getting whale cluster cooldown for {symbol}: {e}")
            return 0
    
    def reset_cooldown(self, symbol: str):
        """
        Reset cooldown untuk symbol (untuk testing/debugging)
        
        Args:
            symbol: Trading symbol
        """
        if symbol in self.last_cluster_detection:
            del self.last_cluster_detection[symbol]
            logger.info(f"[RADAR] Whale cluster cooldown reset for {symbol}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get detector statistics
        
        Returns:
            Dictionary dengan detector stats
        """
        return {
            "window_seconds": self.window_seconds,
            "tracked_symbols": len(self.last_cluster_detection),
            "symbols_in_cooldown": sum(1 for symbol in self.last_cluster_detection.keys() 
                                     if self._is_in_cooldown(symbol)),
            "cluster_thresholds": self.cluster_thresholds
        }


# Global instance
whale_cluster_detector = WhaleClusterDetector()


def get_whale_cluster_detector() -> WhaleClusterDetector:
    """Get global whale cluster detector instance"""
    return whale_cluster_detector
