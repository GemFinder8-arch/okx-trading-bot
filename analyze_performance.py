#!/usr/bin/env python3
"""Analyze trading performance and provide enhancement recommendations."""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def load_trade_data():
    """Load trade data from JSON file."""
    trades_file = Path("data/daily_trades.json")
    if not trades_file.exists():
        print("❌ No trade data found")
        return []
    
    with open(trades_file, 'r') as f:
        return json.load(f)

def analyze_performance(trades):
    """Analyze trading performance and identify issues."""
    if not trades:
        print("❌ No trades to analyze")
        return
    
    print("🔍 COMPREHENSIVE TRADING PERFORMANCE ANALYSIS")
    print("=" * 60)
    
    # Basic metrics
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t.get('pnl_usd', 0) > 0])
    losing_trades = total_trades - winning_trades
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    total_pnl = sum(t.get('pnl_usd', 0) for t in trades)
    
    wins = [t.get('pnl_usd', 0) for t in trades if t.get('pnl_usd', 0) > 0]
    losses = [abs(t.get('pnl_usd', 0)) for t in trades if t.get('pnl_usd', 0) < 0]
    
    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0
    profit_factor = sum(wins) / sum(losses) if losses else float('inf')
    
    print(f"📊 OVERALL PERFORMANCE:")
    print(f"   • Total Trades: {total_trades}")
    print(f"   • Win Rate: {win_rate:.1f}% (Target: >60%)")
    print(f"   • Total PnL: ${total_pnl:.2f}")
    print(f"   • Profit Factor: {profit_factor:.2f} (Target: >1.5)")
    print(f"   • Average Win: ${avg_win:.2f}")
    print(f"   • Average Loss: ${avg_loss:.2f}")
    
    # Performance assessment
    issues = []
    if win_rate < 60:
        issues.append(f"🔴 LOW WIN RATE: {win_rate:.1f}% (need >60%)")
    if profit_factor < 1.5:
        issues.append(f"🔴 LOW PROFIT FACTOR: {profit_factor:.2f} (need >1.5)")
    if total_pnl < 0:
        issues.append(f"🔴 NEGATIVE TOTAL PnL: ${total_pnl:.2f}")
    
    print(f"\n🚨 CRITICAL ISSUES ({len(issues)}):")
    for issue in issues:
        print(f"   {issue}")
    
    return analyze_detailed_patterns(trades)

def analyze_detailed_patterns(trades):
    """Analyze detailed trading patterns."""
    print(f"\n🔍 DETAILED PATTERN ANALYSIS:")
    print("=" * 60)
    
    # Exit reason analysis
    exit_reasons = defaultdict(lambda: {'count': 0, 'wins': 0, 'total_pnl': 0})
    
    for trade in trades:
        reason = trade.get('reason', 'unknown')
        pnl = trade.get('pnl_usd', 0)
        
        exit_reasons[reason]['count'] += 1
        exit_reasons[reason]['total_pnl'] += pnl
        if pnl > 0:
            exit_reasons[reason]['wins'] += 1
    
    print(f"📋 EXIT REASON EFFECTIVENESS:")
    for reason, stats in sorted(exit_reasons.items(), key=lambda x: x[1]['total_pnl'], reverse=True):
        win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
        avg_pnl = stats['total_pnl'] / stats['count'] if stats['count'] > 0 else 0
        
        status = "✅" if win_rate > 60 else "⚠️" if win_rate > 40 else "❌"
        print(f"   {status} {reason:25} | {stats['count']:2d} trades | {win_rate:5.1f}% win | ${avg_pnl:7.2f} avg | ${stats['total_pnl']:8.2f} total")
    
    # Symbol performance
    symbols = defaultdict(lambda: {'count': 0, 'wins': 0, 'total_pnl': 0})
    
    for trade in trades:
        symbol = trade.get('symbol', 'unknown')
        pnl = trade.get('pnl_usd', 0)
        
        symbols[symbol]['count'] += 1
        symbols[symbol]['total_pnl'] += pnl
        if pnl > 0:
            symbols[symbol]['wins'] += 1
    
    print(f"\n💎 SYMBOL PERFORMANCE:")
    for symbol, stats in sorted(symbols.items(), key=lambda x: x[1]['total_pnl'], reverse=True):
        win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
        avg_pnl = stats['total_pnl'] / stats['count'] if stats['count'] > 0 else 0
        
        status = "✅" if win_rate > 60 else "⚠️" if win_rate > 40 else "❌"
        print(f"   {status} {symbol:12} | {stats['count']:2d} trades | {win_rate:5.1f}% win | ${avg_pnl:7.2f} avg | ${stats['total_pnl']:8.2f} total")
    
    # Confidence analysis
    confidences = [t.get('confidence', 0) for t in trades if t.get('confidence', 0) > 0]
    if confidences:
        avg_confidence = np.mean(confidences)
        print(f"\n🎯 CONFIDENCE ANALYSIS:")
        print(f"   • Average Confidence: {avg_confidence:.2f}")
        
        # Confidence vs performance
        high_conf_trades = [t for t in trades if t.get('confidence', 0) > 0.7]
        low_conf_trades = [t for t in trades if 0 < t.get('confidence', 0) < 0.4]
        
        if high_conf_trades:
            high_conf_win_rate = len([t for t in high_conf_trades if t.get('pnl_usd', 0) > 0]) / len(high_conf_trades) * 100
            print(f"   • High Confidence (>0.7): {len(high_conf_trades)} trades, {high_conf_win_rate:.1f}% win rate")
        
        if low_conf_trades:
            low_conf_win_rate = len([t for t in low_conf_trades if t.get('pnl_usd', 0) > 0]) / len(low_conf_trades) * 100
            print(f"   • Low Confidence (<0.4): {len(low_conf_trades)} trades, {low_conf_win_rate:.1f}% win rate")
    
    return generate_recommendations(trades, exit_reasons, symbols)

def generate_recommendations(trades, exit_reasons, symbols):
    """Generate specific enhancement recommendations."""
    print(f"\n💡 ENHANCEMENT RECOMMENDATIONS:")
    print("=" * 60)
    
    recommendations = []
    
    # Win rate analysis
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t.get('pnl_usd', 0) > 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    if win_rate < 50:
        recommendations.append({
            'priority': 'CRITICAL',
            'category': 'Win Rate',
            'issue': f'Very low win rate: {win_rate:.1f}%',
            'recommendation': 'Increase confidence threshold to 0.6+ and improve entry signals',
            'expected_impact': '15-20% improvement in win rate'
        })
    elif win_rate < 60:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Win Rate',
            'issue': f'Below target win rate: {win_rate:.1f}%',
            'recommendation': 'Fine-tune entry conditions and add more technical filters',
            'expected_impact': '5-10% improvement in win rate'
        })
    
    # Exit reason analysis
    worst_exit_reasons = sorted(exit_reasons.items(), key=lambda x: x[1]['total_pnl'])[:3]
    for reason, stats in worst_exit_reasons:
        if stats['total_pnl'] < -50:
            win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Exit Strategy',
                'issue': f'Poor {reason} performance: {win_rate:.1f}% win rate, ${stats["total_pnl"]:.2f} total',
                'recommendation': f'Optimize {reason} conditions - tighten triggers or improve timing',
                'expected_impact': '10-15% reduction in losses'
            })
    
    # Symbol analysis
    worst_symbols = sorted(symbols.items(), key=lambda x: x[1]['total_pnl'])[:3]
    for symbol, stats in worst_symbols:
        if stats['total_pnl'] < -30 and stats['count'] > 2:
            win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Asset Selection',
                'issue': f'{symbol} underperforming: {win_rate:.1f}% win rate, ${stats["total_pnl"]:.2f} total',
                'recommendation': f'Consider blacklisting {symbol} or improving its analysis',
                'expected_impact': '5-10% improvement in overall performance'
            })
    
    # Confidence analysis
    confidences = [t.get('confidence', 0) for t in trades if t.get('confidence', 0) > 0]
    if confidences:
        avg_confidence = np.mean(confidences)
        if avg_confidence < 0.5:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Signal Quality',
                'issue': f'Low average confidence: {avg_confidence:.2f}',
                'recommendation': 'Increase minimum confidence threshold and improve signal generation',
                'expected_impact': '10-15% improvement in trade quality'
            })
    
    # Position sizing analysis
    position_values = []
    for trade in trades:
        entry_price = trade.get('entry_price', 0)
        amount = trade.get('amount', 0)
        position_value = entry_price * amount
        position_values.append(position_value)
    
    if position_values:
        avg_position = np.mean(position_values)
        std_position = np.std(position_values)
        cv = std_position / avg_position if avg_position > 0 else 0
        
        if cv > 0.5:  # High variability
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Position Sizing',
                'issue': f'Inconsistent position sizing (CV: {cv:.2f})',
                'recommendation': 'Implement strict 5% position sizing rule',
                'expected_impact': 'Better risk management and consistency'
            })
    
    # Print recommendations
    for i, rec in enumerate(recommendations, 1):
        priority_color = "🔴" if rec['priority'] == 'CRITICAL' else "🟠" if rec['priority'] == 'HIGH' else "🟡"
        print(f"{i:2d}. {priority_color} {rec['priority']} - {rec['category']}")
        print(f"     Issue: {rec['issue']}")
        print(f"     Fix: {rec['recommendation']}")
        print(f"     Impact: {rec['expected_impact']}")
        print()
    
    return recommendations

def main():
    """Main analysis function."""
    print("🔄 Loading trade data...")
    trades = load_trade_data()
    
    if not trades:
        print("❌ No trade data available for analysis")
        return
    
    print(f"✅ Loaded {len(trades)} trades for analysis\n")
    
    recommendations = analyze_performance(trades)
    
    print(f"📊 ANALYSIS COMPLETE!")
    print(f"   • {len(recommendations)} enhancement opportunities identified")
    print(f"   • Focus on HIGH and CRITICAL priority items first")
    print(f"   • Check the Excel report for detailed breakdowns")

if __name__ == "__main__":
    main()
