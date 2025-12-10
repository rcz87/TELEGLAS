#!/usr/bin/env python3
"""
GPT API Authentication & Security
Authentication middleware and security utilities
"""

import time
import hashlib
import ipaddress
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

try:
    from .config import settings
except ImportError:
    from config import settings


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests: Dict[str, List[float]] = {}
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed based on rate limit"""
        now = time.time()
        
        # Clean old requests
        if key in self.requests:
            self.requests[key] = [req_time for req_time in self.requests[key] 
                                if now - req_time < window]
        else:
            self.requests[key] = []
        
        # Check if under limit
        if len(self.requests[key]) >= limit:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True


class APIKeyAuth:
    """API Key Authentication"""
    
    def __init__(self):
        self.security = HTTPBearer(auto_error=False)
        self.rate_limiter = RateLimiter()
    
    async def verify_api_key(self, credentials: Optional[HTTPAuthorizationCredentials]) -> str:
        """Verify API key and return key identifier"""
        if not settings.require_auth:
            return "anonymous"
        
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        api_key = credentials.credentials
        
        # Validate API key format
        if not self._is_valid_api_key_format(api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key format"
            )
        
        # Check if API key is valid
        if not validate_api_key(api_key):
            logger.warning(f"[AUTH] Invalid API key attempt: {api_key[:8]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Check rate limit
        if not self.rate_limiter.is_allowed(
            api_key, 
            get_rate_limit_per_key(), 
            settings.rate_limit_window
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        return api_key
    
    def _is_valid_api_key_format(self, api_key: str) -> bool:
        """Validate API key format"""
        # Basic format validation - adjust based on your API key format
        if len(api_key) < 16:
            return False
        if not all(c.isalnum() or c in "-_" for c in api_key):
            return False
        return True


class IPWhitelistAuth:
    """IP Whitelist Authentication"""
    
    async def verify_ip_address(self, request: Request) -> str:
        """Verify client IP address"""
        if not settings.require_ip_whitelist:
            return "any"
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Validate IP format
        try:
            ipaddress.ip_address(client_ip)
        except ValueError:
            logger.warning(f"[AUTH] Invalid IP format: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid IP address format"
            )
        
        # Check if IP is in allowlist
        if not validate_ip_address(client_ip):
            logger.warning(f"[AUTH] IP not in allowlist: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="IP address not authorized"
            )
        
        return client_ip
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check for forwarded IP first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the list
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to client IP
        return request.client.host if request.client else "unknown"


class SecurityHeaders:
    """Security headers middleware"""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get security headers for responses"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }


class RequestLogger:
    """Request logging utility"""
    
    @staticmethod
    async def log_request(
        request: Request,
        api_key: str,
        client_ip: str,
        response_status: int,
        processing_time: float
    ):
        """Log request details"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "url": str(request.url),
            "client_ip": client_ip,
            "api_key": api_key[:8] + "..." if len(api_key) > 8 else api_key,
            "status_code": response_status,
            "processing_time_ms": round(processing_time * 1000, 2),
            "user_agent": request.headers.get("User-Agent", "unknown"),
        }
        
        # Log based on status
        if response_status >= 500:
            logger.error(f"[API] Server Error: {log_data}")
        elif response_status >= 400:
            logger.warning(f"[API] Client Error: {log_data}")
        else:
            logger.info(f"[API] Success: {log_data}")


class InputValidator:
    """Input validation utilities"""
    
    @staticmethod
    def validate_symbol(symbol: str) -> str:
        """Validate and normalize symbol"""
        if not symbol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Symbol is required"
            )
        
        # Clean and normalize
        symbol = symbol.strip().upper()
        
        # Check length
        if len(symbol) > settings.max_symbol_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Symbol too long (max {settings.max_symbol_length} characters)"
            )
        
        # Check format
        if not symbol.isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Symbol must contain only letters and numbers"
            )
        
        # Check if supported
        if not is_symbol_supported(symbol):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Symbol '{symbol}' is not supported. Use /info for supported symbols."
            )
        
        return symbol
    
    @staticmethod
    def validate_limit(limit: Optional[int], default: int, maximum: int) -> int:
        """Validate limit parameter"""
        if limit is None:
            return default
        
        if limit < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be at least 1"
            )
        
        if limit > maximum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Limit cannot exceed {maximum}"
            )
        
        return limit
    
    @staticmethod
    def validate_threshold(threshold: Optional[float]) -> Optional[float]:
        """Validate threshold parameter"""
        if threshold is None:
            return None
        
        if threshold < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Threshold cannot be negative"
            )
        
        if threshold > 1_000_000_000:  # 1 billion
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Threshold is too high"
            )
        
        return threshold


# Global instances
api_key_auth = APIKeyAuth()
ip_whitelist_auth = IPWhitelistAuth()
security_headers = SecurityHeaders()
request_logger = RequestLogger()
input_validator = InputValidator()


# Import functions from config
try:
    from .config import (
        validate_api_key,
        validate_ip_address,
        is_symbol_supported,
        get_rate_limit_per_key
    )
except ImportError:
    from config import (
        validate_api_key,
        validate_ip_address,
        is_symbol_supported,
        get_rate_limit_per_key
    )


def generate_api_key_hash(api_key: str) -> str:
    """Generate hash of API key for logging"""
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]


def get_client_info(request: Request, api_key: str) -> Dict[str, Any]:
    """Get client information for logging"""
    return {
        "ip": ip_whitelist_auth._get_client_ip(request),
        "user_agent": request.headers.get("User-Agent", "unknown"),
        "referer": request.headers.get("Referer", "none"),
        "api_key_hash": generate_api_key_hash(api_key) if api_key != "anonymous" else "none",
        "timestamp": datetime.utcnow().isoformat(),
    }


def sanitize_for_logging(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize sensitive data for logging"""
    sanitized = data.copy()
    
    # Remove or mask sensitive fields
    sensitive_fields = ["api_key", "password", "token", "secret"]
    for field in sensitive_fields:
        if field in sanitized:
            if sanitized[field]:
                sanitized[field] = "***"
            else:
                del sanitized[field]
    
    return sanitized
