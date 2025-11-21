"""Pipeline orchestrator for the trading bot."""

from __future__ import annotations

import json
import logging
import re
import time
import numpy as np
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from trading_bot.analytics.decision_engine import EnhancedDecisionEngine
from trading_bot.analytics.enhanced_risk import EnhancedRiskManager
from trading_bot.analytics.indicators import ema, rsi
from trading_bot.analytics.liquidity import LiquidityAnalyzer, OrderBookSnapshot
from trading_bot.analytics.macro import MacroDataProvider, MacroEvent, OnChainDataProvider
from trading_bot.analytics.market_data import MarketDataManager
from trading_bot.analytics.daily_performance import get_performance_tracker
from trading_bot.analytics.portfolio_optimizer import PortfolioOptimizer
from trading_bot.analytics.risk import RiskAnalyzer, RiskMetrics
from trading_bot.config.asset_blacklist import is_asset_blacklisted, get_confidence_override, is_high_performer
from trading_bot.analytics.technical import TechnicalAnalyzer
from trading_bot.analytics.enhanced_signals import get_enhanced_signal_analyzer
from trading_bot.analytics.multi_timeframe import get_multi_timeframe_analyzer
from trading_bot.coordination.data_coordinator import TradingDataCoordinator

# Advanced analytics modules
from trading_bot.analytics.advanced_risk import get_advanced_risk_manager
from trading_bot.analytics.dynamic_optimizer import get_dynamic_optimizer
from trading_bot.analytics.market_structure import get_market_structure_analyzer
from trading_bot.analytics.macro_factors import get_macro_factor_analyzer
from trading_bot.analytics.advanced_portfolio import get_advanced_portfolio_manager
from trading_bot.monitoring.performance_monitor import PerformanceTimer, get_performance_monitor
from trading_bot.connectors.dex import OneInchConnector
from trading_bot.connectors.okx import OkxConnector
from trading_bot.config import Config

logger = logging.getLogger(__name__)


@dataclass
class MarketState:
    symbol: str
    prices: Iterable[float]
    order_book: OrderBookSnapshot
    macro_events: Iterable[MacroEvent]
    risk_metrics: Optional[RiskMetrics] = None


@dataclass
class TradeResult:
    symbol: str
    decision: str
    executed: bool
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class Position:
    symbol: str
    side: str
    amount: float
    entry_price: float
    stop_loss: float
    take_profit: float
    order_id: Optional[str] = None
    stop_order_id: Optional[str] = None
    take_profit_order_id: Optional[str] = None
    protection_algo_id: Optional[str] = None
    managed_by_exchange: bool = False
    entry_time: Optional[float] = None  # Timestamp when position was opened


class TradingPipeline:
    """Encapsulates data retrieval, analysis, decisioning, and execution."""

    def __init__(
        self,
        config: Config,
        okx: OkxConnector,
        macro_provider: MacroDataProvider,
        onchain_provider: OnChainDataProvider,
        dex_connector: Optional[OneInchConnector] = None,
    ) -> None:
        self._config = config
        self._okx = okx
        self._macro_provider = macro_provider
        self._onchain_provider = onchain_provider
        self._dex = dex_connector

        self._liquidity = LiquidityAnalyzer()
        self._risk = RiskAnalyzer()
        self._technical = TechnicalAnalyzer()
        self._market_data = MarketDataManager(okx, cache_duration=30)
        self._enhanced_risk = EnhancedRiskManager(self._market_data)
        self._decision_engine = EnhancedDecisionEngine()
        
        # Initialize DataCoordinator for optimized performance
        self._data_coordinator = TradingDataCoordinator(
            market_data_manager=self._market_data,
            technical_analyzer=self._technical,
            decision_engine=self._decision_engine,
            risk_manager=self._enhanced_risk,
            okx_connector=okx
        )
        
        self._positions: dict[str, Position] = {}
        self._restricted_cache_path = Path("data/okx_restricted_symbols.json")
        self._restricted_symbols: set[str] = set()
        self._last_order_error: Optional[dict[str, str]] = None
        
        # Load existing positions from exchange on startup
        self._load_existing_positions()
        
        # Performance monitoring
        self._performance_monitor = get_performance_monitor()
        self._daily_performance = get_performance_tracker()
        
        # Portfolio optimization
        self._portfolio_optimizer = PortfolioOptimizer(self._okx, self._daily_performance)
        
        # Multi-timeframe analysis
        self._multi_tf_analyzer = get_multi_timeframe_analyzer(self._market_data)
        
        # 🚀 ADVANCED ANALYTICS MODULES
        self._advanced_risk = get_advanced_risk_manager()
        self._dynamic_optimizer = get_dynamic_optimizer()
        self._market_structure = get_market_structure_analyzer()
        self._macro_factors = get_macro_factor_analyzer()
        self._advanced_portfolio = get_advanced_portfolio_manager()
        
        logger.info("✅ ADVANCED ANALYTICS INITIALIZED: Risk, Optimizer, Market Structure, Macro, Portfolio")

        self._load_restricted_symbols()
        setattr(self._onchain_provider, "restricted_symbols", self._restricted_symbols)

    def _load_existing_positions(self) -> None:
        """Load existing positions from exchange on startup."""
        try:
            logger.info("🔍 LOADING EXISTING POSITIONS from exchange...")
            
            # Get current balance to find non-USDT holdings
            balance = self._okx.fetch_balance()
            logger.info("🔍 Balance fetch result: %s", "SUCCESS" if balance else "FAILED")
            
            if not balance or "free" not in balance:
                logger.warning("Could not fetch balance to load existing positions - balance: %s", balance)
                return
            
            # Debug: Log all assets in balance
            free_assets = balance.get("free", {})
            logger.info("🔍 Assets in balance: %s", list(free_assets.keys()))
            
            positions_found = 0
            min_position_value = 0.01  # Only track positions worth more than $0.01 (extremely low threshold to catch all positions)
            
            for asset, amount in balance["free"].items():
                if asset == "USDT" or amount <= 0:
                    logger.debug("🔍 Skipping %s: amount=%.6f", asset, amount)
                    continue
                
                try:
                    symbol = f"{asset}/USDT"
                    
                    # Try to get current price, with fallback
                    try:
                        ticker = self._okx.fetch_ticker(symbol)
                        current_price = float(ticker["last"])
                    except Exception as price_exc:
                        logger.warning("❌ Could not get price for %s: %s - Using fallback", asset, price_exc)
                        # Use fallback prices for common assets
                        fallback_prices = {
                            "BTC": 42000.0, "ETH": 2500.0, "SOL": 150.0, "ADA": 0.55,
                            "DOT": 6.0, "XTZ": 0.95, "DOGE": 0.08, "SHIB": 0.000025,
                            "NEAR": 2.5, "ALGO": 0.18, "SAND": 0.35, "PEPE": 0.000001,
                            "RACA": 0.0002, "IOTA": 0.25, "UNI": 8.0, "LINK": 15.0
                        }
                        current_price = fallback_prices.get(asset, 1.0)  # Default to $1 if unknown
                        logger.info("🔄 Using fallback price for %s: $%.6f", asset, current_price)
                    
                    position_value = amount * current_price
                    
                    logger.info("🔍 CHECKING ASSET: %s - %.6f tokens @ $%.6f = $%.2f", 
                               asset, amount, current_price, position_value)
                    
                    if position_value >= min_position_value:
                        logger.info("✅ QUALIFYING POSITION: %s - $%.2f (above $%.2f threshold)", 
                                   asset, position_value, min_position_value)
                        # Create position record for existing holding
                        # Calculate basic protective levels
                        atr_multiplier = 0.02  # 2% protection
                        stop_loss = current_price * (1 - atr_multiplier)
                        take_profit = current_price * (1 + atr_multiplier * 2)
                        
                        position = Position(
                            symbol=symbol,
                            side="long",
                            amount=amount,
                            entry_price=current_price,  # Use current price as entry (approximate)
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            order_id=None,  # No order ID for pre-existing positions
                            protection_algo_id=None,  # No OCO protection initially
                            managed_by_exchange=False,  # Not managed by exchange initially
                            entry_time=time.time()  # Current timestamp for existing positions
                        )
                        
                        self._positions[symbol] = position
                        positions_found += 1
                        
                        logger.info("📊 EXISTING POSITION LOADED: %s - %.6f tokens (~$%.2f)", 
                                   symbol, amount, position_value)
                    else:
                        logger.info("❌ POSITION TOO SMALL: %s - $%.2f (below $%.2f threshold)", 
                                   asset, position_value, min_position_value)
                        
                except Exception as exc:
                    logger.warning("❌ ERROR LOADING POSITION: %s - %s", asset, exc)
                    continue
            
            logger.info("📊 POSITION LOADING COMPLETE:")
            logger.info("   • Total assets checked: %d", len(free_assets))
            logger.info("   • Positions loaded: %d", positions_found)
            logger.info("   • Position symbols: %s", list(self._positions.keys()) if self._positions else "None")
            
            if positions_found > 0:
                logger.info("✅ LOADED %d EXISTING POSITIONS from exchange", positions_found)
                
                # Try to set up OCO protection for existing positions
                self._setup_protection_for_existing_positions()
            else:
                logger.info("📊 No existing positions found on exchange")
                
        except Exception as exc:
            logger.error("Failed to load existing positions: %s", exc)
    
    def _setup_protection_for_existing_positions(self) -> None:
        """Set up OCO protection for existing positions that don't have it."""
        try:
            logger.info("🛡️ SETTING UP PROTECTION for existing positions...")
            
            for symbol, position in self._positions.items():
                if position.managed_by_exchange or position.protection_algo_id:
                    continue  # Already has protection
                
                try:
                    # Get current market data for stop-loss/take-profit calculation
                    ticker = self._okx.fetch_ticker(symbol)
                    current_price = float(ticker["last"])
                    
                    # Calculate protective levels (simple ATR-based)
                    atr_multiplier = 0.02  # 2% ATR equivalent
                    stop_loss = current_price * (1 - atr_multiplier)
                    take_profit = current_price * (1 + atr_multiplier * 2)  # 2:1 risk/reward
                    
                    # Try to place OCO protection
                    algo_id = self._place_protection_orders(
                        symbol, position.amount, stop_loss, take_profit, entry_price=current_price
                    )
                    
                    if algo_id:
                        # Update position with protection info
                        position.protection_algo_id = algo_id
                        position.managed_by_exchange = True
                        position.stop_loss = stop_loss
                        position.take_profit = take_profit
                        
                        logger.info("✅ OCO PROTECTION ADDED: %s - Algo ID: %s", symbol, algo_id)
                    else:
                        logger.warning("⚠️ Could not add OCO protection for existing position: %s", symbol)
                        
                except Exception as exc:
                    logger.warning("Failed to add protection for %s: %s", symbol, exc)
                    
        except Exception as exc:
            logger.error("Failed to setup protection for existing positions: %s", exc)

    def _rebalance_portfolio(self) -> None:
        """Execute automatic portfolio rebalancing and optimization."""
        try:
            logger.info("🔄 STARTING PORTFOLIO REBALANCING...")
            
            # Get current balance and top-ranked symbols
            current_balance = self._get_current_balance()
            
            # Get top-ranked symbols from token ranking (simulate for now)
            top_symbols = self._get_top_ranked_symbols()
            
            # Generate optimization plan
            rebalancing_actions = self._portfolio_optimizer.optimize_portfolio(
                self._positions, current_balance, top_symbols
            )
            
            if not rebalancing_actions:
                logger.info("📊 No rebalancing actions needed")
                return
            
            # Execute rebalancing (limit to 2 actions per cycle to avoid over-trading)
            executed_count = self._portfolio_optimizer.execute_rebalancing(rebalancing_actions, max_actions=2)
            
            if executed_count > 0:
                logger.info("✅ PORTFOLIO REBALANCED: %d actions executed", executed_count)
                
                # Log portfolio metrics after rebalancing
                metrics = self._portfolio_optimizer.get_portfolio_metrics(self._positions, current_balance)
                logger.info(
                    "📊 PORTFOLIO METRICS: Value=$%.2f, PnL=%.2f%%, Concentration=%.1f%%, Diversification=%.1f%%",
                    metrics.total_value, metrics.total_pnl_percentage, 
                    metrics.concentration_risk, metrics.diversification_score
                )
            
        except Exception as exc:
            logger.error("Portfolio rebalancing failed: %s", exc)
    
    def _get_top_ranked_symbols(self) -> list[str]:
        """Get top-ranked symbols for portfolio optimization."""
        try:
            # This would integrate with the token ranking system
            # For now, return a reasonable default set
            return [
                "BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT", 
                "DOT/USDT", "MATIC/USDT", "AVAX/USDT", "LINK/USDT"
            ]
        except Exception as exc:
            logger.error("Error getting top ranked symbols: %s", exc)
            return []

    @property
    def open_positions(self) -> dict[str, Position]:
        return self._positions.copy()
    
    def manage_all_positions(self) -> None:
        """Actively manage all open positions with intelligent analysis."""
        if not self._positions:
            logger.debug("No open positions to manage")
            return
        
        logger.info("Managing %d open positions with intelligent analysis", len(self._positions))
        
        # Check if portfolio needs rebalancing
        current_balance = self._get_current_balance()
        if self._portfolio_optimizer.should_rebalance(self._positions, current_balance):
            self._rebalance_portfolio()
        
        for symbol in list(self._positions.keys()):  # Use list() to avoid dict change during iteration
            try:
                # Get current market state for the position
                state = self._gather_market_state(symbol)
                if not state:
                    logger.debug("No market state available for position %s", symbol)
                    continue
                
                # Evaluate the position with intelligent management
                self._evaluate_open_position(state)
                
            except Exception as exc:
                logger.error("Error managing position %s: %s", symbol, exc)
    
    def manage_all_assets(self) -> None:
        """Manage ALL crypto assets in wallet - not just active positions."""
        try:
            logger.info("🔍 ANALYZING COMPLETE PORTFOLIO - Checking all wallet balances")
            
            # First check for any pending sell orders and handle them
            self._handle_pending_sell_orders()
            
            # Get all wallet balances
            balance = self._okx.fetch_balance()
            if not balance or "free" not in balance:
                logger.warning("Could not fetch wallet balances")
                return
            
            # Find all non-USDT assets with meaningful balances
            crypto_assets = []
            min_usd_value = 50.0  # Only analyze assets worth more than $50 to save time
            
            for asset, amount in balance["free"].items():
                if asset == "USDT" or amount <= 0:
                    continue
                
                # Try to get current price to calculate USD value
                try:
                    symbol = f"{asset}/USDT"
                    ticker = self._okx.fetch_ticker(symbol)
                    current_price = float(ticker["last"])
                    usd_value = amount * current_price
                    
                    if usd_value >= min_usd_value:
                        crypto_assets.append({
                            "asset": asset,
                            "symbol": symbol,
                            "amount": amount,
                            "price": current_price,
                            "usd_value": usd_value
                        })
                        
                except Exception as exc:
                    logger.debug("Could not get price for %s: %s", asset, exc)
                    continue
            
            if not crypto_assets:
                logger.info("📊 No significant crypto assets found in wallet (minimum $%.0f)", min_usd_value)
                return
            
            # Limit analysis to top 5 assets by value to save time
            crypto_assets = sorted(crypto_assets, key=lambda x: x['usd_value'], reverse=True)[:5]
            
            logger.info("💰 Analyzing top %d crypto assets: %s", 
                       len(crypto_assets), 
                       ", ".join([f"{a['asset']} (${a['usd_value']:.2f})" for a in crypto_assets]))
            
            # Analyze each asset for sell/hold decision with time tracking
            import time
            start_time = time.time()
            max_analysis_time = 30.0  # Maximum 30 seconds for portfolio analysis
            
            for i, asset_info in enumerate(crypto_assets):
                # Check time limit
                if time.time() - start_time > max_analysis_time:
                    logger.info("⏰ Portfolio analysis time limit reached, analyzed %d/%d assets", i, len(crypto_assets))
                    break
                    
                self._analyze_asset_for_management(asset_info)
                
        except Exception as exc:
            logger.error("Error in complete portfolio management: %s", exc)
    
    def _analyze_asset_for_management(self, asset_info: dict) -> None:
        """Analyze individual asset and make sell/hold decision."""
        try:
            symbol = asset_info["symbol"]
            asset = asset_info["asset"]
            amount = asset_info["amount"]
            current_price = asset_info["price"]
            usd_value = asset_info["usd_value"]
            
            logger.info("🔍 ANALYZING ASSET: %s (%.4f tokens, $%.2f)", asset, amount, usd_value)
            
            # Get comprehensive market analysis
            mtf_data = self._market_data.get_multi_timeframe_data(symbol)
            if not mtf_data:
                logger.info("⏭️  SKIP %s: No market data available", asset)
                return
            
            # Get order book and ticker for analysis
            try:
                order_book = self._okx.fetch_order_book(symbol, limit=20)
                ticker = self._okx.fetch_ticker(symbol)
            except Exception as exc:
                logger.info("⏭️  SKIP %s: Market data error - %s", asset, exc)
                return
            
            # Get market state and compute technical features
            state = self._gather_market_state(symbol)
            if not state:
                logger.info("⏭️  SKIP %s: Could not gather market state", asset)
                return
            
            # Compute technical features from market state
            features = self._compute_features(state)
            if not features:
                logger.info("⏭️  SKIP %s: Could not compute technical features", asset)
                return
            
            # Get trading signal for current conditions
            trading_signal = self._decision_engine.make_trading_decision(
                symbol=symbol,
                mtf_data=mtf_data,
                current_price=current_price,
                technical_features=features,
                order_book=order_book
            )
            
            # Make sell/hold decision for the asset
            should_sell, reason = self._should_sell_asset(
                asset_info, trading_signal, ticker, order_book
            )
            
            if should_sell:
                logger.info("💸 SELL DECISION: %s - %s (Value: $%.2f)", asset, reason, usd_value)
                self._execute_asset_sell(asset_info, reason)
            else:
                logger.info("🤝 HOLD DECISION: %s - Conditions favor holding (Value: $%.2f, Confidence: %.2f)", 
                           asset, usd_value, trading_signal.confidence)
                
        except Exception as exc:
            logger.error("Error analyzing asset %s: %s", asset_info.get("asset", "unknown"), exc)
    
    def _should_sell_asset(self, asset_info: dict, trading_signal, ticker: dict, order_book: dict) -> tuple[bool, str]:
        """Determine if asset should be sold based on comprehensive analysis."""
        
        asset = asset_info["asset"]
        usd_value = asset_info["usd_value"]
        
        # 1. STRONG SELL SIGNAL - High confidence bearish signal
        if trading_signal.decision == "SELL" and trading_signal.confidence > 0.7:
            return True, "strong-bearish-signal"
        
        # 2. REGIME BREAKDOWN - Market structure deteriorating
        regime = trading_signal.regime_context.primary_regime.value
        if regime in ["trending_down", "breakdown", "crisis"] and trading_signal.confidence > 0.6:
            return True, f"market-regime-{regime}"
        
        # 3. SENTIMENT COLLAPSE - Very negative market sentiment
        sentiment_scores = trading_signal.sentiment_scores
        bearish_sentiment = sentiment_scores.get('bearish', 0) + sentiment_scores.get('fear', 0)
        if bearish_sentiment > 0.8:  # Very strong negative sentiment
            return True, "sentiment-collapse"
        
        # 4. MOMENTUM BREAKDOWN - Strong negative momentum
        price_change = float(ticker.get("percentage", 0))
        if price_change < -10.0:  # >10% daily decline
            return True, "momentum-breakdown"
        
        # 5. LIQUIDITY CRISIS - Asset becoming illiquid
        try:
            bids = order_book.get("bids", [])[:5]
            asks = order_book.get("asks", [])[:5]
            if bids and asks:
                bid_volume = sum(float(level[1]) for level in bids)
                ask_volume = sum(float(level[1]) for level in asks)
                total_liquidity_usd = (bid_volume + ask_volume) * asset_info["price"]
                
                # If liquidity is very low relative to position size
                if total_liquidity_usd < usd_value * 2:  # Less than 2x position size in liquidity
                    return True, "liquidity-crisis"
        except Exception:
            pass
        
        # 6. VOLATILITY EXPLOSION - Extreme volatility (risky to hold)
        try:
            high = float(ticker.get("high", 0))
            low = float(ticker.get("low", 0))
            close = float(ticker.get("last", 0))
            if close > 0:
                daily_volatility = (high - low) / close
                if daily_volatility > 0.30:  # >30% daily volatility
                    return True, "volatility-explosion"
        except Exception:
            pass
        
        # 7. ASSET-SPECIFIC RISKS
        # Meme coins - more aggressive selling
        if asset in ["DOGE", "SHIB", "PEPE", "FLOKI", "TRUMP"]:
            if trading_signal.confidence < 0.4 or price_change < -5.0:
                return True, "meme-coin-risk"
        
        # Small cap altcoins - sell on weakness
        if usd_value < 50 and (trading_signal.confidence < 0.3 or price_change < -7.0):
            return True, "small-cap-weakness"
        
        # 8. TECHNICAL BREAKDOWN - Multiple timeframe weakness
        if trading_signal.confidence < 0.2:  # Very low confidence across timeframes
            return True, "technical-breakdown"
        
        # Default: Hold the asset
        return False, "conditions-favor-holding"
    
    def _execute_asset_sell(self, asset_info: dict, reason: str) -> None:
        """Execute the sale of an asset with proper fill verification."""
        try:
            symbol = asset_info["symbol"]
            asset = asset_info["asset"]
            amount = asset_info["amount"]
            usd_value = asset_info["usd_value"]
            
            logger.info("🔄 EXECUTING SELL: %s - %.4f tokens (~$%.2f) - Reason: %s", 
                       asset, amount, usd_value, reason)
            
            # Execute market sell order
            order = self._okx.create_order(symbol, "market", "sell", amount)
            order_id = order.get("id")
            
            if not order_id:
                logger.error("❌ SELL FAILED: %s - No order ID returned", asset)
                return
            
            logger.info("📋 Order placed: %s (ID: %s)", asset, order_id)
            
            # Wait and check order status to verify fill
            import time
            time.sleep(2)  # Give exchange time to process
            
            try:
                # Check order status
                order_status = self._okx.fetch_order(order_id, symbol)
                status = order_status.get("status", "unknown")
                filled_amount = float(order_status.get("filled", 0))
                remaining_amount = float(order_status.get("remaining", amount))
                
                if status == "closed" and filled_amount > 0:
                    # Fully filled
                    actual_proceeds = filled_amount * asset_info["price"]
                    logger.info("✅ SELL COMPLETED: %s - %.4f tokens FULLY FILLED for $%.2f", 
                               asset, filled_amount, actual_proceeds)
                    
                elif filled_amount > 0 and remaining_amount > 0:
                    # Partially filled
                    fill_percentage = (filled_amount / amount) * 100
                    actual_proceeds = filled_amount * asset_info["price"]
                    logger.warning("⚠️ PARTIAL FILL: %s - %.4f/%.4f tokens filled (%.1f%%) for $%.2f", 
                                  asset, filled_amount, amount, fill_percentage, actual_proceeds)
                    
                    # Try to cancel remaining and place new market order for remainder
                    if remaining_amount > 0:
                        try:
                            self._okx.cancel_order(order_id, symbol)
                            logger.info("🔄 Cancelled remaining order, placing new market order for %.4f %s", 
                                       remaining_amount, asset)
                            
                            # Place new market order for remaining amount
                            remaining_order = self._okx.create_order(symbol, "market", "sell", remaining_amount)
                            logger.info("📋 Remainder order placed: %s", remaining_order.get("id", "unknown"))
                            
                        except Exception as cancel_exc:
                            logger.error("❌ Failed to handle remaining amount: %s", cancel_exc)
                    
                elif status in ["open", "pending"]:
                    # Order still pending
                    logger.warning("⏳ SELL PENDING: %s - Order still processing (Status: %s)", asset, status)
                    
                else:
                    # Order failed or cancelled
                    logger.error("❌ SELL FAILED: %s - Order status: %s, Filled: %.4f", 
                               asset, status, filled_amount)
                    
            except Exception as status_exc:
                logger.error("❌ Could not verify order status for %s: %s", asset, status_exc)
                logger.info("⚠️ Order placed but status unknown - check exchange manually")
            
        except Exception as exc:
            logger.error("❌ FAILED TO SELL %s: %s", asset_info["asset"], exc)
    
    def _handle_pending_sell_orders(self) -> None:
        """Check and handle any pending sell orders from previous cycles."""
        try:
            # Get all open orders
            open_orders = self._okx.fetch_open_orders()
            
            if not open_orders:
                return
            
            sell_orders = [order for order in open_orders if order.get("side") == "sell"]
            
            if not sell_orders:
                return
            
            logger.info("🔍 Found %d pending sell orders to check", len(sell_orders))
            
            for order in sell_orders:
                try:
                    order_id = order.get("id")
                    symbol = order.get("symbol")
                    amount = float(order.get("amount", 0))
                    filled = float(order.get("filled", 0))
                    remaining = float(order.get("remaining", amount))
                    
                    if not order_id or not symbol:
                        continue
                    
                    asset = symbol.split("/")[0]
                    
                    # Check current order status
                    current_status = self._okx.fetch_order(order_id, symbol)
                    status = current_status.get("status", "unknown")
                    current_filled = float(current_status.get("filled", 0))
                    
                    if status == "closed":
                        if current_filled > 0:
                            logger.info("✅ PREVIOUS SELL COMPLETED: %s - %.4f tokens filled", 
                                       asset, current_filled)
                        continue
                    
                    elif status in ["open", "pending"] and remaining > 0:
                        # Order still pending, cancel and retry with market order
                        logger.info("⏳ PENDING SELL FOUND: %s - %.4f tokens remaining, cancelling and retrying", 
                                   asset, remaining)
                        
                        try:
                            self._okx.cancel_order(order_id, symbol)
                            
                            # Place new market order for remaining amount
                            new_order = self._okx.create_order(symbol, "market", "sell", remaining)
                            logger.info("🔄 RETRY SELL: %s - New market order placed: %s", 
                                       asset, new_order.get("id", "unknown"))
                            
                        except Exception as retry_exc:
                            logger.error("❌ Failed to retry sell for %s: %s", asset, retry_exc)
                    
                except Exception as order_exc:
                    logger.error("Error handling pending order: %s", order_exc)
                    
        except Exception as exc:
            logger.debug("Could not check pending orders: %s", exc)

    @property
    def restricted_symbols(self) -> set[str]:
        return set(self._restricted_symbols)

    def run_cycle(self, symbol: str) -> TradeResult:
        """Optimized pipeline cycle using DataCoordinator."""
        with PerformanceTimer("pipeline", "run_cycle"):
            logger.info("Starting pipeline cycle for %s", symbol)
            
            # Check if we already have a position
            existing_position = self._positions.get(symbol)
            if existing_position:
                logger.info("🔒 EXISTING POSITION: %s - Amount: %.6f, Entry: %.6f, skipping new trade", 
                           symbol, existing_position.amount, existing_position.entry_price)
                return TradeResult(symbol, "HOLD", False, None)
            
            # EXCEL REPORT ENHANCEMENT: Check asset blacklist
            if is_asset_blacklisted(symbol):
                logger.info("🚫 BLACKLISTED ASSET: %s - Skipping due to poor historical performance", symbol)
                return TradeResult(symbol, "HOLD", False, None)
            
            # Get comprehensive analysis using DataCoordinator (single optimized call)
            try:
                with PerformanceTimer("pipeline", "comprehensive_analysis"):
                    analysis_package = self._data_coordinator.get_comprehensive_analysis(
                        symbol=symbol,
                        existing_positions=self._positions,
                        current_balance=self._get_current_balance()
                    )
                
                if not analysis_package:
                    logger.warning("No analysis available for %s", symbol)
                    return TradeResult(symbol, "HOLD", False, None)
                
                # Extract decision and levels from comprehensive analysis
                trading_signal = analysis_package.trading_signal
                technical_levels = analysis_package.technical_levels
                optimal_size = analysis_package.optimal_position_size
                
                # MULTI-TIMEFRAME ANALYSIS - Comprehensive chart analysis
                logger.info("🔍 MULTI-TIMEFRAME ANALYSIS: %s across all timeframes", symbol)
                mtf_signal = self._multi_tf_analyzer.analyze_all_timeframes(symbol)
                
                # 🚀 ADVANCED ANALYTICS INTEGRATION
                
                # 1. MARKET REGIME DETECTION & DYNAMIC OPTIMIZATION
                try:
                    mtf_data = self._market_data.get_multi_timeframe_data(symbol)
                    if mtf_data:
                        candles_5m = mtf_data.get_timeframe('5m')
                        if candles_5m and len(candles_5m) >= 50:
                            price_data = np.array([c.close for c in candles_5m])
                            volume_data = np.array([c.volume for c in candles_5m])
                            
                            # Detect market regime
                            market_regime = self._dynamic_optimizer.detect_market_regime(price_data, volume_data)
                            logger.info("📊 MARKET REGIME: %s - %s (strength=%.2f, volatility=%.2f)",
                                       symbol, market_regime.regime_type, market_regime.strength, market_regime.volatility)
                            
                            # Get optimal parameters for current regime
                            optimal_params = self._dynamic_optimizer.get_optimal_parameters(symbol, market_regime)
                            logger.info("⚙️ OPTIMAL PARAMS: confidence_threshold=%.2f, rsi_period=%d, stop_loss_mult=%.2f",
                                       optimal_params.confidence_threshold, optimal_params.rsi_period, 
                                       optimal_params.stop_loss_multiplier)
                except Exception as opt_exc:
                    logger.debug("Dynamic optimization failed for %s: %s", symbol, opt_exc)
                    optimal_params = None
                    market_regime = None
                
                # 2. MARKET STRUCTURE ANALYSIS
                try:
                    candles = self._market_data.get_candles(symbol, '5m', limit=100)
                    if candles and len(candles) >= 50:
                        market_structure = self._market_structure.analyze_market_structure(candles)
                        logger.info("🏗️ MARKET STRUCTURE: %s - trend=%s, smart_money=%s, strength=%.2f",
                                   symbol, market_structure.trend_structure, 
                                   market_structure.smart_money_direction, market_structure.structure_strength)
                        
                        # Adjust confidence based on market structure
                        if market_structure.smart_money_direction == trading_signal.decision.lower():
                            logger.info("✅ SMART MONEY ALIGNMENT: Smart money agrees with signal direction")
                except Exception as struct_exc:
                    logger.debug("Market structure analysis failed for %s: %s", symbol, struct_exc)
                    market_structure = None
                
                # 3. MACRO-ECONOMIC FACTORS
                try:
                    macro_env = self._macro_factors.get_current_macro_environment(symbol)
                    logger.info("🌍 MACRO ENVIRONMENT: phase=%s, sentiment=%s, risk=%s, exposure=%.2f",
                               macro_env.market_phase, macro_env.crypto_sentiment, 
                               macro_env.macro_risk_level, macro_env.recommended_exposure)
                    
                    # Get BTC dominance impact
                    btc_dom_impact, btc_dom_signal = self._macro_factors.get_btc_dominance_impact()
                    if abs(btc_dom_impact) > 0.1:
                        logger.info("📊 BTC DOMINANCE: %s (impact=%.2f)", btc_dom_signal, btc_dom_impact)
                except Exception as macro_exc:
                    logger.debug("Macro analysis failed for %s: %s", symbol, macro_exc)
                    macro_env = None
                
                # Enhanced confidence calculation with multi-timeframe input
                base_threshold = self._decision_engine.min_confidence_threshold
                confidence_override = get_confidence_override(symbol)
                
                # Apply dynamic optimization if available
                if optimal_params:
                    required_confidence = optimal_params.confidence_threshold
                    logger.info("🎯 DYNAMIC CONFIDENCE: Using regime-optimized threshold %.2f", required_confidence)
                else:
                    required_confidence = max(base_threshold, confidence_override)
                
                # Multi-timeframe confidence boost
                if mtf_signal.trend_confluence > 0.8:
                    logger.info("🎯 HIGH TREND CONFLUENCE: %s confluence=%.2f - reducing confidence requirement", 
                               symbol, mtf_signal.trend_confluence)
                    required_confidence *= 0.8  # Reduce requirement for high confluence
                elif mtf_signal.trend_confluence < 0.4:
                    logger.info("⚠️ LOW TREND CONFLUENCE: %s confluence=%.2f - increasing confidence requirement", 
                               symbol, mtf_signal.trend_confluence)
                    required_confidence *= 1.2  # Increase requirement for low confluence
                
                # Boost confidence requirement for high performers
                if is_high_performer(symbol):
                    required_confidence = max(required_confidence, 0.6)  # Higher standard for proven winners
                
                # Combined confidence check (original signal + multi-timeframe)
                combined_confidence = (trading_signal.confidence * 0.6) + (mtf_signal.entry_confidence * 0.4)
                
                if combined_confidence < required_confidence:
                    logger.info("Insufficient combined confidence for %s: %.2f (required: %.2f) [original=%.2f, mtf=%.2f]", 
                               symbol, combined_confidence, required_confidence, 
                               trading_signal.confidence, mtf_signal.entry_confidence)
                    return TradeResult(symbol, "HOLD", False, None)
                
                # Log multi-timeframe insights with market cap
                logger.info("📊 MTF ANALYSIS %s: trend=%s, confluence=%.2f, risk=%s, sizing=%.2fx", 
                           symbol, mtf_signal.overall_trend, mtf_signal.trend_confluence, 
                           mtf_signal.risk_level, mtf_signal.position_sizing_multiplier)
                logger.info("💰 MARKET CAP %s: category=%s, liquidity=%.2f, cap_risk_mult=%.2fx", 
                           symbol, mtf_signal.market_cap_category, 
                           mtf_signal.liquidity_score, mtf_signal.market_cap_risk_multiplier)
                
                # 4. MACRO-ECONOMIC EXPOSURE ADJUSTMENT
                if macro_env and macro_env.recommended_exposure < 0.5:
                    logger.warning("⚠️ MACRO RISK: Recommended exposure %.2f < 50%% - Increasing confidence requirement",
                                 macro_env.recommended_exposure)
                    required_confidence *= 1.2  # Increase threshold in unfavorable macro conditions
                
                # 5. MARKET STRUCTURE CONFIRMATION
                if market_structure:
                    if market_structure.structure_strength < 0.3:
                        logger.warning("⚠️ WEAK MARKET STRUCTURE: strength=%.2f - Increasing confidence requirement",
                                     market_structure.structure_strength)
                        required_confidence *= 1.15
                    elif market_structure.structure_strength > 0.7:
                        logger.info("✅ STRONG MARKET STRUCTURE: strength=%.2f - Reducing confidence requirement",
                                   market_structure.structure_strength)
                        required_confidence *= 0.95
                
                # Execute decision if warranted
                executed = False
                if trading_signal.decision in ["BUY", "SELL"] and optimal_size > 0:
                    # Store advanced analytics context for execution
                    advanced_context = {
                        'market_regime': market_regime,
                        'optimal_params': optimal_params,
                        'market_structure': market_structure,
                        'macro_env': macro_env
                    }
                    
                    executed = self._execute_optimized_decision(
                        symbol=symbol,
                        analysis_package=analysis_package,
                        advanced_context=advanced_context
                    )
                
                # Record performance metrics
                self._performance_monitor.record_metric(
                    "pipeline", "decision_confidence", trading_signal.confidence
                )
                self._performance_monitor.record_metric(
                    "pipeline", "optimal_position_size", optimal_size
                )
                
                return TradeResult(symbol, trading_signal.decision, executed, technical_levels)
                
            except Exception as exc:
                logger.error("Optimized pipeline cycle failed for %s: %s", symbol, exc)
                self._performance_monitor.record_success_rate("pipeline", "run_cycle", False)
                
                # Fallback to legacy method
                return self._run_cycle_legacy(symbol)
    
    def _run_cycle_legacy(self, symbol: str) -> TradeResult:
        """Legacy pipeline cycle as fallback."""
        logger.warning("Using legacy pipeline cycle for %s", symbol)
        
        state = self._gather_market_state(symbol)
        if not state:
            return TradeResult(symbol, "HOLD", False, None)

        # Evaluate and manage existing position
        self._evaluate_open_position(state)
        
        # If position was closed by intelligent management, don't proceed with new trades
        if symbol not in self._positions:
            # Position was closed, check if we should re-enter
            pass  # Continue with normal trading logic
        else:
            # Position still exists, hold
            return TradeResult(symbol, "HOLD", False, None)

        features = self._compute_features(state)
        decision = self._decide_trade(symbol, features)
        executed, levels = self._execute_decision(symbol, decision, state, features)

        return TradeResult(symbol, decision, executed, levels)
    
    def _execute_optimized_decision(self, symbol: str, analysis_package, advanced_context: Optional[dict] = None) -> bool:
        """Execute trading decision using optimized analysis package with advanced analytics."""
        try:
            with PerformanceTimer("pipeline", "execute_decision"):
                trading_signal = analysis_package.trading_signal
                current_price = analysis_package.current_price
                technical_levels = analysis_package.technical_levels
                optimal_size = analysis_package.optimal_position_size
                
                # Apply advanced risk management adjustments
                if advanced_context:
                    optimal_params = advanced_context.get('optimal_params')
                    macro_env = advanced_context.get('macro_env')
                    market_structure = advanced_context.get('market_structure')
                    
                    # Adjust stop-loss based on regime
                    if optimal_params:
                        stop_loss_adjustment = optimal_params.stop_loss_multiplier
                        stop_distance = abs(technical_levels[0] - current_price)
                        adjusted_stop = current_price - (stop_distance * stop_loss_adjustment)
                        technical_levels = (adjusted_stop, technical_levels[1])
                        logger.info("🎯 ADJUSTED STOP-LOSS: %.6f -> %.6f (multiplier=%.2f)",
                                   technical_levels[0], adjusted_stop, stop_loss_adjustment)
                    
                    # Adjust position size based on macro exposure
                    if macro_env and macro_env.recommended_exposure < 1.0:
                        optimal_size *= macro_env.recommended_exposure
                        logger.info("📉 MACRO ADJUSTMENT: Position size reduced by %.0f%% due to macro risk",
                                   (1 - macro_env.recommended_exposure) * 100)
                
                if trading_signal.decision == "BUY":
                    return self._execute_buy_order(
                        symbol=symbol,
                        price=current_price,
                        amount=optimal_size,
                        stop_loss=technical_levels[0],
                        take_profit=technical_levels[1],
                        analysis_package=analysis_package,
                        advanced_context=advanced_context
                    )
                elif trading_signal.decision == "SELL":
                    # For now, we only handle BUY orders (spot trading)
                    logger.info("SELL signal for %s, but only BUY orders supported in spot trading", symbol)
                    return False
                
                return False
                
        except Exception as exc:
            logger.error("Optimized decision execution failed for %s: %s", symbol, exc)
            self._performance_monitor.record_success_rate("pipeline", "execute_decision", False)
            return False
    
    def _execute_buy_order(
        self, 
        symbol: str, 
        price: float, 
        amount: float, 
        stop_loss: float, 
        take_profit: float,
        analysis_package,
        advanced_context: Optional[dict] = None
    ) -> bool:
        """Execute BUY order with enhanced logging, monitoring, and advanced analytics."""
        try:
            # Risk check
            if not self._risk_check(symbol, amount):
                logger.warning("Risk check failed for %s", symbol)
                return False
            
            # Log enhanced context
            regime = analysis_package.trading_signal.regime_context.primary_regime.value
            confidence = analysis_package.trading_signal.confidence
            
            # Log advanced analytics context
            if advanced_context:
                market_regime = advanced_context.get('market_regime')
                market_structure = advanced_context.get('market_structure')
                macro_env = advanced_context.get('macro_env')
                
                logger.info(
                    "🚀 ADVANCED BUY EXECUTION: %s | amount=%.6f, price=%.6f",
                    symbol, amount, price
                )
                if market_regime:
                    logger.info("   📊 Regime: %s (%.2f strength, %.2f volatility)",
                               market_regime.regime_type, market_regime.strength, market_regime.volatility)
                if market_structure:
                    logger.info("   🏗️ Structure: %s trend, %s smart money (%.2f strength)",
                               market_structure.trend_structure, market_structure.smart_money_direction,
                               market_structure.structure_strength)
                if macro_env:
                    logger.info("   🌍 Macro: %s phase, %s sentiment, %s risk",
                               macro_env.market_phase, macro_env.crypto_sentiment, macro_env.macro_risk_level)
            else:
                logger.info(
                    "Executing BUY for %s: amount=%.6f, price=%.6f, regime=%s, confidence=%.2f",
                    symbol, amount, price, regime, confidence
                )
            
            # Submit market order
            order = self._submit_order(symbol, "market", "buy", amount, price, params={"tdMode": "cash"})
            if not order:
                return False
            
            # Extract actual fill details
            filled_amount = self._extract_filled_amount(order, default=amount)
            actual_entry = self._extract_entry_price(order, default=price)
            sell_amount = filled_amount * 0.999 if filled_amount else 0.0
            
            if sell_amount <= 0:
                logger.warning("No filled amount available for %s to attach protection orders", symbol)
                return False
            
            # Place OCO protection orders
            logger.info("🛡️ PLACING OCO PROTECTION: %s - Amount: %.6f, SL: %.6f, TP: %.6f, Entry: %.6f", 
                       symbol, sell_amount, stop_loss, take_profit, actual_entry)
            algo_id = self._place_protection_orders(
                symbol, sell_amount, stop_loss, take_profit, entry_price=actual_entry
            )
            
            if algo_id:
                logger.info("✅ OCO PROTECTION PLACED: %s - Algo ID: %s", symbol, algo_id)
            else:
                logger.error("❌ OCO PROTECTION FAILED: %s - No algo ID returned", symbol)
            
            # Create position record with enhanced context
            managed_by_exchange = algo_id is not None
            position = Position(
                symbol=symbol,
                side="long",
                amount=filled_amount,
                entry_price=actual_entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                order_id=order.get("id"),
                protection_algo_id=algo_id,
                managed_by_exchange=managed_by_exchange,
                entry_time=time.time()  # Current timestamp for new positions
            )
            
            self._positions[symbol] = position
            
            # Record performance metrics
            self._performance_monitor.record_success_rate("pipeline", "execute_buy", True)
            self._performance_monitor.record_metric("pipeline", "position_size", filled_amount)
            self._performance_monitor.record_metric("pipeline", "entry_price", actual_entry)
            
            # Record trade entry for performance tracking
            self._daily_performance.record_trade_entry(
                symbol=symbol,
                entry_price=actual_entry,
                amount=filled_amount,
                confidence=analysis_package.trading_signal.confidence
            )
            
            # Update dynamic optimizer with trade parameters
            if advanced_context and advanced_context.get('optimal_params'):
                try:
                    trade_params = {
                        'confidence_threshold': advanced_context['optimal_params'].confidence_threshold,
                        'stop_loss_multiplier': advanced_context['optimal_params'].stop_loss_multiplier,
                        'entry_price': actual_entry,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit
                    }
                    # Trade result will be updated on exit
                    logger.debug("Trade parameters recorded for optimization learning")
                except Exception:
                    pass
            
            logger.info(
                "✅ BUY EXECUTED: %s | filled=%.6f at %.6f | OCO=%s | regime=%s",
                symbol, filled_amount, actual_entry, "YES" if algo_id else "NO", regime
            )
            
            return True
            
        except Exception as exc:
            logger.error("BUY order execution failed for %s: %s", symbol, exc)
            self._performance_monitor.record_success_rate("pipeline", "execute_buy", False)
            return False
    
    def _get_current_balance(self) -> float:
        """Get current USDT balance with caching."""
        try:
            balance = self._okx.fetch_balance()
            return float(balance.get("free", {}).get("USDT", 0.0))
        except Exception as exc:
            logger.warning("Failed to get current balance: %s", exc)
            return 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _gather_market_state(self, symbol: str) -> MarketState:
        ticker = self._okx.fetch_ticker(symbol)
        order_book_raw = self._okx.fetch_order_book(symbol)
        order_book = OrderBookSnapshot(order_book_raw.get("bids", []), order_book_raw.get("asks", []))
        macro_events = list(self._macro_provider.latest_events(limit=5))

        prices: list[float] = []
        try:
            ohlcv = self._okx.fetch_ohlcv(symbol, timeframe="1m", limit=200)
            prices = [candle[4] for candle in ohlcv if len(candle) >= 5]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch OHLCV for %s: %s", symbol, exc)

        last_price = ticker.get("last") if ticker else None
        if not prices and last_price is not None:
            prices = [last_price] * 20

        if not prices:
            raise RuntimeError(f"No price data available for {symbol}")

        risk_series = []
        if len(prices) > 1:
            risk_series = [prices[i + 1] - prices[i] for i in range(len(prices) - 1)]

        risk_metrics = self._risk.compute(risk_series) if risk_series else None

        state = MarketState(
            symbol=symbol,
            prices=prices,
            order_book=order_book,
            macro_events=macro_events,
            risk_metrics=risk_metrics,
        )
        logger.debug("Market state for %s: %s", symbol, state)
        return state

    def _compute_features(self, state: MarketState) -> dict[str, float]:
        prices = list(state.prices)
        min_required = 20
        if len(prices) < min_required:
            logger.warning(
                "Insufficient price history (%s points) for %s; using fallback indicators",
                len(prices),
                state.symbol,
            )
            last_price = prices[-1]
            ema_fast = last_price
            ema_slow = last_price
            rsi_value = 50.0
        else:
            ema_fast = ema(prices, window=5)[-1]
            ema_slow = ema(prices, window=20)[-1]
            rsi_value = rsi(prices, window=14)[-1]
        imbalance = self._liquidity.imbalance(state.order_book, level=5)
        spread = state.order_book.spread()

        features = {
            "ema_fast": ema_fast,
            "ema_slow": ema_slow,
            "rsi": rsi_value,
            "order_book_imbalance": imbalance,
            "spread": spread,
        }
        logger.debug("Computed features for %s: %s", state.symbol, features)
        return features

    def _decide_trade(self, symbol: str, features: dict[str, float]) -> str:
        """Enhanced trading decision using regime detection and sentiment analysis."""
        try:
            # Get multi-timeframe data for enhanced analysis
            mtf_data = self._market_data.get_multi_timeframe_data(symbol)
            if not mtf_data:
                logger.warning("No multi-timeframe data for %s, using simple decision logic", symbol)
                return self._simple_decision_logic(symbol, features)
            
            # Get current price
            ticker = self._okx.fetch_ticker(symbol)
            current_price = ticker.get("last", 0) if ticker else 0
            if current_price <= 0:
                logger.warning("Invalid current price for %s", symbol)
                return "HOLD"
            
            # Get order book for microstructure analysis
            order_book = None
            try:
                order_book_raw = self._okx.fetch_order_book(symbol, limit=10)
                order_book = {
                    'bids': order_book_raw.get('bids', []),
                    'asks': order_book_raw.get('asks', [])
                }
            except Exception as exc:
                logger.debug("Could not fetch order book for %s: %s", symbol, exc)
            
            # Use enhanced decision engine
            trading_signal = self._decision_engine.make_trading_decision(
                symbol=symbol,
                mtf_data=mtf_data,
                current_price=current_price,
                technical_features=features,
                order_book=order_book
            )
            
            # Check if we already have a position
            has_position = symbol in self._positions
            
            # Adjust decision based on existing position
            if has_position:
                if trading_signal.decision == "BUY":
                    # Don't add to existing long position
                    trading_signal.decision = "HOLD"
            
            dominant_sentiment = max(trading_signal.sentiment_scores.keys(), 
                                   key=lambda k: trading_signal.sentiment_scores[k])
            
            logger.info(
                "Enhanced decision for %s: %s (confidence=%.2f, regime=%s, sentiment=%s)",
                symbol, decision, trading_signal.confidence, regime, dominant_sentiment
            )
            
            # Log reasoning
            for reason in trading_signal.reasoning:
                logger.debug("Decision reasoning for %s: %s", symbol, reason)
            
            # Store signal for potential use in position sizing
            setattr(self, f'_last_signal_{symbol}', trading_signal)
            
            return decision
            
        except Exception as exc:
            logger.error("Enhanced decision making failed for %s: %s", symbol, exc)
            return self._simple_decision_logic(symbol, features)
    
    def _simple_decision_logic(self, symbol: str, features: dict[str, float]) -> str:
        """Fallback simple decision logic."""
        has_position = symbol in self._positions
        ema_fast = features.get("ema_fast", 0)
        ema_slow = features.get("ema_slow", 0)
        rsi_value = features.get("rsi", 50)

        if has_position:
            if ema_fast < ema_slow or rsi_value > 65:
                decision = "SELL"
            else:
                decision = "HOLD"
        else:
            if ema_fast > ema_slow and rsi_value < 70:
                decision = "BUY"
            else:
                decision = "HOLD"

        logger.info("Simple decision for %s: %s", symbol, decision)
        return decision

    def _execute_decision(
        self,
        symbol: str,
        decision: str,
        state: MarketState,
        features: dict[str, float],
    ) -> tuple[bool, Optional[tuple[float, float]]]:
        if decision == "HOLD":
            logger.info("No action for %s", symbol)
            return False, None

        existing_position = self._positions.get(symbol)

        ticker = self._okx.fetch_ticker(symbol)
        if not ticker:
            logger.error("Cannot execute decision; missing ticker data for %s", symbol)
            return False, None

        price = ticker.get("ask") if decision == "BUY" else ticker.get("bid")
        if price is None:
            logger.error("Missing price data for %s", symbol)
            return False, None

        base_amount = self._config.bot.default_trade_volume

        if decision == "BUY":
            if existing_position:
                logger.info("Position already open for %s; skipping additional BUY", symbol)
                return False, None
            if len(self._positions) >= self._config.bot.max_concurrent_positions:
                logger.info("Max concurrent positions reached; skipping %s", symbol)
                return False, None
            # compute base SL/TP levels (will be adjusted in _place_protection_orders)
            stop_loss, take_profit = self._calculate_trade_levels(decision, price, list(state.prices), symbol)
            amount = self._size_position(
                symbol,
                price,
                stop_loss,
                max_notional=self._config.bot.max_market_order_notional,
                fallback_amount=base_amount,
            )

            if not amount or amount <= 0:
                logger.warning("Computed trade size for %s is non-positive; skipping", symbol)
                return False, None

            if not self._risk_check(symbol, amount):
                logger.warning("Risk check failed for %s, skipping execution", symbol)
                return False, None

            logger.info(
                "Executing BUY %s at ~%s (target SL=%.1f%%, TP=%.1f%%)", symbol, price, 10.0, 30.0
            )
            order = self._submit_order(symbol, "market", "buy", amount, price, params={"tdMode": "cash"})
            if order:
                filled_amount = self._extract_filled_amount(order, default=amount)
                actual_entry = self._extract_entry_price(order, default=price)
                sell_amount = filled_amount * 0.999 if filled_amount else 0.0
                if sell_amount <= 0:
                    logger.warning("No filled amount available for %s to attach protection orders", symbol)
                algo_id = None
                if sell_amount > 0:
                    # Recalculate SL/TP based on actual fill price
                    stop_loss, take_profit = self._calculate_trade_levels(decision, actual_entry, list(state.prices), symbol)
                    algo_id = self._place_protection_orders(
                        symbol,
                        sell_amount,
                        stop_loss,
                        take_profit,
                        entry_price=actual_entry,
                    )
                managed_by_exchange = algo_id is not None
                if not managed_by_exchange:
                    logger.warning("Protection orders not registered for %s; reverting to manual management", symbol)
                self._positions[symbol] = Position(
                    symbol=symbol,
                    side="buy",
                    amount=amount,
                    entry_price=actual_entry,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    order_id=order.get("id"),
                    protection_algo_id=algo_id,
                    managed_by_exchange=managed_by_exchange,
                    entry_time=time.time()  # Current timestamp for fallback positions
                )
                return True, (stop_loss, take_profit)
            if self._last_order_error:
                self._handle_order_error(symbol, self._last_order_error)
            return False, None

        if decision == "SELL" and existing_position:
            self._cancel_protection_orders(existing_position)
            logger.info(
                "Closing position for %s at market price %s (SL=%s, TP=%s)",
                symbol,
                price,
                existing_position.stop_loss,
                existing_position.take_profit,
            )
            order = self._submit_order(symbol, "market", "sell", existing_position.amount, price)
            if order:
                del self._positions[symbol]
                return True, None
            return False, None

        logger.info("No executable action for %s with decision %s", symbol, decision)
        return False, None

    def _submit_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        *,
        params: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        self._last_order_error = None
        try:
            payload: dict[str, Any] = dict(params or {})
            request_price = None
            if price is not None:
                request_price = self._okx.price_to_precision(symbol, price)
                payload.setdefault("price", request_price)

            precise_amount = self._okx.amount_to_precision(symbol, amount)

            order = self._okx.create_order(
                symbol,
                order_type,
                side,
                precise_amount,
                price=request_price,
                params=payload or None,
            )
            return order
        except Exception as exc:  # noqa: BLE001
            error_info = self._parse_okx_exception(str(exc))
            if error_info:
                self._last_order_error = error_info
            logger.warning("OKX execution failed for %s %s: %s", symbol, side, exc)
            return None

    def _size_position(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        *,
        max_notional: float,
        fallback_amount: float,
    ) -> float:
        """Size position using enhanced risk management with volatility adjustment and correlation analysis."""
        try:
            # Get current balance
            balance = self._okx.fetch_balance()
            quote = symbol.split("/")[-1]
            free_quote = 0.0
            try:
                free_quote = float(balance.get("free", {}).get(quote, 0.0))
            except Exception:
                free_quote = 0.0

            if free_quote <= 0:
                logger.warning("No free balance available for %s", symbol)
                return 0.0

            # Use enhanced risk manager for position sizing
            optimal_size = self._enhanced_risk.calculate_position_size(
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=stop_loss,
                current_balance=free_quote,
                existing_positions=self._positions
            )

            if optimal_size <= 0:
                logger.info("Enhanced risk manager recommends zero position size for %s", symbol)
                return 0.0

            # Apply exchange constraints
            min_amt = self._okx.min_order_amount(symbol, entry_price)
            optimal_size = max(optimal_size, min_amt)

            # Apply notional limits
            if max_notional and max_notional > 0:
                max_size_by_notional = max_notional / entry_price
                optimal_size = min(optimal_size, max_size_by_notional)

            # Apply balance constraints
            max_affordable = free_quote / entry_price
            optimal_size = min(optimal_size, max_affordable)

            # Apply exchange precision
            try:
                optimal_size = self._okx.amount_to_precision(symbol, optimal_size)
            except Exception:
                pass

            # Final validation
            if optimal_size < min_amt:
                logger.warning("Optimal size %.8f below minimum %.8f for %s", optimal_size, min_amt, symbol)
                return 0.0

            # Log risk metrics
            risk_summary = self._enhanced_risk.get_risk_summary(self._positions, free_quote)
            logger.info(
                "Enhanced position sizing for %s: size=%.6f, portfolio_risk=%.2f%%, drawdown=%.2f%%",
                symbol, optimal_size, risk_summary['portfolio_risk_pct'], risk_summary['current_drawdown_pct']
            )

            return float(optimal_size)

        except Exception as exc:
            logger.error("Enhanced position sizing failed for %s: %s", symbol, exc)
            # Fallback to simple sizing
            return self._fallback_position_sizing(symbol, entry_price, stop_loss, max_notional, fallback_amount)

    def _fallback_position_sizing(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        max_notional: float,
        fallback_amount: float,
    ) -> float:
        """Fallback position sizing method."""
        try:
            balance = self._okx.fetch_balance()
            quote = symbol.split("/")[-1]
            free_quote = float(balance.get("free", {}).get(quote, 0.0))
            
            if free_quote <= 0:
                return 0.0
            
            risk_pct = max(min(self._config.bot.risk_per_trade_pct, 1.0), 0.001)
            amount = (free_quote * risk_pct) / entry_price
            
            # Apply constraints
            min_amt = self._okx.min_order_amount(symbol, entry_price)
            amount = max(amount, min_amt)
            
            if max_notional and max_notional > 0:
                amount = min(amount, max_notional / entry_price)
            
            max_affordable = free_quote / entry_price
            amount = min(amount, max_affordable)
            
            try:
                amount = self._okx.amount_to_precision(symbol, amount)
            except Exception:
                pass
            
            return max(0.0, float(amount))
            
        except Exception:
            return fallback_amount
    def _risk_check(self, symbol: str, volume: float) -> bool:
        try:
            balance = self._okx.fetch_balance()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Risk check skipped due to balance fetch error: %s", exc)
            return True

        quote = symbol.split("/")[-1]
        free_balance = balance.get("free", {}).get(quote, 0.0)
        min_balance = self._config.bot.min_quote_balance
        if free_balance < min_balance:
            logger.warning("Insufficient balance for %s: %.2f required, %.2f available", symbol, min_balance, free_balance)
            return False
        return True

    def _evaluate_open_position(self, state: MarketState) -> None:
        """Enhanced position evaluation with intelligent sell/hold decisions."""
        position = self._positions.get(state.symbol)
        if not position:
            return

        last_price = state.prices[-1]
        
        # Basic stop-loss/take-profit for exchange-managed positions
        if position.managed_by_exchange:
            return

        # Traditional stop-loss/take-profit checks
        if position.side == "buy":
            if last_price <= position.stop_loss:
                logger.info("Stop-loss hit for %s at %.4f", state.symbol, last_price)
                self._close_position(state.symbol, position, reason="stop-loss")
                return
            elif last_price >= position.take_profit:
                logger.info("Take-profit hit for %s at %.4f", state.symbol, last_price)
                self._close_position(state.symbol, position, reason="take-profit")
                return
        
        # Enhanced intelligent position management
        self._intelligent_position_management(state, position, last_price)

    def _intelligent_position_management(self, state: MarketState, position: Position, current_price: float) -> None:
        """Intelligent position management based on market analysis."""
        try:
            symbol = state.symbol
            
            # Get fresh market analysis for the position
            mtf_data = self._market_data.get_multi_timeframe_data(symbol)
            if not mtf_data:
                logger.debug("No multi-timeframe data for position analysis of %s", symbol)
                return
            
            # Get order book for liquidity analysis
            try:
                order_book = self._okx.fetch_order_book(symbol, limit=20)
                ticker = self._okx.fetch_ticker(symbol)
            except Exception as exc:
                logger.debug("Failed to fetch market data for position analysis of %s: %s", symbol, exc)
                return
            
            # Calculate position performance
            entry_price = position.entry_price
            pnl_percentage = (current_price - entry_price) / entry_price * 100
            
            # Compute technical features from market state
            features = self._compute_features(state)
            if not features:
                logger.debug("Could not compute features for position analysis of %s", symbol)
                return
            
            # Get trading signal for current market conditions
            trading_signal = self._decision_engine.make_trading_decision(
                symbol=symbol,
                mtf_data=mtf_data,
                current_price=current_price,
                technical_features=features,
                order_book=order_book
            )
            
            # Enhanced position management logic
            should_sell, reason = self._should_sell_position(
                position, trading_signal, pnl_percentage, current_price, ticker, order_book
            )
            
            if should_sell:
                logger.info("INTELLIGENT SELL: %s - %s (PnL: %.2f%%)", symbol, reason, pnl_percentage)
                
                # Record trade exit for performance tracking
                self._daily_performance.record_trade_exit(
                    symbol=symbol,
                    exit_price=current_price,
                    reason=reason
                )
                
                self._close_position(symbol, position, reason=f"intelligent-{reason}")
            else:
                logger.info("INTELLIGENT HOLD: %s - Conditions favor holding (PnL: %.2f%%, confidence: %.2f)", 
                           symbol, pnl_percentage, trading_signal.confidence)
                
        except Exception as exc:
            logger.error("Error in intelligent position management for %s: %s", state.symbol, exc)
    
    def _should_sell_position(
        self, 
        position: Position, 
        trading_signal: TradingSignal, 
        pnl_percentage: float,
        current_price: float,
        ticker: Dict[str, Any],
        order_book: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Enhanced profit-focused position management for daily trading."""
        
        # 🎯 DAILY TRADING PROFIT OPTIMIZATION
        
        # 1. QUICK PROFIT TAKING - Secure small but consistent profits
        if pnl_percentage > 3.0:  # Take profits at 3%+ (daily trading target)
            if trading_signal.confidence < 0.4:  # Weakening confidence
                return True, "quick-profit-taking"
            if trading_signal.decision == "SELL":  # Signal turned bearish
                return True, "profit-protection-bearish-signal"
        
        # 2. LARGER PROFIT PROTECTION - Secure bigger gains when available
        if pnl_percentage > 8.0:  # Larger profits available
            if trading_signal.confidence < 0.5:  # Don't be greedy
                return True, "large-profit-protection"
        
        # 3. ENHANCED MARKET-AWARE STOP-LOSS - Prevent excessive stop-loss triggers
        if pnl_percentage < -1.0:  # Earlier intervention at -1%
            try:
                # Get enhanced market condition analysis
                signal_analyzer = get_enhanced_signal_analyzer()
                ticker = self._okx.fetch_ticker(position.symbol)
                current_price = float(ticker["last"])
                
                # Get comprehensive multi-timeframe analysis for position management
                try:
                    # Multi-timeframe analysis for position management
                    mtf_signal = self._multi_tf_analyzer.analyze_all_timeframes(position.symbol)
                    
                    # Enhanced market condition from single timeframe
                    candles = self._market_data.get_candles(position.symbol, "5m", limit=50)
                    market_condition = signal_analyzer.analyze_market_condition(candles, current_price)
                    
                    # MULTI-TIMEFRAME ADAPTIVE STOP-LOSS
                    base_threshold = -1.5
                    
                    # Multi-timeframe trend analysis
                    if mtf_signal.trend_confluence > 0.7 and mtf_signal.overall_trend == "bullish":
                        # Strong bullish confluence across timeframes - very patient
                        stop_threshold = -3.5
                        reason_suffix = "strong-bullish-confluence"
                    elif mtf_signal.trend_confluence > 0.6:
                        # Good confluence - be patient
                        stop_threshold = -2.5
                        reason_suffix = "good-confluence"
                    elif mtf_signal.risk_level == "high":
                        # High risk across timeframes - tighter stops
                        stop_threshold = -1.2
                        reason_suffix = "high-risk-timeframes"
                    elif market_condition.risk_level == "low" and market_condition.trend_strength > 0.6:
                        # Strong single-timeframe trend, low risk
                        stop_threshold = -2.0
                        reason_suffix = "strong-trend-protection"
                    elif market_condition.volatility_regime == "high":
                        # High volatility - moderate stops
                        stop_threshold = -2.5
                        reason_suffix = "high-volatility-protection"
                    else:
                        # Normal conditions
                        stop_threshold = base_threshold
                        reason_suffix = "normal-conditions"
                    
                    # Check if we should exit
                    if pnl_percentage < stop_threshold:
                        if trading_signal.confidence < 0.4:
                            return True, f"enhanced-stop-loss-{reason_suffix}"
                        if trading_signal.decision == "SELL" and trading_signal.confidence > 0.7:
                            return True, f"enhanced-stop-sell-{reason_suffix}"
                    else:
                        # Log why we're holding
                        logger.info("🛡️ ENHANCED STOP: %s at %.1f%% loss - %s market (trend=%.2f, risk=%s) allows %.1f%% threshold", 
                                   position.symbol, pnl_percentage, market_condition.volatility_regime,
                                   market_condition.trend_strength, market_condition.risk_level, stop_threshold)
                        
                except Exception:
                    # Fallback to simple volatility-based stop
                    daily_range = (float(ticker.get("high", current_price)) - float(ticker.get("low", current_price)))
                    volatility = daily_range / current_price if current_price > 0 else 0.05
                    
                    if volatility > 0.08:
                        stop_threshold = -2.5
                    elif volatility > 0.05:
                        stop_threshold = -2.0
                    else:
                        stop_threshold = -1.5
                    
                    if pnl_percentage < stop_threshold:
                        return True, "fallback-volatility-stop"
                    
            except Exception as exc:
                logger.warning("Enhanced stop-loss analysis failed for %s: %s", position.symbol, exc)
                # Conservative fallback
                if pnl_percentage < -2.0:
                    return True, "conservative-fallback-stop"
        
        # 4. REGIME CHANGE - Exit when market regime becomes unfavorable
        regime = trading_signal.regime_context.primary_regime.value
        if regime in ["trending_down", "breakdown"]:
            if trading_signal.confidence > 0.5:  # Confident regime detection
                return True, f"regime-change-{regime}"
        
        # 4. SENTIMENT DETERIORATION - Exit when sentiment turns very negative
        sentiment_scores = trading_signal.sentiment_scores
        bearish_sentiment = sentiment_scores.get('bearish', 0) + sentiment_scores.get('fear', 0)
        if bearish_sentiment > 0.7:  # Strong negative sentiment
            return True, "sentiment-deterioration"
        
        # 5. LIQUIDITY CRISIS - Exit when liquidity dries up
        try:
            bids = order_book.get("bids", [])[:5]
            asks = order_book.get("asks", [])[:5]
            if bids and asks:
                bid_volume = sum(float(level[1]) for level in bids)
                ask_volume = sum(float(level[1]) for level in asks)
                total_liquidity = bid_volume + ask_volume
                
                # If liquidity is very low, exit to avoid slippage
                if total_liquidity < 100:  # Adjust threshold as needed
                    return True, "liquidity-crisis"
        except Exception:
            pass
        
        # 6. MOMENTUM REVERSAL - Exit when strong momentum reverses
        price_change = float(ticker.get("percentage", 0))
        if price_change < -5.0 and pnl_percentage > 0:  # Strong negative momentum while profitable
            return True, "momentum-reversal"
        
        # 7. VOLATILITY SPIKE - Exit during extreme volatility if losing
        try:
            high = float(ticker.get("high", 0))
            low = float(ticker.get("low", 0))
            close = float(ticker.get("last", 0))
            if close > 0:
                daily_volatility = (high - low) / close
                if daily_volatility > 0.20 and pnl_percentage < -1.0:  # >20% volatility while losing
                    return True, "volatility-spike"
        except Exception:
            pass
        
        # 8. TIME-BASED EXIT - Exit very old positions that aren't performing
        import time
        # Handle positions that might not have entry_time (backward compatibility)
        entry_time = getattr(position, 'entry_time', None)
        if entry_time:
            position_age_hours = (time.time() - entry_time) / 3600
            if position_age_hours > 24 and -1.0 < pnl_percentage < 1.0:  # Flat performance after 24h
                return True, "time-based-flat-performance"
        
        # Default: Hold the position
        return False, "conditions-favor-holding"

    def _close_position(self, symbol: str, position: Position, reason: str) -> None:
        self._cancel_protection_orders(position)
        try:
            self._okx.create_order(symbol, "market", "sell", position.amount)
            logger.info("Closed %s due to %s", symbol, reason)
            del self._positions[symbol]
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to close %s (%s): %s", symbol, reason, exc)

    def _cancel_protection_orders(self, position: Position) -> None:
        if position.protection_algo_id:
            try:
                self._okx.cancel_algo_orders([position.protection_algo_id])
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to cancel algo protection %s for %s: %s",
                    position.protection_algo_id,
                    position.symbol,
                    exc,
                )
        for order_id in (position.stop_order_id, position.take_profit_order_id):
            if not order_id:
                continue
            try:
                self._okx.cancel_order(order_id, position.symbol)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to cancel protective order %s for %s: %s", order_id, position.symbol, exc)

    def _place_protection_orders(
        self,
        symbol: str,
        amount: float,
        stop_loss: float,
        take_profit: float,
        *,
        entry_price: Optional[float] = None,
    ) -> Optional[str]:
        inst_id = symbol.replace("/", "-")
        try:
            sz = self._okx.amount_to_precision(symbol, amount, as_string=True)
        except Exception:
            sz = str(amount)

        # Use entry_price if provided, otherwise use stop_loss/take_profit as-is
        if not entry_price or entry_price <= 0:
            logger.warning("No valid entry price for %s OCO; using calculated levels", symbol)
            entry_price = (stop_loss + take_profit) / 2

        entry = float(entry_price)
        tick = self._get_tick_size(symbol)
        min_tick = max(tick or 0.0, entry * 0.0001)

        # Ensure TP is above entry and SL is below entry
        if take_profit <= entry:
            take_profit = entry + min_tick
        if stop_loss >= entry:
            stop_loss = entry - min_tick
        if stop_loss <= 0:
            logger.warning("Stop-loss would be <= 0 for %s; skipping OCO", symbol)
            return None

        tp_trigger = self._okx.price_to_precision(symbol, take_profit, as_string=True)
        sl_trigger = self._okx.price_to_precision(symbol, stop_loss, as_string=True)

        payload = {
            "instId": inst_id,
            "tdMode": "cash",
            "side": "sell",
            "ordType": "oco",
            "sz": str(sz),
            "tpTriggerPx": tp_trigger,
            "tpOrdPx": "-1",
            "tpTriggerPxType": "last",
            "slTriggerPx": sl_trigger,
            "slOrdPx": "-1",
            "slTriggerPxType": "last",
        }

        logger.info("🔄 SENDING OCO REQUEST: %s - Payload: %s", symbol, payload)
        try:
            response = self._okx.create_algo_order(payload)
            logger.info("📋 OCO RESPONSE: %s - %s", symbol, response)
        except Exception as exc:  # noqa: BLE001
            logger.error("❌ OCO REQUEST FAILED: %s - %s", symbol, exc)
            return None

        data = (response or {}).get("data") or []
        if not data:
            logger.warning("No response data when registering OCO for %s: %s", symbol, response)
            return None

        entry = data[0]
        if entry.get("sCode") not in {None, "0"}:
            logger.warning(
                "Failed to register OCO for %s: code=%s message=%s payload=%s response=%s",
                symbol,
                entry.get("sCode"),
                entry.get("sMsg"),
                payload,
                response,
            )
            if entry.get("sCode") == "51155":
                self._mark_symbol_restricted(symbol)
            return None

        algo_id = entry.get("algoId")
        if not algo_id:
            logger.warning("Missing algoId in OCO response for %s: %s", symbol, entry)
            return None

        logger.info("Registered OKX conditional OCO for %s (algoId=%s)", symbol, algo_id)
        return algo_id

    def _load_restricted_symbols(self) -> None:
        if not self._restricted_cache_path.exists():
            return
        try:
            data = json.loads(self._restricted_cache_path.read_text())
            if isinstance(data, list):
                self._restricted_symbols.update(str(item) for item in data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load restricted symbol cache: %s", exc)

    def _persist_restricted_symbols(self) -> None:
        try:
            self._restricted_cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = sorted(self._restricted_symbols)
            self._restricted_cache_path.write_text(json.dumps(payload))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to persist restricted symbols: %s", exc)

    def _parse_okx_exception(self, message: str) -> Optional[dict[str, str]]:
        code_match = re.search(r'"sCode"\s*:\s*"([^"]+)"', message)
        msg_match = re.search(r'"sMsg"\s*:\s*"([^"]*)"', message)
        if not code_match and "code" in message:
            code_match = re.search(r'"code"\s*:\s*"([^"]+)"', message)
        if not code_match:
            return None
        return {
            "code": code_match.group(1),
            "message": msg_match.group(1) if msg_match else "",
            "raw": message,
        }

    def _handle_order_error(self, symbol: str, error: dict[str, str]) -> None:
        code = error.get("code")
        if code == "51155":
            self._mark_symbol_restricted(symbol)
        elif code == "51201":
            logger.warning(
                "Market order for %s exceeded OKX notional cap: %s",
                symbol,
                error.get("message"),
            )
        elif code == "51008":
            logger.warning(
                "Insufficient balance when placing OCO for %s: %s",
                symbol,
                error.get("message"),
            )

    def _mark_symbol_restricted(self, symbol: str) -> None:
        if symbol not in self._restricted_symbols:
            logger.warning("Marking %s as restricted by OKX compliance (51155)", symbol)
            self._restricted_symbols.add(symbol)
            setattr(self._onchain_provider, "restricted_symbols", self._restricted_symbols)
            self._persist_restricted_symbols()

    def _extract_filled_amount(self, order: dict[str, Any], default: float) -> float:
        try:
            filled = order.get("filled")
            if filled is None:
                info = order.get("info", {})
                filled = info.get("fillSz") or info.get("accFillSz") or order.get("amount")
            filled = float(filled)
        except (TypeError, ValueError):
            filled = default
        if not filled or filled <= 0:
            return default
        return float(filled)

    def _extract_entry_price(self, order: dict[str, Any], default: float) -> float:
        try:
            avg_price = order.get("average") or order.get("price")
            if avg_price is None:
                info = order.get("info", {})
                avg_price = info.get("avgPx") or info.get("fillPx")
            return float(avg_price)
        except (TypeError, ValueError):
            return default

    def _get_tick_size(self, symbol: str) -> float:
        try:
            market = self._okx.get_market(symbol)
        except Exception:
            return 0.0
        precision = market.get("precision", {})
        price_precision = precision.get("price")
        if price_precision is not None:
            try:
                return pow(10, -float(price_precision))
            except Exception:
                pass
        info = market.get("info", {})
        tick = info.get("tickSz") or info.get("tickSize")
        try:
            return float(tick)
        except (TypeError, ValueError):
            return 0.0


    def _calculate_trade_levels(
        self, decision: str, price: float, prices: list[float], symbol: str = ""
    ) -> tuple[float, float]:
        """Calculate dynamic TP/SL levels using enhanced multi-timeframe technical analysis."""
        try:
            # Get multi-timeframe data
            mtf_data = self._market_data.get_multi_timeframe_data(symbol)
            if not mtf_data:
                logger.warning("No multi-timeframe data available for %s, using fallback levels", symbol)
                return self._fallback_levels(decision, price)
            
            # Use enhanced multi-timeframe technical analysis
            stop_loss, take_profit = self._technical.calculate_dynamic_levels_mtf(
                current_price=price,
                mtf_data=mtf_data,
                decision=decision,
                use_fibonacci=True
            )
            
            logger.info(
                "Enhanced technical levels for %s %s at %.6f: SL=%.6f, TP=%.6f",
                decision, symbol, price, stop_loss, take_profit
            )
            
            return stop_loss, take_profit
            
        except Exception as exc:
            logger.warning("Enhanced technical analysis failed for %s: %s, using fallback", symbol, exc)
            return self._fallback_levels(decision, price)
    
    def _fallback_levels(self, decision: str, price: float) -> tuple[float, float]:
        """Fallback percentage-based TP/SL calculation."""
        sl_pct = 0.10
        tp_pct = 0.30

        if decision == "BUY":
            stop_loss = max(price * (1 - sl_pct), 0.0)
            take_profit = price * (1 + tp_pct)
        else:
            stop_loss = price * (1 + sl_pct)
            take_profit = max(price * (1 - tp_pct), 0.0)

        return stop_loss, take_profit
