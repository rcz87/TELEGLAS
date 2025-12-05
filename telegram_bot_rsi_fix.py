#!/usr/bin/env python3
"""
Script to fix the RSI field extraction in telegram_bot.py
"""

import re

def fix_rsi_extraction():
    """Fix the RSI field extraction in telegram_bot.py"""
    
    # Read the current telegram_bot.py file
    with open('handlers/telegram_bot.py', 'r') as f:
        content = f.read()
    
    # Find and replace the wrong RSI extraction
    # Pattern to find the wrong RSI extraction lines
    wrong_pattern = r'rsi_1h_new = safe_get\(rsi_1h_4h_1d, [\'"]rsi_1h[\'"]\)'
    correct_replacement = 'rsi_1h_new = safe_get(rsi_1h_4h_1d, \'1h\')'
    
    content = re.sub(wrong_pattern, correct_replacement, content)
    
    wrong_pattern = r'rsi_4h_new = safe_get\(rsi_1h_4h_1d, [\'"]rsi_4h[\'"]\)'
    correct_replacement = 'rsi_4h_new = safe_get(rsi_1h_4h_1d, \'4h\')'
    
    content = re.sub(wrong_pattern, correct_replacement, content)
    
    wrong_pattern = r'rsi_1d_new = safe_get\(rsi_1h_4h_1d, [\'"]rsi_1d[\'"]\)'
    correct_replacement = 'rsi_1d_new = safe_get(rsi_1h_4h_1d, \'1d\')'
    
    content = re.sub(wrong_pattern, correct_replacement, content)
    
    # Write the fixed content back
    with open('handlers/telegram_bot.py', 'w') as f:
        f.write(content)
    
    print("✅ Fixed RSI field extraction in telegram_bot.py")
    print("Changed:")
    print("  rsi_1h_new = safe_get(rsi_1h_4h_1d, 'rsi_1h') → rsi_1h_new = safe_get(rsi_1h_4h_1d, '1h')")
    print("  rsi_4h_new = safe_get(rsi_1h_4h_1d, 'rsi_4h') → rsi_4h_new = safe_get(rsi_1h_4h_1d, '4h')")
    print("  rsi_1d_new = safe_get(rsi_1h_4h_1d, 'rsi_1d') → rsi_1d_new = safe_get(rsi_1h_4h_1d, '1d')")

if __name__ == "__main__":
    fix_rsi_extraction()
