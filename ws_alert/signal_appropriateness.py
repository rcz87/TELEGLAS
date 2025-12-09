"""
Signal Appropriateness Engine

Menilai kelayakan dan appropriateness dari sinyal trading berdasarkan
berbagai faktor seperti kondisi market, risk management, dan historikal performance.
"""

import asyncio
import logging
import time
import math
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Jenis-jenis sinyal"""
    LIQUIDATION = "liquidation"
    WHALE_ACTIVITY = "whale_activity"
    STORM_DETECTION = "storm_detection"
    VOLUME_SPIKE = "volume_spike"
    PRICE_MOVEMENT = "price_movement"
    FUNDING_RATE = "funding_rate"
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"

class SignalQuality(Enum):
    """Kualitas sinyal"""
    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    POOR = "poor"
    INVALID = "invalid"

class RiskLevel(Enum):
    """Tingkat risiko"""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"

@dataclass
class MarketCondition:
    """Kondisi market saat ini"""
    timestamp: float
    price: float
    volume_24h: float
    volatility_24h: float
    trend: str  # "bullish", "bearish", "sideways"
    momentum: float
    rsi: float
    macd: float
    bollinger_position: float  # -1 to 1, -1 = lower band, 1 = upper band
    volume_ratio: float  # current volume / average volume
    price_change_1h: float
    price_change_24h: float

@dataclass
class SignalData:
    """Data sinyal yang akan dievaluasi"""
    signal_id: str
    signal_type: SignalType
    symbol: str
    timestamp: float
    data: Dict[str, Any]
    source: str
    confidence: float = 0.0
    market_condition: Optional[MarketCondition] = None

@dataclass
class AppropriatenessScore:
    """Hasil evaluasi appropriateness sinyal"""
    signal_id: str
    overall_score: float  # 0-100
    quality: SignalQuality
    risk_level: RiskLevel
    appropriateness_factors: Dict[str, float]
    recommendation: str
    confidence: float
    timestamp: float
    detailed_analysis: Dict[str, Any] = field(default_factory=dict)

class SignalAppropriatenessEngine:
    """Engine untuk menilai appropriateness sinyal trading"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.signal_history: List[Dict[str, Any]] = []
        self.market_history: Dict[str, List[MarketCondition]] = {}
        self.performance_metrics: Dict[str, Dict[str, float]] = {}
        
        # Konfigurasi weights untuk faktor-faktor evaluasi
        self.weights = {
            'market_condition': 0.25,
            'signal_strength': 0.20,
            'historical_performance': 0.15,
            'risk_factors': 0.15,
            'timing_appropriateness': 0.10,
            'volume_confirmation': 0.10,
            'technical_alignment': 0.05
        }
        
        # Threshold untuk masing-masing kualitas
        self.quality_thresholds = {
            SignalQuality.EXCELLENT: 80,
            SignalQuality.GOOD: 60,
            SignalQuality.MODERATE: 40,
            SignalQuality.POOR: 20
        }
        
        # Threshold untuk risiko
        self.risk_thresholds = {
            RiskLevel.VERY_LOW: 20,
            RiskLevel.LOW: 40,
            RiskLevel.MODERATE: 60,
            RiskLevel.HIGH: 80
        }
    
    async def evaluate_signal(self, signal: SignalData) -> AppropriatenessScore:
        """Evaluasi appropriateness sinyal"""
        try:
            self.logger.info(f"Evaluating signal {signal.signal_id} for {signal.symbol}")
            
            # Get market condition jika tidak ada
            if not signal.market_condition:
                signal.market_condition = await self._get_market_condition(signal.symbol)
            
            # Hitung faktor-faktor evaluasi
            factors = await self._calculate_factors(signal)
            
            # Hitung overall score
            overall_score = self._calculate_overall_score(factors)
            
            # Tentukan kualitas dan risiko
            quality = self._determine_quality(overall_score)
            risk_level = self._determine_risk_level(factors)
            
            # Generate recommendation
            recommendation = self._generate_recommendation(overall_score, quality, risk_level, factors)
            
            # Hitung confidence
            confidence = self._calculate_confidence(factors, signal)
            
            # Detailed analysis
            detailed_analysis = await self._perform_detailed_analysis(signal, factors)
            
            score = AppropriatenessScore(
                signal_id=signal.signal_id,
                overall_score=overall_score,
                quality=quality,
                risk_level=risk_level,
                appropriateness_factors=factors,
                recommendation=recommendation,
                confidence=confidence,
                timestamp=time.time(),
                detailed_analysis=detailed_analysis
            )
            
            # Simpan ke history
            await self._save_signal_history(signal, score)
            
            return score
            
        except Exception as e:
            self.logger.error(f"Error evaluating signal {signal.signal_id}: {e}")
            return AppropriatenessScore(
                signal_id=signal.signal_id,
                overall_score=0.0,
                quality=SignalQuality.INVALID,
                risk_level=RiskLevel.VERY_HIGH,
                appropriateness_factors={},
                recommendation="INVALID_SIGNAL",
                confidence=0.0,
                timestamp=time.time()
            )
    
    async def _get_market_condition(self, symbol: str) -> MarketCondition:
        """Dapatkan kondisi market saat ini"""
        try:
            # Mock implementation - dalam production ini akan fetch data real
            base_price = 50000.0 + (hash(symbol) % 10000)
            
            return MarketCondition(
                timestamp=time.time(),
                price=base_price,
                volume_24h=1000000000.0 + (hash(symbol) % 500000000),
                volatility_24h=0.02 + (hash(symbol) % 100) / 10000,
                trend="bullish" if hash(symbol) % 3 == 0 else "bearish" if hash(symbol) % 3 == 1 else "sideways",
                momentum=(hash(symbol) % 200 - 100) / 100,
                rsi=30 + (hash(symbol) % 40),
                macd=(hash(symbol) % 200 - 100) / 1000,
                bollinger_position=(hash(symbol) % 200 - 100) / 100,
                volume_ratio=0.8 + (hash(symbol) % 40) / 100,
                price_change_1h=(hash(symbol) % 200 - 100) / 10000,
                price_change_24h=(hash(symbol) % 400 - 200) / 10000
            )
        except Exception as e:
            self.logger.error(f"Error getting market condition for {symbol}: {e}")
            # Return default market condition
            return MarketCondition(
                timestamp=time.time(),
                price=50000.0,
                volume_24h=1000000000.0,
                volatility_24h=0.02,
                trend="sideways",
                momentum=0.0,
                rsi=50.0,
                macd=0.0,
                bollinger_position=0.0,
                volume_ratio=1.0,
                price_change_1h=0.0,
                price_change_24h=0.0
            )
    
    async def _calculate_factors(self, signal: SignalData) -> Dict[str, float]:
        """Hitung semua faktor evaluasi"""
        factors = {}
        
        # Market Condition Factor
        factors['market_condition'] = await self._evaluate_market_condition(signal)
        
        # Signal Strength Factor
        factors['signal_strength'] = await self._evaluate_signal_strength(signal)
        
        # Historical Performance Factor
        factors['historical_performance'] = await self._evaluate_historical_performance(signal)
        
        # Risk Factors
        factors['risk_factors'] = await self._evaluate_risk_factors(signal)
        
        # Timing Appropriateness
        factors['timing_appropriateness'] = await self._evaluate_timing(signal)
        
        # Volume Confirmation
        factors['volume_confirmation'] = await self._evaluate_volume_confirmation(signal)
        
        # Technical Alignment
        factors['technical_alignment'] = await self._evaluate_technical_alignment(signal)
        
        return factors
    
    async def _evaluate_market_condition(self, signal: SignalData) -> float:
        """Evaluasi kondisi market"""
        if not signal.market_condition:
            return 50.0
        
        mc = signal.market_condition
        score = 50.0  # Base score
        
        # Adjust based on volatility (moderate volatility is good)
        if 0.01 <= mc.volatility_24h <= 0.05:
            score += 20
        elif mc.volatility_24h > 0.1:
            score -= 20
        
        # Adjust based on volume
        if mc.volume_ratio >= 1.5:
            score += 15
        elif mc.volume_ratio < 0.5:
            score -= 15
        
        # Adjust based on trend (depending on signal type)
        if signal.signal_type == SignalType.LIQUIDATION:
            # Liquidations are more valuable in extreme trends
            if mc.trend in ["bullish", "bearish"]:
                score += 10
        elif signal.signal_type == SignalType.WHALE_ACTIVITY:
            # Whale activity is good in any trend but better in strong trends
            if mc.trend != "sideways":
                score += 15
        
        # RSI consideration
        if 30 <= mc.rsi <= 70:  # Normal range
            score += 10
        elif mc.rsi < 20 or mc.rsi > 80:  # Extreme conditions
            if signal.signal_type == SignalType.LIQUIDATION:
                score += 15  # Liquidations likely in extreme conditions
            else:
                score -= 10
        
        return max(0, min(100, score))
    
    async def _evaluate_signal_strength(self, signal: SignalData) -> float:
        """Evaluasi kekuatan sinyal"""
        base_score = signal.confidence * 100  # Convert confidence to 0-100 scale
        
        # Adjust based on signal type and data
        if signal.signal_type == SignalType.LIQUIDATION:
            # Check liquidation size
            liq_amount = signal.data.get('quantity', 0)
            if liq_amount > 1000:  # Large liquidation
                base_score += 20
            elif liq_amount > 100:
                base_score += 10
        
        elif signal.signal_type == SignalType.WHALE_ACTIVITY:
            # Check transaction size
            whale_amount = signal.data.get('quantity', 0)
            if whale_amount > 500:  # Large whale
                base_score += 20
            elif whale_amount > 100:
                base_score += 10
        
        elif signal.signal_type == SignalType.STORM_DETECTION:
            # Check storm intensity
            storm_count = signal.data.get('liquidation_count', 0)
            if storm_count > 50:
                base_score += 25
            elif storm_count > 20:
                base_score += 15
        
        return max(0, min(100, base_score))
    
    async def _evaluate_historical_performance(self, signal: SignalData) -> float:
        """Evaluasi performa historikal sinyal serupa"""
        # Get historical performance for this signal type and symbol
        historical_key = f"{signal.signal_type.value}_{signal.symbol}"
        
        if historical_key not in self.performance_metrics:
            # Default performance
            return 60.0
        
        perf = self.performance_metrics[historical_key]
        
        # Calculate score based on success rate and profitability
        success_rate = perf.get('success_rate', 0.5)
        avg_profit = perf.get('avg_profit', 0.0)
        
        # Success rate contributes 70%, profit contributes 30%
        score = (success_rate * 70) + (min(max(avg_profit * 100, -30), 30) * 0.3)
        
        return max(0, min(100, score))
    
    async def _evaluate_risk_factors(self, signal: SignalData) -> float:
        """Evaluasi faktor risiko (higher is better = lower risk)"""
        score = 70.0  # Base score
        
        if not signal.market_condition:
            return score
        
        mc = signal.market_condition
        
        # Volatility risk
        if mc.volatility_24h > 0.1:
            score -= 30
        elif mc.volatility_24h > 0.05:
            score -= 15
        
        # Volume risk
        if mc.volume_ratio < 0.3:  # Very low volume
            score -= 25
        
        # Time risk (market hours, news events, etc.)
        current_hour = datetime.now().hour
        if 2 <= current_hour <= 6:  # Low activity hours
            score -= 10
        
        # Trend risk
        if mc.trend == "sideways":
            score -= 15  # Sideways markets are riskier for many signals
        
        return max(0, min(100, score))
    
    async def _evaluate_timing(self, signal: SignalData) -> float:
        """Evaluasi timing appropriateness"""
        score = 50.0
        
        # Check if similar signals occurred recently
        recent_signals = [
            s for s in self.signal_history[-50:]  # Last 50 signals
            if (s['symbol'] == signal.symbol and 
                s['type'] == signal.signal_type.value and
                time.time() - s['timestamp'] < 300)  # Within 5 minutes
        ]
        
        if recent_signals:
            # Similar signals recently - lower score (avoid redundancy)
            score -= len(recent_signals) * 10
        else:
            # No recent similar signals - higher score
            score += 20
        
        # Market timing
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 16:  # Active market hours
            score += 15
        elif 22 <= current_hour or current_hour <= 2:  # Low activity
            score -= 10
        
        return max(0, min(100, score))
    
    async def _evaluate_volume_confirmation(self, signal: SignalData) -> float:
        """Evaluasi konfirmasi volume"""
        if not signal.market_condition:
            return 50.0
        
        mc = signal.market_condition
        score = 50.0
        
        # Volume ratio
        if mc.volume_ratio >= 2.0:
            score += 30
        elif mc.volume_ratio >= 1.5:
            score += 20
        elif mc.volume_ratio >= 1.2:
            score += 10
        elif mc.volume_ratio < 0.5:
            score -= 20
        
        # Volume trend (increasing is good)
        if hasattr(mc, 'volume_trend') and mc.volume_trend > 0:
            score += 15
        
        return max(0, min(100, score))
    
    async def _evaluate_technical_alignment(self, signal: SignalData) -> float:
        """Evaluasi alignment dengan indikator teknikal"""
        if not signal.market_condition:
            return 50.0
        
        mc = signal.market_condition
        score = 50.0
        
        # RSI alignment
        if signal.signal_type == SignalType.LIQUIDATION:
            # Liquidations more likely at extremes
            if mc.rsi < 20 or mc.rsi > 80:
                score += 20
        elif signal.signal_type == SignalType.WHALE_ACTIVITY:
            # Whale accumulation/distribution
            if 30 <= mc.rsi <= 70:
                score += 15
        
        # MACD alignment
        if abs(mc.macd) > 0.5:  # Strong MACD
            score += 10
        
        # Bollinger Bands
        if abs(mc.bollinger_position) > 0.8:  # Near bands
            score += 10
        
        return max(0, min(100, score))
    
    def _calculate_overall_score(self, factors: Dict[str, float]) -> float:
        """Hitung overall score berdasarkan weights"""
        total_score = 0.0
        total_weight = 0.0
        
        for factor, score in factors.items():
            if factor in self.weights:
                weight = self.weights[factor]
                total_score += score * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 50.0
    
    def _determine_quality(self, overall_score: float) -> SignalQuality:
        """Tentukan kualitas sinyal berdasarkan score"""
        for quality, threshold in self.quality_thresholds.items():
            if overall_score >= threshold:
                return quality
        return SignalQuality.POOR
    
    def _determine_risk_level(self, factors: Dict[str, float]) -> RiskLevel:
        """Tentukan level risiko"""
        risk_score = 100 - factors.get('risk_factors', 50)  # Invert risk factors
        
        for risk_level, threshold in self.risk_thresholds.items():
            if risk_score <= threshold:
                return risk_level
        return RiskLevel.VERY_HIGH
    
    def _generate_recommendation(self, overall_score: float, quality: SignalQuality, 
                                risk_level: RiskLevel, factors: Dict[str, float]) -> str:
        """Generate rekomendasi berdasarkan evaluasi"""
        if quality == SignalQuality.INVALID:
            return "REJECT_SIGNAL"
        
        if quality == SignalQuality.EXCELLENT and risk_level in [RiskLevel.VERY_LOW, RiskLevel.LOW]:
            return "STRONG_BUY"
        elif quality == SignalQuality.GOOD and risk_level in [RiskLevel.VERY_LOW, RiskLevel.LOW, RiskLevel.MODERATE]:
            return "BUY"
        elif quality == SignalQuality.MODERATE and risk_level in [RiskLevel.LOW, RiskLevel.MODERATE]:
            return "CONSIDER"
        elif risk_level == RiskLevel.VERY_HIGH:
            return "AVOID"
        elif quality == SignalQuality.POOR:
            return "REJECT"
        else:
            return "HOLD"
    
    def _calculate_confidence(self, factors: Dict[str, float], signal: SignalData) -> float:
        """Hitung confidence score"""
        # Base confidence
        confidence = 50.0
        
        # Factor consistency (how consistent are the factor scores?)
        factor_values = list(factors.values())
        if len(factor_values) > 1:
            std_dev = statistics.stdev(factor_values)
            # Lower standard deviation = higher consistency = higher confidence
            consistency_score = max(0, 100 - (std_dev * 2))
            confidence = (confidence + consistency_score) / 2
        
        # Signal strength boosts confidence
        signal_strength = factors.get('signal_strength', 50)
        confidence = (confidence * 0.7) + (signal_strength * 0.3)
        
        return max(0, min(100, confidence))
    
    async def _perform_detailed_analysis(self, signal: SignalData, factors: Dict[str, float]) -> Dict[str, Any]:
        """Perform detailed analysis of the signal"""
        analysis = {
            'signal_summary': {
                'type': signal.signal_type.value,
                'symbol': signal.symbol,
                'source': signal.source,
                'timestamp': signal.timestamp
            },
            'factor_breakdown': factors,
            'strengths': [],
            'weaknesses': [],
            'market_context': {},
            'suggestions': []
        }
        
        # Identify strengths and weaknesses
        for factor, score in factors.items():
            if score >= 70:
                analysis['strengths'].append(f"{factor.replace('_', ' ').title()}: {score:.1f}")
            elif score <= 30:
                analysis['weaknesses'].append(f"{factor.replace('_', ' ').title()}: {score:.1f}")
        
        # Market context
        if signal.market_condition:
            mc = signal.market_condition
            analysis['market_context'] = {
                'trend': mc.trend,
                'volatility': f"{mc.volatility_24h:.2%}",
                'volume_ratio': f"{mc.volume_ratio:.2f}x",
                'rsi': f"{mc.rsi:.1f}",
                'price_change_24h': f"{mc.price_change_24h:.2%}"
            }
        
        # Generate suggestions
        if factors.get('market_condition', 50) < 40:
            analysis['suggestions'].append("Consider waiting for better market conditions")
        
        if factors.get('volume_confirmation', 50) < 40:
            analysis['suggestions'].append("Wait for volume confirmation before acting")
        
        if factors.get('timing_appropriateness', 50) < 40:
            analysis['suggestions'].append("Consider the timing - similar signals occurred recently")
        
        return analysis
    
    async def _save_signal_history(self, signal: SignalData, score: AppropriatenessScore):
        """Simpan signal ke history"""
        history_entry = {
            'signal_id': signal.signal_id,
            'type': signal.signal_type.value,
            'symbol': signal.symbol,
            'timestamp': signal.timestamp,
            'score': score.overall_score,
            'quality': score.quality.value,
            'recommendation': score.recommendation
        }
        
        self.signal_history.append(history_entry)
        
        # Keep only last 1000 signals
        if len(self.signal_history) > 1000:
            self.signal_history = self.signal_history[-1000:]
    
    def update_performance_metrics(self, signal_id: str, success: bool, profit_pct: float = 0.0):
        """Update performance metrics berdasarkan hasil aktual"""
        # Find the signal in history
        signal_entry = None
        for entry in self.signal_history:
            if entry['signal_id'] == signal_id:
                signal_entry = entry
                break
        
        if not signal_entry:
            return
        
        key = f"{signal_entry['type']}_{signal_entry['symbol']}"
        
        if key not in self.performance_metrics:
            self.performance_metrics[key] = {
                'total_signals': 0,
                'successful_signals': 0,
                'success_rate': 0.0,
                'total_profit': 0.0,
                'avg_profit': 0.0
            }
        
        metrics = self.performance_metrics[key]
        metrics['total_signals'] += 1
        
        if success:
            metrics['successful_signals'] += 1
            metrics['total_profit'] += profit_pct
        
        metrics['success_rate'] = metrics['successful_signals'] / metrics['total_signals']
        metrics['avg_profit'] = metrics['total_profit'] / metrics['total_signals']
    
    def get_signal_statistics(self, signal_type: Optional[SignalType] = None, 
                           symbol: Optional[str] = None, 
                           hours: int = 24) -> Dict[str, Any]:
        """Dapatkan statistik sinyal"""
        cutoff_time = time.time() - (hours * 3600)
        
        filtered_signals = [
            s for s in self.signal_history
            if s['timestamp'] >= cutoff_time and
            (signal_type is None or s['type'] == signal_type.value) and
            (symbol is None or s['symbol'] == symbol)
        ]
        
        if not filtered_signals:
            return {'total': 0, 'avg_score': 0, 'quality_distribution': {}}
        
        scores = [s['score'] for s in filtered_signals]
        avg_score = statistics.mean(scores)
        
        quality_counts = {}
        for signal in filtered_signals:
            quality = signal['quality']
            quality_counts[quality] = quality_counts.get(quality, 0) + 1
        
        return {
            'total': len(filtered_signals),
            'avg_score': avg_score,
            'min_score': min(scores),
            'max_score': max(scores),
            'quality_distribution': quality_counts,
            'recommendation_distribution': self._count_recommendations(filtered_signals)
        }
    
    def _count_recommendations(self, signals: List[Dict[str, Any]]) -> Dict[str, int]:
        """Hitung distribusi rekomendasi"""
        rec_counts = {}
        for signal in signals:
            rec = signal['recommendation']
            rec_counts[rec] = rec_counts.get(rec, 0) + 1
        return rec_counts

# Global instance
signal_appropriateness_engine = SignalAppropriatenessEngine()

def get_signal_appropriateness_engine() -> SignalAppropriatenessEngine:
    """Get global signal appropriateness engine instance"""
    return signal_appropriateness_engine
