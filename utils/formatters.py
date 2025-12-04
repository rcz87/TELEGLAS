"""
Formatters for CryptoSat Bot
Contains various formatting functions for different data types and outputs.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from services.coinglass_api import safe_float, safe_int, safe_get, safe_list_get


def build_raw_orderbook_text(
    symbol: str,
    history_data: Any,
    binance_depth_data: list,
    aggregated_depth_data: list,
    exchange: str = "Binance",
    ob_interval: str = "1h",
    depth_range: str = "1%"
) -> str:
    """
    Build formatted RAW ORDERBOOK report from orderbook data.
    Follows exact structure requirements in Indonesian/English mix.
    
    Args:
        symbol: Trading symbol (e.g., "BTCUSDT")
        history_data: Data from orderbook history endpoint
        binance_depth_data: Data from Binance ask-bids history endpoint  
        aggregated_depth_data: Data from aggregated ask-bids history endpoint
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
        if history_data and len(history_data) > 0:
            latest_data = history_data[0] if isinstance(history_data, list) else history_data
            if isinstance(latest_data, dict):
                ts_ms = safe_int(latest_data.get("createTime"))
                if ts_ms > 0:
                    dt = datetime.fromtimestamp(ts_ms / 1000)
                    timestamp = dt.strftime('%Y-%m-%d %H:%M UTC')
        
        lines.append(f"Timestamp      : {timestamp}")
        lines.append("")
        
        # Extract top bids and asks from history data
        top_bids = []
        top_asks = []
        
        if history_data and len(history_data) > 0:
            latest_data = history_data[0] if isinstance(history_data, list) else history_data
            if isinstance(latest_data, dict):
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
        
        # Process Binance depth data
        if binance_depth_data and len(binance_depth_data) > 0:
            data_list = binance_depth_data
            if isinstance(data_list, list):
                # Show up to 2 latest entries (Hari #2 = newest, Hari #1 = older)
                recent_data = data_list[-2:] if len(data_list) >= 2 else data_list
                
                for i, period_data in enumerate(reversed(recent_data)):  # Reverse to show older first
                    if isinstance(period_data, dict):
                        period_time = safe_int(period_data.get("time"))
                        if period_time > 0:
                            dt = datetime.fromtimestamp(period_time / 1000)
                            time_str = dt.strftime('%Y-%m-%d %H:%M UTC')
                        else:
                            time_str = "N/A"
                        
                        bids_total = safe_float(period_data.get("bidsUsd", period_data.get("bidsTotalUsd", 0)))
                        asks_total = safe_float(period_data.get("asksUsd", period_data.get("asksTotalUsd", 0)))
                        bids_amount = safe_float(period_data.get("bidsCt", period_data.get("bidsAmount", 0)))
                        asks_amount = safe_float(period_data.get("asksCt", period_data.get("asksAmount", 0)))
                        
                        # Only show data if we have real values (not zeros or None)
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
            lines.append("")
        
        lines.append("--------------------------------------------------")
        lines.append("")
        
        # Section 3: Aggregated Orderbook Depth (Multi-Exchange) - 1H
        lines.append("3) Aggregated Orderbook Depth (Multi-Exchange) - 1H")
        lines.append("")
        
        # Process aggregated depth data - NO ZERO FALLBACKS
        if aggregated_depth_data and len(aggregated_depth_data) > 0:
            data_list = aggregated_depth_data
            if isinstance(data_list, list):
                # Show up to 2 latest entries (Periode #2 = newest, Periode #1 = older)
                recent_data = data_list[-2:] if len(data_list) >= 2 else data_list
                
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
                        
                        # Only show data if we have real values (not zeros or None)
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
                spread_pct = ((best_ask - best_bid) / best_bid) * 100
                
                if spread_pct < 0.1:
                    snapshot_bias_text = f"Likuiditas sangat tebal di {best_bid:,.0f}"
                elif spread_pct < 0.5:
                    snapshot_bias_text = f"Likuiditas tebal di sekitar {best_bid:,.0f}"
                else:
                    snapshot_bias_text = f"Spread lebar, likuiditas tipis di {best_bid:,.0f}"
        
        # Analyze Binance depth bias
        binance_bias_text = "Data tidak tersedia"
        if binance_depth_data and len(binance_depth_data) > 0:
            latest_binance = binance_depth_data[-1] if isinstance(binance_depth_data, list) else binance_depth_data
            if isinstance(latest_binance, dict):
                bids_total = safe_float(latest_binance.get("bidsUsd", latest_binance.get("bidsTotalUsd", 0)))
                asks_total = safe_float(latest_binance.get("asksUsd", latest_binance.get("asksTotalUsd", 0)))
                
                if bids_total > asks_total * 1.05:
                    binance_bias_text = "Masih 🟩 Long Dominant"
                elif asks_total > bids_total * 1.05:
                    binance_bias_text = "Masih 🟥 Short Dominant"
                else:
                    binance_bias_text = "Campuran, seimbang"
        
        # Analyze aggregated bias
        agg_bias_text = "Data tidak tersedia"
        if aggregated_depth_data and len(aggregated_depth_data) > 0:
            latest_agg = aggregated_depth_data[-1] if isinstance(aggregated_depth_data, list) else aggregated_depth_data
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
