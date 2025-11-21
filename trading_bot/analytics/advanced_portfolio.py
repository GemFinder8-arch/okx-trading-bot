"""Advanced portfolio management including pairs trading, sector rotation, and dynamic hedging."""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
import time

logger = logging.getLogger(__name__)


@dataclass
class PairsTradingOpportunity:
    """Pairs trading opportunity."""
    symbol_a: str
    symbol_b: str
    spread: float
    z_score: float
    confidence: float
    direction: str  # "long_a_short_b" or "short_a_long_b"
    expected_return: float
    risk_level: str


@dataclass
class SectorRotationSignal:
    """Sector rotation signal."""
    from_sector: str
    to_sector: str
    strength: float  # 0.0 to 1.0
    duration_estimate: int  # days
    symbols_to_buy: List[str]
    symbols_to_sell: List[str]


@dataclass
class HedgingStrategy:
    """Dynamic hedging strategy."""
    hedge_type: str  # "correlation", "volatility", "directional"
    hedge_symbol: str
    hedge_ratio: float  # Position size ratio
    hedge_direction: str  # "long" or "short"
    effectiveness: float  # Expected hedge effectiveness 0.0 to 1.0


@dataclass
class PortfolioOptimization:
    """Portfolio optimization result."""
    target_weights: Dict[str, float]
    risk_metrics: Dict[str, float]
    expected_return: float
    sharpe_ratio: float
    max_drawdown_estimate: float
    rebalancing_actions: List[Tuple[str, str, float]]  # (symbol, action, amount)


class AdvancedPortfolioManager:
    """Advanced portfolio management strategies."""
    
    def __init__(self):
        """Initialize advanced portfolio manager."""
        self.correlation_matrix = {}
        self.sector_classifications = self._initialize_sector_classifications()
        self.pairs_history = defaultdict(deque)
        self.sector_momentum = defaultdict(deque)
        
        # Portfolio constraints
        self.max_sector_weight = 0.4  # 40% max in any sector
        self.max_single_position = 0.15  # 15% max in any single asset
        self.min_diversification = 5  # Minimum 5 positions
        
    def _initialize_sector_classifications(self) -> Dict[str, str]:
        """Initialize cryptocurrency sector classifications."""
        return {
            # Layer 1 Blockchains
            "BTC/USDT": "store_of_value",
            "ETH/USDT": "smart_contracts",
            "SOL/USDT": "smart_contracts",
            "ADA/USDT": "smart_contracts",
            "DOT/USDT": "interoperability",
            "AVAX/USDT": "smart_contracts",
            "ALGO/USDT": "smart_contracts",
            "NEAR/USDT": "smart_contracts",
            
            # DeFi
            "UNI/USDT": "defi",
            "SUSHI/USDT": "defi",
            "AAVE/USDT": "defi",
            "COMP/USDT": "defi",
            
            # Gaming & Metaverse
            "SAND/USDT": "gaming_metaverse",
            "MANA/USDT": "gaming_metaverse",
            "AXS/USDT": "gaming_metaverse",
            
            # Meme Coins
            "DOGE/USDT": "meme",
            "SHIB/USDT": "meme",
            "PEPE/USDT": "meme",
            
            # Infrastructure
            "LINK/USDT": "infrastructure",
            "MATIC/USDT": "infrastructure",
            
            # Stablecoins
            "USDC/USDT": "stablecoin",
            
            # Others
            "XTZ/USDT": "smart_contracts",
            "IOTA/USDT": "iot",
            "ZRO/USDT": "interoperability"
        }
    
    def identify_pairs_trading_opportunities(self, price_data: Dict[str, np.ndarray], 
                                           correlation_threshold: float = 0.7) -> List[PairsTradingOpportunity]:
        """Identify pairs trading opportunities based on correlation and spread analysis."""
        try:
            opportunities = []
            symbols = list(price_data.keys())
            
            # Calculate correlations and identify pairs
            for i in range(len(symbols)):
                for j in range(i + 1, len(symbols)):
                    symbol_a, symbol_b = symbols[i], symbols[j]
                    
                    if len(price_data[symbol_a]) < 50 or len(price_data[symbol_b]) < 50:
                        continue
                    
                    # Calculate correlation
                    min_length = min(len(price_data[symbol_a]), len(price_data[symbol_b]))
                    prices_a = price_data[symbol_a][-min_length:]
                    prices_b = price_data[symbol_b][-min_length:]
                    
                    correlation = np.corrcoef(prices_a, prices_b)[0, 1]
                    
                    if abs(correlation) > correlation_threshold:
                        # Calculate spread and z-score
                        spread = prices_a - prices_b
                        spread_mean = np.mean(spread)
                        spread_std = np.std(spread)
                        
                        if spread_std > 0:
                            current_spread = spread[-1]
                            z_score = (current_spread - spread_mean) / spread_std
                            
                            # Identify trading opportunity
                            if abs(z_score) > 2.0:  # 2 standard deviations
                                direction = "long_a_short_b" if z_score < 0 else "short_a_long_b"
                                confidence = min(abs(z_score) / 3.0, 1.0)  # Normalize to 0-1
                                expected_return = abs(z_score) * spread_std / np.mean(prices_a)
                                
                                risk_level = "low" if abs(z_score) > 3.0 else "medium"
                                
                                opportunity = PairsTradingOpportunity(
                                    symbol_a=symbol_a,
                                    symbol_b=symbol_b,
                                    spread=current_spread,
                                    z_score=z_score,
                                    confidence=confidence,
                                    direction=direction,
                                    expected_return=expected_return,
                                    risk_level=risk_level
                                )
                                
                                opportunities.append(opportunity)
            
            # Sort by confidence and return top opportunities
            opportunities.sort(key=lambda x: x.confidence, reverse=True)
            return opportunities[:5]  # Top 5 opportunities
            
        except Exception as exc:
            logger.warning("Pairs trading analysis failed: %s", exc)
            return []
    
    def analyze_sector_rotation(self, price_data: Dict[str, np.ndarray], 
                              volume_data: Dict[str, np.ndarray]) -> List[SectorRotationSignal]:
        """Analyze sector rotation opportunities."""
        try:
            # Calculate sector performance
            sector_performance = defaultdict(list)
            sector_volume = defaultdict(list)
            
            for symbol, prices in price_data.items():
                sector = self.sector_classifications.get(symbol, "other")
                if len(prices) >= 20:
                    # Calculate 20-day performance
                    performance = (prices[-1] - prices[-20]) / prices[-20]
                    sector_performance[sector].append(performance)
                    
                    if symbol in volume_data and len(volume_data[symbol]) >= 20:
                        volume_change = (np.mean(volume_data[symbol][-5:]) - 
                                       np.mean(volume_data[symbol][-20:-5])) / np.mean(volume_data[symbol][-20:-5])
                        sector_volume[sector].append(volume_change)
            
            # Calculate sector averages
            sector_avg_performance = {}
            sector_avg_volume = {}
            
            for sector in sector_performance:
                sector_avg_performance[sector] = np.mean(sector_performance[sector])
                sector_avg_volume[sector] = np.mean(sector_volume.get(sector, [0]))
            
            # Identify rotation opportunities
            rotation_signals = []
            
            # Sort sectors by performance
            sorted_sectors = sorted(sector_avg_performance.items(), key=lambda x: x[1], reverse=True)
            
            if len(sorted_sectors) >= 2:
                # Strong sector (to rotate into)
                strong_sector, strong_performance = sorted_sectors[0]
                # Weak sector (to rotate out of)
                weak_sector, weak_performance = sorted_sectors[-1]
                
                performance_gap = strong_performance - weak_performance
                
                if performance_gap > 0.1:  # 10% performance gap
                    # Get symbols for rotation
                    symbols_to_buy = [s for s, sect in self.sector_classifications.items() 
                                    if sect == strong_sector]
                    symbols_to_sell = [s for s, sect in self.sector_classifications.items() 
                                     if sect == weak_sector]
                    
                    # Estimate rotation strength and duration
                    volume_confirmation = sector_avg_volume.get(strong_sector, 0) > 0.2
                    strength = min(performance_gap * (2 if volume_confirmation else 1), 1.0)
                    duration_estimate = int(20 * strength)  # 20 days max
                    
                    signal = SectorRotationSignal(
                        from_sector=weak_sector,
                        to_sector=strong_sector,
                        strength=strength,
                        duration_estimate=duration_estimate,
                        symbols_to_buy=symbols_to_buy[:3],  # Top 3 symbols
                        symbols_to_sell=symbols_to_sell[:3]
                    )
                    
                    rotation_signals.append(signal)
            
            return rotation_signals
            
        except Exception as exc:
            logger.warning("Sector rotation analysis failed: %s", exc)
            return []
    
    def design_hedging_strategy(self, portfolio: Dict[str, float], 
                              price_data: Dict[str, np.ndarray], 
                              market_conditions: Dict) -> List[HedgingStrategy]:
        """Design dynamic hedging strategies for portfolio protection."""
        try:
            hedging_strategies = []
            
            # 1. CORRELATION HEDGING
            # Find negatively correlated assets for hedging
            portfolio_symbols = list(portfolio.keys())
            
            for symbol in portfolio_symbols:
                if symbol not in price_data or len(price_data[symbol]) < 30:
                    continue
                
                # Find best hedge (most negatively correlated)
                best_hedge = None
                best_correlation = 1.0  # Start with worst case
                
                for potential_hedge in price_data:
                    if potential_hedge == symbol or len(price_data[potential_hedge]) < 30:
                        continue
                    
                    # Calculate correlation
                    min_length = min(len(price_data[symbol]), len(price_data[potential_hedge]))
                    returns_a = np.diff(price_data[symbol][-min_length:]) / price_data[symbol][-min_length:-1]
                    returns_b = np.diff(price_data[potential_hedge][-min_length:]) / price_data[potential_hedge][-min_length:-1]
                    
                    correlation = np.corrcoef(returns_a, returns_b)[0, 1]
                    
                    if correlation < best_correlation:
                        best_correlation = correlation
                        best_hedge = potential_hedge
                
                # Create hedge if good negative correlation found
                if best_hedge and best_correlation < -0.3:
                    hedge_ratio = min(abs(best_correlation) * portfolio[symbol], 0.5)  # Max 50% hedge
                    effectiveness = abs(best_correlation)
                    
                    strategy = HedgingStrategy(
                        hedge_type="correlation",
                        hedge_symbol=best_hedge,
                        hedge_ratio=hedge_ratio,
                        hedge_direction="long",
                        effectiveness=effectiveness
                    )
                    
                    hedging_strategies.append(strategy)
            
            # 2. VOLATILITY HEDGING
            # Use stablecoins or low-volatility assets during high volatility periods
            market_volatility = market_conditions.get('volatility', 0.05)
            
            if market_volatility > 0.08:  # High volatility threshold
                # Recommend stablecoin hedge
                stablecoin_hedge = HedgingStrategy(
                    hedge_type="volatility",
                    hedge_symbol="USDC/USDT",
                    hedge_ratio=min(market_volatility * 2, 0.3),  # Up to 30% in stablecoins
                    hedge_direction="long",
                    effectiveness=0.9  # Stablecoins are very effective volatility hedges
                )
                
                hedging_strategies.append(stablecoin_hedge)
            
            # 3. DIRECTIONAL HEDGING
            # Use BTC as a hedge during market downturns (flight to quality)
            market_sentiment = market_conditions.get('sentiment', 'neutral')
            
            if market_sentiment in ['bearish', 'very_bearish']:
                btc_weight = sum(portfolio.get(s, 0) for s in portfolio if 'BTC' in s)
                
                if btc_weight < 0.3:  # Less than 30% in BTC
                    btc_hedge = HedgingStrategy(
                        hedge_type="directional",
                        hedge_symbol="BTC/USDT",
                        hedge_ratio=0.3 - btc_weight,  # Increase to 30%
                        hedge_direction="long",
                        effectiveness=0.7  # BTC is moderately effective as crypto hedge
                    )
                    
                    hedging_strategies.append(btc_hedge)
            
            return hedging_strategies
            
        except Exception as exc:
            logger.warning("Hedging strategy design failed: %s", exc)
            return []
    
    def optimize_portfolio_allocation(self, available_symbols: List[str], 
                                    price_data: Dict[str, np.ndarray],
                                    risk_tolerance: float = 0.5) -> PortfolioOptimization:
        """Optimize portfolio allocation using modern portfolio theory."""
        try:
            # Filter symbols with sufficient data
            valid_symbols = [s for s in available_symbols 
                           if s in price_data and len(price_data[s]) >= 60]
            
            if len(valid_symbols) < 3:
                return self._default_portfolio_optimization(available_symbols)
            
            # Calculate returns and covariance matrix
            returns_data = {}
            for symbol in valid_symbols:
                prices = price_data[symbol]
                returns = np.diff(prices) / prices[:-1]
                returns_data[symbol] = returns
            
            # Align returns to same length
            min_length = min(len(returns) for returns in returns_data.values())
            aligned_returns = np.array([returns[-min_length:] for returns in returns_data.values()])
            
            # Calculate expected returns and covariance matrix
            expected_returns = np.mean(aligned_returns, axis=1)
            cov_matrix = np.cov(aligned_returns)
            
            # Optimize using simplified mean-variance optimization
            target_weights = self._mean_variance_optimization(
                expected_returns, cov_matrix, risk_tolerance
            )
            
            # Apply constraints
            target_weights = self._apply_portfolio_constraints(
                dict(zip(valid_symbols, target_weights)), valid_symbols
            )
            
            # Calculate portfolio metrics
            portfolio_return = np.dot(list(target_weights.values()), expected_returns)
            portfolio_variance = np.dot(list(target_weights.values()), 
                                      np.dot(cov_matrix, list(target_weights.values())))
            portfolio_std = np.sqrt(portfolio_variance)
            
            sharpe_ratio = portfolio_return / portfolio_std if portfolio_std > 0 else 0
            
            # Estimate max drawdown (simplified)
            max_drawdown_estimate = portfolio_std * 2.5  # Rough estimate
            
            # Generate rebalancing actions (placeholder)
            rebalancing_actions = []
            for symbol, weight in target_weights.items():
                if weight > 0.01:  # Only include significant positions
                    rebalancing_actions.append((symbol, "buy", weight))
            
            return PortfolioOptimization(
                target_weights=target_weights,
                risk_metrics={
                    "volatility": portfolio_std,
                    "var_95": np.percentile(aligned_returns.flatten(), 5)
                },
                expected_return=portfolio_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown_estimate=max_drawdown_estimate,
                rebalancing_actions=rebalancing_actions
            )
            
        except Exception as exc:
            logger.warning("Portfolio optimization failed: %s", exc)
            return self._default_portfolio_optimization(available_symbols)
    
    def _mean_variance_optimization(self, expected_returns: np.ndarray, 
                                  cov_matrix: np.ndarray, risk_tolerance: float) -> np.ndarray:
        """Simplified mean-variance optimization."""
        try:
            n_assets = len(expected_returns)
            
            # Risk aversion parameter
            risk_aversion = 1.0 / risk_tolerance if risk_tolerance > 0 else 2.0
            
            # Simplified optimization: inverse volatility weighting with return adjustment
            inv_volatility = 1.0 / np.sqrt(np.diag(cov_matrix))
            inv_volatility = inv_volatility / np.sum(inv_volatility)  # Normalize
            
            # Adjust for expected returns
            return_adjustment = expected_returns / np.sum(np.abs(expected_returns)) if np.sum(np.abs(expected_returns)) > 0 else np.ones(n_assets) / n_assets
            
            # Combine volatility and return factors
            weights = (inv_volatility + return_adjustment * risk_tolerance) / 2
            weights = weights / np.sum(weights)  # Normalize
            
            return weights
            
        except Exception:
            # Equal weight fallback
            n_assets = len(expected_returns)
            return np.ones(n_assets) / n_assets
    
    def _apply_portfolio_constraints(self, weights: Dict[str, float], 
                                   symbols: List[str]) -> Dict[str, float]:
        """Apply portfolio constraints to weights."""
        try:
            # Apply maximum single position constraint
            for symbol in weights:
                weights[symbol] = min(weights[symbol], self.max_single_position)
            
            # Apply sector constraints
            sector_weights = defaultdict(float)
            for symbol, weight in weights.items():
                sector = self.sector_classifications.get(symbol, "other")
                sector_weights[sector] += weight
            
            # Adjust if any sector exceeds maximum
            for sector, total_weight in sector_weights.items():
                if total_weight > self.max_sector_weight:
                    # Scale down all symbols in this sector
                    scale_factor = self.max_sector_weight / total_weight
                    for symbol in weights:
                        if self.sector_classifications.get(symbol, "other") == sector:
                            weights[symbol] *= scale_factor
            
            # Renormalize weights
            total_weight = sum(weights.values())
            if total_weight > 0:
                for symbol in weights:
                    weights[symbol] /= total_weight
            
            # Remove very small positions
            weights = {symbol: weight for symbol, weight in weights.items() 
                      if weight >= 0.01}  # Minimum 1% position
            
            return weights
            
        except Exception:
            # Equal weight fallback
            n_symbols = len(symbols)
            return {symbol: 1.0 / n_symbols for symbol in symbols}
    
    def calculate_portfolio_risk_metrics(self, portfolio: Dict[str, float], 
                                       price_data: Dict[str, np.ndarray]) -> Dict[str, float]:
        """Calculate comprehensive portfolio risk metrics."""
        try:
            # Calculate portfolio returns
            portfolio_returns = []
            
            # Get aligned price data
            min_length = min(len(price_data[symbol]) for symbol in portfolio 
                           if symbol in price_data and len(price_data[symbol]) > 0)
            
            if min_length < 30:
                return {"error": "insufficient_data"}
            
            for i in range(1, min_length):
                daily_return = 0
                for symbol, weight in portfolio.items():
                    if symbol in price_data and len(price_data[symbol]) > i:
                        symbol_return = (price_data[symbol][-i] - price_data[symbol][-i-1]) / price_data[symbol][-i-1]
                        daily_return += weight * symbol_return
                
                portfolio_returns.append(daily_return)
            
            portfolio_returns = np.array(portfolio_returns)
            
            # Calculate risk metrics
            volatility = np.std(portfolio_returns) * np.sqrt(252)  # Annualized
            
            # Value at Risk (95%)
            var_95 = np.percentile(portfolio_returns, 5)
            
            # Maximum Drawdown
            cumulative_returns = np.cumprod(1 + portfolio_returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - running_max) / running_max
            max_drawdown = np.min(drawdowns)
            
            # Sharpe Ratio (assuming 0% risk-free rate)
            mean_return = np.mean(portfolio_returns)
            sharpe_ratio = mean_return / np.std(portfolio_returns) if np.std(portfolio_returns) > 0 else 0
            
            # Sortino Ratio
            downside_returns = portfolio_returns[portfolio_returns < 0]
            downside_std = np.std(downside_returns) if len(downside_returns) > 0 else np.std(portfolio_returns)
            sortino_ratio = mean_return / downside_std if downside_std > 0 else 0
            
            return {
                "volatility": volatility,
                "var_95": var_95,
                "max_drawdown": max_drawdown,
                "sharpe_ratio": sharpe_ratio,
                "sortino_ratio": sortino_ratio,
                "expected_return": mean_return * 252,  # Annualized
                "win_rate": len(portfolio_returns[portfolio_returns > 0]) / len(portfolio_returns)
            }
            
        except Exception as exc:
            logger.warning("Portfolio risk metrics calculation failed: %s", exc)
            return {"error": str(exc)}
    
    def _default_portfolio_optimization(self, symbols: List[str]) -> PortfolioOptimization:
        """Return default portfolio optimization when analysis fails."""
        n_symbols = min(len(symbols), 8)  # Max 8 positions
        equal_weight = 1.0 / n_symbols
        
        target_weights = {symbols[i]: equal_weight for i in range(n_symbols)}
        
        return PortfolioOptimization(
            target_weights=target_weights,
            risk_metrics={"volatility": 0.3, "var_95": -0.05},
            expected_return=0.1,
            sharpe_ratio=0.5,
            max_drawdown_estimate=0.2,
            rebalancing_actions=[(symbol, "buy", weight) for symbol, weight in target_weights.items()]
        )


# Singleton instance
_advanced_portfolio_manager = None

def get_advanced_portfolio_manager() -> AdvancedPortfolioManager:
    """Get singleton advanced portfolio manager."""
    global _advanced_portfolio_manager
    if _advanced_portfolio_manager is None:
        _advanced_portfolio_manager = AdvancedPortfolioManager()
    return _advanced_portfolio_manager
