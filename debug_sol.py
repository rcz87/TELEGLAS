import asyncio
from services.coinglass_api import coinglass_api

async def debug_sol():
    api = coinglass_api
    symbol = "SOL"
    
    print(f"=== DEBUG SOL ENDPOINTS ===")
    
    async with api:
        # Test symbol resolution
        resolved = await api.resolve_symbol(symbol)
        print(f"Symbol resolution: {symbol} -> {resolved}")
        
        if not resolved:
            print("❌ Symbol tidak didukung")
            return
            
        # Test working endpoints dengan endpoint yang benar
        endpoints_to_test = [
            ("Futures Coins Markets", lambda: api.get_futures_coins_markets(resolved)),
            ("Open Interest Exchange List", lambda: api.get_open_interest_exchange_list(resolved)),
            ("Funding Rate Exchange List", lambda: api.get_funding_rate_exchange_list(resolved)),
            ("Liquidation Exchange List", lambda: api.get_liquidation_exchange_list(resolved)),
        ]
        
        for name, endpoint_func in endpoints_to_test:
            try:
                print(f"\n--- Testing {name} ---")
                result = await endpoint_func()
                print(f"Success: {result.get('success', False)}")
                if result.get('success'):
                    data = result.get('data', [])
                    print(f"Data items: {len(data)}")
                    if data and len(data) > 0:
                        print(f"Sample: {data[0]}")
                else:
                    print(f"Error: {result}")
            except Exception as e:
                print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(debug_sol())
