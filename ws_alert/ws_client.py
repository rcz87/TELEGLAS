"""
CoinGlass WebSocket Client for Real-Time Alerts

Handles WebSocket connections to CoinGlass API for:
- Liquidation orders
- Futures trades (whale transactions)
- Auto-reconnection with exponential backoff
- Ping/pong mechanism for connection health
"""

import asyncio
import json
import logging
import os
import time
from typing import Callable, Dict, List, Optional, Any
from datetime import datetime

try:
    import websockets
    import aiohttp
except ImportError as e:
    raise ImportError("Required packages missing: pip install websockets aiohttp") from e

from .config import alert_settings

logger = logging.getLogger("ws_alert.ws_client")


class CoinGlassWebSocketClient:
    """Async WebSocket client for CoinGlass real-time data"""
    
    def __init__(self):
        self.websocket = None
        self.session = None
        self.is_connected = False
        self.is_running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.base_reconnect_delay = 2  # seconds
        self.max_reconnect_delay = 60  # seconds
        
        # Enhanced ping configuration (from config)
        self.ping_interval = alert_settings.WS_PING_INTERVAL
        self.ping_timeout = alert_settings.WS_PING_TIMEOUT
        self.min_ping_interval = alert_settings.WS_MIN_PING_INTERVAL
        self.max_ping_interval = alert_settings.WS_MAX_PING_INTERVAL
        self.adaptive_ping_enabled = alert_settings.WS_ADAPTIVE_PING_ENABLED
        
        # Ping tracking
        self.last_ping_time = 0
        self.last_pong_time = 0
        self.ping_success_count = 0
        self.ping_failure_count = 0
        self.avg_ping_response_time = 0  # moving average
        self.connection_quality_score = 1.0  # 0-1 scale
        
        self.message_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.subscribed_channels = set()
        
        # WebSocket URL with API key
        api_key = alert_settings.coinglass_api_key_ws
        if not api_key or api_key == "YOUR_KEY_HERE":
            logger.warning("[WS_CLIENT] WebSocket API key not configured - using fallback mode")
            self.ws_url = None
        else:
            self.ws_url = f"wss://open-ws.coinglass.com/ws-api?cg-api-key={api_key}"
            logger.info(f"[WS_CLIENT] Initialized with URL: {self.ws_url[:50]}...")
    
    def _get_ws_url(self) -> str:
        """Get WebSocket URL"""
        return self.ws_url
    
    def _create_subscribe_message(self, channels: List[str]) -> str:
        """Create subscription message"""
        return json.dumps({
            "op": "subscribe",
            "args": channels
        })
    
    async def connect_ws(self) -> bool:
        """Establish WebSocket connection"""
        if not self.ws_url:
            logger.error("[WS_CLIENT] Cannot connect - no WebSocket URL configured")
            return False
            
        try:
            logger.info(f"[WS_CLIENT] Connecting to CoinGlass WebSocket...")
            
            # Create connection with timeout
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    self.ws_url,
                    ping_interval=None,  # We'll handle ping manually
                    ping_timeout=None,
                    close_timeout=10,
                    max_size=10**7,  # 10MB max message size
                ),
                timeout=30.0
            )
            
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("[WS_CLIENT] ✅ Connected to CoinGlass WebSocket")
            
            # Start ping task
            asyncio.create_task(self._ping_loop())
            
            return True
            
        except Exception as e:
            logger.error(f"[WS_CLIENT] ❌ Connection failed: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Graceful disconnect"""
        logger.info("[WS_CLIENT] Disconnecting...")
        self.is_running = False
        self.is_connected = False
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"[WS_CLIENT] Error closing websocket: {e}")
        
        self.websocket = None
        logger.info("[WS_CLIENT] Disconnected")
    
    async def subscribe(self, channels: List[str]) -> bool:
        """Subscribe to channels"""
        if not self.is_connected:
            logger.error("[WS_CLIENT] Cannot subscribe - not connected")
            return False
        
        try:
            for channel in channels:
                if channel in self.subscribed_channels:
                    logger.debug(f"[WS_CLIENT] Already subscribed to: {channel}")
                    continue
                
                subscribe_msg = {
                    "op": "subscribe",
                    "args": [channel]
                }
                
                await self.websocket.send(json.dumps(subscribe_msg))
                self.subscribed_channels.add(channel)
                logger.info(f"[WS_CLIENT] 📡 Subscribed to: {channel}")
                
                # Small delay between subscriptions
                await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"[WS_CLIENT] ❌ Subscribe failed: {e}")
            return False
    
    async def unsubscribe(self, channels: List[str]) -> bool:
        """Unsubscribe from channels"""
        if not self.is_connected:
            return False
        
        try:
            for channel in channels:
                if channel not in self.subscribed_channels:
                    continue
                
                unsubscribe_msg = {
                    "op": "unsubscribe",
                    "args": [channel]
                }
                
                await self.websocket.send(json.dumps(unsubscribe_msg))
                self.subscribed_channels.discard(channel)
                logger.info(f"[WS_CLIENT] 📡 Unsubscribed from: {channel}")
            
            return True
            
        except Exception as e:
            logger.error(f"[WS_CLIENT] ❌ Unsubscribe failed: {e}")
            return False
    
    async def listen_messages(self, callback: Callable[[Dict[str, Any]], None]):
        """Listen for WebSocket messages and call callback"""
        if not self.is_connected:
            logger.error("[WS_CLIENT] Cannot listen - not connected")
            return
        
        self.message_callback = callback
        self.is_running = True
        logger.info("[WS_CLIENT] 🎧 Starting message listener...")
        
        try:
            async for message in self.websocket:
                if not self.is_running:
                    break
                
                try:
                    # Handle pong response
                    if message == "pong":
                        self.last_pong_time = time.time()
                        logger.debug("[WS_CLIENT] 🏓 Received pong")
                        continue
                    
                    # Parse JSON message
                    data = json.loads(message)
                    
                    # Handle ping response
                    if data.get("event") == "ping":
                        logger.debug("[WS_CLIENT] 🏓 Received ping response")
                        continue
                    
                    # Handle subscription confirmation
                    if data.get("success"):
                        logger.info(f"[WS_CLIENT] ✅ Subscription confirmed: {data}")
                        continue
                    
                    # Handle errors
                    if data.get("error"):
                        logger.error(f"[WS_CLIENT] ❌ Error: {data}")
                        continue
                    
                    # Process data message
                    if callback:
                        await self._safe_callback(data)
                    else:
                        logger.debug(f"[WS_CLIENT] 📨 Received: {data}")
                
                except json.JSONDecodeError as e:
                    logger.error(f"[WS_CLIENT] ❌ JSON decode error: {e}")
                except Exception as e:
                    logger.error(f"[WS_CLIENT] ❌ Message processing error: {e}")
        
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"[WS_CLIENT] ⚠️ Connection closed: {e}")
            self.is_connected = False
        except Exception as e:
            logger.error(f"[WS_CLIENT] ❌ Listen error: {e}")
            self.is_connected = False
        
        finally:
            self.is_running = False
            logger.info("[WS_CLIENT] 🛑 Message listener stopped")
    
    async def _safe_callback(self, data: Dict[str, Any]):
        """Safely call user callback with error handling"""
        try:
            if asyncio.iscoroutinefunction(self.message_callback):
                await self.message_callback(data)
            else:
                self.message_callback(data)
        except Exception as e:
            logger.error(f"[WS_CLIENT] ❌ Callback error: {e}")
    
    async def _ping_loop(self):
        """Enhanced ping loop with adaptive interval and timeout handling"""
        while self.is_connected and self.is_running:
            try:
                # Use adaptive ping interval
                current_interval = self._get_adaptive_ping_interval()
                await asyncio.sleep(current_interval)
                
                if self.is_connected and self.websocket:
                    ping_time = time.time()
                    await self.websocket.send("ping")
                    self.last_ping_time = ping_time
                    logger.debug(f"[WS_CLIENT] 🏓 Sent ping (interval: {current_interval}s)")
                    
                    # Wait for pong response with timeout
                    try:
                        await asyncio.wait_for(
                            self._wait_for_pong(),
                            timeout=self.ping_timeout
                        )
                        
                        # Update ping statistics
                        response_time = time.time() - ping_time
                        self._update_ping_statistics(response_time, success=True)
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"[WS_CLIENT] ⚠️ Pong timeout after {self.ping_timeout}s")
                        self._update_ping_statistics(0, success=False)
                        
                        # Consider connection lost on multiple timeouts
                        if self.ping_failure_count >= 3:
                            logger.error("[WS_CLIENT] ❌ Multiple ping timeouts - connection lost")
                            break
                    
                    # Adaptive adjustment
                    if self.adaptive_ping_enabled:
                        self._adjust_ping_interval()
            
            except Exception as e:
                logger.error(f"[WS_CLIENT] ❌ Ping loop error: {e}")
                self.ping_failure_count += 1
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _wait_for_pong(self):
        """Wait for pong response"""
        start_time = self.last_pong_time
        while self.is_connected and self.is_running:
            await asyncio.sleep(0.1)
            if self.last_pong_time > start_time:
                return
    
    def _get_adaptive_ping_interval(self) -> float:
        """Get current adaptive ping interval based on connection quality"""
        if not self.adaptive_ping_enabled:
            return self.ping_interval
        
        # Adjust interval based on connection quality
        if self.connection_quality_score >= 0.8:
            # Excellent connection - can use longer interval
            return min(self.ping_interval * 1.5, self.max_ping_interval)
        elif self.connection_quality_score >= 0.6:
            # Good connection - normal interval
            return self.ping_interval
        elif self.connection_quality_score >= 0.4:
            # Poor connection - more frequent pings
            return max(self.ping_interval * 0.7, self.min_ping_interval)
        else:
            # Very poor connection - maximum frequency
            return self.min_ping_interval
    
    def _update_ping_statistics(self, response_time: float, success: bool):
        """Update ping statistics and connection quality"""
        if success:
            self.ping_success_count += 1
            self.ping_failure_count = 0  # Reset failure count on success
            
            # Update moving average of response time
            if self.avg_ping_response_time == 0:
                self.avg_ping_response_time = response_time
            else:
                # Exponential moving average with alpha=0.3
                self.avg_ping_response_time = (
                    0.7 * self.avg_ping_response_time + 0.3 * response_time
                )
            
            logger.debug(f"[WS_CLIENT] 🏓 Pong received in {response_time:.2f}s "
                        f"(avg: {self.avg_ping_response_time:.2f}s)")
        else:
            self.ping_failure_count += 1
        
        # Update connection quality score
        self._update_connection_quality()
    
    def _update_connection_quality(self):
        """Update connection quality score based on recent ping performance"""
        total_pings = self.ping_success_count + self.ping_failure_count
        
        if total_pings == 0:
            self.connection_quality_score = 1.0
            return
        
        # Success rate component (70% weight)
        success_rate = self.ping_success_count / total_pings
        
        # Response time component (30% weight)
        # Assume response times under 1s are excellent, over 5s are poor
        if self.avg_ping_response_time > 0:
            time_score = max(0, 1 - (self.avg_ping_response_time - 1) / 4)
            time_score = min(1, time_score)
        else:
            time_score = 1.0
        
        # Combined score
        self.connection_quality_score = (0.7 * success_rate + 0.3 * time_score)
        
        logger.debug(f"[WS_CLIENT] 📊 Connection quality: {self.connection_quality_score:.2f} "
                    f"(success: {success_rate:.2f}, time: {time_score:.2f})")
    
    def _adjust_ping_interval(self):
        """Adjust ping interval based on connection quality"""
        if not self.adaptive_ping_enabled:
            return
        
        new_interval = self._get_adaptive_ping_interval()
        
        # Only log if interval actually changed
        if abs(new_interval - self.ping_interval) > 0.5:
            logger.info(f"[WS_CLIENT] 🔄 Adjusting ping interval: "
                       f"{self.ping_interval:.1f}s → {new_interval:.1f}s "
                       f"(quality: {self.connection_quality_score:.2f})")
            
            self.ping_interval = new_interval
    
    def set_ping_interval(self, interval: float):
        """Manually set ping interval"""
        if not self.min_ping_interval <= interval <= self.max_ping_interval:
            logger.warning(f"[WS_CLIENT] Ping interval {interval}s out of range "
                          f"[{self.min_ping_interval}s, {self.max_ping_interval}s]")
            return
        
        self.ping_interval = interval
        logger.info(f"[WS_CLIENT] Ping interval set to {interval}s")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get detailed connection status"""
        return {
            "connected": self.is_connected,
            "running": self.is_running,
            "ping_interval": self.ping_interval,
            "ping_timeout": self.ping_timeout,
            "success_count": self.ping_success_count,
            "failure_count": self.ping_failure_count,
            "avg_response_time": self.avg_ping_response_time,
            "connection_quality": self.connection_quality_score,
            "adaptive_ping_enabled": self.adaptive_ping_enabled,
            "last_ping": self.last_ping_time,
            "last_pong": self.last_pong_time,
            "subscribed_channels": list(self.subscribed_channels)
        }
    
    async def _reconnect_with_backoff(self):
        """Reconnect with exponential backoff"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"[WS_CLIENT] ❌ Max reconnection attempts reached: {self.max_reconnect_attempts}")
            return False
        
        # Calculate delay with exponential backoff
        delay = min(
            self.base_reconnect_delay * (2 ** self.reconnect_attempts),
            self.max_reconnect_delay
        )
        
        self.reconnect_attempts += 1
        logger.warning(f"[WS_CLIENT] 🔄 Reconnecting in {delay}s (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
        
        await asyncio.sleep(delay)
        
        # Attempt reconnection
        if await self.connect_ws():
            # Resubscribe to previous channels
            if self.subscribed_channels:
                await self.subscribe(list(self.subscribed_channels))
            return True
        
        return False
    
    async def run_with_reconnect(self, channels: List[str], callback: Callable[[Dict[str, Any]], None]):
        """Run WebSocket listener with auto-reconnect"""
        logger.info("[WS_CLIENT] 🚀 Starting WebSocket with auto-reconnect...")
        
        # Check if WebSocket is configured
        if not self.ws_url:
            logger.warning("[WS_CLIENT] ⚠️ WebSocket not configured - skipping WebSocket connection")
            return
        
        # Initial connection
        if not await self.connect_ws():
            logger.error("[WS_CLIENT] ❌ Initial connection failed")
            return
        
        # Subscribe to channels
        if not await self.subscribe(channels):
            logger.error("[WS_CLIENT] ❌ Initial subscription failed")
            await self.disconnect()
            return
        
        # Main loop with reconnection
        while self.is_running or self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                # Start listening
                await self.listen_messages(callback)
                
                # If we reach here, connection was lost
                if self.is_running:  # Only reconnect if we're supposed to be running
                    logger.info("[WS_CLIENT] 🔄 Connection lost, attempting reconnection...")
                    if await self._reconnect_with_backoff():
                        continue  # Reconnected, continue listening
                    else:
                        break  # Reconnection failed
                else:
                    break  # Graceful shutdown
            
            except KeyboardInterrupt:
                logger.info("[WS_CLIENT] ⏹️ Interrupted by user")
                break
            except Exception as e:
                logger.error(f"[WS_CLIENT] ❌ Unexpected error: {e}")
                break
        
        await self.disconnect()
        logger.info("[WS_CLIENT] 🛑 WebSocket client stopped")


# Helper functions for easier usage
async def connect_ws() -> CoinGlassWebSocketClient:
    """Create and connect WebSocket client"""
    client = CoinGlassWebSocketClient()
    await client.connect_ws()
    return client


async def subscribe_to_channels(client: CoinGlassWebSocketClient, channels: List[str]) -> bool:
    """Subscribe to channels using client"""
    return await client.subscribe(channels)


async def listen_to_messages(client: CoinGlassWebSocketClient, callback: Callable[[Dict[str, Any]], None]):
    """Listen to messages using client"""
    await client.listen_messages(callback)


# Channel constants
LIQUIDATION_ORDERS_CHANNEL = "liquidationOrders"
FUTURES_TRADES_CHANNEL_TEMPLATE = "futures_trades@{exchange}@{symbol}@{usd_threshold}"


def build_futures_trades_channel(exchange: str = "Binance", symbol: str = "BTCUSDT", usd_threshold: int = 10000) -> str:
    """Build futures trades channel string"""
    return FUTURES_TRADES_CHANNEL_TEMPLATE.format(
        exchange=exchange,
        symbol=symbol,
        usd_threshold=usd_threshold
    )


# Default channel configurations
DEFAULT_CHANNELS = [
    LIQUIDATION_ORDERS_CHANNEL,
    build_futures_trades_channel("Binance", "BTCUSDT", 10000),
]
