#!/usr/bin/env python3
"""
Debug script to examine the structure of futures/supported-coins response
"""

import asyncio
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.coinglass_api import coinglass_api

async def debug_futures_coins_structure():
    """Debug the structure of futures/supported-coins response"""
    
    print("Debugging Futures/Supported-Coins Structure")
    print("=" * 50)
    
    try:
        async with coinglass_api:
            result = await coinglass_api.get_supported_futures_coins()
            
            if result.get("success"):
                data = result.get("data", [])
                print(f"Total coins retrieved: {len(data)}")
                
                if isinstance(data, list) and data:
                    print("\nFirst 3 items structure:")
                    for i, item in enumerate(data[:3], 1):
                        print(f"\nItem {i}:")
                        print(f"Type: {type(item)}")
                        if isinstance(item, dict):
                            print("Keys:", list(item.keys()))
                            for key, value in item.items():
                                print(f"  {key}: {value} (type: {type(value)})")
                        else:
                            print(f"Value: {item}")
                    
                    print("\nLooking for common symbol fields...")
                    symbol_fields = []
                    for i, item in enumerate(data[:20], 1):  # Check first 20 items
                        if isinstance(item, dict):
                            for key in item.keys():
                                if any(keyword in key.lower() for keyword in ['symbol', 'pair', 'name', 'coin', 'ticker']):
                                    if key not in symbol_fields:
                                        symbol_fields.append(key)
                    
                    print(f"Found potential symbol fields: {symbol_fields}")
                    
                    print("\nSample symbol extractions:")
                    test_fields = ['symbol', 'pair', 'name', 'coin', 'baseAsset', 'quoteAsset']
                    
                    for i, item in enumerate(data[:5], 1):
                        print(f"\nItem {i}:")
                        for field in test_fields:
                            if field in item:
                                value = str(item[field]).upper().strip()
                                print(f"  {field}: {value}")
                                
                                # Try to extract base symbol
                                if value.endswith('USDT'):
                                    base = value[:-4]
                                    print(f"    -> Base: {base}")
                                elif value.endswith('USD'):
                                    base = value[:-3]
                                    print(f"    -> Base: {base}")
                
                print("\n" + "=" * 50)
                print("Debug complete!")
            else:
                print(f"API call failed: {result.get('error')}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_futures_coins_structure())
