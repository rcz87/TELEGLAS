import asyncio
from services.coinglass_api import CoinGlassAPI
from config import settings

async def main():
    api = CoinGlassAPI()
    
    symbols = ["BTC", "XRP"]

    for sym in symbols:
        print("=" * 40)
        print(f"TEST SYMBOL: {sym}")
        print("- RSI MULTI-TF ----------")
        try:
            # Test RSI for multiple timeframes
            rsi_1h = await api.get_rsi_value(sym, "1h")
            rsi_4h = await api.get_rsi_value(sym, "4h") 
            rsi_1d = await api.get_rsi_value(sym, "1d")
            
            rsi_result = {
                "1h": rsi_1h,
                "4h": rsi_4h, 
                "1d": rsi_1d
            }
            print("RSI RESULT:", rsi_result)
        except Exception as e:
            print("RSI ERROR:", e)

        print("- LONG/SHORT RATIO ------")
        try:
            ls = await api.get_global_long_short_ratio(sym)
            print("LONG/SHORT RESULT:", ls)
        except Exception as e:
            print("LONG/SHORT ERROR:", e)

        print("- ORDERBOOK SNAPSHOT ----")
        try:
            # Test orderbook history
            base_symbol, futures_pair = api.resolve_orderbook_symbols(sym)
            ob = await api.get_orderbook_history(base_symbol, futures_pair, exchange="Binance")
            print("ORDERBOOK RESULT:", ob)
        except Exception as e:
            print("ORDERBOOK ERROR:", e)

if __name__ == "__main__":
    asyncio.run(main())
