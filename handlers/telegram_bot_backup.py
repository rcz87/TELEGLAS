import asyncio
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from functools import wraps
from loguru import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
  +++++++ REPLACE
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

        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

        # Message handler for non-commands
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

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

        welcome_message = (
            f"🛸 *Welcome to CryptoSat Bot, {self.sanitize(username)}!*\n\n"
            "🎯 *High-Frequency Trading Signals & Market Intelligence*\n\n"
            "📊 *Available Commands:*\n"
            "/liq `[SYMBOL]` - Get liquidation data\n"
            "/raw `[SYMBOL]` - Comprehensive market data\n"
            "/sentiment - Market sentiment analysis\n"
            "/whale - Recent whale transactions\n"
            "/subscribe `[SYMBOL]` - Subscribe to alerts\n"
            "/unsubscribe `[SYMBOL]` - Unsubscribe from alerts\n"
            "/status - Bot status and performance\n"
            "/alerts - View your alert subscriptions\n\n"
            "🚨 *Real-time Monitoring Active:*\n"
            "• Massive Liquidations (>$1M)\n"
            "• Whale Movements (>$500K)\n"
            "• Extreme Funding Rates\n\n"
            "⚡ Powered by CoinGlass API v4"
        )

        await update.message.reply_text(welcome_message, parse_mode="Markdown")

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
            "• Whale transactions: $500K+\n"
            "• Funding rates: ±1%\n\n"
            "⚡ Data updates every 5-30 seconds"
        )

        await update.message.reply_text(help_message, parse_mode="Markdown")
  +++++++ REPLACE

    @require_access
    async def handle_liquidation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /liq command"""

        # Extract symbol from command
        symbol = None
        if context.args:
            symbol = context.args[0].upper()

        if not symbol:
            await update.message.reply_text(
                self.sanitize("❌ *Symbol Required*\n\n"
                "Usage: /liq `[SYMBOL]`\n"
                "Example: /liq BTC"),
                parse_mode="MarkdownV2",
            )
            return

        # Get liquidation data
        liquidation_data = await liquidation_monitor.get_symbol_liquidation_summary(
            symbol
        )

        if not liquidation_data:
            await update.message.reply_text(
                self.sanitize(f"❌ *No Data Found*\n\n"
                f"Could not retrieve liquidation data for {symbol}\n"
                "Please check the symbol and try again."),
                parse_mode="MarkdownV2",
            )
            return

        # Format response
        liq_emoji = "📉" if liquidation_data["liquidation_usd"] > 1000000 else "📊"
        price_emoji = "🔴" if liquidation_data["price_change"] < 0 else "🟢"

        message = (
            f"{liq_emoji} *{self.sanitize(symbol)} Liquidation Data*\n\n"
            f"💰 Total Liquidations: ${liquidation_data['liquidation_usd']:,.0f}\n"
            f"{price_emoji} Price Change: {liquidation_data['price_change']:+.2f}%\n"
            f"📊 24h Volume: ${liquidation_data['volume_24h']:,.0f}\n"
            f"🕐 Last Update: {liquidation_data['last_update']}\n\n"
        )

        await update.message.reply_text(message, parse_mode="MarkdownV2")

    @require_access
    async def handle_sentiment(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /sentiment command"""

        # Get Fear & Greed Index
        fear_greed = await funding_rate_radar.get_fear_greed_index()

        if not fear_greed:
            await update.message.reply_text(
                self.sanitize("❌ *Service Unavailable*\n\n"
                "Could not retrieve market sentiment data.\n"
                "Please try again in a few moments."),
                parse_mode="MarkdownV2",
            )
            return

        # Determine emoji based on value
        value = fear_greed["value"]
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

        message = (
            f"{emoji} *Market Sentiment Analysis*\n\n"
            f"📊 Fear & Greed Index: {value}\n"
            f"🏷️ Classification: {self.sanitize(fear_greed['classification'])}\n"
            f"📝 Interpretation: {self.sanitize(fear_greed['interpretation'])}\n"
            f"🕐 Updated: {self.sanitize(fear_greed['timestamp'])}\n\n"
            f"📈 *Market Overview:*\n"
            f"• Extreme Fear (0-20): Good buying opportunity\n"
            f"• Fear (20-40): Accumulate gradually\n"
            f"• Neutral (40-60): Hold positions\n"
            f"• Greed (60-80): Consider taking profits\n"
            f"• Extreme Greed (80-100): High risk zone"
        )

        await update.message.reply_text(message, parse_mode="MarkdownV2")

    @require_access
    async def handle_whale(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /whale command"""

        # Get recent whale activity
        whale_activity = await whale_watcher.get_recent_whale_activity(limit=5)

        if not whale_activity:
            await update.message.reply_text(
                self.sanitize("🐋 *Recent Whale Activity*\n\n"
                "No significant whale transactions detected in the last 24 hours.\n"
                "Whale threshold: $500,000+"),
                parse_mode="MarkdownV2",
            )
            return

        # Format response
        message = "🐋 *Recent Whale Transactions*\n\n"

        for i, tx in enumerate(whale_activity, 1):
            side_emoji = "🟢" if tx["side"] == "buy" else "🔴"
            side_text = "BUY" if tx["side"] == "buy" else "SELL"

            timestamp = datetime.fromisoformat(tx["timestamp"]).strftime("%H:%M:%S")

            message += (
                f"{i}. {side_emoji} *{self.sanitize(tx['symbol'])}* - {side_text}\n"
                f"   💰 ${tx['amount_usd']:,.0f} @ ${tx['price']:,.4f}\n"
                f"   🕐 {timestamp} UTC\n\n"
            )

        message += f"📋 Showing latest {len(whale_activity)} transactions\n"
        message += "💸 Minimum: $500,000\n"
        message += "🏦 Source: Hyperliquid"

        await update.message.reply_text(message, parse_mode="MarkdownV2")

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
                parse_mode="MarkdownV2",
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
                f"• 🐋 Whale Transactions (>$500K)\n"
                f"• 💰 Extreme Funding Rates (±1%)\n\n"
                f"Use /alerts to manage your subscriptions."),
                parse_mode="MarkdownV2",
            )
        else:
            await update.message.reply_text(
                self.sanitize("❌ *Subscription Failed*\n\n"
                "Could not process your subscription. Please try again."),
                parse_mode="MarkdownV2",
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
                parse_mode="MarkdownV2",
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
                parse_mode="MarkdownV2",
            )
        else:
            await update.message.reply_text(
                self.sanitize("❌ *Unsubscribe Failed*\n\n"
                "You may not have an active subscription for this symbol."),
                parse_mode="MarkdownV2",
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
                parse_mode="MarkdownV2",
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

        await update.message.reply_text(message, parse_mode="MarkdownV2")

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

        await update.message.reply_text(message, parse_mode="MarkdownV2")

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

        await update.message.reply_text(message, parse_mode="MarkdownV2")

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
                "alert you to significant whale transactions (>$500K)."),
                parse_mode="MarkdownV2",
            )
        else:
            await update.message.reply_text(
                self.sanitize("⚠️ *Configuration Required*\n\n"
                "To enable whale alerts, please set:\n"
                "`ENABLE_WHALE_ALERTS=true` in your environment\n\n"
                "Then restart the bot for changes to take effect.\n\n"
                "Current status: Whale alerts are DISABLED"),
                parse_mode="MarkdownV2",
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
                parse_mode="MarkdownV2",
            )
        else:
            await update.message.reply_text(
                self.sanitize("⚠️ *Configuration Required*\n\n"
                "To disable whale alerts, please set:\n"
                "`ENABLE_WHALE_ALERTS=false` in your environment\n\n"
                "Then restart the bot for changes to take effect.\n\n"
                "Current status: Whale alerts are ENABLED"),
                parse_mode="MarkdownV2",
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

            # Format to standardized layout
            formatted_message = self._format_standardized_raw_output(comprehensive_data)

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
            spot_24h = safe_get(volume, 'spot_24h')
            
            # Funding data
            funding = safe_get(data, 'funding', {})
            current_funding = safe_float(safe_get(funding, 'current_funding'), 0.0)
            next_funding = safe_get(funding, 'next_funding', 'N/A')
            funding_history = safe_get(funding, 'funding_history', [])
            
            # Liquidation data
            liquidations = safe_get(data, 'liquidations', {})
            total_liq_24h = safe_float(safe_get(liquidations, 'total_24h'), 0.0)
            long_liq_24h = safe_float(safe_get(liquidations, 'long_liq'), 0.0)
            short_liq_24h = safe_float(safe_get(liquidations, 'short_liq'), 0.0)
            
            # Long/Short ratio data
            ls_ratio = safe_get(data, 'long_short_ratio', {})
            account_ratio_global = safe_float(safe_get(ls_ratio, 'account_ratio_global'), 1.0)
            position_ratio_global = safe_float(safe_get(ls_ratio, 'position_ratio_global'), 1.0)
            ls_by_exchange = safe_get(ls_ratio, 'by_exchange', {})
            ls_binance = safe_float(safe_get(ls_by_exchange, 'Binance'), 1.0)
            ls_bybit = safe_float(safe_get(ls_by_exchange, 'Bybit'), 1.0)
            ls_okx = safe_float(safe_get(ls_by_exchange, 'OKX'), 1.0)
            
            # Taker Flow data
            taker_flow = safe_get(data, 'taker_flow', {})
            tf_5m = safe_get(taker_flow, '5m', {})
            tf_15m = safe_get(taker_flow, '15m', {})
            tf_1h = safe_get(taker_flow, '1h', {})
            tf_4h = safe_get(taker_flow, '4h', {})
            
            # RSI data
            rsi = safe_get(data, 'rsi', {})
            rsi_5m = safe_get(rsi, '5m')
            rsi_15m = safe_get(rsi, '15m')
            rsi_1h = safe_get(rsi, '1h')
            rsi_4h = safe_get(rsi, '4h')
            
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
            
            # Format funding history
            funding_history_text = 'No history available' if not funding_history else f'{len(funding_history)} entries'
            
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
Current Funding: {current_funding:+.4f}%
Next Funding : {next_funding}
Funding History:
{funding_history_text}

Liquidations
Total 24H : {total_liq_24h_million:.2f}M
Long Liq : {long_liq_24h_million:.2f}M
Short Liq : {short_liq_24h_million:.2f}M

Long/Short Ratio
Account Ratio (Global) : {account_ratio_global:.2f}
Position Ratio (Global): {position_ratio_global:.2f}
By Exchange:
Binance: {ls_binance:.2f}
Bybit : {ls_bybit:.2f}
OKX : {ls_okx:.2f}

Taker Flow Multi-Timeframe (CVD Proxy)
5M: {format_taker_flow(tf_5m)}
15M: {format_taker_flow(tf_15m)}
1H: {format_taker_flow(tf_1h)}
4H: {format_taker_flow(tf_4h)}

RSI Multi-Timeframe (14)
5M : {format_rsi(rsi_5m)}
15M: {format_rsi(rsi_15m)}
1H : {format_rsi(rsi_1h)}
4H : {format_rsi(rsi_4h)}

CG Levels
{levels_text}"""
            
            return message
            
        except Exception as e:
            logger.error(f"[RAW_DATA] Error formatting standardized data: {e}")
            return f"❌ Error formatting standardized market data for {safe_get(data, 'symbol', 'UNKNOWN')}"

    @require_access
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()  # Acknowledge the callback

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
                    parse_mode="MarkdownV2",
                )
            else:
                await query.edit_message_text(
                    self.sanitize("❌ *Subscription Failed*\n\n" "Please try again later."),
                    parse_mode="MarkdownV2",
                )

    @require_access
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle non-command messages"""
        # Simple message handling - provide help
        await update.message.reply_text(
            self.sanitize("👋 *Hello!*\n\n"
            "Use /help to see available commands.\n"
            "I'm here to provide real-time crypto trading signals!"),
            parse_mode="MarkdownV2",
        )

    async def broadcast_alert(self, message: str):
        """Broadcast alert to alert channel"""
        if not self.alert_channel_id or not settings.ENABLE_BROADCAST_ALERTS:
            return

        try:
            await self.application.bot.send_message(
                chat_id=self.alert_channel_id, text=self.sanitize(message), parse_mode="MarkdownV2"
            )
            logger.info(f"Alert broadcasted to channel {self.alert_channel_id}")
        except Exception as e:
            logger.error(f"Failed to broadcast alert: {e}")

    async def start(self):
        """Start bot with polling - pure async without manual event loop"""
        if not self.application:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        logger.info("Starting CryptoSat Telegram bot...")
        
        # Start polling with proper error handling - NO manual event loop
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(
                drop_pending_updates=True
            )
            logger.info("CryptoSat bot started successfully with polling enabled")
            
        except Exception as e:
            logger.error(f"Failed to start polling: {e}")
            raise

    async def stop(self):
        """Stop the bot"""
        if self.application:
            # Stop polling first
            if hasattr(self.application, 'updater') and self.application.updater:
                await self.application.updater.stop()
            
            # Stop application
            await self.application.stop()
            logger.info("CryptoSat bot stopped")


# Global bot instance
telegram_bot = TelegramBot()
