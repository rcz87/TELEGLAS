import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger
from services.coinglass_api import CoinGlassAPI, safe_float, safe_int, safe_get, safe_list_get
from core.database import db_manager
from config.settings import settings


@dataclass
class LiquidationEvent:
    """Liquidation event data model"""

    symbol: str
    liquidation_usd: float
    side: str  # 'long' or 'short'
    timestamp: datetime
    exchange: Optional[str] = None


@dataclass
class LiquidationSignal:
    """Liquidation trading signal"""

    signal_type: str  # 'pump' or 'dump'
    symbol: str
    total_liquidation_usd: float
    long_liquidation_usd: float
    short_liquidation_usd: float
    long_short_ratio: float
    timestamp: datetime
    confidence_score: float  # 0.0 to 1.0


class LiquidationMonitor:
    """Monitors liquidation data with comprehensive error handling and zero-crash stability"""

    def __init__(self):
        self.api = CoinGlassAPI()
        self.threshold_usd = settings.LIQUIDATION_THRESHOLD_USD
        self.last_check_time = None
        self.liquidation_history = {}  # symbol -> list of recent liquidations

    async def start_monitoring(self):
        """Start liquidation monitoring loop"""
        logger.info("Starting liquidation monitoring")

        while True:
            try:
                await self.check_liquidations()
                await asyncio.sleep(settings.LIQUIDATION_POLL_INTERVAL)

            except Exception as e:
                logger.error(f"Error in liquidation monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds on error

    async def check_liquidations(self):
        """Check for significant liquidation events"""
        try:
            async with self.api as api:
                # Get liquidation data for major exchanges
                exchanges = ["Binance", "OKX", "Bybit"]
                all_data = {}
                
                for exchange in exchanges:
                    try:
                        data = await api.get_liquidation_coin_list(ex_name=exchange)
                        if data and data.get("success", False):
                            all_data[exchange] = data
                        else:
                            logger.warning(f"Failed to get liquidation data from {exchange}: {data.get('error', 'Unknown error') if data else 'No data'}")
                    except Exception as e:
                        logger.error(f"Error fetching liquidation data from {exchange}: {e}")
                        continue

                # Process data from all exchanges
                for exchange, data in all_data.items():
                    await self._process_liquidation_data(data, exchange)

        except Exception as e:
            logger.error(f"Error checking liquidations: {e}")

    async def _process_liquidation_data(self, data: Dict[str, Any], exchange: str):
        """Process liquidation data and identify significant events"""
        try:
            # Handle different response formats
            raw_data = data.get("data", [])
            
            # Handle case where data is not a list
            if isinstance(raw_data, dict):
                raw_data = [raw_data]  # Convert single dict to list
            elif not isinstance(raw_data, list):
                logger.warning(f"Unexpected liquidation data format from {exchange}: {type(raw_data)}")
                return

            if not raw_data:
                logger.debug(f"No liquidation data from {exchange}")
                return

            current_time = datetime.utcnow()
            processed_count = 0

            for i, item in enumerate(raw_data):
                try:
                    # Skip non-dict items
                    if not isinstance(item, dict):
                        logger.debug(f"Skipping non-dict liquidation item at index {i} from {exchange}")
                        continue

                    # Extract liquidation data safely
                    symbol = str(safe_get(item, "symbol", "")).upper().strip()
                    liquidation_usd_24h = safe_float(safe_get(item, "liquidation_usd_24h"), 0.0)
                    long_liq_24h = safe_float(safe_get(item, "long_liquidation_usd_24h"), 0.0)
                    short_liq_24h = safe_float(safe_get(item, "short_liquidation_usd_24h"), 0.0)

                    # Validate required fields
                    if not symbol:
                        logger.debug(f"Missing symbol in liquidation item at index {i} from {exchange}")
                        continue

                    # Validate liquidation amounts are reasonable
                    if liquidation_usd_24h < 0:
                        logger.debug(f"Negative liquidation amount for {symbol}: {liquidation_usd_24h}")
                        continue

                    if liquidation_usd_24h > 1_000_000_000:  # $1B is unrealistic
                        logger.debug(f"Unrealistic liquidation amount for {symbol}: {liquidation_usd_24h}")
                        continue

                    # Ensure consistency: total should equal sum of long + short
                    total_calculated = long_liq_24h + short_liq_24h
                    if abs(total_calculated - liquidation_usd_24h) > liquidation_usd_24h * 0.1:  # 10% tolerance
                        # Use calculated total if more reliable
                        liquidation_usd_24h = total_calculated

                    # Skip zero liquidations
                    if liquidation_usd_24h == 0:
                        continue

                    # Determine liquidation side based on which type dominates
                    side = "long" if long_liq_24h > short_liq_24h else "short"

                    # Create liquidation event
                    event = LiquidationEvent(
                        symbol=symbol,
                        liquidation_usd=liquidation_usd_24h,
                        side=side,
                        timestamp=current_time,
                        exchange=exchange,
                    )

                    # Add to history
                    if symbol not in self.liquidation_history:
                        self.liquidation_history[symbol] = []

                    self.liquidation_history[symbol].append(event)

                    # Keep only last 24 hours of data
                    cutoff_time = current_time - timedelta(hours=24)
                    self.liquidation_history[symbol] = [
                        e for e in self.liquidation_history[symbol] if e.timestamp > cutoff_time
                    ]

                    processed_count += 1

                    # Check for massive liquidations immediately for time-sensitive alerts
                    if liquidation_usd_24h >= self.threshold_usd:
                        await self._check_immediate_liquidations(symbol, exchange)

                except Exception as e:
                    logger.warning(f"Error processing liquidation item at index {i} from {exchange}: {e}")
                    continue

            if processed_count > 0:
                logger.debug(f"Processed {processed_count} liquidation events from {exchange}")

        except Exception as e:
            logger.error(f"Error processing liquidation data from {exchange}: {e}")

    async def _check_immediate_liquidations(self, symbol: str, exchange: str):
        """Check for immediate massive liquidations (time-sensitive)"""
        try:
            if symbol not in self.liquidation_history:
                return

            recent_liquidations = self.liquidation_history[symbol]
            if not recent_liquidations:
                return

            # Look at last 15 minutes for immediate alerts
            current_time = datetime.utcnow()
            min_ago = current_time - timedelta(minutes=15)
            last_15min_liqs = [l for l in recent_liquidations if l.timestamp > min_ago]

            if len(last_15min_liqs) > 0:
                signal = await self._analyze_liquidation_pattern(last_15min_liqs, "15m")
                if signal:
                    await self._handle_liquidation_signal(signal)

        except Exception as e:
            logger.error(f"Error checking immediate liquidations for {symbol}: {e}")

    async def _check_massive_liquidations(self, symbol: str):
        """Check if liquidations exceed threshold and generate signals"""
        try:
            if symbol not in self.liquidation_history:
                return

            recent_liquidations = self.liquidation_history[symbol]
            if not recent_liquidations:
                return

            # Calculate totals for different time windows
            current_time = datetime.utcnow()

            # Last 1 hour
            hour_ago = current_time - timedelta(hours=1)
            last_hour_liqs = [l for l in recent_liquidations if l.timestamp > hour_ago]

            # Check thresholds
            for time_window, liquidations in [
                ("1h", last_hour_liqs),
            ]:
                if not liquidations:
                    continue

                signal = await self._analyze_liquidation_pattern(liquidations, time_window)

                if signal:
                    await self._handle_liquidation_signal(signal)

        except Exception as e:
            logger.error(f"Error checking massive liquidations for {symbol}: {e}")

    async def _analyze_liquidation_pattern(
        self, liquidations: List[LiquidationEvent], time_window: str
    ) -> Optional[LiquidationSignal]:
        """Analyze liquidation pattern to generate trading signal"""
        if not liquidations:
            return None

        try:
            # Calculate totals
            total_liq = sum(l.liquidation_usd for l in liquidations)
            long_liq = sum(l.liquidation_usd for l in liquidations if l.side == "long")
            short_liq = sum(l.liquidation_usd for l in liquidations if l.side == "short")

            # Check if total liquidation exceeds threshold
            threshold_multiplier = 0.5 if time_window == "15m" else 1.0
            effective_threshold = self.threshold_usd * threshold_multiplier

            if total_liq < effective_threshold:
                return None

            # Calculate long/short ratio safely
            long_short_ratio = 1.0  # Default neutral ratio
            if short_liq > 0:
                long_short_ratio = long_liq / short_liq
            elif long_liq > 0:
                long_short_ratio = float('inf')  # All longs

            # Determine signal type and confidence
            signal_type = None
            confidence_score = 0.0

            if long_short_ratio > 2.0:  # Much more long liquidations
                signal_type = "dump"
                confidence_score = min(0.9, long_short_ratio / 5.0)
            elif long_short_ratio < 0.5:  # Much more short liquidations
                signal_type = "pump"
                confidence_score = min(0.9, (1 / max(0.1, long_short_ratio)) / 5.0)
            elif time_window == "15m" and total_liq > effective_threshold * 2:
                # Extreme liquidation in short time window
                signal_type = "dump" if long_liq > short_liq else "pump"
                confidence_score = min(0.8, total_liq / (effective_threshold * 3))

            # Additional confidence based on total volume
            volume_confidence = min(0.3, total_liq / (self.threshold_usd * 2))
            final_confidence = min(0.9, confidence_score + volume_confidence)

            if signal_type and final_confidence > 0.3:
                symbol = liquidations[0].symbol

                return LiquidationSignal(
                    signal_type=signal_type,
                    symbol=symbol,
                    total_liquidation_usd=total_liq,
                    long_liquidation_usd=long_liq,
                    short_liquidation_usd=short_liq,
                    long_short_ratio=long_short_ratio,
                    timestamp=datetime.utcnow(),
                    confidence_score=final_confidence,
                )

        except Exception as e:
            logger.error(f"Error analyzing liquidation pattern: {e}")

        return None

    async def _handle_liquidation_signal(self, signal: LiquidationSignal):
        """Handle generated liquidation signal"""
        try:
            emoji = "🔴" if signal.signal_type == "dump" else "🟢"
            direction = "DUMP" if signal.signal_type == "dump" else "PUMP"

            logger.info(
                f"🚨 LIQUIDATION SIGNAL: {direction} {signal.symbol} "
                f"(${signal.total_liquidation_usd:,.0f}, confidence: {signal.confidence_score:.2f})"
            )

            # Add system alert for broadcasting
            message = self._format_signal_message(signal)
            await db_manager.add_system_alert(
                alert_type="liquidation",
                message=message,
                data={
                    "signal_type": signal.signal_type,
                    "symbol": signal.symbol,
                    "total_liquidation_usd": signal.total_liquidation_usd,
                    "confidence_score": signal.confidence_score,
                    "long_short_ratio": signal.long_short_ratio,
                },
            )

            # Notify subscribed users
            await self._notify_subscribers(signal)

        except Exception as e:
            logger.error(f"Error handling liquidation signal: {e}")

    def _format_signal_message(self, signal: LiquidationSignal) -> str:
        """Format liquidation signal as readable message"""
        try:
            emoji = "🔴" if signal.signal_type == "dump" else "🟢"
            direction = "DUMP" if signal.signal_type == "dump" else "PUMP"

            # Format long/short ratio safely
            if signal.long_short_ratio == float('inf'):
                ratio_text = "∞ (All Longs)"
            elif signal.long_short_ratio == 0:
                ratio_text = "0 (All Shorts)"
            else:
                ratio_text = f"{signal.long_short_ratio:.2f}"

            message = (
                f"{emoji} {direction} ALERT {signal.symbol}\n"
                f"💰 Total Liquidations: ${signal.total_liquidation_usd:,.0f}\n"
                f"📉 Long Liquidations: ${signal.long_liquidation_usd:,.0f}\n"
                f"📈 Short Liquidations: ${signal.short_liquidation_usd:,.0f}\n"
                f"⚖️ L/S Ratio: {ratio_text}\n"
                f"🎯 Confidence: {signal.confidence_score:.0%}\n"
                f"🕐 Time: {signal.timestamp.strftime('%H:%M:%S UTC')}"
            )

            return message

        except Exception as e:
            logger.error(f"Error formatting liquidation signal message: {e}")
            return f"Liquidation Signal for {signal.symbol}"

    async def _notify_subscribers(self, signal: LiquidationSignal):
        """Notify users subscribed to symbol"""
        try:
            subscribers = await db_manager.get_subscribers_for_symbol(
                signal.symbol, "liquidation"
            )

            for subscription in subscribers:
                # Check if liquidation meets user's threshold
                if (
                    hasattr(subscription, 'threshold_usd')
                    and subscription.threshold_usd
                    and signal.total_liquidation_usd < subscription.threshold_usd
                ):
                    continue

                # In a real implementation, this would send via Telegram bot
                logger.info(
                    f"Would notify user {subscription.user_id} about {signal.symbol} liquidation"
                )

        except Exception as e:
            logger.error(f"Error notifying subscribers: {e}")

    async def get_symbol_liquidation_summary(
        self, symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Get liquidation summary for a specific symbol"""
        try:
            async with self.api as api:
                # Get liquidation data across all exchanges for this symbol
                data = await api.get_liquidation_exchange_list(symbol)

                if not data or not data.get("success", False):
                    logger.warning(f"Failed to get liquidation summary for {symbol}: {data.get('error') if data else 'No data'}")
                    return None

                # Handle different response formats
                raw_data = data.get("data", [])
                if isinstance(raw_data, dict):
                    raw_data = [raw_data]
                elif not isinstance(raw_data, list):
                    logger.warning(f"Unexpected liquidation summary format for {symbol}: {type(raw_data)}")
                    return None

                if not raw_data:
                    return None

                # Aggregate data from all exchanges
                total_liquidation_usd = 0.0
                total_long_liquidation = 0.0
                total_short_liquidation = 0.0
                exchange_count = 0

                for item in raw_data:
                    if not isinstance(item, dict):
                        continue

                    total_liquidation_usd += safe_float(safe_get(item, "liquidation_usd_24h"), 0.0)
                    total_long_liquidation += safe_float(safe_get(item, "long_liquidation_usd_24h"), 0.0)
                    total_short_liquidation += safe_float(safe_get(item, "short_liquidation_usd_24h"), 0.0)
                    exchange_count += 1

                return {
                    "symbol": symbol,
                    "liquidation_usd": total_liquidation_usd,
                    "long_liquidation_usd": total_long_liquidation,
                    "short_liquidation_usd": total_short_liquidation,
                    "exchange_count": exchange_count,
                    "price_change": 0.0,  # Not available in this endpoint
                    "volume_24h": 0.0,  # Not available in this endpoint
                    "last_update": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            logger.error(f"Error getting symbol liquidation summary for {symbol}: {e}")
            return None


# Global liquidation monitor instance
liquidation_monitor = LiquidationMonitor()
