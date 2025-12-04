#!/usr/bin/env python3
"""
Debug script to test CoinGlass API endpoints for /raw command
"""
import asyncio
import sys
from loguru import logger
from services.coinglass_api import coinglass_api
from services.raw_data_service import raw_data_service

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level: <8} | {message}")

async def test_raw_endpoints(symbol="BTC"):
    """Test all endpoints used by /raw command"""
    print(f"\n{'='*60}")
    print(f"Testing /raw endpoints for {symbol}")
    print(f"{'='*60}\n")

    async with coinglass_api:
        # 1. Test symbol resolution
        print(f"1. Testing symbol resolution...")
        resolved = await coinglass_api.resolve_symbol(symbol)
        print(f"   ✓ {symbol} -> {resolved}\n")

        if not resolved:
            print(f"   ✗ Symbol not supported!")
            return

        # 2. Test RSI endpoints
        print(f"2. Testing RSI (1h/4h/1d)...")
        try:
            rsi_1h = await coinglass_api.get_rsi_value(resolved, "1h", "Binance")
            rsi_4h = await coinglass_api.get_rsi_value(resolved, "4h", "Binance")
            rsi_1d = await coinglass_api.get_rsi_value(resolved, "1d", "Binance")
            print(f"   RSI 1H: {rsi_1h}")
            print(f"   RSI 4H: {rsi_4h}")
            print(f"   RSI 1D: {rsi_1d}\n")
        except Exception as e:
            print(f"   ✗ RSI Error: {e}\n")

        # 3. Test funding rate
        print(f"3. Testing Funding Rate...")
        try:
            funding = await coinglass_api.get_current_funding_rate(resolved, "Binance")
            print(f"   Current Funding: {funding}%\n")
        except Exception as e:
            print(f"   ✗ Funding Error: {e}\n")

        # 4. Test long/short ratio
        print(f"4. Testing Long/Short Ratio...")
        try:
            ls_data = await coinglass_api.get_global_long_short_ratio(resolved, "Binance")
            print(f"   Success: {ls_data.get('success')}")
            data = ls_data.get('data', [])
            if data:
                latest = data[-1]
                print(f"   Latest entry fields: {list(latest.keys()) if isinstance(latest, dict) else 'Not a dict'}")
                print(f"   Long/Short Ratio: {latest.get('longShortRatio') if isinstance(latest, dict) else 'N/A'}")
                print(f"   Position L/S Ratio: {latest.get('positionLongShortRatio') if isinstance(latest, dict) else 'N/A'}")
            else:
                print(f"   ✗ No data returned")
            print()
        except Exception as e:
            print(f"   ✗ Long/Short Error: {e}\n")

        # 5. Test liquidations
        print(f"5. Testing Liquidations...")
        try:
            liq_data = await coinglass_api.get_liquidation_aggregated_history(resolved)
            print(f"   Success: {liq_data.get('success')}")
            data = liq_data.get('data', [])
            if data:
                print(f"   Total entries: {len(data)}")
                latest = data[-1] if isinstance(data, list) else data
                print(f"   Latest entry fields: {list(latest.keys()) if isinstance(latest, dict) else 'Not a dict'}")
                if isinstance(latest, dict):
                    long_liq = latest.get('aggregated_long_liquidation_usd', 0)
                    short_liq = latest.get('aggregated_short_liquidation_usd', 0)
                    print(f"   Long Liq: ${long_liq:,.2f}")
                    print(f"   Short Liq: ${short_liq:,.2f}")
            else:
                print(f"   ✗ No data returned")
            print()
        except Exception as e:
            print(f"   ✗ Liquidation Error: {e}\n")

        # 6. Test taker flow
        print(f"6. Testing Taker Flow...")
        try:
            taker_data = await coinglass_api.get_taker_flow(resolved, "Binance", "h1", 100)
            print(f"   Success: {taker_data.get('success')}")
            summary = taker_data.get('summary', {})
            if summary:
                print(f"   Summary fields: {list(summary.keys())}")
                print(f"   Total Buy: ${summary.get('total_buy_volume', 0):,.0f}")
                print(f"   Total Sell: ${summary.get('total_sell_volume', 0):,.0f}")
                print(f"   Net Delta: ${summary.get('net_delta', 0):+,.0f}")
            else:
                print(f"   ✗ No summary data")
            print()
        except Exception as e:
            print(f"   ✗ Taker Flow Error: {e}\n")

        # 7. Test comprehensive data (full /raw)
        print(f"7. Testing Full Comprehensive Data...")
        try:
            full_data = await raw_data_service.get_comprehensive_market_data(symbol)
            print(f"   Symbol: {full_data.get('symbol')}")
            print(f"   Has Error: {'error' in full_data}")
            if 'error' in full_data:
                print(f"   Error: {full_data['error']}")
            else:
                rsi_data = full_data.get('rsi_1h_4h_1d', {})
                print(f"   RSI 1H: {rsi_data.get('1h')}")
                print(f"   RSI 4H: {rsi_data.get('4h')}")
                print(f"   RSI 1D: {rsi_data.get('1d')}")

                funding_data = full_data.get('funding', {})
                print(f"   Current Funding: {funding_data.get('current_funding')}")

                ls_data = full_data.get('long_short_ratio', {})
                print(f"   Account Ratio: {ls_data.get('account_ratio_global')}")
                print(f"   Position Ratio: {ls_data.get('position_ratio_global')}")
            print()
        except Exception as e:
            print(f"   ✗ Full Data Error: {e}\n")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTC"
    asyncio.run(test_raw_endpoints(symbol))
