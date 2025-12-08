#!/usr/bin/env python3
"""
Debug the structure of CoinGlass API response to understand the data format
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.coinglass_api import CoinGlassAPI
from loguru import logger


async def debug_coinglass_structure():
    """Debug CoinGlass API response structure"""
    
    coinglass_api = CoinGlassAPI()
    
    logger.info("=== DEBUGGING COINGLASS API STRUCTURE ===")
    
    try:
        # Get supported futures coins
        logger.info("1. Getting supported futures coins...")
        supported_coins = await coinglass_api.get_supported_futures_coins()
        
        logger.info(f"Type of supported_coins: {type(supported_coins)}")
        
        if isinstance(supported_coins, list):
            logger.info(f"Length of list: {len(supported_coins)}")
            if len(supported_coins) > 0:
                logger.info(f"First 5 items: {supported_coins[:5]}")
                logger.info(f"Type of first item: {type(supported_coins[0])}")
        elif isinstance(supported_coins, dict):
            logger.info(f"Dict keys: {list(supported_coins.keys())[:10]}")
        else:
            logger.info(f"Unexpected type: {type(supported_coins)}")
            logger.info(f"Content preview: {str(supported_coins)[:200]}")
        
        # Test major coins directly
        logger.info("\n2. Testing major coins directly...")
        test_coins = ["BTC", "ETH", "BNB"]
        
        for coin in test_coins:
            logger.info(f"Testing {coin}...")
            try:
                resolved = await coinglass_api.resolve_symbol(coin)
                logger.info(f"  {coin} resolves to: {resolved}")
                
                # Try to get some data
                try:
                    market_data = await coinglass_api.get_market_data()
                    logger.info(f"  Market data type: {type(market_data)}")
                    
                    if isinstance(market_data, list):
                        logger.info(f"  Market data length: {len(market_data)}")
                        if len(market_data) > 0:
                            first_item = market_data[0]
                            logger.info(f"  First market item keys: {list(first_item.keys()) if isinstance(first_item, dict) else type(first_item)}")
                    
                except Exception as e:
                    logger.error(f"  Market data error: {e}")
                    
            except Exception as e:
                logger.error(f"  {coin} resolution error: {e}")
        
        # Try to get raw response
        logger.info("\n3. Getting raw API response...")
        try:
            # Make a direct API call to see the structure
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = "https://www.coinglass.com/api/futures/v1/coins"
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Raw API response type: {type(data)}")
                        
                        if isinstance(data, dict):
                            logger.info(f"Response keys: {list(data.keys())}")
                            
                            # Check if there's a data field
                            if 'data' in data:
                                logger.info(f"Data field type: {type(data['data'])}")
                                if isinstance(data['data'], list):
                                    logger.info(f"Data length: {len(data['data'])}")
                                    if len(data['data']) > 0:
                                        logger.info(f"First data item: {data['data'][0]}")
                        
                        elif isinstance(data, list):
                            logger.info(f"Response is list with {len(data)} items")
                            if len(data) > 0:
                                logger.info(f"First item: {data[0]}")
                        
                    else:
                        logger.error(f"API call failed with status: {response.status}")
                        
        except Exception as e:
            logger.error(f"Raw API call error: {e}")
            
    except Exception as e:
        logger.error(f"Overall error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(debug_coinglass_structure())
