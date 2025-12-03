"""
Centralized authentication and access control for CryptoSat bot
"""
from typing import Set
from loguru import logger
from config.settings import settings


def is_user_allowed(user_id: int) -> bool:
    """
    Check if a user is allowed to access the bot based on WHITELISTED_USERS configuration.
    
    Args:
        user_id (int): Telegram user ID to check
        
    Returns:
        bool: True if user is allowed, False otherwise
    """
    logger.info(f"[AUTH] Checking user {user_id}, WHITELISTED_USERS={settings.WHITELISTED_USERS!r}")

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
            
        allowed_ids = [
            int(x.strip()) for x in whitelist_str.split(",") if x.strip()
        ]
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
    return user_id == settings.TELEGRAM_ADMIN_CHAT_ID


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
    
    status = (
        f"[AUTH] Whitelist: {whitelist_str}, "
        f"admin: {settings.TELEGRAM_ADMIN_CHAT_ID}"
    )
    
    return status
