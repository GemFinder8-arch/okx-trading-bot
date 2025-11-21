#!/usr/bin/env python3
"""
Real-time bot monitoring script
Captures and analyzes bot logs line by line
"""

import subprocess
import time
import re
from datetime import datetime

class BotMonitor:
    def __init__(self):
        self.critical_events = []
        self.warnings = []
        self.trades = []
        self.analytics = []
        self.errors = []
        
    def analyze_line(self, line: str):
        """Analyze each log line and categorize it."""
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        timestamp = timestamp_match.group(1) if timestamp_match else "Unknown"
        
        # Critical events
        if "BUY" in line and "EXECUTED" in line:
            self.trades.append(f"[{timestamp}] 🟢 {line}")
            print(f"\n🟢 TRADE EXECUTED: {line}\n")
            
        elif "SELL" in line and "EXECUTED" in line:
            self.trades.append(f"[{timestamp}] 🔴 {line}")
            print(f"\n🔴 POSITION CLOSED: {line}\n")
            
        # OCO Protection
        elif "OCO PROTECTION ACTIVE" in line:
            print(f"✅ OCO: {line}")
            
        elif "OCO PROTECTION FAILED" in line:
            self.warnings.append(f"[{timestamp}] ⚠️ {line}")
            print(f"⚠️ OCO FALLBACK: {line}")
            
        # Advanced Analytics
        elif "MARKET REGIME:" in line:
            self.analytics.append(f"[{timestamp}] 📊 {line}")
            print(f"📊 REGIME: {line}")
            
        elif "MARKET STRUCTURE:" in line:
            self.analytics.append(f"[{timestamp}] 🏗️ {line}")
            print(f"🏗️ STRUCTURE: {line}")
            
        elif "MACRO ENVIRONMENT:" in line:
            self.analytics.append(f"[{timestamp}] 🌍 {line}")
            print(f"🌍 MACRO: {line}")
            
        # Confidence checks
        elif "Insufficient combined confidence" in line:
            print(f"⏭️ SKIPPED: {line}")
            
        # Errors
        elif "ERROR" in line or "❌" in line:
            self.errors.append(f"[{timestamp}] ❌ {line}")
            print(f"\n❌ ERROR: {line}\n")
            
        # Warnings
        elif "WARNING" in line or "⚠️" in line:
            self.warnings.append(f"[{timestamp}] ⚠️ {line}")
            
        # Position management
        elif "EXISTING POSITION" in line:
            print(f"🔒 POSITION: {line}")
            
        elif "LOADING EXISTING POSITIONS" in line:
            print(f"\n{'='*60}")
            print(f"🔍 {line}")
            print(f"{'='*60}\n")
            
        # Rebalancing
        elif "REBALANCING COMPLETE" in line:
            print(f"\n🔄 {line}\n")
            
        # Top tokens
        elif "TOP 5 TOKEN SCORES" in line:
            print(f"\n🏆 {line}\n")
            
    def print_summary(self):
        """Print monitoring summary."""
        print(f"\n{'='*60}")
        print("📊 BOT MONITORING SUMMARY")
        print(f"{'='*60}")
        print(f"🟢 Trades Executed: {len(self.trades)}")
        print(f"⚠️ Warnings: {len(self.warnings)}")
        print(f"❌ Errors: {len(self.errors)}")
        print(f"📊 Analytics Events: {len(self.analytics)}")
        print(f"{'='*60}\n")
        
        if self.trades:
            print("\n🟢 TRADES:")
            for trade in self.trades[-5:]:  # Last 5 trades
                print(f"   {trade}")
                
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors[-5:]:  # Last 5 errors
                print(f"   {error}")

def main():
    print("🚀 STARTING BOT MONITORING...")
    print("=" * 60)
    print("Monitoring logs in real-time...")
    print("Press Ctrl+C to stop and see summary")
    print("=" * 60 + "\n")
    
    monitor = BotMonitor()
    
    try:
        # Start the bot process
        process = subprocess.Popen(
            ["python", "-m", "trading_bot.main"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor output line by line
        for line in process.stdout:
            line = line.strip()
            if line:
                monitor.analyze_line(line)
                
    except KeyboardInterrupt:
        print("\n\n⏹️ Stopping monitoring...")
        process.terminate()
        monitor.print_summary()
        
    except Exception as e:
        print(f"\n❌ Monitoring error: {e}")
        monitor.print_summary()

if __name__ == "__main__":
    main()
