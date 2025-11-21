"""Enhanced risk management with volatility-adjusted sizing and portfolio analysis."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from trading_bot.analytics.market_data import MarketDataManager, MultiTimeframeData

logger = logging.getLogger(__name__)


@dataclass
class PositionRisk:
    """Risk metrics for a single position."""
    symbol: str
    notional_value: float
    risk_amount: float  # Amount at risk (entry - stop_loss) * size
    risk_percentage: float  # Risk as % of portfolio
    volatility: float
    correlation_risk: float  # Risk from correlated positions


@dataclass
class PortfolioRisk:
    """Portfolio-level risk metrics."""
    total_exposure: float
    total_risk: float
    risk_percentage: float  # Total risk as % of portfolio
    max_drawdown: float
    correlation_risk: float
    var_95: float  # 95% Value at Risk
    positions: List[PositionRisk]


class EnhancedRiskManager:
    """Enhanced risk management with portfolio-level analysis."""
    
    def __init__(
        self, 
        market_data_manager: MarketDataManager,
        max_portfolio_risk: float = 0.02,  # 2% max portfolio risk
        max_position_risk: float = 0.005,  # 0.5% max single position risk
        max_correlation: float = 0.7,  # Max correlation between positions
        max_drawdown: float = 0.05,  # 5% max drawdown
        volatility_lookback: int = 30  # Days for volatility calculation
    ):
        """Initialize enhanced risk manager.
        
        Args:
            market_data_manager: Market data manager instance
            max_portfolio_risk: Maximum total portfolio risk (as decimal)
            max_position_risk: Maximum single position risk (as decimal)
            max_correlation: Maximum correlation between positions
            max_drawdown: Maximum allowed drawdown
            volatility_lookback: Days to look back for volatility calculation
        """
        self.market_data = market_data_manager
        self.max_portfolio_risk = max_portfolio_risk
        self.max_position_risk = max_position_risk
        self.max_correlation = max_correlation
        self.max_drawdown = max_drawdown
        self.volatility_lookback = volatility_lookback
        
        # Track portfolio performance
        self.initial_balance: Optional[float] = None
        self.peak_balance: Optional[float] = None
        self.current_drawdown: float = 0.0
        
        # Correlation matrix cache
        self.correlation_cache: Dict[Tuple[str, str], float] = {}
        self.correlation_cache_time: float = 0.0
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        current_balance: float,
        existing_positions: Dict[str, any] = None
    ) -> float:
        """Calculate optimal position size using enhanced risk management.
        
        Args:
            symbol: Trading symbol
            entry_price: Planned entry price
            stop_loss: Stop loss price
            current_balance: Current account balance
            existing_positions: Dictionary of existing positions
            
        Returns:
            Optimal position size (in base currency units)
        """
        try:
            # Initialize balance tracking
            if self.initial_balance is None:
                self.initial_balance = current_balance
                self.peak_balance = current_balance
            
            # Update peak balance and drawdown
            if current_balance > self.peak_balance:
                self.peak_balance = current_balance
            
            self.current_drawdown = (self.peak_balance - current_balance) / self.peak_balance
            
            # Check drawdown limit
            if self.current_drawdown > self.max_drawdown:
                logger.warning(
                    "Current drawdown %.2f%% exceeds limit %.2f%%, reducing position size",
                    self.current_drawdown * 100, self.max_drawdown * 100
                )
                return 0.0  # Stop trading if drawdown too high
            
            # Get volatility for the symbol
            volatility = self._get_symbol_volatility(symbol)
            if volatility is None:
                logger.warning("No volatility data for %s, using conservative sizing", symbol)
                volatility = 0.3  # Conservative default
            
            # Calculate base risk amount
            risk_per_unit = abs(entry_price - stop_loss)
            if risk_per_unit <= 0:
                logger.warning("Invalid risk per unit for %s: %.6f", symbol, risk_per_unit)
                return 0.0
            
            # FIXED: Calculate position size as percentage of balance (5% per trade)
            target_position_percentage = 0.05  # 5% of balance per trade
            max_position_value = current_balance * target_position_percentage
            
            # Calculate position size in base currency units
            position_size = max_position_value / entry_price
            
            # Apply volatility adjustment to reduce size for high volatility assets
            volatility_adjustment = min(1.0, 0.2 / volatility)  # Reduce size for high volatility
            position_size *= volatility_adjustment
            
            # Verify risk per unit is reasonable (risk should be small fraction of position)
            position_value = position_size * entry_price
            risk_amount = position_size * risk_per_unit
            risk_percentage = risk_amount / current_balance
            
            # Log position sizing details
            logger.info(
                "Position sizing for %s: value=$%.2f (%.1f%% of balance), risk=$%.2f (%.2f%% of balance)",
                symbol, position_value, (position_value/current_balance)*100, 
                risk_amount, risk_percentage*100
            )
            
            # Check portfolio-level constraints
            if existing_positions:
                portfolio_risk = self._calculate_portfolio_risk(
                    existing_positions, current_balance
                )
                
                # Check total portfolio risk
                new_position_risk = (position_size * risk_per_unit) / current_balance
                total_risk = portfolio_risk.risk_percentage + new_position_risk
                
                # Ensure we don't exceed portfolio risk limits, but maintain 5% position size limit
                if total_risk > self.max_portfolio_risk:
                    logger.warning(
                        "Portfolio risk %.2f%% would exceed limit %.2f%%, reducing position size",
                        total_risk * 100, self.max_portfolio_risk * 100
                    )
                    
                    # Calculate maximum allowable position size based on risk limits
                    max_new_risk = self.max_portfolio_risk - portfolio_risk.risk_percentage
                    if max_new_risk <= 0:
                        logger.warning("Portfolio risk limit reached, cannot add new position")
                        return 0.0
                    
                    risk_based_size = (max_new_risk * current_balance) / risk_per_unit
                    
                    # Use the smaller of: 5% position size or risk-limited size
                    position_size = min(position_size, risk_based_size)
                    
                    logger.info("Position size reduced to %.6f due to portfolio risk limits", position_size)
                
                # Check correlation limits
                correlation_adjustment = self._calculate_correlation_adjustment(
                    symbol, existing_positions
                )
                position_size *= correlation_adjustment
            
            # Apply additional safety margins
            position_size *= 0.95  # 5% safety margin
            
            # FINAL SAFETY CHECK: Ensure position value never exceeds 5% of balance
            final_position_value = position_size * entry_price
            max_allowed_value = current_balance * 0.05  # 5% hard limit
            
            if final_position_value > max_allowed_value:
                position_size = max_allowed_value / entry_price
                logger.warning(
                    "Position size capped at 5%% of balance: %.6f -> %.6f",
                    final_position_value / entry_price, position_size
                )
            
            # Final logging
            final_value = position_size * entry_price
            final_percentage = (final_value / current_balance) * 100
            
            logger.info(
                "✅ FINAL POSITION SIZE: %s - %.6f units ($%.2f = %.2f%% of balance)",
                symbol, position_size, final_value, final_percentage
            )
            
            return max(0.0, position_size)
            
        except Exception as exc:
            logger.error("Position sizing calculation failed for %s: %s", symbol, exc)
            return 0.0
    
    def _get_symbol_volatility(self, symbol: str) -> Optional[float]:
        """Get volatility for a symbol."""
        try:
            mtf_data = self.market_data.get_multi_timeframe_data(symbol)
            if not mtf_data:
                return None
            
            # Use daily data for volatility calculation if available
            candles = mtf_data.get_timeframe('1d')
            if not candles or len(candles) < 10:
                # Fallback to 1h data
                candles = mtf_data.get_timeframe('1h')
                if not candles or len(candles) < 24:
                    return None
            
            # Calculate returns
            closes = [c.close for c in candles[-self.volatility_lookback:]]
            if len(closes) < 10:
                return None
            
            returns = np.diff(closes) / closes[:-1]
            volatility = np.std(returns) * np.sqrt(365)  # Annualized
            
            return float(volatility)
            
        except Exception as exc:
            logger.warning("Volatility calculation failed for %s: %s", symbol, exc)
            return None
    
    def _calculate_portfolio_risk(
        self, 
        positions: Dict[str, any], 
        current_balance: float
    ) -> PortfolioRisk:
        """Calculate comprehensive portfolio risk metrics."""
        try:
            position_risks = []
            total_exposure = 0.0
            total_risk = 0.0
            
            for symbol, position in positions.items():
                try:
                    # Calculate position metrics
                    notional_value = position.amount * position.entry_price
                    risk_amount = position.amount * abs(position.entry_price - position.stop_loss)
                    risk_percentage = risk_amount / current_balance
                    
                    volatility = self._get_symbol_volatility(symbol) or 0.3
                    
                    position_risk = PositionRisk(
                        symbol=symbol,
                        notional_value=notional_value,
                        risk_amount=risk_amount,
                        risk_percentage=risk_percentage,
                        volatility=volatility,
                        correlation_risk=0.0  # Will be calculated later
                    )
                    
                    position_risks.append(position_risk)
                    total_exposure += notional_value
                    total_risk += risk_amount
                    
                except Exception as exc:
                    logger.warning("Failed to calculate risk for position %s: %s", symbol, exc)
                    continue
            
            # Calculate correlation risk
            correlation_risk = self._calculate_correlation_risk(position_risks)
            
            # Calculate VaR (simplified)
            var_95 = total_risk * 1.65  # Assuming normal distribution
            
            portfolio_risk = PortfolioRisk(
                total_exposure=total_exposure,
                total_risk=total_risk,
                risk_percentage=total_risk / current_balance,
                max_drawdown=self.current_drawdown,
                correlation_risk=correlation_risk,
                var_95=var_95,
                positions=position_risks
            )
            
            return portfolio_risk
            
        except Exception as exc:
            logger.error("Portfolio risk calculation failed: %s", exc)
            return PortfolioRisk(0, 0, 0, 0, 0, 0, [])
    
    def _calculate_correlation_adjustment(
        self, 
        new_symbol: str, 
        existing_positions: Dict[str, any]
    ) -> float:
        """Calculate position size adjustment based on correlation with existing positions."""
        try:
            if not existing_positions:
                return 1.0  # No adjustment needed
            
            max_correlation = 0.0
            
            for existing_symbol in existing_positions.keys():
                correlation = self._get_correlation(new_symbol, existing_symbol)
                if correlation is not None:
                    max_correlation = max(max_correlation, abs(correlation))
            
            # Reduce position size if high correlation
            if max_correlation > self.max_correlation:
                adjustment = 1.0 - ((max_correlation - self.max_correlation) / (1.0 - self.max_correlation))
                logger.info(
                    "High correlation detected for %s (%.2f), adjusting size by %.2f",
                    new_symbol, max_correlation, adjustment
                )
                return max(0.1, adjustment)  # Minimum 10% of original size
            
            return 1.0
            
        except Exception as exc:
            logger.error("❌ CORRELATION ADJUSTMENT FAILED for %s: %s - NO fallback", new_symbol, exc)
            return None
    
    def _get_correlation(self, symbol1: str, symbol2: str) -> Optional[float]:
        """Get correlation between two symbols."""
        try:
            if symbol1 == symbol2:
                return 1.0
            
            # Check cache
            cache_key = tuple(sorted([symbol1, symbol2]))
            if cache_key in self.correlation_cache:
                return self.correlation_cache[cache_key]
            
            # Get price data for both symbols
            mtf_data1 = self.market_data.get_multi_timeframe_data(symbol1)
            mtf_data2 = self.market_data.get_multi_timeframe_data(symbol2)
            
            if not mtf_data1 or not mtf_data2:
                return None
            
            # Use 1h data for correlation
            candles1 = mtf_data1.get_timeframe('1h')
            candles2 = mtf_data2.get_timeframe('1h')
            
            if not candles1 or not candles2:
                return None
            
            # Align timestamps and calculate returns
            min_length = min(len(candles1), len(candles2), 100)  # Use last 100 periods
            
            closes1 = [c.close for c in candles1[-min_length:]]
            closes2 = [c.close for c in candles2[-min_length:]]
            
            if len(closes1) < 20 or len(closes2) < 20:
                return None
            
            returns1 = np.diff(closes1) / closes1[:-1]
            returns2 = np.diff(closes2) / closes2[:-1]
            
            # Calculate correlation
            correlation = np.corrcoef(returns1, returns2)[0, 1]
            
            # Cache the result
            self.correlation_cache[cache_key] = float(correlation)
            
            return float(correlation)
            
        except Exception as exc:
            logger.warning("Correlation calculation failed for %s/%s: %s", symbol1, symbol2, exc)
            return None
    
    def _calculate_correlation_risk(self, position_risks: List[PositionRisk]) -> float:
        """Calculate portfolio correlation risk."""
        try:
            if len(position_risks) < 2:
                return 0.0
            
            total_correlation_risk = 0.0
            
            for i, pos1 in enumerate(position_risks):
                for j, pos2 in enumerate(position_risks[i+1:], i+1):
                    correlation = self._get_correlation(pos1.symbol, pos2.symbol)
                    if correlation is not None and abs(correlation) > 0.5:
                        # Risk increases with correlation and position sizes
                        risk_contribution = abs(correlation) * pos1.risk_percentage * pos2.risk_percentage
                        total_correlation_risk += risk_contribution
            
            return total_correlation_risk
            
        except Exception as exc:
            logger.warning("Correlation risk calculation failed: %s", exc)
            return 0.0
    
    def should_reduce_risk(self) -> bool:
        """Check if risk should be reduced based on current conditions."""
        return self.current_drawdown > (self.max_drawdown * 0.8)  # 80% of max drawdown
    
    def get_risk_summary(self, positions: Dict[str, any], current_balance: float) -> Dict[str, float]:
        """Get summary of current risk metrics."""
        portfolio_risk = self._calculate_portfolio_risk(positions, current_balance)
        
        return {
            'portfolio_risk_pct': portfolio_risk.risk_percentage * 100,
            'total_exposure': portfolio_risk.total_exposure,
            'current_drawdown_pct': self.current_drawdown * 100,
            'correlation_risk': portfolio_risk.correlation_risk,
            'var_95': portfolio_risk.var_95,
            'num_positions': len(positions)
        }
