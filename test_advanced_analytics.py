"""Step-by-step testing of advanced analytics modules."""

import sys
import logging
import numpy as np
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("🧪 ADVANCED ANALYTICS INTEGRATION TEST")
print("=" * 80)
print()

# Test results tracker
test_results = {
    'passed': [],
    'failed': [],
    'warnings': []
}

def test_step(step_name, test_func):
    """Run a test step and track results."""
    print(f"\n{'='*80}")
    print(f"📋 STEP: {step_name}")
    print(f"{'='*80}")
    try:
        test_func()
        test_results['passed'].append(step_name)
        print(f"✅ {step_name} - PASSED")
        return True
    except Exception as exc:
        test_results['failed'].append((step_name, str(exc)))
        print(f"❌ {step_name} - FAILED: {exc}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# STEP 1: Test Module Imports
# ============================================================================

def test_imports():
    """Test that all modules can be imported."""
    print("\n🔍 Testing module imports...")
    
    # Test advanced_risk
    print("   Importing advanced_risk...")
    from trading_bot.analytics.advanced_risk import get_advanced_risk_manager
    print("   ✓ advanced_risk imported")
    
    # Test dynamic_optimizer
    print("   Importing dynamic_optimizer...")
    from trading_bot.analytics.dynamic_optimizer import get_dynamic_optimizer
    print("   ✓ dynamic_optimizer imported")
    
    # Test market_structure
    print("   Importing market_structure...")
    from trading_bot.analytics.market_structure import get_market_structure_analyzer
    print("   ✓ market_structure imported")
    
    # Test macro_factors
    print("   Importing macro_factors...")
    from trading_bot.analytics.macro_factors import get_macro_factor_analyzer
    print("   ✓ macro_factors imported")
    
    # Test advanced_portfolio
    print("   Importing advanced_portfolio...")
    from trading_bot.analytics.advanced_portfolio import get_advanced_portfolio_manager
    print("   ✓ advanced_portfolio imported")
    
    print("\n✅ All modules imported successfully!")

# ============================================================================
# STEP 2: Test Module Initialization
# ============================================================================

def test_initialization():
    """Test that all modules can be initialized."""
    print("\n🔍 Testing module initialization...")
    
    from trading_bot.analytics.advanced_risk import get_advanced_risk_manager
    from trading_bot.analytics.dynamic_optimizer import get_dynamic_optimizer
    from trading_bot.analytics.market_structure import get_market_structure_analyzer
    from trading_bot.analytics.macro_factors import get_macro_factor_analyzer
    from trading_bot.analytics.advanced_portfolio import get_advanced_portfolio_manager
    
    # Initialize modules
    print("   Initializing advanced_risk_manager...")
    risk_mgr = get_advanced_risk_manager()
    print(f"   ✓ Advanced Risk Manager: {type(risk_mgr).__name__}")
    
    print("   Initializing dynamic_optimizer...")
    optimizer = get_dynamic_optimizer()
    print(f"   ✓ Dynamic Optimizer: {type(optimizer).__name__}")
    
    print("   Initializing market_structure_analyzer...")
    structure = get_market_structure_analyzer()
    print(f"   ✓ Market Structure Analyzer: {type(structure).__name__}")
    
    print("   Initializing macro_factor_analyzer...")
    macro = get_macro_factor_analyzer()
    print(f"   ✓ Macro Factor Analyzer: {type(macro).__name__}")
    
    print("   Initializing advanced_portfolio_manager...")
    portfolio = get_advanced_portfolio_manager()
    print(f"   ✓ Advanced Portfolio Manager: {type(portfolio).__name__}")
    
    print("\n✅ All modules initialized successfully!")

# ============================================================================
# STEP 3: Test Dynamic Optimizer
# ============================================================================

def test_dynamic_optimizer():
    """Test dynamic optimizer functionality."""
    print("\n🔍 Testing Dynamic Optimizer...")
    
    from trading_bot.analytics.dynamic_optimizer import get_dynamic_optimizer
    
    optimizer = get_dynamic_optimizer()
    
    # Create sample price and volume data
    print("   Creating sample market data...")
    price_data = np.array([100 + i + np.random.randn() * 2 for i in range(100)])
    volume_data = np.array([1000 + np.random.randn() * 100 for _ in range(100)])
    
    # Test regime detection
    print("   Testing market regime detection...")
    regime = optimizer.detect_market_regime(price_data, volume_data)
    print(f"   ✓ Detected regime: {regime.regime_type}")
    print(f"     - Strength: {regime.strength:.2f}")
    print(f"     - Volatility: {regime.volatility:.2f}")
    print(f"     - Duration: {regime.duration}")
    print(f"     - Volume profile: {regime.volume_profile}")
    
    # Test optimal parameters
    print("   Testing optimal parameter calculation...")
    optimal_params = optimizer.get_optimal_parameters("BTC/USDT", regime)
    print(f"   ✓ Optimal parameters calculated:")
    print(f"     - Confidence threshold: {optimal_params.confidence_threshold:.2f}")
    print(f"     - RSI period: {optimal_params.rsi_period}")
    print(f"     - Stop-loss multiplier: {optimal_params.stop_loss_multiplier:.2f}")
    print(f"     - Take-profit multiplier: {optimal_params.take_profit_multiplier:.2f}")
    
    print("\n✅ Dynamic Optimizer working correctly!")

# ============================================================================
# STEP 4: Test Market Structure Analyzer
# ============================================================================

def test_market_structure():
    """Test market structure analyzer functionality."""
    print("\n🔍 Testing Market Structure Analyzer...")
    
    from trading_bot.analytics.market_structure import get_market_structure_analyzer
    from dataclasses import dataclass
    
    # Create mock candle data
    @dataclass
    class MockCandle:
        open: float
        high: float
        low: float
        close: float
        volume: float
    
    print("   Creating sample candle data...")
    candles = []
    base_price = 100
    for i in range(100):
        price_change = np.random.randn() * 2
        open_price = base_price
        close_price = base_price + price_change
        high_price = max(open_price, close_price) + abs(np.random.randn())
        low_price = min(open_price, close_price) - abs(np.random.randn())
        volume = 1000 + np.random.randn() * 100
        
        candles.append(MockCandle(open_price, high_price, low_price, close_price, volume))
        base_price = close_price
    
    structure_analyzer = get_market_structure_analyzer()
    
    print("   Analyzing market structure...")
    structure = structure_analyzer.analyze_market_structure(candles)
    print(f"   ✓ Market structure analyzed:")
    print(f"     - Trend structure: {structure.trend_structure}")
    print(f"     - Smart money direction: {structure.smart_money_direction}")
    print(f"     - Structure strength: {structure.structure_strength:.2f}")
    print(f"     - Key levels found: {len(structure.key_levels)}")
    print(f"     - Liquidity pools: {len(structure.liquidity_pools)}")
    
    print("\n✅ Market Structure Analyzer working correctly!")

# ============================================================================
# STEP 5: Test Macro Factors Analyzer
# ============================================================================

def test_macro_factors():
    """Test macro factors analyzer functionality."""
    print("\n🔍 Testing Macro Factors Analyzer...")
    
    from trading_bot.analytics.macro_factors import get_macro_factor_analyzer
    
    macro_analyzer = get_macro_factor_analyzer()
    
    print("   Getting macro environment...")
    macro_env = macro_analyzer.get_current_macro_environment("BTC/USDT")
    print(f"   ✓ Macro environment assessed:")
    print(f"     - Market phase: {macro_env.market_phase}")
    print(f"     - Dollar strength: {macro_env.dollar_strength}")
    print(f"     - Crypto sentiment: {macro_env.crypto_sentiment}")
    print(f"     - Funding environment: {macro_env.funding_environment}")
    print(f"     - Correlation regime: {macro_env.correlation_regime}")
    print(f"     - Macro risk level: {macro_env.macro_risk_level}")
    print(f"     - Recommended exposure: {macro_env.recommended_exposure:.2f}")
    
    print("   Testing BTC dominance impact...")
    impact, signal = macro_analyzer.get_btc_dominance_impact()
    print(f"   ✓ BTC dominance impact: {signal} (impact={impact:.2f})")
    
    print("\n✅ Macro Factors Analyzer working correctly!")

# ============================================================================
# STEP 6: Test Advanced Portfolio Manager
# ============================================================================

def test_advanced_portfolio():
    """Test advanced portfolio manager functionality."""
    print("\n🔍 Testing Advanced Portfolio Manager...")
    
    from trading_bot.analytics.advanced_portfolio import get_advanced_portfolio_manager
    
    portfolio_manager = get_advanced_portfolio_manager()
    
    # Create sample price data for multiple symbols
    print("   Creating sample portfolio data...")
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"]
    price_data = {}
    volume_data = {}
    
    for symbol in symbols:
        price_data[symbol] = np.array([100 + i + np.random.randn() * 5 for i in range(100)])
        volume_data[symbol] = np.array([1000 + np.random.randn() * 200 for _ in range(100)])
    
    # Test pairs trading
    print("   Testing pairs trading identification...")
    pairs = portfolio_manager.identify_pairs_trading_opportunities(price_data)
    print(f"   ✓ Found {len(pairs)} pairs trading opportunities")
    if pairs:
        print(f"     - Top opportunity: {pairs[0].symbol_a} vs {pairs[0].symbol_b}")
        print(f"       Direction: {pairs[0].direction}, Confidence: {pairs[0].confidence:.2f}")
    
    # Test sector rotation
    print("   Testing sector rotation analysis...")
    rotations = portfolio_manager.analyze_sector_rotation(price_data, volume_data)
    print(f"   ✓ Found {len(rotations)} sector rotation signals")
    if rotations:
        print(f"     - Rotation: {rotations[0].from_sector} → {rotations[0].to_sector}")
        print(f"       Strength: {rotations[0].strength:.2f}")
    
    # Test portfolio optimization
    print("   Testing portfolio optimization...")
    optimization = portfolio_manager.optimize_portfolio_allocation(symbols, price_data)
    print(f"   ✓ Portfolio optimized:")
    print(f"     - Expected return: {optimization.expected_return:.4f}")
    print(f"     - Sharpe ratio: {optimization.sharpe_ratio:.2f}")
    print(f"     - Max drawdown estimate: {optimization.max_drawdown_estimate:.2f}")
    print(f"     - Positions: {len(optimization.target_weights)}")
    
    print("\n✅ Advanced Portfolio Manager working correctly!")

# ============================================================================
# STEP 7: Test Advanced Risk Manager
# ============================================================================

def test_advanced_risk():
    """Test advanced risk manager functionality."""
    print("\n🔍 Testing Advanced Risk Manager...")
    
    from trading_bot.analytics.advanced_risk import get_advanced_risk_manager
    
    risk_manager = get_advanced_risk_manager()
    
    # Test Kelly Criterion
    print("   Testing Kelly Criterion calculation...")
    kelly_fraction = risk_manager.calculate_kelly_fraction(
        symbol="BTC/USDT",
        confidence=0.7,
        market_conditions={'volatility': 0.05, 'trend_strength': 0.6}
    )
    print(f"   ✓ Kelly fraction: {kelly_fraction:.4f}")
    
    # Test risk metrics
    print("   Testing risk metrics calculation...")
    metrics = risk_manager.calculate_risk_metrics()
    print(f"   ✓ Risk metrics calculated:")
    print(f"     - Sharpe ratio: {metrics.sharpe_ratio:.2f}")
    print(f"     - Sortino ratio: {metrics.sortino_ratio:.2f}")
    print(f"     - Max drawdown: {metrics.max_drawdown:.2%}")
    print(f"     - Win rate: {metrics.win_rate:.2%}")
    
    print("\n✅ Advanced Risk Manager working correctly!")

# ============================================================================
# STEP 8: Test Pipeline Integration
# ============================================================================

def test_pipeline_integration():
    """Test that pipeline can import and use advanced modules."""
    print("\n🔍 Testing Pipeline Integration...")
    
    print("   Importing pipeline...")
    from trading_bot.orchestration.pipeline import TradingPipeline
    print("   ✓ Pipeline imported successfully")
    
    print("   Checking for advanced analytics attributes...")
    # We can't fully initialize without config, but we can check the class
    import inspect
    init_source = inspect.getsource(TradingPipeline.__init__)
    
    checks = [
        ('_advanced_risk', 'Advanced Risk Manager'),
        ('_dynamic_optimizer', 'Dynamic Optimizer'),
        ('_market_structure', 'Market Structure Analyzer'),
        ('_macro_factors', 'Macro Factors Analyzer'),
        ('_advanced_portfolio', 'Advanced Portfolio Manager')
    ]
    
    for attr, name in checks:
        if attr in init_source:
            print(f"   ✓ {name} integrated")
        else:
            raise Exception(f"{name} not found in pipeline initialization")
    
    print("\n✅ Pipeline integration verified!")

# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    print("\n🚀 Starting comprehensive test suite...\n")
    
    # Run all test steps
    test_step("1. Module Imports", test_imports)
    test_step("2. Module Initialization", test_initialization)
    test_step("3. Dynamic Optimizer", test_dynamic_optimizer)
    test_step("4. Market Structure Analyzer", test_market_structure)
    test_step("5. Macro Factors Analyzer", test_macro_factors)
    test_step("6. Advanced Portfolio Manager", test_advanced_portfolio)
    test_step("7. Advanced Risk Manager", test_advanced_risk)
    test_step("8. Pipeline Integration", test_pipeline_integration)
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    total_tests = len(test_results['passed']) + len(test_results['failed'])
    passed = len(test_results['passed'])
    failed = len(test_results['failed'])
    
    print(f"\n✅ Passed: {passed}/{total_tests}")
    if test_results['passed']:
        for test in test_results['passed']:
            print(f"   ✓ {test}")
    
    if test_results['failed']:
        print(f"\n❌ Failed: {failed}/{total_tests}")
        for test, error in test_results['failed']:
            print(f"   ✗ {test}")
            print(f"     Error: {error}")
    
    if test_results['warnings']:
        print(f"\n⚠️  Warnings: {len(test_results['warnings'])}")
        for warning in test_results['warnings']:
            print(f"   ⚠ {warning}")
    
    # Final verdict
    print("\n" + "=" * 80)
    if failed == 0:
        print("🎉 ALL TESTS PASSED! Advanced analytics integration is successful!")
        print("=" * 80)
        print("\n✅ You can now start the trading bot with full advanced analytics!")
        print("   Run: python simsim_server_bot D1.py")
    else:
        print("⚠️  SOME TESTS FAILED - Please review errors above")
        print("=" * 80)
    
    print()
