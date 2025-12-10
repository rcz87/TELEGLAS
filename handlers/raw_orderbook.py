#!/usr/bin/env python3
"""
Handler for /raw_orderbook command - using new message builder with proper error handling
"""

import asyncio
import sys
import re
from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

# Add parent directory to path for imports
sys.path.insert(0, '.')

async def raw_orderbook_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /raw_orderbook command - using new message builder with English standardization
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    try:
        # Extract symbol from command
        if not context.args:
            await update.message.reply_text(
                "❌ *Symbol Required*\n\n"
                "Usage: /raw_orderbook `[SYMBOL]`\n\n"
                "Examples:\n"
                "• /raw_orderbook BTC\n"
                "• /raw_orderbook ETH\n"
                "• /raw_orderbook SOL",
                parse_mode="Markdown"
            )
            return
        
        symbol = context.args[0].upper()
        
        # Validate symbol format
        if not re.match(r'^[A-Z]{2,6}$', symbol):
            await update.message.reply_text(
                "❌ *Invalid Symbol*\n\n"
                "Symbol must be 2-6 letters (A-Z only).\n\n"
                "Examples: BTC, ETH, SOL, ADA, DOT, AVAX, MATIC\n\n"
                "Usage: /raw_orderbook `[SYMBOL]`",
                parse_mode="Markdown"
            )
            return
        
        # Send typing action to show we're working
        await update.message.chat.send_action(action="typing")
        
        # Use new message builder with proper error handling
        from utils.message_builders import build_raw_orderbook_message
        
        # Build message using new builder
        formatted_message = await build_raw_orderbook_message(symbol, "Binance")
        
        # Add data source label for consistency
        header = "📊 *ORDERBOOK DEPTH* `[Data Source: Multi-Exchange]`\n\n"
        final_message = header + formatted_message
        
        # Check if message indicates no data available
        if "❌ No orderbook data available" in formatted_message or "❌ Error building" in formatted_message:
            # Provide a more user-friendly fallback message
            fallback_message = f"""❌ *Orderbook Data Unavailable*

Orderbook data is temporarily unavailable for `{symbol}`.

**What happened:**
• CoinGlass orderbook API may be experiencing delays
• This symbol might have limited orderbook support
• Market data temporarily unavailable

**Try these alternatives:**
• /raw `{symbol}` → General market data (always available)
• /raw_orderbook BTC → Try with major symbols
• Wait 30 seconds and retry

💡 *Best results:* Orderbook works best with BTC, ETH, SOL futures"""
            
            await update.message.reply_text(fallback_message, parse_mode="Markdown")
        else:
            # Send formatted orderbook data
            await update.message.reply_text(final_message, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"[RAW_ORDERBOOK_HANDLER] Error: {e}")
        await update.message.reply_text(
            "❌ *Service Error*\n\n"
            "Failed to fetch orderbook data.\n\n"
            "Please try again in a few moments.\n"
            "If problem persists, contact admin.",
            parse_mode="Markdown"
        )
