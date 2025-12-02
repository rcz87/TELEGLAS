"""
Centralized authentication and access control for CryptoSat bot
"""
from typing import Set
from loguru import logger
from config.settings import settings


def get_allowed_user_ids() -> Set[int]:
    """
    Get all allowed user IDs based on configuration.
    Always includes the owner, plus whitelist if private mode is enabled.
    
    Returns:
        Set[int]: Set of allowed user IDs
    """
    # Always include owner
    ids = {settings.TELEGRAM_OWNER_ID}
    
    # Add whitelist users if configured
    if settings.TELEGRAM_WHITELIST_IDS:
        for part in settings.TELEGRAM_WHITELIST_IDS.split(","):
            part = part.strip()
            if part:
                try:
                    ids.add(int(part))
                except ValueError:
                    logger.warning(f"[AUTH] Invalid user id in TELEGRAM_WHITELIST_IDS: {part!r}")
    
    logger.debug(f"[AUTH] Allowed user IDs: {ids}")
    return ids


def is_user_allowed(user_id: int) -> bool:
    """
    Check if a user is allowed to access the bot.
    
    Args:
        user_id (int): Telegram user ID to check
        
    Returns:
        bool: True if user is allowed, False otherwise
    """
    # If bot is not private, everyone is allowed
    if not settings.TELEGRAM_PRIVATE_BOT:
        logger.debug(f"[AUTH] Public mode: allowing user {user_id}")
        return True
    
    # In private mode, check against allowed IDs
    allowed_ids = get_allowed_user_ids()
    is_allowed = user_id in allowed_ids
    
    if is_allowed:
        logger.debug(f"[AUTH] User {user_id} is allowed")
    else:
        logger.info(f"[AUTH] Access denied for user {user_id}")
    
    return is_allowed


def is_owner(user_id: int) -> bool:
    """
    Check if a user is the bot owner.
    
    Args:
        user_id (int): Telegram user ID to check
        
    Returns:
        bool: True if user is the owner, False otherwise
    """
    return user_id == settings.TELEGRAM_OWNER_ID


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
    allowed_ids = get_allowed_user_ids()
    
    status = (
        f"[AUTH] Private mode: {settings.TELEGRAM_PRIVATE_BOT}, "
        f"owner: {settings.TELEGRAM_OWNER_ID}, "
        f"whitelist: {allowed_ids}"
    )
    
    return status
