"""Enhanced signal analysis to reduce stop-loss triggers and improve trend confluence."""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MarketCondition:
    """Market condition analysis result."""
    trend_strength: float  # 0.0 to 1.0
    volatility_regime: str  # "low", "medium", "high"
    momentum_quality: float  # 0.0 to 1.0
    support_resistance_level: float
    risk_level: str  # "low", "medium", "high"


class EnhancedSignalAnalyzer:
    """Advanced signal analysis to prevent premature stop-loss triggers."""
    
    def __init__(self):
        """Initialize enhanced signal analyzer."""
        self.min_trend_strength = 0.4
        self.volatility_thresholds = {"low": 0.03, "medium": 0.06, "high": 0.12}
        
    def analyze_market_condition(self, candles: List, current_price: float) -> MarketCondition:
        """Analyze current market conditions for better entry/exit decisions."""
        try:
            if not candles or len(candles) < 20:
                return self._default_condition(current_price)
            
            closes = np.array([c.close for c in candles])
            highs = np.array([c.high for c in candles])
            lows = np.array([c.low for c in candles])
            volumes = np.array([c.volume for c in candles])
            
            # 1. TREND STRENGTH ANALYSIS
            trend_strength = self._calculate_trend_strength(closes)
            
            # 2. VOLATILITY REGIME
            volatility_regime = self._determine_volatility_regime(highs, lows, closes)
            
            # 3. MOMENTUM QUALITY
            momentum_quality = self._assess_momentum_quality(closes, volumes)
            
            # 4. SUPPORT/RESISTANCE LEVELS
            support_resistance = self._find_key_levels(highs, lows, current_price)
            
            # 5. OVERALL RISK ASSESSMENT
            risk_level = self._assess_risk_level(trend_strength, volatility_regime, momentum_quality)
            
            return MarketCondition(
                trend_strength=trend_strength,
                volatility_regime=volatility_regime,
                momentum_quality=momentum_quality,
                support_resistance_level=support_resistance,
                risk_level=risk_level
            )
            
        except Exception as exc:
            logger.warning("Market condition analysis failed: %s", exc)
            return self._default_condition(current_price)
    
    def _calculate_trend_strength(self, closes: np.ndarray) -> float:
        """Calculate trend strength using multiple indicators."""
        try:
            # EMA-based trend strength
            ema_8 = self._ema(closes, 8)
            ema_21 = self._ema(closes, 21)
            ema_50 = self._ema(closes, 50)
            
            # Trend alignment score
            current_price = closes[-1]
            alignment_score = 0
            
            if current_price > ema_8[-1] > ema_21[-1] > ema_50[-1]:
                alignment_score = 1.0  # Perfect uptrend alignment
            elif current_price < ema_8[-1] < ema_21[-1] < ema_50[-1]:
                alignment_score = 1.0  # Perfect downtrend alignment
            elif current_price > ema_8[-1] > ema_21[-1]:
                alignment_score = 0.7  # Strong short-term trend
            elif current_price < ema_8[-1] < ema_21[-1]:
                alignment_score = 0.7  # Strong short-term trend
            else:
                alignment_score = 0.3  # Weak or sideways trend
            
            # Trend momentum (slope of EMA)
            ema_slope = (ema_21[-1] - ema_21[-5]) / ema_21[-5] if len(ema_21) >= 5 else 0
            momentum_score = min(abs(ema_slope) * 20, 1.0)  # Normalize
            
            # Combined trend strength
            trend_strength = (alignment_score * 0.7) + (momentum_score * 0.3)
            return max(0.0, min(1.0, trend_strength))
            
        except Exception as exc:
            logger.error("❌ TREND STRENGTH CALCULATION FAILED - NO fallback: %s", exc)
            return None
    
    def _determine_volatility_regime(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> str:
        """Determine current volatility regime."""
        try:
            # Calculate ATR-based volatility
            tr = np.maximum(highs[1:] - lows[1:], 
                           np.maximum(np.abs(highs[1:] - closes[:-1]), 
                                    np.abs(lows[1:] - closes[:-1])))
            atr = np.mean(tr[-14:]) if len(tr) >= 14 else np.mean(tr)
            volatility = atr / closes[-1]
            
            if volatility < self.volatility_thresholds["low"]:
                return "low"
            elif volatility < self.volatility_thresholds["medium"]:
                return "medium"
            else:
                return "high"
                
        except Exception:
            return "medium"
    
    def _assess_momentum_quality(self, closes: np.ndarray, volumes: np.ndarray) -> float:
        """Assess the quality of current momentum."""
        try:
            # RSI for momentum
            rsi = self._rsi(closes, 14)
            
            # Volume confirmation
            recent_volume = np.mean(volumes[-5:]) if len(volumes) >= 5 else volumes[-1]
            avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Price momentum
            price_change = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0
            
            # Quality scoring
            momentum_score = 0.5  # Base score
            
            # RSI contribution (healthy momentum zones)
            if 40 <= rsi[-1] <= 60:
                momentum_score += 0.3  # Healthy momentum
            elif 30 <= rsi[-1] <= 70:
                momentum_score += 0.2  # Acceptable momentum
            else:
                momentum_score -= 0.1  # Extreme momentum (risky)
            
            # Volume confirmation
            if volume_ratio > 1.2:
                momentum_score += 0.2  # Strong volume support
            elif volume_ratio > 0.8:
                momentum_score += 0.1  # Adequate volume
            
            # Price momentum consistency
            if abs(price_change) > 0.02:  # Strong price movement
                momentum_score += 0.1
            
            return max(0.0, min(1.0, momentum_score))
            
        except Exception as exc:
            logger.error("❌ MOMENTUM SCORE CALCULATION FAILED - NO fallback: %s", exc)
            return None
    
    def _find_key_levels(self, highs: np.ndarray, lows: np.ndarray, current_price: float) -> float:
        """Find nearest support/resistance level."""
        try:
            # Simple support/resistance using recent highs/lows
            recent_highs = highs[-20:]
            recent_lows = lows[-20:]
            
            # Find nearest significant level
            resistance = np.max(recent_highs)
            support = np.min(recent_lows)
            
            # Return the nearest level
            if abs(current_price - resistance) < abs(current_price - support):
                return resistance
            else:
                return support
                
        except Exception:
            return current_price
    
    def _assess_risk_level(self, trend_strength: float, volatility_regime: str, momentum_quality: float) -> str:
        """Assess overall risk level for position management."""
        risk_score = 0
        
        # Trend strength contribution
        if trend_strength > 0.7:
            risk_score += 1  # Strong trend = lower risk
        elif trend_strength < 0.3:
            risk_score -= 1  # Weak trend = higher risk
        
        # Volatility contribution
        if volatility_regime == "low":
            risk_score += 1  # Low volatility = lower risk
        elif volatility_regime == "high":
            risk_score -= 1  # High volatility = higher risk
        
        # Momentum quality contribution
        if momentum_quality > 0.7:
            risk_score += 1  # Good momentum = lower risk
        elif momentum_quality < 0.3:
            risk_score -= 1  # Poor momentum = higher risk
        
        # Final risk assessment
        if risk_score >= 2:
            return "low"
        elif risk_score <= -2:
            return "high"
        else:
            return "medium"
    
    def _default_condition(self, current_price: float) -> MarketCondition:
        """Return default market condition when analysis fails."""
        return MarketCondition(
            trend_strength=0.5,
            volatility_regime="medium",
            momentum_quality=0.5,
            support_resistance_level=current_price,
            risk_level="medium"
        )
    
    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average."""
        alpha = 2.0 / (period + 1.0)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        
        return ema
    
    def _rsi(self, closes: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate RSI."""
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = np.convolve(gains, np.ones(period)/period, mode='valid')
        avg_losses = np.convolve(losses, np.ones(period)/period, mode='valid')
        
        rs = avg_gains / (avg_losses + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        # Pad with initial values
        rsi_padded = np.full(len(closes), 50.0)
        rsi_padded[period:] = rsi
        
        return rsi_padded


def get_enhanced_signal_analyzer() -> EnhancedSignalAnalyzer:
    """Get singleton instance of enhanced signal analyzer."""
    if not hasattr(get_enhanced_signal_analyzer, '_instance'):
        get_enhanced_signal_analyzer._instance = EnhancedSignalAnalyzer()
    return get_enhanced_signal_analyzer._instance
