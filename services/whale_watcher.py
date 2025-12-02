import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger
from services.coinglass import CoinGlassAPI
from core.database import db_manager
from config.settings import settings


@dataclass
class WhaleTransaction:
    """Whale transaction data model"""

    transaction_hash: str
    symbol: str
    side: str  # 'buy' or 'sell'
    amount_usd: float
    price: float
    quantity: float
    timestamp: datetime
    exchange: str = "hyperliquid"


@dataclass
class WhaleSignal:
    """Whale trading signal"""

    signal_type: str  # 'accumulation' or 'distribution'
    symbol: str
    transaction_amount_usd: float
    side: str
    price: float
    timestamp: datetime
    confidence_score: float  # 0.0 to 1.0


class WhaleWatcher:
    """Monitors whale transactions and generates accumulation/distribution signals"""

    def __init__(self):
        self.api = CoinGlassAPI()
        self.threshold_usd = settings.WHALE_TRANSACTION_THRESHOLD_USD
        self.whale_history = {}  # symbol -> list of recent whale transactions
        self.last_check_time = None

    async def start_monitoring(self):
        """Start the whale monitoring loop"""
        logger.info("Starting whale monitoring")

        while True:
            try:
                await self.check_whale_transactions()
                await asyncio.sleep(settings.WHALE_POLL_INTERVAL)

            except Exception as e:
                logger.error(f"Error in whale monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds on error

    async def check_whale_transactions(self):
        """Check for significant whale transactions"""
        try:
            async with self.api:
                # Get whale alerts from Hyperliquid
                whale_data = await self.api.get_whale_alert_hyperliquid()

                if not whale_data.get("success", False):
                    logger.warning("Failed to get whale data")
                    return

                await self._process_whale_data(whale_data.get("data", []))

        except Exception as e:
            logger.error(f"Error checking whale transactions: {e}")

    async def _process_whale_data(self, data: List[Dict[str, Any]]):
        """Process whale transaction data and identify significant events"""
        current_time = datetime.utcnow()

        for item in data:
            try:
                # Extract transaction data
                transaction_hash = item.get("hash", "")
                symbol = item.get("symbol", "").upper()
                side = item.get("side", "").lower()
                amount_usd = float(item.get("amountUSD", 0))
                price = float(item.get("price", 0))
                quantity = float(item.get("quantity", 0))
                timestamp_str = item.get("timestamp", "")

                # Validate required fields
                if not all([transaction_hash, symbol, side, amount_usd > 0]):
                    continue

                # Check if transaction meets threshold
                if amount_usd < self.threshold_usd:
                    continue

                # Parse timestamp
                timestamp = self._parse_timestamp(timestamp_str)
                if not timestamp:
                    timestamp = current_time

                # Check if already processed
                if await db_manager.is_whale_transaction_cached(transaction_hash):
                    continue

                # Create whale transaction
                transaction = WhaleTransaction(
                    transaction_hash=transaction_hash,
                    symbol=symbol,
                    side=side,
                    amount_usd=amount_usd,
                    price=price,
                    quantity=quantity,
                    timestamp=timestamp,
                )

                # Cache transaction
                await db_manager.cache_whale_transaction(
                    transaction_hash, symbol, side, amount_usd, timestamp.isoformat()
                )

                # Add to history
                if symbol not in self.whale_history:
                    self.whale_history[symbol] = []

                self.whale_history[symbol].append(transaction)

                # Keep only last 24 hours of data
                cutoff_time = current_time - timedelta(hours=24)
                self.whale_history[symbol] = [
                    t for t in self.whale_history[symbol] if t.timestamp > cutoff_time
                ]

                # Generate signal for this transaction
                signal = await self._analyze_whale_transaction(transaction)

                if signal:
                    await self._handle_whale_signal(signal)

            except (ValueError, KeyError) as e:
                logger.warning(f"Error processing whale transaction item: {e}")
                continue

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp from various formats"""
        if not timestamp_str:
            return None

        try:
            # Try ISO format first
            if "T" in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

            # Try Unix timestamp
            if timestamp_str.isdigit():
                return datetime.fromtimestamp(int(timestamp_str))

            # Try other formats
            formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]

            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue

        except Exception:
            pass

        return None

    async def _analyze_whale_transaction(
        self, transaction: WhaleTransaction
    ) -> Optional[WhaleSignal]:
        """Analyze whale transaction to generate trading signal"""
        # Base confidence on transaction size
        size_multiplier = transaction.amount_usd / self.threshold_usd
        base_confidence = min(0.9, size_multiplier / 5.0)  # Cap at 90%

        # Determine signal type
        signal_type = "accumulation" if transaction.side == "buy" else "distribution"

        # Additional analysis: check recent whale activity pattern
        pattern_confidence = await self._analyze_whale_pattern(
            transaction.symbol, transaction.side
        )

        # Combine confidences
        final_confidence = (base_confidence + pattern_confidence) / 2

        if final_confidence > 0.3:  # Minimum confidence threshold
            return WhaleSignal(
                signal_type=signal_type,
                symbol=transaction.symbol,
                transaction_amount_usd=transaction.amount_usd,
                side=transaction.side,
                price=transaction.price,
                timestamp=datetime.utcnow(),
                confidence_score=final_confidence,
            )

        return None

    async def _analyze_whale_pattern(self, symbol: str, current_side: str) -> float:
        """Analyze recent whale activity pattern for confidence boost"""
        if symbol not in self.whale_history:
            return 0.0

        recent_transactions = self.whale_history[symbol]
        if len(recent_transactions) < 2:
            return 0.0

        # Look at last hour of activity
        current_time = datetime.utcnow()
        hour_ago = current_time - timedelta(hours=1)
        recent_hour = [t for t in recent_transactions if t.timestamp > hour_ago]

        if len(recent_hour) < 2:
            return 0.0

        # Calculate pattern consistency
        same_side_count = sum(1 for t in recent_hour if t.side == current_side)
        consistency_ratio = same_side_count / len(recent_hour)

        # Pattern confidence based on consistency
        if consistency_ratio > 0.8:  # Very consistent
            return 0.3
        elif consistency_ratio > 0.6:  # Moderately consistent
            return 0.15
        else:  # Mixed signals
            return 0.0

    async def _handle_whale_signal(self, signal: WhaleSignal):
        """Handle generated whale signal"""
        action_emoji = "🟢" if signal.signal_type == "accumulation" else "🔴"
        side_emoji = "📈" if signal.side == "buy" else "📉"

        logger.info(
            f"{action_emoji} WHALE SIGNAL: {signal.signal_type.upper()} {signal.symbol} "
            f"${signal.transaction_amount_usd:,.0f} {signal.side} "
            f"(confidence: {signal.confidence_score:.2f})"
        )

        # Add system alert for broadcasting
        message = self._format_signal_message(signal)
        await db_manager.add_system_alert(
            alert_type="whale",
            message=message,
            data={
                "signal_type": signal.signal_type,
                "symbol": signal.symbol,
                "transaction_amount_usd": signal.transaction_amount_usd,
                "side": signal.side,
                "price": signal.price,
                "confidence_score": signal.confidence_score,
            },
        )

        # Notify subscribed users
        await self._notify_subscribers(signal)

    def _format_signal_message(self, signal: WhaleSignal) -> str:
        """Format whale signal as readable message"""
        action_emoji = "🟢" if signal.signal_type == "accumulation" else "🔴"
        side_emoji = "📈" if signal.side == "buy" else "📉"
        action = (
            "ACCUMULATION" if signal.signal_type == "accumulation" else "DISTRIBUTION"
        )

        message = (
            f"{action_emoji} {action} ALERT {signal.symbol}\n"
            f"{side_emoji} Whale {signal.side.upper()} ${signal.transaction_amount_usd:,.0f}\n"
            f"💲 Price: ${signal.price:,.4f}\n"
            f"🎯 Confidence: {signal.confidence_score:.0%}\n"
            f"🕐 Time: {signal.timestamp.strftime('%H:%M:%S UTC')}\n"
            f"🏦 Exchange: Hyperliquid"
        )

        return message

    async def _notify_subscribers(self, signal: WhaleSignal):
        """Notify users subscribed to the symbol"""
        try:
            subscribers = await db_manager.get_subscribers_for_symbol(
                signal.symbol, "whale"
            )

            for subscription in subscribers:
                # Check if transaction meets user's threshold
                if (
                    subscription.threshold_usd
                    and signal.transaction_amount_usd < subscription.threshold_usd
                ):
                    continue

                # In a real implementation, this would send via Telegram bot
                logger.info(
                    f"Would notify user {subscription.user_id} about {signal.symbol} whale activity"
                )

        except Exception as e:
            logger.error(f"Error notifying whale subscribers: {e}")

    async def get_recent_whale_activity(
        self, symbol: str = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get recent whale activity for a symbol or all symbols"""
        try:
            if symbol and symbol in self.whale_history:
                transactions = self.whale_history[symbol]
            else:
                # Get transactions from all symbols
                all_transactions = []
                for symbol_txs in self.whale_history.values():
                    all_transactions.extend(symbol_txs)
                transactions = all_transactions

            # Sort by timestamp (most recent first) and limit
            transactions.sort(key=lambda x: x.timestamp, reverse=True)
            recent_transactions = transactions[:limit]

            return [
                {
                    "symbol": tx.symbol,
                    "side": tx.side,
                    "amount_usd": tx.amount_usd,
                    "price": tx.price,
                    "timestamp": tx.timestamp.isoformat(),
                    "transaction_hash": tx.transaction_hash,
                }
                for tx in recent_transactions
            ]

        except Exception as e:
            logger.error(f"Error getting recent whale activity: {e}")
            return []


# Global whale watcher instance
whale_watcher = WhaleWatcher()
