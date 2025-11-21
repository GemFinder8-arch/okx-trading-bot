#!/usr/bin/env python3
"""
Debug why real API data isn't showing in logs
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_data_flow():
    """Debug the data flow from API to logs."""
    
    print("🔍 DEBUGGING DATA FLOW: API → LOGS")
    print("=" * 60)
    
    try:
        from trading_bot.analytics.market_cap_analyzer import MarketCapAnalyzer
        
        analyzer = MarketCapAnalyzer()
        
        # Test the full flow for XTZ
        print("📊 TESTING FULL DATA FLOW FOR XTZ/USDT:")
        print()
        
        # Step 1: Test _fetch_market_data
        print("1. 🔍 Testing _fetch_market_data...")
        market_data = analyzer._fetch_market_data("XTZ/USDT")
        
        if market_data:
            print("   ✅ _fetch_market_data SUCCESS!")
            print(f"   Market Cap: ${market_data['market_cap']:,.0f}")
            print(f"   Rank: #{market_data['market_cap_rank']}")
        else:
            print("   ❌ _fetch_market_data FAILED!")
            print("   This is why we get fallback data!")
        
        print()
        
        # Step 2: Test full get_market_cap_data
        print("2. 📈 Testing get_market_cap_data...")
        result = analyzer.get_market_cap_data("XTZ/USDT")
        
        print(f"   Final Market Cap: ${result.market_cap:,.0f}")
        print(f"   Final Rank: #{result.market_cap_rank}")
        print(f"   Final Liquidity: {result.liquidity_score:.3f}")
        print(f"   Category: {result.market_cap_category}")
        
        # Check if this matches what we see in logs
        if result.market_cap == 597_384_729:
            print("   ❌ USING FALLBACK DATA!")
            print("   Real API data is not making it through")
        elif abs(result.market_cap - 600_920_801) < 10_000_000:
            print("   ✅ USING REAL API DATA!")
        else:
            print(f"   ⚠️ UNKNOWN DATA SOURCE: ${result.market_cap:,.0f}")
        
        print()
        
        # Step 3: Check liquidity calculation
        print("3. 💧 Testing liquidity calculation...")
        
        if result.liquidity_score in [0.5, 0.6, 1.0]:
            print(f"   ❌ PERFECT DECIMAL: {result.liquidity_score}")
            print("   Still using risk_profile values!")
        else:
            print(f"   ✅ GRANULAR VALUE: {result.liquidity_score}")
            print("   New logarithmic calculation working!")
        
        print()
        
        # Step 4: Test multiple symbols to see pattern
        print("4. 🔄 Testing multiple symbols...")
        
        test_symbols = ["XTZ/USDT", "FIL/USDT", "ADA/USDT"]
        
        for symbol in test_symbols:
            result = analyzer.get_market_cap_data(symbol)
            print(f"   {symbol}: ${result.market_cap:,.0f}, liquidity={result.liquidity_score:.3f}")
        
        print()
        
        # Step 5: Check if there's caching interfering
        print("5. 🗄️ Checking for caching issues...")
        
        # Force fresh data
        analyzer.cache = {}  # Clear any cache
        
        fresh_result = analyzer.get_market_cap_data("XTZ/USDT")
        print(f"   Fresh call: ${fresh_result.market_cap:,.0f}")
        
        if fresh_result.market_cap != result.market_cap:
            print("   ⚠️ CACHING AFFECTING RESULTS!")
        else:
            print("   ✅ Consistent results")
        
    except Exception as exc:
        print(f"❌ DEBUG ERROR: {exc}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 FINDINGS:")
    print("If APIs work but logs show fallback:")
    print("1. Error in _fetch_market_data flow")
    print("2. Exception handling catching real data")
    print("3. Symbol mapping issues")
    print("4. Caching old fallback data")
    print("5. Multi-threading race conditions")

if __name__ == "__main__":
    debug_data_flow()
