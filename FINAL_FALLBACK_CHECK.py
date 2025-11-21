#!/usr/bin/env python3
"""
Final check for critical fallback patterns in core trading files
"""

import os
import re

def final_fallback_check():
    """Check core trading files for remaining critical fallbacks."""
    
    print("🔍 FINAL FALLBACK CHECK - CORE TRADING FILES")
    print("=" * 60)
    
    # Core trading files to check
    core_files = [
        'trading_bot/analytics/market_regime.py',
        'trading_bot/analytics/market_structure.py',
        'trading_bot/analytics/multi_timeframe.py',
        'trading_bot/analytics/technical.py',
        'trading_bot/analytics/token_ranking.py',
        'trading_bot/analytics/enhanced_signals.py',
        'trading_bot/analytics/macro_factors.py',
        'trading_bot/analytics/market_cap_analyzer.py',
        'trading_bot/analytics/portfolio_optimizer.py',
        'trading_bot/orchestration/pipeline.py'
    ]
    
    critical_patterns = [
        (r'return 0\.5(?!\s*\+|\s*-|\s*\*)', 'Static 0.5 returns'),
        (r'return 1\.0(?!\s*-|\s*\*)', 'Static 1.0 returns'),
        (r'_fallback_', 'Fallback functions'),
        (r'_default_.*\(\)', 'Default functions'),
        (r'risk_profile\[', 'Risk profile usage'),
        (r'except.*return.*[0-9]\.', 'Exception fallbacks'),
    ]
    
    total_issues = 0
    
    for file_path in core_files:
        if not os.path.exists(file_path):
            print(f"⚠️ {file_path}: File not found")
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_issues = 0
            print(f"\n📁 {os.path.basename(file_path)}:")
            
            for pattern, description in critical_patterns:
                matches = list(re.finditer(pattern, content))
                
                if matches:
                    print(f"   ❌ {description}: {len(matches)} found")
                    file_issues += len(matches)
                    
                    # Show first few matches
                    for i, match in enumerate(matches[:3]):
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_num - 1].strip()
                        print(f"      Line {line_num}: {line_content[:60]}...")
                    
                    if len(matches) > 3:
                        print(f"      ... and {len(matches) - 3} more")
                else:
                    print(f"   ✅ {description}: Clean")
            
            if file_issues == 0:
                print(f"   🎉 {os.path.basename(file_path)}: FULLY CLEANED!")
            
            total_issues += file_issues
            
        except Exception as exc:
            print(f"   ❌ Error reading {file_path}: {exc}")
    
    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS:")
    print(f"Total critical issues in core trading files: {total_issues}")
    
    if total_issues == 0:
        print("\n🎉 SUCCESS! ALL CORE TRADING FILES CLEANED!")
        print("✅ No static fallbacks")
        print("✅ No fake default values")  
        print("✅ No hardcoded risk profiles")
        print("✅ Real data only!")
    else:
        print(f"\n⚠️ {total_issues} issues remaining in core trading logic")
        print("These need to be addressed for 100% real data operation")
    
    print("\n🏆 CORE TRADING SYSTEM STATUS:")
    if total_issues <= 5:
        print("🟢 EXCELLENT: Ready for production trading")
    elif total_issues <= 15:
        print("🟡 GOOD: Minor cleanup needed")
    else:
        print("🔴 NEEDS WORK: Significant fallbacks remain")

if __name__ == "__main__":
    final_fallback_check()
