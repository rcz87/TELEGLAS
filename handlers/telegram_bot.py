import asyncio
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from functools import wraps
from loguru import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.helpers import escape_markdown
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from config.settings import settings
from core.database import db_manager, UserSubscription
from services.liquidation_monitor import liquidation_monitor
from services.whale_watcher import whale_watcher
from services.funding_rate_radar import funding_rate_radar
from services.coinglass_api import coinglass_api
from utils.auth import is_user_allowed, log_access_attempt, get_access_status_message
from utils.formatters import build_raw_orderbook_text, format_whale_radar_enhanced, format_whale_radar_message
from handlers.raw_orderbook import raw_orderbook_handler


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Create main menu keyboard with command buttons"""
    keyboard = [
        [KeyboardButton("/raw"), KeyboardButton("/whale")],
        [KeyboardButton("/liq"), KeyboardButton("/sentiment")],
        [KeyboardButton("/status"), KeyboardButton("/alerts")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def require_access(func):
    """
    Decorator to check if user is allowed to access bot.
    Replaces old _is_whitelisted method with centralized auth.
    """
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            user = None
            if update and getattr(update, "message", None):
                user = update.message.from_user
            elif update and getattr(update, "callback_query", None):
                user = update.callback_query.from_user
            
            user_id = user.id if user else None
            username = user.username or user.first_name if user else "Unknown"
            command = update.message.text.split()[0] if update and update.message and update.message.text else "unknown"

            if user_id is None:
                logger.warning("[AUTH] Update without user, denying access")
                if update and hasattr(update, 'effective_message') and update.effective_message:
                    await update.effective_message.reply_text(
                        "🚫 Access Denied\nUnable to identify user.",
                        parse_mode=None,
                    )
                return

            # Check access using centralized auth
            if not is_user_allowed(user_id):
                log_access_attempt(user_id, username, command, allowed=False)
                if update and hasattr(update, 'effective_message') and update.effective_message:
                    await update.effective_message.reply_text(
                        "🚫 *Access Denied*\n"
                        "This is a private bot. You need to be whitelisted to use it.\n"
                        "Please contact the administrator for access.",
                        parse_mode="Markdown",
                    )
                return

            # Log successful access
            log_access_attempt(user_id, username, command, allowed=True)
            return await func(self, update, context, *args, **kwargs)
            
        except Exception as e:
            logger.exception("Error in require_access decorator: %s", e)
            if update and hasattr(update, 'effective_message') and update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ An error occurred while processing your request.",
                    parse_mode=None,
                )
            return
    
    return wrapper


def require_public_access(func):
    """
    Decorator for commands that should be public (like /status or /ping).
    Only denies access if user cannot be identified.
    """
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            user = None
            if update and getattr(update, "message", None):
                user = update.message.from_user
            elif update and getattr(update, "callback_query", None):
                user = update.callback_query.from_user
            
            user_id = user.id if user else None
            username = user.username or user.first_name if user else "Unknown"
            command = update.message.text.split()[0] if update and update.message and update.message.text else "unknown"

            if user_id is None:
                logger.warning("[AUTH] Update without user, denying access")
                if update and hasattr(update, 'effective_message') and update.effective_message:
                    await update.effective_message.reply_text(
                        "🚫 Access Denied\nUnable to identify user.",
                        parse_mode=None,
                    )
                return

            # Always allow access for public commands, just log it
            log_access_attempt(user_id, username, command, allowed=True)
            return await func(self, update, context, *args, **kwargs)
            
        except Exception as e:
            logger.exception("Error in require_public_access decorator: %s", e)
            if update and hasattr(update, 'effective_message') and update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ An error occurred while processing your request.",
                    parse_mode=None,
                )
            return
    
    return wrapper


class TelegramBot:
    """Telegram bot handler for CryptoSat"""

    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.admin_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
        self.alert_channel_id = settings.TELEGRAM_ALERT_CHANNEL_ID
        self.whitelisted_users = settings.WHITELISTED_USERS
        self.application = None

    def sanitize(self, msg: str) -> str:
        """Escape all Telegram Markdown special characters"""
        import re
        return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', msg)

    async def initialize(self):
        """Initialize Telegram bot"""
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")

        # Validate settings
        settings.validate()

        # Initialize database
        await db_manager.initialize()

        # Create application
        self.application = Application.builder().token(self.token).build()

        # Add handlers
        self._add_handlers()

        # Set up bot commands
        await self._setup_bot_commands()

        logger.info("Telegram bot initialized successfully")

    def _add_handlers(self):
        """Add all command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.handle_start))
        self.application.add_handler(CommandHandler("help", self.handle_help))
        self.application.add_handler(CommandHandler("liq", self.handle_liquidation))
        self.application.add_handler(CommandHandler("sentiment", self.handle_sentiment))
        self.application.add_handler(CommandHandler("whale", self.handle_whale))
        self.application.add_handler(CommandHandler("subscribe", self.handle_subscribe))
        self.application.add_handler(
            CommandHandler("unsubscribe", self.handle_unsubscribe)
        )
        self.application.add_handler(CommandHandler("status", self.handle_status))
        self.application.add_handler(CommandHandler("alerts", self.handle_alerts))
        self.application.add_handler(CommandHandler("raw", self.handle_raw_data))
        self.application.add_handler(CommandHandler("alerts_status", self.handle_alerts_status))
        self.application.add_handler(CommandHandler("alerts_on_w", self.handle_alerts_on_whale))
        self.application.add_handler(CommandHandler("alerts_off_w", self.handle_alerts_off_whale))
        # Add raw_orderbook handler from dedicated module
        self.application.add_handler(CommandHandler("raw_orderbook", raw_orderbook_handler))

        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

        # Message handler for non-commands
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

    async def _setup_bot_commands(self):
        """Set up bot commands to appear in Telegram command menu"""
        try:
            from telegram import BotCommand
            
            commands = [
                BotCommand("start", "Start the bot and see main menu"),
                BotCommand("help", "Show help and available commands"),
                BotCommand("raw", "Get comprehensive market data for a symbol"),
                BotCommand("raw_orderbook", "Orderbook depth & imbalance analysis"),
                BotCommand("liq", "Get liquidation data for a symbol"),
                BotCommand("sentiment", "Show market sentiment analysis"),
                BotCommand("whale", "Show recent whale transactions"),
                BotCommand("subscribe", "Subscribe to alerts for a symbol"),
                BotCommand("unsubscribe", "Unsubscribe from alerts"),
                BotCommand("alerts", "View your alert subscriptions"),
                BotCommand("status", "Check bot status and performance"),
                BotCommand("alerts_status", "Show alert system status"),
                BotCommand("alerts_on_w", "Turn ON whale alerts"),
                BotCommand("alerts_off_w", "Turn OFF whale alerts"),
            ]
            
            await self.application.bot.set_my_commands(commands)
            logger.info("Bot commands set up successfully")
            
        except Exception as e:
            logger.error(f"Failed to set up bot commands: {e}")
            # Don't raise exception - bot can still work without commands list

    def _is_whitelisted(self, user_id: int) -> bool:
        """Check if user is whitelisted - admin always has access"""
        # Admin always has access
        if user_id == self.admin_chat_id:
            return True
        
        # If whitelist is empty, deny access (security)
        if not self.whitelisted_users:
            return False
            
        # Check if user is in whitelist
        return user_id in self.whitelisted_users

    @require_access
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = None
        if update.message:
            user = update.message.from_user
        elif update.callback_query:
            user = update.callback_query.from_user
        username = user.username or user.first_name

        keyboard = get_main_menu_keyboard()

        welcome_message = (
            f"🛸 Welcome to CryptoSat Bot, R11C0!\n\n"
            "🎯 High-Frequency Trading Signals & Market Intelligence\n"
            "Powered by real-time data & CoinGlass API v4.\n\n"
            "📊 Main Commands:\n"
            "/liq [SYMBOL]         → Liquidation radar (24H)  \n"
            "/raw [SYMBOL]         → Raw market data multi-timeframe  \n"
            "/raw_orderbook [SYMBOL] → Orderbook depth & imbalance  \n"
            "/whale                → Whale radar (multi-coin Hyperliquid)\n"
            "/sentiment            → Market sentiment (global view)\n\n"
            "/subscribe [SYMBOL]   → Subscribe alerts untuk 1 coin  \n"
            "/unsubscribe [SYMBOL] → Hentikan alert untuk 1 coin  \n"
            "/status               → Cek status sistem & layanan  \n"
            "/alerts               → Lihat daftar alert aktif  \n"
            "/alerts_on_w          → Aktifkan whale alert  \n"
            "/alerts_off_w         → Matikan whale alert  \n\n"
            "💡 Contoh:\n"
            "• /liq BTC  \n"
            "• /raw SOL  \n"
            "• /raw_orderbook BTC  \n"
            "• /subscribe BTC  \n\n"
            "🚨 Real-time Monitoring Aktif:\n"
            "• Massive liquidations (>$1M)  \n"
            "• Whale movements (>$500K)  \n"
            "• Extreme funding rates  \n\n"
            "👇 Gunakan tombol di bawah untuk akses cepat ke:\n"
            "• /liq BTC   • /raw BTC   • /whale   • /status"
        )

        await update.message.reply_text(welcome_message, reply_markup=keyboard)

    @require_access
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""

        help_message = (
            "📖 *CryptoSat Bot Help*\n\n"
            "🎯 *Commands:*\n\n"
            "📊 *Market Data:*\n"
            "/liq `[SYMBOL]` - Get liquidation data for specific coin\n"
            "  Example: /liq BTC\n\n"
            "/raw `[SYMBOL]` - Comprehensive market data analysis\n"
            "  Example: /raw BTC\n"
            "  Includes: Price, OI, Volume, Funding, Liquidations,\n"
            "  L/S Ratios, Taker Flow, RSI, CG Levels\n\n"
            "/sentiment - Show Fear & Greed Index + L/S Ratio\n"
            "/whale - Display 5 latest whale transactions\n\n"
            "🔔 *Alert Management:*\n"
            "/subscribe `[SYMBOL]` - Subscribe to alerts for a coin\n"
            "  Example: /subscribe BTC\n\n"
            "/unsubscribe `[SYMBOL]` - Unsubscribe from alerts\n"
            "  Example: /unsubscribe BTC\n\n"
            "/alerts - View your current subscriptions\n\n"
            "ℹ️ *Other:*\n"
            "/status - Check bot status and API limits\n"
            "/help - Show this help message\n\n"
            "📝 *Note:*\n"
            "• All alerts are filtered by minimum thresholds\n"
            "• Liquidations: $1M+\n"
            f"• Whale transactions: ${settings.WHALE_TRANSACTION_THRESHOLD_USD:,.0f}+\n"
            "• Funding rates: ±1%\n\n"
            "⚡ Data updates every 5-30 seconds"
        )

        await update.message.reply_text(help_message, parse_mode="Markdown")

    @require_access
    async def handle_liquidation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /liq command - using new message builder"""
        from utils.message_builders import build_liq_message

        # Extract symbol from command
        symbol = None
        if context.args:
            symbol = context.args[0].upper()

        if not symbol:
            await update.message.reply_text(
                self.sanitize("❌ *Symbol Required*\n\n"
                "Usage: /liq `[SYMBOL]`\n"
                "Example: /liq BTC"),
                parse_mode="Markdown",
            )
            return

        try:
            # Use new message builder
            message = await build_liq_message(symbol)
            
            # Send the formatted message (plain text to avoid markdown issues)
            await update.message.reply_text(message, parse_mode=None)
            
        except Exception as e:
            logger.error(f"[LIQ] Error building liquidation message for {symbol}: {e}")
            await update.message.reply_text(
                f"⚠️ Terjadi kesalahan saat mengambil data liquidation untuk {symbol}. Coba lagi beberapa saat lagi.",
                parse_mode=None
            )

    @require_access
    async def handle_sentiment(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /sentiment command - Enhanced with fallback mechanism"""

        # Send typing action
        await update.message.chat.send_action(action="typing")

        try:
            # Initialize sentiment data collection
            sentiment_data = {
                "fear_greed": None,
                "funding_sentiment": None,
                "oi_trend": None,
                "market_trend": None,
                "ls_ratio": None
            }

            # Try to get Fear & Greed Index
            try:
                fear_greed = await funding_rate_radar.get_fear_greed_index()
                if fear_greed:
                    sentiment_data["fear_greed"] = fear_greed
                    logger.info("[SENTIMENT] Successfully retrieved Fear & Greed Index")
                else:
                    logger.warning("[SENTIMENT] Fear & Greed Index unavailable")
            except Exception as e:
                logger.warning(f"[SENTIMENT] Fear & Greed Index failed: {e}")

            # Try to get funding sentiment from major symbols
            try:
                funding_sentiment = await self._get_funding_sentiment()
                if funding_sentiment:
                    sentiment_data["funding_sentiment"] = funding_sentiment
                    logger.info("[SENTIMENT] Successfully retrieved funding sentiment")
            except Exception as e:
                logger.warning(f"[SENTIMENT] Funding sentiment failed: {e}")

            # Try to get OI trend
            try:
                oi_trend = await self._get_oi_trend()
                if oi_trend:
                    sentiment_data["oi_trend"] = oi_trend
                    logger.info("[SENTIMENT] Successfully retrieved OI trend")
            except Exception as e:
                logger.warning(f"[SENTIMENT] OI trend failed: {e}")

            # Try to get market trend
            try:
                market_trend = await self._get_market_trend()
                if market_trend:
                    sentiment_data["market_trend"] = market_trend
                    logger.info("[SENTIMENT] Successfully retrieved market trend")
            except Exception as e:
                logger.warning(f"[SENTIMENT] Market trend failed: {e}")

            # Try to get L/S ratio for BTC as market indicator
            try:
                ls_ratio = await self._get_ls_ratio_sentiment()
                if ls_ratio:
                    sentiment_data["ls_ratio"] = ls_ratio
                    logger.info("[SENTIMENT] Successfully retrieved L/S ratio sentiment")
            except Exception as e:
                logger.warning(f"[SENTIMENT] L/S ratio sentiment failed: {e}")

            # Check if we have any data
            has_data = any(sentiment_data.values())
            
            if not has_data:
                await update.message.reply_text(
                    self.sanitize("❌ *Service Unavailable*\n\n"
                    "Could not retrieve market sentiment data.\n"
                    "Please try again in a few moments."),
                    parse_mode="Markdown",
                )
                return

            # Format comprehensive sentiment message
            message = self._format_sentiment_message(sentiment_data)
            
            await update.message.reply_text(message, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"[SENTIMENT] Error in handle_sentiment: {e}")
            await update.message.reply_text(
                self.sanitize("❌ *Error*\n\n"
                "Failed to process sentiment data.\n"
                "Please try again later."),
                parse_mode="Markdown",
            )

    async def _get_funding_sentiment(self) -> Optional[Dict[str, Any]]:
        """Get funding sentiment from major symbols"""
        try:
            # Check funding rates for major symbols
            major_symbols = ["BTC", "ETH"]
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            total_rate = 0.0
            valid_data = 0

            async with coinglass_api:
                for symbol in major_symbols:
                    try:
                        funding_data = await coinglass_api.get_funding_rate_exchange_list(symbol)
                        if funding_data.get("success"):
                            data = funding_data.get("data", [])
                            if isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict):
                                        rate = coinglass_api.safe_float(item.get("fundingRate"), 0.0)
                                        if abs(rate) < 0.1:  # Filter unrealistic rates
                                            total_rate += rate
                                            valid_data += 1
                                            if rate > 0.001:  # > 0.1%
                                                positive_count += 1
                                            elif rate < -0.001:  # < -0.1%
                                                negative_count += 1
                                            else:
                                                neutral_count += 1
                                        break  # Take first valid exchange
                    except Exception as e:
                        logger.debug(f"[SENTIMENT] Failed to get funding for {symbol}: {e}")
                        continue

            if valid_data == 0:
                return None

            avg_rate = total_rate / valid_data if valid_data > 0 else 0.0
            
            # Determine sentiment
            if positive_count > negative_count:
                sentiment = "Bullish"
                emoji = "🟢"
            elif negative_count > positive_count:
                sentiment = "Bearish"
                emoji = "🔴"
            else:
                sentiment = "Neutral"
                emoji = "🟡"

            return {
                "sentiment": sentiment,
                "emoji": emoji,
                "avg_rate": avg_rate * 100,  # Convert to percentage
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count,
                "total_symbols": len(major_symbols)
            }

        except Exception as e:
            logger.error(f"[SENTIMENT] Error getting funding sentiment: {e}")
            return None

    async def _get_oi_trend(self) -> Optional[Dict[str, Any]]:
        """Get Open Interest trend for major symbols"""
        try:
            # Check OI trend for BTC
            async with coinglass_api:
                try:
                    oi_data = await coinglass_api.get_open_interest_exchange_list("BTC")
                    if oi_data.get("success"):
                        data = oi_data.get("data", [])
                        if isinstance(data, list) and len(data) >= 2:
                            # Get recent data points
                            recent_data = data[-2:]  # Last 2 data points
                            if len(recent_data) >= 2:
                                current_oi = coinglass_api.safe_float(recent_data[-1].get("close", 0))
                                previous_oi = coinglass_api.safe_float(recent_data[-2].get("close", 0))
                                
                                if current_oi > 0 and previous_oi > 0:
                                    change_pct = ((current_oi - previous_oi) / previous_oi) * 100
                                    
                                    if change_pct > 2:
                                        trend = "Increasing"
                                        emoji = "📈"
                                    elif change_pct < -2:
                                        trend = "Decreasing"
                                        emoji = "📉"
                                    else:
                                        trend = "Stable"
                                        emoji = "➡️"
                                    
                                    return {
                                        "trend": trend,
                                        "emoji": emoji,
                                        "change_pct": change_pct,
                                        "current_oi": current_oi,
                                        "previous_oi": previous_oi
                                    }
                except Exception as e:
                    logger.debug(f"[SENTIMENT] OI trend analysis failed: {e}")

            return None

        except Exception as e:
            logger.error(f"[SENTIMENT] Error getting OI trend: {e}")
            return None

    async def _get_market_trend(self) -> Optional[Dict[str, Any]]:
        """Get market trend from price changes"""
        try:
            # Get price change data for major symbols
            async with coinglass_api:
                try:
                    price_data = await coinglass_api.get_price_change_list()
                    if price_data.get("success"):
                        data = price_data.get("data", [])
                        if isinstance(data, list):
                            # Find BTC and ETH
                            btc_data = None
                            eth_data = None
                            
                            for item in data:
                                if isinstance(item, dict):
                                    symbol = str(item.get("symbol", "")).upper()
                                    if symbol == "BTC":
                                        btc_data = item
                                    elif symbol == "ETH":
                                        eth_data = item
                            
                            # Analyze trend
                            bullish_count = 0
                            bearish_count = 0
                            total_change = 0.0
                            valid_count = 0
                            
                            for item in [btc_data, eth_data]:
                                if item:
                                    change_24h = coinglass_api.safe_float(item.get("price_change_percent_24h", 0))
                                    if change_24h != 0:
                                        total_change += change_24h
                                        valid_count += 1
                                        if change_24h > 0:
                                            bullish_count += 1
                                        elif change_24h < 0:
                                            bearish_count += 1
                            
                            if valid_count > 0:
                                avg_change = total_change / valid_count
                                
                                if bullish_count > bearish_count and avg_change > 1:
                                    trend = "Bullish"
                                    emoji = "🟢"
                                elif bearish_count > bullish_count and avg_change < -1:
                                    trend = "Bearish"
                                    emoji = "🔴"
                                else:
                                    trend = "Neutral"
                                    emoji = "🟡"
                                
                                return {
                                    "trend": trend,
                                    "emoji": emoji,
                                    "avg_change": avg_change,
                                    "bullish_count": bullish_count,
                                    "bearish_count": bearish_count,
                                    "valid_count": valid_count
                                }
                except Exception as e:
                    logger.debug(f"[SENTIMENT] Market trend analysis failed: {e}")

            return None

        except Exception as e:
            logger.error(f"[SENTIMENT] Error getting market trend: {e}")
            return None

    async def _get_ls_ratio_sentiment(self) -> Optional[Dict[str, Any]]:
        """Get L/S ratio sentiment from BTC"""
        try:
            async with coinglass_api:
                try:
                    ls_data = await coinglass_api.get_global_long_short_ratio("BTC", "Binance", "h1")
                    if ls_data:
                        long_percent = coinglass_api.safe_float(ls_data.get("long_percent", 0))
                        short_percent = coinglass_api.safe_float(ls_data.get("short_percent", 0))
                        
                        if long_percent > 0 and short_percent > 0:
                            if long_percent > 60:
                                sentiment = "Long Dominant"
                                emoji = "🟢"
                            elif short_percent > 60:
                                sentiment = "Short Dominant"
                                emoji = "🔴"
                            else:
                                sentiment = "Balanced"
                                emoji = "🟡"
                            
                            return {
                                "sentiment": sentiment,
                                "emoji": emoji,
                                "long_percent": long_percent,
                                "short_percent": short_percent
                            }
                except Exception as e:
                    logger.debug(f"[SENTIMENT] L/S ratio analysis failed: {e}")

            return None

        except Exception as e:
            logger.error(f"[SENTIMENT] Error getting L/S ratio sentiment: {e}")
            return None

    def _format_sentiment_message(self, sentiment_data: Dict[str, Any]) -> str:
        """Format comprehensive sentiment message"""
        try:
            message_parts = []
            
            # Header
            message_parts.append("📊 *Market Sentiment Analysis*\n")
            
            # Fear & Greed Index
            if sentiment_data.get("fear_greed"):
                fg = sentiment_data["fear_greed"]
                value = fg.get("value", 0)
                classification = fg.get("classification", "Unknown")
                interpretation = fg.get("interpretation", "")
                timestamp = fg.get("timestamp", "")
                
                # Determine emoji based on value
                if value <= 20:
                    emoji = "😱"
                elif value <= 40:
                    emoji = "😰"
                elif value <= 60:
                    emoji = "😐"
                elif value <= 80:
                    emoji = "😏"
                else:
                    emoji = "😈"
                
                message_parts.append(
                    f"{emoji} *Fear & Greed Index: {value}*\n"
                    f"🏷️ Classification: {self.sanitize(classification)}\n"
                    f"📝 {self.sanitize(interpretation)}\n"
                )
            
            # Market Trend
            if sentiment_data.get("market_trend"):
                mt = sentiment_data["market_trend"]
                emoji = mt.get("emoji", "📊")
                trend = mt.get("trend", "Unknown")
                avg_change = mt.get("avg_change", 0)
                
                message_parts.append(
                    f"{emoji} *Market Trend: {trend}*\n"
                    f"📈 Average Change: {avg_change:+.2f}%\n"
                )
            
            # Funding Sentiment
            if sentiment_data.get("funding_sentiment"):
                fs = sentiment_data["funding_sentiment"]
                emoji = fs.get("emoji", "💰")
                sentiment = fs.get("sentiment", "Unknown")
                avg_rate = fs.get("avg_rate", 0)
                
                message_parts.append(
                    f"{emoji} *Funding Sentiment: {sentiment}*\n"
                    f"💸 Average Rate: {avg_rate:+.4f}%\n"
                )
            
            # OI Trend
            if sentiment_data.get("oi_trend"):
                oi = sentiment_data["oi_trend"]
                emoji = oi.get("emoji", "📊")
                trend = oi.get("trend", "Unknown")
                change_pct = oi.get("change_pct", 0)
                
                message_parts.append(
                    f"{emoji} *OI Trend: {trend}*\n"
                    f"📊 Change: {change_pct:+.2f}%\n"
                )
            
            # L/S Ratio
            if sentiment_data.get("ls_ratio"):
                ls = sentiment_data["ls_ratio"]
                emoji = ls.get("emoji", "⚖️")
                sentiment = ls.get("sentiment", "Unknown")
                long_percent = ls.get("long_percent", 0)
                short_percent = ls.get("short_percent", 0)
                
                message_parts.append(
                    f"{emoji} *L/S Ratio: {sentiment}*\n"
                    f"🟢 Long: {long_percent:.1f}% | 🔴 Short: {short_percent:.1f}%\n"
                )
            
            # Footer
            message_parts.append("\n📡 *Data Sources:* CoinGlass API")
            message_parts.append("⚡ *Real-time Market Intelligence*")
            
            return "\n".join(message_parts)
            
        except Exception as e:
            logger.error(f"[SENTIMENT] Error formatting sentiment message: {e}")
            return "❌ Error formatting sentiment data"

    @require_access
    async def handle_whale(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /whale command - using new message builder"""
        from utils.message_builders import build_whale_message

        # Send typing action
        await update.message.chat.send_action(action="typing")
        
        try:
            # Use new message builder
            message = await build_whale_message()
            
            # Send the formatted message (plain text to avoid markdown issues)
            if len(message) > 4000:  # Telegram limit
                # Split into chunks if too long
                chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk, parse_mode=None)
            else:
                await update.message.reply_text(message, parse_mode=None)
            
        except Exception as e:
            logger.error(f"[WHALE] Error building whale message: {e}")
            await update.message.reply_text(
                "⚠️ Terjadi kesalahan saat mengambil data whale. Coba lagi beberapa saat lagi.",
                parse_mode=None
            )

    @require_access
    async def handle_subscribe(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /subscribe command"""

        # Extract symbol from command
        symbol = None
        if context.args:
            symbol = context.args[0].upper()

        if not symbol:
            # Show subscription keyboard
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔥 Liquidations", callback_data=f"sub_liq_{symbol or 'BTC'}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🐋 Whales", callback_data=f"sub_whale_{symbol or 'BTC'}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "💰 Funding Rates",
                        callback_data=f"sub_funding_{symbol or 'BTC'}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📊 All Alerts", callback_data=f"sub_all_{symbol or 'BTC'}"
                    )
                ],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                self.sanitize(f"🔔 *Subscribe to Alerts*\n\n"
                f"Choose alert type for `{symbol or 'BTC'}`:"),
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
            return

        # Get user ID from compatible implementation
        user = None
        if update.message:
            user = update.message.from_user
        elif update.callback_query:
            user = update.callback_query.from_user
        
        # For simplicity, subscribe to all alerts
        subscription = UserSubscription(
            user_id=user.id if user else None,
            symbol=symbol,
            alert_types=["liquidation", "whale", "funding"],
        )

        success = await db_manager.add_user_subscription(subscription)

        if success:
            await update.message.reply_text(
                self.sanitize(f"✅ *Subscription Successful*\n\n"
                f"You're now subscribed to all alerts for `{symbol}`:\n"
                f"• 🚨 Massive Liquidations (>$1M)\n"
                f"• 🐋 Whale Transactions (>${settings.WHALE_TRANSACTION_THRESHOLD_USD:,.0f})\n"
                f"• 💰 Extreme Funding Rates (±1%)\n\n"
                f"Use /alerts to manage your subscriptions."),
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                self.sanitize("❌ *Subscription Failed*\n\n"
                "Could not process your subscription. Please try again."),
                parse_mode="Markdown",
            )

    @require_access
    async def handle_unsubscribe(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /unsubscribe command"""

        # Extract symbol from command
        symbol = None
        if context.args:
            symbol = context.args[0].upper()

        if not symbol:
            await update.message.reply_text(
                self.sanitize("❌ *Symbol Required*\n\n"
                "Usage: /unsubscribe `[SYMBOL]`\n"
                "Example: /unsubscribe BTC"),
                parse_mode="Markdown",
            )
            return

        # Get user ID from compatible implementation
        user = None
        if update.message:
            user = update.message.from_user
        elif update.callback_query:
            user = update.callback_query.from_user
        
        # Remove subscription
        success = await db_manager.remove_user_subscription(
            user.id if user else None, symbol
        )

        if success:
            await update.message.reply_text(
                self.sanitize(f"✅ *Unsubscribed*\n\n"
                f"You've been unsubscribed from all alerts for {symbol}."),
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                self.sanitize("❌ *Unsubscribe Failed*\n\n"
                "You may not have an active subscription for this symbol."),
                parse_mode="Markdown",
            )

    @require_access
    async def handle_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts command - show user's subscriptions"""
        # Get user ID from compatible implementation
        user = None
        if update.message:
            user = update.message.from_user
        elif update.callback_query:
            user = update.callback_query.from_user

        subscriptions = await db_manager.get_user_subscriptions(
            user.id if user else None
        )

        if not subscriptions:
            await update.message.reply_text(
                self.sanitize("📭 *No Active Subscriptions*\n\n"
                "You're not subscribed to any alerts.\n"
                "Use /subscribe `[SYMBOL]` to get started."),
                parse_mode="Markdown",
            )
            return

        message = "🔔 *Your Alert Subscriptions*\n\n"

        for sub in subscriptions:
            alert_types = ", ".join([f"• {t.title()}" for t in sub.alert_types])
            message += (
                f"📊 *{self.sanitize(sub.symbol)}*\n"
                f"{alert_types}\n"
                f"🕐 Subscribed: {sub.created_at[:10]}\n\n"
            )

        await update.message.reply_text(message, parse_mode="Markdown")

    @require_access
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""

        # This would typically include API rate limit info, bot uptime, etc.
        # For now, provide basic status
        message = (
            "🤖 *CryptoSat Bot Status*\n\n"
            "✅ All systems operational\n"
            "📊 Data feeds active\n"
            "🔔 Alert broadcasting enabled\n\n"
            "📈 *Performance Metrics:*\n"
            f"• Liquidation checks: Every {settings.LIQUIDATION_POLL_INTERVAL}s\n"
            f"• Whale monitoring: Every {settings.WHALE_POLL_INTERVAL}s\n"
            f"• Funding rate analysis: Every {settings.FUNDING_RATE_POLL_INTERVAL}s\n\n"
            f"⚡ API Rate Limit: {settings.API_CALLS_PER_MINUTE}/minute\n"
            f"🛡️ Security: Whitelist enabled\n\n"
            f"🕐 Uptime: Bot is running"
        )

        await update.message.reply_text(message, parse_mode="Markdown")

    @require_access
    async def handle_alerts_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts_status command - show which alerts are ON/OFF"""
        # Get user from compatible implementation
        user = None
        if update.message:
            user = update.message.from_user
        elif update.callback_query:
            user = update.callback_query.from_user
        
        user_id = user.id if user else None
        username = user.username or user.first_name if user else "Unknown"
        
        # Log incoming update
        logger.info(f"[TELEGRAM] User {user_id} (@{username}) sent /alerts_status command")

        # Build status message
        whale_status = "🟢 ON" if settings.ENABLE_WHALE_ALERTS else "🔴 OFF"
        broadcast_status = "🟢 ON" if settings.ENABLE_BROADCAST_ALERTS else "🔴 OFF"
        
        message = (
            "🔔 *Alert System Status*\n\n"
            f"🐋 Whale Alerts: {whale_status}\n"
            f"📢 Broadcast Alerts: {broadcast_status}\n\n"
            "📋 *Manual Only Modules:*\n"
            "• Liquidation Monitor (MANUAL ONLY)\n"
            "• Funding Rate Radar (MANUAL ONLY)\n"
            "• Market Sentiment (MANUAL ONLY)\n"
            "• Scan & Scalping (MANUAL ONLY)\n"
            "• Raw Data Analysis (MANUAL ONLY)\n\n"
            "💡 *Control Commands:*\n"
            "/alerts_on_w - Turn ON whale alerts\n"
            "/alerts_off_w - Turn OFF whale alerts\n"
            "/alerts_status - Show this status"
        )

        await update.message.reply_text(message, parse_mode="Markdown")

    @require_access
    async def handle_alerts_on_whale(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts_on_w command - turn ON whale alerts"""
        # Get user from compatible implementation
        user = None
        if update.message:
            user = update.message.from_user
        elif update.callback_query:
            user = update.callback_query.from_user
        
        user_id = user.id if user else None
        username = user.username or user.first_name if user else "Unknown"
        
        # Log incoming update
        logger.info(f"[TELEGRAM] User {user_id} (@{username}) sent /alerts_on_w command")

        # Update settings (this would typically modify environment variables or config)
        # For now, just show confirmation and current status
        if settings.ENABLE_WHALE_ALERTS:
            await update.message.reply_text(
                self.sanitize("🐋 *Whale alerts already enabled*\n\n"
                "Whale monitoring is currently running and will automatically\n"
                f"alert you to significant whale transactions (>${settings.WHALE_TRANSACTION_THRESHOLD_USD:,.0f})."),
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                self.sanitize("⚠️ *Configuration Required*\n\n"
                "To enable whale alerts, please set:\n"
                "`ENABLE_WHALE_ALERTS=true` in your environment\n\n"
                "Then restart the bot for changes to take effect.\n\n"
                "Current status: Whale alerts are DISABLED"),
                parse_mode="Markdown",
            )
            logger.warning(f"[ALERT_CONTROL] User {user_id} tried to enable whale alerts but ENABLE_WHALE_ALERTS=false")

    @require_access
    async def handle_alerts_off_whale(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts_off_w command - turn OFF whale alerts"""
        # Get user from compatible implementation
        user = None
        if update.message:
            user = update.message.from_user
        elif update.callback_query:
            user = update.callback_query.from_user
        
        user_id = user.id if user else None
        username = user.username or user.first_name if user else "Unknown"
        
        # Log incoming update
        logger.info(f"[TELEGRAM] User {user_id} (@{username}) sent /alerts_off_w command")

        if not settings.ENABLE_WHALE_ALERTS:
            await update.message.reply_text(
                self.sanitize("🐋 *Whale alerts already disabled*\n\n"
                "Whale monitoring is currently not running automatically.\n"
                "You can still use /whale command for manual checks."),
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                self.sanitize("⚠️ *Configuration Required*\n\n"
                "To disable whale alerts, please set:\n"
                "`ENABLE_WHALE_ALERTS=false` in your environment\n\n"
                "Then restart the bot for changes to take effect.\n\n"
                "Current status: Whale alerts are ENABLED"),
                parse_mode="Markdown",
            )
            logger.info(f"[ALERT_CONTROL] User {user_id} tried to disable whale alerts but needs config change")

    @require_access
    async def handle_raw_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /raw command - standardized comprehensive market data"""
        # Get user from compatible implementation
        user = None
        if update.message:
            user = update.message.from_user
        elif update.callback_query:
            user = update.callback_query.from_user
        
        user_id = user.id if user else None
        username = user.username or user.first_name if user else "Unknown"
        
        # Check if this is exactly "/raw" or "/raw@botname" with no args
        message_text = update.message.text.strip()
        is_raw_only = message_text in ['/raw', f'/raw@{self.application.bot.username}'] if self.application and self.application.bot else message_text == '/raw'
        
        if is_raw_only:
            await update.message.reply_text(
                "❌ Symbol Required. Usage: /raw [SYMBOL]",
                parse_mode=None,
            )
            return

        # Extract argument after /raw
        try:
            args_raw = update.message.text.split(maxsplit=1)[1].strip()
        except IndexError:
            await update.message.reply_text(
                "❌ Symbol Required. Usage: /raw [SYMBOL]",
                parse_mode=None,
            )
            return

        # Log incoming update
        logger.info(f"[/raw] user_id={user_id} username={username} symbol={args_raw}")

        # Send typing action to show we're working
        await update.message.chat.send_action(action="typing")

        try:
            # Import raw data service for comprehensive data aggregation
            from services.raw_data_service import raw_data_service
            from services.coinglass_api import SymbolNotSupported, RawDataUnavailable
            
            # Get comprehensive market data using existing service
            comprehensive_data = await raw_data_service.get_comprehensive_market_data(args_raw)
            
            # Check if symbol is supported
            if "error" in comprehensive_data and "not supported" in comprehensive_data.get("error", "").lower():
                await update.message.reply_text(
                    "❌ Symbol not supported or data not available from CoinGlass.\n\n"
                    "Please try a major futures symbol like: BTC, ETH, SOL, HYPE, etc.",
                    parse_mode=None,
                )
                logger.info(f"[/raw] Symbol '{args_raw}' not supported by CoinGlass")
                return

            # Use new standardized formatter from RawDataService
            formatted_message = raw_data_service.format_standard_raw_message_for_telegram(comprehensive_data)

            # Send comprehensive data as plain text to avoid Markdown parsing errors
            await update.message.reply_text(
                formatted_message,
                parse_mode=None,  # No Markdown parsing
                disable_web_page_preview=True
            )

            logger.info(f"[/raw] Successfully generated standardized response for {args_raw}")

        except SymbolNotSupported as e:
            logger.info(f"[/raw] Symbol not supported: {e}")
            await update.message.reply_text(
                "❌ Symbol not supported or data not available from CoinGlass.\n\n"
                "Please try a major futures symbol like: BTC, ETH, SOL, HYPE, etc.",
                parse_mode=None,
            )
        except (RawDataUnavailable, Exception) as e:
            logger.error(f"[/raw] Error fetching raw data for {args_raw}: {e}")
            await update.message.reply_text(
                f"❌ Service Error\n\n"
                f"Failed to fetch raw data for {args_raw}. Please try again later.",
                parse_mode=None,
            )


    def _format_raw_orderbook_message(self, data: dict) -> str:
        """Format raw orderbook data according to exact requirements"""
        try:
            # Extract data
            exchange = data.get("exchange", "Binance")
            symbol = data.get("symbol", "UNKNOWN")
            interval_ob = data.get("interval_ob", "1h")
            depth_range = data.get("depth_range", "1%")
            
            snapshot = data.get("snapshot", {})
            binance_depth = data.get("binance_depth", {})
            aggregated_depth = data.get("aggregated_depth", {})
            
            # Build message lines
            lines = []
            
            # Header
            lines.append(f"[RAW ORDERBOOK - {symbol}]")
            lines.append("")
            
            # Info Umum section
            lines.append("Info Umum")
            lines.append(f"Exchange       : {exchange}")
            lines.append(f"Symbol         : {symbol}")
            lines.append(f"Interval OB    : {interval_ob} (snapshot level)")
            lines.append(f"Depth Range    : {depth_range}")
            lines.append("")
            
            # Section 1: Snapshot Orderbook (Level Price - History 1H)
            lines.append("1) Snapshot Orderbook (Level Price - History 1H)")
            lines.append("")
            
            # Extract timestamp from snapshot
            timestamp = snapshot.get("timestamp", "N/A")
            if timestamp and timestamp != "N/A":
                lines.append(f"Timestamp      : {timestamp}")
            else:
                lines.append("Timestamp      : N/A")
            lines.append("")
            
            # Extract top bids and asks
            top_bids = snapshot.get("top_bids", [])
            top_asks = snapshot.get("top_asks", [])
            
            # Display top bids
            lines.append("Top Bids (Pembeli)")
            if top_bids:
                for i, bid in enumerate(top_bids[:5], 1):
                    if isinstance(bid, list) and len(bid) >= 2:
                        price = bid[0]
                        qty = bid[1]
                        lines.append(f"• {price} → {qty} {symbol.replace('USDT', '')}")
                    else:
                        lines.append(f"• Invalid bid data format")
            else:
                lines.append("• No bid data available")
            lines.append("")
            
            # Display top asks
            lines.append("Top Asks (Penjual)")
            if top_asks:
                for i, ask in enumerate(top_asks[:5], 1):
                    if isinstance(ask, list) and len(ask) >= 2:
                        price = ask[0]
                        qty = ask[1]
                        lines.append(f"• {price} → {qty} {symbol.replace('USDT', '')}")
                    else:
                        lines.append(f"• Invalid ask data format")
            else:
                lines.append("• No ask data available")
            lines.append("")
            lines.append("--------------------------------------------------")
            lines.append("")
            
            # Section 2: Binance Orderbook Depth (Bids vs Asks) - 1D
            lines.append("2) Binance Orderbook Depth (Bids vs Asks) - 1D")
            lines.append("")
            
            bids_usd = binance_depth.get("bids_usd")
            asks_usd = binance_depth.get("asks_usd")
            bids_qty = binance_depth.get("bids_qty")
            asks_qty = binance_depth.get("asks_qty")
            bias_label = binance_depth.get("bias_label")
            
            if bids_usd is not None and asks_usd is not None:
                # Format USD values
                def format_usd(value):
                    if value >= 1_000_000:
                        return f"${value/1_000_000:.2f}M"
                    elif value >= 1_000:
                        return f"${value/1_000:.2f}K"
                    else:
                        return f"${value:.2f}"
                
                lines.append(f"Total Bids (USD)  : {format_usd(bids_usd)}")
                lines.append(f"Total Asks (USD)  : {format_usd(asks_usd)}")
                
                # Calculate percentages
                total_usd = bids_usd + asks_usd
                if total_usd > 0:
                    bid_pct = (bids_usd / total_usd) * 100
                    ask_pct = (asks_usd / total_usd) * 100
                    lines.append(f"Bid/Ask Ratio     : {bid_pct:.0f}% vs {ask_pct:.0f}%")
                else:
                    lines.append("Bid/Ask Ratio     : N/A")
                
                # Bias label
                if bias_label:
                    lines.append(f"Bias              : {bias_label}")
                else:
                    lines.append("Bias              : Data tidak tersedia")
            else:
                lines.append("Total Bids (USD)  : $0.00")
                lines.append("Total Asks (USD)  : $0.00")
                lines.append("Bid/Ask Ratio     : N/A")
                lines.append("Bias              : Symbol tidak didukung di endpoint depth ini")
                lines.append("")
                lines.append("💡 Catatan: Symbol seperti BOB biasanya tidak didukung")
                lines.append("   di endpoint depth Binance/Aggregated CoinGlass.")
                lines.append("   Hanya major futures (BTC, ETH, SOL, dll) yang tersedia.")
            lines.append("")
            lines.append("--------------------------------------------------")
            lines.append("")
            
            # Section 3: Aggregated Orderbook Depth (Multi-Exchange) - 1H
            lines.append("3) Aggregated Orderbook Depth (Multi-Exchange) - 1H")
            lines.append("")
            
            agg_bids_usd = aggregated_depth.get("bids_usd")
            agg_asks_usd = aggregated_depth.get("asks_usd")
            agg_bids_qty = aggregated_depth.get("bids_qty")
            agg_asks_qty = aggregated_depth.get("asks_qty")
            agg_bias_label = aggregated_depth.get("bias_label")
            
            if agg_bids_usd is not None and agg_asks_usd is not None:
                lines.append(f"Total Bids (USD)  : {format_usd(agg_bids_usd)}")
                lines.append(f"Total Asks (USD)  : {format_usd(agg_asks_usd)}")
                
                # Calculate percentages
                total_agg_usd = agg_bids_usd + agg_asks_usd
                if total_agg_usd > 0:
                    agg_bid_pct = (agg_bids_usd / total_agg_usd) * 100
                    agg_ask_pct = (agg_asks_usd / total_agg_usd) * 100
                    lines.append(f"Bid/Ask Ratio     : {agg_bid_pct:.0f}% vs {agg_ask_pct:.0f}%")
                else:
                    lines.append("Bid/Ask Ratio     : N/A")
                
                # Bias label
                if agg_bias_label:
                    lines.append(f"Bias              : {agg_bias_label}")
                else:
                    lines.append("Bias              : Data tidak tersedia")
            else:
                lines.append("Total Bids (USD)  : $0.00")
                lines.append("Total Asks (USD)  : $0.00")
                lines.append("Bid/Ask Ratio     : N/A")
                lines.append("Bias              : Symbol tidak didukung di endpoint aggregated ini")
                lines.append("")
                lines.append("💡 Catatan: Symbol seperti BOB biasanya tidak didukung")
                lines.append("   di endpoint aggregated CoinGlass.")
                lines.append("   Hanya major futures (BTC, ETH, SOL, dll) yang tersedia.")
            lines.append("")
            lines.append("--------------------------------------------------")
            lines.append("")
            
            # TL;DR Section
            lines.append("TL;DR Orderbook Bias")
            
            # Analyze snapshot bias
            snapshot_bias_text = "Data tidak tersedia"
            if top_bids and top_asks:
                # Extract numeric values from formatted strings
                bid_levels = []
                ask_levels = []
                
                for bid in top_bids[:3]:  # Top 3 levels
                    if isinstance(bid, list) and len(bid) >= 2:
                        bid_levels.append(float(bid[0]))
                
                for ask in top_asks[:3]:  # Top 3 levels
                    if isinstance(ask, list) and len(ask) >= 2:
                        ask_levels.append(float(ask[0]))
                
                if bid_levels and ask_levels:
                    best_bid = max(bid_levels)
                    best_ask = min(ask_levels)
                    spread_pct = ((best_ask - best_bid) / best_bid) * 100
                    
                    if spread_pct < 0.1:
                        snapshot_bias_text = f"OK, spread ketat & likuid di {best_bid}"
                    elif spread_pct < 0.5:
                        snapshot_bias_text = f"Likuiditas tebal di sekitar {best_bid}"
                    else:
                        snapshot_bias_text = f"Spread lebar, likuiditas tipis di {best_bid}"
            
            # Binance depth bias
            binance_bias_text = "Data tidak tersedia"
            if bids_usd is not None and asks_usd is not None:
                if bids_usd > 0 or asks_usd > 0:
                    binance_bias_text = bias_label if bias_label else "Data terbatas"
                else:
                    binance_bias_text = "Symbol tidak didukung di endpoint ini"
            
            # Aggregated bias
            agg_bias_text = "Data tidak tersedia"
            if agg_bids_usd is not None and agg_asks_usd is not None:
                if agg_bids_usd > 0 or agg_asks_usd > 0:
                    agg_bias_text = agg_bias_label if agg_bias_label else "Data terbatas"
                else:
                    agg_bias_text = "Symbol tidak didukung di endpoint ini"
            
            lines.append(f"• Binance Depth (1D)     : {binance_bias_text}")
            lines.append(f"• Aggregated Depth (1H)  : {agg_bias_text}")
            lines.append(f"• Snapshot Level (1H)    : {snapshot_bias_text}")
            lines.append("")
            lines.append("Note: Data real dari CoinGlass Orderbook (2 endpoint: history + aggregated).")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error formatting raw orderbook message: {e}")
            return f"❌ Error formatting orderbook data: {str(e)}\n\nPlease try again later."

    def _format_standardized_raw_output(self, data: Dict[str, Any]) -> str:
        """Format comprehensive raw data according to the exact standardized layout"""
        try:
            from services.coinglass_api import safe_float, safe_int, safe_get, safe_list_get
            
            # Extract symbol and basic info
            symbol = safe_get(data, 'symbol', 'UNKNOWN').upper()
            timestamp = safe_get(data, 'timestamp', '')
            
            # Improve timestamp formatting - convert ISO to readable format
            if timestamp:
                try:
                    from datetime import datetime
                    # Parse ISO timestamp and format as readable
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_timestamp = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                except:
                    formatted_timestamp = timestamp  # Fallback to original
            else:
                formatted_timestamp = ''
            
            # Get general info
            general = safe_get(data, 'general_info', {})
            price_change = safe_get(data, 'price_change', {})
            
            # Extract basic price data
            last_price = safe_float(safe_get(general, 'last_price'), 0.0)
            mark_price = safe_float(safe_get(general, 'mark_price'), 0.0)
            
            # Price changes
            change_1h = safe_float(safe_get(price_change, '1h'), 0.0)
            change_4h = safe_float(safe_get(price_change, '4h'), 0.0) 
            change_24h = safe_float(safe_get(price_change, '24h'), 0.0)
            high_24h = safe_float(safe_get(price_change, 'high_24h'), 0.0)
            low_24h = safe_float(safe_get(price_change, 'low_24h'), 0.0)
            high_7d = safe_float(safe_get(price_change, 'high_7d'), 0.0)
            low_7d = safe_float(safe_get(price_change, 'low_7d'), 0.0)
            
            # Open Interest data
            oi = safe_get(data, 'open_interest', {})
            total_oi = safe_float(safe_get(oi, 'total_oi'), 0.0)
            oi_change_1h = safe_float(safe_get(oi, 'oi_1h'), 0.0)
            oi_change_24h = safe_float(safe_get(oi, 'oi_24h'), 0.0)
            oi_per_exchange = safe_get(oi, 'per_exchange', {})
            oi_binance = safe_float(safe_get(oi_per_exchange, 'Binance'), 0.0)
            oi_bybit = safe_float(safe_get(oi_per_exchange, 'Bybit'), 0.0)
            oi_okx = safe_float(safe_get(oi_per_exchange, 'OKX'), 0.0)
            oi_others = safe_float(safe_get(oi_per_exchange, 'Others'), 0.0)
            
            # Volume data
            volume = safe_get(data, 'volume', {})
            futures_24h = safe_float(safe_get(volume, 'futures_24h'), 0.0)
            perp_24h = safe_float(safe_get(volume, 'perp_24h'), 0.0)
            spot_24h = safe_float(safe_get(volume, 'spot_24h'))
            
            # Funding data
            funding = safe_get(data, 'funding', {})
            current_funding = safe_float(safe_get(funding, 'current_funding'))
            next_funding = safe_get(funding, 'next_funding', 'N/A')
            funding_history = safe_get(funding, 'funding_history', [])
            
            # Liquidation data
            liquidations = safe_get(data, 'liquidations', {})
            total_liq_24h = safe_float(safe_get(liquidations, 'total_24h'), 0.0)
            long_liq_24h = safe_float(safe_get(liquidations, 'long_liq'), 0.0)
            short_liq_24h = safe_float(safe_get(liquidations, 'short_liq'), 0.0)
            
            # Long/Short ratio data
            ls_ratio = safe_get(data, 'long_short_ratio', {})
            account_ratio_global = safe_get(ls_ratio, 'account_ratio_global')
            position_ratio_global = safe_get(ls_ratio, 'position_ratio_global')
            ls_by_exchange = safe_get(ls_ratio, 'by_exchange', {})
            ls_binance = safe_get(ls_by_exchange, 'Binance')
            ls_bybit = safe_get(ls_by_exchange, 'Bybit')
            ls_okx = safe_get(ls_by_exchange, 'OKX')
            
            # Orderbook data - fetch if not present
            orderbook_data = safe_get(data, 'orderbook')
            if orderbook_data is None:
                # Try to fetch orderbook data on-demand
                try:
                    from services.coinglass_api import coinglass_api
                    base_symbol, futures_pair = coinglass_api.resolve_orderbook_symbols(symbol)
                    # Note: This needs to be called from an async function
                    orderbook_data = None  # Skip async call in sync context
                except:
                    orderbook_data = None
            
            # Extract orderbook information
            orderbook_timestamp = safe_get(orderbook_data, 'snapshot_timestamp') if orderbook_data else None
            top_bids = safe_get(orderbook_data, 'top_bids', []) if orderbook_data else []
            top_asks = safe_get(orderbook_data, 'top_asks', []) if orderbook_data else []
            
            # Taker Flow data
            taker_flow = safe_get(data, 'taker_flow', {})
            tf_5m = safe_get(taker_flow, '5m', {})
            tf_15m = safe_get(taker_flow, '15m', {})
            tf_1h = safe_get(taker_flow, '1h', {})
            tf_4h = safe_get(taker_flow, '4h', {})
            
            # RSI data - Use new 1h/4h/1d format
            rsi_1h_4h_1d = safe_get(data, 'rsi_1h_4h_1d', {})
            rsi_1h_new = safe_get(rsi_1h_4h_1d, '1h')
            rsi_4h_new = safe_get(rsi_1h_4h_1d, '4h')
            rsi_1d_new = safe_get(rsi_1h_4h_1d, '1d')
            
            # CG Levels data
            cg_levels = safe_get(data, 'cg_levels', {})
            support_levels = safe_get(cg_levels, 'support')
            resistance_levels = safe_get(cg_levels, 'resistance')
            
            # Format values with proper units
            total_oi_billion = total_oi / 1e9 if total_oi > 0 else 0.0
            oi_binance_billion = oi_binance / 1e9 if oi_binance > 0 else 0.0
            oi_bybit_billion = oi_bybit / 1e9 if oi_bybit > 0 else 0.0
            oi_okx_billion = oi_okx / 1e9 if oi_okx > 0 else 0.0
            oi_others_billion = oi_others / 1e9 if oi_others > 0 else 0.0
            
            futures_volume_24h_billion = futures_24h / 1e9 if futures_24h > 0 else 0.0
            perp_volume_24h_billion = perp_24h / 1e9 if perp_24h > 0 else 0.0
            spot_volume_24h_billion = spot_24h / 1e9 if spot_24h and spot_24h > 0 else 0.0
            
            total_liq_24h_million = total_liq_24h / 1e6 if total_liq_24h > 0 else 0.0
            long_liq_24h_million = long_liq_24h / 1e6 if long_liq_24h > 0 else 0.0
            short_liq_24h_million = short_liq_24h / 1e6 if short_liq_24h > 0 else 0.0
            
            # Helper function to format RSI values
            def format_rsi(value):
                return f"{value:.2f}" if value is not None else "N/A"
            
            # Helper function to format long/short ratio
            def format_ls_ratio(value):
                return f"{value:.2f}" if value is not None else "N/A"
            
            # Helper function to format funding rate
            def format_funding_rate(value):
                return f"{value:+.4f}%" if value is not None else "N/A"
            
            # Helper function to format taker flow values
            def format_taker_flow(tf_data):
                buy = safe_get(tf_data, 'buy')
                sell = safe_get(tf_data, 'sell')
                net = safe_get(tf_data, 'net')
                
                if buy is None or sell is None or net is None:
                    return "N/A"
                return f"Buy ${buy:.0f}M | Sell ${sell:.0f}M | Net ${net:+.0f}M"
            
            # Format support/resistance levels
            if support_levels is None or resistance_levels is None:
                levels_text = "Support/Resistance: N/A (not available for current plan)"
            else:
                support_str = ', '.join([f'${x:.2f}' for x in (support_levels[:3] if isinstance(support_levels, list) else [support_levels])])
                resistance_str = ', '.join([f'${x:.2f}' for x in (resistance_levels[:3] if isinstance(resistance_levels, list) else [resistance_levels])])
                levels_text = f"Support : {support_str}\nResistance: {resistance_str}"
            
            # Format spot volume
            spot_volume_text = f"{spot_volume_24h_billion:.2f}B" if spot_24h is not None else "N/A"

            # Format funding history with details
            def format_funding_history_details(history_data):
                """Format funding history with rate and timestamp details"""
                if not history_data or not isinstance(history_data, list):
                    return "No history available"

                history_lines = []
                for i, entry in enumerate(history_data[:5], 1):  # Show last 5 entries
                    if isinstance(entry, dict):
                        # Extract funding rate - try multiple field names
                        rate = (safe_float(safe_get(entry, "fundingRate")) or
                               safe_float(safe_get(entry, "rate")) or
                               safe_float(safe_get(entry, "avgFundingRate")) or
                               safe_float(safe_get(entry, "funding_rate")) or 0.0)

                        # Extract timestamp - try multiple field names
                        timestamp = (safe_get(entry, "createTime") or
                                   safe_get(entry, "timestamp") or
                                   safe_get(entry, "time") or
                                   safe_get(entry, "createTimeUtc") or "Unknown")

                        # Format timestamp to be more readable if it's a number
                        if timestamp and timestamp != "Unknown":
                            try:
                                if isinstance(timestamp, (int, float)):
                                    from datetime import datetime
                                    dt = datetime.fromtimestamp(timestamp / 1000)  # Convert ms to seconds
                                    timestamp = dt.strftime("%m-%d %H:%M")  # Short format: MM-DD HH:MM
                            except:
                                pass  # Keep original if conversion fails

                        # Format rate as percentage
                        rate_pct = rate * 100.0 if rate < 1 else rate  # Convert decimal to percentage if needed
                        history_lines.append(f"  {timestamp}: {rate_pct:+.4f}%")
                    else:
                        history_lines.append(f"  Entry {i}: Invalid format")

                return "\n".join(history_lines) if history_lines else "No valid history data"

            funding_history_text = format_funding_history_details(funding_history)

            # Build exact standardized message
            message = f"""[RAW DATA - {symbol} - REAL PRICE MULTI-TF]

Info Umum
Symbol : {symbol}
Timeframe : 1H
Timestamp (UTC): {formatted_timestamp}
Last Price: {last_price:.4f}
Mark Price: {mark_price:.4f}
Price Source: coinglass_futures

Price Change
1H : {change_1h:+.2f}%
4H : {change_4h:+.2f}%
24H : {change_24h:+.2f}%
High/Low 24H: {low_24h:.4f}/{high_24h:.4f}
High/Low 7D : {low_7d:.4f}/{high_7d:.4f}

Open Interest
Total OI : {total_oi_billion:.2f}B
OI 1H : {oi_change_1h:+.1f}%
OI 24H : {oi_change_24h:+.1f}%

OI per Exchange
Binance : {oi_binance_billion:.2f}B
Bybit : {oi_bybit_billion:.2f}B
OKX : {oi_okx_billion:.2f}B
Others : {oi_others_billion:.2f}B

Volume
Futures 24H: {futures_volume_24h_billion:.2f}B
Perp 24H : {perp_volume_24h_billion:.2f}B
Spot 24H : {spot_volume_text}

Funding
Current Funding: {format_funding_rate(current_funding)}
Next Funding : {next_funding}
Funding History:
{funding_history_text}

Liquidations
Total 24H : {total_liq_24h_million:.2f}M
Long Liq : {long_liq_24h_million:.2f}M
Short Liq : {short_liq_24h_million:.2f}M

Long/Short Ratio
Account Ratio (Global) : {format_ls_ratio(account_ratio_global)}
Position Ratio (Global): {format_ls_ratio(position_ratio_global)}
By Exchange:
Binance: {format_ls_ratio(ls_binance)}
Bybit : {format_ls_ratio(ls_bybit)}
OKX : {format_ls_ratio(ls_okx)}

Taker Flow Multi-Timeframe (CVD Proxy)
5M: {format_taker_flow(tf_5m)}
15M: {format_taker_flow(tf_15m)}
1H: {format_taker_flow(tf_1h)}
4H: {format_taker_flow(tf_4h)}

RSI (1h/4h/1d)
1H : {format_rsi(rsi_1h_new)}
4H : {format_rsi(rsi_4h_new)}
1D : {format_rsi(rsi_1d_new)}

CG Levels
{levels_text}

Orderbook Snapshot
Timestamp: {orderbook_timestamp if orderbook_timestamp else 'N/A'}
Top 5 Bids: {', '.join([f'${bid:.2f}' if isinstance(bid, (int, float)) else str(bid) for bid in top_bids[:5]]) if top_bids else 'N/A'}
Top 5 Asks: {', '.join([f'${ask:.2f}' if isinstance(ask, (int, float)) else str(ask) for ask in top_asks[:5]]) if top_asks else 'N/A'}"""
            
            return message
            
        except Exception as e:
            logger.error(f"[RAW_DATA] Error formatting standardized data: {e}")
            return f"❌ Error formatting standardized market data for {safe_get(data, 'symbol', 'UNKNOWN')}"

    @require_access
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()  # Acknowledge callback

        # Parse callback data
        data = query.data
        if data.startswith("sub_"):
            parts = data.split("_")
            alert_type = parts[1]
            symbol = parts[2] if len(parts) > 2 else "BTC"

            # Create subscription
            subscription = UserSubscription(
                user_id=query.from_user.id,
                symbol=symbol,
                alert_types=(
                    [alert_type]
                    if alert_type != "all"
                    else ["liquidation", "whale", "funding"]
                ),
            )

            success = await db_manager.add_user_subscription(subscription)

            if success:
                alert_text = "All alerts" if alert_type == "all" else alert_type.title()
                await query.edit_message_text(
                    self.sanitize(f"✅ *Subscribed to {alert_text} for {symbol}*\n\n"
                    "You'll receive notifications when significant events occur."),
                    parse_mode="Markdown",
                )
            else:
                await query.edit_message_text(
                    self.sanitize("❌ *Subscription Failed*\n\n" "Please try again later."),
                    parse_mode="Markdown",
                )

    @require_access
    async def handle_text_buttons(self, update: Update, context):
        """Handle button clicks from main menu keyboard"""
        txt = update.message.text

        if txt == "/raw":
            await update.message.reply_text("Masukkan symbol, contoh: /raw SOL")
            return

        if txt == "/liq":
            await update.message.reply_text("Masukkan symbol, contoh: /liq BTC")
            return

        if txt == "/whale":
            return await self.handle_whale(update, context)

        if txt == "/sentiment":
            return await self.handle_sentiment(update, context)

        if txt == "/status":
            return await self.handle_status(update, context)

        if txt == "/alerts":
            return await self.handle_alerts(update, context)

        # Fallback for other text messages
        await update.message.reply_text(
            self.sanitize("👋 *Hello!*\n\n"
            "Gunakan tombol menu di bawah atau ketik /help untuk melihat semua perintah.\n"
            "Saya di sini untuk memberikan sinyal trading real-time!"),
            parse_mode="Markdown",
        )

    @require_access
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle non-command messages"""
        # Handle button clicks from main menu
        return await self.handle_text_buttons(update, context)

    async def broadcast_alert(self, message: str):
        """Broadcast alert to alert channel"""
        if not self.alert_channel_id or not settings.ENABLE_BROADCAST_ALERTS:
            return

        try:
            await self.application.bot.send_message(
                chat_id=self.alert_channel_id, text=self.sanitize(message), parse_mode="Markdown"
            )
            logger.info(f"Alert broadcasted to channel {self.alert_channel_id}")
        except Exception as e:
            logger.error(f"Failed to broadcast alert: {e}")

    async def start(self):
        """Start bot with polling - pure async without manual event loop"""
        if not self.application:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        logger.info("Starting CryptoSat Telegram bot...")
        
        # Initialize application first (outside retry loop)
        try:
            await self.application.initialize()
            await self.application.start()
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            raise
        
        # Add retry mechanism for start_polling
        from telegram.error import NetworkError, TimedOut, RetryAfter
        max_retries = 5
        
        for i in range(max_retries):
            try:
                logger.info(f"[TELEGRAM] Starting polling attempt {i+1}/{max_retries}")
                await self.application.updater.start_polling(
                    drop_pending_updates=True
                )
                logger.info("CryptoSat bot started successfully with polling enabled")
                return
                
            except (NetworkError, TimedOut, RetryAfter) as e:
                logger.warning(f"[TELEGRAM] Polling failed: {e}, retrying {i+1}/{max_retries}")
                if i < max_retries - 1:  # Don't sleep on last attempt
                    await asyncio.sleep(5)  # Delay 5 seconds between retries
            except Exception as e:
                logger.error(f"[TELEGRAM] Unexpected polling error: {e}")
                raise
        
        logger.error("[TELEGRAM] Polling failed after max retry attempts")
        raise Exception("Polling failed after retry")

    async def stop(self):
        """Stop bot"""
        if self.application:
            # Stop polling first
            if hasattr(self.application, 'updater') and self.application.updater:
                await self.application.updater.stop()
            
            # Stop application
            await self.application.stop()
            logger.info("CryptoSat bot stopped")


# Global bot instance
telegram_bot = TelegramBot()
