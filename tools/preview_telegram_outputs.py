#!/usr/bin/env python3
"""
TELEGLAS Preview Engine
Preview output dari 4 command utama tanpa menjalankan bot

Cara menjalankan:
#   cd /opt/TELEGLAS
#   source venv/bin/activate
#   python -m tools.preview_telegram_outputs
"""

import asyncio
import sys
import os
from datetime import datetime
from loguru import logger

# Add parent directory to path untuk import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.message_builders import (
    build_liq_message,
    build_whale_message,
    build_raw_message,
    build_raw_orderbook_message
)


def print_banner():
    """Print banner untuk preview engine"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                TELEGLAS PREVIEW ENGINE                          ║
║                                                              ║
║  Preview output 4 command utama TANPA menjalankan bot:         ║
║  • /liq      - Liquidation data                              ║
║  • /whale    - Whale radar                                   ║
║  • /raw      - Raw market data                               ║
║  • /raw_orderbook - Orderbook depth analysis                 ║
║                                                              ║
║  Data real dari CoinGlass API                                 ║
║  TIDAK mengirim apapun ke Telegram                           ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_separator(title: str):
    """Print separator dengan title"""
    separator = f"\n{'='*60}"
    print(separator)
    print(f"  {title}")
    print(separator)


async def preview_liq():
    """Preview liquidation command output"""
    try:
        print("\n🔍 PREVIEW: /liq command")
        print("   Symbol: BTC (default)")
        print("   Source: CoinGlass Liquidation API")
        print("   Format: Telegram message")
        print("-" * 60)
        
        # Build liquidation message
        message = await build_liq_message("BTC")
        
        print(message)
        
    except Exception as e:
        logger.error(f"[PREVIEW_LIQ] Error: {e}")
        print(f"❌ Error previewing /liq: {str(e)}")


async def preview_whale():
    """Preview whale radar command output"""
    try:
        print("\n🔍 PREVIEW: /whale command")
        print("   Source: Hyperliquid Whale API")
        print("   Format: Telegram message")
        print("-" * 60)
        
        # Build whale message
        message = await build_whale_message()
        
        print(message)
        
    except Exception as e:
        logger.error(f"[PREVIEW_WHALE] Error: {e}")
        print(f"❌ Error previewing /whale: {str(e)}")


async def preview_raw():
    """Preview raw market data command output"""
    try:
        print("\n🔍 PREVIEW: /raw command")
        print("   Symbol: BTC")
        print("   Source: CoinGlass Market Data API")
        print("   Format: Telegram message")
        print("-" * 60)
        
        # Build raw message
        message = await build_raw_message("BTC")
        
        print(message)
        
    except Exception as e:
        logger.error(f"[PREVIEW_RAW] Error: {e}")
        print(f"❌ Error previewing /raw: {str(e)}")


async def preview_raw_orderbook():
    """Preview raw orderbook command output"""
    try:
        print("\n🔍 PREVIEW: /raw_orderbook command")
        print("   Symbol: BTC")
        print("   Exchange: Binance")
        print("   Source: CoinGlass Orderbook API")
        print("   Format: Telegram message")
        print("-" * 60)
        
        # Build raw orderbook message
        message = await build_raw_orderbook_message("BTC", "Binance")
        
        print(message)
        
    except Exception as e:
        logger.error(f"[PREVIEW_RAW_ORDERBOOK] Error: {e}")
        print(f"❌ Error previewing /raw_orderbook: {str(e)}")


async def run_all_previews():
    """Jalankan semua preview functions"""
    start_time = datetime.now()
    
    print_banner()
    print(f"\n⏰ Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Preview 1: Liquidation
    print_separator("1. LIQUIDATION DATA (/liq)")
    await preview_liq()
    
    # Preview 2: Whale Radar
    print_separator("2. WHALE RADAR (/whale)")
    await preview_whale()
    
    # Preview 3: Raw Market Data
    print_separator("3. RAW MARKET DATA (/raw)")
    await preview_raw()
    
    # Preview 4: Raw Orderbook
    print_separator("4. RAW ORDERBOOK (/raw_orderbook)")
    await preview_raw_orderbook()
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    print_separator("PREVIEW SUMMARY")
    print(f"✅ All previews completed successfully!")
    print(f"⏰ Duration: {duration.total_seconds():.2f} seconds")
    print(f"🕐 Ended at: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("\n📝 NOTES:")
    print("• Data diambil langsung dari CoinGlass API")
    print("• Output sama persis seperti yang akan muncul di Telegram")
    print("• TIDAK mengirim apapun ke Telegram")
    print("• TIDAK mengganggu operasi bot yang sedang berjalan")
    print("• Bisa dijalankan kapan saja tanpa mempengaruhi bot")


async def main():
    """Main function untuk preview engine"""
    try:
        # Configure logger untuk preview
        logger.remove()
        logger.add(sys.stdout, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")
        
        # Run all previews
        await run_all_previews()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Preview interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"[MAIN] Error: {e}")
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Run preview engine
    asyncio.run(main())
