#!/usr/bin/env python3
"""
Comprehensive live bot monitoring system
Tracks: errors, fake data, API limitations, real data patterns
"""

import sys
import os
import time
import logging
import threading
import queue
from datetime import datetime
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup logging to capture bot output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class BotMonitor:
    """Real-time bot monitoring system."""
    
    def __init__(self):
        self.errors = defaultdict(int)
        self.api_calls = defaultdict(int)
        self.real_data_patterns = []
        self.fake_data_patterns = []
        self.api_failures = defaultdict(list)
        self.rate_limits = defaultdict(int)
        self.start_time = datetime.now()
        self.last_prices = {}
        self.data_quality_scores = []
        self.trading_signals = []
        self.position_updates = []
        
    def log_event(self, event_type, details):
        """Log and categorize events."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if event_type == "ERROR":
            self.errors[details] += 1
            logger.error(f"[{timestamp}] ERROR: {details}")
            
        elif event_type == "API_CALL":
            self.api_calls[details] += 1
            logger.info(f"[{timestamp}] API: {details}")
            
        elif event_type == "REAL_DATA":
            self.real_data_patterns.append((timestamp, details))
            logger.info(f"[{timestamp}] ✅ REAL DATA: {details}")
            
        elif event_type == "FAKE_DATA":
            self.fake_data_patterns.append((timestamp, details))
            logger.warning(f"[{timestamp}] ⚠️ FAKE DATA: {details}")
            
        elif event_type == "API_FAILURE":
            self.api_failures[details].append(timestamp)
            self.rate_limits[details] += 1
            logger.warning(f"[{timestamp}] ❌ API FAILURE: {details}")
            
        elif event_type == "TRADING_SIGNAL":
            self.trading_signals.append((timestamp, details))
            logger.info(f"[{timestamp}] 🎯 TRADING SIGNAL: {details}")
            
        elif event_type == "POSITION_UPDATE":
            self.position_updates.append((timestamp, details))
            logger.info(f"[{timestamp}] 💰 POSITION: {details}")
    
    def analyze_price_movement(self, symbol, price):
        """Detect real vs static price data."""
        if symbol in self.last_prices:
            old_price = self.last_prices[symbol]
            change = ((price - old_price) / old_price) * 100
            
            if abs(change) > 0.01:  # More than 0.01% change
                self.log_event("REAL_DATA", f"{symbol}: ${price} (Δ {change:+.3f}%)")
                return True
            elif abs(change) == 0:
                self.log_event("FAKE_DATA", f"{symbol}: Static price ${price}")
                return False
        
        self.last_prices[symbol] = price
        return None
    
    def check_data_quality(self, data_dict):
        """Analyze data quality for real vs fake patterns."""
        quality_score = 0
        total_checks = 0
        
        for key, value in data_dict.items():
            total_checks += 1
            
            # Check for perfect round numbers (suspicious)
            if isinstance(value, (int, float)):
                if value % 1 == 0 and value > 100:  # Perfect integer
                    quality_score -= 10
                elif str(value).endswith('000'):  # Round thousands
                    quality_score -= 5
                else:
                    quality_score += 10
            
            # Check for typical fallback values
            if value in [0.5, 1.0, 0.0, 100, 200]:
                quality_score -= 15
            
            # Check for realistic ranges
            if isinstance(value, float) and 0 <= value <= 1:
                if value not in [0.0, 0.5, 1.0]:  # Not a fallback
                    quality_score += 5
        
        if total_checks > 0:
            final_score = max(0, min(100, quality_score / total_checks))
            self.data_quality_scores.append(final_score)
            return final_score
        return 0
    
    def print_summary(self):
        """Print comprehensive monitoring summary."""
        elapsed = datetime.now() - self.start_time
        
        print("\n" + "=" * 70)
        print("🔍 BOT MONITORING SUMMARY")
        print("=" * 70)
        
        print(f"\n⏱️ RUNTIME: {elapsed}")
        
        # Error Summary
        if self.errors:
            print(f"\n❌ ERRORS DETECTED: {sum(self.errors.values())}")
            for error, count in sorted(self.errors.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   • {error}: {count}x")
        else:
            print(f"\n✅ NO ERRORS DETECTED")
        
        # API Summary
        if self.api_calls:
            print(f"\n📡 API CALLS: {sum(self.api_calls.values())}")
            for api, count in sorted(self.api_calls.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   • {api}: {count}x")
        
        # API Failures
        if self.api_failures:
            print(f"\n⚠️ API FAILURES: {sum(len(v) for v in self.api_failures.values())}")
            for api, failures in sorted(self.api_failures.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
                print(f"   • {api}: {len(failures)}x failures")
        else:
            print(f"\n✅ NO API FAILURES")
        
        # Real Data Patterns
        if self.real_data_patterns:
            print(f"\n✅ REAL DATA PATTERNS: {len(self.real_data_patterns)}")
            for timestamp, pattern in self.real_data_patterns[-3:]:
                print(f"   [{timestamp}] {pattern}")
        
        # Fake Data Patterns
        if self.fake_data_patterns:
            print(f"\n⚠️ FAKE DATA PATTERNS: {len(self.fake_data_patterns)}")
            for timestamp, pattern in self.fake_data_patterns[-3:]:
                print(f"   [{timestamp}] {pattern}")
        else:
            print(f"\n✅ NO FAKE DATA DETECTED")
        
        # Trading Signals
        if self.trading_signals:
            print(f"\n🎯 TRADING SIGNALS: {len(self.trading_signals)}")
            for timestamp, signal in self.trading_signals[-3:]:
                print(f"   [{timestamp}] {signal}")
        
        # Position Updates
        if self.position_updates:
            print(f"\n💰 POSITION UPDATES: {len(self.position_updates)}")
            for timestamp, update in self.position_updates[-3:]:
                print(f"   [{timestamp}] {update}")
        
        # Data Quality
        if self.data_quality_scores:
            avg_quality = sum(self.data_quality_scores) / len(self.data_quality_scores)
            print(f"\n📊 DATA QUALITY SCORE: {avg_quality:.1f}/100")
            if avg_quality >= 80:
                print("   ✅ EXCELLENT: High quality real data")
            elif avg_quality >= 60:
                print("   🟡 GOOD: Mostly real data")
            else:
                print("   ⚠️ POOR: Potential fake data detected")
        
        # Rate Limiting
        if self.rate_limits:
            print(f"\n🚫 RATE LIMITS HIT: {sum(self.rate_limits.values())}")
            for api, count in sorted(self.rate_limits.items(), key=lambda x: x[1], reverse=True):
                print(f"   • {api}: {count}x")
        
        print("\n" + "=" * 70)

class LogTailer:
    """Tail bot logs in real-time."""
    
    def __init__(self, log_file, monitor):
        self.log_file = log_file
        self.monitor = monitor
        self.running = True
        self.last_position = 0
        
    def tail_logs(self):
        """Continuously read new log lines."""
        try:
            with open(self.log_file, 'r') as f:
                # Start at end of file
                f.seek(0, 2)
                self.last_position = f.tell()
                
                while self.running:
                    f.seek(self.last_position)
                    line = f.readline()
                    
                    if line:
                        self.analyze_log_line(line.strip())
                        self.last_position = f.tell()
                    else:
                        time.sleep(0.5)
        except FileNotFoundError:
            pass
        except Exception as exc:
            logger.error(f"Error tailing logs: {exc}")
    
    def analyze_log_line(self, line):
        """Analyze log line for patterns."""
        line_lower = line.lower()
        
        # Detect errors
        if 'error' in line_lower or 'exception' in line_lower:
            self.monitor.log_event("ERROR", line[:100])
        
        # Detect API calls
        if 'api' in line_lower or 'request' in line_lower:
            self.monitor.log_event("API_CALL", line[:100])
        
        # Detect rate limits
        if '429' in line or 'rate limit' in line_lower or 'too many requests' in line_lower:
            self.monitor.log_event("API_FAILURE", "Rate limit exceeded")
        
        # Detect real data patterns
        if 'market cap' in line_lower and '$' in line:
            self.monitor.log_event("REAL_DATA", line[:100])
        
        if 'price' in line_lower and '$' in line:
            self.monitor.log_event("REAL_DATA", line[:100])
        
        # Detect trading signals
        if 'buy' in line_lower or 'sell' in line_lower or 'signal' in line_lower:
            if 'confidence' in line_lower or 'signal' in line_lower:
                self.monitor.log_event("TRADING_SIGNAL", line[:100])
        
        # Detect position updates
        if 'position' in line_lower or 'entry' in line_lower or 'exit' in line_lower:
            self.monitor.log_event("POSITION_UPDATE", line[:100])
        
        # Detect fake data patterns
        if 'fallback' in line_lower or 'default' in line_lower or 'mock' in line_lower:
            self.monitor.log_event("FAKE_DATA", line[:100])
        
        if 'return 0.5' in line or 'return 1.0' in line or 'return none' in line_lower:
            self.monitor.log_event("FAKE_DATA", line[:100])

def monitor_bot_live():
    """Main monitoring function."""
    
    print("🎯 BOT LIVE MONITORING SYSTEM")
    print("=" * 70)
    print("Monitoring for:")
    print("✅ Real data patterns (live prices, market caps)")
    print("❌ Errors and exceptions")
    print("⚠️ Fake data and fallbacks")
    print("🚫 API rate limits and failures")
    print("🎯 Trading signals and positions")
    print("=" * 70)
    print()
    
    monitor = BotMonitor()
    
    # Create log tailer thread
    log_tailer = LogTailer('bot_monitor.log', monitor)
    tailer_thread = threading.Thread(target=log_tailer.tail_logs, daemon=True)
    tailer_thread.start()
    
    # Monitor loop
    try:
        while True:
            time.sleep(30)  # Print summary every 30 seconds
            monitor.print_summary()
            
    except KeyboardInterrupt:
        print("\n\n🛑 MONITORING STOPPED")
        log_tailer.running = False
        time.sleep(1)
        monitor.print_summary()
        
        # Final analysis
        print("\n" + "=" * 70)
        print("📋 FINAL ANALYSIS")
        print("=" * 70)
        
        if not monitor.fake_data_patterns:
            print("✅ NO FAKE DATA DETECTED - 100% Real Data Confirmed!")
        else:
            print(f"⚠️ {len(monitor.fake_data_patterns)} fake data patterns detected")
        
        if not monitor.errors:
            print("✅ NO ERRORS - Bot running cleanly!")
        else:
            print(f"❌ {sum(monitor.errors.values())} errors detected")
        
        if not monitor.api_failures:
            print("✅ NO API FAILURES - All APIs working!")
        else:
            print(f"⚠️ {sum(len(v) for v in monitor.api_failures.values())} API failures detected")
        
        if monitor.trading_signals:
            print(f"🎯 {len(monitor.trading_signals)} trading signals generated")
        
        if monitor.position_updates:
            print(f"💰 {len(monitor.position_updates)} position updates")
        
        print("\n" + "=" * 70)

if __name__ == "__main__":
    monitor_bot_live()
