#!/usr/bin/env python3
"""
Test API connectivity to see why we're getting fallback data
"""

import requests
import json

def test_coingecko_api():
    """Test CoinGecko API connectivity."""
    
    print("🔍 TESTING COINGECKO API CONNECTIVITY")
    print("=" * 60)
    
    try:
        # Test Tezos API call
        print("📡 Testing: https://api.coingecko.com/api/v3/coins/tezos")
        
        response = requests.get("https://api.coingecko.com/api/v3/coins/tezos", timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract key data
            market_data = data.get("market_data", {})
            market_cap = market_data.get("market_cap", {}).get("usd", 0)
            rank = data.get("market_cap_rank", 999)
            price = market_data.get("current_price", {}).get("usd", 0)
            
            print("✅ API WORKING! Real data received:")
            print(f"   Market Cap: ${market_cap:,.0f}")
            print(f"   Rank: #{rank}")
            print(f"   Price: ${price:.6f}")
            
            # Compare with our fallback
            print(f"\n🔍 COMPARISON WITH FALLBACK:")
            print(f"   Real API: ${market_cap:,.0f}")
            print(f"   Our Fallback: $597,384,729")
            
            if abs(market_cap - 597_384_729) > 100_000_000:
                print("   ❌ MAJOR DIFFERENCE - API has different data!")
            else:
                print("   ✅ Similar values")
                
        elif response.status_code == 429:
            print("❌ RATE LIMITED!")
            print("   CoinGecko is blocking our requests")
            print("   This explains why we're getting fallback data")
            
        else:
            print(f"❌ API ERROR: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT!")
        print("   API is too slow, bot falling back to hardcoded data")
        
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR!")
        print("   No internet or API is down")
        
    except Exception as exc:
        print(f"❌ UNEXPECTED ERROR: {exc}")

def test_okx_candles():
    """Test OKX candle data to see why we get exactly 200."""
    
    print("\n" + "=" * 60)
    print("🔍 TESTING OKX CANDLE DATA")
    print("=" * 60)
    
    try:
        # Test OKX API (public endpoint)
        url = "https://www.okx.com/api/v5/market/candles?instId=XTZ-USDT&bar=1m&limit=300"
        print(f"📡 Testing: {url}")
        
        response = requests.get(url, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("code") == "0":
                candles = data.get("data", [])
                print(f"✅ OKX API WORKING! Received {len(candles)} candles")
                
                if len(candles) == 200:
                    print("   ⚠️ EXACTLY 200 CANDLES - This explains the logs!")
                    print("   OKX might be limiting to 200 despite our 300 request")
                elif len(candles) == 300:
                    print("   ✅ Got 300 candles as requested")
                else:
                    print(f"   📊 Got {len(candles)} candles (varies by availability)")
                    
            else:
                print(f"❌ OKX API ERROR: {data}")
                
        else:
            print(f"❌ HTTP ERROR: {response.status_code}")
            
    except Exception as exc:
        print(f"❌ OKX API ERROR: {exc}")

def test_bot_market_cap_call():
    """Test the actual bot's market cap analyzer."""
    
    print("\n" + "=" * 60)
    print("🔍 TESTING BOT'S MARKET CAP ANALYZER")
    print("=" * 60)
    
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        from trading_bot.analytics.market_cap_analyzer import MarketCapAnalyzer
        
        analyzer = MarketCapAnalyzer()
        
        # Test with XTZ
        print("📊 Testing bot's analyzer with XTZ/USDT...")
        
        result = analyzer._fetch_from_coingecko("XTZ")
        
        if result:
            print("✅ BOT'S COINGECKO CALL WORKING!")
            print(f"   Market Cap: ${result['market_cap']:,.0f}")
            print(f"   Rank: #{result['market_cap_rank']}")
        else:
            print("❌ BOT'S COINGECKO CALL FAILED!")
            print("   This is why we're getting fallback data")
            
            # Test the fallback
            fallback = analyzer._get_fallback_data("XTZ/USDT")
            print(f"\n📋 FALLBACK DATA:")
            print(f"   Market Cap: ${fallback.market_cap:,.0f}")
            print(f"   Liquidity: {fallback.liquidity_score}")
            print(f"   Rank: #{fallback.market_cap_rank}")
            
    except Exception as exc:
        print(f"❌ BOT TEST ERROR: {exc}")

if __name__ == "__main__":
    test_coingecko_api()
    test_okx_candles()
    test_bot_market_cap_call()
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSIS SUMMARY:")
    print("If APIs are working but bot uses fallback, then:")
    print("1. Bot has API connectivity issues")
    print("2. Rate limiting is blocking requests")
    print("3. Error handling is too aggressive")
    print("4. Timeouts are too short")
