import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger
from services.coinglass import CoinGlassAPI
from core.database import db_manager
from config.settings import settings


@dataclass
class FundingRateData:
    """Funding rate data model"""

    symbol: str
    exchange: str
    funding_rate: float  # As decimal (0.01 = 1%)
    next_funding_time: Optional[datetime]
    timestamp: datetime


@dataclass
class FundingRateSignal:
    """Funding rate trading signal"""

    signal_type: str  # 'reversal_long' or 'reversal_short'
    symbol: str
    current_rate: float
    average_rate: float
    extreme_threshold: float
    exchanges_count: int
    timestamp: datetime
    confidence_score: float  # 0.0 to 1.0


class FundingRateRadar:
    """Monitors funding rates and generates reversal signals"""

    def __init__(self):
        self.api = CoinGlassAPI()
        self.extreme_threshold = settings.EXTREME_FUNDING_RATE
        self.funding_history = {}  # symbol -> list of historical funding rates
        self.last_check_time = None

    async def start_monitoring(self):
        """Start the funding rate monitoring loop"""
        logger.info("Starting funding rate monitoring")

        while True:
            try:
                await self.check_funding_rates()
                await asyncio.sleep(settings.FUNDING_RATE_POLL_INTERVAL)

            except Exception as e:
                logger.error(f"Error in funding rate monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds on error

    async def check_funding_rates(self):
        """Check for extreme funding rates"""
        try:
            async with self.api:
                # Get funding rates for all exchanges
                funding_data = await self.api.get_funding_rate_exchange_list()

                if not funding_data.get("success", False):
                    logger.warning("Failed to get funding rate data")
                    return

                await self._process_funding_data(funding_data.get("data", []))

        except Exception as e:
            logger.error(f"Error checking funding rates: {e}")

    async def _process_funding_data(self, data: List[Dict[str, Any]]):
        """Process funding rate data and identify extreme rates"""
        current_time = datetime.utcnow()

        for item in data:
            try:
                # Extract funding rate data
                symbol = item.get("symbol", "").upper()
                exchange = item.get("exchange", "").lower()
                funding_rate = float(item.get("fundingRate", 0))
                next_funding_str = item.get("nextFundingTime", "")

                if not symbol or not exchange:
                    continue

                # Parse next funding time
                next_funding_time = self._parse_funding_time(next_funding_str)

                # Create funding rate data
                rate_data = FundingRateData(
                    symbol=symbol,
                    exchange=exchange,
                    funding_rate=funding_rate,
                    next_funding_time=next_funding_time,
                    timestamp=current_time,
                )

                # Store in history
                history_key = f"{symbol}_{exchange}"
                if history_key not in self.funding_history:
                    self.funding_history[history_key] = []

                self.funding_history[history_key].append(rate_data)

                # Keep only last 48 hours of data
                cutoff_time = current_time - timedelta(hours=48)
                self.funding_history[history_key] = [
                    r
                    for r in self.funding_history[history_key]
                    if r.timestamp > cutoff_time
                ]

            except (ValueError, KeyError) as e:
                logger.warning(f"Error processing funding rate item: {e}")
                continue

        # Analyze aggregated data for signals
        await self._analyze_aggregated_funding_rates()

    def _parse_funding_time(self, time_str: str) -> Optional[datetime]:
        """Parse next funding time from various formats"""
        if not time_str:
            return None

        try:
            # Try ISO format first
            if "T" in time_str:
                return datetime.fromisoformat(time_str.replace("Z", "+00:00"))

            # Try Unix timestamp (milliseconds)
            if time_str.replace(".", "").isdigit():
                timestamp = (
                    int(float(time_str)) / 1000
                )  # Convert to seconds if milliseconds
                return datetime.fromtimestamp(timestamp)

            # Try other formats
            formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]

            for fmt in formats:
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue

        except Exception:
            pass

        return None

    async def _analyze_aggregated_funding_rates(self):
        """Analyze aggregated funding rates across exchanges for signals"""
        # Group by symbol
        symbol_rates = {}

        for key, history in self.funding_history.items():
            if not history:
                continue

            symbol = key.split("_")[0]
            latest_data = history[-1]  # Get most recent data

            if symbol not in symbol_rates:
                symbol_rates[symbol] = []

            symbol_rates[symbol].append(latest_data)

        # Analyze each symbol
        for symbol, rates in symbol_rates.items():
            if len(rates) < 2:  # Need at least 2 exchanges for meaningful analysis
                continue

            signal = await self._analyze_symbol_funding_rates(symbol, rates)

            if signal:
                await self._handle_funding_signal(signal)

    async def _analyze_symbol_funding_rates(
        self, symbol: str, rates: List[FundingRateData]
    ) -> Optional[FundingRateSignal]:
        """Analyze funding rates for a specific symbol"""
        if len(rates) < 2:
            return None

        # Calculate average funding rate across exchanges
        current_rates = [r.funding_rate for r in rates]
        average_rate = sum(current_rates) / len(current_rates)

        # Calculate historical average (last 24 hours)
        historical_rates = []
        current_time = datetime.utcnow()
        day_ago = current_time - timedelta(hours=24)

        for key, history in self.funding_history.items():
            if key.startswith(f"{symbol}_"):
                for rate_data in history:
                    if rate_data.timestamp > day_ago:
                        historical_rates.append(rate_data.funding_rate)

        if not historical_rates:
            historical_average = 0
        else:
            historical_average = sum(historical_rates) / len(historical_rates)

        # Check for extreme funding rates
        extreme_positive = (
            average_rate > self.extreme_threshold
        )  # Very high positive rate
        extreme_negative = (
            average_rate < -self.extreme_threshold
        )  # Very high negative rate

        if not (extreme_positive or extreme_negative):
            return None

        # Determine signal type and confidence
        signal_type = None
        confidence_score = 0.0

        if extreme_positive:
            # Very high positive funding rate suggests over-leveraged longs
            signal_type = "reversal_short"
            confidence_score = min(0.9, average_rate / (self.extreme_threshold * 2))
        elif extreme_negative:
            # Very high negative funding rate suggests over-leveraged shorts
            signal_type = "reversal_long"
            confidence_score = min(
                0.9, abs(average_rate) / (self.extreme_threshold * 2)
            )

        # Additional confidence based on deviation from historical average
        deviation = abs(average_rate - historical_average)
        deviation_confidence = min(0.3, deviation / 0.02)  # Max 30% from deviation
        final_confidence = min(0.9, confidence_score + deviation_confidence)

        if final_confidence > 0.4:  # Minimum confidence threshold
            return FundingRateSignal(
                signal_type=signal_type,
                symbol=symbol,
                current_rate=average_rate,
                average_rate=historical_average,
                extreme_threshold=self.extreme_threshold,
                exchanges_count=len(rates),
                timestamp=datetime.utcnow(),
                confidence_score=final_confidence,
            )

        return None

    async def _handle_funding_signal(self, signal: FundingRateSignal):
        """Handle generated funding rate signal"""
        direction_emoji = "🔴" if signal.signal_type == "reversal_short" else "🟢"
        direction = (
            "SHORT REVERSAL"
            if signal.signal_type == "reversal_short"
            else "LONG REVERSAL"
        )
        rate_emoji = "📈" if signal.current_rate > 0 else "📉"

        logger.info(
            f"{direction_emoji} FUNDING SIGNAL: {direction} {signal.symbol} "
            f"Rate: {signal.current_rate:.4f} ({'extreme high' if signal.current_rate > 0 else 'extreme low'}) "
            f"(confidence: {signal.confidence_score:.2f})"
        )

        # Add system alert for broadcasting
        message = self._format_signal_message(signal)
        await db_manager.add_system_alert(
            alert_type="funding_rate",
            message=message,
            data={
                "signal_type": signal.signal_type,
                "symbol": signal.symbol,
                "current_rate": signal.current_rate,
                "average_rate": signal.average_rate,
                "exchanges_count": signal.exchanges_count,
                "confidence_score": signal.confidence_score,
            },
        )

        # Notify subscribed users
        await self._notify_subscribers(signal)

    def _format_signal_message(self, signal: FundingRateSignal) -> str:
        """Format funding rate signal as readable message"""
        direction_emoji = "🔴" if signal.signal_type == "reversal_short" else "🟢"
        direction = (
            "SHORT REVERSAL"
            if signal.signal_type == "reversal_short"
            else "LONG REVERSAL"
        )
        rate_emoji = "📈" if signal.current_rate > 0 else "📉"
        rate_text = "EXTREME HIGH" if signal.current_rate > 0 else "EXTREME LOW"

        message = (
            f"{direction_emoji} {direction} ALERT {signal.symbol}\n"
            f"{rate_emoji} Funding Rate: {signal.current_rate:.4f} ({rate_text})\n"
            f"📊 24h Avg: {signal.average_rate:.4f}\n"
            f"🏦 Exchanges: {signal.exchanges_count}\n"
            f"🎯 Confidence: {signal.confidence_score:.0%}\n"
            f"🕐 Time: {signal.timestamp.strftime('%H:%M:%S UTC')}\n"
            f"⚠️ Potential funding squeeze incoming!"
        )

        return message

    async def _notify_subscribers(self, signal: FundingRateSignal):
        """Notify users subscribed to the symbol"""
        try:
            subscribers = await db_manager.get_subscribers_for_symbol(
                signal.symbol, "funding"
            )

            for subscription in subscribers:
                # In a real implementation, this would send via Telegram bot
                logger.info(
                    f"Would notify user {subscription.user_id} about {signal.symbol} funding rate signal"
                )

        except Exception as e:
            logger.error(f"Error notifying funding rate subscribers: {e}")

    async def get_symbol_funding_rates(self, symbol: str) -> List[Dict[str, Any]]:
        """Get current funding rates for a specific symbol across exchanges"""
        try:
            async with self.api:
                data = await self.api.get_funding_rate_exchange_list(symbol=symbol)

                if not data.get("success", False):
                    return []

                funding_rates = []
                for item in data.get("data", []):
                    exchange = item.get("exchange", "").lower()
                    funding_rate = float(item.get("fundingRate", 0))
                    next_funding_time = item.get("nextFundingTime", "")

                    if exchange and funding_rate != 0:
                        funding_rates.append(
                            {
                                "exchange": exchange,
                                "funding_rate": funding_rate,
                                "funding_rate_percentage": funding_rate * 100,
                                "next_funding_time": next_funding_time,
                                "is_extreme_high": funding_rate
                                > self.extreme_threshold,
                                "is_extreme_low": funding_rate
                                < -self.extreme_threshold,
                            }
                        )

                # Sort by absolute funding rate (most extreme first)
                funding_rates.sort(key=lambda x: abs(x["funding_rate"]), reverse=True)

                return funding_rates

        except Exception as e:
            logger.error(f"Error getting symbol funding rates: {e}")
            return []

    async def get_fear_greed_index(self) -> Optional[Dict[str, Any]]:
        """Get Fear & Greed Index for market sentiment"""
        try:
            async with self.api:
                data = await self.api.get_fear_greed_history()

                if not data.get("success", False):
                    return None

                fear_greed_data = data.get("data", [])
                if not fear_greed_data:
                    return None

                # Get the most recent data
                latest = fear_greed_data[-1]

                return {
                    "value": int(latest.get("value", 0)),
                    "classification": latest.get("value_classification", "Unknown"),
                    "timestamp": latest.get("timestamp", ""),
                    "interpretation": self._interpret_fear_greed(
                        int(latest.get("value", 0))
                    ),
                }

        except Exception as e:
            logger.error(f"Error getting Fear & Greed Index: {e}")
            return None

    def _interpret_fear_greed(self, value: int) -> str:
        """Interpret Fear & Greed Index value"""
        if value <= 20:
            return "Extreme Fear - Potential buying opportunity"
        elif value <= 40:
            return "Fear - Market fearful, consider accumulation"
        elif value <= 60:
            return "Neutral - Balanced market conditions"
        elif value <= 80:
            return "Greed - Market getting overheated"
        else:
            return "Extreme Greed - High risk of correction"


# Global funding rate radar instance
funding_rate_radar = FundingRateRadar()
