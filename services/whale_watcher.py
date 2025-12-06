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
        """Start whale monitoring loop"""
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
                    # Continue to loop - don't let one error stop the monitoring
                    await asyncio.sleep(30)  # Wait 30 seconds on error

        finally:
            # Clean up session when stopping
            if hasattr(self.api, 'close_session'):
                await self.api.close_session()
            logger.info("[STOP] Whale monitoring stopped")

    async def stop_monitoring(self):
        """Stop whale monitoring loop gracefully"""
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
            # Don't re-raise - let's monitoring loop continue
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

                # FIXED: Extract transaction data with correct API field mapping
                # API response fields: user, symbol, position_action, position_value_usd, entry_price, position_size, create_time
                transaction_hash = str(safe_get(item, "user", "")).strip()  # API uses "user" not "hash"
                symbol = str(safe_get(item, "symbol", "")).upper().strip()
                
                # FIXED: Map position_action to side (2=sell, 1=buy based on typical API conventions)
                position_action = safe_int(safe_get(item, "position_action", 0))
                if position_action == 2:
                    side = "sell"
                elif position_action == 1:
                    side = "buy"
                else:
                    side = "unknown"
                
                # FIXED: Use position_value_usd instead of amountUSD
                amount_usd = safe_float(safe_get(item, "position_value_usd"), 0.0)
                price = safe_float(safe_get(item, "entry_price"), 0.0)
                quantity = safe_float(safe_get(item, "position_size"), 0.0)
                
                # FIXED: Use create_time instead of timestamp
                create_time = safe_int(safe_get(item, "create_time", 0))
                timestamp_str = str(create_time) if create_time > 0 else ""

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
        """Notify users subscribed to symbol"""
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
        """Get recent whale activity for a symbol or all symbols with API fallback"""
        try:
            # Try to get from memory first
            if self.whale_history:
                if symbol and symbol in self.whale_history:
                    transactions = self.whale_history[symbol]
                else:
                    # Get transactions from all symbols
                    all_transactions = []
                    for symbol_txs in self.whale_history.values():
                        all_transactions.extend(symbol_txs)
                    transactions = all_transactions

                if transactions:
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

            # Fallback: Get fresh data from API
            logger.info(f"[WHALE_FALLBACK] No memory data, fetching fresh whale data from API")
            return await self._get_fresh_whale_activity(symbol, limit)

        except Exception as e:
            logger.error(f"Error getting recent whale activity: {e}")
            return []

    async def _get_fresh_whale_activity(
        self, symbol: str = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get fresh whale activity directly from API"""
        try:
            # Get whale alerts from Hyperliquid
            whale_data = await self.api.get_whale_alert_hyperliquid()

            if not whale_data.get("success", False):
                logger.warning(f"[WHALE_API] Failed to get fresh whale data: {whale_data.get('error', 'Unknown error')}")
                return []

            # Handle different response formats
            data = whale_data.get("data", [])
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                return []

            current_time = datetime.utcnow()
            transactions = []

            for item in data:
                try:
                    if not isinstance(item, dict):
                        continue

                    # Extract transaction data with correct API field mapping
                    transaction_hash = str(safe_get(item, "user", "")).strip()
                    item_symbol = str(safe_get(item, "symbol", "")).upper().strip()
                    
                    # Map position_action to side
                    position_action = safe_int(safe_get(item, "position_action", 0))
                    if position_action == 2:
                        side = "sell"
                    elif position_action == 1:
                        side = "buy"
                    else:
                        continue  # Skip unknown sides
                    
                    # Use position_value_usd
                    amount_usd = safe_float(safe_get(item, "position_value_usd"), 0.0)
                    price = safe_float(safe_get(item, "entry_price"), 0.0)
                    
                    # Parse timestamp
                    create_time = safe_int(safe_get(item, "create_time", 0))
                    timestamp = self._parse_timestamp(str(create_time)) if create_time > 0 else current_time

                    # Filter by symbol if specified
                    if symbol and item_symbol != symbol.upper():
                        continue

                    # Only include transactions above threshold
                    if amount_usd < 100000:  # Lower threshold for sample trades
                        continue

                    transactions.append({
                        "symbol": item_symbol,
                        "side": side,
                        "amount_usd": amount_usd,
                        "price": price,
                        "timestamp": timestamp.isoformat(),
                        "transaction_hash": transaction_hash,
                    })

                except Exception as e:
                    logger.warning(f"Error processing whale item: {e}")
                    continue

            # Sort by timestamp (most recent first) and limit
            transactions.sort(key=lambda x: x["timestamp"], reverse=True)
            return transactions[:limit]

        except Exception as e:
            logger.error(f"Error getting fresh whale activity: {e}")
            return []

    async def get_whale_radar_data(self, min_threshold: float = 500000) -> Dict[str, Any]:
        """Get whale radar data with multi-coin analysis"""
        try:
            # Get fresh whale data from API
            whale_data = await self._get_fresh_whale_activity(symbol=None, limit=100)
            
            if not whale_data:
                logger.warning("[WHALE_RADAR] No whale data available")
                return {"symbols_above_threshold": [], "symbols_below_threshold": []}

            # Group by symbol and calculate statistics
            symbol_stats = {}
            total_alerts = len(whale_data)
            
            for tx in whale_data:
                symbol = tx["symbol"]
                if symbol not in symbol_stats:
                    symbol_stats[symbol] = {
                        "buy_count": 0,
                        "sell_count": 0,
                        "buy_usd": 0.0,
                        "sell_usd": 0.0,
                        "total_usd": 0.0,
                        "net_usd": 0.0,
                        "transactions": []
                    }

                # Update statistics
                amount_usd = tx["amount_usd"]
                if tx["side"] == "buy":
                    symbol_stats[symbol]["buy_count"] += 1
                    symbol_stats[symbol]["buy_usd"] += amount_usd
                else:
                    symbol_stats[symbol]["sell_count"] += 1
                    symbol_stats[symbol]["sell_usd"] += amount_usd

                symbol_stats[symbol]["total_usd"] += amount_usd
                symbol_stats[symbol]["net_usd"] = symbol_stats[symbol]["buy_usd"] - symbol_stats[symbol]["sell_usd"]
                symbol_stats[symbol]["transactions"].append(tx)

            # Separate symbols above and below threshold
            symbols_above_threshold = []
            symbols_below_threshold = []

            for symbol, stats in symbol_stats.items():
                total_usd = stats["total_usd"]
                net_usd = stats["net_usd"]
                
                # Determine if significant based on total activity
                is_above_threshold = total_usd >= min_threshold
                
                radar_item = {
                    "symbol": symbol,
                    "buy_count": stats["buy_count"],
                    "sell_count": stats["sell_count"],
                    "buy_usd": stats["buy_usd"],
                    "sell_usd": stats["sell_usd"],
                    "total_usd": total_usd,
                    "net_usd": net_usd,
                    "dominant_side": "BUY" if net_usd > 0 else "SELL",
                }

                if is_above_threshold:
                    symbols_above_threshold.append(radar_item)
                else:
                    symbols_below_threshold.append(radar_item)

            # Sort by total USD (descending)
            symbols_above_threshold.sort(key=lambda x: x["total_usd"], reverse=True)
            symbols_below_threshold.sort(key=lambda x: x["total_usd"], reverse=True)

            logger.info(
                f"[WHALE_RADAR] Processed {total_alerts} alerts, "
                f"{len(symbols_above_threshold)} symbols above threshold, "
                f"{len(symbols_below_threshold)} symbols below threshold"
            )

            return {
                "symbols_above_threshold": symbols_above_threshold,
                "symbols_below_threshold": symbols_below_threshold,
                "total_alerts": total_alerts,
            }

        except Exception as e:
            logger.error(f"Error getting whale radar data: {e}")
            return {"symbols_above_threshold": [], "symbols_below_threshold": []}

    async def get_whale_positions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get current whale positions from Hyperliquid"""
        try:
            # Get whale position data
            position_data = await self.api.get_whale_position_hyperliquid()

            if not position_data.get("success", False):
                logger.warning(f"[WHALE_POSITION] Failed to get position data: {position_data.get('error', 'Unknown error')}")
                return []

            # Handle different response formats
            data = position_data.get("data", [])
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                return []

            positions = []
            for item in data:
                try:
                    if not isinstance(item, dict):
                        continue

                    symbol = str(safe_get(item, "symbol", "")).upper().strip()
                    if not symbol:
                        continue

                    # Extract position data
                    notional_usd = safe_float(safe_get(item, "notional_usd"), 0.0)
                    leverage = safe_float(safe_get(item, "leverage"), 0.0)
                    side = str(safe_get(item, "side", "")).lower()

                    if notional_usd > 0:
                        positions.append({
                            "symbol": symbol,
                            "position_value_usd": notional_usd,
                            "leverage": leverage,
                            "side": side,
                        })

                except Exception as e:
                    logger.warning(f"Error processing position item: {e}")
                    continue

            # Sort by position value (descending) and limit
            positions.sort(key=lambda x: x["position_value_usd"], reverse=True)
            return positions[:limit]

        except Exception as e:
            logger.error(f"Error getting whale positions: {e}")
            return []

    async def get_enhanced_whale_radar_data(self, user_threshold: float = None) -> Dict[str, Any]:
        """Get enhanced whale radar data with dynamic thresholds and active symbols"""
        try:
            # Determine thresholds based on symbol type and user input
            btc_eth_threshold = user_threshold if user_threshold else 500_000
            altcoin_threshold = user_threshold if user_threshold else 100_000
            
            # Get fresh whale data from API with no limit to process ALL transactions
            whale_data = await self._get_fresh_whale_activity(symbol=None, limit=1000)
            
            if not whale_data:
                logger.warning("[ENHANCED_RADAR] No whale data available")
                return {
                    "symbols_above_threshold": [], 
                    "symbols_below_threshold": [],
                    "active_whale_symbols": [],
                    "total_alerts": 0
                }

            # Group by symbol and calculate statistics
            symbol_stats = {}
            total_alerts = len(whale_data)
            
            for tx in whale_data:
                symbol = tx["symbol"]
                if symbol not in symbol_stats:
                    symbol_stats[symbol] = {
                        "buy_count": 0,
                        "sell_count": 0,
                        "buy_usd": 0.0,
                        "sell_usd": 0.0,
                        "total_usd": 0.0,
                        "net_usd": 0.0,
                        "transactions": [],
                        "buy_amounts": [],
                        "sell_amounts": []
                    }

                # Update statistics
                amount_usd = tx["amount_usd"]
                if tx["side"] == "buy":
                    symbol_stats[symbol]["buy_count"] += 1
                    symbol_stats[symbol]["buy_usd"] += amount_usd
                    symbol_stats[symbol]["buy_amounts"].append(amount_usd)
                else:
                    symbol_stats[symbol]["sell_count"] += 1
                    symbol_stats[symbol]["sell_usd"] += amount_usd
                    symbol_stats[symbol]["sell_amounts"].append(amount_usd)

                symbol_stats[symbol]["total_usd"] += amount_usd
                symbol_stats[symbol]["net_usd"] = symbol_stats[symbol]["buy_usd"] - symbol_stats[symbol]["sell_usd"]
                symbol_stats[symbol]["transactions"].append(tx)

            # Separate symbols above and below threshold
            symbols_above_threshold = []
            symbols_below_threshold = []
            active_whale_symbols = []

            for symbol, stats in symbol_stats.items():
                total_usd = stats["total_usd"]
                net_usd = stats["net_usd"]
                buy_count = stats["buy_count"]
                sell_count = stats["sell_count"]
                
                # Determine threshold based on symbol type
                if symbol in ["BTC", "ETH"]:
                    threshold = btc_eth_threshold
                else:
                    threshold = altcoin_threshold
                
                # Determine if significant based on total activity
                is_above_threshold = total_usd >= threshold
                has_activity = buy_count > 0 or sell_count > 0
                
                # Sort buy and sell amounts (descending)
                stats["buy_amounts"].sort(reverse=True)
                stats["sell_amounts"].sort(reverse=True)
                
                # Format amounts for display
                buy_amounts_formatted = [f"${amount:,.0f}" for amount in stats["buy_amounts"][:3]]
                sell_amounts_formatted = [f"${amount:,.0f}" for amount in stats["sell_amounts"][:3]]
                
                radar_item = {
                    "symbol": symbol,
                    "buy_count": buy_count,
                    "sell_count": sell_count,
                    "buy_usd": stats["buy_usd"],
                    "sell_usd": stats["sell_usd"],
                    "total_usd": total_usd,
                    "net_usd": net_usd,
                    "dominant_side": "BUY" if net_usd > 0 else "SELL",
                }
                
                # Active whale symbols data
                active_symbol_data = {
                    "symbol": symbol,
                    "total_trades": buy_count + sell_count,
                    "buy_count": buy_count,
                    "sell_count": sell_count,
                    "buy_amounts": buy_amounts_formatted,
                    "sell_amounts": sell_amounts_formatted,
                }

                if is_above_threshold:
                    symbols_above_threshold.append(radar_item)
                else:
                    symbols_below_threshold.append(radar_item)
                
                # Add to active symbols if there's any activity
                if has_activity:
                    active_whale_symbols.append(active_symbol_data)

            # Sort by total USD (descending)
            symbols_above_threshold.sort(key=lambda x: x["total_usd"], reverse=True)
            symbols_below_threshold.sort(key=lambda x: x["total_usd"], reverse=True)
            active_whale_symbols.sort(key=lambda x: x["total_trades"], reverse=True)

            # Comprehensive logging
            logger.info(
                f"[WHALE] Parsed {total_alerts} alerts, "
                f"{len(symbols_above_threshold)} symbols above threshold, "
                f"{len(symbols_below_threshold)} symbols below threshold, "
                f"{len(active_whale_symbols)} symbols detected with whale activity."
            )

            return {
                "symbols_above_threshold": symbols_above_threshold,
                "symbols_below_threshold": symbols_below_threshold,
                "active_whale_symbols": active_whale_symbols,
                "total_alerts": total_alerts,
            }

        except Exception as e:
            logger.error(f"Error getting enhanced whale radar data: {e}")
            return {
                "symbols_above_threshold": [], 
                "symbols_below_threshold": [],
                "active_whale_symbols": [],
                "total_alerts": 0
            }


async def get_enhanced_whale_radar(user_threshold: float = None):
    """
    Get complete whale radar data including enhanced data, sample trades, and positions
    
    Args:
        user_threshold: Custom threshold for whale detection
        
    Returns:
        Tuple of (enhanced_data, sample_trades, all_positions)
    """
    try:
        watcher = WhaleWatcher()
        
        # Get enhanced whale radar data
        enhanced_data = await watcher.get_enhanced_whale_radar_data(user_threshold)
        
        # Get sample recent whale trades
        sample_trades_result = await watcher.get_recent_whale_activity(limit=20)
        sample_trades = sample_trades_result if isinstance(sample_trades_result, list) else sample_trades_result.get('trades', [])
        
        # Get whale positions
        all_positions = await watcher.get_whale_positions(limit=20)
        
        return enhanced_data, sample_trades, all_positions
        
    except Exception as e:
        logger.error(f"Error getting complete whale radar: {e}")
        return {}, [], []


# Global whale watcher instance
whale_watcher = WhaleWatcher()
