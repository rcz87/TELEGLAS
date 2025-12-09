#!/usr/bin/env python3
"""
Debug message formatting issue
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ws_alert.alert_engine import alert_engine
from ws_alert.whale_cluster_detector import ClusterInfo

def main():
    print("Debug message formatting...")
    
    cluster = ClusterInfo(
        symbol='BTCUSDT',
        cluster_type='buy_cluster',
        total_buy_usd=3500000,
        total_sell_usd=500000,
        buy_count=5,
        sell_count=2,
        dominant_side='BUY',
        dominance_ratio=0.875,
        window=30,
        timestamp=time.time()
    )

    message = alert_engine.format_whale_cluster_message(cluster)
    print('Formatted message:')
    print(message)
    print()
    print('Checking for specific elements:')
    print(f'Contains $5.0M: {"$5.0M" in message}')
    print(f'Contains $4.0M: {"$4.0M" in message}')
    print(f'Total volume: ${(cluster.total_buy_usd + cluster.total_sell_usd)/1000000:.1f}M')

if __name__ == "__main__":
    main()
