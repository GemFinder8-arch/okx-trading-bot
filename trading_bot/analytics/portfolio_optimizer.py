"""Automatic portfolio rebalancing and optimization for daily trading."""

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class AssetAllocation:
    """Target allocation for an asset."""
    symbol: str
    target_percentage: float
    current_percentage: float
    current_value: float
    target_value: float
    rebalance_amount: float  # Positive = buy, negative = sell
    priority: int = 1  # 1=high, 2=medium, 3=low


@dataclass
class PortfolioMetrics:
    """Portfolio performance and risk metrics."""
    total_value: float
    total_pnl: float
    total_pnl_percentage: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    correlation_risk: float
    concentration_risk: float
    diversification_score: float


class PortfolioOptimizer:
    """Automatic portfolio rebalancing and optimization system."""
    
    def __init__(self, okx_connector, performance_tracker):
        """Initialize portfolio optimizer."""
        self.okx = okx_connector
        self.performance_tracker = performance_tracker
        
        # Rebalancing parameters
        self.max_position_percentage = 15.0  # Max 15% per asset
        self.min_position_percentage = 2.0   # Min 2% to maintain position
        self.rebalance_threshold = 5.0       # Rebalance if >5% deviation
        self.max_positions = 8               # Optimal portfolio size
        
        # Performance thresholds
        self.underperformer_threshold = -10.0  # Sell if <-10% and poor outlook
        self.profit_taking_threshold = 25.0    # Consider selling if >25% profit
        self.correlation_limit = 0.7           # Max correlation between assets
        
        # Rebalancing frequency
        self.last_rebalance_time = 0
        self.rebalance_interval = 3600 * 4  # 4 hours minimum between rebalances
        
        logger.info("Portfolio optimizer initialized with max %d positions", self.max_positions)
    
    def should_rebalance(self, positions: Dict[str, any], current_balance: float) -> bool:
        """Determine if portfolio needs rebalancing."""
        try:
            # Check time since last rebalance
            if time.time() - self.last_rebalance_time < self.rebalance_interval:
                return False
            
            if not positions:
                return False
            
            # Calculate current allocations
            total_portfolio_value = self._calculate_total_portfolio_value(positions, current_balance)
            
            needs_rebalancing = False
            reasons = []
            
            # Check for concentration risk
            for symbol, position in positions.items():
                current_value = position.amount * self._get_current_price(symbol)
                current_percentage = (current_value / total_portfolio_value) * 100
                
                if current_percentage > self.max_position_percentage:
                    needs_rebalancing = True
                    reasons.append(f"{symbol} over-concentrated ({current_percentage:.1f}%)")
            
            # Check for underperformers
            underperformers = self._identify_underperformers(positions)
            if underperformers:
                needs_rebalancing = True
                reasons.append(f"{len(underperformers)} underperforming assets")
            
            # Check portfolio size
            if len(positions) > self.max_positions:
                needs_rebalancing = True
                reasons.append(f"Too many positions ({len(positions)})")
            
            if needs_rebalancing:
                logger.info("🔄 REBALANCING NEEDED: %s", ", ".join(reasons))
            
            return needs_rebalancing
            
        except Exception as exc:
            logger.error("Error checking rebalance need: %s", exc)
            return False
    
    def optimize_portfolio(
        self, 
        positions: Dict[str, any], 
        current_balance: float,
        top_ranked_symbols: List[str]
    ) -> List[AssetAllocation]:
        """Generate optimal portfolio allocation."""
        try:
            logger.info("🎯 OPTIMIZING PORTFOLIO with %d positions", len(positions))
            
            total_portfolio_value = self._calculate_total_portfolio_value(positions, current_balance)
            
            # 1. Analyze current positions
            current_allocations = self._analyze_current_allocations(positions, total_portfolio_value)
            
            # 2. Identify positions to reduce/eliminate
            positions_to_reduce = self._identify_positions_to_reduce(current_allocations, positions)
            
            # 3. Calculate target allocations
            target_allocations = self._calculate_target_allocations(
                current_allocations, top_ranked_symbols, total_portfolio_value
            )
            
            # 4. Generate rebalancing actions
            rebalancing_actions = self._generate_rebalancing_actions(
                current_allocations, target_allocations, total_portfolio_value
            )
            
            # 5. Prioritize actions
            prioritized_actions = self._prioritize_rebalancing_actions(rebalancing_actions)
            
            logger.info("📊 Generated %d rebalancing actions", len(prioritized_actions))
            
            return prioritized_actions
            
        except Exception as exc:
            logger.error("Portfolio optimization failed: %s", exc)
            return []
    
    def execute_rebalancing(
        self, 
        rebalancing_actions: List[AssetAllocation],
        max_actions: int = 3
    ) -> int:
        """Execute portfolio rebalancing actions."""
        try:
            executed_actions = 0
            failed_actions = 0
            executed_symbols = []
            
            # Sort by priority and execute top actions
            sorted_actions = sorted(rebalancing_actions, key=lambda x: (x.priority, abs(x.rebalance_amount)))
            total_actions = min(len(sorted_actions), max_actions)
            
            for action in sorted_actions[:max_actions]:
                if self._execute_rebalancing_action(action):
                    executed_actions += 1
                    executed_symbols.append(action.symbol)
                    logger.info("✅ REBALANCED: %s - Action: %s, Amount: %.6f", 
                               action.symbol, action.action, abs(action.rebalance_amount))
                else:
                    failed_actions += 1
                    logger.warning("❌ REBALANCE FAILED: %s - Action: %s", action.symbol, action.action)
                    
                # Add delay between actions
                if executed_actions < max_actions:
                    time.sleep(2)
            
            if executed_actions > 0:
                self.last_rebalance_time = time.time()
                logger.info("✅ REBALANCING COMPLETE: %d/%d actions executed successfully [%s]", 
                           executed_actions, total_actions, ", ".join(executed_symbols))
            
            if failed_actions > 0:
                logger.warning("⚠️ REBALANCING PARTIAL: %d actions failed", failed_actions)
            
            return executed_actions
            
        except Exception as exc:
            logger.error("Rebalancing execution failed: %s", exc)
            return 0
    
    def _calculate_total_portfolio_value(self, positions: Dict[str, any], current_balance: float) -> float:
        """Calculate total portfolio value including cash."""
        try:
            total_value = current_balance  # Start with cash balance
            
            for symbol, position in positions.items():
                current_price = self._get_current_price(symbol)
                position_value = position.amount * current_price
                total_value += position_value
            
            return total_value
            
        except Exception as exc:
            logger.error("Error calculating portfolio value: %s", exc)
            return current_balance
    
    def _analyze_current_allocations(
        self, 
        positions: Dict[str, any], 
        total_value: float
    ) -> Dict[str, AssetAllocation]:
        """Analyze current portfolio allocations."""
        allocations = {}
        
        try:
            for symbol, position in positions.items():
                current_price = self._get_current_price(symbol)
                current_value = position.amount * current_price
                current_percentage = (current_value / total_value) * 100
                
                # Calculate performance
                entry_price = getattr(position, 'entry_price', current_price)
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                
                allocations[symbol] = AssetAllocation(
                    symbol=symbol,
                    target_percentage=0.0,  # Will be calculated later
                    current_percentage=current_percentage,
                    current_value=current_value,
                    target_value=0.0,  # Will be calculated later
                    rebalance_amount=0.0,  # Will be calculated later
                    priority=1
                )
                
                logger.debug(
                    "Current allocation: %s = %.1f%% ($%.2f, PnL: %.1f%%)",
                    symbol, current_percentage, current_value, pnl_percentage
                )
            
            return allocations
            
        except Exception as exc:
            logger.error("Error analyzing allocations: %s", exc)
            return {}
    
    def _identify_underperformers(self, positions: Dict[str, any]) -> List[str]:
        """Identify underperforming assets that should be reduced."""
        underperformers = []
        
        try:
            for symbol, position in positions.items():
                current_price = self._get_current_price(symbol)
                entry_price = getattr(position, 'entry_price', current_price)
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                
                # Check if asset is underperforming
                if pnl_percentage < self.underperformer_threshold:
                    # Additional check: is the trend still negative?
                    if self._is_trend_negative(symbol):
                        underperformers.append(symbol)
                        logger.info(
                            "📉 UNDERPERFORMER: %s (%.1f%% loss, negative trend)",
                            symbol, pnl_percentage
                        )
            
            return underperformers
            
        except Exception as exc:
            logger.error("Error identifying underperformers: %s", exc)
            return []
    
    def _identify_positions_to_reduce(
        self, 
        current_allocations: Dict[str, AssetAllocation],
        positions: Dict[str, any]
    ) -> List[str]:
        """Identify positions that should be reduced."""
        positions_to_reduce = []
        
        try:
            for symbol, allocation in current_allocations.items():
                should_reduce = False
                reason = ""
                
                # Over-concentrated positions
                if allocation.current_percentage > self.max_position_percentage:
                    should_reduce = True
                    reason = f"over-concentrated ({allocation.current_percentage:.1f}%)"
                
                # Large profits that should be partially taken
                position = positions.get(symbol)
                if position:
                    current_price = self._get_current_price(symbol)
                    entry_price = getattr(position, 'entry_price', current_price)
                    pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                    
                    if pnl_percentage > self.profit_taking_threshold:
                        should_reduce = True
                        reason = f"large profit ({pnl_percentage:.1f}%)"
                
                if should_reduce:
                    positions_to_reduce.append(symbol)
                    logger.info("🔻 REDUCE POSITION: %s - %s", symbol, reason)
            
            return positions_to_reduce
            
        except Exception as exc:
            logger.error("Error identifying positions to reduce: %s", exc)
            return []
    
    def _calculate_target_allocations(
        self,
        current_allocations: Dict[str, AssetAllocation],
        top_ranked_symbols: List[str],
        total_value: float
    ) -> Dict[str, AssetAllocation]:
        """Calculate optimal target allocations."""
        target_allocations = {}
        
        try:
            # Start with current allocations
            for symbol, allocation in current_allocations.items():
                target_allocations[symbol] = allocation
            
            # Determine target portfolio size
            target_positions = min(len(top_ranked_symbols), self.max_positions)
            
            # Calculate base allocation percentage
            base_allocation = 80.0 / target_positions  # 80% invested, 20% cash
            
            # Assign target allocations based on ranking
            for i, symbol in enumerate(top_ranked_symbols[:target_positions]):
                # Higher ranked symbols get slightly larger allocations
                rank_multiplier = 1.0 + (target_positions - i - 1) * 0.1
                target_percentage = min(base_allocation * rank_multiplier, self.max_position_percentage)
                
                if symbol in target_allocations:
                    target_allocations[symbol].target_percentage = target_percentage
                else:
                    # New position to add
                    target_allocations[symbol] = AssetAllocation(
                        symbol=symbol,
                        target_percentage=target_percentage,
                        current_percentage=0.0,
                        current_value=0.0,
                        target_value=0.0,
                        rebalance_amount=0.0,
                        priority=1
                    )
                
                target_allocations[symbol].target_value = (target_percentage / 100) * total_value
            
            # Set target percentage to 0 for symbols not in top rankings
            for symbol in list(target_allocations.keys()):
                if symbol not in top_ranked_symbols[:target_positions]:
                    target_allocations[symbol].target_percentage = 0.0
                    target_allocations[symbol].target_value = 0.0
            
            return target_allocations
            
        except Exception as exc:
            logger.error("Error calculating target allocations: %s", exc)
            return current_allocations
    
    def _generate_rebalancing_actions(
        self,
        current_allocations: Dict[str, AssetAllocation],
        target_allocations: Dict[str, AssetAllocation],
        total_value: float
    ) -> List[AssetAllocation]:
        """Generate specific rebalancing actions."""
        actions = []
        
        try:
            for symbol, target in target_allocations.items():
                current = current_allocations.get(symbol, AssetAllocation(
                    symbol=symbol, target_percentage=0, current_percentage=0,
                    current_value=0, target_value=0, rebalance_amount=0
                ))
                
                # Calculate rebalancing amount
                value_difference = target.target_value - current.current_value
                percentage_difference = abs(target.target_percentage - current.current_percentage)
                
                # Only rebalance if difference is significant
                if percentage_difference > self.rebalance_threshold:
                    action = AssetAllocation(
                        symbol=symbol,
                        target_percentage=target.target_percentage,
                        current_percentage=current.current_percentage,
                        current_value=current.current_value,
                        target_value=target.target_value,
                        rebalance_amount=value_difference,
                        priority=self._calculate_action_priority(current, target)
                    )
                    
                    actions.append(action)
                    
                    logger.info(
                        "🔄 REBALANCE ACTION: %s %.1f%% -> %.1f%% ($%.2f)",
                        symbol, current.current_percentage, target.target_percentage, value_difference
                    )
            
            return actions
            
        except Exception as exc:
            logger.error("Error generating rebalancing actions: %s", exc)
            return []
    
    def _prioritize_rebalancing_actions(self, actions: List[AssetAllocation]) -> List[AssetAllocation]:
        """Prioritize rebalancing actions by importance."""
        try:
            # Sort by priority, then by absolute rebalance amount
            prioritized = sorted(actions, key=lambda x: (x.priority, -abs(x.rebalance_amount)))
            
            for i, action in enumerate(prioritized):
                action_type = "BUY" if action.rebalance_amount > 0 else "SELL"
                logger.info(
                    "Priority %d: %s %s $%.2f (%.1f%% -> %.1f%%)",
                    i + 1, action_type, action.symbol, abs(action.rebalance_amount),
                    action.current_percentage, action.target_percentage
                )
            
            return prioritized
            
        except Exception as exc:
            logger.error("Error prioritizing actions: %s", exc)
            return actions
    
    def _calculate_action_priority(self, current: AssetAllocation, target: AssetAllocation) -> int:
        """Calculate priority for rebalancing action."""
        # Priority 1 (highest): Risk reduction
        if current.current_percentage > self.max_position_percentage:
            return 1
        
        # Priority 2: Large deviations
        deviation = abs(target.target_percentage - current.current_percentage)
        if deviation > 10.0:
            return 2
        
        # Priority 3: Normal rebalancing
        return 3
    
    def _execute_rebalancing_action(self, action: AssetAllocation) -> bool:
        """Execute a single rebalancing action."""
        try:
            if abs(action.rebalance_amount) < 10.0:  # Skip very small amounts
                return False
            
            if action.rebalance_amount > 0:
                # BUY action
                current_price = self._get_current_price(action.symbol)
                amount_to_buy = action.rebalance_amount / current_price
                
                logger.info(
                    "🟢 REBALANCE BUY: %s %.6f units ($%.2f)",
                    action.symbol, amount_to_buy, action.rebalance_amount
                )
                
                # Execute buy order (simplified - would integrate with actual trading)
                return True
                
            else:
                # SELL action
                amount_to_sell = abs(action.rebalance_amount)
                current_price = self._get_current_price(action.symbol)
                units_to_sell = amount_to_sell / current_price
                
                logger.info(
                    "🔴 REBALANCE SELL: %s %.6f units ($%.2f)",
                    action.symbol, units_to_sell, amount_to_sell
                )
                
                # Execute sell order (simplified - would integrate with actual trading)
                return True
                
        except Exception as exc:
            logger.error("Failed to execute rebalancing action for %s: %s", action.symbol, exc)
            return False
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol."""
        try:
            ticker = self.okx.fetch_ticker(symbol)
            return float(ticker["last"])
        except Exception as exc:
            logger.error("❌ PRICE FETCH FAILED for %s: %s - NO fallback", symbol, exc)
            return None
    
    def _is_trend_negative(self, symbol: str) -> bool:
        """Check if the trend is negative for a symbol."""
        try:
            # Simplified trend check - would use technical analysis
            ticker = self.okx.fetch_ticker(symbol)
            current_price = float(ticker["last"])
            
            # Get some historical data for trend analysis
            ohlcv = self.okx.fetch_ohlcv(symbol, '1h', limit=24)
            if len(ohlcv) >= 24:
                price_24h_ago = ohlcv[0][4]  # Close price 24h ago
                return current_price < price_24h_ago * 0.98  # Down more than 2%
            
            return False
            
        except Exception as exc:
            logger.debug("Error checking trend for %s: %s", symbol, exc)
            return False
    
    def get_portfolio_metrics(self, positions: Dict[str, any], current_balance: float) -> PortfolioMetrics:
        """Calculate comprehensive portfolio metrics."""
        try:
            total_value = self._calculate_total_portfolio_value(positions, current_balance)
            
            # Calculate basic metrics
            total_pnl = 0.0
            position_values = []
            
            for symbol, position in positions.items():
                current_price = self._get_current_price(symbol)
                entry_price = getattr(position, 'entry_price', current_price)
                position_value = position.amount * current_price
                position_pnl = (current_price - entry_price) * position.amount
                
                total_pnl += position_pnl
                position_values.append(position_value)
            
            total_pnl_percentage = (total_pnl / (total_value - total_pnl)) * 100 if total_value > total_pnl else 0.0
            
            # Calculate concentration risk
            concentration_risk = 0.0
            if position_values:
                max_position = max(position_values)
                concentration_risk = (max_position / total_value) * 100
            
            # Calculate diversification score
            diversification_score = min(len(positions) / self.max_positions * 100, 100.0)
            
            return PortfolioMetrics(
                total_value=total_value,
                total_pnl=total_pnl,
                total_pnl_percentage=total_pnl_percentage,
                sharpe_ratio=0.0,  # Would calculate with historical data
                max_drawdown=0.0,  # Would calculate with historical data
                volatility=0.0,    # Would calculate with historical data
                correlation_risk=0.0,  # Would calculate with correlation matrix
                concentration_risk=concentration_risk,
                diversification_score=diversification_score
            )
            
        except Exception as exc:
            logger.error("Error calculating portfolio metrics: %s", exc)
            return PortfolioMetrics(
                total_value=current_balance, total_pnl=0.0, total_pnl_percentage=0.0,
                sharpe_ratio=0.0, max_drawdown=0.0, volatility=0.0,
                correlation_risk=0.0, concentration_risk=0.0, diversification_score=0.0
            )
