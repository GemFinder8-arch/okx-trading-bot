"""Daily performance tracking and optimization for profitable trading."""

import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Record of a single trade for performance tracking."""
    symbol: str
    side: str  # "BUY" or "SELL"
    entry_price: float
    exit_price: Optional[float] = None
    amount: float = 0.0
    entry_time: float = 0.0
    exit_time: Optional[float] = None
    pnl_usd: Optional[float] = None
    pnl_percentage: Optional[float] = None
    reason: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class DailyStats:
    """Daily trading statistics."""
    date: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl_usd: float = 0.0
    total_pnl_percentage: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0


class DailyPerformanceTracker:
    """Track and optimize daily trading performance for consistent profits."""
    
    def __init__(self, data_dir: str = "data"):
        """Initialize performance tracker."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.trades_file = self.data_dir / "daily_trades.json"
        self.stats_file = self.data_dir / "daily_stats.json"
        
        self.trades: List[TradeRecord] = []
        self.daily_stats: Dict[str, DailyStats] = {}
        
        self._load_data()
    
    def record_trade_entry(
        self, 
        symbol: str, 
        entry_price: float, 
        amount: float,
        confidence: float
    ) -> str:
        """Record a new trade entry."""
        trade_id = f"{symbol}_{int(time.time())}"
        
        trade = TradeRecord(
            symbol=symbol,
            side="BUY",
            entry_price=entry_price,
            amount=amount,
            entry_time=time.time(),
            confidence=confidence
        )
        
        self.trades.append(trade)
        logger.info(f"📈 TRADE ENTRY: {symbol} at ${entry_price:.6f} (confidence: {confidence:.2f})")
        
        return trade_id
    
    def record_trade_exit(
        self, 
        symbol: str, 
        exit_price: float, 
        reason: str
    ) -> Optional[float]:
        """Record trade exit and calculate PnL."""
        # Find the most recent open trade for this symbol
        for trade in reversed(self.trades):
            if trade.symbol == symbol and trade.exit_price is None:
                trade.exit_price = exit_price
                trade.exit_time = time.time()
                trade.reason = reason
                
                # Calculate PnL
                trade.pnl_usd = (exit_price - trade.entry_price) * trade.amount
                trade.pnl_percentage = ((exit_price - trade.entry_price) / trade.entry_price) * 100
                
                logger.info(
                    f"📊 TRADE EXIT: {symbol} at ${exit_price:.6f} - "
                    f"PnL: ${trade.pnl_usd:.2f} ({trade.pnl_percentage:.2f}%) - {reason}"
                )
                
                self._update_daily_stats()
                self._save_data()
                
                return trade.pnl_percentage
        
        logger.warning(f"No open trade found for {symbol}")
        return None
    
    def get_daily_performance(self, date: Optional[str] = None) -> DailyStats:
        """Get performance stats for a specific date."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        return self.daily_stats.get(date, DailyStats(date=date))
    
    def get_win_rate(self, days: int = 7) -> float:
        """Get win rate over the last N days."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        total_trades = 0
        winning_trades = 0
        
        for date_str, stats in self.daily_stats.items():
            date = datetime.strptime(date_str, "%Y-%m-%d")
            if start_date <= date <= end_date:
                total_trades += stats.total_trades
                winning_trades += stats.winning_trades
        
        return (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    def get_profit_summary(self, days: int = 7) -> Dict[str, float]:
        """Get profit summary over the last N days."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        total_pnl = 0.0
        total_trades = 0
        winning_trades = 0
        
        for date_str, stats in self.daily_stats.items():
            date = datetime.strptime(date_str, "%Y-%m-%d")
            if start_date <= date <= end_date:
                total_pnl += stats.total_pnl_usd
                total_trades += stats.total_trades
                winning_trades += stats.winning_trades
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        avg_daily_profit = total_pnl / days if days > 0 else 0.0
        
        return {
            "total_pnl_usd": total_pnl,
            "total_trades": total_trades,
            "win_rate_pct": win_rate,
            "avg_daily_profit": avg_daily_profit,
            "days_analyzed": days
        }
    
    def should_reduce_trading(self) -> bool:
        """Determine if trading should be reduced due to poor performance."""
        recent_performance = self.get_profit_summary(days=3)
        
        # Reduce trading if:
        # 1. Win rate below 40% in last 3 days
        # 2. Total PnL negative in last 3 days
        # 3. More than 5 consecutive losses
        
        if recent_performance["win_rate_pct"] < 40.0:
            logger.warning("⚠️ Win rate below 40%, reducing trading activity")
            return True
        
        if recent_performance["total_pnl_usd"] < -100.0:  # More than $100 loss
            logger.warning("⚠️ Significant losses detected, reducing trading activity")
            return True
        
        return False
    
    def _update_daily_stats(self):
        """Update daily statistics."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Get today's completed trades
        today_trades = [
            trade for trade in self.trades
            if (trade.exit_time and 
                datetime.fromtimestamp(trade.exit_time).strftime("%Y-%m-%d") == today)
        ]
        
        if not today_trades:
            return
        
        # Calculate statistics
        total_trades = len(today_trades)
        winning_trades = len([t for t in today_trades if t.pnl_usd and t.pnl_usd > 0])
        losing_trades = total_trades - winning_trades
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        total_pnl_usd = sum(t.pnl_usd for t in today_trades if t.pnl_usd)
        
        wins = [t.pnl_usd for t in today_trades if t.pnl_usd and t.pnl_usd > 0]
        losses = [abs(t.pnl_usd) for t in today_trades if t.pnl_usd and t.pnl_usd < 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        
        profit_factor = (sum(wins) / sum(losses)) if losses else float('inf')
        
        # Update daily stats
        self.daily_stats[today] = DailyStats(
            date=today,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl_usd=total_pnl_usd,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor
        )
        
        logger.info(
            f"📊 TODAY'S PERFORMANCE: {total_trades} trades, "
            f"{win_rate:.1f}% win rate, ${total_pnl_usd:.2f} PnL"
        )
    
    def _load_data(self):
        """Load existing trade data."""
        try:
            if self.trades_file.exists():
                with open(self.trades_file, 'r') as f:
                    trades_data = json.load(f)
                    self.trades = [TradeRecord(**trade) for trade in trades_data]
            
            if self.stats_file.exists():
                with open(self.stats_file, 'r') as f:
                    stats_data = json.load(f)
                    self.daily_stats = {
                        date: DailyStats(**stats) for date, stats in stats_data.items()
                    }
        except Exception as exc:
            logger.warning(f"Could not load performance data: {exc}")
    
    def _save_data(self):
        """Save trade data to files."""
        try:
            with open(self.trades_file, 'w') as f:
                json.dump([asdict(trade) for trade in self.trades], f, indent=2)
            
            with open(self.stats_file, 'w') as f:
                json.dump({
                    date: asdict(stats) for date, stats in self.daily_stats.items()
                }, f, indent=2)
        except Exception as exc:
            logger.error(f"Could not save performance data: {exc}")


# Global performance tracker instance
_performance_tracker: Optional[DailyPerformanceTracker] = None


def get_performance_tracker() -> DailyPerformanceTracker:
    """Get global performance tracker instance."""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = DailyPerformanceTracker()
    return _performance_tracker
