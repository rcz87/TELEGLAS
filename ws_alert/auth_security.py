"""
Authentication & Security Module (Poin 3)

Handles:
- API key rotation and management
- Request signing for enhanced security
- Privacy filtering and data masking
- Rate limiting per authentication
- Token management and expiry
"""

import hashlib
import hmac
import time
import json
import logging
import secrets
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
import base64

from .config import alert_settings

logger = logging.getLogger("ws_alert.auth_security")


@dataclass
class AuthToken:
    """Authentication token with expiry"""
    token: str
    key_id: str
    expires_at: datetime
    created_at: datetime
    usage_count: int = 0
    last_used: Optional[datetime] = None


@dataclass
class APIKeyRotation:
    """API key rotation tracking"""
    key_id: str
    api_key: str
    created_at: datetime
    last_rotated: Optional[datetime] = None
    rotation_count: int = 0
    is_active: bool = True


class RateLimiter:
    """Rate limiting per authentication key"""
    
    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests = max_requests_per_minute
        self.requests: Dict[str, List[float]] = {}
    
    def is_allowed(self, key_id: str) -> bool:
        """Check if request is allowed for this key"""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        if key_id in self.requests:
            self.requests[key_id] = [
                req_time for req_time in self.requests[key_id] 
                if req_time > minute_ago
            ]
        else:
            self.requests[key_id] = []
        
        # Check if under limit
        if len(self.requests[key_id]) < self.max_requests:
            self.requests[key_id].append(now)
            return True
        
        logger.warning(f"[AUTH] Rate limit exceeded for key: {key_id}")
        return False
    
    def get_usage_stats(self, key_id: str) -> Dict[str, Any]:
        """Get usage statistics for a key"""
        now = time.time()
        minute_ago = now - 60
        
        recent_requests = self.requests.get(key_id, [])
        recent_count = len([t for t in recent_requests if t > minute_ago])
        
        return {
            "current_minute_requests": recent_count,
            "max_requests_per_minute": self.max_requests,
            "remaining_requests": max(0, self.max_requests - recent_count),
            "reset_time": now + 60
        }


class DataMasker:
    """Privacy data masking and filtering"""
    
    SENSITIVE_FIELDS = [
        "api_key", "secret", "token", "password", "private_key",
        "wallet_address", "user_id", "ip_address", "email"
    ]
    
    @staticmethod
    def mask_value(value: str, threshold: float = 0) -> str:
        """Mask sensitive value based on threshold"""
        if not value or not alert_settings.MASK_SENSITIVE_FIELDS:
            return value
        
        # For large USD values, mask partially
        try:
            numeric_value = float(value)
            if numeric_value >= threshold:
                # Show only first and last digits for large amounts
                str_val = str(numeric_value)
                if len(str_val) > 4:
                    return f"{str_val[:2]}***{str_val[-2:]}"
        except (ValueError, TypeError):
            pass
        
        # For strings, mask middle portion
        if len(value) <= 8:
            return "*" * len(value)
        elif len(value) <= 16:
            return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
        else:
            return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"
    
    @staticmethod
    def filter_sensitive_data(data: Dict[str, Any], threshold_usd: float = 0) -> Dict[str, Any]:
        """Filter sensitive data from dictionary"""
        if not alert_settings.PRIVATE_DATA_MASKING:
            return data
        
        filtered_data = {}
        
        for key, value in data.items():
            # Check if key is sensitive
            key_lower = key.lower()
            is_sensitive = any(sensitive in key_lower for sensitive in DataMasker.SENSITIVE_FIELDS)
            
            if is_sensitive:
                filtered_data[key] = DataMasker.mask_value(str(value), threshold_usd)
            elif isinstance(value, dict):
                # Recursively filter nested dictionaries
                filtered_data[key] = DataMasker.filter_sensitive_data(value, threshold_usd)
            elif isinstance(value, (list, tuple)):
                # Filter list items
                filtered_list = []
                for item in value:
                    if isinstance(item, dict):
                        filtered_list.append(DataMasker.filter_sensitive_data(item, threshold_usd))
                    else:
                        filtered_list.append(item)
                filtered_data[key] = filtered_list
            else:
                # Check for USD values above threshold
                try:
                    if isinstance(value, (int, float)) and value >= threshold_usd:
                        filtered_data[key] = DataMasker.mask_value(str(value), threshold_usd)
                    else:
                        filtered_data[key] = value
                except (ValueError, TypeError):
                    filtered_data[key] = value
        
        return filtered_data
    
    @staticmethod
    def should_mask_transaction(transaction_data: Dict[str, Any]) -> bool:
        """Determine if transaction should be masked based on privacy rules"""
        if not alert_settings.PRIVATE_DATA_MASKING:
            return False
        
        # Check USD amount
        usd_amount = transaction_data.get("usd_value", 0) or transaction_data.get("amount_usd", 0)
        if usd_amount >= alert_settings.PRIVATE_DATA_THRESHOLD_USD:
            return True
        
        # Check for sensitive symbols or exchanges
        sensitive_symbols = transaction_data.get("sensitive_symbols", [])
        if sensitive_symbols:
            return True
        
        return False


class RequestSigner:
    """HMAC request signing for enhanced security"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode('utf-8')
    
    def sign_request(self, method: str, url: str, body: str = "", timestamp: Optional[int] = None) -> Dict[str, str]:
        """Create signature for API request"""
        if not alert_settings.REQUEST_SIGNING_ENABLED:
            return {}
        
        if timestamp is None:
            timestamp = int(time.time())
        
        # Create message to sign
        message = f"{method.upper()}\\n{url}\\n{body}\\n{timestamp}"
        
        # Generate HMAC signature
        signature = hmac.new(
            self.secret_key,
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "X-Signature": signature,
            "X-Timestamp": str(timestamp),
            "X-Key-ID": "default"
        }
    
    def verify_signature(self, method: str, url: str, body: str, signature: str, timestamp: int, key_id: str = "default") -> bool:
        """Verify request signature"""
        if not alert_settings.REQUEST_SIGNING_ENABLED:
            return True
        
        # Check timestamp freshness (prevent replay attacks)
        now = int(time.time())
        if abs(now - timestamp) > 300:  # 5 minutes
            logger.warning(f"[AUTH] Request timestamp too old: {timestamp}")
            return False
        
        # Recreate expected signature
        expected_message = f"{method.upper()}\\n{url}\\n{body}\\n{timestamp}"
        expected_signature = hmac.new(
            self.secret_key,
            expected_message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)


class AuthManager:
    """Main authentication and security manager"""
    
    def __init__(self):
        self.active_tokens: Dict[str, AuthToken] = {}
        self.api_keys: Dict[str, APIKeyRotation] = {}
        self.rate_limiter = RateLimiter(alert_settings.RATE_LIMIT_PER_AUTH_KEY)
        self.request_signer = RequestSigner(alert_settings.HMAC_SECRET_KEY)
        self.data_masker = DataMasker()
        
        # Initialize with current API key
        self._initialize_api_keys()
        
        logger.info("[AUTH] Authentication manager initialized")
    
    def _initialize_api_keys(self):
        """Initialize API keys from configuration"""
        if alert_settings.COINGLASS_API_KEY:
            key_id = "coinglass_primary"
            self.api_keys[key_id] = APIKeyRotation(
                key_id=key_id,
                api_key=alert_settings.COINGLASS_API_KEY,
                created_at=datetime.now(),
                is_active=True
            )
            logger.info(f"[AUTH] Initialized API key: {key_id}")
        
        if alert_settings.COINGLASS_API_KEY_WS:
            key_id = "coinglass_ws"
            self.api_keys[key_id] = APIKeyRotation(
                key_id=key_id,
                api_key=alert_settings.COINGLASS_API_KEY_WS,
                created_at=datetime.now(),
                is_active=True
            )
            logger.info(f"[AUTH] Initialized WebSocket API key: {key_id}")
    
    def generate_auth_token(self, key_id: str, expiry_hours: Optional[int] = None) -> Optional[str]:
        """Generate authentication token for API key"""
        if key_id not in self.api_keys:
            logger.error(f"[AUTH] Unknown key ID: {key_id}")
            return None
        
        if expiry_hours is None:
            expiry_hours = alert_settings.AUTH_TOKEN_EXPIRY_HOURS
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=expiry_hours)
        
        # Store token
        auth_token = AuthToken(
            token=token,
            key_id=key_id,
            expires_at=expires_at,
            created_at=datetime.now()
        )
        
        self.active_tokens[token] = auth_token
        logger.info(f"[AUTH] Generated token for {key_id}, expires: {expires_at}")
        
        return token
    
    def validate_token(self, token: str) -> Optional[AuthToken]:
        """Validate and return authentication token"""
        auth_token = self.active_tokens.get(token)
        
        if not auth_token:
            logger.warning(f"[AUTH] Invalid token: {token[:10]}...")
            return None
        
        # Check expiry
        if datetime.now() > auth_token.expires_at:
            logger.warning(f"[AUTH] Token expired: {auth_token.key_id}")
            del self.active_tokens[token]
            return None
        
        # Update usage
        auth_token.usage_count += 1
        auth_token.last_used = datetime.now()
        
        return auth_token
    
    def get_api_key(self, key_id: str) -> Optional[str]:
        """Get API key by ID with rate limiting"""
        if not self.rate_limiter.is_allowed(key_id):
            return None
        
        api_key_obj = self.api_keys.get(key_id)
        if not api_key_obj or not api_key_obj.is_active:
            return None
        
        return api_key_obj.api_key
    
    def rotate_api_key(self, key_id: str, new_key: str) -> bool:
        """Rotate API key for enhanced security"""
        if key_id not in self.api_keys:
            logger.error(f"[AUTH] Cannot rotate unknown key: {key_id}")
            return False
        
        old_key = self.api_keys[key_id]
        old_key.is_active = False
        old_key.last_rotated = datetime.now()
        old_key.rotation_count += 1
        
        # Create new key
        new_key_obj = APIKeyRotation(
            key_id=key_id,
            api_key=new_key,
            created_at=datetime.now(),
            rotation_count=old_key.rotation_count + 1,
            is_active=True
        )
        
        self.api_keys[key_id] = new_key_obj
        
        # Invalidate existing tokens for this key
        tokens_to_remove = [
            token for token, auth_token in self.active_tokens.items()
            if auth_token.key_id == key_id
        ]
        
        for token in tokens_to_remove:
            del self.active_tokens[token]
        
        logger.info(f"[AUTH] Rotated API key: {key_id}")
        return True
    
    def sign_request(self, method: str, url: str, body: str = "") -> Dict[str, str]:
        """Sign API request"""
        return self.request_signer.sign_request(method, url, body)
    
    def filter_private_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from response"""
        return self.data_masker.filter_sensitive_data(
            data, 
            alert_settings.PRIVATE_DATA_THRESHOLD_USD
        )
    
    def cleanup_expired_tokens(self):
        """Clean up expired tokens"""
        now = datetime.now()
        expired_tokens = [
            token for token, auth_token in self.active_tokens.items()
            if now > auth_token.expires_at
        ]
        
        for token in expired_tokens:
            del self.active_tokens[token]
            logger.debug(f"[AUTH] Cleaned expired token: {token[:10]}...")
        
        if expired_tokens:
            logger.info(f"[AUTH] Cleaned {len(expired_tokens)} expired tokens")
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get security and authentication status"""
        active_key_count = len([k for k in self.api_keys.values() if k.is_active])
        total_tokens = len(self.active_tokens)
        
        # Check for expired tokens
        now = datetime.now()
        expired_tokens = len([
            t for t in self.active_tokens.values() 
            if now > t.expires_at
        ])
        
        return {
            "active_api_keys": active_key_count,
            "total_api_keys": len(self.api_keys),
            "active_tokens": total_tokens,
            "expired_tokens": expired_tokens,
            "request_signing_enabled": alert_settings.REQUEST_SIGNING_ENABLED,
            "data_masking_enabled": alert_settings.PRIVATE_DATA_MASKING,
            "rate_limit_per_key": alert_settings.RATE_LIMIT_PER_AUTH_KEY,
            "private_data_threshold_usd": alert_settings.PRIVATE_DATA_THRESHOLD_USD,
            "api_key_rotation_enabled": alert_settings.API_KEY_ROTATION_ENABLED
        }


# Global authentication manager
auth_manager = AuthManager()
