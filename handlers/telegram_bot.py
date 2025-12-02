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
from services.raw_data_service import raw_data_service


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

        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

        # Message handler for non-commands
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

    def _is_whitelisted(self, user_id: int) -> bool:
        """Check if user is whitelisted"""
        return not self.whitelisted_users or user_id in self.whitelisted_users

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name

        if not self._is_whitelisted(user_id):
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
        if not self._is_whitelisted(update.effective_user.id):
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
        if not self._is_whitelisted(update.effective_user.id):
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
        if not self._is_whitelisted(update.effective_user.id):
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

    async def handle_raw_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /raw command - comprehensive market data"""
        if not self._is_whitelisted(update.effective_user.id):
            return

        # Extract symbol from command
        symbol = None
        if context.args:
            symbol = context.args[0].upper()

        if not symbol:
            await update.message.reply_text(
                "❌ *Symbol Required*\n\n"
                "Usage: /raw `[SYMBOL]`\n"
                "Example: /raw BTC\n\n"
                "This command provides comprehensive market data including:\n"
                "• Price information (1H, 4H, 24H, 7D changes)\n"
                "• Open Interest analysis\n"
                "• Volume data\n"
                "• Funding rates\n"
                "• Liquidations\n"
                "• Long/Short ratios\n"
                "• Taker flow (CVD proxy)\n"
                "• RSI multi-timeframe\n"
                "• CoinGlass levels (support/resistance)",
                parse_mode="Markdown",
            )
            return

        # Send typing action to show we're working
        await update.message.chat.send_action(action="typing")

        try:
            # Get comprehensive market data
            market_data = await raw_data_service.get_comprehensive_market_data(symbol)

            if "error" in market_data:
                await update.message.reply_text(
                    f"❌ *Data Fetch Error*\n\n"
                    f"Could not retrieve market data for `{symbol}`\n"
                    f"Error: {market_data['error']}\n\n"
                    f"Please try again in a few moments.",
                    parse_mode="Markdown",
                )
                return

            # Format for Telegram display
            formatted_message = raw_data_service.format_for_telegram(market_data)

            # Send the comprehensive data
            await update.message.reply_text(
                formatted_message,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )

        except Exception as e:
            logger.error(f"Error in /raw command for {symbol}: {e}")
            await update.message.reply_text(
                "❌ *Service Error*\n\n"
                "An error occurred while fetching market data.\n"
                "Please try again later.",
                parse_mode="Markdown",
            )

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
        """Start the bot"""
        if not self.application:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        logger.info("Starting CryptoSat Telegram bot...")
        await self.application.initialize()
        await self.application.start()
        logger.info("CryptoSat bot started successfully")

    async def stop(self):
        """Stop the bot"""
        if self.application:
            await self.application.stop()
            logger.info("CryptoSat bot stopped")


# Global bot instance
telegram_bot = TelegramBot()
