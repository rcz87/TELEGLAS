"""
Global Radar Engine (GRE) - Stage 4

Sistem intel otomatis yang dapat mendeteksi market anomaly di seluruh futures market,
tanpa user meminta simbol apa pun. Menggabungkan Liquidation Storm Detector
dan Whale Cluster Detection untuk composite pattern analysis.

Author: TELEGLAS Team
Version: Stage 4.4.0
"""

import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio

from .event_aggregator import get_event_aggregator
from .liquidation_storm_detector import get_liquidation_storm_detector, StormInfo
from .whale_cluster_detector import get_whale_cluster_detector, ClusterInfo

logger = logging.getLogger("ws_alert.global_radar_engine")


class RadarPatternType(Enum):
    """Types of radar patterns"""
    STORM_ONLY = "storm_only"
    CLUSTER_ONLY = "cluster_only"
    STORM_AND_CLUSTER = "storm_and_cluster"
    CONVERGENCE = "convergence"  # Strongest pattern


@dataclass
class RadarEvent:
    """Comprehensive radar event data"""
    symbol: str
    patterns: List[RadarPatternType]
    storm_info: Optional[StormInfo] = None
    cluster_info: Optional[ClusterInfo] = None
    
    # Composite metrics
    composite_score: float = 0.0
    volatility_level: str = "low"  # low, medium, high, extreme
    market_pressure: str = "neutral"  # bullish, bearish, neutral
    
    # Timing
    window_seconds: int = 30
    timestamp: float = 0.0
    
    # Analysis summary
    summary: str = ""
    signal_strength: str = "weak"  # weak, moderate, strong, extreme


class GlobalRadarEngine:
    """
    Global Radar Engine - Sistem intel otomatis untuk market anomaly detection
    
    Menggabungkan data dari:
    - Event Aggregator (buffer events)
    - Liquidation Storm Detector (storm detection)
    - Whale Cluster Detector (cluster detection)
    
    Menghasilkan composite radar events dengan pattern correlation.
    """
    
    def __init__(self):
        self.aggregator = get_event_aggregator()
        self.storm_detector = get_liquidation_storm_detector()
        self.cluster_detector = get_whale_cluster_detector()
        
        # Composite thresholds
        self.composite_thresholds = {
            "MAJORS": {
                "min_composite_score": 0.7,
                "min_storm_volume": 2000000,  # $2M
                "min_cluster_volume": 3000000,  # $3M
                "convergence_bonus": 0.3
            },
            "LARGE_CAP": {
                "min_composite_score": 0.6,
                "min_storm_volume": 1000000,  # $1M
                "min_cluster_volume": 1500000,  # $1.5M
                "convergence_bonus": 0.25
            },
            "MID_CAP": {
                "min_composite_score": 0.5,
                "min_storm_volume": 500000,   # $0.5M
                "min_cluster_volume": 500000,   # $0.5M
                "convergence_bonus": 0.2
            }
        }
        
        # Cooldown tracking (per symbol)
        self.radar_cooldowns: Dict[str, float] = {}
        self.default_cooldown = 300  # 5 minutes default
        
        logger.info("[RADAR] Global Radar Engine initialized")
    
    def _get_symbol_group_config(self, symbol: str) -> Dict[str, Any]:
        """Get configuration for symbol group"""
        from .config import AlertConfig
        group_name = AlertConfig.get_symbol_group(symbol)
        return self.composite_thresholds.get(group_name, self.composite_thresholds["MID_CAP"])
    
    def _calculate_composite_score(self, storm_info: Optional[StormInfo], 
                                 cluster_info: Optional[ClusterInfo],
                                 symbol: str) -> Tuple[float, List[RadarPatternType]]:
        """
        Calculate composite radar score and identify patterns
        
        Returns:
            Tuple of (score, patterns)
        """
        patterns = []
        score = 0.0
        
        logger.info(f"[RADAR] DEBUG _calculate_composite_score: {symbol}")
        logger.info(f"[RADAR] DEBUG storm_info: {storm_info}")
        logger.info(f"[RADAR] DEBUG cluster_info: {cluster_info}")
        
        # Storm detection contribution
        storm_score = 0.0
        if storm_info:
            config = self._get_symbol_group_config(symbol)
            min_storm_volume = config["min_storm_volume"]
            
            logger.info(f"[RADAR] DEBUG storm config: {config}")
            logger.info(f"[RADAR] DEBUG min_storm_volume: {min_storm_volume}")
            logger.info(f"[RADAR] DEBUG storm_info.total_usd: {storm_info.total_usd}")
            
            # Normalize storm score (0-0.5 range)
            storm_score = min(storm_info.total_usd / (min_storm_volume * 3), 0.5)
            
            logger.info(f"[RADAR] DEBUG storm_score: {storm_score}")
            
            if storm_info.total_usd >= min_storm_volume:
                patterns.append(RadarPatternType.STORM_ONLY)
                logger.info(f"[RADAR] Storm pattern detected for {symbol}: ${storm_info.total_usd:,.0f}")
        
        # Cluster detection contribution
        cluster_score = 0.0
        if cluster_info:
            config = self._get_symbol_group_config(symbol)
            min_cluster_volume = config["min_cluster_volume"]
            
            # Normalize cluster score (0-0.5 range)
            cluster_volume = cluster_info.total_buy_usd + cluster_info.total_sell_usd
            
            logger.info(f"[RADAR] DEBUG cluster config: {config}")
            logger.info(f"[RADAR] DEBUG min_cluster_volume: {min_cluster_volume}")
            logger.info(f"[RADAR] DEBUG cluster_volume: {cluster_volume}")
            
            cluster_score = min(cluster_volume / (min_cluster_volume * 3), 0.5)
            
            logger.info(f"[RADAR] DEBUG cluster_score: {cluster_score}")
            
            if cluster_volume >= min_cluster_volume:
                patterns.append(RadarPatternType.CLUSTER_ONLY)
                logger.info(f"[RADAR] Cluster pattern detected for {symbol}: ${cluster_volume:,.0f}")
        
        # Convergence bonus (both storm and cluster)
        if storm_info and cluster_info:
            config = self._get_symbol_group_config(symbol)
            convergence_bonus = config["convergence_bonus"]
            score += convergence_bonus
            
            patterns.remove(RadarPatternType.STORM_ONLY)
            patterns.remove(RadarPatternType.CLUSTER_ONLY)
            patterns.append(RadarPatternType.STORM_AND_CLUSTER)
            
            # Check for extreme convergence
            if (storm_info.total_usd >= config["min_storm_volume"] * 2 and 
                (cluster_info.total_buy_usd + cluster_info.total_sell_usd) >= config["min_cluster_volume"] * 2):
                patterns.append(RadarPatternType.CONVERGENCE)
                logger.info(f"[RADAR] EXTREME convergence detected for {symbol}")
        
        # Base score
        score += storm_score + cluster_score
        
        logger.info(f"[RADAR] DEBUG final score: {score}, patterns: {[p.value for p in patterns]}")
        
        return score, patterns
    
    def _determine_market_pressure(self, storm_info: Optional[StormInfo], 
                                  cluster_info: Optional[ClusterInfo]) -> str:
        """Determine overall market pressure direction"""
        if not storm_info and not cluster_info:
            return "neutral"
        
        bullish_signals = 0
        bearish_signals = 0
        
        # Storm signals
        if storm_info:
            if storm_info.side == "short_liq":  # Short liquidations = bullish
                bullish_signals += 2
            else:  # Long liquidations = bearish
                bearish_signals += 2
        
        # Cluster signals
        if cluster_info:
            if cluster_info.dominant_side == "BUY":
                bullish_signals += cluster_info.dominance_ratio * 2
            else:
                bearish_signals += cluster_info.dominance_ratio * 2
        
        # Determine pressure
        if bullish_signals > bearish_signals * 1.5:
            return "bullish"
        elif bearish_signals > bullish_signals * 1.5:
            return "bearish"
        else:
            return "neutral"
    
    def _determine_volatility_level(self, storm_info: Optional[StormInfo], 
                                   cluster_info: Optional[ClusterInfo]) -> str:
        """Determine volatility level based on activity"""
        total_activity = 0.0
        
        if storm_info:
            total_activity += storm_info.total_usd
            total_activity += storm_info.count * 100000  # Weight by count
        
        if cluster_info:
            total_activity += cluster_info.total_buy_usd + cluster_info.total_sell_usd
            total_activity += (cluster_info.buy_count + cluster_info.sell_count) * 50000  # Weight by count
        
        if total_activity >= 10000000:  # $10M+
            return "extreme"
        elif total_activity >= 5000000:  # $5M+
            return "high"
        elif total_activity >= 2000000:  # $2M+
            return "medium"
        else:
            return "low"
    
    def _create_radar_event(self, symbol: str, storm_info: Optional[StormInfo], 
                          cluster_info: Optional[ClusterInfo]) -> Optional[RadarEvent]:
        """Create comprehensive radar event from individual patterns"""
        
        # Calculate composite score and patterns
        score, patterns = self._calculate_composite_score(storm_info, cluster_info, symbol)
        
        logger.info(f"[RADAR] DEBUG: {symbol} - Score: {score:.2f}, Patterns: {[p.value for p in patterns]}")
        
        if not patterns:
            logger.info(f"[RADAR] DEBUG: No patterns found for {symbol}")
            return None
        
        # Check minimum score requirement
        config = self._get_symbol_group_config(symbol)
        min_score = config["min_composite_score"]
        
        # Allow storm_only or cluster_only with lower threshold
        if score < min_score and RadarPatternType.CONVERGENCE not in patterns:
            # Special case: allow strong single patterns with lower threshold
            if (RadarPatternType.STORM_ONLY in patterns or 
                RadarPatternType.CLUSTER_ONLY in patterns):
                if score >= 0.4:  # Lower threshold for single patterns
                    logger.info(f"[RADAR] Single pattern allowed for {symbol}: {score:.2f}")
                else:
                    logger.debug(f"[RADAR] Score too low for {symbol}: {score:.2f} < 0.4")
                    return None
            else:
                logger.debug(f"[RADAR] Score too low for {symbol}: {score:.2f} < {min_score:.2f}")
                return None
        
        # Create radar event
        radar_event = RadarEvent(
            symbol=symbol,
            patterns=patterns,
            storm_info=storm_info,
            cluster_info=cluster_info,
            composite_score=score,
            volatility_level=self._determine_volatility_level(storm_info, cluster_info),
            market_pressure=self._determine_market_pressure(storm_info, cluster_info),
            window_seconds=30,
            timestamp=time.time()
        )
        
        # Determine signal strength
        if score >= 0.8 or RadarPatternType.CONVERGENCE in patterns:
            radar_event.signal_strength = "extreme"
        elif score >= 0.6:
            radar_event.signal_strength = "strong"
        elif score >= 0.4:
            radar_event.signal_strength = "moderate"
        else:
            radar_event.signal_strength = "weak"
        
        # Generate summary
        radar_event.summary = self._generate_summary(radar_event)
        
        return radar_event
    
    def _generate_summary(self, radar_event: RadarEvent) -> str:
        """Generate human-readable summary for radar event"""
        patterns = radar_event.patterns
        
        if RadarPatternType.CONVERGENCE in patterns:
            return f"Extreme convergence: Storm + Whale Cluster detected"
        elif RadarPatternType.STORM_AND_CLUSTER in patterns:
            return f"Whale + Storm patterns detected"
        elif RadarPatternType.STORM_ONLY in patterns:
            return f"Liquidation storm activity detected"
        elif RadarPatternType.CLUSTER_ONLY in patterns:
            return f"Whale cluster accumulation detected"
        else:
            return f"Market anomaly detected"
    
    def check_symbol_radar(self, symbol: str) -> Optional[RadarEvent]:
        """
        Check radar status for a specific symbol
        
        Args:
            symbol: Trading symbol to check
            
        Returns:
            RadarEvent if significant patterns detected, None otherwise
        """
        try:
            logger.debug(f"[RADAR] Checking radar for {symbol}")
            
            # Check cooldown
            if not self._should_check_symbol(symbol):
                return None
            
            # DEBUG: Check aggregator state
            liq_window = self.aggregator.get_liq_window(symbol, window_sec=30)
            trade_window = self.aggregator.get_trade_window(symbol, window_sec=30)
            
            logger.info(f"[RADAR] DEBUG aggregator state for {symbol}:")
            logger.info(f"[RADAR] DEBUG - liquidations: {len(liq_window)} events")
            logger.info(f"[RADAR] DEBUG - trades: {len(trade_window)} events")
            
            # Get individual pattern results
            storm_info = self.storm_detector.check_storm(symbol)
            cluster_info = self.cluster_detector.check_cluster(symbol)
            
            logger.info(f"[RADAR] DEBUG detector results for {symbol}:")
            logger.info(f"[RADAR] DEBUG - storm_info: {storm_info}")
            logger.info(f"[RADAR] DEBUG - cluster_info: {cluster_info}")
            
            # Create composite radar event
            radar_event = self._create_radar_event(symbol, storm_info, cluster_info)
            
            if radar_event:
                logger.info(f"[RADAR] 🚀 Radar event: {symbol} - {radar_event.summary}")
                logger.info(f"[RADAR] Score: {radar_event.composite_score:.2f}, "
                          f"Pressure: {radar_event.market_pressure}, "
                          f"Volatility: {radar_event.volatility_level}")
                
                # Update cooldown
                self._update_cooldown(symbol)
                
                return radar_event
            
            return None
            
        except Exception as e:
            logger.error(f"[RADAR] Error checking radar for {symbol}: {e}")
            return None
    
    def check_multiple_symbols(self, symbols: List[str]) -> List[RadarEvent]:
        """
        Check radar for multiple symbols
        
        Args:
            symbols: List of symbols to check
            
        Returns:
            List of radar events detected
        """
        radar_events = []
        
        for symbol in symbols:
            try:
                radar_event = self.check_symbol_radar(symbol)
                if radar_event:
                    radar_events.append(radar_event)
            except Exception as e:
                logger.error(f"[RADAR] Error checking {symbol}: {e}")
                continue
        
        return radar_events
    
    def scan_all_active_symbols(self) -> List[RadarEvent]:
        """
        Scan all symbols that have recent activity in aggregator
        
        Returns:
            List of radar events from all active symbols
        """
        try:
            # Get all symbols with recent activity
            active_symbols = self.aggregator.get_active_symbols(window_seconds=60)
            
            if not active_symbols:
                logger.debug("[RADAR] No active symbols found")
                return []
            
            logger.info(f"[RADAR] Scanning {len(active_symbols)} active symbols")
            
            # Check radar for all active symbols
            radar_events = self.check_multiple_symbols(active_symbols)
            
            if radar_events:
                logger.info(f"[RADAR] 🎯 Found {len(radar_events)} radar events")
                for event in radar_events:
                    logger.info(f"[RADAR]   - {event.symbol}: {event.summary}")
            
            return radar_events
            
        except Exception as e:
            logger.error(f"[RADAR] Error scanning active symbols: {e}")
            return []
    
    def _should_check_symbol(self, symbol: str) -> bool:
        """Check if symbol should be checked (cooldown logic)"""
        if symbol not in self.radar_cooldowns:
            return True
        
        last_check = self.radar_cooldowns[symbol]
        time_since_last = time.time() - last_check
        
        # Dynamic cooldown based on volatility level
        cooldown = self.default_cooldown
        
        # Shorter cooldown for high volatility symbols
        if symbol in self.radar_cooldowns:
            # Check if this is a high-frequency symbol
            recent_activity = self.aggregator.get_trade_window(symbol, window_sec=300)
            if len(recent_activity) > 50:  # High activity
                cooldown = self.default_cooldown * 0.5  # Half cooldown
        
        return time_since_last >= cooldown
    
    def _update_cooldown(self, symbol: str):
        """Update cooldown for symbol"""
        self.radar_cooldowns[symbol] = time.time()
    
    def reset_cooldown(self, symbol: str):
        """Reset cooldown for a symbol (for testing)"""
        if symbol in self.radar_cooldowns:
            del self.radar_cooldowns[symbol]
        logger.info(f"[RADAR] Cooldown reset for {symbol}")
    
    def cleanup_old_cooldowns(self, max_age_hours: int = 1):
        """Clean up old cooldown records"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        old_symbols = []
        for symbol, timestamp in self.radar_cooldowns.items():
            if timestamp < cutoff_time:
                old_symbols.append(symbol)
        
        for symbol in old_symbols:
            del self.radar_cooldowns[symbol]
        
        if old_symbols:
            logger.info(f"[RADAR] Cleaned up {len(old_symbols)} old cooldown records")
    
    def get_radar_statistics(self) -> Dict[str, Any]:
        """Get radar engine statistics"""
        return {
            "tracked_symbols": len(self.radar_cooldowns),
            "last_cooldowns": {
                symbol: time.time() - timestamp 
                for symbol, timestamp in sorted(
                    self.radar_cooldowns.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:10]
            },
            "aggregator_stats": self.aggregator.get_statistics(),
            "storm_detector_active_symbols": len(self.storm_detector.symbol_cooldowns),
            "cluster_detector_active_symbols": len(self.cluster_detector.symbol_cooldowns)
        }


# Global instance
_global_radar_engine = None


def get_global_radar_engine() -> GlobalRadarEngine:
    """Get global radar engine instance"""
    global _global_radar_engine
    if _global_radar_engine is None:
        _global_radar_engine = GlobalRadarEngine()
    return _global_radar_engine


def check_global_radar(symbol: str) -> Optional[RadarEvent]:
    """Convenience function to check radar for single symbol"""
    return get_global_radar_engine().check_symbol_radar(symbol)


def scan_all_symbols_radar() -> List[RadarEvent]:
    """Convenience function to scan all active symbols"""
    return get_global_radar_engine().scan_all_active_symbols()
