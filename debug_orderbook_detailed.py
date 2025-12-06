import sys
import asyncio
from typing import Dict, List, Any, Optional
from services.coinglass_api import CoinGlassAPI, safe_float, safe_int
from utils.formatters import build_raw_orderbook_text


def normalize_orderbook_data(raw_data: List) -> Dict[str, Any]:
    """
    Normalize raw orderbook data from CoinGlass API to structured format
    
    Args:
        raw_data: Raw data from API in format [timestamp, [bids], [asks]]
        
    Returns:
        Structured dict with clear fields
    """
    if not raw_data or not isinstance(raw_data, list) or len(raw_data) < 3:
        return {
            "success": False,
            "error": "Invalid data format",
            "timestamp": 0,
            "bids": [],
            "asks": []
        }
    
    try:
        timestamp = raw_data[0]
        bids_raw = raw_data[1] if len(raw_data) > 1 else []
        asks_raw = raw_data[2] if len(raw_data) > 2 else []
        
        # Convert bids to structured format
        bids = []
        if isinstance(bids_raw, list):
            for bid in bids_raw:
                if isinstance(bid, list) and len(bid) >= 2:
                    bids.append({
                        "price": safe_float(bid[0]),
                        "size": safe_float(bid[1])
                    })
        
        # Convert asks to structured format
        asks = []
        if isinstance(asks_raw, list):
            for ask in asks_raw:
                if isinstance(ask, list) and len(ask) >= 2:
                    asks.append({
                        "price": safe_float(ask[0]),
                        "size": safe_float(ask[1])
                    })
        
        return {
            "success": True,
            "timestamp": timestamp,
            "bids": bids,
            "asks": asks,
            "exchange": "Binance"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": 0,
            "bids": [],
            "asks": []
        }


def calculate_orderbook_summary(bids: List[Dict], asks: List[Dict]) -> Dict[str, Any]:
    """
    Calculate orderbook summary metrics
    
    Args:
        bids: List of bid orders with price and size
        asks: List of ask orders with price and size
        
    Returns:
        Summary dict with key metrics
    """
    if not bids or not asks:
        return {
            "best_bid": None,
            "best_ask": None,
            "mid_price": None,
            "spread": None,
            "spread_pct": None,
            "total_bid_levels": 0,
            "total_ask_levels": 0
        }
    
    # Find best bid (highest price) and best ask (lowest price)
    best_bid = max(bids, key=lambda x: x["price"])
    best_ask = min(asks, key=lambda x: x["price"])
    
    # Calculate mid price and spread
    mid_price = (best_bid["price"] + best_ask["price"]) / 2
    spread = best_ask["price"] - best_bid["price"]
    spread_pct = (spread / best_bid["price"]) * 100 if best_bid["price"] > 0 else 0
    
    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid_price": mid_price,
        "spread": spread,
        "spread_pct": spread_pct,
        "total_bid_levels": len(bids),
        "total_ask_levels": len(asks)
    }


def detect_liquidity_walls(orders: List[Dict], wall_multiplier: float = 5.0) -> List[Dict]:
    """
    Detect liquidity walls (unusually large orders)
    
    Args:
        orders: List of orders with price and size
        wall_multiplier: Multiplier for median size to consider as wall
        
    Returns:
        List of walls sorted by size (largest first)
    """
    if not orders:
        return []
    
    # Calculate median size
    sizes = [order["size"] for order in orders if order["size"] > 0]
    if not sizes:
        return []
    
    sizes.sort()
    median_size = sizes[len(sizes) // 2]
    
    # Find walls (orders much larger than median)
    walls = []
    for order in orders:
        if order["size"] >= median_size * wall_multiplier:
            walls.append(order)
    
    # Sort by size (largest first)
    walls.sort(key=lambda x: x["size"], reverse=True)
    return walls[:10]  # Return top 10 walls


def calculate_liquidity_distribution(bids: List[Dict], asks: List[Dict], mid_price: float) -> Dict[str, Any]:
    """
    Calculate liquidity distribution in price zones around mid price
    
    Args:
        bids: List of bid orders
        asks: List of ask orders  
        mid_price: Mid price for zone calculation
        
    Returns:
        Distribution data by zones
    """
    if not bids or not asks or mid_price <= 0:
        return {
            "bids": {"zone_0_0.5": 0, "zone_0.5_1": 0, "zone_1_plus": 0},
            "asks": {"zone_0_0.5": 0, "zone_0.5_1": 0, "zone_1_plus": 0}
        }
    
    def calculate_zone_volume(orders: List[Dict], is_bid: bool) -> Dict[str, float]:
        zones = {"zone_0_0.5": 0, "zone_0.5_1": 0, "zone_1_plus": 0}
        
        for order in orders:
            if order["price"] <= 0 or order["size"] <= 0:
                continue
                
            # Calculate distance from mid price
            if is_bid:
                distance_pct = ((mid_price - order["price"]) / mid_price) * 100
            else:
                distance_pct = ((order["price"] - mid_price) / mid_price) * 100
            
            # Assign to zone
            if distance_pct <= 0.5:
                zones["zone_0_0.5"] += order["size"]
            elif distance_pct <= 1.0:
                zones["zone_0.5_1"] += order["size"]
            else:
                zones["zone_1_plus"] += order["size"]
        
        return zones
    
    return {
        "bids": calculate_zone_volume(bids, True),
        "asks": calculate_zone_volume(asks, False)
    }


def print_orderbook_summary(symbol: str, data: Dict[str, Any]):
    """
    Print human-readable orderbook summary
    
    Args:
        symbol: Trading symbol
        data: Normalized orderbook data
    """
    if not data.get("success"):
        print(f"❌ Error: {data.get('error', 'Unknown error')}")
        return
    
    bids = data.get("bids", [])
    asks = data.get("asks", [])
    timestamp = data.get("timestamp", 0)
    exchange = data.get("exchange", "Unknown")
    
    # Calculate summary
    summary = calculate_orderbook_summary(bids, asks)
    
    # Convert timestamp to readable format
    from datetime import datetime
    if timestamp > 0:
        dt = datetime.fromtimestamp(timestamp)
        time_str = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    else:
        time_str = "N/A"
    
    print(f"\n=== ORDERBOOK SUMMARY ({symbol}, {exchange}) ===")
    print(f"Timestamp     : {time_str}")
    
    if summary["best_bid"] and summary["best_ask"]:
        print(f"Best Bid      : {summary['best_bid']['price']:.4f} (size {summary['best_bid']['size']:.3f})")
        print(f"Best Ask      : {summary['best_ask']['price']:.4f} (size {summary['best_ask']['size']:.3f})")
        print(f"Mid Price     : {summary['mid_price']:.4f}")
        print(f"Spread        : {summary['spread']:.4f} ({summary['spread_pct']:.2f}%)")
    
    print(f"Total Levels   : {summary['total_bid_levels']} bids / {summary['total_ask_levels']} asks")
    
    # Detect liquidity walls
    bid_walls = detect_liquidity_walls(bids)
    ask_walls = detect_liquidity_walls(asks)
    
    if bid_walls:
        print(f"\nTop {len(bid_walls)} Bid Walls (by size):")
        for i, wall in enumerate(bid_walls[:5], 1):
            print(f"- {wall['price']:.4f} : {wall['size']:.3f}")
    
    if ask_walls:
        print(f"\nTop {len(ask_walls)} Ask Walls (by size):")
        for i, wall in enumerate(ask_walls[:5], 1):
            print(f"- {wall['price']:.4f} : {wall['size']:.3f}")
    
    # Liquidity distribution
    if summary["mid_price"]:
        distribution = calculate_liquidity_distribution(bids, asks, summary["mid_price"])
        
        print(f"\nLiquidity Distribution (distance from mid):")
        print("Bids:")
        print(f"- 0–0.5% : {distribution['bids']['zone_0_0.5']:.3f}")
        print(f"- 0.5–1% : {distribution['bids']['zone_0.5_1']:.3f}")
        print(f"- >1%    : {distribution['bids']['zone_1_plus']:.3f}")
        
        print("Asks:")
        print(f"- 0–0.5% : {distribution['asks']['zone_0_0.5']:.3f}")
        print(f"- 0.5–1% : {distribution['asks']['zone_0.5_1']:.3f}")
        print(f"- >1%    : {distribution['asks']['zone_1_plus']:.3f}")
    
    # Show sample levels
    if bids:
        print(f"\nSample 5 closest Bid Levels:")
        print("Price     Size")
        for bid in bids[:5]:
            print(f"{bid['price']:.4f}  {bid['size']:.3f}")
    
    if asks:
        print(f"\nSample 5 closest Ask Levels:")
        print("Price     Size")
        for ask in asks[:5]:
            print(f"{ask['price']:.4f}  {ask['size']:.3f}")


async def main():
    # Parse command line arguments
    if len(sys.argv) != 2:
        print("Usage: python debug_orderbook_detailed.py [SYMBOL]")
        print("Example: python debug_orderbook_detailed.py BTC")
        print("Example: python debug_orderbook_detailed.py XRP")
        return
    
    symbol = sys.argv[1].upper().strip()
    if not symbol:
        print("Error: Symbol cannot be empty")
        return
    
    api = CoinGlassAPI()
    
    # Resolve symbols properly
    base_symbol, futures_pair = api.resolve_orderbook_symbols(symbol)
    
    print(f"Testing orderbook for {symbol}")
    print(f"Base symbol: {base_symbol}")
    print(f"Futures pair: {futures_pair}")
    
    try:
        async with api:
            # Get orderbook history snapshot
            result = await api.get_orderbook_history_snapshot(base_symbol, futures_pair)
            
            if result and result.get("success"):
                # Get's raw snapshot data
                raw_data = result.get("data", [])
                if raw_data and isinstance(raw_data, list) and len(raw_data) > 0:
                    # Normalize raw data
                    normalized_data = normalize_orderbook_data(raw_data[0])
                    
                    if normalized_data.get("success"):
                        # Print human-readable summary
                        print_orderbook_summary(futures_pair, normalized_data)
                    else:
                        print(f"❌ Error normalizing data: {normalized_data.get('error')}")
                else:
                    print(f"❌ No valid orderbook data found")
            else:
                print(f"❌ Error fetching orderbook: {result.get('error', 'Unknown error') if result else 'No data returned'}")
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
