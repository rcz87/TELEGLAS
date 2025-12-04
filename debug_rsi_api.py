#!/usr/bin/env python3
"""
Debug RSI API response to understand the issue
"""

import asyncio
import json
from services.coinglass_api import coinglass_api


async def debug_rsi_api():
    """Debug RSI API response structure"""
    
    async with coinglass_api:
        # Test with different parameters
        test_cases = [
            {"symbol": "BTCUSDT", "interval": "1h", "exchange": "Binance"},
            {"symbol": "BTCUSDT", "interval": "1d", "exchange": "Binance"},
            {"symbol": "ETHUSDT", "interval": "1h", "exchange": "Binance"},
        ]
        
        for params in test_cases:
            print(f"\n=== Testing with params: {params} ===")
            
            # Call the API directly
            result = await coinglass_api._make_request("/api/futures/indicators/rsi", params)
            
            print(f"Success: {result.get('success')}")
            print(f"Error: {result.get('error', 'None')}")
            print(f"Data length: {len(result.get('data', []))}")
            
            if result.get('data'):
                print(f"First data item: {json.dumps(result['data'][0], indent=2) if result['data'] else 'None'}")
                print(f"Last data item: {json.dumps(result['data'][-1], indent=2) if result['data'] else 'None'}")
            else:
                print("No data returned")
            
            # Try the full response
            print(f"Full response keys: {list(result.keys())}")


if __name__ == "__main__":
    asyncio.run(debug_rsi_api())
