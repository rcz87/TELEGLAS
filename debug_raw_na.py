#!/usr/bin/env python3
"""
Debug script to find where N/A appears in RAW output
"""
import asyncio
from dotenv import load_dotenv

load_dotenv()

from services.raw_data_service import raw_data_service

async def main():
    print("=== DEBUG RAW OUTPUT FOR N/A ===")
    
    # Get RAW data
    raw_data = await raw_data_service.get_comprehensive_market_data('BTC')
    raw_output = raw_data_service.format_for_telegram(raw_data)
    
    print("RAW OUTPUT (first 1000 chars):")
    print("-" * 50)
    print(raw_output[:1000])
    print("-" * 50)
    
    # Find lines with N/A
    lines = raw_output.split('\n')
    na_lines = []
    for i, line in enumerate(lines):
        if 'N/A' in line:
            na_lines.append(f"Line {i+1}: {line}")
    
    if na_lines:
        print(f"\nFound {len(na_lines)} lines with 'N/A':")
        for line in na_lines:
            print(f"  {line}")
    else:
        print("\nNo 'N/A' found in output")
    
    # Check raw data structure
    print(f"\nRaw data keys: {list(raw_data.keys())}")
    
    # Check specific fields that might have N/A
    potential_na_fields = ['support_resistance', 'orderbook_snapshot']
    for field in potential_na_fields:
        if field in raw_data:
            print(f"{field}: {raw_data[field]}")

if __name__ == "__main__":
    asyncio.run(main())
