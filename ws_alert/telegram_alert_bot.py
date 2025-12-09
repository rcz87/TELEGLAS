"""
Telegram Alert Bot - Bot khusus untuk mengirim alert otomatis

Bot ini berfungsi sebagai "sender/producer" murni - tidak ada handler command manual.
Fokus utama: mengirim alert dari berbagai sumber (whale, liquidation, WebSocket, dll).
"""

import asyncio
import re
from typing import List, Optional, Dict, Any
from loguru import logger
from telegram import Bot
from telegram.helpers import escape_markdown
from ws_alert.config import alert_settings


class TelegramAlertBot:
    """Bot Telegram khusus untuk alert otomatis"""
    
    def __init__(self):
        self.token = alert_settings.TELEGRAM_ALERT_TOKEN
        self.bot = None
        self._initialized = False
        
    async def initialize(self):
        """Inisialisasi bot alert"""
        if not self.token:
            raise ValueError("[ALERT_BOT] TELEGRAM_ALERT_TOKEN is required")
        
        # Validasi token berbeda dari bot utama
        main_bot_token = alert_settings.__dict__.get('TELEGRAM_BOT_TOKEN', '')
        if self.token == main_bot_token:
            raise ValueError("[ALERT_BOT] Alert token must be different from main bot token")
        
        # Create bot instance
        self.bot = Bot(token=self.token)
        
        # Test connection
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"[ALERT_BOT] Initialized: @{bot_info.username} ({bot_info.first_name})")
            self._initialized = True
        except Exception as e:
            logger.error(f"[ALERT_BOT] Failed to initialize: {e}")
            raise
    
    def _ensure_initialized(self):
        """Pastikan bot sudah diinisialisasi"""
        if not self._initialized or not self.bot:
            raise RuntimeError("[ALERT_BOT] Bot not initialized. Call initialize() first.")
    
    def sanitize(self, msg: str) -> str:
        """Escape semua karakter Markdown khusus Telegram"""
        return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', msg)
    
    async def send_alert_text(
        self, 
        chat_id: str, 
        text: str, 
        parse_mode: str = None,
        disable_web_page_preview: bool = True
    ) -> bool:
        """
        Kirim pesan text alert ke chat tertentu
        
        Args:
            chat_id: Target chat ID
            text: Pesan yang akan dikirim
            parse_mode: Markdown/HTML formatting (default: None untuk plain text)
            disable_web_page_preview: Disable link preview
            
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        self._ensure_initialized()
        
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30
            )
            logger.debug(f"[ALERT_BOT] Message sent to {chat_id}: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"[ALERT_BOT] Failed to send message to {chat_id}: {e}")
            return False
    
    async def send_alert_to_all_chats(
        self, 
        text: str, 
        parse_mode: str = None,
        disable_web_page_preview: bool = True
    ) -> Dict[str, bool]:
        """
        Kirim alert ke semua chat IDs yang dikonfigurasi
        
        Args:
            text: Pesan yang akan dikirim
            parse_mode: Markdown/HTML formatting
            disable_web_page_preview: Disable link preview
            
        Returns:
            Dict[str, bool]: Results per chat_id
        """
        results = {}
        
        for chat_id in alert_settings.alert_chat_ids:
            success = await self.send_alert_text(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview
            )
            results[chat_id] = success
            
            # Small delay between messages to avoid rate limits
            await asyncio.sleep(0.1)
        
        success_count = sum(results.values())
        logger.info(f"[ALERT_BOT] Sent to {success_count}/{len(results)} chats")
        
        return results
    
    async def send_whale_alert(self, signal_data: Dict[str, Any]) -> bool:
        """
        Kirim whale alert dengan format khusus
        
        Args:
            signal_data: Data whale signal dari alert engine
            
        Returns:
            bool: True jika berhasil ke semua target chats
        """
        try:
            # Format whale alert message
            message = self._format_whale_alert(signal_data)
            
            # Send to all configured chats
            results = await self.send_alert_to_all_chats(
                text=message,
                parse_mode=None  # Plain text untuk avoid parsing errors
            )
            
            # Return True if at least one chat succeeded
            return any(results.values())
            
        except Exception as e:
            logger.error(f"[ALERT_BOT] Error sending whale alert: {e}")
            return False
    
    async def send_liquidation_alert(self, liquidation_data: Dict[str, Any]) -> bool:
        """
        Kirim liquidation alert dengan format khusus
        
        Args:
            liquidation_data: Data liquidation dari alert engine
            
        Returns:
            bool: True jika berhasil ke semua target chats
        """
        try:
            # Format liquidation alert message
            message = self._format_liquidation_alert(liquidation_data)
            
            # Send to all configured chats
            results = await self.send_alert_to_all_chats(
                text=message,
                parse_mode=None  # Plain text
            )
            
            # Return True if at least one chat succeeded
            return any(results.values())
            
        except Exception as e:
            logger.error(f"[ALERT_BOT] Error sending liquidation alert: {e}")
            return False
    
    async def send_funding_alert(self, funding_data: Dict[str, Any]) -> bool:
        """
        Kirim funding rate alert dengan format khusus
        
        Args:
            funding_data: Data funding rate dari alert engine
            
        Returns:
            bool: True jika berhasil ke semua target chats
        """
        try:
            # Format funding alert message
            message = self._format_funding_alert(funding_data)
            
            # Send to all configured chats
            results = await self.send_alert_to_all_chats(
                text=message,
                parse_mode=None  # Plain text
            )
            
            # Return True if at least one chat succeeded
            return any(results.values())
            
        except Exception as e:
            logger.error(f"[ALERT_BOT] Error sending funding alert: {e}")
            return False
    
    async def send_test_alert(self) -> bool:
        """
        Kirim test alert untuk verifikasi bot berjalan
        
        Returns:
            bool: True jika berhasil
        """
        try:
            from datetime import datetime
            
            test_message = (
                "🤖 [WS ALERT BOT TEST]\n\n"
                f"🕐 Test Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                "✅ Alert bot is running successfully\n"
                "🔔 Ready to receive whale and other alerts\n\n"
                "📡 This message confirms the alert bot is operational."
            )
            
            results = await self.send_alert_to_all_chats(
                text=test_message,
                parse_mode=None
            )
            
            success_count = sum(results.values())
            logger.info(f"[ALERT_BOT] Test alert sent to {success_count}/{len(results)} chats")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"[ALERT_BOT] Error sending test alert: {e}")
            return False
    
    def _format_whale_alert(self, signal_data: Dict[str, Any]) -> str:
        """Format whale alert message"""
        try:
            signal_type = signal_data.get('signal_type', 'unknown')
            symbol = signal_data.get('symbol', 'UNKNOWN')
            amount_usd = signal_data.get('transaction_amount_usd', 0)
            side = signal_data.get('side', 'unknown')
            price = signal_data.get('price', 0)
            confidence = signal_data.get('confidence_score', 0)
            timestamp = signal_data.get('timestamp', '')
            
            # Format timestamp
            if timestamp:
                try:
                    from datetime import datetime
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    time_str = dt.strftime('%H:%M:%S UTC')
                except:
                    time_str = str(timestamp)
            else:
                time_str = 'Unknown'
            
            # Emoji berdasarkan signal type dan side
            action_emoji = "🟢" if signal_type == "accumulation" else "🔴"
            side_emoji = "📈" if side == "buy" else "📉"
            
            # Format amount
            if amount_usd >= 1000000:
                amount_str = f"${amount_usd/1000000:.1f}M"
            elif amount_usd >= 1000:
                amount_str = f"${amount_usd/1000:.0f}K"
            else:
                amount_str = f"${amount_usd:.0f}"
            
            message = (
                f"{action_emoji} WHALE ALERT - {signal_type.upper()}\n\n"
                f"📊 Symbol: {symbol}\n"
                f"{side_emoji} Action: {side.upper()}\n"
                f"💰 Amount: {amount_str}\n"
                f"💲 Price: ${price:,.4f}\n"
                f"🎯 Confidence: {confidence:.0%}\n"
                f"🕐 Time: {time_str}\n"
                f"🏦 Exchange: Hyperliquid\n\n"
                "📡 WS Alert Bot | Real-time Whale Monitoring"
            )
            
            return message
            
        except Exception as e:
            logger.error(f"[ALERT_BOT] Error formatting whale alert: {e}")
            return f"🐋 Whale Alert for {signal_data.get('symbol', 'Unknown')}"
    
    def _format_liquidation_alert(self, liquidation_data: Dict[str, Any]) -> str:
        """Format liquidation alert message"""
        try:
            symbol = liquidation_data.get('symbol', 'UNKNOWN')
            amount_usd = liquidation_data.get('amount_usd', 0)
            side = liquidation_data.get('side', 'unknown')
            price = liquidation_data.get('price', 0)
            timestamp = liquidation_data.get('timestamp', '')
            
            # Format timestamp
            if timestamp:
                try:
                    from datetime import datetime
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    time_str = dt.strftime('%H:%M:%S UTC')
                except:
                    time_str = str(timestamp)
            else:
                time_str = 'Unknown'
            
            # Emoji dan format
            side_emoji = "🔴" if side == "long" else "🟢"
            side_text = "Longs" if side == "long" else "Shorts"
            
            # Format amount
            if amount_usd >= 1000000:
                amount_str = f"${amount_usd/1000000:.1f}M"
            elif amount_usd >= 1000:
                amount_str = f"${amount_usd/1000:.0f}K"
            else:
                amount_str = f"${amount_usd:.0f}"
            
            message = (
                f"🚨 MASSIVE LIQUIDATION\n\n"
                f"📊 Symbol: {symbol}\n"
                f"{side_emoji} Liquidated: {side_text}\n"
                f"💰 Amount: {amount_str}\n"
                f"💲 Price: ${price:,.4f}\n"
                f"🕐 Time: {time_str}\n\n"
                "📡 WS Alert Bot | Liquidation Monitor"
            )
            
            return message
            
        except Exception as e:
            logger.error(f"[ALERT_BOT] Error formatting liquidation alert: {e}")
            return f"🚨 Liquidation Alert for {liquidation_data.get('symbol', 'Unknown')}"
    
    def _format_funding_alert(self, funding_data: Dict[str, Any]) -> str:
        """Format funding rate alert message"""
        try:
            symbol = funding_data.get('symbol', 'UNKNOWN')
            funding_rate = funding_data.get('funding_rate', 0)
            next_funding_time = funding_data.get('next_funding_time', '')
            
            # Emoji berdasarkan rate
            if funding_rate > 0.01:
                emoji = "🔥"
                rate_text = "High Positive"
            elif funding_rate < -0.01:
                emoji = "❄️"
                rate_text = "High Negative"
            else:
                emoji = "💰"
                rate_text = "Extreme"
            
            # Format rate
            rate_pct = funding_rate * 100
            
            message = (
                f"{emoji} EXTREME FUNDING RATE - {rate_text}\n\n"
                f"📊 Symbol: {symbol}\n"
                f"📈 Rate: {rate_pct:+.4f}%\n"
                f"⏰ Next Funding: {next_funding_time or 'Unknown'}\n\n"
                "📡 WS Alert Bot | Funding Rate Monitor"
            )
            
            return message
            
        except Exception as e:
            logger.error(f"[ALERT_BOT] Error formatting funding alert: {e}")
            return f"💰 Funding Alert for {funding_data.get('symbol', 'Unknown')}"
    
    async def process_alert_event(self, event: Dict[str, Any]):
        """
        Process generic alert event - interface untuk WebSocket/alert engine lain
        
        Args:
            event: Dict dengan alert data berupa:
                - alert_type: 'whale', 'liquidation', 'funding', dll
                - data: Payload data spesifik untuk alert type tersebut
        """
        try:
            alert_type = event.get('alert_type', 'unknown')
            data = event.get('data', {})
            
            logger.debug(f"[ALERT_BOT] Processing {alert_type} alert event")
            
            # Route ke handler yang sesuai
            if alert_type == 'whale':
                await self.send_whale_alert(data)
            elif alert_type == 'liquidation':
                await self.send_liquidation_alert(data)
            elif alert_type == 'funding':
                await self.send_funding_alert(data)
            else:
                # Generic alert handler
                await self._send_generic_alert(alert_type, data)
                
        except Exception as e:
            logger.error(f"[ALERT_BOT] Error processing alert event: {e}")
    
    async def _send_generic_alert(self, alert_type: str, data: Dict[str, Any]):
        """Handler untuk alert types yang tidak spesifik"""
        try:
            symbol = data.get('symbol', 'Unknown')
            message = data.get('message', f'{alert_type.title()} alert for {symbol}')
            
            generic_message = (
                f"🔔 {alert_type.upper()} ALERT\n\n"
                f"📊 Symbol: {symbol}\n"
                f"📝 Message: {message}\n\n"
                "📡 WS Alert Bot | Automated Alert System"
            )
            
            await self.send_alert_to_all_chats(
                text=generic_message,
                parse_mode=None
            )
            
        except Exception as e:
            logger.error(f"[ALERT_BOT] Error sending generic alert: {e}")


# Global instance
telegram_alert_bot = TelegramAlertBot()
