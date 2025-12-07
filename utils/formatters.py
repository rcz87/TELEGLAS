"""
Formatters for CryptoSat Bot
Contains various formatting functions for different data types and outputs.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
from services.coinglass_api import safe_float, safe_int, safe_get, safe_list_get


def format_notional_compact(value: float) -> str:
    """
    Helper function to format notional values in compact form.
    
    Args:
        value: Amount in USD
        
    Returns:
        Formatted string (e.g., "$1.9M", "$250.3K")
    """
    if value >= 1_000_000:
        return f"${value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value/1_000:.0f}K"
    else:
        return f"${value:.0f}"


def format_price(price: float) -> str:
    """
    Helper function to format price based on value.
    
    Args:
        price: Price value
        
    Returns:
        Formatted price string
    """
    if price >= 1:
        return f"{price:.2f}"
    else:
        return f"{price:.6f}"


def format_whale_radar_message(data: Dict[str, Any]) -> str:
    """
    Format whale radar data with clean, Telegram-friendly output.
    
    Args:
        data: Whale radar data dictionary containing:
            - active_symbols: List of active whale symbols with stats
            - recent_trades: List of recent whale trades
            - positions: List of whale positions
    
    Returns:
        Formatted string for Telegram output
    """
    try:
        lines = []
        
        # Header
        lines.append("🐋 Whale Radar – Hyperliquid (Multi Coin)")
        lines.append("")
        
        # Extract data
        active_symbols = data.get("active_symbols", [])
        recent_trades = data.get("recent_trades", [])
        positions = data.get("positions", [])
        
        # Section 1: Active Whale Symbols
        lines.append("📊 Active Whale Symbols")
        if active_symbols:
            for symbol_data in active_symbols[:8]:  # Top 8 active symbols
                symbol = symbol_data.get("symbol", "UNKNOWN")
                total_trades = symbol_data.get("total_trades", 0)
                buy_count = symbol_data.get("buy_count", 0)
                sell_count = symbol_data.get("sell_count", 0)
                total_notional = symbol_data.get("total_notional_usd", 0)
                
                # Calculate total notional from buy/sell amounts
                total_notional = symbol_data.get("buy_usd", 0) + symbol_data.get("sell_usd", 0)
                notional_str = format_notional_compact(total_notional)
                
                lines.append(f"• {symbol} – {total_trades} trades | {buy_count}B / {sell_count}S | Notional ≈ {notional_str}")
        else:
            lines.append("• No significant whale activity detected")
        lines.append("")
        
        # Section 2: Sample Recent Whale Trades
        lines.append("🕒 Sample Recent Whale Trades")
        if recent_trades:
            for i, trade in enumerate(recent_trades[:5], 1):  # Max 5 trades
                symbol = trade.get("symbol", "UNKNOWN")
                side = trade.get("side", "UNKNOWN").upper()
                amount_usd = trade.get("amount_usd", 0)
                price = trade.get("price", 0)
                
                # Format compact notional and price
                notional_str = format_notional_compact(amount_usd)
                price_str = format_price(price)
                
                lines.append(f"{i}) [{side}] {symbol} – {notional_str} @ ${price_str}")
        else:
            lines.append("• No recent whale trades available")
        lines.append("")
        
        # Section 3: Top Whale Positions
        lines.append("📌 Top Whale Positions")
        if positions:
            for position in positions[:3]:  # Max 3 positions
                symbol = position.get("symbol", "UNKNOWN")
                side = position.get("side", "UNKNOWN").title()
                position_value = position.get("position_value_usd", 0)
                entry_price = position.get("entry_price", 0)
                
                # Format compact notional and price
                value_str = format_notional_compact(position_value)
                price_str = format_price(entry_price)
                
                lines.append(f"• {symbol} – {side} {value_str} @ ${price_str}")
        else:
            lines.append("• Position data sementara belum tersedia.")
        lines.append("")
        
        # Section 4: TL;DR
        lines.append("TL;DR:")
        
        # Analyze whale activity patterns
        btc_eth_data = [s for s in active_symbols if s.get("symbol") in ["BTC", "ETH"]]
        altcoin_data = [s for s in active_symbols if s.get("symbol") not in ["BTC", "ETH"]]
        
        if btc_eth_data:
            # Check BTC/ETH buy/sell pressure
            btc_eth_buy_total = sum(s.get("buy_notional_usd", 0) for s in btc_eth_data)
            btc_eth_sell_total = sum(s.get("sell_notional_usd", 0) for s in btc_eth_data)
            
            if btc_eth_buy_total > btc_eth_sell_total * 1.2:
                lines.append("• BTC/ETH lebih banyak tekanan beli")
            elif btc_eth_sell_total > btc_eth_buy_total * 1.2:
                lines.append("• BTC/ETH lebih banyak tekanan jual")
            else:
                lines.append("• BTC/ETH aktivitas seimbang")
        
        if altcoin_data:
            # Check altcoin sell pressure
            altcoin_buy_total = sum(s.get("buy_notional_usd", 0) for s in altcoin_data)
            altcoin_sell_total = sum(s.get("sell_notional_usd", 0) for s in altcoin_data)
            
            if altcoin_sell_total > altcoin_buy_total * 1.3:
                # Get top 3 altcoins with sell pressure
                top_sell_altcoins = sorted(altcoin_data, 
                                        key=lambda x: x.get("sell_notional_usd", 0), 
                                        reverse=True)[:3]
                altcoin_names = [s.get("symbol", "UNKNOWN") for s in top_sell_altcoins]
                lines.append(f"• Altcoin tertentu ({', '.join(altcoin_names)}) didominasi sell (profit taking / distribusi)")
            else:
                lines.append("• Altcoin aktivitas campuran")
        
        if not btc_eth_data and not altcoin_data:
            lines.append("• Aktivitas whale minimal saat ini")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"[FORMATTER] Error formatting whale radar message: {e}")
        return "❌ Error formatting whale radar data"


def format_whale_radar_enhanced(enhanced_data: Dict[str, Any], sample_trades: List[Dict[str, Any]], all_positions: List[Dict[str, Any]]) -> str:
    """
    Legacy function - use format_whale_radar_message instead.
    Kept for backward compatibility.
    """
    # Convert old format to new format
    data = {
        "active_symbols": enhanced_data.get("active_whale_symbols", []),
        "recent_trades": sample_trades,
        "positions": all_positions
    }
    return format_whale_radar_message(data)


def format_usd_millions(amount_usd: float) -> str:
    """
    Format USD amount in millions with proper suffix.
    
    Args:
        amount_usd: Amount in USD
        
    Returns:
        Formatted string (e.g., "$24.5M", "$0.70M")
    """
    if amount_usd >= 1_000_000:
        return f"${amount_usd/1_000_000:.1f}M"
    elif amount_usd >= 1000:
        return f"${amount_usd/1000:.0f}K"
    else:
        return f"${amount_usd:.0f}"


def build_raw_orderbook_text(
    symbol: str,
    history_data: Any,
    binance_depth_data: Any,
    aggregated_depth_data: Any,
    exchange: str = "Binance",
    ob_interval: str = "1h",
    depth_range: str = "1%"
) -> str:
    """
    Build formatted RAW ORDERBOOK report from orderbook data.
    Enhanced with proper support detection and actionable analysis.
    
    Args:
        symbol: Trading symbol (e.g., "BTCUSDT")
        history_data: Data from orderbook history endpoint
        binance_depth_data: Data from Binance ask-bids history endpoint (enhanced format)
        aggregated_depth_data: Data from aggregated ask-bids history endpoint (enhanced format)
        exchange: Exchange name (default: "Binance")
        ob_interval: Orderbook interval (default: "1h")
        depth_range: Depth range (default: "1%")
        
    Returns:
        Formatted text safe for Telegram (no MarkdownV2 characters)
    """
    try:
        lines = []
        
        # Header
        lines.append(f"[RAW ORDERBOOK - {symbol}]")
        lines.append("")
        
        # Info Umum section
        lines.append("Info Umum")
        lines.append(f"Exchange       : {exchange}")
        lines.append(f"Symbol         : {symbol}")
        lines.append(f"Interval OB    : {ob_interval} (snapshot level)")
        lines.append(f"Depth Range    : {depth_range}")
        lines.append("")
        
        # Section 1: Snapshot Orderbook (Level Price - History 1H)
        lines.append("1) Snapshot Orderbook (Level Price - History 1H)")
        lines.append("")
        
        # Extract timestamp from history data
        timestamp = "N/A"
        if history_data:
            # Handle enhanced format (dict with time, bids, asks)
            if isinstance(history_data, dict) and "time" in history_data:
                ts_ms = safe_int(history_data.get("time"))
                if ts_ms > 0:
                    dt = datetime.fromtimestamp(ts_ms / 1000)
                    timestamp = dt.strftime('%Y-%m-%d %H:%M UTC')
            # Handle list format
            elif isinstance(history_data, list) and len(history_data) > 0:
                latest_data = history_data[0]
                
                # Handle actual API response structure: [timestamp, [bids], [asks]]
                if isinstance(latest_data, list) and len(latest_data) >= 1:
                    ts_unix = safe_int(latest_data[0])  # Unix timestamp (not milliseconds)
                    if ts_unix > 0:
                        dt = datetime.fromtimestamp(ts_unix)
                        timestamp = dt.strftime('%Y-%m-%d %H:%M UTC')
                
                # Fallback to dict-based structure
                elif isinstance(latest_data, dict):
                    ts_ms = safe_int(latest_data.get("createTime"))
                    if ts_ms > 0:
                        dt = datetime.fromtimestamp(ts_ms / 1000)
                        timestamp = dt.strftime('%Y-%m-%d %H:%M UTC')
        
        lines.append(f"Timestamp      : {timestamp}")
        lines.append("")
        
        # Extract top bids and asks from history data
        top_bids = []
        top_asks = []
        
        if history_data:
            # Handle format from raw_data_service.build_raw_orderbook_data
            if isinstance(history_data, dict):
                # Check for top_bids and top_asks arrays
                bids_data = history_data.get("top_bids", [])
                asks_data = history_data.get("top_asks", [])
                
                # Extract bid data from array format: [[price, qty], [price, qty], ...]
                if isinstance(bids_data, list) and bids_data:
                    for i, bid in enumerate(bids_data[:5]):  # Top 5 bids
                        if isinstance(bid, list) and len(bid) >= 2:
                            price = safe_float(bid[0])
                            qty = safe_float(bid[1])
                            if price > 0 and qty > 0:
                                top_bids.append(f"• {price:,.6f}   | {qty:.3f}")
                
                # Extract ask data from array format: [[price, qty], [price, qty], ...]
                if isinstance(asks_data, list) and asks_data:
                    for i, ask in enumerate(asks_data[:5]):  # Top 5 asks
                        if isinstance(ask, list) and len(ask) >= 2:
                            price = safe_float(ask[0])
                            qty = safe_float(ask[1])
                            if price > 0 and qty > 0:
                                top_asks.append(f"• {price:,.6f}   | {qty:.3f}")
            
            # Handle enhanced format (dict with time, bids, asks)
            elif isinstance(history_data, dict) and "bids" in history_data and "asks" in history_data:
                bids_data = history_data.get("bids", [])
                asks_data = history_data.get("asks", [])
                
                # Extract bid data from array format: [[price, qty], [price, qty], ...]
                if isinstance(bids_data, list) and bids_data:
                    for i, bid in enumerate(bids_data[:5]):  # Top 5 bids
                        if isinstance(bid, list) and len(bid) >= 2:
                            price = safe_float(bid[0])
                            qty = safe_float(bid[1])
                            if price > 0 and qty > 0:
                                top_bids.append(f"• {price:,.0f}   | {qty:.3f} BTC")
                
                # Extract ask data from array format: [[price, qty], [price, qty], ...]
                if isinstance(asks_data, list) and asks_data:
                    for i, ask in enumerate(asks_data[:5]):  # Top 5 asks
                        if isinstance(ask, list) and len(ask) >= 2:
                            price = safe_float(ask[0])
                            qty = safe_float(ask[1])
                            if price > 0 and qty > 0:
                                top_asks.append(f"• {price:,.0f}   | {qty:.3f} BTC")
            
            # Handle list format
            elif isinstance(history_data, list) and len(history_data) > 0:
                latest_data = history_data[0]
                
                # Handle actual API response structure: [timestamp, [bids], [asks]]
                if isinstance(latest_data, list) and len(latest_data) >= 3:
                    timestamp = latest_data[0]  # Unix timestamp
                    bids_data = latest_data[1] if len(latest_data) > 1 else []
                    asks_data = latest_data[2] if len(latest_data) > 2 else []
                    
                    # Extract bid data from array format: [[price, qty], [price, qty], ...]
                    if isinstance(bids_data, list) and bids_data:
                        for i, bid in enumerate(bids_data[:5]):  # Top 5 bids
                            if isinstance(bid, list) and len(bid) >= 2:
                                price = safe_float(bid[0])
                                qty = safe_float(bid[1])
                                if price > 0 and qty > 0:
                                    top_bids.append(f"• {price:,.0f}   | {qty:.3f} BTC")
                    
                    # Extract ask data from array format: [[price, qty], [price, qty], ...]
                    if isinstance(asks_data, list) and asks_data:
                        for i, ask in enumerate(asks_data[:5]):  # Top 5 asks
                            if isinstance(ask, list) and len(ask) >= 2:
                                price = safe_float(ask[0])
                                qty = safe_float(ask[1])
                                if price > 0 and qty > 0:
                                    top_asks.append(f"• {price:,.0f}   | {qty:.3f} BTC")
                
                # Fallback to original dict-based structure (for compatibility)
                elif isinstance(latest_data, dict):
                    # Extract bid data
                    bid_list = safe_get(latest_data, "bidList", [])
                    if isinstance(bid_list, list) and bid_list:
                        for i, bid in enumerate(bid_list[:5]):  # Top 5 bids
                            if isinstance(bid, dict):
                                price = safe_float(bid.get("price"))
                                qty = safe_float(bid.get("size", bid.get("amount")))
                                if price > 0 and qty > 0:
                                    top_bids.append(f"• {price:,.0f}   | {qty:.3f} BTC")
                    
                    # Extract ask data
                    ask_list = safe_get(latest_data, "askList", [])
                    if isinstance(ask_list, list) and ask_list:
                        for i, ask in enumerate(ask_list[:5]):  # Top 5 asks
                            if isinstance(ask, dict):
                                price = safe_float(ask.get("price"))
                                qty = safe_float(ask.get("size", ask.get("amount")))
                                if price > 0 and qty > 0:
                                    top_asks.append(f"• {price:,.0f}   | {qty:.3f} BTC")
        
        # Display top bids
        lines.append("Top Bids (Pembeli)")
        if top_bids:
            for bid in top_bids:
                lines.append(bid)
        else:
            lines.append("• No bid data available")
        
        lines.append("")
        
        # Display top asks
        lines.append("Top Asks (Penjual)")
        if top_asks:
            for ask in top_asks:
                lines.append(ask)
        else:
            lines.append("• No ask data available")
        
        lines.append("")
        lines.append("--------------------------------------------------")
        lines.append("")
        
        # Section 2: Binance Orderbook Depth (Bids vs Asks) - 1D
        lines.append("2) Binance Orderbook Depth (Bids vs Asks) - 1D")
        lines.append("")
        
        # Process Binance depth data - STANDARD LIST FORMAT from CoinGlass API
        if binance_depth_data:
            # Handle format from raw_data_service.build_raw_orderbook_data
            if isinstance(binance_depth_data, dict) and "bids_usd" in binance_depth_data:
                bids_usd = safe_float(binance_depth_data.get("bids_usd", 0))
                asks_usd = safe_float(binance_depth_data.get("asks_usd", 0))
                bids_qty = safe_float(binance_depth_data.get("bids_qty", 0))
                asks_qty = safe_float(binance_depth_data.get("asks_qty", 0))
                bias_label = binance_depth_data.get("bias_label", "N/A")
                
                if bids_usd > 0 or asks_usd > 0:
                    # Calculate pressure
                    if asks_usd > 0:
                        pressure_pct = ((bids_usd - asks_usd) / asks_usd) * 100
                        if pressure_pct > 0.5:
                            pressure_text = f"🟩 Long Dominant (+{pressure_pct:.1f}%)"
                        elif pressure_pct < -0.5:
                            pressure_text = f"🟥 Short Dominant ({pressure_pct:.1f}%)"
                        else:
                            pressure_text = "Neutral"
                    else:
                        pressure_text = "Neutral"
                    
                    # Format USD values
                    def format_usd(value):
                        if value >= 1e6:
                            return f"${value/1e6:,.2f}M"
                        elif value >= 1e3:
                            return f"${value/1e3:,.0f}K"
                        else:
                            return f"${value:,.2f}"
                    
                    lines.append(f"• Bids (Long) : {format_usd(bids_usd)}  | {bids_qty:.3f}")
                    lines.append(f"• Asks (Short): {format_usd(asks_usd)}  | {asks_qty:.3f}")
                    lines.append(f"• Pressure    : {pressure_text}")
                    lines.append("")
                else:
                    lines.append("• No Binance depth data available")
            # Handle enhanced format with support detection
            elif isinstance(binance_depth_data, dict) and "supported" in binance_depth_data:
                if not binance_depth_data.get("supported"):
                    lines.append(f"• {binance_depth_data.get('message', 'Binance depth data not supported for this symbol')}")
                else:
                    # Enhanced format: extract data from depth_data
                    depth_data = binance_depth_data.get("depth_data", {})
                    if depth_data:
                        bids_usd = safe_float(depth_data.get("bids_usd", 0))
                        asks_usd = safe_float(depth_data.get("asks_usd", 0))
                        bids_quantity = safe_float(depth_data.get("bids_quantity", 0))
                        asks_quantity = safe_float(depth_data.get("asks_quantity", 0))
                        
                        # Always show enhanced format data when available
                        if True:  # Always show enhanced format data when available
                            # Calculate pressure
                            if asks_usd > 0:
                                pressure_pct = ((bids_usd - asks_usd) / asks_usd) * 100
                                if pressure_pct > 0.5:
                                    pressure_text = f"🟩 Long Dominant (+{pressure_pct:.1f}%)"
                                elif pressure_pct < -0.5:
                                    pressure_text = f"🟥 Short Dominant ({pressure_pct:.1f}%)"
                                else:
                                    pressure_text = "Neutral"
                            else:
                                pressure_text = "Neutral"
                            
                            # Format USD values
                            def format_usd(value):
                                if value >= 1e6:
                                    return f"${value/1e6:,.2f}M"
                                elif value >= 1e3:
                                    return f"${value/1e3:,.0f}K"
                                else:
                                    return f"${value:,.2f}"
                            
                            lines.append(f"• Bids (Long) : {format_usd(bids_usd)}  | {bids_quantity:.3f} BTC")
                            lines.append(f"• Asks (Short): {format_usd(asks_usd)}  | {asks_quantity:.3f} BTC")
                            lines.append(f"• Pressure    : {pressure_text}")
                            lines.append("")
                        else:
                            lines.append("• Binance depth data supported but no volume data available")
                    else:
                        lines.append("• Binance depth data supported but no data available")
            # Handle standard list format from CoinGlass API
            elif isinstance(binance_depth_data, list) and len(binance_depth_data) > 0:
                # Show up to 2 latest entries (Hari #2 = newest, Hari #1 = older)
                recent_data = binance_depth_data[-2:] if len(binance_depth_data) >= 2 else binance_depth_data
                
                for i, period_data in enumerate(reversed(recent_data)):  # Reverse to show older first
                    if isinstance(period_data, dict):
                        period_time = safe_int(period_data.get("time"))
                        if period_time > 0:
                            dt = datetime.fromtimestamp(period_time / 1000)
                            time_str = dt.strftime('%Y-%m-%d %H:%M UTC')
                        else:
                            time_str = "N/A"
                        
                        bids_total = safe_float(period_data.get("bids_usd", period_data.get("bidsUsd", period_data.get("bidsTotalUsd", 0))))
                        asks_total = safe_float(period_data.get("asks_usd", period_data.get("asksUsd", period_data.get("asksTotalUsd", 0))))
                        bids_amount = safe_float(period_data.get("bids_quantity", period_data.get("bidsCt", period_data.get("bidsAmount", 0))))
                        asks_amount = safe_float(period_data.get("asks_quantity", period_data.get("asksCt", period_data.get("asksAmount", 0))))
                        
                        # Only show data if we have real values (not zeros or none)
                        if (bids_total is not None and bids_total > 0 and 
                            asks_total is not None and asks_total > 0 and
                            bids_amount is not None and bids_amount > 0 and
                            asks_amount is not None and asks_amount > 0):
                            
                            # Calculate pressure
                            if asks_total > 0:
                                pressure_pct = ((bids_total - asks_total) / asks_total) * 100
                                if pressure_pct > 0.5:
                                    pressure_text = f"🟩 Long Dominant (+{pressure_pct:.1f}%)"
                                elif pressure_pct < -0.5:
                                    pressure_text = f"🟥 Short Dominant ({pressure_pct:.1f}%)"
                                else:
                                    pressure_text = "Neutral"
                            else:
                                pressure_text = "Neutral"
                            
                            # Format USD values
                            def format_usd(value):
                                if value >= 1e6:
                                    return f"${value/1e6:,.2f}M"
                                elif value >= 1e3:
                                    return f"${value/1e3:,.0f}K"
                                else:
                                    return f"${value:,.2f}"
                            
                            lines.append(f"[Hari #{i+1}]")
                            lines.append(f"• Waktu       : {time_str}")
                            lines.append(f"• Bids (Long) : {format_usd(bids_total)}  | {bids_amount:.3f} BTC")
                            lines.append(f"• Asks (Short): {format_usd(asks_total)}  | {asks_amount:.3f} BTC")
                            lines.append(f"• Pressure    : {pressure_text}")
                            lines.append("")
            else:
                lines.append("• No Binance depth data available")
        else:
            lines.append("• No Binance depth data available")
        lines.append("")
        
        lines.append("--------------------------------------------------")
        lines.append("")
        
        # Section 3: Aggregated Orderbook Depth (Multi-Exchange) - 1H
        lines.append("3) Aggregated Orderbook Depth (Multi-Exchange) - 1H")
        lines.append("")
        
        # Process aggregated depth data with enhanced support detection
        if aggregated_depth_data:
            # Handle format from raw_data_service.build_raw_orderbook_data
            if isinstance(aggregated_depth_data, dict) and "bids_usd" in aggregated_depth_data:
                agg_bids_usd = safe_float(aggregated_depth_data.get("bids_usd", 0))
                agg_asks_usd = safe_float(aggregated_depth_data.get("asks_usd", 0))
                agg_bids_qty = safe_float(aggregated_depth_data.get("bids_qty", 0))
                agg_asks_qty = safe_float(aggregated_depth_data.get("asks_qty", 0))
                bias_label = aggregated_depth_data.get("bias_label", "N/A")
                
                if agg_bids_usd > 0 or agg_asks_usd > 0:
                    # Calculate pressure
                    if agg_asks_usd > 0:
                        pressure_pct = ((agg_bids_usd - agg_asks_usd) / agg_asks_usd) * 100
                        if pressure_pct > 0.5:
                            pressure_text = f"🟩 Long Dominant (+{pressure_pct:.1f}%)"
                        elif pressure_pct < -0.5:
                            pressure_text = f"🟥 Short Dominant ({pressure_pct:.1f}%)"
                        else:
                            pressure_text = "Neutral"
                    else:
                        pressure_text = "Neutral"
                    
                    # Format USD values
                    def format_usd(value):
                        if value >= 1e6:
                            return f"${value/1e6:,.2f}M"
                        elif value >= 1e3:
                            return f"${value/1e3:,.0f}K"
                        else:
                            return f"${value:,.2f}"
                    
                    lines.append(f"• Agg. Bids   : {format_usd(agg_bids_usd)}  | {agg_bids_qty:.3f}")
                    lines.append(f"• Agg. Asks   : {format_usd(agg_asks_usd)}  | {agg_asks_qty:.3f}")
                    lines.append(f"• Pressure    : {pressure_text}")
                    lines.append("")
                else:
                    lines.append("• No aggregated depth data available")
            # Check if this is enhanced format with support detection
            elif isinstance(aggregated_depth_data, dict) and "supported" in aggregated_depth_data:
                if not aggregated_depth_data.get("supported"):
                    lines.append(f"• {aggregated_depth_data.get('message', 'Aggregated depth data not supported for this symbol')}")
                else:
                    # Enhanced format: extract data from aggregated_data
                    agg_data = aggregated_depth_data.get("aggregated_data", {})
                    if agg_data:
                        agg_bids_usd = safe_float(agg_data.get("aggregated_bids_usd", 0))
                        agg_asks_usd = safe_float(agg_data.get("aggregated_asks_usd", 0))
                        agg_bids_quantity = safe_float(agg_data.get("aggregated_bids_quantity", 0))
                        agg_asks_quantity = safe_float(agg_data.get("aggregated_asks_quantity", 0))
                        
                        if agg_bids_usd > 0 or agg_asks_usd > 0:
                            # Calculate pressure
                            if agg_asks_usd > 0:
                                pressure_pct = ((agg_bids_usd - agg_asks_usd) / agg_asks_usd) * 100
                                if pressure_pct > 0.5:
                                    pressure_text = f"🟩 Long Dominant (+{pressure_pct:.1f}%)"
                                elif pressure_pct < -0.5:
                                    pressure_text = f"🟥 Short Dominant ({pressure_pct:.1f}%)"
                                else:
                                    pressure_text = "Neutral"
                            else:
                                pressure_text = "Neutral"
                            
                            # Format USD values
                            def format_usd(value):
                                if value >= 1e6:
                                    return f"${value/1e6:,.2f}M"
                                elif value >= 1e3:
                                    return f"${value/1e3:,.0f}K"
                                else:
                                    return f"${value:,.2f}"
                            
                            lines.append(f"• Agg. Bids   : {format_usd(agg_bids_usd)}  | {agg_bids_quantity:.3f} BTC")
                            lines.append(f"• Agg. Asks   : {format_usd(agg_asks_usd)}  | {agg_asks_quantity:.3f} BTC")
                            lines.append(f"• Pressure    : {pressure_text}")
                        else:
                            lines.append("• Aggregated depth data supported but no volume data available")
                    else:
                        lines.append("• Aggregated depth data supported but no data available")
            elif isinstance(aggregated_depth_data, list) and len(aggregated_depth_data) > 0:
                # Show up to 2 latest entries (Periode #2 = newest, Periode #1 = older)
                recent_data = aggregated_depth_data[-2:] if len(aggregated_depth_data) >= 2 else aggregated_depth_data
                
                for i, period_data in enumerate(reversed(recent_data)):  # Reverse to show older first
                    if isinstance(period_data, dict):
                        period_time = safe_int(period_data.get("time"))
                        if period_time > 0:
                            dt = datetime.fromtimestamp(period_time / 1000)
                            time_str = dt.strftime('%Y-%m-%d %H:%M UTC')
                        else:
                            time_str = "N/A"
                        
                        agg_bids = safe_float(period_data.get("aggregatedBidsUsd"))
                        agg_asks = safe_float(period_data.get("aggregatedAsksUsd"))
                        agg_bids_amount = safe_float(period_data.get("aggregatedBidsCt"))
                        agg_asks_amount = safe_float(period_data.get("aggregatedAsksCt"))
                        
                        # Only show data if we have real values (not zeros or none)
                        if (agg_bids is not None and agg_bids > 0 and 
                            agg_asks is not None and agg_asks > 0 and
                            agg_bids_amount is not None and agg_bids_amount > 0 and
                            agg_asks_amount is not None and agg_asks_amount > 0):
                            
                            # Calculate pressure
                            if agg_asks > 0:
                                pressure_pct = ((agg_bids - agg_asks) / agg_asks) * 100
                                if pressure_pct > 0.5:
                                    pressure_text = f"🟩 Long Dominant (+{pressure_pct:.1f}%)"
                                elif pressure_pct < -0.5:
                                    pressure_text = f"🟥 Short Dominant ({pressure_pct:.1f}%)"
                                else:
                                    pressure_text = "Neutral"
                            else:
                                pressure_text = "Neutral"
                            
                            # Format USD values
                            def format_usd(value):
                                if value >= 1e6:
                                    return f"${value/1e6:,.2f}M"
                                elif value >= 1e3:
                                    return f"${value/1e3:,.0f}K"
                                else:
                                    return f"${value:,.2f}"
                            
                            lines.append(f"[Periode #{i+1}]")
                            lines.append(f"• Waktu       : {time_str}")
                            lines.append(f"• Agg. Bids   : {format_usd(agg_bids)}  | {agg_bids_amount:.3f} BTC")
                            lines.append(f"• Agg. Asks   : {format_usd(agg_asks)}  | {agg_asks_amount:.3f} BTC")
                            lines.append(f"• Pressure    : {pressure_text}")
                            lines.append("")
            else:
                lines.append("• No aggregated depth data available")
        else:
            lines.append("• No aggregated depth data available")
        lines.append("")
        
        lines.append("--------------------------------------------------")
        lines.append("")
        
        # TL;DR Section
        lines.append("TL;DR Orderbook Bias")
        
        # Analyze snapshot bias
        snapshot_bias_text = "Data tidak tersedia"
        if top_bids and top_asks:
            # Extract numeric values from formatted strings
            bid_levels = []
            ask_levels = []
            
            for bid in top_bids[:3]:  # Top 3 levels
                try:
                    parts = bid.split("|")
                    if len(parts) > 1:
                        price_str = parts[0].strip().replace("•", "").replace(",", "")
                        bid_levels.append(float(price_str))
                except:
                    pass
            
            for ask in top_asks[:3]:  # Top 3 levels
                try:
                    parts = ask.split("|")
                    if len(parts) > 1:
                        price_str = parts[0].strip().replace("•", "").replace(",", "")
                        ask_levels.append(float(price_str))
                except:
                    pass
            
            if bid_levels and ask_levels:
                best_bid = max(bid_levels)
                best_ask = min(ask_levels)
                if best_bid > 0:
                    spread_pct = ((best_ask - best_bid) / best_bid) * 100
                else:
                    spread_pct = 0
                
                if spread_pct < 0.1:
                    snapshot_bias_text = f"Likuiditas sangat tebal di {best_bid:,.0f}"
                elif spread_pct < 0.5:
                    snapshot_bias_text = f"Likuiditas tebal di sekitar {best_bid:,.0f}"
                else:
                    snapshot_bias_text = f"Spread lebar, likuiditas tipis di {best_bid:,.0f}"
        
        # Analyze Binance depth bias (enhanced format support)
        binance_bias_text = "Data tidak tersedia"
        if binance_depth_data:
            # Handle enhanced format with support detection
            if isinstance(binance_depth_data, dict) and "supported" in binance_depth_data:
                if binance_depth_data.get("supported"):
                    depth_data = binance_depth_data.get("depth_data", {})
                    if depth_data:
                        bids_total = safe_float(depth_data.get("bids_usd", 0))
                        asks_total = safe_float(depth_data.get("asks_usd", 0))
                        
                        if bids_total > asks_total * 1.02:  # Lower threshold to 2%
                            binance_bias_text = "Masih 🟩 Long Dominant"
                        elif asks_total > bids_total * 1.02:  # Lower threshold to 2%
                            binance_bias_text = "Masih 🟥 Short Dominant"
                        else:
                            binance_bias_text = "Campuran, seimbang"
                    else:
                        binance_bias_text = "Data tidak tersedia"
                else:
                    binance_bias_text = "Symbol tidak didukung di endpoint ini"
            # Handle legacy list format
            elif isinstance(binance_depth_data, list) and len(binance_depth_data) > 0:
                latest_binance = binance_depth_data[-1]
                if isinstance(latest_binance, dict):
                    bids_total = safe_float(latest_binance.get("bidsUsd", latest_binance.get("bidsTotalUsd", 0)))
                    asks_total = safe_float(latest_binance.get("asksUsd", latest_binance.get("asksTotalUsd", 0)))
                    
                    if bids_total > asks_total * 1.05:
                        binance_bias_text = "Masih 🟩 Long Dominant"
                    elif asks_total > bids_total * 1.05:
                        binance_bias_text = "Masih 🟥 Short Dominant"
                    else:
                        binance_bias_text = "Campuran, seimbang"
        
        # Analyze aggregated bias (enhanced format support)
        agg_bias_text = "Data tidak tersedia"
        if aggregated_depth_data:
            # Handle enhanced format with support detection
            if isinstance(aggregated_depth_data, dict) and "supported" in aggregated_depth_data:
                if aggregated_depth_data.get("supported"):
                    agg_data = aggregated_depth_data.get("aggregated_data", {})
                    if agg_data:
                        agg_bids = safe_float(agg_data.get("aggregated_bids_usd", 0))
                        agg_asks = safe_float(agg_data.get("aggregated_asks_usd", 0))
                        
                        if agg_bids > agg_asks * 1.05:
                            agg_bias_text = "Masih 🟩 Long Dominant"
                        elif agg_asks > agg_bids * 1.05:
                            agg_bias_text = "Masih 🟥 Short Dominant"
                        else:
                            agg_bias_text = "Campuran, seimbang"
                    else:
                        agg_bias_text = "Data tidak tersedia"
                else:
                    agg_bias_text = "Symbol tidak didukung di endpoint ini"
            # Handle legacy list format
            elif isinstance(aggregated_depth_data, list) and len(aggregated_depth_data) > 0:
                latest_agg = aggregated_depth_data[-1]
                if isinstance(latest_agg, dict):
                    agg_bids = safe_float(latest_agg.get("aggregatedBidsUsd", 0))
                    agg_asks = safe_float(latest_agg.get("aggregatedAsksUsd", 0))
                    
                    if agg_bids > agg_asks * 1.05:
                        agg_bias_text = "Masih 🟩 Long Dominant"
                    elif agg_asks > agg_bids * 1.05:
                        agg_bias_text = "Masih 🟥 Short Dominant"
                    else:
                        agg_bias_text = "Campuran, seimbang"
        
        lines.append(f"• Binance Depth (1D)     : {binance_bias_text}")
        lines.append(f"• Aggregated Depth (1H)  : {agg_bias_text}")
        lines.append(f"• Snapshot Level (1H)    : {snapshot_bias_text}")
        
        lines.append("")
        lines.append("Note: Data real dari CoinGlass Orderbook (3 endpoint).")
        
        return "\n".join(lines)
        
    except Exception as e:
        # Fallback error message
        return f"❌ Error formatting raw orderbook data: {str(e)}\n\nPlease try again later."


def format_orderbook_imbalance(analytics: dict) -> str:
    """
    Format orderbook imbalance analysis for Telegram output.
    
    Args:
        analytics: Analytics dictionary containing imbalance data
        
    Returns:
        Formatted string for orderbook imbalance section
    """
    try:
        lines = []
        lines.append("━━━━━━━━━━ ORDERBOOK IMBALANCE ━━━━━━━━━━")
        
        imbalance_data = analytics.get("imbalance", {})
        
        # Binance 1D imbalance
        binance_1d = imbalance_data.get("binance_1d", {})
        binance_pct = binance_1d.get("imbalance_pct", 0.0)
        binance_bias = binance_1d.get("bias", "mixed")
        
        if binance_bias == "buyer":
            binance_emoji = "🟩"
            binance_text = "Buyer Dominant"
        elif binance_bias == "seller":
            binance_emoji = "🔴"
            binance_text = "Seller Dominant"
        else:
            binance_emoji = "🟨"
            binance_text = "Mixed"
        
        lines.append(f"• Binance 1D    : {binance_pct:+.1f}% {binance_emoji} {binance_text}")
        
        # Aggregated 1H imbalance
        aggregated_1h = imbalance_data.get("aggregated_1h", {})
        agg_pct = aggregated_1h.get("imbalance_pct", 0.0)
        agg_bias = aggregated_1h.get("bias", "mixed")
        
        if agg_bias == "buyer":
            agg_emoji = "🟩"
            agg_text = "Buyer Dominant"
        elif agg_bias == "seller":
            agg_emoji = "🔴"
            agg_text = "Seller Dominant"
        else:
            agg_emoji = "🟨"
            agg_text = "Mixed"
        
        lines.append(f"• Aggregated 1H : {agg_pct:+.1f}% {agg_emoji} {agg_text}")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"[FORMATTER] Error formatting orderbook imbalance: {e}")
        return "━━━━━━━━━━ ORDERBOOK IMBALANCE ━━━━━━━━━━\n• Error calculating imbalance data"


def format_spoofing_block(analytics: dict) -> str:
    """
    Format spoofing detection analysis for Telegram output.
    
    Args:
        analytics: Analytics dictionary containing spoofing data
        
    Returns:
        Formatted string for spoofing detection section
    """
    try:
        lines = []
        
        spoofing_data = analytics.get("spoofing", {})
        has_spoofing = spoofing_data.get("has_spoofing", False)
        
        if has_spoofing:
            lines.append("⚠️ SPOOFING ALERT")
            
            spoof_type = spoofing_data.get("type", "unknown").upper()
            level_price = spoofing_data.get("level_price", 0)
            size_usd = spoofing_data.get("size_usd", 0)
            
            # Format price and size
            if level_price >= 1:
                price_str = f"${level_price:,.0f}"
            else:
                price_str = f"${level_price:.6f}"
            
            if size_usd >= 1_000_000:
                size_str = f"${size_usd/1_000_000:.1f}M"
            elif size_usd >= 1_000:
                size_str = f"${size_usd/1_000:.0f}K"
            else:
                size_str = f"${size_usd:.0f}"
            
            lines.append(f"Large {spoof_type} wall at {price_str} – Size: {size_str}")
            lines.append("→ Likely fake liquidity (possible whale trap)")
        else:
            lines.append("Spoofing Detector")
            lines.append("• No suspicious spoofing detected ✔️")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"[FORMATTER] Error formatting spoofing detection: {e}")
        return "Spoofing Detector\n• Error detecting spoofing activity"


def format_liquidity_walls(analytics: dict) -> str:
    """
    Format liquidity walls analysis for Telegram output.
    
    Args:
        analytics: Analytics dictionary containing walls data
        
    Returns:
        Formatted string for liquidity walls section
    """
    try:
        lines = []
        lines.append("━━━━━━━━━━ LIQUIDITY WALLS ━━━━━━━━━━")
        
        walls_data = analytics.get("walls", {})
        buy_walls = walls_data.get("buy_walls", [])
        sell_walls = walls_data.get("sell_walls", [])
        
        # Format and display sell walls (resistance)
        if sell_walls:
            for wall in sell_walls:
                price = wall.get("price", 0)
                size_usd = wall.get("size_usd", 0)
                
                # Format price
                if price >= 1:
                    price_str = f"{price:,.0f}"
                else:
                    price_str = f"{price:.6f}"
                
                # Format size
                if size_usd >= 1_000_000:
                    size_str = f"${size_usd/1_000_000:.1f}M"
                elif size_usd >= 1_000:
                    size_str = f"${size_usd/1_000:.0f}K"
                else:
                    size_str = f"${size_usd:.0f}"
                
                lines.append(f"🧱 SELL WALL @ {price_str} ({size_str})")
        
        # Format and display buy walls (support)
        if buy_walls:
            for wall in buy_walls:
                price = wall.get("price", 0)
                size_usd = wall.get("size_usd", 0)
                
                # Format price
                if price >= 1:
                    price_str = f"{price:,.0f}"
                else:
                    price_str = f"{price:.6f}"
                
                # Format size
                if size_usd >= 1_000_000:
                    size_str = f"${size_usd/1_000_000:.1f}M"
                elif size_usd >= 1_000:
                    size_str = f"${size_usd/1_000:.0f}K"
                else:
                    size_str = f"${size_usd:.0f}"
                
                lines.append(f"🧱 BUY WALL  @ {price_str} ({size_str})")
        
        # If no walls detected
        if not buy_walls and not sell_walls:
            lines.append("• No significant liquidity walls detected")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"[FORMATTER] Error formatting liquidity walls: {e}")
        return "━━━━━━━━━━ LIQUIDITY WALLS ━━━━━━━━━━\n• Error detecting liquidity walls"


def build_raw_orderbook_text_enhanced(orderbook_data: dict) -> str:
    """
    Build enhanced RAW ORDERBOOK report with institutional features.
    This is the new main formatter that includes all 3 institutional features.
    
    Args:
        orderbook_data: Complete orderbook data dictionary with analytics
        
    Returns:
        Formatted text safe for Telegram with all sections
    """
    try:
        lines = []
        
        # Extract basic info
        symbol = orderbook_data.get("symbol", "UNKNOWN")
        exchange = orderbook_data.get("exchange", "Binance")
        interval_ob = orderbook_data.get("interval_ob", "1h")
        depth_range = orderbook_data.get("depth_range", "1%")
        
        # Header
        lines.append(f"[RAW ORDERBOOK - {symbol}]")
        lines.append("")
        
        # Info Umum section
        lines.append("Info Umum")
        lines.append(f"Exchange       : {exchange}")
        lines.append(f"Symbol         : {symbol}")
        lines.append(f"Interval OB    : {interval_ob} (snapshot level)")
        lines.append(f"Depth Range    : {depth_range}")
        lines.append("")
        
        # Section 1: Snapshot Orderbook
        snapshot = orderbook_data.get("snapshot", {})
        lines.append("1) Snapshot Orderbook (Level Price - History 1H)")
        lines.append("")
        
        timestamp = snapshot.get("timestamp", "N/A")
        lines.append(f"Timestamp      : {timestamp}")
        lines.append("")
        
        # Top bids
        top_bids = snapshot.get("top_bids", [])
        lines.append("Top Bids (Pembeli)")
        if top_bids:
            for i, bid in enumerate(top_bids[:5], 1):
                if isinstance(bid, list) and len(bid) >= 2:
                    price = safe_float(bid[0])
                    qty = safe_float(bid[1])
                    if price > 0 and qty > 0:
                        if price >= 1:
                            price_str = f"{price:,.0f}"
                        else:
                            price_str = f"{price:.6f}"
                        lines.append(f"{i}. {price_str}   | {qty:.3f}")
        else:
            lines.append("• No bid data available")
        
        lines.append("")
        
        # Top asks
        top_asks = snapshot.get("top_asks", [])
        lines.append("Top Asks (Penjual)")
        if top_asks:
            for i, ask in enumerate(top_asks[:5], 1):
                if isinstance(ask, list) and len(ask) >= 2:
                    price = safe_float(ask[0])
                    qty = safe_float(ask[1])
                    if price > 0 and qty > 0:
                        if price >= 1:
                            price_str = f"{price:,.0f}"
                        else:
                            price_str = f"{price:.6f}"
                        lines.append(f"{i}. {price_str}   | {qty:.3f}")
        else:
            lines.append("• No ask data available")
        
        lines.append("")
        lines.append("--------------------------------------------------")
        lines.append("")
        
        # Section 2: Binance Orderbook Depth
        binance_depth = orderbook_data.get("binance_depth", {})
        lines.append("2) Binance Orderbook Depth (Bids vs Asks) - 1D")
        lines.append("")
        
        bids_usd = safe_float(binance_depth.get("bids_usd", 0))
        asks_usd = safe_float(binance_depth.get("asks_usd", 0))
        bias_label = binance_depth.get("bias_label", "N/A")
        
        if bids_usd > 0 or asks_usd > 0:
            def format_usd(value):
                if value >= 1e6:
                    return f"${value/1e6:,.2f}M"
                elif value >= 1e3:
                    return f"${value/1e3:,.0f}K"
                else:
                    return f"${value:,.2f}"
            
            lines.append(f"• Bids (Long) : {format_usd(bids_usd)}")
            lines.append(f"• Asks (Short): {format_usd(asks_usd)}")
            lines.append(f"• Bias        : {bias_label}")
        else:
            lines.append("• No Binance depth data available")
        
        lines.append("")
        lines.append("--------------------------------------------------")
        lines.append("")
        
        # Section 3: Aggregated Orderbook Depth
        aggregated_depth = orderbook_data.get("aggregated_depth", {})
        lines.append("3) Aggregated Orderbook Depth (Multi-Exchange) - 1H")
        lines.append("")
        
        agg_bids_usd = safe_float(aggregated_depth.get("bids_usd", 0))
        agg_asks_usd = safe_float(aggregated_depth.get("asks_usd", 0))
        agg_bias_label = aggregated_depth.get("bias_label", "N/A")
        
        if agg_bids_usd > 0 or agg_asks_usd > 0:
            def format_usd(value):
                if value >= 1e6:
                    return f"${value/1e6:,.2f}M"
                elif value >= 1e3:
                    return f"${value/1e3:,.0f}K"
                else:
                    return f"${value:,.2f}"
            
            lines.append(f"• Agg. Bids   : {format_usd(agg_bids_usd)}")
            lines.append(f"• Agg. Asks   : {format_usd(agg_asks_usd)}")
            lines.append(f"• Bias        : {agg_bias_label}")
        else:
            lines.append("• No aggregated depth data available")
        
        lines.append("")
        
        # NEW: Section 4: Orderbook Imbalance
        analytics = orderbook_data.get("analytics", {})
        if analytics:
            lines.append(format_orderbook_imbalance(analytics))
            lines.append("")
        
        # NEW: Section 5: Spoofing Detector
        if analytics:
            lines.append(format_spoofing_block(analytics))
            lines.append("")
        
        # NEW: Section 6: Liquidity Walls
        if analytics:
            lines.append(format_liquidity_walls(analytics))
            lines.append("")
        
        # TL;DR Section
        lines.append("TL;DR Orderbook Bias")
        
        # Analyze overall bias
        if bids_usd > 0 and asks_usd > 0:
            if bids_usd > asks_usd * 1.1:
                binance_tldr = "🟩 Buyer pressure detected"
            elif asks_usd > bids_usd * 1.1:
                binance_tldr = "🔴 Seller pressure detected"
            else:
                binance_tldr = "🟨 Balanced orderbook"
        else:
            binance_tldr = "Data tidak tersedia"
        
        if agg_bids_usd > 0 and agg_asks_usd > 0:
            if agg_bids_usd > agg_asks_usd * 1.1:
                agg_tldr = "🟩 Buyer pressure detected"
            elif agg_asks_usd > agg_bids_usd * 1.1:
                agg_tldr = "🔴 Seller pressure detected"
            else:
                agg_tldr = "🟨 Balanced orderbook"
        else:
            agg_tldr = "Data tidak tersedia"
        
        lines.append(f"• Binance 1D     : {binance_tldr}")
        lines.append(f"• Aggregated 1H  : {agg_tldr}")
        
        # Add spoofing and walls summary
        if analytics:
            spoofing_data = analytics.get("spoofing", {})
            walls_data = analytics.get("walls", {})
            
            if spoofing_data.get("has_spoofing"):
                lines.append("• ⚠️ Potential spoofing detected")
            
            buy_walls = walls_data.get("buy_walls", [])
            sell_walls = walls_data.get("sell_walls", [])
            
            if buy_walls or sell_walls:
                lines.append(f"• 🧱 {len(buy_walls)} buy walls, {len(sell_walls)} sell walls detected")
        
        lines.append("")
        lines.append("Note: Data real dari CoinGlass Orderbook dengan analitik institusional.")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"[FORMATTER] Error building enhanced raw orderbook text: {e}")
        return f"❌ Error formatting enhanced raw orderbook data: {str(e)}\n\nPlease try again later."
