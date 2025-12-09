#!/usr/bin/env python3
"""
Debug SELL cluster detection issue
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ws_alert.event_aggregator import get_event_aggregator
from ws_alert.whale_cluster_detector import get_whale_cluster_detector

def main():
    print("Debug SELL cluster detection...")
    
    aggregator = get_event_aggregator()
    detector = get_whale_cluster_detector()

    # Clear aggregator
    aggregator.clear_old_events(0)
    detector.reset_cooldown('ETHUSDT')

    # Create SELL trades
    trades = [
        {'symbol': 'ETHUSDT', 'side': 2, 'price': 3500, 'volUsd': 800000, 'exName': 'Binance', 'time': int(time.time() * 1000), 'timestamp': time.time()},
        {'symbol': 'ETHUSDT', 'side': 2, 'price': 3480, 'volUsd': 700000, 'exName': 'Binance', 'time': int(time.time() * 1000), 'timestamp': time.time()},
        {'symbol': 'ETHUSDT', 'side': 2, 'price': 3520, 'volUsd': 600000, 'exName': 'Binance', 'time': int(time.time() * 1000), 'timestamp': time.time()},
        {'symbol': 'ETHUSDT', 'side': 1, 'price': 3490, 'volUsd': 300000, 'exName': 'Binance', 'time': int(time.time() * 1000), 'timestamp': time.time()},
    ]

    for trade in trades:
        aggregator.add_trade_event(trade)

    # Check window
    window = aggregator.get_trade_window('ETHUSDT', 30)
    print(f'Trades in window: {len(window)}')
    for w in window:
        print(f'  Side {w["side"]}: ${w["volUsd"]:,.0f}')

    # Get threshold info
    threshold_config = detector.get_cluster_threshold('ETHUSDT')
    print(f'ETHUSDT threshold: {threshold_config}')
    
    # Check cluster
    cluster = detector.check_cluster('ETHUSDT')
    if cluster:
        print(f'Cluster detected: {cluster.dominant_side} ${cluster.total_buy_usd:,.0f} BUY vs ${cluster.total_sell_usd:,.0f} SELL ({cluster.dominance_ratio:.1%})')
    else:
        print('No cluster detected')

if __name__ == "__main__":
    main()
