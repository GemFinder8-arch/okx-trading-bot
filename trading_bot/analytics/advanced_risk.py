"""Advanced risk management system with Kelly Criterion, MAE tracking, and dynamic optimization."""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Individual trade record for risk analysis."""
    symbol: str
    entry_price: float
    exit_price: Optional[float]
    entry_time: float
    exit_time: Optional[float]
    position_size: float
    pnl: Optional[float]
    max_adverse_excursion: float  # MAE - maximum loss during trade
    max_favorable_excursion: float  # MFE - maximum profit during trade
    confidence: float
    market_cap_category: str
    volatility: float


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics."""
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    kelly_fraction: float
    var_95: float  # Value at Risk 95%
    expected_return: float
    volatility: float
    calmar_ratio: float


class AdvancedRiskManager:
    """Advanced risk management with Kelly Criterion and MAE tracking."""
    
    def __init__(self, data_path: str = "data/risk_data.json"):
        """Initialize advanced risk manager."""
        self.data_path = Path(data_path)
        self.trade_records: List[TradeRecord] = []
        self.mae_tracking: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.performance_history: deque = deque(maxlen=252)  # 1 year of daily returns
        
        # Risk parameters
        self.max_position_size = 0.05  # 5% base position size
        self.max_portfolio_risk = 0.20  # 20% maximum portfolio risk
        self.kelly_multiplier = 0.25  # Conservative Kelly fraction multiplier
        
        # Load existing data
        self._load_risk_data()
    
    def calculate_kelly_fraction(self, symbol: str, confidence: float, market_conditions: Dict) -> float:
        """Calculate Kelly Criterion position size."""
        try:
            # Get historical performance for this symbol
            symbol_trades = [t for t in self.trade_records if t.symbol == symbol and t.pnl is not None]
            
            if len(symbol_trades) < 10:  # Need minimum trade history
                return self.max_position_size * 0.5  # Conservative default
            
            # Calculate win rate and average win/loss
            wins = [t.pnl for t in symbol_trades if t.pnl > 0]
            losses = [abs(t.pnl) for t in symbol_trades if t.pnl < 0]
            
            if not wins or not losses:
                return self.max_position_size * 0.5
            
            win_rate = len(wins) / len(symbol_trades)
            avg_win = np.mean(wins)
            avg_loss = np.mean(losses)
            
            # Kelly formula: f = (bp - q) / b
            # where b = odds (avg_win/avg_loss), p = win_rate, q = loss_rate
            if avg_loss == 0:
                return self.max_position_size * 0.5
            
            b = avg_win / avg_loss  # Odds
            p = win_rate
            q = 1 - p
            
            kelly_fraction = (b * p - q) / b
            
            # Apply confidence and market condition adjustments
            confidence_multiplier = min(confidence * 1.5, 1.0)  # Boost for high confidence
            
            # Market cap adjustment
            market_cap_mult = market_conditions.get('market_cap_multiplier', 1.0)
            
            # Volatility adjustment
            volatility = market_conditions.get('volatility', 0.05)
            volatility_mult = max(0.5, 1.0 - (volatility * 2))  # Reduce size for high volatility
            
            # Final Kelly fraction with safety multiplier
            final_kelly = kelly_fraction * self.kelly_multiplier * confidence_multiplier * market_cap_mult * volatility_mult
            
            # Clamp to reasonable bounds
            return max(0.01, min(final_kelly, self.max_position_size))
            
        except Exception as exc:
            logger.warning("Kelly fraction calculation failed for %s: %s", symbol, exc)
            return self.max_position_size * 0.5
    
    def track_mae_mfe(self, symbol: str, entry_price: float, current_price: float, position_size: float, is_long: bool = True) -> Tuple[float, float]:
        """Track Maximum Adverse Excursion and Maximum Favorable Excursion."""
        try:
            if is_long:
                pnl_percentage = (current_price - entry_price) / entry_price
            else:
                pnl_percentage = (entry_price - current_price) / entry_price
            
            # Update MAE/MFE tracking
            if symbol not in self.mae_tracking:
                self.mae_tracking[symbol] = deque(maxlen=1000)
            
            current_tracking = self.mae_tracking[symbol]
            
            if not current_tracking:
                # First entry
                current_tracking.append({
                    'mae': min(0, pnl_percentage),
                    'mfe': max(0, pnl_percentage),
                    'entry_price': entry_price,
                    'current_pnl': pnl_percentage
                })
            else:
                # Update existing tracking
                last_record = current_tracking[-1]
                last_record['mae'] = min(last_record['mae'], pnl_percentage)
                last_record['mfe'] = max(last_record['mfe'], pnl_percentage)
                last_record['current_pnl'] = pnl_percentage
            
            return current_tracking[-1]['mae'], current_tracking[-1]['mfe']
            
        except Exception as exc:
            logger.warning("MAE/MFE tracking failed for %s: %s", symbol, exc)
            return 0.0, 0.0
    
    def calculate_optimal_stop_loss(self, symbol: str, entry_price: float, volatility: float, confidence: float) -> Optional[float]:
        """Calculate optimal stop-loss based on MAE analysis.
        
        Returns None if insufficient real data available (no fake defaults).
        """
        try:
            # Get historical MAE data for this symbol
            symbol_trades = [t for t in self.trade_records if t.symbol == symbol and t.max_adverse_excursion < 0]
            
            if len(symbol_trades) < 5:
                # Insufficient real data - return None instead of fake default
                logger.debug("Insufficient MAE data for %s - skipping optimal stop-loss calculation", symbol)
                return None
            
            # Analyze MAE distribution
            mae_values = [abs(t.max_adverse_excursion) for t in symbol_trades]
            mae_percentiles = np.percentile(mae_values, [50, 75, 90, 95])
            
            # Choose stop based on confidence and market conditions
            if confidence > 0.8:
                stop_percentile = mae_percentiles[2]  # 90th percentile for high confidence
            elif confidence > 0.6:
                stop_percentile = mae_percentiles[1]  # 75th percentile for medium confidence
            else:
                stop_percentile = mae_percentiles[0]  # 50th percentile for low confidence
            
            # Adjust for current volatility
            volatility_adjustment = min(volatility * 1.5, 0.03)  # Max 3% volatility adjustment
            final_stop_distance = max(stop_percentile, volatility_adjustment)
            
            # Clamp to reasonable bounds (1% to 8%)
            final_stop_distance = max(0.01, min(final_stop_distance, 0.08))
            
            return entry_price * (1 - final_stop_distance)
            
        except Exception as exc:
            logger.debug("Optimal stop-loss calculation failed for %s: %s - returning None (no fake data)", symbol, exc)
            return None  # REAL DATA ONLY: No fake defaults
    
    def calculate_position_heat(self, positions: Dict) -> float:
        """Calculate current portfolio heat (total risk exposure)."""
        try:
            total_heat = 0.0
            
            for symbol, position in positions.items():
                # Calculate potential loss if all positions hit stop-loss
                if hasattr(position, 'stop_loss') and position.stop_loss:
                    potential_loss = abs(position.entry_price - position.stop_loss) / position.entry_price
                    position_heat = potential_loss * (position.amount * position.entry_price)
                    total_heat += position_heat
            
            return total_heat
            
        except Exception as exc:
            logger.warning("Position heat calculation failed: %s", exc)
            return 0.0
    
    def calculate_risk_metrics(self) -> RiskMetrics:
        """Calculate comprehensive risk metrics."""
        try:
            if len(self.trade_records) < 10:
                return self._default_risk_metrics()
            
            # Get completed trades with PnL
            completed_trades = [t for t in self.trade_records if t.pnl is not None]
            returns = [t.pnl for t in completed_trades]
            
            if not returns:
                return self._default_risk_metrics()
            
            returns_array = np.array(returns)
            
            # Basic metrics
            total_return = np.sum(returns_array)
            win_rate = len([r for r in returns if r > 0]) / len(returns)
            
            wins = [r for r in returns if r > 0]
            losses = [abs(r) for r in returns if r < 0]
            
            profit_factor = sum(wins) / sum(losses) if losses else float('inf')
            
            # Risk-adjusted metrics
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            
            # Sharpe ratio (assuming risk-free rate = 0)
            sharpe_ratio = mean_return / std_return if std_return > 0 else 0
            
            # Sortino ratio (downside deviation)
            downside_returns = [r for r in returns if r < 0]
            downside_std = np.std(downside_returns) if downside_returns else std_return
            sortino_ratio = mean_return / downside_std if downside_std > 0 else 0
            
            # Maximum drawdown
            cumulative_returns = np.cumsum(returns_array)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - running_max) / running_max
            max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0
            
            # Value at Risk (95%)
            var_95 = np.percentile(returns_array, 5) if len(returns_array) > 0 else 0
            
            # Kelly fraction
            if losses and win_rate > 0:
                avg_win = np.mean(wins) if wins else 0
                avg_loss = np.mean(losses) if losses else 1
                b = avg_win / avg_loss
                kelly_fraction = (b * win_rate - (1 - win_rate)) / b
            else:
                kelly_fraction = 0
            
            # Calmar ratio (return / max drawdown)
            calmar_ratio = total_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            return RiskMetrics(
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                profit_factor=profit_factor,
                kelly_fraction=kelly_fraction,
                var_95=var_95,
                expected_return=mean_return,
                volatility=std_return,
                calmar_ratio=calmar_ratio
            )
            
        except Exception as exc:
            logger.warning("Risk metrics calculation failed: %s", exc)
            return self._default_risk_metrics()
    
    def should_reduce_exposure(self, current_positions: Dict, market_conditions: Dict) -> bool:
        """Determine if exposure should be reduced based on risk metrics."""
        try:
            # Calculate current portfolio heat
            portfolio_heat = self.calculate_position_heat(current_positions)
            
            # Get recent performance
            risk_metrics = self.calculate_risk_metrics()
            
            # Risk reduction triggers
            triggers = []
            
            # 1. Excessive portfolio heat
            if portfolio_heat > self.max_portfolio_risk:
                triggers.append("portfolio_heat_excessive")
            
            # 2. Poor recent performance
            if risk_metrics.sharpe_ratio < 0:
                triggers.append("negative_sharpe")
            
            # 3. High drawdown
            if risk_metrics.max_drawdown < -0.15:  # 15% drawdown
                triggers.append("high_drawdown")
            
            # 4. Market volatility spike
            market_volatility = market_conditions.get('volatility', 0.05)
            if market_volatility > 0.1:  # 10% volatility
                triggers.append("high_market_volatility")
            
            if triggers:
                logger.info("🛡️ RISK REDUCTION TRIGGERED: %s", ", ".join(triggers))
                return True
            
            return False
            
        except Exception as exc:
            logger.warning("Risk exposure check failed: %s", exc)
            return False
    
    def record_trade(self, trade_record: TradeRecord):
        """Record a completed trade for analysis."""
        try:
            self.trade_records.append(trade_record)
            
            # Maintain reasonable history size
            if len(self.trade_records) > 10000:
                self.trade_records = self.trade_records[-5000:]  # Keep last 5000 trades
            
            # Save to disk
            self._save_risk_data()
            
        except Exception as exc:
            logger.warning("Trade recording failed: %s", exc)
    
    def _load_risk_data(self):
        """Load risk data from disk."""
        try:
            if self.data_path.exists():
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    
                # Convert to TradeRecord objects
                for trade_data in data.get('trades', []):
                    trade_record = TradeRecord(**trade_data)
                    self.trade_records.append(trade_record)
                    
                logger.info("Loaded %d trade records for risk analysis", len(self.trade_records))
                
        except Exception as exc:
            logger.warning("Failed to load risk data: %s", exc)
    
    def _save_risk_data(self):
        """Save risk data to disk."""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert TradeRecord objects to dict
            trades_data = []
            for trade in self.trade_records[-1000:]:  # Save last 1000 trades
                trades_data.append({
                    'symbol': trade.symbol,
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price,
                    'entry_time': trade.entry_time,
                    'exit_time': trade.exit_time,
                    'position_size': trade.position_size,
                    'pnl': trade.pnl,
                    'max_adverse_excursion': trade.max_adverse_excursion,
                    'max_favorable_excursion': trade.max_favorable_excursion,
                    'confidence': trade.confidence,
                    'market_cap_category': trade.market_cap_category,
                    'volatility': trade.volatility
                })
            
            data = {'trades': trades_data}
            
            with open(self.data_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as exc:
            logger.warning("Failed to save risk data: %s", exc)
    


# Singleton instance
_advanced_risk_manager = None

def get_advanced_risk_manager() -> AdvancedRiskManager:
    """Get singleton advanced risk manager."""
    global _advanced_risk_manager
    if _advanced_risk_manager is None:
        _advanced_risk_manager = AdvancedRiskManager()
    return _advanced_risk_manager
