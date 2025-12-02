import asyncio
from services.coinglass_api import coinglass_api

async def debug_api_response():
    try:
        async with coinglass_api:
            # Test the markets endpoint to see actual response structure
            result = await coinglass_api.get_futures_coins_markets('BTC')
            print('Markets API response:')
            print(f'Success: {result.get("success")}')
            if result.get('success'):
                data = result.get('data', [])
                print(f'Data length: {len(data)}')
                if data:
                    print('First item structure:')
                    first_item = data[0]
                    for key, value in first_item.items():
                        print(f'  {key}: {value}')
                    
                    # Find BTC specifically
                    for item in data:
                        if isinstance(item, dict) and str(item.get("symbol", "")).upper() == 'BTC':
                            print('\nBTC item found:')
                            for key, value in item.items():
                                print(f'  {key}: {value}')
                            break
                else:
                    print('No data found')
            else:
                print(f'Error: {result.get("error")}')
                
    except Exception as e:
        print(f'Exception: {e}')

if __name__ == "__main__":
    asyncio.run(debug_api_response())
