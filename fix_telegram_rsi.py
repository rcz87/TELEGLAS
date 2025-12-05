#!/usr/bin/env python3
"""
Quick fix for Telegram bot RSI field extraction issue
"""

# Test the exact field names that should be used
import asyncio
from services.raw_data_service import raw_data_service

async def test_fix():
    """Test the fix for RSI field extraction"""
    
    symbol = "XRP"
    
    print("=" * 60)
    print(f"TESTING RSI FIELD FIX FOR: {symbol}")
    print("=" * 60)
    
    try:
        # Get comprehensive market data
        comprehensive_data = await raw_data_service.get_comprehensive_market_data(symbol)
        
        if "error" in comprehensive_data:
            print(f"❌ ERROR: {comprehensive_data['error']}")
            return
        
        # Test the CURRENT (wrong) extraction
        from services.coinglass_api import safe_get
        
        rsi_1h_4h_1d = safe_get(comprehensive_data, 'rsi_1h_4h_1d', {})
        rsi_1h_wrong = safe_get(rsi_1h_4h_1d, 'rsi_1h')  # WRONG
        rsi_4h_wrong = safe_get(rsi_1h_4h_1d, 'rsi_4h')  # WRONG  
        rsi_1d_wrong = safe_get(rsi_1h_4h_1d, 'rsi_1d')  # WRONG
        
        # Test the CORRECT extraction
        rsi_1h_correct = safe_get(rsi_1h_4h_1d, '1h')  # CORRECT
        rsi_4h_correct = safe_get(rsi_1h_4h_1d, '4h')  # CORRECT
        rsi_1d_correct = safe_get(rsi_1h_4h_1d, '1d')  # CORRECT
        
        print(f"RSI dict structure: {rsi_1h_4h_1d}")
        print(f"WRONG extraction (rsi_1h): {rsi_1h_wrong}")
        print(f"WRONG extraction (rsi_4h): {rsi_4h_wrong}")
        print(f"WRONG extraction (rsi_1d): {rsi_1d_wrong}")
        print(f"CORRECT extraction (1h): {rsi_1h_correct}")
        print(f"CORRECT extraction (4h): {rsi_4h_correct}")
        print(f"CORRECT extraction (1d): {rsi_1d_correct}")
        
        print("\n✅ FIX VERIFICATION:")
        print(f"  RSI 1h should be: {rsi_1h_correct}")
        print(f"  RSI 4h should be: {rsi_4h_correct}")
        print(f"  RSI 1d should be: {rsi_1d_correct}")
        
        if rsi_1h_correct and rsi_4h_correct and rsi_1d_correct:
            print("✅ All RSI values extracted correctly!")
        else:
            print("❌ RSI extraction still has issues")
        
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fix())
