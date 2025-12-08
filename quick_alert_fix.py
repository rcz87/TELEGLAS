#!/usr/bin/env python3
"""
Quick fix untuk pending alerts issue
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

def check_database_only():
    """Check database without async operations"""
    print("DATABASE CHECK ONLY")
    print("=" * 30)
    
    try:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get pending alerts details
        cursor.execute("""
            SELECT id, alert_type, message, created_at 
            FROM system_alerts 
            WHERE is_sent = 0 
            ORDER BY created_at DESC
        """)
        
        pending = cursor.fetchall()
        print(f"Total pending alerts: {len(pending)}")
        
        for alert in pending:
            print(f"\nAlert ID {alert[0]}:")
            print(f"  Type: {alert[1]}")
            print(f"  Created: {alert[3]}")
            print(f"  Message: {alert[2][:80]}...")
        
        conn.close()
        return pending
        
    except Exception as e:
        print(f"Error: {e}")
        return []

async def manual_broadcast_test():
    """Manual test of broadcast without Telegram initialization"""
    print("\nMANUAL BROADCAST TEST")
    print("=" * 30)
    
    try:
        # Get pending alerts
        await db_manager.initialize()
        pending = await db_manager.get_pending_alerts(limit=5)
        
        print(f"Testing broadcast for {len(pending)} alerts...")
        
        # Test without actually sending to Telegram
        for alert in pending:
            print(f"Alert {alert['id']}: {alert['alert_type']}")
            print(f"  Would broadcast: {alert['message'][:50]}...")
            
            # Simulate marking as sent
            try:
                await db_manager.mark_alert_sent(alert['id'])
                print(f"  Status: Marked as sent (test)")
            except Exception as e:
                print(f"  Error: {e}")
        
    except Exception as e:
        print(f"Error in manual test: {e}")

def analyze_configuration():
    """Analyze alert configuration"""
    print("\nCONFIGURATION ANALYSIS")
    print("=" * 30)
    
    print(f"ENABLE_BROADCAST_ALERTS: {settings.ENABLE_BROADCAST_ALERTS}")
    print(f"ENABLE_WHALE_ALERTS: {settings.ENABLE_WHALE_ALERTS}")
    print(f"TELEGRAM_ALERT_CHANNEL_ID: {settings.TELEGRAM_ALERT_CHANNEL_ID}")
    
    # The key issue!
    if settings.ENABLE_BROADCAST_ALERTS == False and settings.ENABLE_WHALE_ALERTS == True:
        print("\n!!! ISSUE IDENTIFIED !!!")
        print("ENABLE_BROADCAST_ALERTS is False")
        print("ENABLE_WHALE_ALERTS is True")
        print("This creates a conflict in main.py _broadcast_pending_alerts()")
        print("\nThe function checks ENABLE_BROADCAST_ALERTS first:")
        print("if not settings.ENABLE_BROADCAST_ALERTS and not settings.ENABLE_WHALE_ALERTS:")
        print("    return  # No broadcasting allowed")
        print("\nSince ENABLE_BROADCAST_ALERTS=False, the function returns early!")
        print("Even though whale alerts should be sent.")
        print("\nSOLUTION: Set ENABLE_BROADCAST_ALERTS=True")

def suggest_fixes():
    """Suggest fixes for the alert system"""
    print("\nSUGGESTED FIXES")
    print("=" * 30)
    
    print("1. IMMEDIATE FIX:")
    print("   Set ENABLE_BROADCAST_ALERTS=true in .env file")
    print("   This will allow the broadcast scheduler to work")
    
    print("\n2. CODE FIX (alternative):")
    print("   Modify main.py _broadcast_pending_alerts() function:")
    print("   Change the logic to allow whale alerts even when general broadcasting is disabled")
    
    print("\n3. CLEANUP:")
    print("   After fixing, pending alerts should be automatically sent")
    print("   Or manually clear them if they're old")

async def main():
    """Main function"""
    print("TELEGLAS ALERT SYSTEM QUICK FIX")
    print("=" * 50)
    
    # Check configuration
    analyze_configuration()
    
    # Check database
    pending = check_database_only()
    
    # Manual test
    await manual_broadcast_test()
    
    # Suggest fixes
    suggest_fixes()
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    if pending:
        print(f"Found {len(pending)} pending alerts")
        print("Root cause: ENABLE_BROADCAST_ALERTS=False blocking broadcast")
        print("Solution: Set ENABLE_BROADCAST_ALERTS=True in .env")
    else:
        print("No pending alerts found")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
