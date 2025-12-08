#!/usr/bin/env python3
"""
Simple script untuk memeriksa status alert di sistem TELEGLAS
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

async def main():
    """Main function"""
    print("TELEGLAS Alert Status Check")
    print("=" * 50)
    
    # Check configuration
    print("\n=== ALERT CONFIGURATION ===")
    print(f"ENABLE_BROADCAST_ALERTS: {settings.ENABLE_BROADCAST_ALERTS}")
    print(f"ENABLE_WHALE_ALERTS: {settings.ENABLE_WHALE_ALERTS}")
    print(f"WHALE_TRANSACTION_THRESHOLD_USD: ${settings.WHALE_TRANSACTION_THRESHOLD_USD:,.0f}")
    print(f"LIQUIDATION_THRESHOLD_USD: ${settings.LIQUIDATION_THRESHOLD_USD:,.0f}")
    print(f"WHALE_POLL_INTERVAL: {settings.WHALE_POLL_INTERVAL} seconds")
    print(f"TELEGRAM_ALERT_CHANNEL_ID: {settings.TELEGRAM_ALERT_CHANNEL_ID}")
    
    # Check if required settings are present
    if settings.ENABLE_BROADCAST_ALERTS or settings.ENABLE_WHALE_ALERTS:
        if not settings.TELEGRAM_ALERT_CHANNEL_ID:
            print("WARNING: Alerts enabled but no TELEGRAM_ALERT_CHANNEL_ID set")
        else:
            print("OK: Alert channel configured")
    else:
        print("INFO: All broadcasting is disabled")
    
    # Check database directly
    print("\n=== DATABASE STATUS ===")
    
    try:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        print(f"Database path: {db_path}")
        
        if not os.path.exists(db_path):
            print("ERROR: Database file does not exist")
            return
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"OK: Database tables: {[table[0] for table in tables]}")
        
        # Check system_alerts table
        try:
            cursor.execute("SELECT COUNT(*) FROM system_alerts;")
            total_alerts = cursor.fetchone()[0]
            print(f"OK: Total alerts in database: {total_alerts}")
            
            cursor.execute("SELECT COUNT(*) FROM system_alerts WHERE is_sent = 0;")
            pending_alerts = cursor.fetchone()[0]
            print(f"OK: Pending alerts (not sent): {pending_alerts}")
            
            cursor.execute("SELECT COUNT(*) FROM system_alerts WHERE is_sent = 1;")
            sent_alerts = cursor.fetchone()[0]
            print(f"OK: Sent alerts: {sent_alerts}")
            
            # Show recent alerts
            cursor.execute("""
                SELECT alert_type, message, is_sent, created_at 
                FROM system_alerts 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            recent_alerts = cursor.fetchall()
            
            if recent_alerts:
                print("\nRecent alerts:")
                for alert in recent_alerts:
                    status = "SENT" if alert[2] else "PENDING"
                    print(f"  [{status}] {alert[0]}: {alert[1][:80]}...")
                    
        except sqlite3.OperationalError as e:
            print(f"ERROR: Querying system_alerts: {e}")
            
        # Check user_subscriptions table
        try:
            cursor.execute("SELECT COUNT(*) FROM user_subscriptions WHERE is_active = 1;")
            active_subscriptions = cursor.fetchone()[0]
            print(f"OK: Active user subscriptions: {active_subscriptions}")
            
        except sqlite3.OperationalError:
            print("INFO: No user_subscriptions table found")
            
        conn.close()
        
    except Exception as e:
        print(f"ERROR: Inspecting database: {e}")
    
    # Test alert generation
    print("\n=== TEST ALERT GENERATION ===")
    
    try:
        # Test adding a test alert
        await db_manager.initialize()
        
        await db_manager.add_system_alert(
            alert_type="test",
            message="Test alert from alert_status_simple.py",
            data={"test": True}
        )
        
        print("OK: Test alert added successfully")
        
        # Check if it was added
        pending = await db_manager.get_pending_alerts(limit=10)
        test_alerts = [a for a in pending if a['alert_type'] == 'test']
        
        if test_alerts:
            print(f"OK: Test alert found in pending alerts: {test_alerts[0]['message']}")
        else:
            print("ERROR: Test alert not found in pending alerts")
            
    except Exception as e:
        print(f"ERROR: Testing alert generation: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("ALERT STATUS SUMMARY")
    print("=" * 50)
    
    if settings.ENABLE_WHALE_ALERTS:
        print("STATUS: Whale alerts are ENABLED")
        if settings.TELEGRAM_ALERT_CHANNEL_ID:
            print("STATUS: Alert channel is configured")
            print("ACTION: System should broadcast whale alerts to channel")
        else:
            print("WARNING: Alert channel not configured - alerts won't be sent")
    else:
        print("STATUS: All alerts are DISABLED in settings")
    
    if settings.ENABLE_WHALE_ALERTS and settings.TELEGRAM_ALERT_CHANNEL_ID:
        print("\nEXPECTED BEHAVIOR:")
        print("- Whale watcher runs every 30 seconds")
        print("- When whale transactions > $500,000 are found")
        print("- Alerts are added to database")
        print("- Broadcast job runs every 30 seconds")
        print("- Pending alerts are sent to Telegram channel")
        print("- Alerts are marked as sent in database")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCheck interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
