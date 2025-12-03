"""
Centralized authentication and access control for CryptoSat bot
"""
from typing import Set, Union
from loguru import logger
from config.settings import settings


def is_user_allowed(user_id: int) -> bool:
    """
    Check if a user is allowed to access bot based on WHITELISTED_USERS configuration.
    
    Args:
        user_id (int): Telegram user ID to check
        
    Returns:
        bool: True if user is allowed, False otherwise
    """
    logger.info(f"[AUTH] Checking user {user_id}, WHITELISTED_USERS={settings.WHITELISTED_USERS!r}")

    # Special case: Always allow user ID 5899681906 (hardcoded access)
    if user_id == 5899681906:
        logger.info(f"[AUTH] User {user_id} granted special access (5899681906)")
        return True

    # Wildcard: semua user boleh (kalau diinginkan)
    if str(settings.WHITELISTED_USERS).strip() == "*":
        logger.info("[AUTH] Whitelist='*' => allowing all users")
        return True

    try:
        # Parse WHITELISTED_USERS as comma-separated list or single number
        whitelist_str = str(settings.WHITELISTED_USERS).strip()
        if not whitelist_str:
            logger.warning("[AUTH] WHITELISTED_USERS is empty, denying access")
            return False
            
        allowed_ids = set()
        for x in whitelist_str.split(","):
            x = x.strip()
            if x:
                try:
                    allowed_ids.add(int(x))
                except ValueError as e:
                    logger.warning(f"[AUTH] Invalid user ID in whitelist: {x!r} - {e}")
        
        # Also check TELEGRAM_WHITELIST_IDS for compatibility
        if settings.TELEGRAM_WHITELIST_IDS:
            try:
                for x in settings.TELEGRAM_WHITELIST_IDS.split(","):
                    x = x.strip()
                    if x:
                        allowed_ids.add(int(x))
            except ValueError as e:
                logger.warning(f"[AUTH] Invalid user ID in TELEGRAM_WHITELIST_IDS: {x!r} - {e}")
        
        # Also check settings.whitelist_ids property
        allowed_ids.update(settings.whitelist_ids)
        
    except Exception as e:
        logger.error(f"[AUTH] Failed to parse WHITELISTED_USERS: {e}")
        return False

    allowed = user_id in allowed_ids
    logger.info(f"[AUTH] Allowed IDs={allowed_ids}, user {user_id} allowed={allowed}")
    return allowed


def is_owner(user_id: int) -> bool:
    """
    Check if a user is bot owner.
    
    Args:
        user_id (int): Telegram user ID to check
        
    Returns:
        bool: True if user is owner, False otherwise
    """
    # Check admin chat ID (might be string or int)
    try:
        admin_id = int(settings.TELEGRAM_ADMIN_CHAT_ID) if settings.TELEGRAM_ADMIN_CHAT_ID else 0
    except (ValueError, TypeError):
        admin_id = 0
    
    return user_id == admin_id


def log_access_attempt(user_id: int, username: str = None, command: str = None, allowed: bool = None):
    """
    Log access attempts for security monitoring.
    
    Args:
        user_id (int): Telegram user ID
        username (str, optional): Telegram username
        command (str, optional): Command being accessed
        allowed (bool, optional): Whether access was allowed (overrides check)
    """
    if allowed is None:
        allowed = is_user_allowed(user_id)
    
    user_info = f"user {user_id}"
    if username:
        user_info += f" (@{username})"
    if command:
        user_info += f" command: {command}"
    
    if allowed:
        logger.info(f"[AUTH] Access granted to {user_info}")
    else:
        logger.warning(f"[AUTH] Access denied for {user_info}")


def get_access_status_message() -> str:
    """
    Get a formatted message showing current access control status.
    
    Returns:
        str: Status message for logging
    """
    whitelist_str = str(settings.WHITELISTED_USERS).strip()
    admin_id = settings.TELEGRAM_ADMIN_CHAT_ID
    
    status = (
        f"[AUTH] Whitelist: {whitelist_str}, "
        f"admin: {admin_id}, "
        f"special_user_5899681906: always_allowed"
    )
    
    return status
