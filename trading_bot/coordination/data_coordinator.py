"""Centralized data coordination to eliminate redundant API calls and improve performance."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from trading_bot.analytics.decision_engine import EnhancedDecisionEngine, TradingSignal
from trading_bot.analytics.enhanced_risk import EnhancedRiskManager
from trading_bot.analytics.market_data import MarketDataManager, MultiTimeframeData
from trading_bot.analytics.technical import TechnicalAnalyzer
from trading_bot.infrastructure.cache_manager import get_cache

logger = logging.getLogger(__name__)


@dataclass
class SymbolAnalysisPackage:
    """Complete analysis package for a trading symbol."""
    symbol: str
    mtf_data: MultiTimeframeData
    current_price: float
    order_book: Optional[Dict]
    trading_signal: TradingSignal
    technical_levels: Tuple[float, float]  # (stop_loss, take_profit)
    optimal_position_size: float
    analysis_timestamp: float
    
    def is_stale(self, max_age_seconds: int = 30) -> bool:
        """Check if analysis is stale."""
        return time.time() - self.analysis_timestamp > max_age_seconds


class TradingDataCoordinator:
    """Centralized coordinator for all trading data and analysis."""
    
    def __init__(
        self,
        market_data_manager: MarketDataManager,
        technical_analyzer: TechnicalAnalyzer,
        decision_engine: EnhancedDecisionEngine,
        risk_manager: EnhancedRiskManager,
        okx_connector
    ):
        """Initialize data coordinator.
        
        Args:
            market_data_manager: Market data manager instance
            technical_analyzer: Technical analyzer instance
            decision_engine: Enhanced decision engine instance
            risk_manager: Enhanced risk manager instance
            okx_connector: OKX connector for additional data
        """
        self.market_data = market_data_manager
        self.technical = technical_analyzer
        self.decision_engine = decision_engine
        self.risk_manager = risk_manager
        self.okx = okx_connector
        
        # Analysis cache
        self.analysis_cache = get_cache(
            "symbol_analysis",
            max_size_mb=20.0,
            default_ttl_seconds=30.0,
            persistence_path="data/analysis_cache.pkl"
        )
        
        # Performance tracking
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_requests = 0
    
    def get_comprehensive_analysis(
        self,
        symbol: str,
        existing_positions: Dict[str, any],
        current_balance: float,
        force_refresh: bool = False
    ) -> Optional[SymbolAnalysisPackage]:
        """Get complete analysis for a symbol with single data fetch.
        
        Args:
            symbol: Trading symbol
            existing_positions: Current open positions
            current_balance: Current account balance
            force_refresh: Force refresh of cached analysis
            
        Returns:
            SymbolAnalysisPackage with complete analysis or None if failed
        """
        self.total_requests += 1
        
        # Check cache first
        cache_key = f"analysis_{symbol}"
        if not force_refresh:
            cached_analysis = self.analysis_cache.get(cache_key)
            if cached_analysis and not cached_analysis.is_stale():
                self.cache_hits += 1
                logger.debug("Cache hit for %s analysis", symbol)
                return cached_analysis
        
        self.cache_misses += 1
        
        try:
            # Single coordinated data fetch
            analysis_start = time.time()
            
            # 1. Get multi-timeframe market data (primary data source)
            mtf_data = self.market_data.get_multi_timeframe_data(symbol, force_refresh)
            if not mtf_data:
                logger.warning("No market data available for %s", symbol)
                return None
            
            # 2. Get current price from ticker (fast call)
            current_price = self._get_current_price(symbol)
            if not current_price or current_price <= 0:
                logger.warning("Invalid current price for %s", symbol)
                return None
            
            # 3. Get order book (optional, for microstructure analysis)
            order_book = self._get_order_book(symbol)
            
            # 4. Generate trading signal (uses all above data)
            trading_signal = self.decision_engine.make_trading_decision(
                symbol=symbol,
                mtf_data=mtf_data,
                current_price=current_price,
                technical_features=None,  # Will be calculated internally
                order_book=order_book
            )
            
            # 5. Calculate technical levels (reuses mtf_data)
            technical_levels = self.technical.calculate_dynamic_levels_mtf(
                current_price=current_price,
                mtf_data=mtf_data,
                decision=trading_signal.decision,
                use_fibonacci=True
            )
            
            # 6. Calculate optimal position size (reuses analysis)
            optimal_size = 0.0
            if trading_signal.decision in ["BUY", "SELL"]:
                optimal_size = self.risk_manager.calculate_position_size(
                    symbol=symbol,
                    entry_price=current_price,
                    stop_loss=technical_levels[0],
                    current_balance=current_balance,
                    existing_positions=existing_positions
                )
                
                # Apply signal-based position size multiplier
                size_multiplier = trading_signal.get_position_size_multiplier()
                optimal_size *= size_multiplier
            
            # 7. Create comprehensive analysis package
            analysis_package = SymbolAnalysisPackage(
                symbol=symbol,
                mtf_data=mtf_data,
                current_price=current_price,
                order_book=order_book,
                trading_signal=trading_signal,
                technical_levels=technical_levels,
                optimal_position_size=optimal_size,
                analysis_timestamp=time.time()
            )
            
            # Cache the analysis
            self.analysis_cache.set(cache_key, analysis_package, ttl_seconds=30.0)
            
            analysis_time = time.time() - analysis_start
            logger.debug(
                "Comprehensive analysis for %s completed in %.2fs (decision=%s, confidence=%.2f)",
                symbol, analysis_time, trading_signal.decision, trading_signal.confidence
            )
            
            return analysis_package
            
        except Exception as exc:
            logger.error("Comprehensive analysis failed for %s: %s", symbol, exc)
            return None
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price with caching."""
        try:
            ticker = self.okx.fetch_ticker(symbol)
            return float(ticker.get("last", 0)) if ticker else None
        except Exception as exc:
            logger.warning("Failed to get current price for %s: %s", symbol, exc)
            return None
    
    def _get_order_book(self, symbol: str) -> Optional[Dict]:
        """Get order book with error handling."""
        try:
            order_book_raw = self.okx.fetch_order_book(symbol, limit=10)
            return {
                'bids': order_book_raw.get('bids', []),
                'asks': order_book_raw.get('asks', [])
            }
        except Exception as exc:
            logger.debug("Could not fetch order book for %s: %s", symbol, exc)
            return None
    
    def batch_analyze_symbols(
        self,
        symbols: list[str],
        existing_positions: Dict[str, any],
        current_balance: float,
        max_concurrent: int = 6
    ) -> Dict[str, SymbolAnalysisPackage]:
        """Analyze multiple symbols efficiently.
        
        Args:
            symbols: List of symbols to analyze
            existing_positions: Current open positions
            current_balance: Current account balance
            max_concurrent: Maximum concurrent analyses
            
        Returns:
            Dictionary mapping symbols to their analysis packages
        """
        results = {}
        
        # Process in batches to avoid overwhelming the system
        for i in range(0, len(symbols), max_concurrent):
            batch = symbols[i:i + max_concurrent]
            
            for symbol in batch:
                analysis = self.get_comprehensive_analysis(
                    symbol, existing_positions, current_balance
                )
                if analysis:
                    results[symbol] = analysis
        
        logger.info(
            "Batch analysis completed: %d/%d symbols successful",
            len(results), len(symbols)
        )
        
        return results
    
    def get_performance_stats(self) -> Dict[str, any]:
        """Get coordinator performance statistics."""
        cache_hit_rate = (self.cache_hits / self.total_requests * 100) if self.total_requests > 0 else 0
        
        return {
            'total_requests': self.total_requests,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate_pct': cache_hit_rate,
            'analysis_cache_stats': self.analysis_cache.get_stats()
        }
    
    def clear_cache(self) -> None:
        """Clear analysis cache."""
        self.analysis_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_requests = 0
        logger.info("Data coordinator cache cleared")
    
    def preload_symbols(self, symbols: list[str], existing_positions: Dict, current_balance: float) -> None:
        """Preload analysis for symbols to warm the cache."""
        logger.info("Preloading analysis for %d symbols", len(symbols))
        
        for symbol in symbols:
            try:
                self.get_comprehensive_analysis(symbol, existing_positions, current_balance)
            except Exception as exc:
                logger.warning("Failed to preload analysis for %s: %s", symbol, exc)
        
        logger.info("Symbol preloading completed")
