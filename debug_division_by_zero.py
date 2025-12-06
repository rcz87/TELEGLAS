#!/usr/bin/env python3
"""
Debug script untuk menemukan sumber division by zero error
"""

import asyncio
import sys
import traceback
sys.path.insert(0, '.')

from services.coinglass_api import CoinGlassAPI
from utils.formatters import build_raw_orderbook_text

async def debug_division_by_zero():
    print('=== DEBUGGING DIVISION BY ZERO ===')
    
    api = CoinGlassAPI()
    
    # Test BOB symbol
    symbol = 'BOB'
    base_symbol, futures_pair = api.resolve_orderbook_symbols(symbol)
    print(f'Symbol: {symbol} -> Base: {base_symbol}, Futures: {futures_pair}')
    
    try:
        # Get real data from API
        history_data = await api.get_orderbook_history_snapshot(futures_pair, 'Binance', '1h', 1)
        binance_depth = await api.get_orderbook_ask_bids_history(base_symbol, futures_pair, 'Binance', '1d', 100, '1')
        agg_depth = await api.get_aggregated_orderbook_ask_bids_history(base_symbol, 'Binance', 'h1', 500)
        
        print('\n=== DETAILED DATA INSPECTION ===')
        
        # Inspect history data
        print('\n--- History Data Detail ---')
        if isinstance(history_data, dict):
            print(f'Keys: {list(history_data.keys())}')
            if 'bids' in history_data:
                bids = history_data['bids']
                print(f'Bids type: {type(bids)}, length: {len(bids) if isinstance(bids, list) else "N/A"}')
                if isinstance(bids, list) and len(bids) > 0:
                    print(f'First bid: {bids[0]}')
            if 'asks' in history_data:
                asks = history_data['asks']
                print(f'Asks type: {type(asks)}, length: {len(asks) if isinstance(asks, list) else "N/A"}')
                if isinstance(asks, list) and len(asks) > 0:
                    print(f'First ask: {asks[0]}')
        
        # Inspect binance depth data
        print('\n--- Binance Depth Data Detail ---')
        if isinstance(binance_depth, dict):
            print(f'Keys: {list(binance_depth.keys())}')
            print(f'Supported: {binance_depth.get("supported")}')
            if 'depth_data' in binance_depth:
                depth_data = binance_depth['depth_data']
                print(f'Depth data type: {type(depth_data)}')
                if isinstance(depth_data, dict):
                    print(f'Depth data keys: {list(depth_data.keys())}')
                    for key, value in depth_data.items():
                        print(f'  {key}: {value} (type: {type(value)})')
        
        # Inspect aggregated depth data
        print('\n--- Aggregated Depth Data Detail ---')
        if isinstance(agg_depth, dict):
            print(f'Keys: {list(agg_depth.keys())}')
            print(f'Supported: {agg_depth.get("supported")}')
            if 'aggregated_data' in agg_depth:
                agg_data = agg_depth['aggregated_data']
                print(f'Aggregated data type: {type(agg_data)}')
                if isinstance(agg_data, dict):
                    print(f'Aggregated data keys: {list(agg_data.keys())}')
                    for key, value in agg_data.items():
                        print(f'  {key}: {value} (type: {type(value)})')
        
        # Test formatter with try-catch around each section
        print('\n=== TESTING FORMATTER STEP BY STEP ===')
        
        try:
            result = build_raw_orderbook_text(futures_pair, history_data, binance_depth, agg_depth)
            print('SUCCESS: Formatter completed without error')
            print(result[:500] + '...' if len(result) > 500 else result)
        except Exception as e:
            print(f'ERROR in formatter: {e}')
            traceback.print_exc()
            
            # Try to identify which section causes the error
            print('\n=== TESTING INDIVIDUAL SECTIONS ===')
            
            # Test snapshot bias calculation
            try:
                from utils.formatters import safe_float
                if isinstance(history_data, dict) and 'bids' in history_data and 'asks' in history_data:
                    bids_data = history_data['bids']
                    asks_data = history_data['asks']
                    
                    if isinstance(bids_data, list) and isinstance(asks_data, list) and bids_data and asks_data:
                        # Extract bid levels
                        bid_levels = []
                        for bid in bids_data[:3]:
                            if isinstance(bid, list) and len(bid) >= 2:
                                price = safe_float(bid[0])
                                if price > 0:
                                    bid_levels.append(price)
                        
                        # Extract ask levels
                        ask_levels = []
                        for ask in asks_data[:3]:
                            if isinstance(ask, list) and len(ask) >= 2:
                                price = safe_float(ask[0])
                                if price > 0:
                                    ask_levels.append(price)
                        
                        print(f'Bid levels: {bid_levels}')
                        print(f'Ask levels: {ask_levels}')
                        
                        if bid_levels and ask_levels:
                            best_bid = max(bid_levels)
                            best_ask = min(ask_levels)
                            print(f'Best bid: {best_bid}, Best ask: {best_ask}')
                            
                            if best_bid > 0:
                                spread_pct = ((best_ask - best_bid) / best_bid) * 100
                                print(f'Spread %: {spread_pct}')
            except Exception as e:
                print(f'Error in snapshot bias calculation: {e}')
                traceback.print_exc()
        
    except Exception as e:
        print(f'Error: {e}')
        traceback.print_exc()
    
    await api.close_session()

if __name__ == "__main__":
    asyncio.run(debug_division_by_zero())
