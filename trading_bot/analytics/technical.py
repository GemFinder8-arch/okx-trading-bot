"""Technical analysis indicators for dynamic TP/SL calculation."""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from trading_bot.analytics.market_data import OHLCV, MultiTimeframeData

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """Technical analysis for calculating dynamic TP/SL levels."""

    def __init__(self, atr_period: int = 14, fib_lookback: int = 50):
        """Initialize technical analyzer.
        
        Args:
            atr_period: Period for ATR calculation
            fib_lookback: Number of periods to look back for Fibonacci levels
        """
        self.atr_period = atr_period
        self.fib_lookback = fib_lookback
        
        # Fibonacci retracement levels
        self.fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]

    def calculate_atr(self, highs: list[float], lows: list[float], closes: list[float]) -> Optional[float]:
        """Calculate Average True Range (ATR).
        
        Args:
            highs: List of high prices
            lows: List of low prices  
            closes: List of close prices
            
        Returns:
            ATR value or None if insufficient data
        """
        # Check data availability and log details
        if not highs or not lows or not closes:
            logger.debug("ATR calculation failed: Empty data arrays")
            return None
            
        min_length = min(len(highs), len(lows), len(closes))
        if min_length < self.atr_period + 1:
            logger.debug("ATR calculation failed: Insufficient data (need %d, have %d)", 
                        self.atr_period + 1, min_length)
            return None
            
        try:
            # Ensure all arrays have the same length
            length = min_length
            highs_arr = np.array(highs[-length:])
            lows_arr = np.array(lows[-length:])
            closes_arr = np.array(closes[-length:])
            
            # Validate data quality
            if np.any(np.isnan(highs_arr)) or np.any(np.isnan(lows_arr)) or np.any(np.isnan(closes_arr)):
                logger.debug("ATR calculation failed: NaN values in data")
                return None
            
            if np.any(highs_arr <= 0) or np.any(lows_arr <= 0) or np.any(closes_arr <= 0):
                logger.debug("ATR calculation failed: Invalid price values (<=0)")
                return None
            
            # True Range calculation
            tr1 = highs_arr[1:] - lows_arr[1:]  # High - Low
            tr2 = np.abs(highs_arr[1:] - closes_arr[:-1])  # |High - Previous Close|
            tr3 = np.abs(lows_arr[1:] - closes_arr[:-1])   # |Low - Previous Close|
            
            true_range = np.maximum(tr1, np.maximum(tr2, tr3))
            
            # Use only the most recent ATR period for calculation
            if len(true_range) >= self.atr_period:
                atr = np.mean(true_range[-self.atr_period:])
            else:
                atr = np.mean(true_range)
            
            if np.isnan(atr) or atr <= 0:
                logger.debug("ATR calculation failed: Invalid result (NaN or <=0)")
                return None
            
            logger.debug("ATR calculated successfully: %.6f", atr)
            return float(atr)
            
        except Exception as exc:
            logger.warning("ATR calculation failed: %s", exc)
            return None

    def calculate_fibonacci_levels(
        self, 
        highs: list[float], 
        lows: list[float], 
        trend_direction: str = "up"
    ) -> dict[str, float]:
        """Calculate Fibonacci retracement levels.
        
        Args:
            highs: List of high prices
            lows: List of low prices
            trend_direction: "up" for uptrend, "down" for downtrend
            
        Returns:
            Dictionary of Fibonacci levels
        """
        if len(highs) < self.fib_lookback or len(lows) < self.fib_lookback:
            return {}
            
        try:
            recent_highs = highs[-self.fib_lookback:]
            recent_lows = lows[-self.fib_lookback:]
            
            swing_high = max(recent_highs)
            swing_low = min(recent_lows)
            range_size = swing_high - swing_low
            
            if range_size <= 0:
                return {}
            
            fib_levels = {}
            
            if trend_direction.lower() == "up":
                # For uptrend: retracement from high to low
                for level in self.fib_levels:
                    fib_levels[f"fib_{level}"] = swing_high - (range_size * level)
            else:
                # For downtrend: extension from low to high
                for level in self.fib_levels:
                    fib_levels[f"fib_{level}"] = swing_low + (range_size * level)
                    
            return fib_levels
        except Exception as exc:
            logger.warning("Fibonacci calculation failed: %s", exc)
            return {}

    def calculate_dynamic_levels_mtf(
        self,
        current_price: float,
        mtf_data: MultiTimeframeData,
        decision: str,
        use_fibonacci: bool = True
    ) -> tuple[float, float]:
        """Calculate dynamic TP/SL levels using multi-timeframe analysis.
        
        Args:
            current_price: Current market price
            mtf_data: Multi-timeframe market data
            decision: "BUY" or "SELL"
            use_fibonacci: Whether to use Fibonacci levels
            
        Returns:
            Tuple of (stop_loss, take_profit)
        """
        try:
            # Get volatility-adjusted multipliers
            volatility = self._calculate_volatility_mtf(mtf_data)
            atr_multiplier_sl, atr_multiplier_tp = self._adaptive_atr_multipliers(volatility)
            
            # Use 15m timeframe for primary analysis with reduced requirements
            primary_candles = mtf_data.get_timeframe('15m')
            if not primary_candles or len(primary_candles) < 10:  # Reduced from 20 to 10
                # Fallback to 5m
                primary_candles = mtf_data.get_timeframe('5m')
                if not primary_candles or len(primary_candles) < 10:  # Reduced from 20 to 10
                    # Final fallback to 1m
                    primary_candles = mtf_data.get_timeframe('1m')
                    if not primary_candles or len(primary_candles) < 5:  # Reduced from 20 to 5
                        logger.error("❌ INSUFFICIENT DATA for technical analysis - NO fallback")
                        return None, None
            
            # Extract price arrays
            highs = [c.high for c in primary_candles]
            lows = [c.low for c in primary_candles]
            closes = [c.close for c in primary_candles]
            
            # Multi-timeframe trend confirmation
            trend_confluence = self._analyze_trend_confluence(mtf_data)
            
            # Calculate base levels using original method
            stop_loss, take_profit = self.calculate_dynamic_levels(
                current_price=current_price,
                highs=highs,
                lows=lows,
                closes=closes,
                decision=decision,
                atr_multiplier_sl=atr_multiplier_sl,
                atr_multiplier_tp=atr_multiplier_tp,
                use_fibonacci=use_fibonacci
            )
            
            # Adjust based on trend confluence
            if trend_confluence > 0.7:  # Strong trend agreement
                if decision == "BUY":
                    take_profit *= 1.2  # Let winners run in strong uptrend
                else:
                    take_profit *= 1.2  # Let winners run in strong downtrend
            elif trend_confluence < 0.3:  # Weak/conflicting trends
                if decision == "BUY":
                    stop_loss = current_price * 0.98  # Tighter stops in uncertain conditions
                    take_profit = current_price * 1.02
                else:
                    stop_loss = current_price * 1.02
                    take_profit = current_price * 0.98
            
            logger.info(
                "Multi-timeframe levels for %s at %.6f: SL=%.6f, TP=%.6f (trend_confluence=%.2f, vol=%.4f)",
                decision, current_price, stop_loss, take_profit, trend_confluence, volatility or 0
            )
            
            return stop_loss, take_profit
            
        except Exception as exc:
            logger.error("❌ MULTI-TIMEFRAME ANALYSIS FAILED - NO fallback: %s", exc)
            return None, None

    def calculate_dynamic_levels(
        self,
        current_price: float,
        highs: list[float],
        lows: list[float], 
        closes: list[float],
        decision: str,
        atr_multiplier_sl: float = 2.0,
        atr_multiplier_tp: float = 3.0,
        use_fibonacci: bool = True
    ) -> tuple[float, float]:
        """Calculate dynamic TP/SL levels using ATR and Fibonacci.
        
        Args:
            current_price: Current market price
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            decision: "BUY" or "SELL"
            atr_multiplier_sl: ATR multiplier for stop loss
            atr_multiplier_tp: ATR multiplier for take profit
            use_fibonacci: Whether to use Fibonacci levels
            
        Returns:
            Tuple of (stop_loss, take_profit)
        """
        # Calculate ATR
        atr = self.calculate_atr(highs, lows, closes)
        if not atr:
            # Fallback to percentage-based if ATR fails
            logger.warning("ATR calculation failed, using percentage fallback")
            if decision == "BUY":
                return current_price * 0.9, current_price * 1.3  # 10% SL, 30% TP
            else:
                return current_price * 1.1, current_price * 0.7  # 10% SL, 30% TP
        
        # Base ATR levels
        if decision == "BUY":
            atr_stop_loss = current_price - (atr * atr_multiplier_sl)
            atr_take_profit = current_price + (atr * atr_multiplier_tp)
            trend_direction = "up"
        else:
            atr_stop_loss = current_price + (atr * atr_multiplier_sl)
            atr_take_profit = current_price - (atr * atr_multiplier_tp)
            trend_direction = "down"
        
        # Use Fibonacci levels if enabled
        if use_fibonacci:
            fib_levels = self.calculate_fibonacci_levels(highs, lows, trend_direction)
            
            if fib_levels:
                if decision == "BUY":
                    # For BUY: SL near support (Fib 0.618), TP near resistance (Fib 1.618)
                    fib_sl = fib_levels.get("fib_0.618", atr_stop_loss)
                    fib_tp = fib_levels.get("fib_1.618", atr_take_profit)
                    
                    # Use the more conservative (closer to price) of ATR vs Fib for SL
                    # Use the more aggressive (further from price) of ATR vs Fib for TP
                    stop_loss = max(atr_stop_loss, fib_sl) if fib_sl < current_price else atr_stop_loss
                    take_profit = max(atr_take_profit, fib_tp)
                else:
                    # For SELL: SL near resistance (Fib 0.618), TP near support (Fib 1.618)
                    fib_sl = fib_levels.get("fib_0.618", atr_stop_loss)
                    fib_tp = fib_levels.get("fib_1.618", atr_take_profit)
                    
                    stop_loss = min(atr_stop_loss, fib_sl) if fib_sl > current_price else atr_stop_loss
                    take_profit = min(atr_take_profit, fib_tp)
            else:
                stop_loss = atr_stop_loss
                take_profit = atr_take_profit
        else:
            stop_loss = atr_stop_loss
            take_profit = atr_take_profit
        
        # Ensure levels are valid
        if decision == "BUY":
            stop_loss = max(stop_loss, current_price * 0.5)  # Don't go below 50% of price
            take_profit = max(take_profit, current_price * 1.01)  # At least 1% profit
        else:
            stop_loss = min(stop_loss, current_price * 2.0)  # Don't go above 200% of price
            take_profit = min(take_profit, current_price * 0.99)  # At least 1% profit
        
        logger.info(
            "Dynamic levels for %s at %.6f: SL=%.6f (ATR=%.6f), TP=%.6f (ATR=%.6f)",
            decision, current_price, stop_loss, atr, take_profit, atr
        )
        
        return stop_loss, take_profit

    def detect_trend(self, closes: list[float], period: int = 20) -> str:
        """Detect trend direction using simple moving average and slope analysis.
        
        Args:
            closes: List of close prices
            period: Period for trend detection
            
        Returns:
            "up", "down", or "sideways"
        """
        if not closes or len(closes) < 3:
            return "sideways"
            
        # Adjust period if we don't have enough data
        effective_period = min(period, len(closes))
        if effective_period < 3:
            return "sideways"
            
        try:
            recent_closes = closes[-effective_period:]
            current_price = closes[-1]
            
            # Calculate simple moving average
            sma = sum(recent_closes) / len(recent_closes)
            
            # Calculate slope of recent prices for trend strength
            if len(recent_closes) >= 5:
                x = np.arange(len(recent_closes))
                slope = np.polyfit(x, recent_closes, 1)[0]
                price_range = max(recent_closes) - min(recent_closes)
                relative_slope = slope / (price_range + 1e-8)  # Avoid division by zero
            else:
                relative_slope = 0
            
            # Enhanced trend detection combining SMA and slope
            sma_threshold = 0.015  # 1.5% threshold
            slope_threshold = 0.1
            
            price_vs_sma = (current_price - sma) / sma
            
            if price_vs_sma > sma_threshold and relative_slope > slope_threshold:
                return "up"
            elif price_vs_sma < -sma_threshold and relative_slope < -slope_threshold:
                return "down"
            elif abs(price_vs_sma) > sma_threshold:
                # Price significantly above/below SMA but slope is weak
                return "up" if price_vs_sma > 0 else "down"
            else:
                return "sideways"
                
        except Exception as exc:
            logger.debug("Trend detection failed: %s", exc)
            return "sideways"
    
    def _calculate_volatility_mtf(self, mtf_data: MultiTimeframeData) -> Optional[float]:
        """Calculate volatility using multi-timeframe data."""
        try:
            # Use 1h data for volatility calculation
            candles = mtf_data.get_timeframe('1h')
            if not candles or len(candles) < 20:
                # Fallback to 15m
                candles = mtf_data.get_timeframe('15m')
                if not candles or len(candles) < 20:
                    return None
            
            closes = [c.close for c in candles[-20:]]
            returns = np.diff(closes) / closes[:-1]
            volatility = np.std(returns) * np.sqrt(365 * 24)  # Annualized
            
            return float(volatility)
        except Exception:
            return None
    
    def _adaptive_atr_multipliers(self, volatility: Optional[float]) -> Tuple[float, float]:
        """Calculate adaptive ATR multipliers based on volatility."""
        if not volatility:
            return 2.0, 3.0  # Default values
        
        # Adjust multipliers based on volatility
        if volatility > 0.5:  # Very high volatility
            return 1.5, 4.0  # Tighter stops, wider targets
        elif volatility > 0.3:  # High volatility
            return 1.8, 3.5
        else:
            return 2.0, 3.0  # Normal volatility

    def detect_trend(self, closes: list[float], period: int = 20) -> str:
        """Detect trend direction using simple moving average and slope analysis.
        
        Args:
            closes: List of close prices
            period: Period for trend detection
            
        Returns:
            "up", "down", or "sideways"
        """
        if not closes or len(closes) < 3:
            return "sideways"
            
        # Adjust period if we don't have enough data
        effective_period = min(period, len(closes))
        if effective_period < 3:
            return "sideways"
            
        try:
            recent_closes = closes[-effective_period:]
            current_price = closes[-1]
            
            # Calculate simple moving average
            sma = sum(recent_closes) / len(recent_closes)
            
            # Calculate slope of recent prices for trend strength
            if len(recent_closes) >= 5:
                x = np.arange(len(recent_closes))
                slope = np.polyfit(x, recent_closes, 1)[0]
                price_range = max(recent_closes) - min(recent_closes)
                relative_slope = slope / (price_range + 1e-8)  # Avoid division by zero
            else:
                relative_slope = 0
            
            # Enhanced trend detection combining SMA and slope
            sma_threshold = 0.015  # 1.5% threshold
            slope_threshold = 0.1
            
            price_vs_sma = (current_price - sma) / sma
            
            if price_vs_sma > sma_threshold and relative_slope > slope_threshold:
                return "up"
            elif price_vs_sma < -sma_threshold and relative_slope < -slope_threshold:
                return "down"
            elif abs(price_vs_sma) > sma_threshold:
                # Price significantly above/below SMA but slope is weak
                return "up" if price_vs_sma > 0 else "down"
            else:
                return "sideways"
                
        except Exception as exc:
            logger.debug("Trend detection failed: %s", exc)
            return "sideways"

    def calculate_trend_confluence(self, mtf_data: MultiTimeframeData) -> float:
        """Calculate simplified trend confluence across timeframes.
        
        Args:
            mtf_data: Multi-timeframe candle data
            
        Returns:
            Confluence score (0.0 to 1.0)
        """
        try:
            timeframes = ['1m', '5m', '15m', '1h']
            trend_scores = []
            available_timeframes = []
            
            for tf in timeframes:
                candles = mtf_data.get_timeframe(tf)
                if not candles:
                    logger.debug("No candles available for timeframe %s", tf)
                    continue
                    
                if len(candles) < 5:
                    logger.debug("Insufficient candles for timeframe %s: %d (need 5)", tf, len(candles))
                    continue
                
                closes = [c.close for c in candles]
                trend = self.detect_trend(closes, period=min(20, len(closes) // 2))
                available_timeframes.append(tf)
                
                # Convert trend to numeric score
                if trend == "up":
                    trend_scores.append(1.0)
                elif trend == "down":
                    trend_scores.append(-1.0)
                else:
                    trend_scores.append(0.0)
                
                logger.debug("Timeframe %s: trend=%s, score=%.1f", tf, trend, trend_scores[-1])
            
            if not trend_scores:
                logger.debug("No trend data available, using single timeframe fallback")
                # Fallback: use primary timeframe data if available
                primary_candles = mtf_data.get_timeframe('5m') or mtf_data.get_timeframe('15m') or mtf_data.get_timeframe('1h')
                if primary_candles and len(primary_candles) >= 10:
                    closes = [c.close for c in primary_candles]
                    trend = self.detect_trend(closes, period=min(10, len(closes) // 2))
                    if trend == "up":
                        return 0.7  # Strong uptrend
                    elif trend == "down":
                        return 0.3  # Strong downtrend
                    else:
                        return 0.5  # Sideways (legitimate calculation)
                logger.error("❌ NO TREND DATA for confluence - NO fallback")
                return None
            
            # Calculate confluence as normalized average
            avg_score = sum(trend_scores) / len(trend_scores)
            confluence = (avg_score + 1.0) / 2.0  # Normalize from [-1,1] to [0,1]
            
            logger.debug("Calculated trend confluence: %.3f from %d timeframes", confluence, len(trend_scores))
            return confluence
            
        except Exception as exc:
            logger.error("❌ TREND CONFLUENCE ANALYSIS FAILED - NO fallback: %s", exc)
            return None

    def _adaptive_atr_multipliers(self, volatility: Optional[float]) -> Tuple[float, float]:
        """Calculate adaptive ATR multipliers based on volatility."""
        if not volatility:
            return 2.0, 3.0  # Default values
        
        # Adjust multipliers based on volatility
        if volatility > 0.5:  # Very high volatility
            return 1.5, 4.0  # Tighter stops, wider targets
        elif volatility > 0.3:  # High volatility
            return 1.8, 3.5
        else:
            return 2.0, 3.0  # Normal volatility
    
    def calculate_macd(self, closes: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate MACD indicator."""
        try:
            if len(closes) < slow + signal:
                return np.array([]), np.array([]), np.array([])
            
            ema_fast = self._ema(closes, fast)
            ema_slow = self._ema(closes, slow)
            macd_line = ema_fast - ema_slow
            signal_line = self._ema(macd_line, signal)
            histogram = macd_line - signal_line
            
            return macd_line, signal_line, histogram
        except Exception:
            return np.array([]), np.array([]), np.array([])
    
    def calculate_bollinger_bands(self, closes: np.ndarray, period: int = 20, std_dev: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate Bollinger Bands."""
        try:
            if len(closes) < period:
                return np.array([]), np.array([]), np.array([])
            
            # Simple moving average
            sma = np.convolve(closes, np.ones(period)/period, mode='valid')
            
            # Standard deviation
            std = np.array([np.std(closes[i:i+period]) for i in range(len(closes) - period + 1)])
            
            # Pad arrays to match closes length
            sma_padded = np.full(len(closes), np.nan)
            sma_padded[period-1:] = sma
            
            std_padded = np.full(len(closes), np.nan)
            std_padded[period-1:] = std
            
            upper_band = sma_padded + (std_padded * std_dev)
            lower_band = sma_padded - (std_padded * std_dev)
            
            return upper_band, sma_padded, lower_band
        except Exception:
            return np.array([]), np.array([]), np.array([])
    
    def calculate_stochastic(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, k_period: int = 14, d_period: int = 3) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate Stochastic Oscillator."""
        try:
            if len(closes) < k_period:
                return np.array([]), np.array([])
            
            k_values = []
            for i in range(k_period - 1, len(closes)):
                period_high = np.max(highs[i - k_period + 1:i + 1])
                period_low = np.min(lows[i - k_period + 1:i + 1])
                
                if period_high == period_low:
                    k_values.append(50.0)  # Avoid division by zero
                else:
                    k = ((closes[i] - period_low) / (period_high - period_low)) * 100
                    k_values.append(k)
            
            k_array = np.array(k_values)
            d_array = np.convolve(k_array, np.ones(d_period)/d_period, mode='valid')
            
            # Pad arrays
            k_padded = np.full(len(closes), np.nan)
            k_padded[k_period-1:] = k_array
            
            d_padded = np.full(len(closes), np.nan)
            d_padded[k_period + d_period - 2:] = d_array
            
            return k_padded, d_padded
        except Exception:
            return np.array([]), np.array([])

    def calculate_williams_r(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate Williams %R oscillator."""
        try:
            if len(closes) < period:
                return np.full(len(closes), np.nan)
            
            williams_r = []
            for i in range(period - 1, len(closes)):
                period_high = np.max(highs[i - period + 1:i + 1])
                period_low = np.min(lows[i - period + 1:i + 1])
                
                if period_high == period_low:
                    williams_r.append(-50.0)
                else:
                    wr = ((period_high - closes[i]) / (period_high - period_low)) * -100
                    williams_r.append(wr)
            
            # Pad array
            result = np.full(len(closes), np.nan)
            result[period-1:] = williams_r
            return result
        except Exception:
            return np.full(len(closes), np.nan)
    
    def calculate_fibonacci_levels(self, highs: np.ndarray, lows: np.ndarray, lookback: int = 50) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels."""
        try:
            if len(highs) < lookback or len(lows) < lookback:
                return {}
            
            recent_high = np.max(highs[-lookback:])
            recent_low = np.min(lows[-lookback:])
            diff = recent_high - recent_low
            
            return {
                "0.0": recent_high,
                "23.6": recent_high - (diff * 0.236),
                "38.2": recent_high - (diff * 0.382),
                "50.0": recent_high - (diff * 0.5),
                "61.8": recent_high - (diff * 0.618),
                "78.6": recent_high - (diff * 0.786),
                "100.0": recent_low
            }
        except Exception:
            return {}
    
    def calculate_enhanced_confluence_score(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray, volumes: np.ndarray) -> Dict[str, float]:
        """Calculate comprehensive multi-indicator confluence score."""
        try:
            if len(closes) < 50:  # Need sufficient data
                return {"confluence": 0.5, "strength": 0.5, "momentum": 0.5}
            
            scores = {}
            
            # 1. TREND INDICATORS
            ema_8 = self._ema(closes, 8)
            ema_21 = self._ema(closes, 21)
            ema_50 = self._ema(closes, 50)
            
            # EMA alignment score
            if len(ema_8) > 0 and len(ema_21) > 0 and len(ema_50) > 0:
                if ema_8[-1] > ema_21[-1] > ema_50[-1]:
                    scores['ema_trend'] = 1.0  # Strong uptrend
                elif ema_8[-1] < ema_21[-1] < ema_50[-1]:
                    scores['ema_trend'] = 0.0  # Strong downtrend
                else:
                    scores['ema_trend'] = 0.5  # Mixed/sideways
            else:
                scores['ema_trend'] = 0.5
            
            # 2. MOMENTUM INDICATORS
            rsi = self._rsi(closes, 14)
            macd_line, signal_line, histogram = self.calculate_macd(closes)
            stoch_k, stoch_d = self.calculate_stochastic(highs, lows, closes)
            williams_r = self.calculate_williams_r(highs, lows, closes)
            
            # RSI momentum score
            if len(rsi) > 0:
                if 40 <= rsi[-1] <= 60:
                    scores['rsi_momentum'] = 0.8  # Healthy momentum
                elif 30 <= rsi[-1] <= 70:
                    scores['rsi_momentum'] = 0.6  # Acceptable
                else:
                    scores['rsi_momentum'] = 0.3  # Extreme levels
            else:
                scores['rsi_momentum'] = 0.5
            
            # MACD momentum score
            if len(macd_line) > 0 and len(signal_line) > 0:
                if macd_line[-1] > signal_line[-1] and macd_line[-1] > 0:
                    scores['macd_momentum'] = 0.8  # Bullish momentum
                elif macd_line[-1] < signal_line[-1] and macd_line[-1] < 0:
                    scores['macd_momentum'] = 0.2  # Bearish momentum
                else:
                    scores['macd_momentum'] = 0.5  # Mixed
            else:
                scores['macd_momentum'] = 0.5
            
            # Stochastic momentum score
            if len(stoch_k) > 0:
                if 20 <= stoch_k[-1] <= 80:
                    scores['stoch_momentum'] = 0.7  # Healthy range
                else:
                    scores['stoch_momentum'] = 0.4  # Extreme levels
            else:
                scores['stoch_momentum'] = 0.5
            
            # 3. VOLATILITY INDICATORS
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(closes)
            
            # Bollinger Band position score
            if len(bb_upper) > 0 and len(bb_lower) > 0 and not np.isnan(bb_upper[-1]):
                bb_position = (closes[-1] - bb_lower[-1]) / (bb_upper[-1] - bb_lower[-1])
                if 0.2 <= bb_position <= 0.8:
                    scores['bb_position'] = 0.8  # Good position
                else:
                    scores['bb_position'] = 0.4  # Extreme position
            else:
                scores['bb_position'] = 0.5
            
            # 4. VOLUME CONFIRMATION
            if len(volumes) >= 20:
                recent_volume = np.mean(volumes[-5:])
                avg_volume = np.mean(volumes[-20:])
                volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
                
                if volume_ratio > 1.2:
                    scores['volume_confirm'] = 0.8  # Strong volume
                elif volume_ratio > 0.8:
                    scores['volume_confirm'] = 0.6  # Adequate volume
                else:
                    scores['volume_confirm'] = 0.4  # Weak volume
            else:
                scores['volume_confirm'] = 0.5
            
            # CALCULATE WEIGHTED CONFLUENCE
            weights = {
                'ema_trend': 0.25,
                'rsi_momentum': 0.15,
                'macd_momentum': 0.20,
                'stoch_momentum': 0.15,
                'bb_position': 0.15,
                'volume_confirm': 0.10
            }
            
            confluence = sum(scores.get(key, 0.5) * weight for key, weight in weights.items())
            
            # Calculate overall strength and momentum
            trend_strength = (scores.get('ema_trend', 0.5) + scores.get('bb_position', 0.5)) / 2
            momentum_strength = (scores.get('rsi_momentum', 0.5) + scores.get('macd_momentum', 0.5) + scores.get('stoch_momentum', 0.5)) / 3
            
            return {
                "confluence": confluence,
                "strength": trend_strength,
                "momentum": momentum_strength,
                "individual_scores": scores
            }
            
        except Exception as exc:
            logger.warning("Enhanced confluence calculation failed: %s", exc)
            return {"confluence": 0.5, "strength": 0.5, "momentum": 0.5}

    def _analyze_trend_confluence(self, mtf_data: MultiTimeframeData) -> float:
        """Analyze trend confluence across multiple timeframes."""
        return self.calculate_trend_confluence(mtf_data)
    
    # REMOVED: _fallback_levels - NO FALLBACK DATA ALLOWED
