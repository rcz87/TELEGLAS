#!/usr/bin/env python3
"""
Raw Format Preview Tool
Displays the complete output from build_raw_message and build_raw_orderbook_message
without any modifications to existing code.
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.raw_data_service import RawDataService
from utils.formatters import build_raw_orderbook_text_enhanced


async def preview_raw_formats():
    """Preview current raw and raw_orderbook message formats"""
    
    print("=" * 80)
    print("RAW FORMAT PREVIEW - CURRENT IMPLEMENTATION")
    print("=" * 80)
    print()
    
    # Test build_raw_message
    print("1. build_raw_message('BTC') OUTPUT:")
    print("-" * 60)
    try:
        service = RawDataService()
        raw_data = await service.get_comprehensive_market_data("BTC")
        
        if not raw_data or "error" in raw_data:
            print("❌ No raw data available for BTC")
        else:
            message = service.format_standard_raw_message_for_telegram(raw_data)
            print(message)
    except Exception as e:
        print(f"ERROR: {e}")
    
    print("\n" + "=" * 80)
    print()
    
    # Test build_raw_orderbook_message
    print("2. build_raw_orderbook_message('BTC', 'Binance') OUTPUT:")
    print("-" * 60)
    try:
        service = RawDataService()
        orderbook_data = await service.build_raw_orderbook_data("BTC")
        
        if not orderbook_data:
            print("❌ No orderbook data available for BTC")
        else:
            message = build_raw_orderbook_text_enhanced(orderbook_data)
            print(message)
    except Exception as e:
        print(f"ERROR: {e}")
    
    print("\n" + "=" * 80)
    print("PREVIEW COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(preview_raw_formats())
