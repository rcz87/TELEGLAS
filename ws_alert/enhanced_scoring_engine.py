"""
Enhanced Scoring Engine (Poin 5)

Advanced composite scoring algorithm dengan:
- Weighted scoring untuk different pattern types
- Time-decay scoring untuk temporal relevance
- Market context adjustment untuk situasi awareness
- Multi-factor signal enhancement

Author: TELEGLAS Team
Version: 1.0.0
"""

import time
import math
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics

from .liquidation_storm_detector import StormInfo
from .whale_cluster_detector import ClusterInfo
from .config import AlertConfig

logger = logging.getLogger("ws_alert.enhanced_scoring_engine")


class MarketRegime(Enum):
    """Market regime classification"""
    BULL_MOMENTUM = "bull_momentum"
    BEAR_MOMENTUM = "bear_momentum"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"


class SignalType(Enum):
    """Signal type classification"""
    LIQUIDATION_STORM = "liquidation_storm"
    WHALE_CLUSTER = "whale_cluster"
    CONVERGENCE = "convergence"
    REVERSAL = "reversal"
    MOMENTUM = "momentum"


@dataclass
class WeightConfiguration:
    """Configuration for scoring weights"""
    # Base weights
    storm_weight: float = 0.4
    cluster_weight: float = 0.4
    convergence_weight: float = 0.6
    
    # Volume modifiers
    volume_multiplier: float = 1.5
    frequency_multiplier: float = 1.2
    
    # Time decay factors
    decay_rate: float = 0.1  # per minute
    recency_bonus: float = 0.3
    
    # Market context modifiers
    bull_market_boost: float = 1.2
    bear_market_boost: float = 1.3
    volatile_market_boost: float = 1.1


@dataclass
class MarketContext:
    """Current market context information"""
    regime: MarketRegime
    volatility_index: float  # 0-1, higher = more volatile
    momentum_index: float    # 0-1, directional strength
    volume_index: float      # 0-1, relative volume
    sentiment_score: float   # -1 to 1, negative=bearish
    
    # Market-wide metrics
    total_market_volume: float
    major_symbols_volume: Dict[str, float]
    market_time_hours: int  # Market session time


@dataclass
class EnhancedScore:
    """Enhanced scoring result with detailed breakdown"""
    
    # Base scores
    raw_score: float = 0.0
    weighted_score: float = 0.0
    time_adjusted_score: float = 0.0
    context_adjusted_score: float = 0.0
    
    # Final composite score
    final_score: float = 0.0
    confidence_level: float = 0.0  # 0-1
    
    # Score components
    storm_contribution: float = 0.0
    cluster_contribution: float = 0.0
    convergence_bonus: float = 0.0
    time_decay_multiplier: float = 1.0
    context_multiplier: float = 1.0
    
    # Signal classification
    signal_types: List[SignalType] = None
    signal_strength: str = "weak"  # weak, moderate, strong, extreme
    
    # Temporal analysis
    recency_score: float = 0.0
    momentum_score: float = 0.0
    
    # Market factors
    market_alignment: float = 0.0  # How well signal aligns with market
    volume_anomaly: float = 0.0    # How unusual the volume is
    
    # Timing
    calculation_time: float = 0.0
    
    def __post_init__(self):
        if self.signal_types is None:
            self.signal_types = []


class EnhancedScoringEngine:
    """
    Enhanced Scoring Engine dengan advanced composite scoring algorithm
    
    Features:
    - Weighted scoring untuk different pattern types
    - Time-decay scoring untuk temporal relevance  
    - Market context adjustment untuk situasi awareness
    - Multi-factor signal enhancement
    """
    
    def __init__(self):
        self.weights = WeightConfiguration()
        
        # Market context cache
        self.market_context_cache: Optional[MarketContext] = None
        self.context_cache_time: float = 0
        self.context_cache_ttl: float = 60.0  # 1 minute cache
        
        # Historical data for context analysis
        self.volume_history: Dict[str, List[Tuple[float, float]]] = {}  # symbol -> [(timestamp, volume)]
        self.price_history: Dict[str, List[Tuple[float, float]]] = {}   # symbol -> [(timestamp, price)]
        
        # Scoring statistics
        self.scoring_stats = {
            'total_scores': 0,
            'avg_score': 0.0,
            'max_score': 0.0,
            'score_distribution': {'weak': 0, 'moderate': 0, 'strong': 0, 'extreme': 0}
        }
        
        logger.info("[SCORING] Enhanced Scoring Engine initialized")
    
    def calculate_enhanced_score(self, 
                               symbol: str,
                               storm_info: Optional[StormInfo],
                               cluster_info: Optional[ClusterInfo],
                               current_time: Optional[float] = None) -> EnhancedScore:
        """
        Calculate enhanced composite score with all factors
        
        Args:
            symbol: Trading symbol
            storm_info: Storm detection information
            cluster_info: Cluster detection information  
            current_time: Current timestamp (defaults to now)
            
        Returns:
            EnhancedScore with detailed breakdown
        """
        start_time = time.time()
        
        if current_time is None:
            current_time = time.time()
        
        # Initialize score
        score = EnhancedScore()
        
        try:
            # 1. Calculate base raw scores
            score.storm_contribution = self._calculate_storm_score(storm_info, symbol)
            score.cluster_contribution = self._calculate_cluster_score(cluster_info, symbol)
            score.convergence_bonus = self._calculate_convergence_bonus(storm_info, cluster_info, symbol)
            
            # 2. Apply weighted scoring
            score.weighted_score = self._apply_weighted_scoring(score, symbol)
            
            # 3. Apply time decay
            score.time_adjusted_score, score.time_decay_multiplier = self._apply_time_decay(
                score, storm_info, cluster_info, current_time
            )
            
            # 4. Get market context and apply adjustments
            market_context = self._get_market_context(current_time)
            score.context_adjusted_score, score.context_multiplier = self._apply_market_context(
                score, symbol, market_context
            )
            
            # 5. Calculate final score and confidence
            score.final_score, score.confidence_level = self._calculate_final_score(score, symbol)
            
            # 6. Classify signal types and strength
            score.signal_types = self._classify_signal_types(storm_info, cluster_info)
            score.signal_strength = self._classify_signal_strength(score.final_score)
            
            # 7. Calculate additional factors
            score.recency_score = self._calculate_recency_score(storm_info, cluster_info, current_time)
            score.momentum_score = self._calculate_momentum_score(symbol, market_context)
            score.market_alignment = self._calculate_market_alignment(symbol, score.signal_types, market_context)
            score.volume_anomaly = self._calculate_volume_anomaly(symbol, storm_info, cluster_info)
            
            # 8. Set timing
            score.calculation_time = time.time() - start_time
            
            # 9. Update statistics
            self._update_scoring_stats(score)
            
            logger.debug(f"[SCORING] Enhanced score for {symbol}: {score.final_score:.3f} "
                        f"(confidence: {score.confidence_level:.2f})")
            
            return score
            
        except Exception as e:
            logger.error(f"[SCORING] Error calculating enhanced score for {symbol}: {e}")
            score.calculation_time = time.time() - start_time
            return score
    
    def _calculate_storm_score(self, storm_info: Optional[StormInfo], symbol: str) -> float:
        """Calculate base storm score"""
        if not storm_info:
            return 0.0
        
        # Get symbol-specific threshold
        group_config = self._get_symbol_group_config(symbol)
        min_volume = group_config["min_storm_volume"]
        
        # Base score from volume ratio
        volume_ratio = storm_info.total_usd / min_volume
        
        # Apply logarithmic scaling for diminishing returns
        base_score = math.log10(volume_ratio + 1) / 3.0
        
        # Add count factor (more liquidations = stronger signal)
        count_factor = min(storm_info.count / 10.0, 1.0) * 0.2
        
        # Apply side weighting (short liquidations usually more significant)
        side_weight = 1.2 if storm_info.side == "short_liq" else 1.0
        
        total_score = (base_score + count_factor) * side_weight
        
        logger.debug(f"[SCORING] Storm score for {symbol}: {total_score:.3f} "
                    f"(volume: {storm_info.total_usd:,.0f}, count: {storm_info.count})")
        
        return min(total_score, 1.0)
    
    def _calculate_cluster_score(self, cluster_info: Optional[ClusterInfo], symbol: str) -> float:
        """Calculate base cluster score"""
        if not cluster_info:
            return 0.0
        
        # Get symbol-specific threshold
        group_config = self._get_symbol_group_config(symbol)
        min_volume = group_config["min_cluster_volume"]
        
        # Total cluster volume
        total_volume = cluster_info.total_buy_usd + cluster_info.total_sell_usd
        
        # Base score from volume ratio
        volume_ratio = total_volume / min_volume
        base_score = math.log10(volume_ratio + 1) / 3.0
        
        # Add dominance factor (stronger dominance = stronger signal)
        dominance_factor = cluster_info.dominance_ratio * 0.2
        
        # Add balance factor (balanced buying/selling = accumulation/distribution)
        total_trades = cluster_info.buy_count + cluster_info.sell_count
        if total_trades > 0:
            balance_ratio = min(cluster_info.buy_count, cluster_info.sell_count) / total_trades
            balance_factor = balance_ratio * 0.1
        else:
            balance_factor = 0.0
        
        total_score = base_score + dominance_factor + balance_factor
        
        logger.debug(f"[SCORING] Cluster score for {symbol}: {total_score:.3f} "
                    f"(volume: {total_volume:,.0f}, dominance: {cluster_info.dominance_ratio:.2f})")
        
        return min(total_score, 1.0)
    
    def _calculate_convergence_bonus(self, storm_info: Optional[StormInfo], 
                                   cluster_info: Optional[ClusterInfo], symbol: str) -> float:
        """Calculate convergence bonus when both patterns present"""
        if not storm_info or not cluster_info:
            return 0.0
        
        # Get symbol-specific configuration
        group_config = self._get_symbol_group_config(symbol)
        base_bonus = group_config["convergence_bonus"]
        
        # Check for extreme convergence (both patterns very strong)
        storm_ratio = storm_info.total_usd / group_config["min_storm_volume"]
        cluster_volume = cluster_info.total_buy_usd + cluster_info.total_sell_usd
        cluster_ratio = cluster_volume / group_config["min_cluster_volume"]
        
        if storm_ratio >= 2.0 and cluster_ratio >= 2.0:
            # Extreme convergence - significantly higher bonus
            extreme_multiplier = 1.5
            logger.debug(f"[SCORING] Extreme convergence bonus for {symbol}")
        else:
            extreme_multiplier = 1.0
        
        # Bonus scales with strength of both patterns
        strength_multiplier = min(storm_ratio, cluster_ratio) / 2.0
        final_bonus = base_bonus * extreme_multiplier * strength_multiplier
        
        logger.debug(f"[SCORING] Convergence bonus for {symbol}: {final_bonus:.3f}")
        
        return final_bonus
    
    def _apply_weighted_scoring(self, score: EnhancedScore, symbol: str) -> float:
        """Apply weighted scoring configuration"""
        weighted = 0.0
        
        # Apply storm weight
        if score.storm_contribution > 0:
            weighted += score.storm_contribution * self.weights.storm_weight
        
        # Apply cluster weight  
        if score.cluster_contribution > 0:
            weighted += score.cluster_contribution * self.weights.cluster_weight
        
        # Add convergence bonus (already weighted)
        weighted += score.convergence_bonus
        
        # Normalize to 0-1 range
        return min(weighted, 1.0)
    
    def _apply_time_decay(self, score: EnhancedScore, 
                         storm_info: Optional[StormInfo],
                         cluster_info: Optional[ClusterInfo], 
                         current_time: float) -> Tuple[float, float]:
        """Apply time decay scoring"""
        
        # Get the oldest timestamp from patterns
        oldest_time = current_time
        
        if storm_info and hasattr(storm_info, 'timestamp'):
            oldest_time = min(oldest_time, storm_info.timestamp)
        
        if cluster_info and hasattr(cluster_info, 'timestamp'):
            oldest_time = min(oldest_time, cluster_info.timestamp)
        
        # Calculate time difference in minutes
        time_diff_minutes = (current_time - oldest_time) / 60.0
        
        # Apply exponential decay: multiplier = e^(-decay_rate * time)
        decay_multiplier = math.exp(-self.weights.decay_rate * time_diff_minutes)
        
        # Apply recency bonus for very recent events
        if time_diff_minutes < 5:  # Within 5 minutes
            recency_bonus = self.weights.recency_bonus * (1.0 - time_diff_minutes / 5.0)
            decay_multiplier += recency_bonus
        
        # Apply time decay to weighted score
        time_adjusted = score.weighted_score * decay_multiplier
        
        logger.debug(f"[SCORING] Time decay for score: {decay_multiplier:.3f} "
                    f"(time_diff: {time_diff_minutes:.1f}min)")
        
        return time_adjusted, decay_multiplier
    
    def _get_market_context(self, current_time: float) -> MarketContext:
        """Get current market context with caching"""
        # Check cache
        if (self.market_context_cache and 
            current_time - self.context_cache_time < self.context_cache_ttl):
            return self.market_context_cache
        
        # Calculate fresh context
        context = self._calculate_market_context(current_time)
        
        # Update cache
        self.market_context_cache = context
        self.context_cache_time = current_time
        
        return context
    
    def _calculate_market_context(self, current_time: float) -> MarketContext:
        """Calculate current market context"""
        
        # Get market session time
        market_time_hours = time.localtime(current_time).tm_hour
        
        # Calculate volume index from recent data
        total_volume = 0.0
        major_symbols_volume = {}
        
        for symbol, volumes in self.volume_history.items():
            if volumes:
                recent_volumes = [v for t, v in volumes if current_time - t < 300]  # Last 5 min
                symbol_volume = sum(recent_volumes)
                total_volume += symbol_volume
                major_symbols_volume[symbol] = symbol_volume
        
        # Calculate volume index (normalized)
        volume_index = min(total_volume / 10000000, 1.0)  # Normalize against $10M baseline
        
        # Determine market regime (simplified)
        regime = self._determine_market_regime(market_time_hours, volume_index)
        
        # Calculate other indices (simplified implementations)
        volatility_index = self._calculate_volatility_index(current_time)
        momentum_index = self._calculate_momentum_index(current_time)
        sentiment_score = self._calculate_sentiment_score(current_time)
        
        return MarketContext(
            regime=regime,
            volatility_index=volatility_index,
            momentum_index=momentum_index,
            volume_index=volume_index,
            sentiment_score=sentiment_score,
            total_market_volume=total_volume,
            major_symbols_volume=major_symbols_volume,
            market_time_hours=market_time_hours
        )
    
    def _determine_market_regime(self, market_time_hours: int, volume_index: float) -> MarketRegime:
        """Determine current market regime"""
        # Simplified regime detection
        if volume_index > 0.8:
            return MarketRegime.VOLATILE
        elif 9 <= market_time_hours <= 11:  # Asian session morning
            return MarketRegime.ACCUMULATION
        elif 20 <= market_time_hours <= 23:  # US session
            return MarketRegime.VOLATILE
        elif 2 <= market_time_hours <= 6:  # Quiet hours
            return MarketRegime.SIDEWAYS
        else:
            return MarketRegime.SIDEWAYS
    
    def _calculate_volatility_index(self, current_time: float) -> float:
        """Calculate market volatility index"""
        # Simplified volatility calculation based on volume variance
        all_volatilities = []
        
        for symbol, volumes in self.volume_history.items():
            if len(volumes) >= 2:
                recent_volumes = [v for t, v in volumes if current_time - t < 600]  # Last 10 min
                if len(recent_volumes) >= 2:
                    volatility = statistics.stdev(recent_volumes) / (statistics.mean(recent_volumes) + 1)
                    all_volatilities.append(min(volatility, 1.0))
        
        return statistics.mean(all_volatilities) if all_volatilities else 0.5
    
    def _calculate_momentum_index(self, current_time: float) -> float:
        """Calculate market momentum index"""
        # Simplified momentum calculation
        all_momentums = []
        
        for symbol, prices in self.price_history.items():
            if len(prices) >= 2:
                recent_prices = [p for t, p in prices if current_time - t < 600]  # Last 10 min
                if len(recent_prices) >= 2:
                    price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
                    all_momentums.append(abs(price_change))
        
        return min(statistics.mean(all_momentums) * 10, 1.0) if all_momentums else 0.5
    
    def _calculate_sentiment_score(self, current_time: float) -> float:
        """Calculate market sentiment score"""
        # Simplified sentiment based on buy/sell ratio
        total_buy = 0.0
        total_sell = 0.0
        
        for symbol, volumes in self.volume_history.items():
            # This would need more detailed data in real implementation
            pass  # Simplified for now
        
        # Neutral sentiment for now
        return 0.0
    
    def _apply_market_context(self, score: EnhancedScore, symbol: str, 
                             context: MarketContext) -> Tuple[float, float]:
        """Apply market context adjustments"""
        multiplier = 1.0
        
        # Apply regime-based adjustments
        if context.regime == MarketRegime.BULL_MOMENTUM:
            multiplier *= self.weights.bull_market_boost
        elif context.regime == MarketRegime.BEAR_MOMENTUM:
            multiplier *= self.weights.bear_market_boost
        elif context.regime == MarketRegime.VOLATILE:
            multiplier *= self.weights.volatile_market_boost
        
        # Apply volatility adjustment (higher volatility = higher multiplier)
        volatility_adjustment = 1.0 + (context.volatility_index * 0.3)
        multiplier *= volatility_adjustment
        
        # Apply volume anomaly adjustment
        symbol_volume = context.major_symbols_volume.get(symbol, 0)
        if context.total_market_volume > 0:
            volume_ratio = symbol_volume / context.total_market_volume
            if volume_ratio > 0.3:  # Symbol has unusually high volume
                multiplier *= self.weights.volume_multiplier
        
        # Apply time-of-day adjustment
        if 20 <= context.market_time_hours <= 23:  # Peak hours
            multiplier *= 1.1
        elif 2 <= context.market_time_hours <= 6:  # Quiet hours
            multiplier *= 0.9
        
        context_adjusted = score.time_adjusted_score * multiplier
        
        logger.debug(f"[SCORING] Context adjustment: {multiplier:.3f} "
                    f"(regime: {context.regime.value}, volatility: {context.volatility_index:.2f})")
        
        return context_adjusted, multiplier
    
    def _calculate_final_score(self, score: EnhancedScore, symbol: str) -> Tuple[float, float]:
        """Calculate final composite score and confidence"""
        final_score = score.context_adjusted_score
        
        # Calculate confidence based on data quality and consistency
        confidence_factors = []
        
        # Signal consistency (both storm and cluster present = higher confidence)
        if score.storm_contribution > 0 and score.cluster_contribution > 0:
            confidence_factors.append(0.8)
        elif score.storm_contribution > 0 or score.cluster_contribution > 0:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.3)
        
        # Score stability (not too close to thresholds)
        if abs(final_score - 0.5) > 0.2:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
        
        # Data recency (more recent = higher confidence)
        if score.time_decay_multiplier > 0.8:
            confidence_factors.append(0.8)
        elif score.time_decay_multiplier > 0.5:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.4)
        
        # Market alignment (signal aligns with market trend = higher confidence)
        if score.market_alignment > 0.7:
            confidence_factors.append(0.7)
        elif score.market_alignment > 0.4:
            confidence_factors.append(0.5)
        else:
            confidence_factors.append(0.3)
        
        # Calculate overall confidence
        confidence_level = statistics.mean(confidence_factors)
        
        # Apply confidence moderation to final score
        moderated_score = final_score * (0.5 + confidence_level * 0.5)
        
        return min(moderated_score, 1.0), confidence_level
    
    def _classify_signal_types(self, storm_info: Optional[StormInfo], 
                             cluster_info: Optional[ClusterInfo]) -> List[SignalType]:
        """Classify signal types"""
        signal_types = []
        
        if storm_info and cluster_info:
            signal_types.append(SignalType.CONVERGENCE)
        
        if storm_info:
            signal_types.append(SignalType.LIQUIDATION_STORM)
            
            # Check for reversal signal (liquidation spike might indicate reversal)
            if storm_info.total_usd > 2000000:  # $2M+ liquidations
                signal_types.append(SignalType.REVERSAL)
        
        if cluster_info:
            signal_types.append(SignalType.WHALE_CLUSTER)
            
            # Check for momentum signal (consistent buying/selling)
            if cluster_info.dominance_ratio > 0.7:
                signal_types.append(SignalType.MOMENTUM)
        
        return signal_types
    
    def _classify_signal_strength(self, final_score: float) -> str:
        """Classify signal strength based on score"""
        if final_score >= 0.8:
            return "extreme"
        elif final_score >= 0.6:
            return "strong"
        elif final_score >= 0.4:
            return "moderate"
        else:
            return "weak"
    
    def _calculate_recency_score(self, storm_info: Optional[StormInfo],
                               cluster_info: Optional[ClusterInfo], 
                               current_time: float) -> float:
        """Calculate recency score"""
        recency_scores = []
        
        if storm_info and hasattr(storm_info, 'timestamp'):
            time_diff = current_time - storm_info.timestamp
            recency = max(0, 1.0 - time_diff / 300)  # 5 minute window
            recency_scores.append(recency)
        
        if cluster_info and hasattr(cluster_info, 'timestamp'):
            time_diff = current_time - cluster_info.timestamp
            recency = max(0, 1.0 - time_diff / 300)  # 5 minute window
            recency_scores.append(recency)
        
        return statistics.mean(recency_scores) if recency_scores else 0.0
    
    def _calculate_momentum_score(self, symbol: str, context: MarketContext) -> float:
        """Calculate momentum score for symbol"""
        # Simplified momentum calculation
        if symbol not in self.price_history:
            return 0.5
        
        prices = [p for t, p in self.price_history[symbol] if time.time() - t < 600]
        if len(prices) < 2:
            return 0.5
        
        # Calculate price momentum
        price_change = (prices[-1] - prices[0]) / prices[0]
        momentum = min(abs(price_change) * 10, 1.0)
        
        return momentum
    
    def _calculate_market_alignment(self, symbol: str, signal_types: List[SignalType], 
                                   context: MarketContext) -> float:
        """Calculate how well signal aligns with market context"""
        alignment = 0.5  # Default neutral
        
        # Bull market alignment
        if context.regime == MarketRegime.BULL_MOMENTUM:
            if SignalType.WHALE_CLUSTER in signal_types:
                alignment += 0.3  # Whale accumulation in bull market = good alignment
            if SignalType.LIQUIDATION_STORM in signal_types:
                alignment += 0.2  # Short liquidations in bull market = good
        
        # Bear market alignment
        elif context.regime == MarketRegime.BEAR_MOMENTUM:
            if SignalType.LIQUIDATION_STORM in signal_types:
                alignment += 0.3  # Long liquidations in bear market = good
            if SignalType.WHALE_CLUSTER in signal_types:
                alignment += 0.2  # Whale distribution in bear market
        
        # Volatile market alignment
        elif context.regime == MarketRegime.VOLATILE:
            if SignalType.CONVERGENCE in signal_types:
                alignment += 0.4  # Convergence in volatile market = very good
        
        return min(alignment, 1.0)
    
    def _calculate_volume_anomaly(self, symbol: str, storm_info: Optional[StormInfo],
                                cluster_info: Optional[ClusterInfo]) -> float:
        """Calculate how unusual the current volume is"""
        if symbol not in self.volume_history:
            return 0.5
        
        # Get current volume
        current_volume = 0.0
        if storm_info:
            current_volume += storm_info.total_usd
        if cluster_info:
            current_volume += cluster_info.total_buy_usd + cluster_info.total_sell_usd
        
        if current_volume == 0:
            return 0.0
        
        # Get historical volumes
        volumes = [v for t, v in self.volume_history[symbol] if time.time() - t < 3600]  # Last hour
        if len(volumes) < 5:
            return 0.5
        
        # Calculate anomaly score
        avg_volume = statistics.mean(volumes)
        std_volume = statistics.stdev(volumes)
        
        if std_volume == 0:
            return 0.0
        
        z_score = (current_volume - avg_volume) / std_volume
        anomaly = min(abs(z_score) / 3.0, 1.0)  # Normalize to 0-1
        
        return anomaly
    
    def _get_symbol_group_config(self, symbol: str) -> Dict[str, Any]:
        """Get configuration for symbol group"""
        from .config import AlertConfig
        group_name = AlertConfig.get_symbol_group(symbol)
        
        # Default configurations (same as global_radar_engine for consistency)
        configs = {
            "MAJORS": {
                "min_storm_volume": 2000000,  # $2M
                "min_cluster_volume": 3000000,  # $3M
                "convergence_bonus": 0.3
            },
            "LARGE_CAP": {
                "min_storm_volume": 1000000,  # $1M
                "min_cluster_volume": 1500000,  # $1.5M
                "convergence_bonus": 0.25
            },
            "MID_CAP": {
                "min_storm_volume": 500000,   # $0.5M
                "min_cluster_volume": 500000,   # $0.5M
                "convergence_bonus": 0.2
            }
        }
        
        return configs.get(group_name, configs["MID_CAP"])
    
    def _update_scoring_stats(self, score: EnhancedScore):
        """Update scoring statistics"""
        self.scoring_stats['total_scores'] += 1
        
        # Update average score
        total = self.scoring_stats['total_scores']
        current_avg = self.scoring_stats['avg_score']
        self.scoring_stats['avg_score'] = (current_avg * (total - 1) + score.final_score) / total
        
        # Update max score
        self.scoring_stats['max_score'] = max(self.scoring_stats['max_score'], score.final_score)
        
        # Update distribution
        self.scoring_stats['score_distribution'][score.signal_strength] += 1
    
    def update_historical_data(self, symbol: str, volume: float, price: float, timestamp: float):
        """Update historical data for context analysis"""
        current_time = timestamp
        
        # Update volume history
        if symbol not in self.volume_history:
            self.volume_history[symbol] = []
        
        self.volume_history[symbol].append((current_time, volume))
        
        # Update price history
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append((current_time, price))
        
        # Clean old data (keep last 1 hour)
        cutoff_time = current_time - 3600
        
        self.volume_history[symbol] = [
            (t, v) for t, v in self.volume_history[symbol] if t > cutoff_time
        ]
        
        self.price_history[symbol] = [
            (t, p) for t, p in self.price_history[symbol] if t > cutoff_time
        ]
    
    def get_scoring_statistics(self) -> Dict[str, Any]:
        """Get scoring engine statistics"""
        return {
            **self.scoring_stats,
            'volume_history_symbols': len(self.volume_history),
            'price_history_symbols': len(self.price_history),
            'market_context_cached': self.market_context_cache is not None,
            'context_cache_age': time.time() - self.context_cache_time if self.market_context_cache else None
        }
    
    def reset_statistics(self):
        """Reset scoring statistics"""
        self.scoring_stats = {
            'total_scores': 0,
            'avg_score': 0.0,
            'max_score': 0.0,
            'score_distribution': {'weak': 0, 'moderate': 0, 'strong': 0, 'extreme': 0}
        }
        logger.info("[SCORING] Statistics reset")


# Global instance
_enhanced_scoring_engine = None


def get_enhanced_scoring_engine() -> EnhancedScoringEngine:
    """Get enhanced scoring engine instance"""
    global _enhanced_scoring_engine
    if _enhanced_scoring_engine is None:
        _enhanced_scoring_engine = EnhancedScoringEngine()
    return _enhanced_scoring_engine


def calculate_enhanced_score(symbol: str, storm_info: Optional[StormInfo],
                           cluster_info: Optional[ClusterInfo]) -> EnhancedScore:
    """Convenience function to calculate enhanced score"""
    return get_enhanced_scoring_engine().calculate_enhanced_score(symbol, storm_info, cluster_info)
