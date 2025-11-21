#!/usr/bin/env python3
"""Quick script to check OKX balance and see all assets."""

import sys
from pathlib import Path

# Add the trading_bot directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "trading_bot"))

from trading_bot.connectors.okx import OkxConnector
from trading_bot.config import Config

def main():
    """Check balance and show all assets."""
    print("🔄 Checking OKX balance...")
    
    try:
        # Initialize config and connector
        from trading_bot.config.enhanced_config import load_enhanced_config
        config = load_enhanced_config()
        okx = OkxConnector(config.okx_credentials, sandbox=config.okx_sandbox)
        
        # Fetch balance
        balance = okx.fetch_balance()
        
        if not balance or "free" not in balance:
            print("❌ Could not fetch balance")
            return
        
        print(f"✅ Balance fetched successfully")
        print(f"📊 Total assets in balance: {len(balance['free'])}")
        print("\n🔍 DETAILED ASSET BREAKDOWN:")
        print("=" * 60)
        
        total_assets = 0
        qualifying_assets = 0
        min_threshold = 1.0  # $1 threshold
        
        for asset, amount in balance["free"].items():
            if amount <= 0:
                continue
                
            total_assets += 1
            
            try:
                if asset == "USDT":
                    value = amount
                    price = 1.0
                else:
                    symbol = f"{asset}/USDT"
                    ticker = okx.fetch_ticker(symbol)
                    price = float(ticker["last"])
                    value = amount * price
                
                status = "✅ QUALIFY" if value >= min_threshold else "❌ TOO SMALL"
                if value >= min_threshold:
                    qualifying_assets += 1
                
                print(f"{status} | {asset:8} | {amount:15.6f} @ ${price:10.6f} = ${value:10.2f}")
                
            except Exception as e:
                print(f"❌ ERROR   | {asset:8} | {amount:15.6f} @ ERROR: {e}")
        
        print("=" * 60)
        print(f"📊 SUMMARY:")
        print(f"   • Total assets with balance: {total_assets}")
        print(f"   • Assets above ${min_threshold}: {qualifying_assets}")
        print(f"   • Assets that should be loaded as positions: {qualifying_assets - 1}")  # Exclude USDT
        
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    main()
