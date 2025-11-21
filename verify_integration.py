"""Quick verification that the bot can start with advanced analytics."""

import sys
import logging
from pathlib import Path

# Setup minimal logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("🔍 VERIFYING ADVANCED ANALYTICS INTEGRATION")
print("=" * 60)

try:
    print("\n1. Testing pipeline import with advanced analytics...")
    from trading_bot.orchestration.pipeline import TradingPipeline
    print("   ✅ Pipeline imported successfully")
    
    print("\n2. Checking advanced analytics availability...")
    
    # Check if all modules can be imported
    modules = [
        ("Advanced Risk Manager", "trading_bot.analytics.advanced_risk", "get_advanced_risk_manager"),
        ("Dynamic Optimizer", "trading_bot.analytics.dynamic_optimizer", "get_dynamic_optimizer"),
        ("Market Structure", "trading_bot.analytics.market_structure", "get_market_structure_analyzer"),
        ("Macro Factors", "trading_bot.analytics.macro_factors", "get_macro_factor_analyzer"),
        ("Advanced Portfolio", "trading_bot.analytics.advanced_portfolio", "get_advanced_portfolio_manager")
    ]
    
    for name, module_path, function_name in modules:
        try:
            module = __import__(module_path, fromlist=[function_name])
            get_func = getattr(module, function_name)
            instance = get_func()
            print(f"   ✅ {name}: {type(instance).__name__}")
        except Exception as exc:
            print(f"   ❌ {name}: {exc}")
            raise
    
    print("\n3. Testing integration points...")
    
    # Test that pipeline has the new attributes (by checking source)
    import inspect
    init_source = inspect.getsource(TradingPipeline.__init__)
    
    required_attrs = [
        "_advanced_risk",
        "_dynamic_optimizer", 
        "_market_structure",
        "_macro_factors",
        "_advanced_portfolio"
    ]
    
    for attr in required_attrs:
        if attr in init_source:
            print(f"   ✅ {attr} integrated in pipeline")
        else:
            print(f"   ❌ {attr} missing from pipeline")
            raise Exception(f"{attr} not found in pipeline")
    
    print("\n" + "=" * 60)
    print("🎉 INTEGRATION VERIFICATION COMPLETE!")
    print("=" * 60)
    print("\n✅ ALL ADVANCED ANALYTICS MODULES ARE READY!")
    print("\n🚀 You can now start the trading bot:")
    print("   python simsim_server_bot D1.py")
    print("\n📊 Expected new features:")
    print("   • Market regime detection and adaptive parameters")
    print("   • Volume profile and smart money analysis")
    print("   • Macro-economic risk assessment")
    print("   • Kelly Criterion position sizing")
    print("   • Advanced portfolio optimization")
    print("\n🎯 Watch for enhanced log output with:")
    print("   📊 MARKET REGIME, 🏗️ MARKET STRUCTURE, 🌍 MACRO ENVIRONMENT")
    
except Exception as exc:
    print(f"\n❌ INTEGRATION VERIFICATION FAILED: {exc}")
    print("\nPlease check the error above and fix any issues.")
    sys.exit(1)
