#!/usr/bin/env python3
"""Manual script to generate comprehensive Excel trading reports."""

import sys
import logging
from pathlib import Path

# Add the trading_bot directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "trading_bot"))

from trading_bot.reporting.excel_reporter import generate_trading_report

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('report_generation.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Generate trading analysis report."""
    print("🔄 Generating Comprehensive Trading Analysis Report...")
    print("=" * 60)
    
    try:
        # Generate report for last 30 days
        report_path = generate_trading_report(days_back=30)
        
        if report_path:
            print(f"✅ SUCCESS: Excel report generated!")
            print(f"📊 Report Location: {report_path}")
            print("\n📋 Report Contents:")
            print("   • Trade Details - All individual trades with entry/exit data")
            print("   • Performance Summary - KPIs, win rate, profit metrics")
            print("   • Strategy Analysis - Exit reason effectiveness")
            print("   • Risk Analysis - Position sizing and risk metrics")
            print("   • Symbol Performance - Best/worst performing assets")
            print("   • Time Analysis - Hourly and daily performance patterns")
            print("   • Recommendations - AI-generated strategy improvements")
            
            print("\n🎯 Key Metrics to Review:")
            print("   • Win Rate (Target: >60%)")
            print("   • Profit Factor (Target: >1.5)")
            print("   • Average Win vs Average Loss")
            print("   • Maximum Drawdown")
            print("   • Sharpe Ratio")
            print("   • Exit Reason Effectiveness")
            
            print(f"\n📁 Open the file: {report_path}")
            
        else:
            print("❌ FAILED: Could not generate report")
            print("Check the logs for error details")
            
    except ImportError as e:
        print("❌ MISSING DEPENDENCY: openpyxl not installed")
        print("Install with: pip install openpyxl pandas")
        print(f"Error: {e}")
        
    except Exception as e:
        print(f"❌ ERROR: Report generation failed")
        print(f"Error: {e}")
        logger.exception("Report generation failed")


if __name__ == "__main__":
    main()
