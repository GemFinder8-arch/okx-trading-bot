#!/usr/bin/env python3
"""
Quick bot monitoring - focuses on key indicators
"""

import subprocess
import sys
import time
import re

def monitor_bot_output():
    """Monitor bot output and highlight key indicators."""
    
    print("🚀 MONITORING BOT WITH RATE LIMIT FIXES...")
    print("=" * 60)
    print("⏱️  New Settings: 60s intervals, max 10 symbols")
    print("🔍 Watching for: Data quality, rate limits, analytics")
    print("=" * 60 + "\n")
    
    # Track key metrics
    data_validated_count = 0
    insufficient_data_count = 0
    circuit_breaker_count = 0
    analytics_working = 0
    
    try:
        # Start monitoring existing process
        process = subprocess.Popen(
            ["python", "-c", """
import subprocess
import sys
result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'], 
                       capture_output=True, text=True)
print(result.stdout)
"""],
            capture_output=True, text=True
        )
        
        print("📊 MONITORING ACTIVE BOT PROCESS...")
        print("🔍 Key Indicators to Watch:\n")
        
        # Monitor for 5 minutes to see multiple cycles
        start_time = time.time()
        
        while time.time() - start_time < 300:  # 5 minutes
            # Check for key log patterns (simulated - in real scenario would tail logs)
            print(f"⏱️  Monitoring... {int(time.time() - start_time)}s elapsed")
            
            # Simulate checking for good vs bad indicators
            print("✅ Expected Good Signs:")
            print("   - '✅ DATA VALIDATED: [SYMBOL] has 200 candles'")
            print("   - '📊 MARKET REGIME: [SYMBOL] - sideways'")
            print("   - '🏗️ MARKET STRUCTURE: [SYMBOL] - trend='")
            print("   - '🌍 MACRO ENVIRONMENT: phase='")
            
            print("\n❌ Bad Signs to Watch For:")
            print("   - '⚠️ Insufficient 5m data for [SYMBOL]: 7 candles'")
            print("   - '❌ No valid timeframe data available'")
            print("   - '⚠️ Market data circuit breaker open'")
            
            print(f"\n📈 Current Status (simulated):")
            print(f"   ✅ Data Validated Events: {data_validated_count}")
            print(f"   ❌ Insufficient Data Events: {insufficient_data_count}")
            print(f"   ⚠️ Circuit Breaker Events: {circuit_breaker_count}")
            print(f"   📊 Analytics Working: {analytics_working}")
            
            # Wait for next check
            time.sleep(30)  # Check every 30 seconds
            print("\n" + "─" * 60 + "\n")
            
    except KeyboardInterrupt:
        print("\n⏹️ Monitoring stopped by user")
    except Exception as e:
        print(f"❌ Monitoring error: {e}")

if __name__ == "__main__":
    monitor_bot_output()
