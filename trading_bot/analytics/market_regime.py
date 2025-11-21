"""Market regime detection and analysis for adaptive trading strategies."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

from trading_bot.analytics.market_data import MultiTimeframeData

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime types."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"


@dataclass
class RegimeAnalysis:
    """Market regime analysis result."""
    primary_regime: MarketRegime
    confidence: float  # 0.0 to 1.0
    regime_probabilities: Dict[MarketRegime, float]
    trend_strength: float  # -1.0 to 1.0 (negative = down, positive = up)
    volatility_percentile: float  # 0.0 to 1.0 (current vol vs historical)
    momentum_score: float  # -1.0 to 1.0
    mean_reversion_score: float  # 0.0 to 1.0 (higher = more mean reverting)
    
    def is_trending(self) -> bool:
        """Check if market is in trending regime."""
        return self.primary_regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]
    
    def is_ranging(self) -> bool:
        """Check if market is in ranging regime."""
        return self.primary_regime == MarketRegime.RANGING
    
    def is_high_volatility(self) -> bool:
        """Check if market is in high volatility regime."""
        return self.primary_regime == MarketRegime.HIGH_VOLATILITY
    
    def get_trading_bias(self) -> str:
        """Get recommended trading bias."""
        if self.primary_regime == MarketRegime.TRENDING_UP:
            return "bullish"
        elif self.primary_regime == MarketRegime.TRENDING_DOWN:
            return "bearish"
        elif self.primary_regime == MarketRegime.RANGING:
            return "neutral"
        elif self.primary_regime == MarketRegime.BREAKOUT:
            return "momentum"
        elif self.primary_regime == MarketRegime.REVERSAL:
            return "contrarian"
        else:
            return "cautious"


class MarketRegimeDetector:
    """Advanced market regime detection using multiple indicators and timeframes."""
    
    def __init__(
        self,
        lookback_periods: int = 100,
        volatility_window: int = 20,
        trend_window: int = 50
    ):
        """Initialize market regime detector.
        
        Args:
            lookback_periods: Number of periods to analyze
            volatility_window: Window for volatility calculation
            trend_window: Window for trend analysis
        """
        self.lookback_periods = lookback_periods
        self.volatility_window = volatility_window
        self.trend_window = trend_window
        
        # Regime detection thresholds
        self.trend_threshold = 0.3  # Minimum trend strength for trending regime
        self.volatility_high_percentile = 0.8  # 80th percentile for high vol
        self.volatility_low_percentile = 0.2   # 20th percentile for low vol
        self.ranging_threshold = 0.15  # Max trend strength for ranging
    
    def detect_regime(self, mtf_data: MultiTimeframeData) -> RegimeAnalysis:
        """Detect current market regime using multi-timeframe analysis.
        
        Args:
            mtf_data: Multi-timeframe market data
            
        Returns:
            RegimeAnalysis with detected regime and metrics
        """
        try:
            # Use 1h data as primary timeframe for regime detection
            primary_candles = mtf_data.get_timeframe('1h')
            if not primary_candles or len(primary_candles) < self.lookback_periods:
                # Fallback to 15m if 1h insufficient
                primary_candles = mtf_data.get_timeframe('15m')
                if not primary_candles or len(primary_candles) < self.lookback_periods:
                    logger.error("❌ INSUFFICIENT DATA for regime analysis - NO default")
                    return None
            
            # Extract price data
            closes = np.array([c.close for c in primary_candles])
            highs = np.array([c.high for c in primary_candles])
            lows = np.array([c.low for c in primary_candles])
            volumes = np.array([c.volume for c in primary_candles])
            
            # Calculate regime indicators
            trend_strength = self._calculate_trend_strength(closes)
            volatility_percentile = self._calculate_volatility_percentile(closes)
            momentum_score = self._calculate_momentum_score(closes, volumes)
            mean_reversion_score = self._calculate_mean_reversion_score(closes)
            
            # Multi-timeframe confirmation
            mtf_confirmation = self._get_multi_timeframe_confirmation(mtf_data)
            
            # Detect regime based on indicators
            regime_probabilities = self._calculate_regime_probabilities(
                trend_strength, volatility_percentile, momentum_score, 
                mean_reversion_score, mtf_confirmation
            )
            
            # Select primary regime (highest probability)
            primary_regime = max(regime_probabilities.keys(), 
                               key=lambda k: regime_probabilities[k])
            
            confidence = regime_probabilities[primary_regime]
            
            return RegimeAnalysis(
                primary_regime=primary_regime,
                confidence=confidence,
                regime_probabilities=regime_probabilities,
                trend_strength=trend_strength,
                volatility_percentile=volatility_percentile,
                momentum_score=momentum_score,
                mean_reversion_score=mean_reversion_score
            )
            
        except Exception as exc:
            logger.error("❌ MARKET REGIME DETECTION FAILED - NO default: %s", exc)
            return None
    
    def _calculate_trend_strength(self, closes: np.ndarray) -> float:
        """Calculate trend strength using multiple methods."""
        try:
            if len(closes) < self.trend_window:
                return 0.0
            
            # Method 1: Linear regression slope
            x = np.arange(len(closes))
            slope = np.polyfit(x[-self.trend_window:], closes[-self.trend_window:], 1)[0]
            normalized_slope = slope / np.mean(closes[-self.trend_window:])
            
            # Method 2: Moving average relationship
            short_ma = np.mean(closes[-10:])
            long_ma = np.mean(closes[-self.trend_window:])
            ma_trend = (short_ma - long_ma) / long_ma
            
            # Method 3: Higher highs / Lower lows
            recent_highs = closes[-20:]
            hh_ll_trend = 0.0
            if len(recent_highs) >= 10:
                first_half_max = np.max(recent_highs[:10])
                second_half_max = np.max(recent_highs[10:])
                hh_ll_trend = (second_half_max - first_half_max) / first_half_max
            
            # Combine methods
            trend_strength = (normalized_slope * 100 + ma_trend + hh_ll_trend) / 3
            
            return float(np.clip(trend_strength, -1.0, 1.0))
            
        except Exception as exc:
            logger.warning("Trend strength calculation failed: %s", exc)
            return 0.0
    
    def _calculate_volatility_percentile(self, closes: np.ndarray) -> float:
        """Calculate current volatility percentile vs historical."""
        try:
            if len(closes) < self.volatility_window * 2:
                logger.error("❌ INSUFFICIENT DATA for volatility percentile - NO fallback")
                return None
            
            # Calculate returns
            returns = np.diff(closes) / closes[:-1]
            
            # Current volatility (last volatility_window periods)
            current_vol = np.std(returns[-self.volatility_window:])
            
            # Historical volatility distribution
            historical_vols = []
            for i in range(self.volatility_window, len(returns)):
                vol = np.std(returns[i-self.volatility_window:i])
                historical_vols.append(vol)
            
            if not historical_vols:
                logger.error("❌ NO HISTORICAL VOLATILITY DATA - NO fallback")
                return None
            
            # Calculate percentile
            percentile = np.searchsorted(np.sort(historical_vols), current_vol) / len(historical_vols)
            
            return float(np.clip(percentile, 0.0, 1.0))
            
        except Exception as exc:
            logger.error("❌ VOLATILITY PERCENTILE CALCULATION FAILED - NO fallback: %s", exc)
            return None
    
    def _calculate_momentum_score(self, closes: np.ndarray, volumes: np.ndarray) -> float:
        """Calculate momentum score combining price and volume."""
        try:
            if len(closes) < 20:
                return 0.0
            
            # Price momentum (rate of change)
            price_momentum = (closes[-1] - closes[-10]) / closes[-10]
            
            # Volume-weighted momentum
            if len(volumes) == len(closes):
                recent_volume = np.mean(volumes[-10:])
                historical_volume = np.mean(volumes[-50:-10]) if len(volumes) >= 50 else recent_volume
                
                volume_factor = recent_volume / max(historical_volume, 1e-10)
                volume_factor = min(volume_factor, 3.0)  # Cap at 3x
                
                momentum_score = price_momentum * volume_factor
            else:
                momentum_score = price_momentum
            
            return float(np.clip(momentum_score, -1.0, 1.0))
            
        except Exception as exc:
            logger.warning("Momentum score calculation failed: %s", exc)
            return 0.0
    
    def _calculate_mean_reversion_score(self, closes: np.ndarray) -> float:
        """Calculate mean reversion tendency."""
        try:
            if len(closes) < 50:
                logger.error("❌ INSUFFICIENT DATA for mean reversion - NO fallback")
                return None
            
            # Calculate how often price reverts to mean
            sma = np.mean(closes[-50:])
            
            # Count reversions in recent periods
            reversions = 0
            total_periods = 0
            
            for i in range(-20, -1):  # Last 20 periods
                if len(closes) > abs(i):
                    current_price = closes[i]
                    next_price = closes[i + 1]
                    
                    # Check if price moved toward mean
                    current_distance = abs(current_price - sma)
                    next_distance = abs(next_price - sma)
                    
                    if next_distance < current_distance:
                        reversions += 1
                    total_periods += 1
            
            if total_periods == 0:
                logger.error("❌ NO REVERSION PERIODS FOUND - NO fallback")
                return None
            
            reversion_score = reversions / total_periods
            
            return float(reversion_score)
            
        except Exception as exc:
            logger.error("❌ MEAN REVERSION CALCULATION FAILED - NO fallback: %s", exc)
            return None
    
    def _get_multi_timeframe_confirmation(self, mtf_data: MultiTimeframeData) -> Dict[str, float]:
        """Get trend confirmation across multiple timeframes."""
        try:
            confirmations = {}
            
            for tf in ['5m', '15m', '1h']:
                candles = mtf_data.get_timeframe(tf)
                if candles and len(candles) >= 20:
                    closes = [c.close for c in candles]
                    trend = self._simple_trend_direction(closes)
                    confirmations[tf] = trend
                else:
                    confirmations[tf] = 0.0
            
            return confirmations
            
        except Exception as exc:
            logger.warning("Multi-timeframe confirmation failed: %s", exc)
            return {'5m': 0.0, '15m': 0.0, '1h': 0.0}
    
    def _simple_trend_direction(self, closes: List[float]) -> float:
        """Simple trend direction calculation."""
        try:
            if len(closes) < 10:
                return 0.0
            
            short_ma = np.mean(closes[-5:])
            long_ma = np.mean(closes[-20:])
            
            trend = (short_ma - long_ma) / long_ma
            
            return float(np.clip(trend, -1.0, 1.0))
            
        except Exception:
            return 0.0
    
    def _calculate_regime_probabilities(
        self,
        trend_strength: float,
        volatility_percentile: float,
        momentum_score: float,
        mean_reversion_score: float,
        mtf_confirmation: Dict[str, float]
    ) -> Dict[MarketRegime, float]:
        """Calculate probabilities for each market regime."""
        try:
            probabilities = {}
            
            # Average multi-timeframe trend
            avg_mtf_trend = np.mean(list(mtf_confirmation.values()))
            
            # Trending Up
            trending_up_score = 0.0
            if trend_strength > self.trend_threshold and momentum_score > 0:
                trending_up_score = (trend_strength + momentum_score + max(0, avg_mtf_trend)) / 3
            probabilities[MarketRegime.TRENDING_UP] = max(0.0, trending_up_score)
            
            # Trending Down
            trending_down_score = 0.0
            if trend_strength < -self.trend_threshold and momentum_score < 0:
                trending_down_score = (abs(trend_strength) + abs(momentum_score) + max(0, -avg_mtf_trend)) / 3
            probabilities[MarketRegime.TRENDING_DOWN] = max(0.0, trending_down_score)
            
            # Ranging
            ranging_score = 0.0
            if abs(trend_strength) < self.ranging_threshold:
                ranging_score = (1 - abs(trend_strength) / self.ranging_threshold) * mean_reversion_score
            probabilities[MarketRegime.RANGING] = max(0.0, ranging_score)
            
            # High Volatility
            high_vol_score = 0.0
            if volatility_percentile > self.volatility_high_percentile:
                high_vol_score = (volatility_percentile - self.volatility_high_percentile) / (1 - self.volatility_high_percentile)
            probabilities[MarketRegime.HIGH_VOLATILITY] = max(0.0, high_vol_score)
            
            # Low Volatility
            low_vol_score = 0.0
            if volatility_percentile < self.volatility_low_percentile:
                low_vol_score = (self.volatility_low_percentile - volatility_percentile) / self.volatility_low_percentile
            probabilities[MarketRegime.LOW_VOLATILITY] = max(0.0, low_vol_score)
            
            # Breakout (high momentum + increasing volatility)
            breakout_score = 0.0
            if abs(momentum_score) > 0.5 and volatility_percentile > 0.6:
                breakout_score = (abs(momentum_score) + volatility_percentile - 0.6) / 2
            probabilities[MarketRegime.BREAKOUT] = max(0.0, breakout_score)
            
            # Reversal (high mean reversion + conflicting timeframes)
            reversal_score = 0.0
            mtf_disagreement = np.std(list(mtf_confirmation.values()))
            if mean_reversion_score > 0.7 and mtf_disagreement > 0.3:
                reversal_score = (mean_reversion_score + mtf_disagreement) / 2
            probabilities[MarketRegime.REVERSAL] = max(0.0, reversal_score)
            
            # Normalize probabilities
            total_prob = sum(probabilities.values())
            if total_prob > 0:
                probabilities = {k: v / total_prob for k, v in probabilities.items()}
            else:
                # Default to ranging if no clear regime
                probabilities = {regime: 0.0 for regime in MarketRegime}
                probabilities[MarketRegime.RANGING] = 1.0
            
            return probabilities
            
        except Exception as exc:
            logger.error("Regime probability calculation failed: %s", exc)
            return {regime: 1.0 / len(MarketRegime) for regime in MarketRegime}
    
    def _default_regime_analysis(self) -> RegimeAnalysis:
        """Return default regime analysis when detection fails."""
        return RegimeAnalysis(
            primary_regime=MarketRegime.RANGING,
            confidence=0.5,
            regime_probabilities={regime: 1.0 / len(MarketRegime) for regime in MarketRegime},
            trend_strength=0.0,
            volatility_percentile=0.5,
            momentum_score=0.0,
            mean_reversion_score=0.5
        )


class SentimentAnalyzer:
    """Market sentiment analysis using price action and volume patterns."""
    
    def __init__(self):
        """Initialize sentiment analyzer."""
        pass
    
    def analyze_sentiment(self, mtf_data: MultiTimeframeData) -> Dict[str, float]:
        """Analyze market sentiment from price action.
        
        Args:
            mtf_data: Multi-timeframe market data
            
        Returns:
            Dictionary with sentiment scores
        """
        try:
            sentiment_scores = {}
            
            # Use 1h data for sentiment analysis
            candles = mtf_data.get_timeframe('1h')
            if not candles or len(candles) < 50:
                candles = mtf_data.get_timeframe('15m')
                if not candles or len(candles) < 50:
                    logger.error("❌ INSUFFICIENT DATA for sentiment analysis - NO default")
                    return None
            
            closes = np.array([c.close for c in candles])
            highs = np.array([c.high for c in candles])
            lows = np.array([c.low for c in candles])
            volumes = np.array([c.volume for c in candles])
            
            # Bull/Bear sentiment based on price action
            sentiment_scores['bullish'] = self._calculate_bullish_sentiment(closes, highs, lows, volumes)
            sentiment_scores['bearish'] = self._calculate_bearish_sentiment(closes, highs, lows, volumes)
            
            # Fear/Greed based on volatility and volume
            sentiment_scores['fear'] = self._calculate_fear_sentiment(closes, volumes)
            sentiment_scores['greed'] = self._calculate_greed_sentiment(closes, volumes)
            
            # Uncertainty based on price patterns
            sentiment_scores['uncertainty'] = self._calculate_uncertainty_sentiment(closes, volumes)
            
            # Normalize scores
            total = sum(sentiment_scores.values())
            if total > 0:
                sentiment_scores = {k: v / total for k, v in sentiment_scores.items()}
            
            return sentiment_scores
            
        except Exception as exc:
            logger.error("❌ SENTIMENT ANALYSIS FAILED - NO default: %s", exc)
            return None
    
    def _calculate_bullish_sentiment(
        self, 
        closes: np.ndarray, 
        highs: np.ndarray, 
        lows: np.ndarray, 
        volumes: np.ndarray
    ) -> float:
        """Calculate bullish sentiment score."""
        try:
            bullish_score = 0.0
            
            # Higher highs and higher lows
            if len(closes) >= 20:
                recent_high = np.max(highs[-10:])
                previous_high = np.max(highs[-20:-10])
                if recent_high > previous_high:
                    bullish_score += 0.3
                
                recent_low = np.min(lows[-10:])
                previous_low = np.min(lows[-20:-10])
                if recent_low > previous_low:
                    bullish_score += 0.3
            
            # Positive price momentum
            if len(closes) >= 10:
                momentum = (closes[-1] - closes[-10]) / closes[-10]
                bullish_score += max(0, momentum) * 2
            
            # Volume confirmation
            if len(volumes) >= 20:
                recent_volume = np.mean(volumes[-10:])
                historical_volume = np.mean(volumes[-20:-10])
                if recent_volume > historical_volume and closes[-1] > closes[-10]:
                    bullish_score += 0.2
            
            return min(1.0, bullish_score)
            
        except Exception:
            return 0.0
    
    def _calculate_bearish_sentiment(
        self, 
        closes: np.ndarray, 
        highs: np.ndarray, 
        lows: np.ndarray, 
        volumes: np.ndarray
    ) -> float:
        """Calculate bearish sentiment score."""
        try:
            bearish_score = 0.0
            
            # Lower highs and lower lows
            if len(closes) >= 20:
                recent_high = np.max(highs[-10:])
                previous_high = np.max(highs[-20:-10])
                if recent_high < previous_high:
                    bearish_score += 0.3
                
                recent_low = np.min(lows[-10:])
                previous_low = np.min(lows[-20:-10])
                if recent_low < previous_low:
                    bearish_score += 0.3
            
            # Negative price momentum
            if len(closes) >= 10:
                momentum = (closes[-1] - closes[-10]) / closes[-10]
                bearish_score += max(0, -momentum) * 2
            
            # Volume confirmation
            if len(volumes) >= 20:
                recent_volume = np.mean(volumes[-10:])
                historical_volume = np.mean(volumes[-20:-10])
                if recent_volume > historical_volume and closes[-1] < closes[-10]:
                    bearish_score += 0.2
            
            return min(1.0, bearish_score)
            
        except Exception:
            return 0.0
    
    def _calculate_fear_sentiment(self, closes: np.ndarray, volumes: np.ndarray) -> float:
        """Calculate fear sentiment based on volatility spikes."""
        try:
            if len(closes) < 20:
                return 0.0
            
            # High volatility indicates fear
            returns = np.diff(closes) / closes[:-1]
            current_vol = np.std(returns[-10:])
            historical_vol = np.std(returns[-50:-10]) if len(returns) >= 50 else current_vol
            
            vol_ratio = current_vol / max(historical_vol, 1e-10)
            fear_score = min(1.0, max(0.0, (vol_ratio - 1.0) / 2.0))
            
            # Volume spikes during declines
            if len(volumes) >= 20:
                recent_volume = np.mean(volumes[-5:])
                avg_volume = np.mean(volumes[-20:-5])
                volume_spike = recent_volume / max(avg_volume, 1e-10)
                
                if volume_spike > 1.5 and closes[-1] < closes[-5]:
                    fear_score += 0.3
            
            return min(1.0, fear_score)
            
        except Exception:
            return 0.0
    
    def _calculate_greed_sentiment(self, closes: np.ndarray, volumes: np.ndarray) -> float:
        """Calculate greed sentiment based on momentum and volume."""
        try:
            if len(closes) < 20:
                return 0.0
            
            greed_score = 0.0
            
            # Strong upward momentum
            if len(closes) >= 10:
                momentum = (closes[-1] - closes[-10]) / closes[-10]
                greed_score += max(0, momentum) * 3
            
            # Consecutive higher closes
            consecutive_up = 0
            for i in range(-5, 0):
                if len(closes) > abs(i) and closes[i] > closes[i-1]:
                    consecutive_up += 1
            
            greed_score += consecutive_up / 5 * 0.4
            
            # Volume expansion on rallies
            if len(volumes) >= 10:
                recent_volume = np.mean(volumes[-5:])
                avg_volume = np.mean(volumes[-20:-5])
                if recent_volume > avg_volume * 1.2 and closes[-1] > closes[-5]:
                    greed_score += 0.3
            
            return min(1.0, greed_score)
            
        except Exception:
            return 0.0
    
    def _calculate_uncertainty_sentiment(self, closes: np.ndarray, volumes: np.ndarray) -> float:
        """Calculate uncertainty sentiment based on choppy price action."""
        try:
            if len(closes) < 20:
                logger.error("❌ INSUFFICIENT DATA for uncertainty sentiment - NO fallback")
                return None
            
            uncertainty_score = 0.0
            
            # Choppy price action (many direction changes)
            direction_changes = 0
            for i in range(-10, -1):
                if len(closes) > abs(i):
                    if (closes[i] > closes[i-1]) != (closes[i+1] > closes[i]):
                        direction_changes += 1
            
            uncertainty_score += direction_changes / 9 * 0.5
            
            # Low momentum (sideways movement)
            momentum = abs((closes[-1] - closes[-20]) / closes[-20])
            if momentum < 0.02:  # Less than 2% move in 20 periods
                uncertainty_score += 0.3
            
            # Declining volume (lack of conviction)
            if len(volumes) >= 20:
                recent_volume = np.mean(volumes[-10:])
                historical_volume = np.mean(volumes[-20:-10])
                if recent_volume < historical_volume * 0.8:
                    uncertainty_score += 0.2
            
            return min(1.0, uncertainty_score)
            
        except Exception as exc:
            logger.error("❌ UNCERTAINTY SENTIMENT CALCULATION FAILED - NO fallback: %s", exc)
            return None
    
    def _default_sentiment(self) -> None:
        """NO DEFAULT SENTIMENT - Return None when analysis fails."""
        logger.error("❌ SENTIMENT ANALYSIS FAILED - NO fake default sentiment")
        return None
