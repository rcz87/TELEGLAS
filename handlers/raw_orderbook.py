#!/usr/bin/env python3
"""
Handler for /raw_orderbook command
"""

import asyncio
import sys
from loguru import logger
from services.raw_data_service import raw_data_service

# Add parent directory to path for imports
sys.path.insert(0, '..')

async def raw_orderbook_handler(message):
    """
    Handle /raw_orderbook command
    
    Args:
        message: Telegram message object
    """
    try:
        # Extract symbol from message
        text = message.text.strip()
        parts = text.split()
        
        if len(parts) < 2:
            await message.reply("📋 *Usage:* `/raw_orderbook <symbol>`\n\nExample: `/raw_orderbook BOB` or `/raw_orderbook BTC`")
            return
        
        symbol = parts[1].upper()
        
        # Skip typing indicator for testing
        
        # Get raw orderbook data
        orderbook_data = await raw_data_service.build_raw_orderbook_data(symbol)
        
        # Format message using formatter
        from utils.formatters import build_raw_orderbook_text
        formatted_message = build_raw_orderbook_text(
            orderbook_data.get("symbol", symbol),
            orderbook_data.get("snapshot", {}),
            orderbook_data.get("binance_depth", {}),
            orderbook_data.get("aggregated_depth", {})
        )
        
        # Send the formatted orderbook data
        await message.reply(formatted_message)
            
    except Exception as e:
        logger.error(f"[RAW_ORDERBOOK_HANDLER] Error: {e}")
        await message.reply("❌ Error processing orderbook request. Please try again later.")
