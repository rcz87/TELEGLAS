#!/usr/bin/env python3
"""
Debug script for BOB raw data issues
Tests the actual API responses and data extraction for BOB symbol
"""

import asyncio
import json
from services.coinglass_api import coinglass_api
from services.raw_data_service import RawDataService
from loguru import logger

async def main():
    print("=== DEBUG BOB RAW DATA ===")
    symbol = "BOB"
    
    # Initialize services
    api = coinglass_api
    service = RawDataService()
    
    print(f"\n🔍 Testing symbol: {symbol}")
    print("=" * 50)
    
    # Test 1: Direct API calls for BOB
    print("\n1️⃣ DIRECT API CALLS FOR BOB")
    print("-" * 30)
    
    try:
        async with api:
            # Test market data
            print("\n📊 Testing get_futures_coins_markets...")
            market_result = await api.get_futures_coins_markets(symbol)
            print(f"Market API Success: {market_result.get('success', False)}")
            if market_result.get('success'):
                data = market_result.get('data', [])
                print(f"Number of symbols in response: {len(data)}")
                # Find BOB in the data
                bob_data = None
                for item in data:
                    if item.get('symbol') == symbol:
                        bob_data = item
                        break
                if bob_data:
                    print(f"BOB data found:")
                    print(f"  - Current Price: {bob_data.get('current_price', 'N/A')}")
                    print(f"  - Price Change 1H: {bob_data.get('price_change_percent_1h', 'N/A')}")
                    print(f"  - Price Change 24H: {bob_data.get('price_change_percent_24h', 'N/A')}")
                    print(f"  - Open Interest USD: {bob_data.get('open_interest_usd', 'N/A')}")
                    print(f"  - Long Volume USD 24H: {bob_data.get('long_volume_usd_24h', 'N/A')}")
                    print(f"  - Short Volume USD 24H: {bob_data.get('short_volume_usd_24h', 'N/A')}")
                else:
                    print("❌ BOB not found in market data!")
                    print("Available symbols:", [item.get('symbol') for item in data[:10]])
            else:
                print(f"❌ Market API failed: {market_result}")
            
            # Test open interest
            print("\n📈 Testing get_open_interest_exchange_list...")
            oi_result = await api.get_open_interest_exchange_list(symbol)
            print(f"OI API Success: {oi_result.get('success', False)}")
            if oi_result.get('success'):
                oi_data = oi_result.get('data', [])
                print(f"OI data length: {len(oi_data)}")
                if oi_data:
                    print(f"Sample OI data: {oi_data[0] if oi_data else 'None'}")
            else:
                print(f"❌ OI API failed: {oi_result}")
            
            # Test RSI
            print("\n📊 Testing get_rsi_value for multiple timeframes...")
            from services.coinglass_api import normalize_future_symbol
            normalized_symbol = normalize_future_symbol(symbol)
            print(f"Normalized symbol for RSI: {normalized_symbol}")
            
            for tf in ['1h', '4h', '1d']:
                try:
                    rsi_value = await api.get_rsi_value(normalized_symbol, tf, "Binance")
                    print(f"RSI {tf}: {rsi_value}")
                except Exception as e:
                    print(f"RSI {tf} Error: {e}")
            
            # Test funding rate
            print("\n💰 Testing get_current_funding_rate...")
            try:
                funding_value = await api.get_current_funding_rate(symbol, "Binance")
                print(f"Current funding rate: {funding_value}")
            except Exception as e:
                print(f"Funding rate Error: {e}")
                
    except Exception as e:
        print(f"❌ Error in direct API calls: {e}")
    
    # Test 2: RawDataService comprehensive data
    print("\n\n2️⃣ RAW DATA SERVICE COMPREHENSIVE DATA")
    print("-" * 40)
    
    try:
        comprehensive_data = await service.get_comprehensive_market_data(symbol)
        print(f"Comprehensive data keys: {list(comprehensive_data.keys())}")
        
        # Extract key sections
        print(f"\n📊 PRICE BLOCK:")
        price_change = comprehensive_data.get('price_change', {})
        print(f"  - 1H Change: {price_change.get('1h', 'N/A')}")
        print(f"  - 4H Change: {price_change.get('4h', 'N/A')}")
        print(f"  - 24H Change: {price_change.get('24h', 'N/A')}")
        print(f"  - High 24H: {price_change.get('high_24h', 'N/A')}")
        print(f"  - Low 24H: {price_change.get('low_24h', 'N/A')}")
        print(f"  - High 7D: {price_change.get('high_7d', 'N/A')}")
        print(f"  - Low 7D: {price_change.get('low_7d', 'N/A')}")
        
        print(f"\n📈 OPEN INTEREST BLOCK:")
        oi = comprehensive_data.get('open_interest', {})
        print(f"  - Total OI: {oi.get('total_oi', 'N/A')}")
        print(f"  - OI 1H: {oi.get('oi_1h', 'N/A')}")
        print(f"  - OI 24H: {oi.get('oi_24h', 'N/A')}")
        per_exchange = oi.get('per_exchange', {})
        print(f"  - Binance OI: {per_exchange.get('Binance', 'N/A')}")
        print(f"  - Bybit OI: {per_exchange.get('Bybit', 'N/A')}")
        print(f"  - OKX OI: {per_exchange.get('OKX', 'N/A')}")
        
        print(f"\n📊 VOLUME BLOCK:")
        volume = comprehensive_data.get('volume', {})
        print(f"  - Futures 24H: {volume.get('futures_24h', 'N/A')}")
        print(f"  - Perp 24H: {volume.get('perp_24h', 'N/A')}")
        print(f"  - Spot 24H: {volume.get('spot_24h', 'N/A')}")
        
        print(f"\n📈 RSI BLOCK:")
        rsi_1h_4h_1d = comprehensive_data.get('rsi_1h_4h_1d', {})
        print(f"  - RSI 1H: {rsi_1h_4h_1d.get('1h', 'N/A')}")
        print(f"  - RSI 4H: {rsi_1h_4h_1d.get('4h', 'N/A')}")
        print(f"  - RSI 1D: {rsi_1h_4h_1d.get('1d', 'N/A')}")
        
        print(f"\n💰 FUNDING BLOCK:")
        funding = comprehensive_data.get('funding', {})
        print(f"  - Current Funding: {funding.get('current_funding', 'N/A')}")
        print(f"  - Next Funding: {funding.get('next_funding', 'N/A')}")
        
        print(f"\n📊 LIQUIDATIONS BLOCK:")
        liquidations = comprehensive_data.get('liquidations', {})
        print(f"  - Total 24H: {liquidations.get('total_24h', 'N/A')}")
        print(f"  - Long Liq: {liquidations.get('long_liq', 'N/A')}")
        print(f"  - Short Liq: {liquidations.get('short_liq', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error in comprehensive data: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Formatted message
    print("\n\n3️⃣ FORMATTED TELEGRAM MESSAGE")
    print("-" * 35)
    
    try:
        formatted_message = service.format_standard_raw_message_for_telegram(comprehensive_data)
        print("Formatted message preview:")
        print("=" * 50)
        print(formatted_message)
        print("=" * 50)
    except Exception as e:
        print(f"❌ Error formatting message: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
