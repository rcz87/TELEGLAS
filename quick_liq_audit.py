#!/usr/bin/env python3
"""
QUICK AUDIT FOR /liq COMMAND
============================

Quick version to avoid rate limiting and get immediate results.
"""

import asyncio
import json
import time
from datetime import datetime
import sys
sys.path.append('/opt/TELEGLAS/TELEGLAS')

from services.liquidation_monitor import liquidation_monitor
from services.coinglass_api import safe_float

async def quick_audit():
    """Quick audit of /liq command"""
    print("🔍 QUICK /liq COMMAND AUDIT")
    print("=" * 50)
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "tests": {}
    }
    
    # Test 1: Major symbols
    print("\n📊 Testing Major Symbols...")
    major_symbols = ["BTC", "ETH", "SOL"]
    major_results = []
    
    for symbol in major_symbols:
        try:
            start_time = time.time()
            data = await liquidation_monitor.get_symbol_liquidation_summary(symbol)
            response_time = time.time() - start_time
            
            if data:
                total_liq = safe_float(data.get("liquidation_usd", 0))
                long_liq = safe_float(data.get("long_liquidation_usd", 0))
                short_liq = safe_float(data.get("short_liquidation_usd", 0))
                
                # Check data quality
                has_data = total_liq > 0
                consistent = abs((long_liq + short_liq) - total_liq) <= total_liq * 0.1
                realistic = 0 < total_liq < 1_000_000_000
                
                result = {
                    "symbol": symbol,
                    "success": True,
                    "response_time": response_time,
                    "total_liquidation": total_liq,
                    "long_liquidation": long_liq,
                    "short_liquidation": short_liq,
                    "has_data": has_data,
                    "consistent": consistent,
                    "realistic": realistic,
                    "data_source": data.get("data_source", "unknown")
                }
                
                status = "✅" if (has_data and consistent and realistic) else "⚠️"
                print(f"   {status} {symbol}: ${total_liq:,.0f} ({response_time:.2f}s)")
                
            else:
                result = {
                    "symbol": symbol,
                    "success": False,
                    "response_time": response_time,
                    "error": "No data returned"
                }
                print(f"   ❌ {symbol}: No data")
            
            major_results.append(result)
            
        except Exception as e:
            print(f"   ❌ {symbol}: Error - {e}")
            major_results.append({
                "symbol": symbol,
                "success": False,
                "error": str(e)
            })
    
    results["tests"]["major_symbols"] = major_results
    
    # Test 2: Mid-cap symbols
    print("\n📈 Testing Mid-Cap Symbols...")
    mid_symbols = ["HYPE", "PONKE"]
    mid_results = []
    
    for symbol in mid_symbols:
        try:
            start_time = time.time()
            data = await liquidation_monitor.get_symbol_liquidation_summary(symbol)
            response_time = time.time() - start_time
            
            if data:
                total_liq = safe_float(data.get("liquidation_usd", 0))
                result = {
                    "symbol": symbol,
                    "success": True,
                    "response_time": response_time,
                    "total_liquidation": total_liq,
                    "has_data": total_liq > 0
                }
                
                status = "✅" if total_liq > 0 else "ℹ️"
                print(f"   {status} {symbol}: ${total_liq:,.0f} ({response_time:.2f}s)")
            else:
                result = {
                    "symbol": symbol,
                    "success": False,
                    "response_time": response_time,
                    "error": "No data returned"
                }
                print(f"   ❌ {symbol}: No data")
            
            mid_results.append(result)
            
        except Exception as e:
            print(f"   ❌ {symbol}: Error - {e}")
            mid_results.append({
                "symbol": symbol,
                "success": False,
                "error": str(e)
            })
    
    results["tests"]["mid_cap_symbols"] = mid_results
    
    # Test 3: Invalid symbols
    print("\n🎯 Testing Invalid Symbols...")
    invalid_symbols = ["INVALID123", "FAKECOIN"]
    invalid_results = []
    
    for symbol in invalid_symbols:
        try:
            start_time = time.time()
            data = await liquidation_monitor.get_symbol_liquidation_summary(symbol)
            response_time = time.time() - start_time
            
            # Should return zero data for invalid symbols
            handled_gracefully = (
                data is None or 
                (data and safe_float(data.get("liquidation_usd", 0)) == 0)
            )
            
            result = {
                "symbol": symbol,
                "success": handled_gracefully,
                "response_time": response_time,
                "handled_gracefully": handled_gracefully,
                "data_returned": data is not None
            }
            
            status = "✅" if handled_gracefully else "❌"
            print(f"   {status} {symbol}: {'Handled' if handled_gracefully else 'Not handled'}")
            
            invalid_results.append(result)
            
        except Exception as e:
            # Expected for invalid symbols
            expected_error = any(keyword in str(e).lower() for keyword in ["not supported", "invalid", "not found"])
            result = {
                "symbol": symbol,
                "success": expected_error,
                "expected_error": expected_error,
                "error": str(e)
            }
            
            status = "✅" if expected_error else "❌"
            print(f"   {status} {symbol}: Expected error - {e}")
            
            invalid_results.append(result)
    
    results["tests"]["invalid_symbols"] = invalid_results
    
    # Calculate summary
    major_success = sum(1 for r in major_results if r.get("success", False))
    major_total = len(major_results)
    mid_success = sum(1 for r in mid_results if r.get("success", False))
    mid_total = len(mid_results)
    invalid_success = sum(1 for r in invalid_results if r.get("success", False))
    invalid_total = len(invalid_results)
    
    overall_success_rate = (major_success + mid_success + invalid_success) / (major_total + mid_total + invalid_total)
    
    # Production readiness assessment
    critical_issues = []
    
    # Check major symbols
    if major_success < major_total:
        critical_issues.append("Major symbols not working")
    
    # Check data quality
    data_quality_issues = sum(1 for r in major_results if not (r.get("has_data", False) and r.get("consistent", True) and r.get("realistic", True)))
    if data_quality_issues > 0:
        critical_issues.append(f"Data quality issues in {data_quality_issues} major symbols")
    
    # Check invalid symbol handling
    if invalid_success < invalid_total:
        critical_issues.append("Invalid symbols not handled properly")
    
    # Determine readiness
    if overall_success_rate >= 0.9 and len(critical_issues) == 0:
        readiness = "PRODUCTION READY"
        emoji = "✅"
    elif overall_success_rate >= 0.75 and len(critical_issues) <= 1:
        readiness = "PRODUCTION READY WITH MINOR ISSUES"
        emoji = "⚠️"
    elif overall_success_rate >= 0.6:
        readiness = "NEEDS FIXES BEFORE PRODUCTION"
        emoji = "🔧"
    else:
        readiness = "NOT READY FOR PRODUCTION"
        emoji = "❌"
    
    results["summary"] = {
        "overall_success_rate": overall_success_rate,
        "major_symbols_success": major_success / major_total if major_total > 0 else 0,
        "mid_cap_success": mid_success / mid_total if mid_total > 0 else 0,
        "invalid_symbols_success": invalid_success / invalid_total if invalid_total > 0 else 0,
        "critical_issues": critical_issues,
        "readiness_level": readiness,
        "readiness_emoji": emoji
    }
    
    # Print summary
    print(f"\n📋 AUDIT SUMMARY")
    print("=" * 50)
    print(f"🎯 Overall Success Rate: {overall_success_rate:.1%}")
    print(f"📊 Major Symbols: {major_success}/{major_total} ({major_success/major_total:.1%})")
    print(f"📈 Mid-Cap Symbols: {mid_success}/{mid_total} ({mid_success/mid_total:.1%})")
    print(f"🎯 Invalid Symbols: {invalid_success}/{invalid_total} ({invalid_success/invalid_total:.1%})")
    print(f"\n{emoji} PRODUCTION READINESS: {readiness}")
    
    if critical_issues:
        print(f"\n⚠️  Critical Issues:")
        for issue in critical_issues:
            print(f"   • {issue}")
    else:
        print(f"\n✅ No critical issues found")
    
    # Save results
    report_file = f"/opt/TELEGLAS/TELEGLAS/QUICK_LIQ_AUDIT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    return results

if __name__ == "__main__":
    asyncio.run(quick_audit())
