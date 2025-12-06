#!/usr/bin/env python3
"""
Debug script khusus untuk enhanced format
"""

import asyncio
import sys
import traceback
sys.path.insert(0, '.')

from services.coinglass_api import CoinGlassAPI

async def debug_enhanced_format():
    print('=== DEBUGGING ENHANCED FORMAT ===')
    
    api = CoinGlassAPI()
    
    # Test BOB symbol
    symbol = 'BOB'
    base_symbol, futures_pair = api.resolve_orderbook_symbols(symbol)
    print(f'Symbol: {symbol} -> Base: {base_symbol}, Futures: {futures_pair}')
    
    try:
        # Get real data from API
        binance_depth = await api.get_orderbook_ask_bids_history(base_symbol, futures_pair, 'Binance', '1d', 100, '1')
        agg_depth = await api.get_aggregated_orderbook_ask_bids_history(base_symbol, 'Binance', 'h1', 500)
        
        print('\n=== DETAILED ENHANCED FORMAT INSPECTION ===')
        
        # Inspect binance depth data
        print('\n--- Binance Depth Enhanced Format ---')
        if isinstance(binance_depth, dict):
            print(f'Keys: {list(binance_depth.keys())}')
            print(f'Supported: {binance_depth.get("supported")}')
            print(f'Success: {binance_depth.get("success")}')
            
            if "depth_data" in binance_depth:
                depth_data = binance_depth["depth_data"]
                print(f'Depth data type: {type(depth_data)}')
                print(f'Depth data keys: {list(depth_data.keys()) if isinstance(depth_data, dict) else "Not a dict"}')
                
                if isinstance(depth_data, dict):
                    for key, value in depth_data.items():
                        print(f'  {key}: {value} (type: {type(value)})')
            
            # Check if it has the expected structure
            if "supported" in binance_depth and binance_depth.get("supported"):
                print('✅ Enhanced format detected and supported')
                if "depth_data" in binance_depth and binance_depth["depth_data"]:
                    print('✅ Depth data available')
                else:
                    print('❌ Depth data missing or empty')
            else:
                print('❌ Enhanced format not supported')
        
        # Inspect aggregated depth data
        print('\n--- Aggregated Depth Enhanced Format ---')
        if isinstance(agg_depth, dict):
            print(f'Keys: {list(agg_depth.keys())}')
            print(f'Supported: {agg_depth.get("supported")}')
            print(f'Success: {agg_depth.get("success")}')
            
            if "aggregated_data" in agg_depth:
                agg_data = agg_depth["aggregated_data"]
                print(f'Aggregated data type: {type(agg_data)}')
                print(f'Aggregated data keys: {list(agg_data.keys()) if isinstance(agg_data, dict) else "Not a dict"}')
                
                if isinstance(agg_data, dict):
                    for key, value in agg_data.items():
                        print(f'  {key}: {value} (type: {type(value)})')
            
            # Check if it has the expected structure
            if "supported" in agg_depth and agg_depth.get("supported"):
                print('✅ Enhanced format detected and supported')
                if "aggregated_data" in agg_depth and agg_depth["aggregated_data"]:
                    print('✅ Aggregated data available')
                else:
                    print('❌ Aggregated data missing or empty')
            else:
                print('❌ Enhanced format not supported')
        
        # Test manual extraction
        print('\n=== MANUAL EXTRACTION TEST ===')
        
        # Test Binance depth extraction
        if isinstance(binance_depth, dict) and binance_depth.get("supported"):
            depth_data = binance_depth.get("depth_data", {})
            if depth_data:
                bids_usd = depth_data.get("bids_usd", 0)
                asks_usd = depth_data.get("asks_usd", 0)
                print(f'Binance - Bids USD: {bids_usd}, Asks USD: {asks_usd}')
                
                if bids_usd > 0 or asks_usd > 0:
                    print('✅ Binance depth data has values')
                else:
                    print('❌ Binance depth data has no values')
        
        # Test Aggregated depth extraction
        if isinstance(agg_depth, dict) and agg_depth.get("supported"):
            agg_data = agg_depth.get("aggregated_data", {})
            if agg_data:
                agg_bids_usd = agg_data.get("aggregated_bids_usd", 0)
                agg_asks_usd = agg_data.get("aggregated_asks_usd", 0)
                print(f'Aggregated - Bids USD: {agg_bids_usd}, Asks USD: {agg_asks_usd}')
                
                if agg_bids_usd > 0 or agg_asks_usd > 0:
                    print('✅ Aggregated depth data has values')
                else:
                    print('❌ Aggregated depth data has no values')
        
    except Exception as e:
        print(f'Error: {e}')
        traceback.print_exc()
    
    await api.close_session()

if __name__ == "__main__":
    asyncio.run(debug_enhanced_format())
