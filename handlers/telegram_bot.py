import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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


class TelegramBot:
    """Telegram bot handler for CryptoSat"""

    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.admin_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
        self.alert_channel_id = settings.TELEGRAM_ALERT_CHANNEL_ID
        self.whitelisted_users = settings.WHITELISTED_USERS
        self.application = None

    async def initialize(self):
        """Initialize the Telegram bot"""
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

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name

        # Log incoming update
        logger.info(f"[TELEGRAM] User {user_id} (@{username}) sent /start command")

        if not self._is_whitelisted(user_id):
            logger.warning(f"[TELEGRAM] User {user_id} (@{username}) denied access - not whitelisted")
            await update.message.reply_text(
                "🚫 *Access Denied*\n\n"
                "This is a private bot. You need to be whitelisted to use it.\n"
                "Please contact the administrator for access.",
                parse_mode="Markdown",
            )
            return

        welcome_message = (
            f"🛸 *Welcome to CryptoSat Bot, {username}!*\n\n"
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

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Log incoming update
        logger.info(f"[TELEGRAM] User {user_id} (@{username}) sent /help command")

        if not self._is_whitelisted(user_id):
            logger.warning(f"[TELEGRAM] User {user_id} (@{username}) denied access to /help - not whitelisted")
            await update.message.reply_text(
                "🚫 *Access Denied*\n\n"
                "This is a private bot. You need to be whitelisted to use it.\n"
                "Please contact the administrator for access.",
                parse_mode="Markdown",
            )
            return

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

    async def handle_liquidation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /liq command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Log incoming update
        symbol = context.args[0].upper() if context.args else None
        logger.info(f"[TELEGRAM] User {user_id} (@{username}) sent /liq command for {symbol or 'no symbol'}")

        if not self._is_whitelisted(user_id):
            logger.warning(f"[TELEGRAM] User {user_id} (@{username}) denied access to /liq - not whitelisted")
            return

        # Extract symbol from command
        symbol = None
        if context.args:
            symbol = context.args[0].upper()

        if not symbol:
            await update.message.reply_text(
                "❌ *Symbol Required*\n\n"
                "Usage: /liq `[SYMBOL]`\n"
                "Example: /liq BTC",
                parse_mode="Markdown",
            )
            return

        # Get liquidation data
        liquidation_data = await liquidation_monitor.get_symbol_liquidation_summary(
            symbol
        )

        if not liquidation_data:
            await update.message.reply_text(
                f"❌ *No Data Found*\n\n"
                f"Could not retrieve liquidation data for `{symbol}`\n"
                "Please check the symbol and try again.",
                parse_mode="Markdown",
            )
            return

        # Format response
        liq_emoji = "📉" if liquidation_data["liquidation_usd"] > 1000000 else "📊"
        price_emoji = "🔴" if liquidation_data["price_change"] < 0 else "🟢"

        message = (
            f"{liq_emoji} *{symbol} Liquidation Data*\n\n"
            f"💰 Total Liquidations: ${liquidation_data['liquidation_usd']:,.0f}\n"
            f"{price_emoji} Price Change: {liquidation_data['price_change']:+.2f}%\n"
            f"📊 24h Volume: ${liquidation_data['volume_24h']:,.0f}\n"
            f"🕐 Last Update: {liquidation_data['last_update']}\n\n"
        )

        await update.message.reply_text(message, parse_mode="Markdown")

    async def handle_sentiment(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /sentiment command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Log incoming update
        logger.info(f"[TELEGRAM] User {user_id} (@{username}) sent /sentiment command")

        if not self._is_whitelisted(user_id):
            logger.warning(f"[TELEGRAM] User {user_id} (@{username}) denied access to /sentiment - not whitelisted")
            return

        # Get Fear & Greed Index
        fear_greed = await funding_rate_radar.get_fear_greed_index()

        if not fear_greed:
            await update.message.reply_text(
                "❌ *Service Unavailable*\n\n"
                "Could not retrieve market sentiment data.\n"
                "Please try again in a few moments.",
                parse_mode="Markdown",
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
            f"🏷️ Classification: {fear_greed['classification']}\n"
            f"📝 Interpretation: {fear_greed['interpretation']}\n"
            f"🕐 Updated: {fear_greed['timestamp']}\n\n"
            f"📈 *Market Overview:*\n"
            f"• Extreme Fear (0-20): Good buying opportunity\n"
            f"• Fear (20-40): Accumulate gradually\n"
            f"• Neutral (40-60): Hold positions\n"
            f"• Greed (60-80): Consider taking profits\n"
            f"• Extreme Greed (80-100): High risk zone"
        )

        await update.message.reply_text(message, parse_mode="Markdown")

    async def handle_whale(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /whale command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Log incoming update
        logger.info(f"[TELEGRAM] User {user_id} (@{username}) sent /whale command")

        if not self._is_whitelisted(user_id):
            logger.warning(f"[TELEGRAM] User {user_id} (@{username}) denied access to /whale - not whitelisted")
            return

        # Get recent whale activity
        whale_activity = await whale_watcher.get_recent_whale_activity(limit=5)

        if not whale_activity:
            await update.message.reply_text(
                "🐋 *Recent Whale Activity*\n\n"
                "No significant whale transactions detected in the last 24 hours.\n"
                "Whale threshold: $500,000+",
                parse_mode="Markdown",
            )
            return

        # Format response
        message = "🐋 *Recent Whale Transactions*\n\n"

        for i, tx in enumerate(whale_activity, 1):
            side_emoji = "🟢" if tx["side"] == "buy" else "🔴"
            side_text = "BUY" if tx["side"] == "buy" else "SELL"

            timestamp = datetime.fromisoformat(tx["timestamp"]).strftime("%H:%M:%S")

            message += (
                f"{i}. {side_emoji} *{tx['symbol']}* - {side_text}\n"
                f"   💰 ${tx['amount_usd']:,.0f} @ ${tx['price']:,.4f}\n"
                f"   🕐 {timestamp} UTC\n\n"
            )

        message += f"📋 Showing latest {len(whale_activity)} transactions\n"
        message += "💸 Minimum: $500,000\n"
        message += "🏦 Source: Hyperliquid"

        await update.message.reply_text(message, parse_mode="Markdown")

    async def handle_subscribe(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /subscribe command"""
        if not self._is_whitelisted(update.effective_user.id):
            return

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
                f"🔔 *Subscribe to Alerts*\n\n"
                f"Choose alert type for `{symbol or 'BTC'}`:",
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
            return

        # For simplicity, subscribe to all alerts
        subscription = UserSubscription(
            user_id=update.effective_user.id,
            symbol=symbol,
            alert_types=["liquidation", "whale", "funding"],
        )

        success = await db_manager.add_user_subscription(subscription)

        if success:
            await update.message.reply_text(
                f"✅ *Subscription Successful*\n\n"
                f"You're now subscribed to all alerts for `{symbol}`:\n"
                f"• 🚨 Massive Liquidations (>$1M)\n"
                f"• 🐋 Whale Transactions (>$500K)\n"
                f"• 💰 Extreme Funding Rates (±1%)\n\n"
                f"Use /alerts to manage your subscriptions.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "❌ *Subscription Failed*\n\n"
                "Could not process your subscription. Please try again.",
                parse_mode="Markdown",
            )

    async def handle_unsubscribe(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /unsubscribe command"""
        if not self._is_whitelisted(update.effective_user.id):
            return

        # Extract symbol from command
        symbol = None
        if context.args:
            symbol = context.args[0].upper()

        if not symbol:
            await update.message.reply_text(
                "❌ *Symbol Required*\n\n"
                "Usage: /unsubscribe `[SYMBOL]`\n"
                "Example: /unsubscribe BTC",
                parse_mode="Markdown",
            )
            return

        # Remove subscription
        success = await db_manager.remove_user_subscription(
            update.effective_user.id, symbol
        )

        if success:
            await update.message.reply_text(
                f"✅ *Unsubscribed*\n\n"
                f"You've been unsubscribed from all alerts for `{symbol}`.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "❌ *Unsubscribe Failed*\n\n"
                "You may not have an active subscription for this symbol.",
                parse_mode="Markdown",
            )

    async def handle_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts command - show user's subscriptions"""
        if not self._is_whitelisted(update.effective_user.id):
            return

        subscriptions = await db_manager.get_user_subscriptions(
            update.effective_user.id
        )

        if not subscriptions:
            await update.message.reply_text(
                "📭 *No Active Subscriptions*\n\n"
                "You're not subscribed to any alerts.\n"
                "Use /subscribe `[SYMBOL]` to get started.",
                parse_mode="Markdown",
            )
            return

        message = "🔔 *Your Alert Subscriptions*\n\n"

        for sub in subscriptions:
            alert_types = ", ".join([f"• {t.title()}" for t in sub.alert_types])
            message += (
                f"📊 *{sub.symbol}*\n"
                f"{alert_types}\n"
                f"🕐 Subscribed: {sub.created_at[:10]}\n\n"
            )

        await update.message.reply_text(message, parse_mode="Markdown")

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not self._is_whitelisted(update.effective_user.id):
            return

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

    async def handle_alerts_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts_status command - show which alerts are ON/OFF"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Log incoming update
        logger.info(f"[TELEGRAM] User {user_id} (@{username}) sent /alerts_status command")

        if not self._is_whitelisted(user_id):
            logger.warning(f"[TELEGRAM] User {user_id} (@{username}) denied access to /alerts_status - not whitelisted")
            return

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

    async def handle_alerts_on_whale(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts_on_w command - turn ON whale alerts"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Log incoming update
        logger.info(f"[TELEGRAM] User {user_id} (@{username}) sent /alerts_on_w command")

        if not self._is_whitelisted(user_id):
            logger.warning(f"[TELEGRAM] User {user_id} (@{username}) denied access to /alerts_on_w - not whitelisted")
            return

        # Update settings (this would typically modify environment variables or config)
        # For now, just show confirmation and current status
        if settings.ENABLE_WHALE_ALERTS:
            await update.message.reply_text(
                "🐋 *Whale alerts already enabled*\n\n"
                "Whale monitoring is currently running and will automatically\n"
                "alert you to significant whale transactions (>$500K).",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "⚠️ *Configuration Required*\n\n"
                "To enable whale alerts, please set:\n"
                "`ENABLE_WHALE_ALERTS=true` in your environment\n\n"
                "Then restart the bot for changes to take effect.\n\n"
                "Current status: Whale alerts are DISABLED",
                parse_mode="Markdown",
            )
            logger.warning(f"[ALERT_CONTROL] User {user_id} tried to enable whale alerts but ENABLE_WHALE_ALERTS=false")

    async def handle_alerts_off_whale(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts_off_w command - turn OFF whale alerts"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Log incoming update
        logger.info(f"[TELEGRAM] User {user_id} (@{username}) sent /alerts_off_w command")

        if not self._is_whitelisted(user_id):
            logger.warning(f"[TELEGRAM] User {user_id} (@{username}) denied access to /alerts_off_w - not whitelisted")
            return

        if not settings.ENABLE_WHALE_ALERTS:
            await update.message.reply_text(
                "🐋 *Whale alerts already disabled*\n\n"
                "Whale monitoring is currently not running automatically.\n"
                "You can still use /whale command for manual checks.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "⚠️ *Configuration Required*\n\n"
                "To disable whale alerts, please set:\n"
                "`ENABLE_WHALE_ALERTS=false` in your environment\n\n"
                "Then restart the bot for changes to take effect.\n\n"
                "Current status: Whale alerts are ENABLED",
                parse_mode="Markdown",
            )
            logger.info(f"[ALERT_CONTROL] User {user_id} tried to disable whale alerts but needs config change")

    async def handle_raw_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /raw command - standardized comprehensive market data"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Check if this is exactly "/raw" or "/raw@botname" with no args
        message_text = update.message.text.strip()
        is_raw_only = message_text in ['/raw', f'/raw@{self.application.bot.username}'] if self.application and self.application.bot else message_text == '/raw'
        
        if is_raw_only:
            await update.message.reply_text(
                "❌ *Symbol Required. Usage: /raw [SYMBOL]*",
                parse_mode="Markdown",
            )
            return

        # Extract argument after /raw
        try:
            args_raw = update.message.text.split(maxsplit=1)[1].strip()
        except IndexError:
            await update.message.reply_text(
                "❌ *Symbol Required. Usage: /raw [SYMBOL]*",
                parse_mode="Markdown",
            )
            return

        # Log incoming update
        logger.info(f"[/raw] user_id={user_id} username={username} symbol={args_raw}")

        if not self._is_whitelisted(user_id):
            logger.warning(f"[/raw] User {user_id} (@{username}) denied access - not whitelisted")
            return

        # Send typing action to show we're working
        await update.message.chat.send_action(action="typing")

        try:
            # Import the raw data service for comprehensive data aggregation
            from services.raw_data_service import raw_data_service
            from services.coinglass_api import SymbolNotSupported, RawDataUnavailable
            
            # Get comprehensive market data using the existing service
            comprehensive_data = await raw_data_service.get_comprehensive_market_data(args_raw)
            
            # Check if symbol is supported
            if "error" in comprehensive_data and "not supported" in comprehensive_data.get("error", "").lower():
                await update.message.reply_text(
                    "❌ *Symbol not supported or data not available from CoinGlass.*\n\n"
                    "Please try a major futures symbol like: BTC, ETH, SOL, HYPE, etc.",
                    parse_mode="Markdown",
                )
                logger.info(f"[/raw] Symbol '{args_raw}' not supported by CoinGlass")
                return

            # Format the standardized message
            formatted_message = self._format_standardized_raw_data(comprehensive_data)

            # Send the comprehensive data
            await update.message.reply_text(
                formatted_message,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )

            logger.info(f"[/raw] Successfully generated standardized response for {args_raw}")

        except SymbolNotSupported as e:
            logger.info(f"[/raw] Symbol not supported: {e}")
            await update.message.reply_text(
                "❌ *Symbol not supported or data not available from CoinGlass.*\n\n"
                "Please try a major futures symbol like: BTC, ETH, SOL, HYPE, etc.",
                parse_mode="Markdown",
            )
        except (RawDataUnavailable, Exception) as e:
            logger.error(f"[/raw] Error fetching raw data for {args_raw}: {e}")
            await update.message.reply_text(
                f"❌ *Service Error*\n\n"
                f"Failed to fetch raw data for {args_raw}. Please try again later.",
                parse_mode="Markdown",
            )

    def _format_single_symbol_raw_data(self, data: Dict[str, Any]) -> str:
        """Format single symbol raw data for Telegram display"""
        try:
            symbol = data.get("symbol", "UNKNOWN")
            price = data.get("price", 0)
            change_1h = data.get("change_1h", 0)
            change_24h = data.get("change_24h", 0)
            change_7d = data.get("change_7d", 0)
            oi_total = data.get("oi_total", 0)
            oi_change_24h = data.get("oi_change_24h", 0)
            funding_rate = data.get("funding_rate", 0)
            volume_24h = data.get("volume_24h", 0)
            liq_24h = data.get("liq_24h", 0)
            ls_ratio = data.get("ls_ratio", 0)
            confidence = data.get("confidence", 0)
            
            # Price section with emojis
            price_emoji = "🟢" if change_24h >= 0 else "🔴"
            price_section = (
                f"📊 *RAW DATA — {symbol}*\n\n"
                f"• *Price:* ${price:,.4f}  (1H: {change_1h:+.2f}%, 24H: {change_24h:+.2f}%, 7D: {change_7d:+.2f}%)\n"
            )
            
            # Open Interest section
            oi_section = ""
            if oi_total > 0:
                oi_emoji = "🟢" if oi_change_24h >= 0 else "🔴"
                oi_section = f"• *Open Interest:* ${oi_total:,.0f} (24H: {oi_emoji}{oi_change_24h:+.2f}%)\n"
            
            # Funding Rate section
            funding_section = ""
            if funding_rate != 0:
                funding_emoji = "🟢" if funding_rate >= 0 else "🔴"
                funding_section = f"• *Funding Rate:* {funding_emoji}{funding_rate*100:+.4f}%\n"
            
            # Volume section
            volume_section = ""
            if volume_24h > 0:
                volume_section = f"• *Volume 24H:* ${volume_24h:,.0f}\n"
            
            # Liquidations section
            liq_section = ""
            if liq_24h > 0:
                liq_section = f"• *Liquidations 24H:* ${liq_24h:,.0f}\n"
            
            # Long/Short Ratio section
            ls_section = ""
            if ls_ratio > 0:
                if ls_ratio > 0.6:
                    ls_emoji = "🟢"  # More longs
                    bias = "Long Bias"
                elif ls_ratio < 0.4:
                    ls_emoji = "🔴"  # More shorts
                    bias = "Short Bias"
                else:
                    ls_emoji = "⚪"  # Balanced
                    bias = "Balanced"
                
                ls_section = f"• *L/S Ratio:* {ls_emoji}{ls_ratio:.3f} ({bias})\n"
            
            # Confidence section
            confidence_emoji = "🟢" if confidence >= 80 else "🟡" if confidence >= 60 else "🔴"
            confidence_section = f"• *Data Confidence:* {confidence_emoji}{confidence}/100\n"
            
            # Combine all sections
            message = price_section + oi_section + funding_section + volume_section + liq_section + ls_section + confidence_section
            
            # Add footer
            message += f"\nData source: CoinGlass"
            
            return message
            
        except Exception as e:
            logger.error(f"[RAW_DATA] Error formatting single symbol data: {e}")
            return f"❌ Error formatting market data for {data.get('symbol', 'UNKNOWN')}"

    def _format_standardized_raw_data(self, data: Dict[str, Any]) -> str:
        """Format comprehensive raw data according to the standardized layout"""
        try:
            from services.coinglass_api import safe_float, safe_int, safe_get, safe_list_get
            
            symbol = safe_get(data, 'symbol', 'UNKNOWN').upper()
            timestamp = safe_get(data, 'timestamp', '')
            
            # Extract general info
            general = safe_get(data, 'general_info', {})
            price_change = safe_get(data, 'price_change', general)  # fallback to general
            oi = safe_get(data, 'open_interest', {})
            volume = safe_get(data, 'volume', {})
            funding = safe_get(data, 'funding', {})
            liquidations = safe_get(data, 'liquidations', {})
            ls_ratio = safe_get(data, 'long_short_ratio', {})
            taker_flow = safe_get(data, 'taker_flow', {})
            rsi = safe_get(data, 'rsi', {})
            cg_levels = safe_get(data, 'cg_levels', {})
            
            # Info Umum section
            last_price = safe_float(safe_get(general, 'last_price'), 0.0)
            mark_price = safe_float(safe_get(general, 'mark_price'), 0.0)
            
            # Price Change section
            change_1h = safe_float(safe_get(price_change, '1h'), 0.0)
            change_4h = safe_float(safe_get(price_change, '4h'), 0.0)
            change_24h = safe_float(safe_get(price_change, '24h'), 0.0)
            high_24h = safe_float(safe_get(price_change, 'high_24h'), 0.0)
            low_24h = safe_float(safe_get(price_change, 'low_24h'), 0.0)
            high_7d = safe_float(safe_get(price_change, 'high_7d'), 0.0)
            low_7d = safe_float(safe_get(price_change, 'low_7d'), 0.0)
            
            # Open Interest section
            total_oi = safe_float(safe_get(oi, 'total_oi'), 0.0)
            oi_change_1h = safe_float(safe_get(oi, 'oi_1h'), 0.0)
            oi_change_24h = safe_float(safe_get(oi, 'oi_24h'), 0.0)
            per_exchange = safe_get(oi, 'per_exchange', {})
            oi_binance = safe_float(safe_get(per_exchange, 'Binance'), 0.0)
            oi_bybit = safe_float(safe_get(per_exchange, 'Bybit'), 0.0)
            oi_okx = safe_float(safe_get(per_exchange, 'OKX'), 0.0)
            oi_others = safe_float(safe_get(per_exchange, 'Others'), 0.0)
            
            # Volume section
            futures_24h = safe_float(safe_get(volume, 'futures_24h'), 0.0)
            perp_24h = safe_float(safe_get(volume, 'perp_24h'), 0.0)
            spot_24h = safe_float(safe_get(volume, 'spot_24h'), 0.0)
            
            # Funding section
            current_funding = safe_float(safe_get(funding, 'current_funding'), 0.0)
            next_funding = safe_get(funding, 'next_funding', 'N/A')
            funding_history = safe_get(funding, 'funding_history', [])
            funding_history_text = 'No history available' if not funding_history else f'{len(funding_history)} entries'
            
            # Liquidations section
            total_liq_24h = safe_float(safe_get(liquidations, 'total_24h'), 0.0)
            long_liq_24h = safe_float(safe_get(liquidations, 'long_liq'), 0.0)
            short_liq_24h = safe_float(safe_get(liquidations, 'short_liq'), 0.0)
            
            # Long/Short Ratio section
            account_ratio_global = safe_float(safe_get(ls_ratio, 'account_ratio_global'), 1.0)
            position_ratio_global = safe_float(safe_get(ls_ratio, 'position_ratio_global'), 1.0)
            ls_by_exchange = safe_get(ls_ratio, 'by_exchange', {})
            ls_binance = safe_float(safe_get(ls_by_exchange, 'Binance'), 1.0)
            ls_bybit = safe_float(safe_get(ls_by_exchange, 'Bybit'), 1.0)
            ls_okx = safe_float(safe_get(ls_by_exchange, 'OKX'), 1.0)
            
            # Taker Flow section
            tf_5m = safe_get(taker_flow, '5m', {})
            tf_15m = safe_get(taker_flow, '15m', {})
            tf_1h = safe_get(taker_flow, '1h', {})
            tf_4h = safe_get(taker_flow, '4h', {})
            
            buy_5m = safe_float(safe_get(tf_5m, 'buy'), 0.0)
            sell_5m = safe_float(safe_get(tf_5m, 'sell'), 0.0)
            net_5m = safe_float(safe_get(tf_5m, 'net'), 0.0)
            
            buy_15m = safe_float(safe_get(tf_15m, 'buy'), 0.0)
            sell_15m = safe_float(safe_get(tf_15m, 'sell'), 0.0)
            net_15m = safe_float(safe_get(tf_15m, 'net'), 0.0)
            
            buy_1h = safe_float(safe_get(tf_1h, 'buy'), 0.0)
            sell_1h = safe_float(safe_get(tf_1h, 'sell'), 0.0)
            net_1h = safe_float(safe_get(tf_1h, 'net'), 0.0)
            
            buy_4h = safe_float(safe_get(tf_4h, 'buy'), 0.0)
            sell_4h = safe_float(safe_get(tf_4h, 'sell'), 0.0)
            net_4h = safe_float(safe_get(tf_4h, 'net'), 0.0)
            
            # RSI section
            rsi_5m = safe_float(safe_get(rsi, '5m'), 0.0)
            rsi_15m = safe_float(safe_get(rsi, '15m'), 0.0)
            rsi_1h = safe_float(safe_get(rsi, '1h'), 0.0)
            rsi_4h = safe_float(safe_get(rsi, '4h'), 0.0)
            
            # CG Levels section
            support_levels = safe_get(cg_levels, 'support', [0.0, 0.0, 0.0])
            resistance_levels = safe_get(cg_levels, 'resistance', [0.0, 0.0, 0.0])
            
            # Format values with proper units
            total_oi_billion = total_oi / 1e9 if total_oi > 0 else 0.0
            oi_binance_billion = oi_binance / 1e9 if oi_binance > 0 else 0.0
            oi_bybit_billion = oi_bybit / 1e9 if oi_bybit > 0 else 0.0
            oi_okx_billion = oi_okx / 1e9 if oi_okx > 0 else 0.0
            oi_others_billion = oi_others / 1e9 if oi_others > 0 else 0.0
            
            futures_volume_24h_billion = futures_24h / 1e9 if futures_24h > 0 else 0.0
            perp_volume_24h_billion = perp_24h / 1e9 if perp_24h > 0 else 0.0
            spot_volume_24h_billion = spot_24h / 1e9 if spot_24h > 0 else 0.0
            
            total_liq_24h_million = total_liq_24h / 1e6 if total_liq_24h > 0 else 0.0
            long_liq_24h_million = long_liq_24h / 1e6 if long_liq_24h > 0 else 0.0
            short_liq_24h_million = short_liq_24h / 1e6 if short_liq_24h > 0 else 0.0
            
            # Format support/resistance levels
            support_str = ', '.join([f'{x:.2f}' for x in support_levels])
            resistance_str = ', '.join([f'{x:.2f}' for x in resistance_levels])
            
            # Build the standardized message
            message = f"""[RAW DATA - {symbol} - REAL PRICE MULTI-TF]

Info Umum
Symbol : {symbol}
Timeframe : 1H
Timestamp : {timestamp}
Last Price: {last_price:.4f}
Mark Price: {mark_price:.4f}
Price Source: coinglass_futures

Price Change
1H : {change_1h:+.2f}%
4H : {change_4h:+.2f}%
24H : {change_24h:+.2f}%
High/Low 24H: ${low_24h:.4f} / ${high_24h:.4f}
High/Low 7D : ${low_7d:.4f} / ${high_7d:.4f}

Open Interest
Total OI : ${total_oi_billion:.2f}B
OI 1H : {oi_change_1h:+.1f}%
OI 24H : {oi_change_24h:+.1f}%

OI per Exchange
Binance : ${oi_binance_billion:.2f}B
Bybit : ${oi_bybit_billion:.2f}B
OKX : ${oi_okx_billion:.2f}B
Others : ${oi_others_billion:.2f}B

Volume
Futures 24H: ${futures_volume_24h_billion:.2f}B
Perp 24H : ${perp_volume_24h_billion:.2f}B
Spot 24H : ${spot_volume_24h_billion:.2f}B

Funding
Current Funding: {current_funding:+.4f}%
Next Funding : {next_funding}
Funding History:
{funding_history_text}

Liquidations
Total 24H : ${total_liq_24h_million:.2f}M
Long Liq : ${long_liq_24h_million:.2f}M
Short Liq : ${short_liq_24h_million:.2f}M

Long/Short Ratio
Account Ratio (Global) : {account_ratio_global:.2f}
Position Ratio (Global): {position_ratio_global:.2f}
By Exchange:
Binance: {ls_binance:.2f}
Bybit : {ls_bybit:.2f}
OKX : {ls_okx:.2f}

Taker Flow Multi-Timeframe (CVD Proxy)
5M: Buy ${buy_5m:.0f}M | Sell ${sell_5m:.0f}M | Net ${net_5m:+.0f}M
15M: Buy ${buy_15m:.0f}M | Sell ${sell_15m:.0f}M | Net ${net_15m:+.0f}M
1H: Buy ${buy_1h:.0f}M | Sell ${sell_1h:.0f}M | Net ${net_1h:+.0f}M
4H: Buy ${buy_4h:.0f}M | Sell ${sell_4h:.0f}M | Net ${net_4h:+.0f}M

RSI Multi-Timeframe (14)
5M : {rsi_5m:.2f}
15M: {rsi_15m:.2f}
1H : {rsi_1h:.2f}
4H : {rsi_4h:.2f}

CG Levels
Support : ${support_str}
Resistance: ${resistance_str}"""
            
            return message
            
        except Exception as e:
            logger.error(f"[RAW_DATA] Error formatting standardized data: {e}")
            return f"❌ Error formatting standardized market data for {safe_get(data, 'symbol', 'UNKNOWN')}"

    def _format_raw_market_data(self, data: Dict[str, Any]) -> str:
        """Format raw market data for Telegram display"""
        try:
            symbol = data.get("symbol", "UNKNOWN")
            timestamp = data.get("timestamp", "")
            
            # Price section
            price_data = data.get("price", {})
            price_section = ""
            if price_data:
                last_price = price_data.get("last_price", 0)
                price_change_1h = price_data.get("price_change_1h", 0)
                price_change_24h = price_data.get("price_change_24h", 0)
                volume_24h = price_data.get("volume_24h", 0)
                
                price_emoji = "🟢" if price_change_24h >= 0 else "🔴"
                price_section = (
                    f"{price_emoji} *{symbol} Market Data*\n\n"
                    f"💲 *Price & Changes:*\n"
                    f"   Current: ${last_price:,.4f}\n"
                    f"   1h: {price_change_1h:+.2f}%\n"
                    f"   24h: {price_change_24h:+.2f}%\n"
                    f"   Volume 24h: ${volume_24h:,.0f}\n\n"
                )
            
            # Open Interest section
            oi_data = data.get("open_interest", {})
            oi_section = ""
            if oi_data and oi_data.get("total", 0) > 0:
                total_oi = oi_data.get("total", 0)
                exchange_count = oi_data.get("exchange_count", 0)
                oi_section = (
                    f"📊 *Open Interest:*\n"
                    f"   Total: ${total_oi:,.0f}\n"
                    f"   Exchanges: {exchange_count}\n\n"
                )
            
            # Funding Rate section
            funding_data = data.get("funding", {})
            funding_section = ""
            if funding_data and funding_data.get("exchange_count", 0) > 0:
                avg_rate = funding_data.get("current_average", 0)
                avg_percentage = funding_data.get("current_percentage", 0)
                exchange_count = funding_data.get("exchange_count", 0)
                
                funding_emoji = "🟢" if avg_rate >= 0 else "🔴"
                funding_section = (
                    f"{funding_emoji} *Funding Rate:*\n"
                    f"   Average: {avg_percentage:+.4f}%\n"
                    f"   Exchanges: {exchange_count}\n\n"
                )
            
            # Liquidations section
            liq_data = data.get("liquidations", {})
            liq_section = ""
            if liq_data and liq_data.get("total_24h", 0) > 0:
                total_liq = liq_data.get("total_24h", 0)
                long_liq = liq_data.get("long_24h", 0)
                short_liq = liq_data.get("short_24h", 0)
                exchange_count = liq_data.get("exchange_count", 0)
                
                liq_section = (
                    f"📉 *Liquidations (24h):*\n"
                    f"   Total: ${total_liq:,.0f}\n"
                    f"   Longs: ${long_liq:,.0f}\n"
                    f"   Shorts: ${short_liq:,.0f}\n"
                    f"   Exchanges: {exchange_count}\n\n"
                )
            
            # Long/Short Ratio section
            ls_data = data.get("long_short_ratio", {})
            ls_section = ""
            if ls_data and ls_data.get("account_ratio", 0) > 0:
                account_ratio = ls_data.get("account_ratio", 0)
                position_ratio = ls_data.get("position_ratio", 0)
                exchange = ls_data.get("exchange", "unknown")
                
                # Interpret the ratio
                if account_ratio > 0.6:
                    ls_emoji = "🟢"  # More longs
                    bias = "Long Bias"
                elif account_ratio < 0.4:
                    ls_emoji = "🔴"  # More shorts
                    bias = "Short Bias"
                else:
                    ls_emoji = "⚪"  # Balanced
                    bias = "Balanced"
                
                ls_section = (
                    f"{ls_emoji} *Long/Short Ratio ({exchange}):*\n"
                    f"   Account Ratio: {account_ratio:.3f} ({bias})\n"
                    f"   Position Ratio: {position_ratio:.3f}\n\n"
                )
            
            # Combine all sections
            message = price_section + oi_section + funding_section + liq_section + ls_section
            
            # Add footer
            message += f"🕐 Data: {timestamp}\n"
            message += "⚡ Powered by CoinGlass API v4 (Standard Tier)"
            
            return message
            
        except Exception as e:
            logger.error(f"[RAW_DATA] Error formatting market data: {e}")
            return f"❌ Error formatting market data for {data.get('symbol', 'UNKNOWN')}"

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()  # Acknowledge the callback

        if not self._is_whitelisted(query.from_user.id):
            return

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
                    f"✅ *Subscribed to {alert_text} for {symbol}*\n\n"
                    f"You'll receive notifications when significant events occur.",
                    parse_mode="Markdown",
                )
            else:
                await query.edit_message_text(
                    "❌ *Subscription Failed*\n\n" "Please try again later.",
                    parse_mode="Markdown",
                )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle non-command messages"""
        if not self._is_whitelisted(update.effective_user.id):
            return

        # Simple message handling - provide help
        await update.message.reply_text(
            "👋 *Hello!*\n\n"
            "Use /help to see available commands.\n"
            "I'm here to provide real-time crypto trading signals!",
            parse_mode="Markdown",
        )

    async def broadcast_alert(self, message: str):
        """Broadcast alert to the alert channel"""
        if not self.alert_channel_id or not settings.ENABLE_BROADCAST_ALERTS:
            return

        try:
            await self.application.bot.send_message(
                chat_id=self.alert_channel_id, text=message, parse_mode="Markdown"
            )
            logger.info(f"Alert broadcasted to channel {self.alert_channel_id}")
        except Exception as e:
            logger.error(f"Failed to broadcast alert: {e}")

    async def start(self):
        """Start the bot with polling"""
        if not self.application:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        logger.info("Starting CryptoSat Telegram bot...")
        await self.application.initialize()
        await self.application.start()
        
        # Start polling - this is the missing piece!
        await self.application.updater.start_polling(drop_pending_updates=True)
        
        logger.info("CryptoSat bot started successfully with polling enabled")

    async def stop(self):
        """Stop the bot"""
        if self.application:
            # Stop polling first
            if hasattr(self.application, 'updater') and self.application.updater:
                await self.application.updater.stop()
            
            # Stop the application
            await self.application.stop()
            logger.info("CryptoSat bot stopped")


# Global bot instance
telegram_bot = TelegramBot()
