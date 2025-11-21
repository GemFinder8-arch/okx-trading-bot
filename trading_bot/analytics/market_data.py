"""Enhanced market data management with multi-timeframe support and validation."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from trading_bot.infrastructure.cache_manager import get_cache

logger = logging.getLogger(__name__)


@dataclass
class OHLCV:
    """OHLCV candle data structure."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class MultiTimeframeData:
    """Multi-timeframe market data container."""
    symbol: str
    timeframes: Dict[str, List[OHLCV]]
    last_update: float
    
    def get_timeframe(self, timeframe: str) -> List[OHLCV]:
        """Get data for specific timeframe."""
        return self.timeframes.get(timeframe, [])
    
    def is_stale(self, max_age_seconds: int = 60) -> bool:
        """Check if data is stale."""
        return time.time() - self.last_update > max_age_seconds


class MarketDataManager:
    """Enhanced market data manager with validation and multi-timeframe support."""
    
    def __init__(self, okx_connector, cache_duration: int = 30):
        """Initialize market data manager.
        
        Args:
            okx_connector: OKX exchange connector
            cache_duration: Cache duration in seconds
        """
        self.okx = okx_connector
        self.cache_duration = cache_duration
        
        # Advanced caching system
        self.cache = get_cache(
            "market_data",
            max_size_mb=50.0,
            default_ttl_seconds=cache_duration,
            persistence_path="data/market_data_cache.pkl"
        )
        
        # Legacy cache for compatibility
        self.data_cache: Dict[str, MultiTimeframeData] = {}
        
        # Supported timeframes in order of priority
        self.timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        self.primary_timeframes = ['1m', '5m', '15m', '1h']  # For analysis
        
        # Data quality thresholds - reduced for better compatibility
        self.min_candles = 10  # Reduced from 50 to 10 for more flexibility
        self.max_gap_ratio = 0.2  # Increased tolerance to 20%
        self.outlier_threshold = 5.0  # 5 standard deviations
    
    def get_multi_timeframe_data(
        self, 
        symbol: str, 
        force_refresh: bool = False
    ) -> Optional[MultiTimeframeData]:
        """Get validated multi-timeframe data for symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            force_refresh: Force refresh cached data
            
        Returns:
            MultiTimeframeData or None if data unavailable
        """
        # Check advanced cache first
        cache_key = f"mtf_data_{symbol}"
        if not force_refresh:
            cached_data = self.cache.get(cache_key)
            if cached_data and not cached_data.is_stale(self.cache_duration):
                return cached_data
        
        # Fetch fresh data
        try:
            timeframe_data = {}
            
            for tf in self.primary_timeframes:
                try:
                    # Fetch maximum available data (OKX allows up to 300 for most timeframes)
                    # Let the exchange determine how much data is actually available
                    raw_data = self.okx.fetch_ohlcv(symbol, tf, limit=300)
                    if not raw_data or len(raw_data) < self.min_candles:
                        logger.warning("Insufficient %s data for %s: %d candles", tf, symbol, len(raw_data) if raw_data else 0)
                        continue
                    
                    # Convert to OHLCV objects
                    ohlcv_data = []
                    for candle in raw_data:
                        if len(candle) >= 6:
                            ohlcv_data.append(OHLCV(
                                timestamp=int(candle[0]),
                                open=float(candle[1]),
                                high=float(candle[2]),
                                low=float(candle[3]),
                                close=float(candle[4]),
                                volume=float(candle[5])
                            ))
                    
                    # Validate data quality
                    if self._validate_data_quality(ohlcv_data, tf):
                        timeframe_data[tf] = ohlcv_data
                    else:
                        logger.warning("Data quality check failed for %s %s", symbol, tf)
                        
                except Exception as exc:
                    logger.warning("Failed to fetch %s data for %s: %s", tf, symbol, exc)
                    continue
            
            if not timeframe_data:
                logger.error("No valid timeframe data available for %s", symbol)
                return None
            
            # Create multi-timeframe data object
            mtf_data = MultiTimeframeData(
                symbol=symbol,
                timeframes=timeframe_data,
                last_update=time.time()
            )
            
            # Cache the data in advanced cache
            self.cache.set(cache_key, mtf_data, ttl_seconds=self.cache_duration)
            
            # Also update legacy cache for compatibility
            self.data_cache[symbol] = mtf_data
            
            logger.debug("Updated multi-timeframe data for %s: %s", symbol, list(timeframe_data.keys()))
            return mtf_data
            
        except Exception as exc:
            logger.error("Failed to get multi-timeframe data for %s: %s", symbol, exc)
            return None
    
    def _validate_data_quality(self, data: List[OHLCV], timeframe: str) -> bool:
        """Validate OHLCV data quality.
        
        Args:
            data: List of OHLCV candles
            timeframe: Timeframe string
            
        Returns:
            True if data passes quality checks
        """
        if not data or len(data) < self.min_candles:
            return False
        
        try:
            # Check for missing timestamps (gaps)
            timestamps = [candle.timestamp for candle in data]
            if len(set(timestamps)) != len(timestamps):
                logger.warning("Duplicate timestamps found in %s data", timeframe)
                return False
            
            # Check for reasonable price ranges
            prices = [candle.close for candle in data]
            if any(p <= 0 for p in prices):
                logger.warning("Invalid prices (<=0) found in %s data", timeframe)
                return False
            
            # Check for extreme outliers
            price_changes = np.diff(prices) / prices[:-1]
            if len(price_changes) > 10:
                std_dev = np.std(price_changes)
                outliers = np.abs(price_changes) > (self.outlier_threshold * std_dev)
                if np.sum(outliers) > len(price_changes) * 0.05:  # More than 5% outliers
                    logger.warning("Too many price outliers in %s data: %d/%d", 
                                 timeframe, np.sum(outliers), len(price_changes))
                    return False
            
            # Check OHLC consistency
            for candle in data:
                if not (candle.low <= candle.open <= candle.high and 
                       candle.low <= candle.close <= candle.high):
                    logger.warning("OHLC inconsistency found in %s data", timeframe)
                    return False
            
            return True
            
        except Exception as exc:
            logger.warning("Data validation failed for %s: %s", timeframe, exc)
            return False
    
    def get_candles(self, symbol: str, timeframe: str, limit: int = 100) -> Optional[List[OHLCV]]:
        """Get candles for specific symbol and timeframe.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            List of OHLCV candles or None if unavailable
        """
        try:
            # Get multi-timeframe data
            mtf_data = self.get_multi_timeframe_data(symbol)
            if not mtf_data:
                logger.debug("No multi-timeframe data available for %s", symbol)
                return None
            
            # Get specific timeframe data
            candles = mtf_data.get_timeframe(timeframe)
            if not candles:
                logger.debug("No %s data available for %s", timeframe, symbol)
                return None
            
            # Return last 'limit' candles
            return candles[-limit:] if len(candles) > limit else candles
            
        except Exception as exc:
            logger.warning("Failed to get candles for %s %s: %s", symbol, timeframe, exc)
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price with fallback sources.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Current price or None if unavailable
        """
        try:
            # Try ticker first (fastest)
            ticker = self.okx.fetch_ticker(symbol)
            if ticker and 'last' in ticker:
                return float(ticker['last'])
            
            # Fallback to OHLCV data
            mtf_data = self.get_multi_timeframe_data(symbol)
            if mtf_data:
                # Use 1m data if available, otherwise shortest timeframe
                for tf in ['1m', '5m', '15m', '1h']:
                    candles = mtf_data.get_timeframe(tf)
                    if candles:
                        return candles[-1].close
            
            logger.warning("No price data available for %s", symbol)
            return None
            
        except Exception as exc:
            logger.error("Failed to get current price for %s: %s", symbol, exc)
            return None
    
    def get_volatility(self, symbol: str, period: int = 20) -> Optional[float]:
        """Calculate price volatility (standard deviation of returns).
        
        Args:
            symbol: Trading symbol
            period: Period for volatility calculation
            
        Returns:
            Volatility (annualized) or None if insufficient data
        """
        try:
            mtf_data = self.get_multi_timeframe_data(symbol)
            if not mtf_data:
                return None
            
            # Use 1-hour data for volatility calculation
            candles = mtf_data.get_timeframe('1h')
            if not candles or len(candles) < period + 1:
                # Fallback to 15m data
                candles = mtf_data.get_timeframe('15m')
                if not candles or len(candles) < period + 1:
                    return None
            
            # Calculate returns
            prices = [candle.close for candle in candles[-period-1:]]
            returns = np.diff(prices) / prices[:-1]
            
            # Calculate volatility (annualized)
            volatility = np.std(returns) * np.sqrt(365 * 24)  # Annualized hourly volatility
            
            return float(volatility)
            
        except Exception as exc:
            logger.warning("Failed to calculate volatility for %s: %s", symbol, exc)
            return None
    
    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """Clear data cache.
        
        Args:
            symbol: Specific symbol to clear, or None for all
        """
        if symbol:
            self.data_cache.pop(symbol, None)
        else:
            self.data_cache.clear()
        
        logger.debug("Cleared data cache for %s", symbol or "all symbols")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_symbols = len(self.data_cache)
        stale_symbols = sum(1 for data in self.data_cache.values() 
                          if data.is_stale(self.cache_duration))
        
        return {
            'total_symbols': total_symbols,
            'fresh_symbols': total_symbols - stale_symbols,
            'stale_symbols': stale_symbols
        }
