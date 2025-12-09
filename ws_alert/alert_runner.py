"""
WS Alert Runner - Entry Point untuk Alert Bot

File ini adalah orchestrator utama untuk WS Alert Bot yang:
1. Menginisialisasi WebSocket client untuk real-time data
2. Menghubungkan smart alert engine dengan Telegram bot
3. Menjalankan event loop untuk WebSocket dan alerts
4. Menyediakan testing mode untuk verifikasi
5. Stage 4: Liquidation Storm Detection loop
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any

from .config import alert_settings
from .telegram_alert_bot import telegram_alert_bot
from .alert_engine import alert_engine, process_alert_event
from .ws_client import CoinGlassWebSocketClient, DEFAULT_CHANNELS
from .event_aggregator import get_event_aggregator
from .liquidation_storm_detector import get_liquidation_storm_detector
from .whale_cluster_detector import get_whale_cluster_detector
from .global_radar_engine import get_global_radar_engine

# Setup logging
logging.basicConfig(
    level=getattr(logging, alert_settings.LOG_LEVEL),
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("ws_alert.runner")


class WSAlertRunner:
    """Main orchestrator for WS Alert Bot with Smart Alert Engine"""
    
    def __init__(self):
        self.ws_client = None
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Stage 4: Storm and cluster detection components
        self.storm_detector = None
        self.storm_check_task = None
        self.cluster_detector = None
        self.cluster_check_task = None
        self.global_radar_engine = None
        self.radar_check_task = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"[RUNNER] Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_event.set()
    
    async def initialize(self):
        """Initialize all components"""
        try:
            logger.info("[RUNNER] 🚀 Initializing WS Alert Bot...")
            
            # Validate configuration
            alert_settings.validate()
            logger.info("[RUNNER] ✅ Configuration validated")
            
            # Initialize smart alert engine
            await alert_engine.initialize()
            logger.info("[RUNNER] ✅ Smart alert engine initialized")
            
            # Initialize Stage 4: Storm detector
            self.storm_detector = get_liquidation_storm_detector()
            logger.info("[RUNNER] ✅ Liquidation storm detector initialized")
            
            # Initialize Stage 4: Whale cluster detector
            self.cluster_detector = get_whale_cluster_detector()
            logger.info("[RUNNER] ✅ Whale cluster detector initialized")
            
            # Initialize Stage 4: Global radar engine
            self.global_radar_engine = get_global_radar_engine()
            logger.info("[RUNNER] ✅ Global radar engine initialized")
            
            # Initialize WebSocket client
            self.ws_client = CoinGlassWebSocketClient()
            logger.info("[RUNNER] ✅ WebSocket client initialized")
            
            # Register alert handlers
            self._register_alert_handlers()
            logger.info("[RUNNER] ✅ Smart alert handlers registered")
            
            return True
            
        except Exception as e:
            logger.error(f"[RUNNER] ❌ Initialization failed: {e}")
            return False
    
    def _register_alert_handlers(self):
        """Register alert handlers untuk WebSocket events"""
        # Smart alert engine already has handlers registered internally
        # We just need to ensure routing is correct
        logger.info("[RUNNER] ✅ Smart alert handlers registered")
    
    async def send_startup_message(self):
        """Send startup message to all chat IDs"""
        try:
            message = """🤖 **WS ALERT BOT READY**

🎧 *Listening Live for*:
• 🐋 Whale trades (smart filtering)
• 🔥 Liquidations (threshold-based)
• ⚠️ Liquidation Storms (pattern detection)
• 🐋 Whale Clusters (flow analysis)
• 🚀 Global Radar (market anomaly)
•  Market events (anti-spam)

⚡ *Smart Features*:
• Symbol group thresholds (MAJORS/LARGE_CAP/MID_CAP)
• Cooldown anti-spam system
• Real-time WebSocket connection
• Clean message formatting
• Stage 4: Complete Radar Intelligence

🚀 *Status*: Active
⏰ *Started*: {}""".format(asyncio.get_event_loop().time())
            
            await alert_engine.send_alert(message)
            logger.info("[RUNNER] 📢 Startup message sent")
            
        except Exception as e:
            logger.error(f"[RUNNER] Error sending startup message: {e}")
    
    async def send_test_alert(self):
        """Send test alert for verification"""
        try:
            await alert_engine.send_test_alert()
            logger.info("[RUNNER] 📢 Test alert sent")
            
        except Exception as e:
            logger.error(f"[RUNNER] Error sending test alert: {e}")
    
    async def handle_websocket_event(self, event: Dict[str, Any]):
        """Route WebSocket events to smart alert engine and aggregator"""
        try:
            channel = event.get("channel", "")
            logger.debug(f"[RUNNER] 📨 Received event from channel: {channel}")
            
            # Send to aggregator first (Stage 4)
            await self._send_to_aggregator(event, channel)
            
            # Use smart alert engine for processing (Stage 3)
            await process_alert_event(event)
                
        except Exception as e:
            logger.error(f"[RUNNER] Error handling WebSocket event: {e}")
    
    async def _send_to_aggregator(self, event: Dict[str, Any], channel: str):
        """Send event to event aggregator for Stage 4 processing"""
        try:
            aggregator = get_event_aggregator()
            data_items = event.get('data', [])
            
            if not data_items:
                return
            
            for item in data_items:
                try:
                    if channel == 'liquidationOrders':
                        # Send liquidation event to aggregator
                        aggregator.add_liquidation_event(item)
                    elif channel.startswith('futures_trades'):
                        # Send trade event to aggregator
                        aggregator.add_trade_event(item)
                        
                except Exception as e:
                    logger.error(f"[RUNNER] Error sending item to aggregator: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"[RUNNER] Error in _send_to_aggregator: {e}")
    
    async def _storm_detection_loop(self):
        """Stage 4: Liquidation storm detection loop (runs every 5 seconds)"""
        try:
            logger.info("[RUNNER] ⚠️ Starting liquidation storm detection loop...")
            
            while not self.shutdown_event.is_set():
                try:
                    # Get aggregator to find symbols with recent activity
                    aggregator = get_event_aggregator()
                    
                    # Get symbols that have liquidation events in the last 30 seconds
                    recent_symbols = set()
                    for symbol in aggregator.buffer_liquidations.keys():
                        liq_events = aggregator.get_liq_window(symbol, 30)
                        if liq_events:
                            recent_symbols.add(symbol)
                    
                    if recent_symbols:
                        logger.debug(f"[RUNNER] 🌪️ Checking storms for symbols: {list(recent_symbols)}")
                        
                        # Check for storms in each symbol
                        storms = self.storm_detector.check_multiple_symbols(list(recent_symbols))
                        
                        # Send storm alerts if detected
                        for storm in storms:
                            logger.info(f"[RUNNER] ⚠️ Storm detected: {storm.symbol} {storm.side} ${storm.total_usd:,.0f}")
                            await alert_engine.handle_liquidation_storm(storm)
                    
                    # Wait 5 seconds before next check
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"[RUNNER] Error in storm detection loop: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
                    
        except asyncio.CancelledError:
            logger.info("[RUNNER] Storm detection loop cancelled")
        except Exception as e:
            logger.error(f"[RUNNER] Fatal error in storm detection loop: {e}")
    
    async def _cluster_detection_loop(self):
        """Stage 4: Whale cluster detection loop (runs every 5 seconds)"""
        try:
            logger.info("[RUNNER] 🐋 Starting whale cluster detection loop...")
            
            while not self.shutdown_event.is_set():
                try:
                    # Get aggregator to find symbols with recent trade activity
                    aggregator = get_event_aggregator()
                    
                    # Get symbols that have trade events in the last 30 seconds
                    recent_symbols = set()
                    for symbol in aggregator.buffer_trades.keys():
                        trade_events = aggregator.get_trade_window(symbol, 30)
                        if trade_events:
                            recent_symbols.add(symbol)
                    
                    if recent_symbols:
                        logger.debug(f"[RUNNER] 🐋 Checking clusters for symbols: {list(recent_symbols)}")
                        
                        # Check for clusters in each symbol
                        clusters = self.cluster_detector.check_multiple_symbols(list(recent_symbols))
                        
                        # Send cluster alerts if detected
                        for cluster in clusters:
                            logger.info(f"[RUNNER] 🐋 Cluster detected: {cluster.symbol} {cluster.dominant_side} ${cluster.total_buy_usd + cluster.total_sell_usd:,.0f}")
                            await alert_engine.handle_whale_cluster(cluster)
                    
                    # Wait 5 seconds before next check
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"[RUNNER] Error in cluster detection loop: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
                    
        except asyncio.CancelledError:
            logger.info("[RUNNER] Cluster detection loop cancelled")
        except Exception as e:
            logger.error(f"[RUNNER] Fatal error in cluster detection loop: {e}")
    
    async def _global_radar_detection_loop(self):
        """Stage 4: Global radar detection loop (runs every 5 seconds)"""
        try:
            logger.info("[RUNNER] 🚀 Starting global radar detection loop...")
            
            while not self.shutdown_event.is_set():
                try:
                    # Get aggregator to find symbols with recent activity
                    aggregator = get_event_aggregator()
                    
                    # Get symbols that have any events in the last 30 seconds
                    recent_symbols = set()
                    
                    # Check liquidation events
                    for symbol in aggregator.buffer_liquidations.keys():
                        liq_events = aggregator.get_liq_window(symbol, 30)
                        if liq_events:
                            recent_symbols.add(symbol)
                    
                    # Check trade events
                    for symbol in aggregator.buffer_trades.keys():
                        trade_events = aggregator.get_trade_window(symbol, 30)
                        if trade_events:
                            recent_symbols.add(symbol)
                    
                    if recent_symbols:
                        logger.debug(f"[RUNNER] 🚀 Checking global radar for symbols: {list(recent_symbols)}")
                        
                        # Check for radar events in each symbol
                        radar_events = self.global_radar_engine.check_multiple_symbols(list(recent_symbols))
                        
                        # Send radar alerts if detected
                        for radar_event in radar_events:
                            logger.info(f"[RUNNER] 🚀 Radar event detected: {radar_event.symbol} - {radar_event.summary}")
                            await alert_engine.handle_global_radar_event(radar_event)
                    
                    # Wait 5 seconds before next check
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"[RUNNER] Error in global radar detection loop: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
                    
        except asyncio.CancelledError:
            logger.info("[RUNNER] Global radar detection loop cancelled")
        except Exception as e:
            logger.error(f"[RUNNER] Fatal error in global radar detection loop: {e}")
    
    async def run_alert_loop(self):
        """Main alert loop with WebSocket integration"""
        try:
            logger.info("[RUNNER] 🎧 Starting WebSocket alert loop...")
            
            # Check if WebSocket API key is configured
            if not alert_settings.coinglass_api_key_ws or alert_settings.coinglass_api_key_ws == "YOUR_KEY_HERE":
                logger.warning("[RUNNER] ⚠️ WebSocket API key not configured - running in polling mode only")
                
                # Run traditional polling instead
                await self.run_polling_mode()
                return
            
            # Start Stage 4: Storm detection loop
            self.storm_check_task = asyncio.create_task(self._storm_detection_loop())
            logger.info("[RUNNER] ⚠️ Storm detection loop started")
            
            # Start Stage 4: Whale cluster detection loop
            self.cluster_check_task = asyncio.create_task(self._cluster_detection_loop())
            logger.info("[RUNNER] 🐋 Cluster detection loop started")
            
            # Start Stage 4: Global radar detection loop
            self.radar_check_task = asyncio.create_task(self._global_radar_detection_loop())
            logger.info("[RUNNER] 🚀 Global radar detection loop started")
            
            # Start WebSocket client with auto-reconnect
            await self.ws_client.run_with_reconnect(
                channels=DEFAULT_CHANNELS,
                callback=self.handle_websocket_event
            )
            
        except Exception as e:
            logger.error(f"[RUNNER] Error in alert loop: {e}")
    
    async def run_polling_mode(self):
        """Fallback polling mode when WebSocket is not available"""
        try:
            logger.info("[RUNNER] 📡 Starting polling mode (fallback)...")
            
            # Send startup message
            await self.send_startup_message()
            
            # Start traditional whale monitoring (if needed)
            if alert_settings.ENABLE_WHALE_ALERTS:
                from .alert_engine import start_whale_monitoring
                whale_task = asyncio.create_task(start_whale_monitoring())
            else:
                whale_task = None
            
            # Start Stage 4: Storm detection loop even in polling mode
            self.storm_check_task = asyncio.create_task(self._storm_detection_loop())
            logger.info("[RUNNER] ⚠️ Storm detection loop started in polling mode")
            
            # Start Stage 4: Whale cluster detection loop even in polling mode
            self.cluster_check_task = asyncio.create_task(self._cluster_detection_loop())
            logger.info("[RUNNER] 🐋 Cluster detection loop started in polling mode")
            
            # Start Stage 4: Global radar detection loop even in polling mode
            self.radar_check_task = asyncio.create_task(self._global_radar_detection_loop())
            logger.info("[RUNNER] 🚀 Global radar detection loop started in polling mode")
            
            try:
                # Run until shutdown
                while not self.shutdown_event.is_set():
                    await asyncio.sleep(1)
                    
                    # Cleanup old alert records periodically
                    if asyncio.get_event_loop().time() % 3600 < 1:  # Every hour
                        alert_engine.cleanup()
                    
            finally:
                # Cleanup
                if whale_task:
                    whale_task.cancel()
                    try:
                        await whale_task
                    except asyncio.CancelledError:
                        pass
                
        except Exception as e:
            logger.error(f"[RUNNER] Error in polling mode: {e}")
    
    async def run(self):
        """Main entry point for running alert bot"""
        try:
            logger.info("[RUNNER] 🚀 Starting WS Alert Bot (Stage 4 - Liquidation Storm Detection)...")
            
            # Initialize all components
            if not await self.initialize():
                return 1
            
            self.running = True
            
            # Send startup notification
            await self.send_startup_message()
            
            # Send test alert for verification
            await self.send_test_alert()
            
            logger.info("[RUNNER] ✅ WS Alert Bot is running with Stage 4 features...")
            
            # Run main alert loop
            await self.run_alert_loop()
            
        except KeyboardInterrupt:
            logger.info("[RUNNER] ⏹️ Interrupted by user")
        except Exception as e:
            logger.error(f"[RUNNER] ❌ Fatal error: {e}")
            return 1
        finally:
            await self.cleanup()
        
        return 0
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            logger.info("[RUNNER] 🧹 Cleaning up...")
            
            self.running = False
            
            # Cancel storm detection task
            if self.storm_check_task:
                self.storm_check_task.cancel()
                try:
                    await self.storm_check_task
                except asyncio.CancelledError:
                    pass
                logger.info("[RUNNER] ✅ Storm detection task cancelled")
            
            # Cancel cluster detection task
            if self.cluster_check_task:
                self.cluster_check_task.cancel()
                try:
                    await self.cluster_check_task
                except asyncio.CancelledError:
                    pass
                logger.info("[RUNNER] ✅ Cluster detection task cancelled")
            
            # Cancel radar detection task
            if self.radar_check_task:
                self.radar_check_task.cancel()
                try:
                    await self.radar_check_task
                except asyncio.CancelledError:
                    pass
                logger.info("[RUNNER] ✅ Global radar detection task cancelled")
            
            # Cleanup alert engine
            alert_engine.cleanup()
            
            # Cleanup event aggregator (Stage 4)
            aggregator = get_event_aggregator()
            aggregator.clear_old_events(max_age_seconds=0)  # Clear all events
            
            # Disconnect WebSocket
            if self.ws_client:
                await self.ws_client.disconnect()
            
            logger.info("[RUNNER] ✅ Cleanup completed")
            
        except Exception as e:
            logger.error(f"[RUNNER] Error during cleanup: {e}")


# Global runner instance
ws_alert_runner = WSAlertRunner()


async def main():
    """Main async entry point"""
    try:
        return await ws_alert_runner.run()
    except Exception as e:
        logger.error(f"[RUNNER] Fatal error in main: {e}")
        return 1


def run_sync():
    """Synchronous entry point for script execution"""
    try:
        # Run async main
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            return loop.run_until_complete(main())
        finally:
            loop.close()
            
    except KeyboardInterrupt:
        logger.info("[RUNNER] ⏹️ Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"[RUNNER] Fatal error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = run_sync()
    sys.exit(exit_code)
