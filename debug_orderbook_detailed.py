import asyncio
from services.coinglass_api import CoinGlassAPI

async def main():
    api = CoinGlassAPI()
    
    symbol = "BTC"
    base_symbol, futures_pair = api.resolve_orderbook_symbols(symbol)
    
    print(f"Testing orderbook for {symbol}")
    print(f"Base symbol: {base_symbol}")
    print(f"Futures pair: {futures_pair}")
    
    try:
        # Test the raw endpoint to see what we get
        async with api:
            result = await api._make_request("/api/futures/orderbook/history", {
                "exchange": "Binance",
                "symbol": futures_pair,
                "interval": "1h",
                "limit": 1
            })
            
            print("RAW API RESULT:")
            print(f"Success: {result.get('success')}")
            print(f"Data length: {len(result.get('data', []))}")
            print(f"First data item: {result.get('data', [{}])[0] if result.get('data') else 'None'}")
            print(f"Full result: {result}")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
