"""
Smart Alert Engine untuk WS Alert Bot

Engine ini memproses real-time events dari WebSocket dengan:
- Threshold filtering per symbol group
- Cooldown anti-spam
- Formatting pesan yang rapi
- State tracking untuk mencegah duplicate alerts
- Stage 4: Liquidation Storm Detection
"""

import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal

from .config import alert_settings, AlertConfig
from .telegram_alert_bot import telegram_alert_bot

logger = logging.getLogger("ws_alert.alert_engine")


class AlertState:
    """State tracking untuk anti-spam alerts"""
    
    def __init__(self):
        self.last_alerts: Dict[Tuple[str, str], float] = {}  # (alert_type, symbol) -> timestamp
        logger.info("[ALERT_ENGINE] Alert state initialized")
    
    def should_send_alert(self, alert_type: str, symbol: str, now_ts: Optional[float] = None) -> bool:
        """
        Check if alert should be sent based on cooldown
        
        Args:
            alert_type: Type like "LIQ_LONG", "LIQ_SHORT", "WHALE_BUY", "WHALE_SELL", "LIQ_STORM"
            symbol: Trading symbol like "BTCUSDT"
            now_ts: Current timestamp (defaults to time.time())
        
        Returns:
            True if alert should be sent, False if still in cooldown
        """
        if now_ts is None:
            now_ts = time.time()
        
        key = (alert_type, symbol)
        
        # Special handling for STORM and CLUSTER alerts (uses different cooldown)
        if alert_type in ["LIQ_STORM", "WHALE_CLUSTER"]:
            # Use default cooldown for storm and cluster alerts
            if alert_type == "LIQ_STORM":
                cooldown_seconds = 300  # 5 minutes
            else:  # WHALE_CLUSTER
                cooldown_seconds = 600  # 10 minutes
        else:
            # Get cooldown from config for other alert types
            cooldown_seconds = AlertConfig.get_cooldown_seconds(symbol, alert_type)
        
        # Check if we ever sent this alert type for this symbol
        if key not in self.last_alerts:
            logger.info(f"[ALERT_ENGINE] First time alert for {alert_type}:{symbol}")
            self.last_alerts[key] = now_ts
            return True
        
        # Check cooldown
        last_sent = self.last_alerts[key]
        time_diff = now_ts - last_sent
        
        if time_diff >= cooldown_seconds:
            logger.info(f"[ALERT_ENGINE] Cooldown passed for {alert_type}:{symbol} ({time_diff:.0f}s >= {cooldown_seconds}s)")
            self.last_alerts[key] = now_ts
            return True
        else:
            remaining = cooldown_seconds - time_diff
            logger.info(f"[ALERT_ENGINE] Alert blocked by cooldown for {alert_type}:{symbol} ({remaining:.0f}s remaining)")
            return False
    
    def cleanup_old_alerts(self, max_age_hours: int = 24):
        """Clean up old alert records to prevent memory leak"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        old_keys = []
        for key, timestamp in self.last_alerts.items():
            if timestamp < cutoff_time:
                old_keys.append(key)
        
        for key in old_keys:
            del self.last_alerts[key]
        
        if old_keys:
            logger.info(f"[ALERT_ENGINE] Cleaned up {len(old_keys)} old alert records")


class SmartAlertEngine:
    """Smart Alert Engine dengan threshold filtering dan anti-spam"""
    
    def __init__(self):
        self.state = AlertState()
        self.alert_handlers = {}
        self._is_initialized = False
        
        # Register default handlers
        self.register_alert_handler('liquidation', self.handle_liquidation_event)
        self.register_alert_handler('futures_trades', self.handle_futures_trade_event)
        self.register_alert_handler('liquidation_storm', self.handle_liquidation_storm)
        self.register_alert_handler('whale_cluster', self.handle_whale_cluster)
        self.register_alert_handler('global_radar', self.handle_global_radar_event)
        
        logger.info("[ALERT_ENGINE] Smart Alert Engine initialized")
    
    def register_alert_handler(self, event_type: str, handler_func):
        """Register handler untuk event type"""
        self.alert_handlers[event_type] = handler_func
        logger.info(f"[ALERT_ENGINE] Registered handler for {event_type}")
    
    async def initialize(self):
        """Initialize alert engine"""
        if self._is_initialized:
            return
        
        # Initialize telegram bot
        await telegram_alert_bot.initialize()
        self._is_initialized = True
        logger.info("[ALERT_ENGINE] Alert engine initialized")
    
    def format_usd(self, amount: float) -> str:
        """Format USD amount dengan proper separator"""
        if amount >= 1_000_000:
            return f"${amount/1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount/1_000:.0f}K"
        else:
            return f"${amount:.0f}"
    
    def format_datetime(self, timestamp_ms: int) -> str:
        """Format timestamp ke human readable datetime"""
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    def format_liquidation_message(self, data: dict, threshold: float, group_name: str) -> str:
        """Format liquidation alert message"""
        symbol = data.get('symbol', 'UNKNOWN')
        exchange = data.get('exName', 'Unknown')
        price = data.get('price', 0)
        side = data.get('side', 0)
        vol_usd = data.get('volUsd', 0)
        time_ms = data.get('time', 0)
        
        # Determine liquidation direction
        if side == 1:
            direction = "Long liq 📉"
            alert_type = "LIQ_LONG"
        elif side == 2:
            direction = "Short liq 📈"
            alert_type = "LIQ_SHORT"
        else:
            direction = "Unknown"
            alert_type = "LIQ_UNKNOWN"
        
        return f"""🔥 **Liquidation Alert – {symbol}**

Exchange   : {exchange}
Direction  : {direction}
Nominal    : {self.format_usd(vol_usd)}
Harga      : ${price:,.2f}
Waktu      : {self.format_datetime(time_ms)}

📊 *Details*:
• Kelompok: {group_name}
• Threshold: {self.format_usd(threshold)}
• Event ini melewati volume filter

#liquidation #{symbol.replace('USDT', '')}"""
    
    def format_whale_message(self, data: dict, threshold: float, group_name: str, channel: str) -> str:
        """Format whale trade alert message"""
        symbol = data.get('symbol', 'UNKNOWN')
        exchange = data.get('exName', 'Unknown')
        price = data.get('price', 0)
        side = data.get('side', 0)
        vol_usd = data.get('volUsd', 0)
        time_ms = data.get('time', 0)
        
        # Determine trade direction
        if side == 1:
            direction = "SELL 📉"
            alert_type = "WHALE_SELL"
        elif side == 2:
            direction = "BUY 📈"
            alert_type = "WHALE_BUY"
        else:
            direction = "Unknown"
            alert_type = "WHALE_UNKNOWN"
        
        return f"""🐋 **Whale Trade – {symbol}**

Exchange   : {exchange}
Direction  : {direction}
Nominal    : {self.format_usd(vol_usd)}
Harga      : ${price:,.2f}
Channel    : {channel}
Waktu      : {self.format_datetime(time_ms)}

📊 *Details*:
• Kelompok: {group_name}
• Di atas threshold: {self.format_usd(threshold)}

#whale #{symbol.replace('USDT', '')}"""
    
    def format_liquidation_storm_message(self, storm_info) -> str:
        """Format liquidation storm alert message"""
        symbol = storm_info.symbol
        total_usd = storm_info.total_usd
        side = storm_info.side
        count = storm_info.count
        window = storm_info.window
        
        # Format side display
        side_display = "Long Liquidations 📉" if side == "long_liq" else "Short Liquidations 📈"
        
        return f"""⚠️ **LIQUIDATION STORM – {symbol}**

Side        : {side_display}
Total USD   : {self.format_usd(total_usd)}
Events      : {count} in {window} sec
Note        : Possible capitulation / reversal zone

📊 *Storm Analysis*:
• Accumulated liquidations detected
• High volatility period
• Market stress indicator

#liquidation_storm #{symbol.replace('USDT', '')} #storm"""
    
    async def send_alert(self, message: str, chat_ids: Optional[List[str]] = None):
        """Send alert to configured chat IDs"""
        if not chat_ids:
            chat_ids = alert_settings.alert_chat_ids
        
        if not chat_ids:
            logger.warning("[ALERT_ENGINE] No chat IDs configured for alerts")
            return
        
        for chat_id in chat_ids:
            try:
                await telegram_alert_bot.send_alert_text(chat_id, message)
                logger.info(f"[ALERT_ENGINE] Alert sent to {chat_id}")
            except Exception as e:
                logger.error(f"[ALERT_ENGINE] Failed to send alert to {chat_id}: {e}")
    
    async def handle_liquidation_event(self, event: dict):
        """
        Handle liquidation events with smart filtering
        
        Event format:
        {
            "channel": "liquidationOrders",
            "data": [
                {
                    "baseAsset": "BTC",
                    "exName": "Binance",
                    "price": 56738.00,
                    "side": 2,
                    "symbol": "BTCUSDT",
                    "time": 1725416318379,
                    "volUsd": 3858.18400
                }
            ]
        }
        """
        try:
            logger.info("[ALERT_ENGINE] 🔥 Processing liquidation event")
            
            data_items = event.get('data', [])
            if not data_items:
                logger.debug("[ALERT_ENGINE] No liquidation data in event")
                return
            
            for item in data_items:
                try:
                    symbol = item.get('symbol', '')
                    if not symbol:
                        continue
                    
                    # Get threshold and group
                    threshold = AlertConfig.get_liq_threshold(symbol)
                    group_name = AlertConfig.get_symbol_group(symbol)
                    vol_usd = item.get('volUsd', 0)
                    
                    logger.info(f"[ALERT_ENGINE] Liquidation: {symbol} ${vol_usd:,.0f} (threshold: ${threshold:,.0f})")
                    
                    # Check threshold
                    if vol_usd < threshold:
                        logger.debug(f"[ALERT_ENGINE] Volume below threshold, skipping: {symbol} ${vol_usd:,.0f} < ${threshold:,.0f}")
                        continue
                    
                    # Determine alert type and check cooldown
                    side = item.get('side', 0)
                    alert_type = "LIQ_LONG" if side == 1 else "LIQ_SHORT"
                    
                    if not self.state.should_send_alert(alert_type, symbol):
                        logger.debug(f"[ALERT_ENGINE] Alert blocked by cooldown: {alert_type}:{symbol}")
                        continue
                    
                    # Format and send message
                    message = self.format_liquidation_message(item, threshold, group_name)
                    await self.send_alert(message)
                    
                    logger.info(f"[ALERT_ENGINE] ✅ Liquidation alert sent: {symbol} ${vol_usd:,.0f}")
                    
                except Exception as e:
                    logger.error(f"[ALERT_ENGINE] Error processing liquidation item: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"[ALERT_ENGINE] Error in liquidation handler: {e}")
    
    async def handle_futures_trade_event(self, event: dict):
        """
        Handle whale trade events with smart filtering
        
        Event format:
        {
            "channel": "futures_trades@Binance_BTCUSDT@10000",
            "data": [
                {
                    "baseAsset": "BTC",
                    "exName": "Binance",
                    "price": 56738.00,
                    "side": 2,
                    "symbol": "BTCUSDT",
                    "time": 1725416318379,
                    "volUsd": 3858.18400
                }
            ]
        }
        """
        try:
            logger.info("[ALERT_ENGINE] 🐋 Processing futures trade event")
            
            channel = event.get('channel', '')
            data_items = event.get('data', [])
            
            if not data_items:
                logger.debug("[ALERT_ENGINE] No trade data in event")
                return
            
            for item in data_items:
                try:
                    symbol = item.get('symbol', '')
                    if not symbol:
                        continue
                    
                    # Get threshold and group
                    threshold = AlertConfig.get_whale_threshold(symbol)
                    group_name = AlertConfig.get_symbol_group(symbol)
                    vol_usd = item.get('volUsd', 0)
                    
                    logger.info(f"[ALERT_ENGINE] Whale trade: {symbol} ${vol_usd:,.0f} (threshold: ${threshold:,.0f})")
                    
                    # Check threshold
                    if vol_usd < threshold:
                        logger.debug(f"[ALERT_ENGINE] Volume below threshold, skipping: {symbol} ${vol_usd:,.0f} < ${threshold:,.0f}")
                        continue
                    
                    # Determine alert type and check cooldown
                    side = item.get('side', 0)
                    alert_type = "WHALE_BUY" if side == 2 else "WHALE_SELL"
                    
                    if not self.state.should_send_alert(alert_type, symbol):
                        logger.debug(f"[ALERT_ENGINE] Alert blocked by cooldown: {alert_type}:{symbol}")
                        continue
                    
                    # Format and send message
                    message = self.format_whale_message(item, threshold, group_name, channel)
                    await self.send_alert(message)
                    
                    logger.info(f"[ALERT_ENGINE] ✅ Whale alert sent: {symbol} ${vol_usd:,.0f}")
                    
                except Exception as e:
                    logger.error(f"[ALERT_ENGINE] Error processing trade item: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"[ALERT_ENGINE] Error in trade handler: {e}")
    
    async def handle_liquidation_storm(self, storm_info):
        """
        Handle liquidation storm alerts
        
        Args:
            storm_info: StormInfo object with storm details
        """
        try:
            logger.info(f"[ALERT_ENGINE] ⚠️ Processing liquidation storm: {storm_info.symbol}")
            
            symbol = storm_info.symbol
            alert_type = "LIQ_STORM"
            
            # Check cooldown
            if not self.state.should_send_alert(alert_type, symbol):
                logger.debug(f"[ALERT_ENGINE] Storm alert blocked by cooldown: {symbol}")
                return
            
            # Format and send message
            message = self.format_liquidation_storm_message(storm_info)
            await self.send_alert(message)
            
            logger.info(f"[ALERT_ENGINE] ✅ Liquidation storm alert sent: {symbol} {storm_info.side} ${storm_info.total_usd:,.0f}")
            
        except Exception as e:
            logger.error(f"[ALERT_ENGINE] Error in liquidation storm handler: {e}")
    
    async def handle_whale_cluster(self, cluster_info):
        """
        Handle whale cluster alerts
        
        Args:
            cluster_info: ClusterInfo object with cluster details
        """
        try:
            logger.info(f"[ALERT_ENGINE] 🐋 Processing whale cluster: {cluster_info.symbol}")
            
            symbol = cluster_info.symbol
            alert_type = "WHALE_CLUSTER"
            
            # Check cooldown
            if not self.state.should_send_alert(alert_type, symbol):
                logger.debug(f"[ALERT_ENGINE] Whale cluster alert blocked by cooldown: {symbol}")
                return
            
            # Format and send message
            message = self.format_whale_cluster_message(cluster_info)
            await self.send_alert(message)
            
            logger.info(f"[ALERT_ENGINE] ✅ Whale cluster alert sent: {symbol} {cluster_info.dominant_side} ${cluster_info.total_buy_usd + cluster_info.total_sell_usd:,.0f}")
            
        except Exception as e:
            logger.error(f"[ALERT_ENGINE] Error in whale cluster handler: {e}")
    
    def format_whale_cluster_message(self, cluster_info) -> str:
        """Format whale cluster alert message"""
        symbol = cluster_info.symbol
        total_buy_usd = cluster_info.total_buy_usd
        total_sell_usd = cluster_info.total_sell_usd
        buy_count = cluster_info.buy_count
        sell_count = cluster_info.sell_count
        dominant_side = cluster_info.dominant_side
        dominance_ratio = cluster_info.dominance_ratio
        window = cluster_info.window
        
        # Format dominant side display
        side_emoji = "📈" if dominant_side == "BUY" else "📉"
        
        return f"""🐋 **WHALE CLUSTER – {symbol}**

Cluster Type : {dominant_side} Dominance {side_emoji}
Total Volume : {self.format_usd(total_buy_usd + total_sell_usd)}
BUY Volume   : {self.format_usd(total_buy_usd)} ({buy_count} trades)
SELL Volume  : {self.format_usd(total_sell_usd)} ({sell_count} trades)
Dominance    : {dominance_ratio:.1%}
Window       : {window} seconds

📊 *Cluster Analysis*:
• Significant whale accumulation detected
• {dominant_side} pressure overwhelming
• Potential price movement expected

#whale_cluster #{symbol.replace('USDT', '')}"""
    
    async def handle_global_radar_event(self, radar_event):
        """
        Handle global radar events
        
        Args:
            radar_event: RadarEvent object with composite analysis
        """
        try:
            logger.info(f"[ALERT_ENGINE] 🚀 Processing global radar: {radar_event.symbol}")
            
            symbol = radar_event.symbol
            alert_type = "GLOBAL_RADAR"
            
            # Check cooldown (5 minutes default for global radar)
            if not self.state.should_send_alert(alert_type, symbol):
                logger.debug(f"[ALERT_ENGINE] Global radar alert blocked by cooldown: {symbol}")
                return
            
            # Format and send message
            message = self.format_global_radar_message(radar_event)
            await self.send_alert(message)
            
            logger.info(f"[ALERT_ENGINE] ✅ Global radar alert sent: {symbol} - {radar_event.summary}")
            
        except Exception as e:
            logger.error(f"[ALERT_ENGINE] Error in global radar handler: {e}")
    
    def format_global_radar_message(self, radar_event) -> str:
        """Format global radar alert message"""
        symbol = radar_event.symbol
        patterns = radar_event.patterns
        storm_info = radar_event.storm_info
        cluster_info = radar_event.cluster_info
        composite_score = radar_event.composite_score
        volatility_level = radar_event.volatility_level
        market_pressure = radar_event.market_pressure
        signal_strength = radar_event.signal_strength
        
        # Build pattern description
        pattern_descriptions = []
        if any(p.value == "storm_only" for p in patterns):
            pattern_descriptions.append("Liquidation Storm")
        if any(p.value == "cluster_only" for p in patterns):
            pattern_descriptions.append("Whale Cluster")
        if any(p.value == "storm_and_cluster" for p in patterns):
            pattern_descriptions.append("Storm + Cluster")
        if any(p.value == "convergence" for p in patterns):
            pattern_descriptions.append("EXTREME Convergence")
        
        pattern_str = " + ".join(pattern_descriptions)
        
        # Build message sections
        storm_section = ""
        if storm_info:
            side_emoji = "📉" if storm_info.side == "long_liq" else "📈"
            storm_section = f"Storm USD   : {self.format_usd(storm_info.total_usd)} {side_emoji}\n"
        
        cluster_section = ""
        if cluster_info:
            cluster_volume = cluster_info.total_buy_usd + cluster_info.total_sell_usd
            pressure_emoji = "🟢" if cluster_info.dominant_side == "BUY" else "🔴"
            cluster_section = f"""Whale Flow  : {self.format_usd(cluster_volume)} {pressure_emoji}
  BUY : {self.format_usd(cluster_info.total_buy_usd)}
  SELL: {self.format_usd(cluster_info.total_sell_usd)}"""
        
        # Signal strength indicators
        strength_emoji = {
            "weak": "🔸",
            "moderate": "🔶", 
            "strong": "🟠",
            "extreme": "🔴"
        }.get(signal_strength, "🔸")
        
        volatility_emoji = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🟠", 
            "extreme": "🔴"
        }.get(volatility_level, "🟢")
        
        pressure_emoji = {
            "bullish": "🟢 (Bullish)",
            "bearish": "🔴 (Bearish)",
            "neutral": "🟡 (Neutral)"
        }.get(market_pressure, "🟡 (Neutral)")
        
        return f"""🚀 **GLOBAL RADAR – {symbol}**

Pattern     : {pattern_str}
Signal      : {signal_strength.title()} {strength_emoji}
Score       : {composite_score:.2f}/1.0
Volatility  : {volatility_level.title()} {volatility_emoji}
Pressure    : {pressure_emoji}
Window      : {radar_event.window_seconds} seconds

📊 *Market Activity*:
{storm_section}{cluster_section}

🎯 *Radar Analysis*:
• {radar_event.summary}
• Composite intelligence analysis
• Multi-pattern correlation detected

#global_radar #{symbol.replace('USDT', '')} #market_anomaly"""
    
    async def send_test_alert(self):
        """Send a test alert for verification"""
        logger.info("[ALERT_ENGINE] Sending test alert")
        
        test_message = """🧪 **Test Alert – WS Alert Bot**

Ini adalah test alert dari WebSocket Alert Engine.

✅ *Components Checked*:
• Smart threshold filtering
• Cooldown anti-spam system
• Message formatting
• Telegram bot integration
• Stage 4: Liquidation Storm Detection

📊 *Configuration*:
• Alert chat IDs: {}
• Threshold groups: MAJORS, LARGE_CAP, MID_CAP

#test #ws_alert_bot""".format(len(alert_settings.alert_chat_ids))
        
        await self.send_alert(test_message)
        logger.info("[ALERT_ENGINE] Test alert sent")
    
    def cleanup(self):
        """Cleanup old alert records"""
        self.state.cleanup_old_alerts()
        logger.info("[ALERT_ENGINE] Cleanup completed")


# Global instance
alert_engine = SmartAlertEngine()


# Backward compatibility functions
async def handle_liquidation_event(event: dict):
    """Backward compatibility wrapper"""
    await alert_engine.handle_liquidation_event(event)


async def handle_futures_trade_event(event: dict):
    """Backward compatibility wrapper"""
    await alert_engine.handle_futures_trade_event(event)


async def handle_liquidation_storm(storm_info):
    """Backward compatibility wrapper for liquidation storm"""
    await alert_engine.handle_liquidation_storm(storm_info)


async def handle_whale_cluster(cluster_info):
    """Backward compatibility wrapper for whale cluster"""
    await alert_engine.handle_whale_cluster(cluster_info)


async def handle_global_radar_event(radar_event):
    """Backward compatibility wrapper for global radar"""
    await alert_engine.handle_global_radar_event(radar_event)


# Legacy whale monitoring (for fallback mode)
async def start_whale_monitoring(callback=None):
    """Legacy whale monitoring for compatibility"""
    logger.info("[ALERT_ENGINE] Starting whale monitoring (fallback mode)")
    
    # This would integrate with existing whale watcher if needed
    # For now, just log that it's available
    if callback:
        await callback("Whale monitoring started in fallback mode")


async def process_alert_event(event: dict):
    """
    Process WebSocket alert event through smart engine
    
    Args:
        event: WebSocket event data
    """
    channel = event.get('channel', '')
    
    if channel == 'liquidationOrders':
        await alert_engine.handle_liquidation_event(event)
    elif channel.startswith('futures_trades'):
        await alert_engine.handle_futures_trade_event(event)
    else:
        logger.debug(f"[ALERT_ENGINE] Unknown event channel: {channel}")


def register_alert_handler(alert_type: str, handler_func):
    """Register custom alert handler"""
    alert_engine.register_alert_handler(alert_type, handler_func)
