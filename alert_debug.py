#!/usr/bin/env python3
"""
Debug script untuk menyelesaikan masalah pending alerts
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import db_manager
from config.settings import settings
import sqlite3

async def debug_pending_alerts():
    """Debug pending alerts yang tidak terkirim"""
    print("DEBUGGING PENDING ALERTS")
    print("=" * 50)
    
    try:
        # Initialize database
        await db_manager.initialize()
        
        # Get all pending alerts
        pending_alerts = await db_manager.get_pending_alerts(limit=50)
        
        print(f"Found {len(pending_alerts)} pending alerts:")
        
        for i, alert in enumerate(pending_alerts, 1):
            print(f"\nAlert {i}:")
            print(f"  ID: {alert['id']}")
            print(f"  Type: {alert['alert_type']}")
            print(f"  Created: {alert['created_at']}")
            print(f"  Message: {alert['message'][:100]}...")
            
            # Try to manually broadcast this alert
            print(f"  Status: Testing broadcast...")
            try:
                from handlers.telegram_bot import telegram_bot
                # Initialize telegram bot
                await telegram_bot.initialize()
                
                # Test broadcast
                success = await telegram_bot.broadcast_alert(alert['message'])
                if success:
                    print(f"  Result: SUCCESS - Alert sent to channel")
                    # Mark as sent
                    await db_manager.mark_alert_sent(alert['id'])
                    print(f"  Result: Alert marked as sent")
                else:
                    print(f"  Result: FAILED - Could not send alert")
                    
            except Exception as e:
                print(f"  Result: ERROR - {e}")
        
        # Check remaining pending alerts
        remaining_alerts = await db_manager.get_pending_alerts(limit=50)
        print(f"\nAfter testing: {len(remaining_alerts)} alerts still pending")
        
    except Exception as e:
        print(f"Error debugging alerts: {e}")
        import traceback
        traceback.print_exc()

async def test_broadcast_function():
    """Test broadcast function directly"""
    print("\n" + "=" * 50)
    print("TESTING BROADCAST FUNCTION")
    print("=" * 50)
    
    try:
        from handlers.telegram_bot import telegram_bot
        
        # Initialize
        await telegram_bot.initialize()
        
        # Test message
        test_message = "Test broadcast from alert_debug.py"
        print(f"Testing broadcast: {test_message}")
        
        # Try to broadcast
        success = await telegram_bot.broadcast_alert(test_message)
        
        if success:
            print("SUCCESS: Broadcast function works")
        else:
            print("FAILED: Broadcast function failed")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

async def check_telegram_connection():
    """Check Telegram bot connection"""
    print("\n" + "=" * 50)
    print("CHECKING TELEGRAM CONNECTION")
    print("=" * 50)
    
    try:
        from handlers.telegram_bot import telegram_bot
        
        # Initialize
        await telegram_bot.initialize()
        
        # Get bot info
        bot_info = await telegram_bot.get_bot_info()
        print(f"Bot info: {bot_info}")
        
        # Test channel access
        channel_id = settings.TELEGRAM_ALERT_CHANNEL_ID
        print(f"Testing channel access to: {channel_id}")
        
        # Try to send test message
        test_result = await telegram_bot.send_message(
            chat_id=channel_id,
            text="Connection test from alert_debug.py"
        )
        
        if test_result:
            print("SUCCESS: Can send messages to channel")
        else:
            print("FAILED: Cannot send messages to channel")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main debug function"""
    print("TELEGLAS ALERT SYSTEM DEBUG")
    print("=" * 50)
    
    print(f"ENABLE_BROADCAST_ALERTS: {settings.ENABLE_BROADCAST_ALERTS}")
    print(f"ENABLE_WHALE_ALERTS: {settings.ENABLE_WHALE_ALERTS}")
    print(f"TELEGRAM_ALERT_CHANNEL_ID: {settings.TELEGRAM_ALERT_CHANNEL_ID}")
    
    # Check Telegram connection first
    await check_telegram_connection()
    
    # Test broadcast function
    await test_broadcast_function()
    
    # Debug pending alerts
    await debug_pending_alerts()
    
    print("\n" + "=" * 50)
    print("DEBUG SUMMARY")
    print("=" * 50)
    print("If pending alerts remain after this debug,")
    print("the issue is likely in the broadcast scheduling,")
    print("not the alert generation or Telegram connection.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDebug interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
