#!/usr/bin/env python3
"""Create sample trade data for testing the Excel reporting system."""

import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

def create_sample_trades(num_trades: int = 50) -> list:
    """Create sample trade data for testing."""
    
    symbols = [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT", "DOT/USDT",
        "MATIC/USDT", "AVAX/USDT", "LINK/USDT", "UNI/USDT", "ATOM/USDT"
    ]
    
    exit_reasons = [
        "quick-profit-taking", "profit-protection-bearish-signal", "loss-limitation-low-confidence",
        "regime-change-trending_down", "sentiment-deterioration", "large-profit-protection",
        "intelligent-sell", "stop-loss-hit", "take-profit-hit"
    ]
    
    trades = []
    base_time = datetime.now() - timedelta(days=30)
    
    for i in range(num_trades):
        # Random trade timing
        entry_time = base_time + timedelta(
            days=random.randint(0, 29),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        # Trade duration (1 hour to 3 days)
        duration_hours = random.uniform(1, 72)
        exit_time = entry_time + timedelta(hours=duration_hours)
        
        # Random symbol and prices
        symbol = random.choice(symbols)
        entry_price = random.uniform(0.1, 50000)  # Wide range for different assets
        
        # Generate realistic price movement
        price_change_pct = random.normalvariate(0.5, 8.0)  # Slight positive bias
        exit_price = entry_price * (1 + price_change_pct / 100)
        
        # Trade amount (simulate 5% position sizing)
        portfolio_value = 10000  # Assume $10k portfolio
        position_value = portfolio_value * 0.05  # 5% position
        amount = position_value / entry_price
        
        # Calculate PnL
        pnl_usd = (exit_price - entry_price) * amount
        pnl_percentage = ((exit_price - entry_price) / entry_price) * 100
        
        # Random confidence (higher for winning trades)
        base_confidence = random.uniform(0.3, 0.9)
        if pnl_usd > 0:
            confidence = min(base_confidence + 0.1, 0.95)  # Boost for winners
        else:
            confidence = max(base_confidence - 0.1, 0.25)  # Reduce for losers
        
        # Exit reason (biased based on performance)
        if pnl_percentage > 5:
            reason = random.choice(["quick-profit-taking", "large-profit-protection", "take-profit-hit"])
        elif pnl_percentage < -3:
            reason = random.choice(["loss-limitation-low-confidence", "stop-loss-hit", "sentiment-deterioration"])
        else:
            reason = random.choice(exit_reasons)
        
        trade = {
            "symbol": symbol,
            "side": "BUY",
            "entry_price": round(entry_price, 6),
            "exit_price": round(exit_price, 6),
            "amount": round(amount, 6),
            "entry_time": entry_time.timestamp(),
            "exit_time": exit_time.timestamp(),
            "pnl_usd": round(pnl_usd, 2),
            "pnl_percentage": round(pnl_percentage, 2),
            "reason": reason,
            "confidence": round(confidence, 2)
        }
        
        trades.append(trade)
    
    return trades

def main():
    """Create sample data and save to file."""
    print("🔄 Creating sample trade data for testing...")
    
    # Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Generate sample trades
    trades = create_sample_trades(75)  # 75 sample trades
    
    # Save to JSON file
    trades_file = data_dir / "daily_trades.json"
    with open(trades_file, 'w') as f:
        json.dump(trades, f, indent=2)
    
    # Calculate some basic stats
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t['pnl_usd'] > 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    total_pnl = sum(t['pnl_usd'] for t in trades)
    
    print(f"✅ Created {total_trades} sample trades")
    print(f"📊 Win Rate: {win_rate:.1f}%")
    print(f"💰 Total PnL: ${total_pnl:.2f}")
    print(f"📁 Saved to: {trades_file}")
    print("\nNow you can run: python generate_report.py")

if __name__ == "__main__":
    main()
