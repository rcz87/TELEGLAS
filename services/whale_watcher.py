import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger
from services.coinglass_api import coinglass_api, safe_float, safe_int, safe_get, safe_list_get
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
    """Monitors whale transactions with comprehensive error handling and zero-crash stability"""

    def __init__(self):
        self.api = coinglass_api
        self.threshold_usd = settings.WHALE_TRANSACTION_THRESHOLD_USD
        self.whale_history = {}  # symbol -> list of recent whale transactions
        self.last_check_time = None
        
        # Debounce tracking: symbol -> last_alert_time
        self.last_alert_time = {}
        self.debounce_minutes = 5  # Maximum 1 alert per symbol per 5 minutes
        
        # Connection safety
        self.semaphore = asyncio.Semaphore(3)  # Limit concurrent API calls
        self.running = False

    async def start_monitoring(self):
        """Start the whale monitoring loop"""
        logger.info("[START] Starting whale monitoring")
        self.running = True

        # Initialize session once for continuous operation
        await self.api._ensure_session()

        try:
            while self.running:
                try:
                    async with self.semaphore:  # Limit concurrent API calls
                        await asyncio.wait_for(
                            self.check_whale_transactions(),
                            timeout=30.0  # 30 second timeout for API calls
                        )
                    await asyncio.sleep(settings.WHALE_POLL_INTERVAL)

                except asyncio.TimeoutError:
                    logger.warning("[TIMEOUT] Whale monitoring API call timed out, continuing...")
                    await asyncio.sleep(settings.WHALE_POLL_INTERVAL)
                except Exception as e:
                    error_type = type(e).__name__
                    logger.error(f"[LOOP_ERROR] {error_type} in whale monitoring loop: {str(e)}")
                    # Continue the loop - don't let one error stop the monitoring
                    await asyncio.sleep(30)  # Wait 30 seconds on error

        finally:
            # Clean up session when stopping
            if hasattr(self.api, 'close_session'):
                await self.api.close_session()
            logger.info("[STOP] Whale monitoring stopped")

    async def stop_monitoring(self):
        """Stop the whale monitoring loop gracefully"""
        logger.info("[STOP] Stopping whale monitoring...")
        self.running = False

    async def check_whale_transactions(self):
        """Check for significant whale transactions"""
        try:
            # Get whale alerts from Hyperliquid (session already initialized)
            whale_data = await self.api.get_whale_alert_hyperliquid()

            if not whale_data.get("success", False):
                error_msg = whale_data.get('error', 'Unknown error')
                error_type = type(error_msg).__name__
                logger.error(f"[COINGLASS_ERROR] Whale request failed: {error_type} - {error_msg}")
                return

            # Handle different response formats
            data = whale_data.get("data", [])
            
            # Handle case where data is not a list (could be dict or single item)
            if isinstance(data, dict):
                data = [data]  # Convert single dict to list
            elif not isinstance(data, list):
                logger.warning(f"[DATA_FORMAT] Unexpected whale data format: {type(data)} - Expected list or dict")
                return

            await self._process_whale_data(data)

        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"[WHALE_WATCHER_ERROR] {error_type} in whale transaction check: {str(e)}")
            # Don't re-raise - let the monitoring loop continue
            return

    async def _process_whale_data(self, data: List[Dict[str, Any]]):
        """Process whale transaction data and identify significant events"""
        if not data or not isinstance(data, list):
            logger.debug("No whale data to process")
            return

        current_time = datetime.utcnow()
        processed_count = 0

        for i, item in enumerate(data):
            try:
                # Skip non-dict items
                if not isinstance(item, dict):
                    logger.debug(f"Skipping non-dict whale item at index {i}")
                    continue

                # Extract transaction data safely
                transaction_hash = str(safe_get(item, "hash", "")).strip()
                symbol = str(safe_get(item, "symbol", "")).upper().strip()
                side = str(safe_get(item, "side", "")).lower().strip()
                amount_usd = safe_float(safe_get(item, "amountUSD"), 0.0)
                price = safe_float(safe_get(item, "price"), 0.0)
                quantity = safe_float(safe_get(item, "quantity"), 0.0)
                timestamp_str = str(safe_get(item, "timestamp", "")).strip()

                # Validate required fields
                if not all([transaction_hash, symbol, side]):
                    logger.debug(f"Missing required fields for whale transaction at index {i}")
                    continue

                # Validate side
                if side not in ["buy", "sell"]:
                    logger.debug(f"Invalid side '{side}' for whale transaction {transaction_hash}")
                    continue

                # Check if transaction meets threshold
                if amount_usd < self.threshold_usd:
                    continue

                # Validate amount is reasonable (not ridiculously high)
                if amount_usd > 1_000_000_000:  # $1B is unrealistic for single transaction
                    logger.debug(f"Skipping unrealistic whale amount: ${amount_usd:,.0f}")
                    continue

                # Parse timestamp
                timestamp = self._parse_timestamp(timestamp_str)
                if not timestamp:
                    timestamp = current_time

                # Check if already processed
                try:
                    if await db_manager.is_whale_transaction_cached(transaction_hash):
                        continue
                except Exception as e:
                    logger.warning(f"Error checking whale transaction cache: {e}")
                    # Continue processing even if cache check fails

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
                try:
                    await db_manager.cache_whale_transaction(
                        transaction_hash, symbol, side, amount_usd, timestamp.isoformat()
                    )
                except Exception as e:
                    logger.warning(f"Error caching whale transaction: {e}")

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

                processed_count += 1

            except Exception as e:
                logger.warning(f"Error processing whale transaction item at index {i}: {e}")
                continue

        if processed_count > 0:
            logger.info(f"Processed {processed_count} whale transactions")

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp from various formats"""
        if not timestamp_str:
            return None

        try:
            # Try ISO format first
            if "T" in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

            # Try Unix timestamp (milliseconds or seconds)
            if timestamp_str.replace(".", "").replace("-", "").isdigit():
                timestamp = safe_float(timestamp_str, 0)
                if timestamp > 0:
                    # Convert to seconds if milliseconds
                    if timestamp > 1e12:  # Milliseconds
                        timestamp = timestamp / 1000
                    elif timestamp > 1e10:  # Seconds but with extra digits
                        timestamp = timestamp / 1000
                    return datetime.fromtimestamp(timestamp)

            # Try other formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%d",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue

        except Exception as e:
            logger.debug(f"Failed to parse timestamp '{timestamp_str}': {e}")

        return None

    async def _analyze_whale_transaction(
        self, transaction: WhaleTransaction
    ) -> Optional[WhaleSignal]:
        """Analyze whale transaction to generate trading signal"""
        try:
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

        except Exception as e:
            logger.error(f"Error analyzing whale transaction: {e}")

        return None

    async def _analyze_whale_pattern(self, symbol: str, current_side: str) -> float:
        """Analyze recent whale activity pattern for confidence boost"""
        try:
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

        except Exception as e:
            logger.error(f"Error analyzing whale pattern for {symbol}: {e}")
            return 0.0

    async def _handle_whale_signal(self, signal: WhaleSignal):
        """Handle generated whale signal with debounce logic"""
        try:
            # Check debounce logic - only allow 1 alert per symbol per X minutes
            current_time = datetime.utcnow()
            symbol = signal.symbol
            
            # Check if we recently sent an alert for this symbol
            if symbol in self.last_alert_time:
                time_since_last = current_time - self.last_alert_time[symbol]
                if time_since_last < timedelta(minutes=self.debounce_minutes):
                    logger.debug(
                        f"[DEBOUNCE] Skipping whale alert for {symbol} - "
                        f"last alert was {time_since_last.total_seconds():.0f}s ago"
                    )
                    return

            # Update last alert time
            self.last_alert_time[symbol] = current_time

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

        except Exception as e:
            logger.error(f"Error handling whale signal: {e}")

    def _format_signal_message(self, signal: WhaleSignal) -> str:
        """Format whale signal as readable message"""
        try:
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

        except Exception as e:
            logger.error(f"Error formatting whale signal message: {e}")
            return f"Whale Signal for {signal.symbol}"

    async def _notify_subscribers(self, signal: WhaleSignal):
        """Notify users subscribed to the symbol"""
        try:
            subscribers = await db_manager.get_subscribers_for_symbol(
                signal.symbol, "whale"
            )

            for subscription in subscribers:
                # Check if transaction meets user's threshold
                if (
                    hasattr(subscription, 'threshold_usd')
                    and subscription.threshold_usd
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
