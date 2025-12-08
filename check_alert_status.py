#!/usr/bin/env python3
"""
Script untuk memeriksa status alert yang sedang berjalan di sistem TELEGLAS
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
from loguru import logger
import sqlite3
import json

async def check_database_alerts():
    """Periksa alert yang ada di database"""
    print("=== DATABASE ALERT STATUS ===")
    
    try:
        # Initialize database
        await db_manager.initialize()
        
        # Check pending alerts
        pending_alerts = await db_manager.get_pending_alerts(limit=50)
        
        if pending_alerts:
            print(f"✓ Found {len(pending_alerts)} pending alerts:")
            for alert in pending_alerts:
                print(f"  - ID: {alert['id']}")
                print(f"    Type: {alert['alert_type']}")
                print(f"    Created: {alert['created_at']}")
                print(f"    Message: {alert['message'][:100]}...")
                print()
        else:
            print("✓ No pending alerts found in database")
            
        return pending_alerts
        
    except Exception as e:
        print(f"✗ Error checking database alerts: {e}")
        return []

def check_database_direct():
    """Periksa database secara langsung untuk melihat semua tabel"""
    print("\n=== DIRECT DATABASE INSPECTION ===")
    
    try:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        print(f"Database path: {db_path}")
        
        if not os.path.exists(db_path):
            print("✗ Database file does not exist")
            return
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"✓ Database tables: {[table[0] for table in tables]}")
        
        # Check system_alerts table
        try:
            cursor.execute("SELECT COUNT(*) FROM system_alerts;")
            total_alerts = cursor.fetchone()[0]
            print(f"✓ Total alerts in database: {total_alerts}")
            
            cursor.execute("SELECT COUNT(*) FROM system_alerts WHERE is_sent = 0;")
            pending_alerts = cursor.fetchone()[0]
            print(f"✓ Pending alerts (not sent): {pending_alerts}")
            
            cursor.execute("SELECT COUNT(*) FROM system_alerts WHERE is_sent = 1;")
            sent_alerts = cursor.fetchone()[0]
            print(f"✓ Sent alerts: {sent_alerts}")
            
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
            print(f"✗ Error querying system_alerts: {e}")
            
        # Check user_subscriptions table
        try:
            cursor.execute("SELECT COUNT(*) FROM user_subscriptions WHERE is_active = 1;")
            active_subscriptions = cursor.fetchone()[0]
            print(f"✓ Active user subscriptions: {active_subscriptions}")
            
        except sqlite3.OperationalError:
            print("ℹ No user_subscriptions table found")
            
        conn.close()
        
    except Exception as e:
        print(f"✗ Error inspecting database: {e}")

def check_alert_configuration():
    """Periksa konfigurasi alert"""
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
            print("⚠ WARNING: Alerts enabled but no TELEGRAM_ALERT_CHANNEL_ID set")
        else:
            print("✓ Alert channel configured")
    else:
        print("ℹ All broadcasting is disabled")

def check_scheduler_status():
    """Periksa status scheduler berdasarkan log"""
    print("\n=== SCHEDULER STATUS ===")
    
    # Check if log file exists
    log_file = settings.LOG_FILE
    if os.path.exists(log_file):
        print(f"✓ Log file found: {log_file}")
        
        # Read recent log entries
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-20:]  # Last 20 lines
                
            print("\nRecent log entries:")
            for line in recent_lines:
                if any(keyword in line for keyword in ['broadcast', 'alert', 'scheduler', 'whale']):
                    print(f"  {line.strip()}")
                    
        except Exception as e:
            print(f"✗ Error reading log file: {e}")
    else:
        print(f"ℹ Log file not found: {log_file}")

async def test_alert_generation():
    """Test alert generation"""
    print("\n=== TEST ALERT GENERATION ===")
    
    try:
        # Test adding a test alert
        await db_manager.initialize()
        
        test_alert_data = {
            "symbol": "BTC",
            "amount_usd": 150000,
            "type": "test"
        }
        
        await db_manager.add_system_alert(
            alert_type="test",
            message="🧪 Test alert from check_alert_status.py",
            data=test_alert_data
        )
        
        print("✓ Test alert added successfully")
        
        # Check if it was added
        pending = await db_manager.get_pending_alerts(limit=10)
        test_alerts = [a for a in pending if a['alert_type'] == 'test']
        
        if test_alerts:
            print(f"✓ Test alert found in pending alerts: {test_alerts[0]['message']}")
        else:
            print("✗ Test alert not found in pending alerts")
            
    except Exception as e:
        print(f"✗ Error testing alert generation: {e}")

async def main():
    """Main function"""
    print("TELEGLAS Alert Status Check")
    print("=" * 50)
    
    # Check configuration
    check_alert_configuration()
    
    # Check database directly
    check_database_direct()
    
    # Check database alerts
    pending_alerts = await check_database_alerts()
    
    # Test alert generation
    await test_alert_generation()
    
    # Check scheduler status
    check_scheduler_status()
    
    print("\n" + "=" * 50)
    print("ALERT STATUS SUMMARY")
    print("=" * 50)
    
    if pending_alerts:
        print(f"⚠ {len(pending_alerts)} pending alerts found - these should be broadcast soon")
    else:
        print("✓ No pending alerts - system is up to date")
        
    if settings.ENABLE_BROADCAST_ALERTS or settings.ENABLE_WHALE_ALERTS:
        print("✓ Alert broadcasting is enabled")
        if settings.TELEGRAM_ALERT_CHANNEL_ID:
            print("✓ Alert channel is configured")
        else:
            print("⚠ WARNING: Alert channel not configured")
    else:
        print("ℹ Alert broadcasting is disabled in settings")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCheck interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
