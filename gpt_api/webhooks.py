"""
TELEGLAS GPT API - Webhooks System
Real-time data push mechanism for registered endpoints
"""

import asyncio
import hashlib
import hmac
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import aiofiles
import httpx
from aiohttp_retry import RetryClient, ExponentialRetry
from loguru import logger
from .config import settings
from .schemas import WhaleSnapshot, LiqSnapshot


@dataclass
class WebhookSubscription:
    """Webhook subscription configuration"""
    id: str
    url: str
    api_key: str
    events: List[str]  # Event types: whale, liquidation, price_alert
    symbols: List[str]  # Empty list = all symbols
    secret: Optional[str] = None  # For signature verification
    active: bool = True
    created_at: datetime = None
    last_sent: Optional[datetime] = None
    failure_count: int = 0
    max_failures: int = 5
    rate_limit_seconds: int = 30  # Minimum time between sends
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class WebhookEvent:
    """Webhook event payload"""
    event_type: str
    symbol: str
    data: Dict[str, Any]
    timestamp: datetime
    event_id: str


class WebhookManager:
    """Manages webhook subscriptions and delivery"""
    
    def __init__(self):
        self.enabled = settings.webhooks_enabled if hasattr(settings, 'webhooks_enabled') else True
        self.subscriptions_file = Path("data/webhooks.json")
        self.subscriptions_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.subscriptions: Dict[str, WebhookSubscription] = {}
        self.event_queue = asyncio.Queue()
        self.delivery_task: Optional[asyncio.Task] = None
        
        # HTTP client with retry
        self.http_client = None
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
    async def initialize(self):
        """Initialize webhook system"""
        if not self.enabled:
            logger.info("Webhooks disabled by configuration")
            return
            
        await self.load_subscriptions()
        
        # Initialize HTTP client with retry
        self.http_client = RetryClient(
            retry_options=ExponentialRetry(
                attempts=3,
                start_timeout=1.0,
                max_timeout=10.0,
                factor=2.0
            )
        )
        
        # Start delivery task
        self.delivery_task = asyncio.create_task(self._delivery_loop())
        
        logger.info(f"Webhooks initialized with {len(self.subscriptions)} subscriptions")
    
    async def cleanup(self):
        """Cleanup webhook system"""
        if self.delivery_task:
            self.delivery_task.cancel()
            try:
                await self.delivery_task
            except asyncio.CancelledError:
                pass
                
        if self.http_client:
            await self.http_client.close()
    
    async def load_subscriptions(self):
        """Load subscriptions from file"""
        try:
            if not self.subscriptions_file.exists():
                return
                
            async with aiofiles.open(self.subscriptions_file, 'r') as f:
                content = await f.read()
                data = json.loads(content)
                
            for sub_data in data.get('subscriptions', []):
                subscription = WebhookSubscription(**sub_data)
                # Convert string datetime back to datetime object
                if isinstance(subscription.created_at, str):
                    subscription.created_at = datetime.fromisoformat(subscription.created_at)
                if isinstance(subscription.last_sent, str):
                    subscription.last_sent = datetime.fromisoformat(subscription.last_sent)
                    
                self.subscriptions[subscription.id] = subscription
                
            logger.info(f"Loaded {len(self.subscriptions)} webhook subscriptions")
            
        except Exception as e:
            logger.error(f"Failed to load webhook subscriptions: {e}")
    
    async def save_subscriptions(self):
        """Save subscriptions to file"""
        try:
            data = {
                'subscriptions': [
                    asdict(sub) for sub in self.subscriptions.values()
                ],
                'updated_at': datetime.utcnow().isoformat()
            }
            
            async with aiofiles.open(self.subscriptions_file, 'w') as f:
                await f.write(json.dumps(data, indent=2, default=str))
                
        except Exception as e:
            logger.error(f"Failed to save webhook subscriptions: {e}")
    
    async def register_webhook(self, 
                           url: str, 
                           api_key: str, 
                           events: List[str],
                           symbols: Optional[List[str]] = None,
                           secret: Optional[str] = None) -> str:
        """Register a new webhook subscription"""
        webhook_id = hashlib.sha256(f"{url}{api_key}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]
        
        subscription = WebhookSubscription(
            id=webhook_id,
            url=url,
            api_key=api_key,
            events=events,
            symbols=symbols or [],
            secret=secret
        )
        
        self.subscriptions[webhook_id] = subscription
        await self.save_subscriptions()
        
        logger.info(f"Registered webhook {webhook_id} for {url}")
        return webhook_id
    
    async def unregister_webhook(self, webhook_id: str, api_key: str) -> bool:
        """Unregister a webhook subscription"""
        if webhook_id not in self.subscriptions:
            return False
            
        subscription = self.subscriptions[webhook_id]
        if subscription.api_key != api_key:
            return False
            
        del self.subscriptions[webhook_id]
        await self.save_subscriptions()
        
        logger.info(f"Unregistered webhook {webhook_id}")
        return True
    
    async def get_webhooks(self, api_key: str) -> List[WebhookSubscription]:
        """Get webhooks for an API key"""
        return [
            sub for sub in self.subscriptions.values()
            if sub.api_key == api_key
        ]
    
    async def send_event(self, event_type: str, symbol: str, data: Dict[str, Any]):
        """Queue an event for delivery"""
        if not self.enabled:
            return
            
        event = WebhookEvent(
            event_type=event_type,
            symbol=symbol,
            data=data,
            timestamp=datetime.utcnow(),
            event_id=hashlib.sha256(f"{event_type}{symbol}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]
        )
        
        await self.event_queue.put(event)
        logger.debug(f"Queued webhook event: {event_type} for {symbol}")
    
    async def _delivery_loop(self):
        """Process webhook event delivery"""
        while True:
            try:
                # Get event from queue (with timeout)
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                
                # Find matching subscriptions
                matching_subs = [
                    sub for sub in self.subscriptions.values()
                    if (sub.active and 
                        event.event_type in sub.events and
                        (not sub.symbols or event.symbol in sub.symbols) and
                        self._check_rate_limit(sub))
                ]
                
                # Deliver to all matching subscriptions
                if matching_subs:
                    await asyncio.gather(
                        *[self._deliver_webhook(sub, event) for sub in matching_subs],
                        return_exceptions=True
                    )
                
            except asyncio.TimeoutError:
                # No events in queue, continue
                continue
            except Exception as e:
                logger.error(f"Webhook delivery loop error: {e}")
                await asyncio.sleep(1)
    
    def _check_rate_limit(self, subscription: WebhookSubscription) -> bool:
        """Check if subscription respects rate limit"""
        if not subscription.last_sent:
            return True
            
        time_since_last = datetime.utcnow() - subscription.last_sent
        return time_since_last.total_seconds() >= subscription.rate_limit_seconds
    
    async def _deliver_webhook(self, subscription: WebhookSubscription, event: WebhookEvent):
        """Deliver event to webhook endpoint"""
        try:
            # Prepare payload
            payload = {
                'event_id': event.event_id,
                'event_type': event.event_type,
                'symbol': event.symbol,
                'timestamp': event.timestamp.isoformat(),
                'data': event.data
            }
            
            # Add signature if secret provided
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'TELEGLAS-Webhooks/1.0'
            }
            
            if subscription.secret:
                signature = self._generate_signature(payload, subscription.secret)
                headers['X-TELEGLAS-Signature'] = signature
            
            # Send request
            async with self.http_client as client:
                response = await client.post(
                    subscription.url,
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                
                response.raise_for_status()
            
            # Update subscription
            subscription.last_sent = datetime.utcnow()
            subscription.failure_count = 0
            
            logger.debug(f"Delivered webhook {event.event_id} to {subscription.url}")
            
        except Exception as e:
            subscription.failure_count += 1
            logger.error(f"Failed to deliver webhook {event.event_id} to {subscription.url}: {e}")
            
            # Deactivate if too many failures
            if subscription.failure_count >= subscription.max_failures:
                subscription.active = False
                logger.warning(f"Deactivated webhook {subscription.id} due to too many failures")
                
            await self.save_subscriptions()
    
    def _generate_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """Generate HMAC signature for webhook payload"""
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get webhook statistics"""
        total = len(self.subscriptions)
        active = sum(1 for sub in self.subscriptions.values() if sub.active)
        events_queued = self.event_queue.qsize()
        
        # Count by event type
        event_counts = {}
        for sub in self.subscriptions.values():
            for event in sub.events:
                event_counts[event] = event_counts.get(event, 0) + 1
        
        return {
            'total_subscriptions': total,
            'active_subscriptions': active,
            'inactive_subscriptions': total - active,
            'events_queued': events_queued,
            'event_type_counts': event_counts,
            'system_enabled': self.enabled
        }
    
    async def test_webhook(self, webhook_id: str, api_key: str) -> Dict[str, Any]:
        """Test webhook delivery"""
        if webhook_id not in self.subscriptions:
            return {'success': False, 'error': 'Webhook not found'}
            
        subscription = self.subscriptions[webhook_id]
        if subscription.api_key != api_key:
            return {'success': False, 'error': 'Unauthorized'}
        
        # Create test event
        test_event = WebhookEvent(
            event_type='test',
            symbol='BTC',
            data={'message': 'This is a test webhook from TELEGLAS GPT API'},
            timestamp=datetime.utcnow(),
            event_id='test_' + hashlib.sha256(f"test{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]
        )
        
        try:
            await self._deliver_webhook(subscription, test_event)
            return {'success': True, 'message': 'Test webhook sent successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def reactivate_webhook(self, webhook_id: str, api_key: str) -> bool:
        """Reactivate a failed webhook"""
        if webhook_id not in self.subscriptions:
            return False
            
        subscription = self.subscriptions[webhook_id]
        if subscription.api_key != api_key:
            return False
            
        subscription.active = True
        subscription.failure_count = 0
        await self.save_subscriptions()
        
        logger.info(f"Reactivated webhook {webhook_id}")
        return True


# Global webhook manager
webhook_manager = WebhookManager()


# Event handler decorators
def webhook_handler(event_type: str):
    """Decorator to register webhook event handlers"""
    def decorator(func):
        if event_type not in webhook_manager.event_handlers:
            webhook_manager.event_handlers[event_type] = []
        webhook_manager.event_handlers[event_type].append(func)
        return func
    return decorator


async def initialize_webhooks():
    """Initialize webhook system"""
    await webhook_manager.initialize()


async def cleanup_webhooks():
    """Cleanup webhook system"""
    await webhook_manager.cleanup()


# Event triggers for different data types
async def trigger_whale_event(symbol: str, whale_data: Dict[str, Any]):
    """Trigger whale event webhook"""
    if not webhook_manager.enabled:
        return
        
    # Filter for significant whale transactions
    if whale_data.get('usd_value', 0) >= settings.whale_default_threshold:
        await webhook_manager.send_event('whale', symbol, whale_data)


async def trigger_liquidation_event(symbol: str, liq_data: Dict[str, Any]):
    """Trigger liquidation event webhook"""
    if not webhook_manager.enabled:
        return
        
    # Filter for significant liquidations
    if liq_data.get('usd_value', 0) >= 100000:  # $100k threshold
        await webhook_manager.send_event('liquidation', symbol, liq_data)


async def trigger_price_alert_event(symbol: str, price_data: Dict[str, Any]):
    """Trigger price alert event webhook"""
    if not webhook_manager.enabled:
        return
        
    await webhook_manager.send_event('price_alert', symbol, price_data)
