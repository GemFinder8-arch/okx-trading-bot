#!/usr/bin/env python3
"""
Debug macro data fetching to see what actual values are returned
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_bot.analytics.macro_factors import get_macro_factor_analyzer
import requests

def debug_macro_data():
    """Debug what macro data is actually being fetched."""
    
    print("🔍 DEBUGGING MACRO DATA SOURCES")
    print("=" * 60)
    
    # Get the macro analyzer
    macro_analyzer = get_macro_factor_analyzer()
    
    print("📊 Testing individual data sources...")
    print()
    
    # Test Fear & Greed Index
    print("1. 🔍 FEAR & GREED INDEX:")
    try:
        fear_greed = macro_analyzer._fetch_fear_greed_index()
        print(f"   Result: {fear_greed}")
        if fear_greed:
            if fear_greed > 60:
                print("   → Should contribute to RISK_ON")
            elif fear_greed < 40:
                print("   → Should contribute to RISK_OFF")
            else:
                print("   → Should contribute to NEUTRAL")
        else:
            print("   → NULL - API failed")
    except Exception as exc:
        print(f"   ❌ Error: {exc}")
    
    print()
    
    # Test BTC Dominance
    print("2. 🔍 BTC DOMINANCE:")
    try:
        btc_dom = macro_analyzer._fetch_btc_dominance()
        print(f"   Result: {btc_dom}%")
        if btc_dom:
            if btc_dom > 48:
                print("   → Should contribute to RISK_OFF")
            elif btc_dom < 42:
                print("   → Should contribute to RISK_ON")
            else:
                print("   → Should contribute to NEUTRAL")
        else:
            print("   → NULL - API failed")
    except Exception as exc:
        print(f"   ❌ Error: {exc}")
    
    print()
    
    # Test DXY Index
    print("3. 🔍 DXY INDEX:")
    try:
        dxy = macro_analyzer._fetch_dxy_index()
        print(f"   Result: {dxy}")
        if dxy:
            if dxy > 106:
                print("   → Should contribute to RISK_OFF (strong dollar)")
            elif dxy < 102:
                print("   → Should contribute to RISK_ON (weak dollar)")
            else:
                print("   → Should contribute to NEUTRAL")
        else:
            print("   → NULL - API failed")
    except Exception as exc:
        print(f"   ❌ Error: {exc}")
    
    print()
    
    # Test Total Market Cap
    print("4. 🔍 TOTAL MARKET CAP:")
    try:
        market_cap = macro_analyzer._fetch_total_market_cap()
        print(f"   Result: ${market_cap:,.0f}" if market_cap else "NULL")
        if market_cap:
            if market_cap > 2_500_000_000_000:
                print("   → Should contribute to RISK_ON")
            elif market_cap < 2_000_000_000_000:
                print("   → Should contribute to RISK_OFF")
            else:
                print("   → Should contribute to NEUTRAL")
        else:
            print("   → NULL - API failed")
    except Exception as exc:
        print(f"   ❌ Error: {exc}")
    
    print()
    
    # Test Funding Rates
    print("5. 🔍 FUNDING RATES:")
    try:
        funding_rates = macro_analyzer._fetch_funding_rates()
        print(f"   Results: {funding_rates}")
        if funding_rates:
            avg_funding = sum(funding_rates.values()) / len(funding_rates)
            print(f"   Average: {avg_funding:.4f}")
            if avg_funding > 0.003:
                print("   → Should contribute to BEARISH sentiment")
            elif avg_funding < -0.001:
                print("   → Should contribute to BULLISH sentiment")
            else:
                print("   → Should contribute to NEUTRAL sentiment")
        else:
            print("   → Empty - API failed")
    except Exception as exc:
        print(f"   ❌ Error: {exc}")
    
    print()
    print("=" * 60)
    
    # Test the complete macro environment
    print("📊 COMPLETE MACRO ENVIRONMENT TEST:")
    try:
        macro_env = macro_analyzer.get_current_macro_environment("BTC/USDT")
        print(f"   Market Phase: {macro_env.market_phase}")
        print(f"   Dollar Strength: {macro_env.dollar_strength}")
        print(f"   Crypto Sentiment: {macro_env.crypto_sentiment}")
        print(f"   Funding Environment: {macro_env.funding_environment}")
        print(f"   Macro Risk Level: {macro_env.macro_risk_level}")
        print(f"   Recommended Exposure: {macro_env.recommended_exposure}")
        
        # Manual calculation check
        print(f"\n🔍 MANUAL CALCULATION CHECK:")
        base_exposure = 0.5
        print(f"   Base exposure: {base_exposure}")
        
        # Market phase adjustment
        if macro_env.market_phase == "risk_on":
            base_exposure += 0.2
            print(f"   + Risk ON: +0.2 = {base_exposure}")
        elif macro_env.market_phase == "risk_off":
            base_exposure -= 0.3
            print(f"   + Risk OFF: -0.3 = {base_exposure}")
        
        # Dollar strength adjustment
        if macro_env.dollar_strength == "weak":
            base_exposure += 0.1
            print(f"   + Weak dollar: +0.1 = {base_exposure}")
        elif macro_env.dollar_strength == "strong":
            base_exposure -= 0.1
            print(f"   + Strong dollar: -0.1 = {base_exposure}")
        
        # Crypto sentiment adjustment
        if macro_env.crypto_sentiment == "bullish":
            base_exposure += 0.15
            print(f"   + Bullish sentiment: +0.15 = {base_exposure}")
        elif macro_env.crypto_sentiment == "bearish":
            base_exposure -= 0.15
            print(f"   + Bearish sentiment: -0.15 = {base_exposure}")
        
        # Risk level adjustment
        if macro_env.macro_risk_level == "high":
            base_exposure *= 0.8
            print(f"   + High risk: *0.8 = {base_exposure}")
        elif macro_env.macro_risk_level == "medium":
            base_exposure *= 1.05
            print(f"   + Medium risk: *1.05 = {base_exposure}")
        elif macro_env.macro_risk_level == "low":
            base_exposure *= 1.1
            print(f"   + Low risk: *1.1 = {base_exposure}")
        
        # Final clamp
        final_exposure = max(0.1, min(1.0, base_exposure))
        print(f"   Final (clamped): {final_exposure}")
        
        if final_exposure == 0.1:
            print(f"   ⚠️ CLAMPED TO MINIMUM! Original would be: {base_exposure}")
        
    except Exception as exc:
        print(f"   ❌ Error: {exc}")
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSIS:")
    print("If all APIs return real data but exposure is still 0.10,")
    print("then the current market conditions are genuinely bearish")
    print("and the 0.10 result is mathematically correct.")

if __name__ == "__main__":
    debug_macro_data()
