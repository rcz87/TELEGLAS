#!/usr/bin/env python3
"""
Handler for /raw_orderbook command - using new message builder with proper error handling
"""

import asyncio
import sys
from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

# Add parent directory to path for imports
sys.path.insert(0, '.')

async def raw_orderbook_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /raw_orderbook command - using new message builder
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    try:
        # Extract symbol from command
        if not context.args:
            await update.message.reply_text("📋 *Usage:* `/raw_orderbook <symbol>`\n\nExample: `/raw_orderbook BOB` or `/raw_orderbook BTC`")
            return
        
        symbol = context.args[0].upper()
        
        # Send typing action to show we're working
        await update.message.chat.send_action(action="typing")
        
        # Use new message builder with proper error handling
        from utils.message_builders import build_raw_orderbook_message
        
        # Build message using the new builder
        formatted_message = await build_raw_orderbook_message(symbol, "Binance")
        
        # Check if the message indicates no data available
        if "❌ No orderbook data available" in formatted_message or "❌ Error building" in formatted_message:
            # Provide a more user-friendly fallback message
            fallback_message = f"""[RAW ORDERBOOK - {symbol}]

Orderbook data tidak tersedia untuk simbol ini saat ini.
Kemungkinan:
• Pair ini belum didukung penuh oleh endpoint orderbook.
• Data orderbook untuk simbol ini sedang kosong.

Coba gunakan /raw {symbol} untuk melihat data pasar umumnya."""
            
            await update.message.reply_text(fallback_message)
        else:
            # Send the formatted orderbook data
            await update.message.reply_text(formatted_message)
            
    except Exception as e:
        logger.error(f"[RAW_ORDERBOOK_HANDLER] Error: {e}")
        await update.message.reply_text(f"""⚠️ Terjadi kesalahan saat mengambil data orderbook untuk {symbol if 'symbol' in locals() else 'simbol'}. Coba lagi beberapa saat lagi.""")
