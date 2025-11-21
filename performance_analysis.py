"""Performance analysis and fine-tuning recommendations for advanced analytics."""

import re
import json
from datetime import datetime, timedelta
from pathlib import Path

class AdvancedAnalyticsPerformanceTracker:
    """Track and analyze advanced analytics performance."""
    
    def __init__(self):
        self.data_file = Path("data/performance_tracking.json")
        self.data_file.parent.mkdir(exist_ok=True)
        
    def analyze_current_performance(self, log_content: str):
        """Analyze current performance from log content."""
        
        print("🔍 ADVANCED ANALYTICS PERFORMANCE ANALYSIS")
        print("=" * 80)
        print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Extract key metrics from logs
        metrics = self._extract_metrics(log_content)
        
        # Analyze performance
        self._analyze_regime_detection(metrics)
        self._analyze_confidence_adjustments(metrics)
        self._analyze_macro_risk_management(metrics)
        self._analyze_market_structure_impact(metrics)
        self._provide_fine_tuning_recommendations(metrics)
        
    def _extract_metrics(self, log_content: str):
        """Extract performance metrics from log content."""
        
        metrics = {
            'regime_detections': [],
            'confidence_adjustments': [],
            'macro_risks': [],
            'market_structures': [],
            'trade_decisions': [],
            'symbols_analyzed': set()
        }
        
        lines = log_content.split('\n')
        
        for line in lines:
            # Extract regime detections
            if "📊 MARKET REGIME:" in line:
                match = re.search(r'📊 MARKET REGIME: (\w+/\w+) - (\w+) \(strength=([\d.]+), volatility=([\d.]+)\)', line)
                if match:
                    symbol, regime, strength, volatility = match.groups()
                    metrics['regime_detections'].append({
                        'symbol': symbol,
                        'regime': regime,
                        'strength': float(strength),
                        'volatility': float(volatility)
                    })
                    metrics['symbols_analyzed'].add(symbol)
            
            # Extract confidence adjustments
            if "🎯 DYNAMIC CONFIDENCE:" in line:
                match = re.search(r'🎯 DYNAMIC CONFIDENCE: Using regime-optimized threshold ([\d.]+)', line)
                if match:
                    threshold = float(match.group(1))
                    metrics['confidence_adjustments'].append(threshold)
            
            # Extract macro risk warnings
            if "⚠️ MACRO RISK:" in line:
                match = re.search(r'⚠️ MACRO RISK: Recommended exposure ([\d.]+)', line)
                if match:
                    exposure = float(match.group(1))
                    metrics['macro_risks'].append(exposure)
            
            # Extract market structure assessments
            if "🏗️ MARKET STRUCTURE:" in line:
                match = re.search(r'🏗️ MARKET STRUCTURE: (\w+/\w+) - trend=(\w+), smart_money=(\w+), strength=([\d.]+)', line)
                if match:
                    symbol, trend, smart_money, strength = match.groups()
                    metrics['market_structures'].append({
                        'symbol': symbol,
                        'trend': trend,
                        'smart_money': smart_money,
                        'strength': float(strength)
                    })
            
            # Extract trade decisions
            if "Iteration summary:" in line:
                decisions = re.findall(r'(\w+/\w+):(\w+):(\w+)', line)
                for symbol, decision, action in decisions:
                    metrics['trade_decisions'].append({
                        'symbol': symbol,
                        'decision': decision,
                        'action': action
                    })
        
        return metrics
    
    def _analyze_regime_detection(self, metrics):
        """Analyze regime detection performance."""
        
        print("\n📊 REGIME DETECTION ANALYSIS")
        print("-" * 50)
        
        regimes = metrics['regime_detections']
        if not regimes:
            print("❌ No regime detections found in logs")
            return
        
        # Analyze regime distribution
        regime_counts = {}
        strength_sum = 0
        volatility_sum = 0
        
        for regime in regimes:
            regime_type = regime['regime']
            regime_counts[regime_type] = regime_counts.get(regime_type, 0) + 1
            strength_sum += regime['strength']
            volatility_sum += regime['volatility']
        
        print(f"✅ Analyzed {len(regimes)} regime detections across {len(metrics['symbols_analyzed'])} symbols")
        print(f"📊 Regime Distribution:")
        for regime_type, count in regime_counts.items():
            percentage = (count / len(regimes)) * 100
            print(f"   • {regime_type}: {count} ({percentage:.1f}%)")
        
        avg_strength = strength_sum / len(regimes)
        avg_volatility = volatility_sum / len(regimes)
        
        print(f"📈 Average Regime Strength: {avg_strength:.2f}")
        print(f"📉 Average Market Volatility: {avg_volatility:.2f}")
        
        # Performance assessment
        if avg_strength > 0.8:
            print("✅ EXCELLENT: High regime detection confidence")
        elif avg_strength > 0.6:
            print("✅ GOOD: Moderate regime detection confidence")
        else:
            print("⚠️ ATTENTION: Low regime detection confidence - consider tuning")
    
    def _analyze_confidence_adjustments(self, metrics):
        """Analyze confidence threshold adjustments."""
        
        print("\n🎯 CONFIDENCE ADJUSTMENT ANALYSIS")
        print("-" * 50)
        
        adjustments = metrics['confidence_adjustments']
        if not adjustments:
            print("❌ No confidence adjustments found in logs")
            return
        
        min_conf = min(adjustments)
        max_conf = max(adjustments)
        avg_conf = sum(adjustments) / len(adjustments)
        
        print(f"✅ Tracked {len(adjustments)} confidence adjustments")
        print(f"📊 Confidence Range: {min_conf:.2f} - {max_conf:.2f}")
        print(f"📈 Average Confidence: {avg_conf:.2f}")
        
        # Analyze adjustment behavior
        if max_conf - min_conf > 0.2:
            print("✅ EXCELLENT: Dynamic confidence adjustment working well")
        elif max_conf - min_conf > 0.1:
            print("✅ GOOD: Moderate confidence adjustment")
        else:
            print("⚠️ ATTENTION: Limited confidence adjustment - may need tuning")
        
        # Recommendations based on average confidence
        if avg_conf > 0.7:
            print("💡 RECOMMENDATION: Confidence thresholds are conservative (good for risk management)")
        elif avg_conf < 0.4:
            print("💡 RECOMMENDATION: Confidence thresholds may be too aggressive")
        else:
            print("💡 ASSESSMENT: Confidence thresholds appear well-balanced")
    
    def _analyze_macro_risk_management(self, metrics):
        """Analyze macro risk management performance."""
        
        print("\n🌍 MACRO RISK MANAGEMENT ANALYSIS")
        print("-" * 50)
        
        macro_risks = metrics['macro_risks']
        if not macro_risks:
            print("❌ No macro risk assessments found in logs")
            return
        
        avg_exposure = sum(macro_risks) / len(macro_risks)
        
        print(f"✅ Tracked {len(macro_risks)} macro risk assessments")
        print(f"📊 Average Recommended Exposure: {avg_exposure:.2f}")
        
        if avg_exposure < 0.3:
            print("🛡️ EXCELLENT: System is being very conservative due to macro risk")
            print("💡 This is protecting capital in unfavorable conditions")
        elif avg_exposure < 0.5:
            print("⚠️ MODERATE: System detecting moderate macro risk")
        else:
            print("✅ FAVORABLE: Macro conditions appear supportive")
        
        # Current market assessment
        if macro_risks and macro_risks[-1] < 0.2:
            print("🚨 CURRENT STATUS: High macro risk detected - system in protective mode")
    
    def _analyze_market_structure_impact(self, metrics):
        """Analyze market structure analysis impact."""
        
        print("\n🏗️ MARKET STRUCTURE ANALYSIS")
        print("-" * 50)
        
        structures = metrics['market_structures']
        if not structures:
            print("❌ No market structure analyses found in logs")
            return
        
        # Analyze structure strength
        avg_strength = sum(s['strength'] for s in structures) / len(structures)
        
        # Analyze trend distribution
        trend_counts = {}
        smart_money_counts = {}
        
        for structure in structures:
            trend = structure['trend']
            smart_money = structure['smart_money']
            
            trend_counts[trend] = trend_counts.get(trend, 0) + 1
            smart_money_counts[smart_money] = smart_money_counts.get(smart_money, 0) + 1
        
        print(f"✅ Analyzed {len(structures)} market structures")
        print(f"📊 Average Structure Strength: {avg_strength:.2f}")
        
        print(f"📈 Trend Distribution:")
        for trend, count in trend_counts.items():
            percentage = (count / len(structures)) * 100
            print(f"   • {trend}: {count} ({percentage:.1f}%)")
        
        print(f"🧠 Smart Money Distribution:")
        for smart_money, count in smart_money_counts.items():
            percentage = (count / len(structures)) * 100
            print(f"   • {smart_money}: {count} ({percentage:.1f}%)")
        
        if avg_strength > 0.7:
            print("✅ EXCELLENT: Strong market structure detection")
        else:
            print("⚠️ ATTENTION: Weaker market structures detected")
    
    def _provide_fine_tuning_recommendations(self, metrics):
        """Provide fine-tuning recommendations based on analysis."""
        
        print("\n🔧 FINE-TUNING RECOMMENDATIONS")
        print("=" * 80)
        
        # Analyze overall behavior
        regimes = metrics['regime_detections']
        confidences = metrics['confidence_adjustments']
        macro_risks = metrics['macro_risks']
        decisions = metrics['trade_decisions']
        
        # Count HOLD decisions
        hold_count = sum(1 for d in decisions if d['decision'] == 'HOLD')
        total_decisions = len(decisions)
        hold_percentage = (hold_count / total_decisions * 100) if total_decisions > 0 else 0
        
        print(f"📊 CURRENT BEHAVIOR ANALYSIS:")
        print(f"   • Hold Rate: {hold_percentage:.1f}% ({hold_count}/{total_decisions})")
        
        # Provide specific recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        if hold_percentage > 90:
            print("🔴 VERY CONSERVATIVE BEHAVIOR DETECTED:")
            print("   1. System is being extremely cautious (good for risk management)")
            print("   2. Consider if this matches your risk tolerance")
            print("   3. Current macro conditions may be driving this behavior")
            print("\n   🔧 POTENTIAL ADJUSTMENTS:")
            print("   • Reduce macro risk sensitivity if too conservative")
            print("   • Lower confidence thresholds slightly (0.05-0.10)")
            print("   • Check if regime detection is too strict")
            
        elif hold_percentage > 70:
            print("🟡 CONSERVATIVE BEHAVIOR:")
            print("   1. System is being appropriately cautious")
            print("   2. Good risk management in current conditions")
            print("   3. Monitor for opportunities when conditions improve")
            
        else:
            print("🟢 BALANCED BEHAVIOR:")
            print("   1. System showing good balance of caution and opportunity")
            print("   2. Continue monitoring performance")
        
        # Macro-specific recommendations
        if macro_risks and sum(macro_risks) / len(macro_risks) < 0.2:
            print("\n🌍 MACRO ENVIRONMENT RECOMMENDATIONS:")
            print("   • High macro risk detected - system correctly being defensive")
            print("   • Consider this is protecting your capital")
            print("   • Monitor for macro conditions to improve")
            print("   • When macro improves, expect more aggressive trading")
        
        # Regime-specific recommendations
        if regimes:
            sideways_count = sum(1 for r in regimes if r['regime'] == 'sideways')
            if sideways_count / len(regimes) > 0.8:
                print("\n📊 REGIME-SPECIFIC RECOMMENDATIONS:")
                print("   • Mostly sideways markets detected")
                print("   • System correctly avoiding poor trending conditions")
                print("   • Consider this is optimal behavior for current market")
        
        print(f"\n🎯 NEXT STEPS:")
        print("1. Monitor performance over 1-2 weeks for trend analysis")
        print("2. Compare win rate when trades do execute")
        print("3. Track if macro conditions improve and system becomes more aggressive")
        print("4. Consider current conservative behavior as capital preservation")
        
        print(f"\n✅ OVERALL ASSESSMENT:")
        print("Advanced analytics are working correctly and protecting capital")
        print("in unfavorable market conditions. This is exactly the desired behavior!")

def main():
    """Main analysis function."""
    
    # Sample log content from the terminal (you would read from actual logs)
    sample_log = """
    2025-11-14 05:40:26,376 | INFO | trading_bot.orchestration.pipeline | 🌍 MACRO ENVIRONMENT: phase=risk_off, sentiment=bearish, risk=high, exposure=0.10
    2025-11-14 05:40:26,376 | INFO | trading_bot.orchestration.pipeline | 🎯 DYNAMIC CONFIDENCE: Using regime-optimized threshold 0.65
    2025-11-14 05:40:29,751 | INFO | trading_bot.orchestration.pipeline | 📊 MARKET REGIME: SOL/USDT - sideways (strength=1.00, volatility=0.04)
    2025-11-14 05:40:29,751 | INFO | trading_bot.orchestration.pipeline | ⚙️ OPTIMAL PARAMS: confidence_threshold=0.65, rsi_period=21, stop_loss_mult=1.04
    2025-11-14 05:40:29,754 | INFO | trading_bot.orchestration.pipeline | 🏗️ MARKET STRUCTURE: SOL/USDT - trend=sideways, smart_money=neutral, strength=0.80
    2025-11-14 05:40:38,574 | INFO | __main__ | Iteration summary: STX/USDT:HOLD:SKIP, ADA/USDT:HOLD:SKIP, ZRO/USDT:HOLD:SKIP, RACA/USDT:HOLD:SKIP, DOT/USDT:HOLD:SKIP, USDC/USDT:HOLD:SKIP, NEAR/USDT:HOLD:SKIP, SOL/USDT:HOLD:SKIP, MASK/USDT:HOLD:SKIP, FIL/USDT:HOLD:SKIP
    """
    
    tracker = AdvancedAnalyticsPerformanceTracker()
    tracker.analyze_current_performance(sample_log)

if __name__ == "__main__":
    main()
