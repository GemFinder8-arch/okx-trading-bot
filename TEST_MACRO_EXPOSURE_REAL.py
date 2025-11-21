#!/usr/bin/env python3
"""
Test if macro exposure is actually dynamic or static at 0.10
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_bot.analytics.macro_factors import get_macro_factor_analyzer
import time

def test_macro_exposure():
    """Test macro exposure calculation with different scenarios."""
    
    print("🔍 TESTING MACRO EXPOSURE CALCULATION")
    print("=" * 60)
    
    # Get the macro analyzer
    macro_analyzer = get_macro_factor_analyzer()
    
    # Test multiple symbols to see if exposure varies
    test_symbols = ["BTC/USDT", "ETH/USDT", "ADA/USDT", "SOL/USDT", "XRP/USDT"]
    
    print("📊 Testing macro exposure for different symbols...")
    print()
    
    exposures = []
    
    for symbol in test_symbols:
        try:
            # Get macro environment for each symbol
            macro_env = macro_analyzer.get_current_macro_environment(symbol)
            
            print(f"🔍 {symbol}:")
            print(f"   Market Phase: {macro_env.market_phase}")
            print(f"   Crypto Sentiment: {macro_env.crypto_sentiment}")
            print(f"   Macro Risk Level: {macro_env.macro_risk_level}")
            print(f"   Recommended Exposure: {macro_env.recommended_exposure:.2f}")
            print()
            
            exposures.append(macro_env.recommended_exposure)
            
        except Exception as exc:
            print(f"❌ Error testing {symbol}: {exc}")
    
    # Analysis
    print("📊 ANALYSIS:")
    print(f"   Unique exposure values: {set(exposures)}")
    print(f"   All same value: {'YES' if len(set(exposures)) == 1 else 'NO'}")
    
    if len(set(exposures)) == 1:
        print(f"   ⚠️ STATIC VALUE DETECTED: All symbols return {exposures[0]}")
        print("   This suggests the calculation is not truly dynamic")
    else:
        print(f"   ✅ DYNAMIC VALUES: Different exposures found")
    
    # Test the calculation components
    print("\n🔍 TESTING CALCULATION COMPONENTS:")
    
    # Test with manual macro data
    try:
        # Simulate different market conditions
        test_scenarios = [
            {
                "name": "Bull Market",
                "market_phase": "risk_on",
                "dollar_strength": "weak", 
                "crypto_sentiment": "bullish",
                "funding_environment": "positive",
                "macro_risk_level": "low"
            },
            {
                "name": "Bear Market", 
                "market_phase": "risk_off",
                "dollar_strength": "strong",
                "crypto_sentiment": "bearish", 
                "funding_environment": "negative",
                "macro_risk_level": "high"
            },
            {
                "name": "Neutral Market",
                "market_phase": "neutral",
                "dollar_strength": "neutral",
                "crypto_sentiment": "neutral",
                "funding_environment": "neutral", 
                "macro_risk_level": "medium"
            }
        ]
        
        for scenario in test_scenarios:
            # Calculate exposure manually using the same logic
            base_exposure = 0.5  # 50% base
            
            # Market phase adjustment
            if scenario["market_phase"] == "risk_on":
                base_exposure += 0.2
            elif scenario["market_phase"] == "risk_off":
                base_exposure -= 0.3
            
            # Dollar strength adjustment
            if scenario["dollar_strength"] == "weak":
                base_exposure += 0.1
            elif scenario["dollar_strength"] == "strong":
                base_exposure -= 0.1
            
            # Crypto sentiment adjustment
            if scenario["crypto_sentiment"] == "bullish":
                base_exposure += 0.15
            elif scenario["crypto_sentiment"] == "bearish":
                base_exposure -= 0.15
            
            # Funding environment adjustment
            if scenario["funding_environment"] == "positive":
                base_exposure += 0.05
            elif scenario["funding_environment"] == "negative":
                base_exposure -= 0.05
            
            # Risk level adjustment
            if scenario["macro_risk_level"] == "high":
                base_exposure *= 0.8
            elif scenario["macro_risk_level"] == "medium":
                base_exposure *= 1.05
            elif scenario["macro_risk_level"] == "low":
                base_exposure *= 1.1
            
            # Clamp between 10% and 100%
            final_exposure = max(0.1, min(1.0, base_exposure))
            
            print(f"\n📊 {scenario['name']} Scenario:")
            print(f"   Market Phase: {scenario['market_phase']}")
            print(f"   Dollar Strength: {scenario['dollar_strength']}")
            print(f"   Crypto Sentiment: {scenario['crypto_sentiment']}")
            print(f"   Funding Environment: {scenario['funding_environment']}")
            print(f"   Macro Risk Level: {scenario['macro_risk_level']}")
            print(f"   Calculated Exposure: {final_exposure:.2f}")
            
    except Exception as exc:
        print(f"❌ Error in manual calculation: {exc}")
    
    print("\n" + "=" * 60)
    print("🎯 CONCLUSION:")
    
    if len(set(exposures)) == 1 and exposures[0] == 0.1:
        print("❌ MACRO EXPOSURE IS STATIC AT 0.10")
        print("   Likely causes:")
        print("   1. All macro inputs are returning the same values")
        print("   2. Calculation is being clamped to minimum (0.10)")
        print("   3. API data is not being fetched properly")
        print("   4. Hardcoded values in data sources")
    else:
        print("✅ MACRO EXPOSURE IS DYNAMIC")
        print("   Different symbols return different exposure values")

if __name__ == "__main__":
    test_macro_exposure()
