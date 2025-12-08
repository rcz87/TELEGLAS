#!/usr/bin/env python3
"""
Simple debug to find N/A in RAW output without Unicode issues
"""
import asyncio
from dotenv import load_dotenv

load_dotenv()

from services.raw_data_service import raw_data_service

def clean_text(text):
    """Remove problematic Unicode characters"""
    return text.encode('ascii', 'ignore').decode('ascii')

async def main():
    print("=== DEBUG N/A IN RAW OUTPUT ===")
    
    # Get RAW data
    raw_data = await raw_data_service.get_comprehensive_market_data('BTC')
    
    # Check raw data structure first
    print(f"Raw data keys: {list(raw_data.keys())}")
    
    # Check specific fields that might have N/A
    print("\nChecking specific fields:")
    for key, value in raw_data.items():
        if isinstance(value, str) and 'N/A' in value:
            print(f"  {key}: {value}")
        elif isinstance(value, dict):
            for subkey, subval in value.items():
                if isinstance(subval, str) and 'N/A' in subval:
                    print(f"  {key}.{subkey}: {subval}")
    
    # Try to format and check line by line
    try:
        raw_output = raw_data_service.format_for_telegram(raw_data)
        lines = raw_output.split('\n')
        
        print(f"\nTotal lines: {len(lines)}")
        
        na_lines = []
        for i, line in enumerate(lines):
            if 'N/A' in line:
                na_lines.append((i+1, line))
        
        if na_lines:
            print(f"\nFound {len(na_lines)} lines with 'N/A':")
            for line_num, line in na_lines:
                print(f"  Line {line_num}: {clean_text(line)}")
        else:
            print("\nNo 'N/A' found in formatted output")
            
    except Exception as e:
        print(f"Error formatting: {e}")
        
        # Try to get output piece by piece
        try:
            # Check if CG levels has N/A
            if 'support_resistance' in raw_data:
                sr = raw_data['support_resistance']
                print(f"\nSupport/Resistance: {sr}")
                
        except Exception as e2:
            print(f"Error checking CG levels: {e2}")

if __name__ == "__main__":
    asyncio.run(main())
