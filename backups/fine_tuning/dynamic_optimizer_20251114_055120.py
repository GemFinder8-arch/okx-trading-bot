"""Dynamic parameter optimization and adaptive confidence thresholds."""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
import time
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MarketRegime:
    """Market regime classification."""
    regime_type: str  # "trending_up", "trending_down", "sideways", "volatile"
    strength: float  # 0.0 to 1.0
    duration: int  # periods in this regime
    volatility: float
    volume_profile: str  # "high", "medium", "low"


@dataclass
class OptimalParameters:
    """Optimal parameters for current market conditions."""
    confidence_threshold: float
    rsi_period: int
    ema_fast: int
    ema_slow: int
    macd_fast: int
    macd_slow: int
    macd_signal: int
    bollinger_period: int
    bollinger_std: float
    stop_loss_multiplier: float
    take_profit_multiplier: float


class DynamicOptimizer:
    """Dynamic parameter optimization based on market conditions."""
    
    def __init__(self, data_path: str = "data/optimizer_data.json"):
        """Initialize dynamic optimizer."""
        self.data_path = Path(data_path)
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.regime_history: deque = deque(maxlen=252)  # 1 year of regime data
        self.parameter_performance: Dict[str, Dict] = defaultdict(dict)
        
        # Base parameters for different market regimes
        self.regime_parameters = {
            "trending_up": OptimalParameters(
                confidence_threshold=0.40,
                rsi_period=14,
                ema_fast=8,
                ema_slow=21,
                macd_fast=12,
                macd_slow=26,
                macd_signal=9,
                bollinger_period=20,
                bollinger_std=2.0,
                stop_loss_multiplier=1.5,
                take_profit_multiplier=2.5
            ),
            "trending_down": OptimalParameters(
                confidence_threshold=0.55,
                rsi_period=14,
                ema_fast=8,
                ema_slow=21,
                macd_fast=12,
                macd_slow=26,
                macd_signal=9,
                bollinger_period=20,
                bollinger_std=2.0,
                stop_loss_multiplier=1.2,
                take_profit_multiplier=2.0
            ),
            "sideways": OptimalParameters(
                confidence_threshold=0.60,
                rsi_period=21,
                ema_fast=5,
                ema_slow=13,
                macd_fast=8,
                macd_slow=21,
                macd_signal=5,
                bollinger_period=14,
                bollinger_std=1.8,
                stop_loss_multiplier=1.0,
                take_profit_multiplier=1.5
            ),
            "volatile": OptimalParameters(
                confidence_threshold=0.70,
                rsi_period=10,
                ema_fast=5,
                ema_slow=15,
                macd_fast=8,
                macd_slow=17,
                macd_signal=7,
                bollinger_period=15,
                bollinger_std=2.5,
                stop_loss_multiplier=2.0,
                take_profit_multiplier=3.0
            )
        }
        
        self._load_optimizer_data()
    
    def detect_market_regime(self, price_data: np.ndarray, volume_data: np.ndarray, lookback: int = 50) -> MarketRegime:
        """Detect current market regime."""
        try:
            if len(price_data) < lookback:
                return MarketRegime("sideways", 0.5, 0, 0.05, "medium")
            
            recent_prices = price_data[-lookback:]
            recent_volumes = volume_data[-lookback:] if len(volume_data) >= lookback else None
            
            # 1. TREND DETECTION
            # Linear regression slope
            x = np.arange(len(recent_prices))
            slope, intercept = np.polyfit(x, recent_prices, 1)
            trend_strength = abs(slope) / np.mean(recent_prices)
            
            # Moving average analysis
            ema_20 = self._ema(recent_prices, 20)
            ema_50 = self._ema(recent_prices, min(50, len(recent_prices)))
            
            ma_trend = 1 if ema_20[-1] > ema_50[-1] else -1
            ma_strength = abs(ema_20[-1] - ema_50[-1]) / ema_50[-1]
            
            # 2. VOLATILITY ANALYSIS
            returns = np.diff(recent_prices) / recent_prices[:-1]
            volatility = np.std(returns) * np.sqrt(252)  # Annualized
            
            # 3. VOLUME ANALYSIS
            if recent_volumes is not None:
                volume_trend = np.mean(recent_volumes[-10:]) / np.mean(recent_volumes[-30:])
                if volume_trend > 1.2:
                    volume_profile = "high"
                elif volume_trend > 0.8:
                    volume_profile = "medium"
                else:
                    volume_profile = "low"
            else:
                volume_profile = "medium"
            
            # 4. REGIME CLASSIFICATION
            if volatility > 0.4:  # High volatility threshold
                regime_type = "volatile"
                strength = min(volatility / 0.6, 1.0)
            elif trend_strength > 0.02 and ma_strength > 0.01:  # Trending market
                if ma_trend > 0:
                    regime_type = "trending_up"
                else:
                    regime_type = "trending_down"
                strength = min((trend_strength + ma_strength) / 0.04, 1.0)
            else:  # Sideways market
                regime_type = "sideways"
                strength = 1.0 - min(trend_strength / 0.02, 1.0)
            
            # Calculate regime duration
            duration = self._calculate_regime_duration(regime_type)
            
            regime = MarketRegime(
                regime_type=regime_type,
                strength=strength,
                duration=duration,
                volatility=volatility,
                volume_profile=volume_profile
            )
            
            # Update regime history
            self.regime_history.append(regime)
            
            return regime
            
        except Exception as exc:
            logger.warning("Market regime detection failed: %s", exc)
            return MarketRegime("sideways", 0.5, 0, 0.05, "medium")
    
    def get_optimal_parameters(self, symbol: str, market_regime: MarketRegime, recent_performance: Optional[Dict] = None) -> OptimalParameters:
        """Get optimal parameters for current market conditions."""
        try:
            # Start with base parameters for the regime
            base_params = self.regime_parameters.get(market_regime.regime_type, self.regime_parameters["sideways"])
            
            # Adjust based on regime strength and recent performance
            adjusted_params = OptimalParameters(
                confidence_threshold=self._adjust_confidence_threshold(base_params.confidence_threshold, market_regime, recent_performance),
                rsi_period=self._adjust_rsi_period(base_params.rsi_period, market_regime),
                ema_fast=base_params.ema_fast,
                ema_slow=base_params.ema_slow,
                macd_fast=base_params.macd_fast,
                macd_slow=base_params.macd_slow,
                macd_signal=base_params.macd_signal,
                bollinger_period=self._adjust_bollinger_period(base_params.bollinger_period, market_regime),
                bollinger_std=self._adjust_bollinger_std(base_params.bollinger_std, market_regime),
                stop_loss_multiplier=self._adjust_stop_loss_multiplier(base_params.stop_loss_multiplier, market_regime),
                take_profit_multiplier=self._adjust_take_profit_multiplier(base_params.take_profit_multiplier, market_regime)
            )
            
            # Symbol-specific adjustments
            if symbol in self.parameter_performance:
                adjusted_params = self._apply_symbol_specific_adjustments(adjusted_params, symbol)
            
            return adjusted_params
            
        except Exception as exc:
            logger.warning("Parameter optimization failed for %s: %s", symbol, exc)
            return self.regime_parameters["sideways"]
    
    def _adjust_confidence_threshold(self, base_threshold: float, regime: MarketRegime, recent_performance: Optional[Dict]) -> float:
        """Dynamically adjust confidence threshold."""
        try:
            adjusted = base_threshold
            
            # Regime-based adjustments
            if regime.regime_type == "volatile":
                adjusted += 0.15  # Higher threshold for volatile markets
            elif regime.regime_type == "sideways":
                adjusted += 0.10  # Higher threshold for choppy markets
            
            # Strength-based adjustments
            if regime.strength > 0.8:
                adjusted -= 0.05  # Lower threshold for strong regimes
            elif regime.strength < 0.3:
                adjusted += 0.05  # Higher threshold for weak regimes
            
            # Performance-based adjustments
            if recent_performance:
                win_rate = recent_performance.get('win_rate', 0.5)
                if win_rate > 0.7:
                    adjusted -= 0.05  # Lower threshold for good performance
                elif win_rate < 0.4:
                    adjusted += 0.10  # Higher threshold for poor performance
            
            # Volume-based adjustments
            if regime.volume_profile == "low":
                adjusted += 0.05  # Higher threshold for low volume
            
            return max(0.25, min(0.80, adjusted))  # Clamp between 25% and 80%
            
        except Exception:
            return base_threshold
    
    def _adjust_rsi_period(self, base_period: int, regime: MarketRegime) -> int:
        """Adjust RSI period based on market regime."""
        try:
            if regime.regime_type == "volatile":
                return max(7, base_period - 4)  # Shorter period for volatile markets
            elif regime.regime_type == "sideways":
                return min(21, base_period + 7)  # Longer period for sideways markets
            else:
                return base_period
        except Exception:
            return base_period
    
    def _adjust_bollinger_period(self, base_period: int, regime: MarketRegime) -> int:
        """Adjust Bollinger Band period based on market regime."""
        try:
            if regime.regime_type == "volatile":
                return max(10, base_period - 5)  # Shorter period for volatile markets
            elif regime.regime_type == "trending_up" or regime.regime_type == "trending_down":
                return min(30, base_period + 10)  # Longer period for trending markets
            else:
                return base_period
        except Exception:
            return base_period
    
    def _adjust_bollinger_std(self, base_std: float, regime: MarketRegime) -> float:
        """Adjust Bollinger Band standard deviation based on market regime."""
        try:
            if regime.regime_type == "volatile":
                return min(3.0, base_std + 0.5)  # Wider bands for volatile markets
            elif regime.volatility < 0.2:
                return max(1.5, base_std - 0.3)  # Tighter bands for low volatility
            else:
                return base_std
        except Exception:
            return base_std
    
    def _adjust_stop_loss_multiplier(self, base_multiplier: float, regime: MarketRegime) -> float:
        """Adjust stop-loss multiplier based on market regime."""
        try:
            volatility_adjustment = regime.volatility * 2.0  # Scale volatility impact
            
            if regime.regime_type == "volatile":
                return min(3.0, base_multiplier + volatility_adjustment)
            elif regime.regime_type == "trending_up" or regime.regime_type == "trending_down":
                if regime.strength > 0.7:
                    return min(2.5, base_multiplier + 0.5)  # Wider stops for strong trends
            
            return max(0.8, min(2.5, base_multiplier + volatility_adjustment * 0.5))
            
        except Exception:
            return base_multiplier
    
    def _adjust_take_profit_multiplier(self, base_multiplier: float, regime: MarketRegime) -> float:
        """Adjust take-profit multiplier based on market regime."""
        try:
            if regime.regime_type == "trending_up" or regime.regime_type == "trending_down":
                if regime.strength > 0.8:
                    return min(4.0, base_multiplier + 1.0)  # Larger targets for strong trends
            elif regime.regime_type == "sideways":
                return max(1.2, base_multiplier - 0.5)  # Smaller targets for sideways markets
            
            return base_multiplier
            
        except Exception:
            return base_multiplier
    
    def _apply_symbol_specific_adjustments(self, params: OptimalParameters, symbol: str) -> OptimalParameters:
        """Apply symbol-specific parameter adjustments based on historical performance."""
        try:
            symbol_data = self.parameter_performance.get(symbol, {})
            
            # Adjust confidence threshold based on symbol performance
            symbol_win_rate = symbol_data.get('win_rate', 0.5)
            if symbol_win_rate > 0.7:
                params.confidence_threshold *= 0.9  # Lower threshold for high-performing symbols
            elif symbol_win_rate < 0.4:
                params.confidence_threshold *= 1.15  # Higher threshold for poor-performing symbols
            
            # Adjust stop-loss based on symbol volatility
            symbol_volatility = symbol_data.get('avg_volatility', 0.05)
            if symbol_volatility > 0.1:
                params.stop_loss_multiplier *= 1.3  # Wider stops for volatile symbols
            
            return params
            
        except Exception:
            return params
    
    def _calculate_regime_duration(self, current_regime: str) -> int:
        """Calculate how long we've been in the current regime."""
        try:
            if not self.regime_history:
                return 0
            
            duration = 0
            for regime in reversed(self.regime_history):
                if regime.regime_type == current_regime:
                    duration += 1
                else:
                    break
            
            return duration
            
        except Exception:
            return 0
    
    def update_parameter_performance(self, symbol: str, parameters: Dict, trade_result: Dict):
        """Update parameter performance tracking."""
        try:
            if symbol not in self.parameter_performance:
                self.parameter_performance[symbol] = {
                    'trades': [],
                    'win_rate': 0.5,
                    'avg_return': 0.0,
                    'avg_volatility': 0.05
                }
            
            symbol_data = self.parameter_performance[symbol]
            
            # Add trade result
            trade_data = {
                'parameters': parameters,
                'result': trade_result,
                'timestamp': time.time()
            }
            
            symbol_data['trades'].append(trade_data)
            
            # Keep only recent trades (last 100)
            if len(symbol_data['trades']) > 100:
                symbol_data['trades'] = symbol_data['trades'][-100:]
            
            # Update aggregated metrics
            recent_trades = symbol_data['trades'][-20:]  # Last 20 trades
            wins = [t for t in recent_trades if t['result'].get('pnl', 0) > 0]
            symbol_data['win_rate'] = len(wins) / len(recent_trades) if recent_trades else 0.5
            
            returns = [t['result'].get('pnl', 0) for t in recent_trades]
            symbol_data['avg_return'] = np.mean(returns) if returns else 0.0
            
            # Save data
            self._save_optimizer_data()
            
        except Exception as exc:
            logger.warning("Parameter performance update failed for %s: %s", symbol, exc)
    
    def get_dynamic_confidence_threshold(self, symbol: str, base_confidence: float, market_conditions: Dict) -> float:
        """Get dynamic confidence threshold based on multiple factors."""
        try:
            # Market regime detection
            price_data = market_conditions.get('price_history', np.array([]))
            volume_data = market_conditions.get('volume_history', np.array([]))
            
            if len(price_data) > 10:
                regime = self.detect_market_regime(price_data, volume_data)
                optimal_params = self.get_optimal_parameters(symbol, regime)
                
                # Blend base confidence with optimal threshold
                dynamic_threshold = (base_confidence * 0.3) + (optimal_params.confidence_threshold * 0.7)
                
                logger.debug("Dynamic confidence for %s: base=%.2f, regime=%s, final=%.2f", 
                           symbol, base_confidence, regime.regime_type, dynamic_threshold)
                
                return dynamic_threshold
            else:
                return base_confidence
                
        except Exception as exc:
            logger.warning("Dynamic confidence calculation failed for %s: %s", symbol, exc)
            return base_confidence
    
    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average."""
        if len(data) == 0:
            return np.array([])
        
        alpha = 2.0 / (period + 1.0)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        
        return ema
    
    def _load_optimizer_data(self):
        """Load optimizer data from disk."""
        try:
            if self.data_path.exists():
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    
                self.parameter_performance = data.get('parameter_performance', {})
                logger.info("Loaded optimizer data for %d symbols", len(self.parameter_performance))
                
        except Exception as exc:
            logger.warning("Failed to load optimizer data: %s", exc)
    
    def _save_optimizer_data(self):
        """Save optimizer data to disk."""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'parameter_performance': self.parameter_performance
            }
            
            with open(self.data_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as exc:
            logger.warning("Failed to save optimizer data: %s", exc)


# Singleton instance
_dynamic_optimizer = None

def get_dynamic_optimizer() -> DynamicOptimizer:
    """Get singleton dynamic optimizer."""
    global _dynamic_optimizer
    if _dynamic_optimizer is None:
        _dynamic_optimizer = DynamicOptimizer()
    return _dynamic_optimizer
