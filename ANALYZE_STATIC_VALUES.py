#!/usr/bin/env python3
"""
Analyze the bot logs for static/fake values that should be dynamic
"""

import re
from collections import Counter

def analyze_log_patterns():
    """Analyze log patterns for static values."""
    
    print("🔍 ANALYZING LOG PATTERNS FOR STATIC/FAKE VALUES")
    print("=" * 60)
    
    # Sample log data from the terminal
    log_lines = [
        "📊 MARKET REGIME: XTZ/USDT - sideways (strength=0.98, volatility=0.07) [200 candles]",
        "📊 MARKET REGIME: FIL/USDT - sideways (strength=0.96, volatility=0.11) [200 candles]", 
        "📊 MARKET REGIME: ADA/USDT - sideways (strength=0.97, volatility=0.07) [200 candles]",
        "🌍 MACRO ENVIRONMENT: phase=risk_off, sentiment=bearish, risk=high, exposure=0.10",
        "🌍 MACRO ENVIRONMENT: phase=risk_off, sentiment=bearish, risk=high, exposure=0.10",
        "🌍 MACRO ENVIRONMENT: phase=risk_off, sentiment=bearish, risk=high, exposure=0.10",
        "⚙️ OPTIMAL PARAMS: confidence_threshold=0.65, rsi_period=21, stop_loss_mult=1.07",
        "⚙️ OPTIMAL PARAMS: confidence_threshold=0.60, rsi_period=21, stop_loss_mult=1.11",
        "⚙️ OPTIMAL PARAMS: confidence_threshold=0.60, rsi_period=21, stop_loss_mult=1.07",
        "🏗️ MARKET STRUCTURE: XTZ/USDT - trend=sideways, smart_money=neutral, strength=0.80",
        "🏗️ MARKET STRUCTURE: FIL/USDT - trend=lower_highs_lows, smart_money=bearish, strength=1.00",
        "🏗️ MARKET STRUCTURE: ADA/USDT - trend=sideways, smart_money=neutral, strength=0.70",
        "💰 MARKET CAP ANALYSIS XTZ/USDT: category=small, cap=$597M, rank=#144, liquidity=0.60",
        "💰 MARKET CAP ANALYSIS FIL/USDT: category=small, cap=$500M, rank=#100, liquidity=0.50",
        "💰 MARKET CAP ANALYSIS ADA/USDT: category=large, cap=$18972M, rank=#11, liquidity=1.00",
        "📊 MULTI-TF SYNTHESIS XTZ/USDT: trend=bearish, confluence=0.50, confidence=0.85, risk=high",
        "📊 MULTI-TF SYNTHESIS FIL/USDT: trend=bearish, confluence=0.50, confidence=0.89, risk=high",
        "📊 MULTI-TF SYNTHESIS ADA/USDT: trend=bearish, confluence=0.44, confidence=0.85, risk=low",
        "✅ DATA VALIDATED: XTZ/USDT has 200 candles - PROCEEDING WITH ADVANCED ANALYTICS",
        "✅ DATA VALIDATED: FIL/USDT has 200 candles - PROCEEDING WITH ADVANCED ANALYTICS",
        "✅ DATA VALIDATED: ADA/USDT has 200 candles - PROCEEDING WITH ADVANCED ANALYTICS"
    ]
    
    print("🔍 SUSPICIOUS PATTERNS ANALYSIS:")
    print()
    
    # 1. Check for repeated identical values
    print("1. 📊 MACRO ENVIRONMENT VALUES:")
    macro_values = []
    for line in log_lines:
        if "MACRO ENVIRONMENT:" in line:
            macro_values.append(line.split("MACRO ENVIRONMENT: ")[1])
    
    unique_macro = set(macro_values)
    print(f"   Total macro entries: {len(macro_values)}")
    print(f"   Unique macro values: {len(unique_macro)}")
    
    if len(unique_macro) == 1:
        print(f"   ⚠️ SUSPICIOUS: All macro environments identical")
        print(f"   Value: {list(unique_macro)[0]}")
    else:
        print(f"   ✅ DYNAMIC: Multiple different macro environments")
    
    print()
    
    # 2. Check candle counts
    print("2. 📊 CANDLE COUNTS:")
    candle_counts = []
    for line in log_lines:
        if "has 200 candles" in line:
            candle_counts.append("200")
        elif " candles]" in line:
            match = re.search(r'\[(\d+) candles\]', line)
            if match:
                candle_counts.append(match.group(1))
    
    candle_counter = Counter(candle_counts)
    print(f"   Candle count distribution: {dict(candle_counter)}")
    
    if len(candle_counter) == 1 and "200" in candle_counter:
        print(f"   ⚠️ SUSPICIOUS: All symbols have exactly 200 candles")
        print(f"   This could indicate:")
        print(f"     - API limit set to 200")
        print(f"     - Static data source")
        print(f"     - Hardcoded limit")
    else:
        print(f"   ✅ VARIES: Different candle counts found")
    
    print()
    
    # 3. Check RSI periods
    print("3. ⚙️ RSI PERIODS:")
    rsi_periods = []
    for line in log_lines:
        if "rsi_period=" in line:
            match = re.search(r'rsi_period=(\d+)', line)
            if match:
                rsi_periods.append(match.group(1))
    
    rsi_counter = Counter(rsi_periods)
    print(f"   RSI period distribution: {dict(rsi_counter)}")
    
    if len(rsi_counter) == 1:
        print(f"   ⚠️ SUSPICIOUS: All symbols use same RSI period ({list(rsi_counter.keys())[0]})")
        print(f"   Should vary based on market regime")
    else:
        print(f"   ✅ DYNAMIC: Multiple RSI periods used")
    
    print()
    
    # 4. Check confluence values
    print("4. 📊 TREND CONFLUENCE:")
    confluence_values = []
    for line in log_lines:
        if "confluence=" in line:
            match = re.search(r'confluence=([0-9.]+)', line)
            if match:
                confluence_values.append(float(match.group(1)))
    
    unique_confluence = set(confluence_values)
    print(f"   Confluence values found: {sorted(unique_confluence)}")
    
    # Check for suspicious patterns
    if 0.50 in confluence_values and confluence_values.count(0.50) > len(confluence_values) * 0.5:
        print(f"   ⚠️ SUSPICIOUS: Too many 0.50 values (50% of entries)")
        print(f"   This suggests default/fallback values being used")
    else:
        print(f"   ✅ VARIES: Good distribution of confluence values")
    
    print()
    
    # 5. Check market cap categories
    print("5. 💰 MARKET CAP CATEGORIES:")
    market_caps = []
    for line in log_lines:
        if "cap=$" in line:
            match = re.search(r'cap=\$([0-9M]+)', line)
            if match:
                market_caps.append(match.group(1))
    
    print(f"   Market caps found: {market_caps}")
    
    # Check for suspicious round numbers
    suspicious_caps = ["500M", "1000M", "2000M", "5000M"]
    found_suspicious = [cap for cap in market_caps if cap in suspicious_caps]
    
    if found_suspicious:
        print(f"   ⚠️ SUSPICIOUS: Round number market caps found: {found_suspicious}")
        print(f"   Real market caps are rarely exact round numbers")
    else:
        print(f"   ✅ REALISTIC: Market caps appear to be real values")
    
    print()
    
    # 6. Check for hardcoded liquidity values
    print("6. 💧 LIQUIDITY SCORES:")
    liquidity_values = []
    for line in log_lines:
        if "liquidity=" in line:
            match = re.search(r'liquidity=([0-9.]+)', line)
            if match:
                liquidity_values.append(float(match.group(1)))
    
    liquidity_counter = Counter(liquidity_values)
    print(f"   Liquidity distribution: {dict(liquidity_counter)}")
    
    # Check for too many round numbers (0.5, 0.6, 1.0, etc.)
    round_values = [v for v in liquidity_values if v in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]]
    if len(round_values) > len(liquidity_values) * 0.8:
        print(f"   ⚠️ SUSPICIOUS: {len(round_values)}/{len(liquidity_values)} values are round numbers")
        print(f"   Real liquidity scores should be more varied")
    else:
        print(f"   ✅ REALISTIC: Good mix of liquidity values")
    
    print()
    print("=" * 60)
    print("🎯 SUMMARY OF FINDINGS:")
    
    # Generate summary
    issues_found = []
    
    if len(unique_macro) == 1:
        issues_found.append("All macro environments identical")
    
    if len(candle_counter) == 1 and "200" in candle_counter:
        issues_found.append("All symbols have exactly 200 candles")
    
    if len(rsi_counter) == 1:
        issues_found.append("All RSI periods identical")
    
    if 0.50 in confluence_values and confluence_values.count(0.50) > len(confluence_values) * 0.5:
        issues_found.append("Too many 0.50 confluence values")
    
    if found_suspicious:
        issues_found.append("Round number market caps detected")
    
    round_liquidity = [v for v in liquidity_values if v in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]]
    if len(round_liquidity) > len(liquidity_values) * 0.8:
        issues_found.append("Too many round liquidity values")
    
    if issues_found:
        print("❌ ISSUES DETECTED:")
        for issue in issues_found:
            print(f"   • {issue}")
        print()
        print("🔧 RECOMMENDATIONS:")
        print("   1. Check if APIs are returning real data")
        print("   2. Verify calculation logic for dynamic values")
        print("   3. Add more randomness/variation to fallback values")
        print("   4. Ensure market-specific calculations")
    else:
        print("✅ NO MAJOR ISSUES DETECTED")
        print("   Values appear to be reasonably dynamic")

if __name__ == "__main__":
    analyze_log_patterns()
