"""Parallel execution manager for optimized API calls and symbol processing."""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result of a parallel task execution."""
    task_id: str
    symbol: str
    success: bool
    result: Any
    error: Optional[str]
    execution_time: float


@dataclass
class BatchResult:
    """Result of a batch execution."""
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    total_time: float
    results: List[TaskResult]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        return (self.successful_tasks / self.total_tasks * 100) if self.total_tasks > 0 else 0.0


class ParallelExecutor:
    """Parallel execution manager for optimized trading operations."""
    
    def __init__(
        self,
        max_workers: int = 10,
        timeout_seconds: int = 30,
        rate_limit_per_second: int = 20
    ):
        """Initialize parallel executor.
        
        Args:
            max_workers: Maximum number of parallel workers
            timeout_seconds: Timeout for individual tasks
            rate_limit_per_second: Maximum API calls per second
        """
        self.max_workers = max_workers
        self.timeout_seconds = timeout_seconds
        self.rate_limit_per_second = rate_limit_per_second
        self.min_interval = 1.0 / rate_limit_per_second
        
        # Rate limiting
        self.last_call_time = 0.0
        self.call_count = 0
        self.call_times: List[float] = []
    
    def execute_batch(
        self,
        tasks: List[Tuple[str, str, Callable, tuple, dict]],
        description: str = "Batch execution"
    ) -> BatchResult:
        """Execute a batch of tasks in parallel with rate limiting.
        
        Args:
            tasks: List of (task_id, symbol, function, args, kwargs)
            description: Description for logging
            
        Returns:
            BatchResult with execution statistics
        """
        start_time = time.time()
        results: List[TaskResult] = []
        
        logger.info("Starting %s with %d tasks", description, len(tasks))
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {}
            
            for task_id, symbol, func, args, kwargs in tasks:
                # Apply rate limiting
                self._apply_rate_limit()
                
                future = executor.submit(
                    self._execute_single_task,
                    task_id, symbol, func, args, kwargs
                )
                future_to_task[future] = (task_id, symbol)
            
            # Collect results as they complete
            for future in as_completed(future_to_task.keys(), timeout=self.timeout_seconds):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    task_id, symbol = future_to_task[future]
                    error_result = TaskResult(
                        task_id=task_id,
                        symbol=symbol,
                        success=False,
                        result=None,
                        error=str(exc),
                        execution_time=0.0
                    )
                    results.append(error_result)
                    logger.warning("Task %s for %s failed: %s", task_id, symbol, exc)
        
        # Calculate statistics
        total_time = time.time() - start_time
        successful_tasks = sum(1 for r in results if r.success)
        failed_tasks = len(results) - successful_tasks
        
        batch_result = BatchResult(
            total_tasks=len(tasks),
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            total_time=total_time,
            results=results
        )
        
        logger.info(
            "%s completed: %d/%d successful (%.1f%%) in %.2fs",
            description, successful_tasks, len(tasks), 
            batch_result.success_rate, total_time
        )
        
        return batch_result
    
    def _execute_single_task(
        self,
        task_id: str,
        symbol: str,
        func: Callable,
        args: tuple,
        kwargs: dict
    ) -> TaskResult:
        """Execute a single task with timing and error handling."""
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            return TaskResult(
                task_id=task_id,
                symbol=symbol,
                success=True,
                result=result,
                error=None,
                execution_time=execution_time
            )
            
        except Exception as exc:
            execution_time = time.time() - start_time
            
            return TaskResult(
                task_id=task_id,
                symbol=symbol,
                success=False,
                result=None,
                error=str(exc),
                execution_time=execution_time
            )
    
    def _apply_rate_limit(self) -> None:
        """Apply rate limiting to prevent API overload."""
        current_time = time.time()
        
        # Clean old call times (older than 1 second)
        self.call_times = [t for t in self.call_times if current_time - t < 1.0]
        
        # Check if we need to wait
        if len(self.call_times) >= self.rate_limit_per_second:
            sleep_time = 1.0 - (current_time - self.call_times[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
                current_time = time.time()
        
        # Record this call
        self.call_times.append(current_time)
    
    def execute_market_data_batch(
        self,
        symbols: List[str],
        market_data_manager,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Execute parallel market data fetching for multiple symbols.
        
        Args:
            symbols: List of trading symbols
            market_data_manager: MarketDataManager instance
            force_refresh: Force refresh cached data
            
        Returns:
            Dictionary mapping symbols to their market data
        """
        tasks = []
        
        for symbol in symbols:
            task = (
                f"market_data_{symbol}",
                symbol,
                market_data_manager.get_multi_timeframe_data,
                (symbol, force_refresh),
                {}
            )
            tasks.append(task)
        
        batch_result = self.execute_batch(tasks, f"Market data fetch for {len(symbols)} symbols")
        
        # Convert results to dictionary
        market_data = {}
        for result in batch_result.results:
            if result.success and result.result:
                market_data[result.symbol] = result.result
        
        return market_data
    
    def execute_technical_analysis_batch(
        self,
        symbol_data_pairs: List[Tuple[str, Any]],
        technical_analyzer,
        decision: str = "BUY"
    ) -> Dict[str, Tuple[float, float]]:
        """Execute parallel technical analysis for multiple symbols.
        
        Args:
            symbol_data_pairs: List of (symbol, market_data) pairs
            technical_analyzer: TechnicalAnalyzer instance
            decision: Trading decision ("BUY" or "SELL")
            
        Returns:
            Dictionary mapping symbols to (stop_loss, take_profit) tuples
        """
        tasks = []
        
        for symbol, mtf_data in symbol_data_pairs:
            if not mtf_data:
                continue
                
            # Get current price from data
            current_price = None
            for tf in ['1m', '5m', '15m']:
                candles = mtf_data.get_timeframe(tf)
                if candles:
                    current_price = candles[-1].close
                    break
            
            if current_price:
                task = (
                    f"technical_analysis_{symbol}",
                    symbol,
                    technical_analyzer.calculate_dynamic_levels_mtf,
                    (current_price, mtf_data, decision),
                    {"use_fibonacci": True}
                )
                tasks.append(task)
        
        batch_result = self.execute_batch(tasks, f"Technical analysis for {len(tasks)} symbols")
        
        # Convert results to dictionary
        technical_levels = {}
        for result in batch_result.results:
            if result.success and result.result:
                technical_levels[result.symbol] = result.result
        
        return technical_levels
    
    def execute_risk_analysis_batch(
        self,
        symbol_price_pairs: List[Tuple[str, float, float]],
        enhanced_risk_manager,
        current_balance: float,
        existing_positions: Dict[str, Any]
    ) -> Dict[str, float]:
        """Execute parallel risk analysis for position sizing.
        
        Args:
            symbol_price_pairs: List of (symbol, entry_price, stop_loss) tuples
            enhanced_risk_manager: EnhancedRiskManager instance
            current_balance: Current account balance
            existing_positions: Dictionary of existing positions
            
        Returns:
            Dictionary mapping symbols to optimal position sizes
        """
        tasks = []
        
        for symbol, entry_price, stop_loss in symbol_price_pairs:
            task = (
                f"risk_analysis_{symbol}",
                symbol,
                enhanced_risk_manager.calculate_position_size,
                (),
                {
                    "symbol": symbol,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "current_balance": current_balance,
                    "existing_positions": existing_positions
                }
            )
            tasks.append(task)
        
        batch_result = self.execute_batch(tasks, f"Risk analysis for {len(tasks)} symbols")
        
        # Convert results to dictionary
        position_sizes = {}
        for result in batch_result.results:
            if result.success and result.result is not None:
                position_sizes[result.symbol] = result.result
        
        return position_sizes
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        current_time = time.time()
        recent_calls = [t for t in self.call_times if current_time - t < 60.0]  # Last minute
        
        return {
            "calls_per_minute": len(recent_calls),
            "calls_per_second": len([t for t in self.call_times if current_time - t < 1.0]),
            "max_calls_per_second": self.rate_limit_per_second,
            "active_workers": self.max_workers
        }
