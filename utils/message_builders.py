"""
Message builders for TELEGLAS bot
Contains helper functions to build messages without Telegram dependencies
"""

import asyncio
from typing import Dict, List, Optional, Any
from loguru import logger
from services.whale_watcher import WhaleWatcher, get_enhanced_whale_radar
from services.raw_data_service import RawDataService
from services.liquidation_monitor import LiquidationMonitor
from utils.formatters import (
    build_raw_orderbook_text_enhanced
)


# Helper functions untuk build message tanpa Telegram dependency

async def build_liq_message(symbol: str = None) -> str:
    """
    Build liquidation message for preview with upgraded format
    
    Args:
        symbol: Trading symbol (optional, defaults to BTC)
        
    Returns:
        Formatted liquidation message string
    """
    try:
        # Use default symbol if none provided
        if not symbol:
            symbol = "BTC"
        
        # Initialize liquidation monitor
        monitor = LiquidationMonitor()
        
        # Get liquidation data using correct method
        liquidation_data = await monitor.get_symbol_liquidation_summary(symbol)
        
        if not liquidation_data:
            return f"❌ No liquidation data available for {symbol}"
        
        # Extract data using correct field names
        total_liq = liquidation_data.get("liquidation_usd", 0)
        long_liq = liquidation_data.get("long_liquidation_usd", 0)
        short_liq = liquidation_data.get("short_liquidation_usd", 0)
        exchange_count = liquidation_data.get("exchange_count", 0)
        data_source = liquidation_data.get("data_source", "api")
        price_change = liquidation_data.get("price_change", 0)
        volume_24h = liquidation_data.get("volume_24h", 0)
        
        # Format values
        def format_million(value):
            if value >= 1_000_000:
                return f"${value/1_000_000:.2f}M"
            elif value >= 1_000:
                return f"${value/1_000:.0f}K"
            else:
                return f"${value:.0f}"
        
        # Calculate L/S ratio
        ls_ratio = "N/A"
        if long_liq > 0 and short_liq > 0:
            ratio = short_liq / long_liq
            ls_ratio = f"1 : {ratio:.1f}"
        elif long_liq > 0 and short_liq == 0:
            ls_ratio = "1 : 0 (hanya long)"
        elif long_liq == 0 and short_liq > 0:
            ls_ratio = "0 : 1 (hanya short)"
        
        # Determine dominant side
        dominant_side = "N/A"
        bias_emoji = "➡️"
        if short_liq > long_liq:
            dominant_side = "dominan SHORT liq"
            bias_emoji = "⬆️"
        elif long_liq > short_liq:
            dominant_side = "dominan LONG liq"
            bias_emoji = "⬇️"
        
        # Determine fallback status
        fallback_status = "ON" if data_source == "raw_fallback" else "OFF"
        
        # Build the message with new format
        lines = []
        lines.append(f"📊 LIQUIDATION RADAR – {symbol.upper()} (24H)")
        lines.append("")
        
        # Ringkasan section
        lines.append("Ringkasan:")
        lines.append(f"• Total Liq : {format_million(total_liq)}")
        lines.append(f"• Long Liq  : {format_million(long_liq)}")
        lines.append(f"• Short Liq : {format_million(short_liq)}")
        lines.append(f"• L/S Ratio : {ls_ratio} ({dominant_side})")
        lines.append("")
        
        # Market Context section
        lines.append("Market Context:")
        lines.append(f"• Price 24H  : {price_change:+.2f}%")
        lines.append(f"• Volume 24H : {format_million(volume_24h)}")
        lines.append(f"• Sumber Data: {exchange_count} exchange (CoinGlass, fallback: {fallback_status})")
        lines.append("")
        
        # Interpretasi Cepat section
        lines.append("Interpretasi Cepat:")
        if short_liq > long_liq:
            lines.append("• Banyak short yang ke-liquid → potensi short squeeze LANJUT / trend up masih sehat")
            lines.append("• Kalau harga sekarang dekat resistance besar + liq long mulai tebal → waspada pembalikan")
        elif long_liq > short_liq:
            lines.append("• Banyak long yang ke-liquid → potensi long squeeze / trend down masih sehat")
            lines.append("• Kalau harga sekarang dekat support besar + liq short mulai tebal → waspada pembalikan")
        else:
            lines.append("• Liquidation seimbang → market dalam fase konsolidasi")
        lines.append("")
        
        # TL;DR section
        lines.append("TL;DR:")
        if short_liq > long_liq:
            lines.append(f"• Bias liq: {bias_emoji} PRO BULL (short lebih banyak ke-*hajar*)")
            lines.append("• Setup lanjutan: cari buy on dip selama tidak ada long liq tebal di bawah harga sekarang")
        elif long_liq > short_liq:
            lines.append(f"• Bias liq: {bias_emoji} PRO BEAR (long lebih banyak ke-*hajar*)")
            lines.append("• Setup lanjutan: cari sell on rally selama tidak ada short liq tebal di atas harga sekarang")
        else:
            lines.append(f"• Bias liq: {bias_emoji} NETRAL (liquidation seimbang)")
            lines.append("• Setup lanjutan: tunggu konfirmasi breakout atau reversal pattern")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"[LIQ_BUILDER] Error building liquidation message: {e}")
        return f"❌ Error building liquidation message: {str(e)}"


async def build_whale_message() -> str:
    """
    Build whale radar message for preview with upgraded format
    
    Returns:
        Formatted whale radar message string
    """
    try:
        # Get enhanced whale radar data
        enhanced_data, sample_trades, all_positions = await get_enhanced_whale_radar()
        
        # Extract active symbols data
        active_symbols = enhanced_data.get("active_whale_symbols", [])
        
        if not active_symbols:
            return "🐋 WHALE RADAR – HYPERLIQUID\n\n❌ No whale activity detected at the moment."
        
        # Format notional values
        def format_notional(value):
            if value >= 1_000_000:
                return f"${value/1_000_000:.1f}M"
            elif value >= 1_000:
                return f"${value/1_000:.0f}K"
            else:
                return f"${value:.0f}"
        
        # Sort symbols by notional (descending)
        sorted_symbols = sorted(active_symbols, key=lambda x: x.get("notional_usd", 0), reverse=True)
        
        # Build the message with new format
        lines = []
        lines.append("🐋 WHALE RADAR – HYPERLIQUID")
        lines.append("")
        
        # Top 3 Paling Panas section
        lines.append("Top 3 Paling Panas (Notional):")
        for i, symbol_data in enumerate(sorted_symbols[:3], 1):
            symbol = symbol_data.get("symbol", "UNKNOWN")
            notional = symbol_data.get("notional_usd", 0)
            buy_count = symbol_data.get("buy_count", 0)
            sell_count = symbol_data.get("sell_count", 0)
            
            # Determine dominant side
            if buy_count > sell_count:
                dominant = "Dominan BUY"
            elif sell_count > buy_count:
                dominant = "Dominan SELL"
            else:
                dominant = "Seimbang"
            
            lines.append(f"{i}) {symbol} – ≈ {format_notional(notional)} ({buy_count}B / {sell_count}S) → {dominant}")
        
        lines.append("")
        
        # Ringkasan Aktivitas section
        lines.append("Ringkasan Aktivitas:")
        for symbol_data in sorted_symbols[:7]:  # Show top 7 for activity summary
            symbol = symbol_data.get("symbol", "UNKNOWN")
            buy_count = symbol_data.get("buy_count", 0)
            sell_count = symbol_data.get("sell_count", 0)
            total_trades = buy_count + sell_count
            
            # Add pressure indicator
            pressure = ""
            if buy_count > sell_count:
                pressure = " (buy pressure)"
            elif sell_count > buy_count:
                pressure = " (sell pressure)"
            
            lines.append(f"• {symbol:<6} : {total_trades} trades | {buy_count} BUY / {sell_count} SELL{pressure}")
        
        lines.append("")
        
        # Sample trades section
        if sample_trades:
            lines.append("📌 Sampel Transaksi Terbaru:")
            for i, trade in enumerate(sample_trades[:5], 1):
                side = trade.get("side", "UNKNOWN").upper()
                symbol = trade.get("symbol", "UNKNOWN")
                amount = trade.get("amount_usd", 0)
                price = trade.get("price", 0)
                
                lines.append(f"{i}) [{side}] {symbol} – {format_notional(amount)} @ ${price:.2f}")
        else:
            lines.append("📌 Sampel Transaksi Terbaru:")
            lines.append("• No recent trades available")
        
        lines.append("")
        
        # Interpretasi Cepat section
        lines.append("Interpretasi Cepat:")
        
        # Analyze top symbols
        btc_data = next((s for s in sorted_symbols if s.get("symbol") == "BTC"), None)
        eth_data = next((s for s in sorted_symbols if s.get("symbol") == "ETH"), None)
        
        if btc_data:
            btc_buy = btc_data.get("buy_count", 0)
            btc_sell = btc_data.get("sell_count", 0)
            if btc_sell > btc_buy:
                lines.append("• BTC: Whale lebih agresif SELL → potensi tekanan turun / distribusi")
            elif btc_buy > btc_sell:
                lines.append("• BTC: Whale lebih agresif BUY → potensi tekanan naik / akumulasi")
            else:
                lines.append("• BTC: Whale activity seimbang → fase konsolidasi")
        
        # Find accumulation candidates
        accumulation_symbols = []
        for symbol_data in sorted_symbols[:5]:
            symbol = symbol_data.get("symbol", "")
            buy_count = symbol_data.get("buy_count", 0)
            sell_count = symbol_data.get("sell_count", 0)
            if buy_count > sell_count and symbol not in ["BTC", "ETH"]:
                accumulation_symbols.append(symbol)
        
        if accumulation_symbols:
            symbols_str = " & ".join(accumulation_symbols[:3])  # Max 3 symbols
            lines.append(f"• {symbols_str}: Whale lebih banyak BUY → kandidat follow-trend / scalp long")
        
        lines.append("")
        
        # TL;DR section
        lines.append("TL;DR:")
        
        # Focus summary
        focus_symbols = []
        for symbol_data in sorted_symbols[:3]:
            symbol = symbol_data.get("symbol", "")
            buy_count = symbol_data.get("buy_count", 0)
            sell_count = symbol_data.get("sell_count", 0)
            
            if sell_count > buy_count:
                focus_symbols.append(f"{symbol} (dominasi sell)")
            elif buy_count > sell_count:
                focus_symbols.append(f"{symbol} (whale akumulasi)")
            else:
                focus_symbols.append(f"{symbol} (seimbang)")
        
        if focus_symbols:
            focus_str = ", ".join(focus_symbols)
            lines.append(f"• Fokus utama: {focus_str}")
        
        lines.append("• Gunakan bersama /raw & /liq untuk konfirmasi entry.")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"[WHALE_BUILDER] Error building whale message: {e}")
        return f"❌ Error building whale message: {str(e)}"


async def build_raw_message(symbol: str) -> str:
    """
    Build raw market data message for preview
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Formatted raw market data message string
    """
    try:
        # Initialize raw data service
        service = RawDataService()
        
        # Get comprehensive market data
        raw_data = await service.get_comprehensive_market_data(symbol)
        
        if not raw_data or "error" in raw_data:
            return f"❌ No raw data available for {symbol}"
        
        # Format using existing formatter
        message = service.format_standard_raw_message_for_telegram(raw_data)
        
        return message
        
    except Exception as e:
        logger.error(f"[RAW_BUILDER] Error building raw message: {e}")
        return f"❌ Error building raw message: {str(e)}"


async def build_raw_orderbook_message(symbol: str, exchange: str = "Binance") -> str:
    """
    Build raw orderbook message for preview with proper error handling
    
    Args:
        symbol: Trading symbol
        exchange: Exchange name (default: Binance)
        
    Returns:
        Formatted raw orderbook message string
    """
    try:
        # Initialize raw data service
        service = RawDataService()
        
        # Get orderbook data using the correct method
        orderbook_data = await service.build_raw_orderbook_data(symbol)
        
        # Check if orderbook data is valid
        if not orderbook_data:
            return f"❌ No orderbook data available for {symbol}"
        
        # Check if data contains meaningful orderbook information
        snapshot = orderbook_data.get("snapshot", {})
        binance_depth = orderbook_data.get("binance_depth", {})
        aggregated_depth = orderbook_data.get("aggregated_depth", {})
        
        # Log detailed orderbook data for debugging
        logger.info(f"[RAW_ORDERBOOK_BUILDER] Processing {symbol}:")
        logger.info(f"[RAW_ORDERBOOK_BUILDER] Snapshot keys: {list(snapshot.keys())}")
        logger.info(f"[RAW_ORDERBOOK_BUILDER] Binance depth keys: {list(binance_depth.keys())}")
        logger.info(f"[RAW_ORDERBOOK_BUILDER] Aggregated depth keys: {list(aggregated_depth.keys())}")
        
        # Check if all major components are empty/None
        has_snapshot_data = (
            snapshot.get("top_bids") or 
            snapshot.get("top_asks") or 
            snapshot.get("timestamp")
        )
        
        # Loosen validation for Binance depth - don't require > 0 values
        has_binance_depth = (
            binance_depth.get("bids_usd") is not None and 
            binance_depth.get("asks_usd") is not None
        )
        
        # Loosen validation for Aggregated depth - don't require > 0 values
        has_aggregated_depth = (
            aggregated_depth.get("bids_usd") is not None and 
            aggregated_depth.get("asks_usd") is not None
        )
        
        logger.info(f"[RAW_ORDERBOOK_BUILDER] Data availability:")
        logger.info(f"[RAW_ORDERBOOK_BUILDER] - has_snapshot_data: {has_snapshot_data}")
        logger.info(f"[RAW_ORDERBOOK_BUILDER] - has_binance_depth: {has_binance_depth}")
        logger.info(f"[RAW_ORDERBOOK_BUILDER] - has_aggregated_depth: {has_aggregated_depth}")
        
        # Log actual values for debugging
        if has_binance_depth:
            logger.info(f"[RAW_ORDERBOOK_BUILDER] Binance depth values: bids_usd={binance_depth.get('bids_usd')}, asks_usd={binance_depth.get('asks_usd')}")
        if has_aggregated_depth:
            logger.info(f"[RAW_ORDERBOOK_BUILDER] Aggregated depth values: bids_usd={aggregated_depth.get('bids_usd')}, asks_usd={aggregated_depth.get('asks_usd')}")
        
        # If no meaningful data is available, return fallback message
        if not (has_snapshot_data or has_binance_depth or has_aggregated_depth):
            logger.warning(f"[RAW_ORDERBOOK_BUILDER] No orderbook data available for {symbol}")
            return f"""❌ Orderbook Data Unavailable

Orderbook data is temporarily unavailable for `{symbol}`.

**What happened:**
• CoinGlass orderbook API may be experiencing delays
• This symbol might have limited orderbook support
• Market data temporarily unavailable

**Try these alternatives:**
• /raw {symbol} → General market data (always available)
• /raw_orderbook BTC → Try with major symbols
• Wait 30 seconds and retry

💡 Best results: Orderbook works best with BTC, ETH, SOL futures"""
        
        # Format using existing formatter
        message = build_raw_orderbook_text_enhanced(orderbook_data)
        
        return message
        
    except Exception as e:
        logger.error(f"[RAW_ORDERBOOK_BUILDER] Error building raw orderbook message: {e}")
        return f"""[RAW ORDERBOOK - {symbol}]

Orderbook data tidak tersedia untuk simbol ini saat ini.
Kemungkinan:
• Pair ini belum didukung penuh oleh endpoint orderbook.
• Data orderbook untuk simbol ini sedang kosong.

Coba gunakan /raw {symbol} untuk melihat data pasar umumnya."""


# Additional helper functions for testing

async def test_all_builders():
    """
    Test all message builders with sample data
    
    Returns:
        Dict with results from all builders
    """
    results = {}
    
    try:
        # Test liquidation builder
        results["liq"] = await build_liq_message("BTC")
        
        # Test whale builder
        results["whale"] = await build_whale_message()
        
        # Test raw builder
        results["raw"] = await build_raw_message("BTC")
        
        # Test raw orderbook builder
        results["raw_orderbook"] = await build_raw_orderbook_message("BTC", "Binance")
        
    except Exception as e:
        logger.error(f"[TEST_BUILDERS] Error testing builders: {e}")
        results["error"] = str(e)
    
    return results
