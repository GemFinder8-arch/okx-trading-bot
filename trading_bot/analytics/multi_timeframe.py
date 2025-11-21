"""Comprehensive multi-timeframe analysis for all chart types."""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from trading_bot.analytics.market_cap_analyzer import get_market_cap_analyzer

logger = logging.getLogger(__name__)


@dataclass
class TimeframeAnalysis:
    """Analysis result for a single timeframe."""
    timeframe: str
    trend_direction: str  # "up", "down", "sideways"
    trend_strength: float  # 0.0 to 1.0
    momentum: float  # -1.0 to 1.0
    volatility: float  # 0.0 to 1.0
    support_level: float
    resistance_level: float
    rsi: float
    volume_trend: str  # "increasing", "decreasing", "stable"
    confidence: float  # 0.0 to 1.0


@dataclass
class MultiTimeframeSignal:
    """Comprehensive multi-timeframe trading signal."""
    overall_trend: str  # "bullish", "bearish", "neutral"
    trend_confluence: float  # 0.0 to 1.0
    entry_confidence: float  # 0.0 to 1.0
    risk_level: str  # "low", "medium", "high"
    timeframe_analyses: Dict[str, TimeframeAnalysis]
    recommended_stop_loss: float
    recommended_take_profit: float
    position_sizing_multiplier: float  # 0.5 to 1.5
    market_cap_category: str  # "large", "mid", "small", "micro", "nano"
    market_cap_risk_multiplier: float  # Market cap based risk adjustment
    liquidity_score: float  # 0.0 to 1.0


class MultiTimeframeAnalyzer:
    """Comprehensive multi-timeframe chart analysis."""
    
    def __init__(self, market_data_manager):
        """Initialize multi-timeframe analyzer."""
        self.market_data = market_data_manager
        self.timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
        self.timeframe_weights = {
            "1m": 0.05,   # Very short-term noise
            "5m": 0.10,   # Short-term signals
            "15m": 0.20,  # Entry timing (INCREASED from 0.15 for better entry precision)
            "1h": 0.25,   # Medium-term trend
            "4h": 0.25,   # Primary trend (DECREASED from 0.30 to balance 15m increase)
            "1d": 0.15    # Long-term bias
        }
        
    def analyze_all_timeframes(self, symbol: str) -> MultiTimeframeSignal:
        """Analyze symbol across all timeframes simultaneously."""
        try:
            logger.info("🔍 MULTI-TIMEFRAME ANALYSIS: %s across %d timeframes", symbol, len(self.timeframes))
            
            # Sequential analysis to reduce API load (was parallel)
            timeframe_results = {}
            
            # Prioritize most important timeframes for rate limiting
            priority_timeframes = ["5m", "15m", "1h", "4h"]  # Skip 1m and 1d to reduce calls
            
            for tf in priority_timeframes:
                try:
                    analysis = self._analyze_timeframe(symbol, tf)
                    if analysis:
                        timeframe_results[tf] = analysis
                        logger.debug("✅ %s analysis complete: trend=%s, strength=%.2f", 
                                   tf, analysis.trend_direction, analysis.trend_strength)
                except Exception as exc:
                    logger.warning("❌ %s analysis failed: %s", tf, exc)
            
            if not timeframe_results:
                logger.error("❌ NO TIMEFRAME ANALYSIS SUCCEEDED for %s - NO default signal", symbol)
                return None
            
            # Synthesize multi-timeframe signal
            return self._synthesize_signal(symbol, timeframe_results)
            
        except Exception as exc:
            logger.error("❌ MULTI-TIMEFRAME ANALYSIS FAILED for %s: %s - NO default signal", symbol, exc)
            return None
    
    def _analyze_timeframe(self, symbol: str, timeframe: str) -> Optional[TimeframeAnalysis]:
        """Analyze a single timeframe."""
        try:
            import time
            import random
            
            # Add small random delay to prevent rate limiting
            time.sleep(random.uniform(0.1, 0.3))
            
            # Get appropriate number of candles based on timeframe - reduced for rate limiting
            candle_counts = {
                "1m": 50,    # Reduced from 100
                "5m": 50,    # Reduced from 100
                "15m": 48,   # Reduced from 96
                "1h": 84,    # Reduced from 168
                "4h": 90,    # Reduced from 180
                "1d": 45     # Reduced from 90
            }
            
            limit = candle_counts.get(timeframe, 50)
            candles = self.market_data.get_candles(symbol, timeframe, limit=limit)
            
            if not candles or len(candles) < 10:  # Reduced from 20 to 10
                logger.debug("Insufficient candles for %s %s: %d", symbol, timeframe, len(candles) if candles else 0)
                return None
            
            # Extract OHLCV data
            opens = np.array([c.open for c in candles])
            highs = np.array([c.high for c in candles])
            lows = np.array([c.low for c in candles])
            closes = np.array([c.close for c in candles])
            volumes = np.array([c.volume for c in candles])
            
            current_price = closes[-1]
            
            # 1. TREND ANALYSIS
            trend_direction, trend_strength = self._analyze_trend(closes, highs, lows)
            
            # 2. MOMENTUM ANALYSIS
            momentum = self._calculate_momentum(closes, volumes)
            
            # 3. VOLATILITY ANALYSIS
            volatility = self._calculate_volatility(highs, lows, closes)
            
            # 4. SUPPORT/RESISTANCE LEVELS
            support_level, resistance_level = self._find_support_resistance(highs, lows, closes)
            
            # 5. RSI ANALYSIS
            rsi = self._calculate_rsi(closes)
            
            # 6. VOLUME TREND
            volume_trend = self._analyze_volume_trend(volumes)
            
            # 7. TIMEFRAME CONFIDENCE
            confidence = self._calculate_timeframe_confidence(
                trend_strength, momentum, volatility, rsi, len(candles)
            )
            
            return TimeframeAnalysis(
                timeframe=timeframe,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                momentum=momentum,
                volatility=volatility,
                support_level=support_level,
                resistance_level=resistance_level,
                rsi=rsi,
                volume_trend=volume_trend,
                confidence=confidence
            )
            
        except Exception as exc:
            logger.warning("Timeframe analysis failed for %s %s: %s", symbol, timeframe, exc)
            return None
    
    def _analyze_trend(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray) -> Tuple[str, float]:
        """Comprehensive trend analysis."""
        try:
            # Multiple EMA analysis
            ema_8 = self._ema(closes, 8)
            ema_21 = self._ema(closes, 21)
            ema_50 = self._ema(closes, 50)
            ema_200 = self._ema(closes, min(200, len(closes)//2))
            
            current_price = closes[-1]
            
            # EMA alignment scoring
            alignment_score = 0
            total_checks = 0
            
            # Short-term alignment
            if len(ema_8) > 0 and len(ema_21) > 0:
                if current_price > ema_8[-1] > ema_21[-1]:
                    alignment_score += 2
                elif current_price < ema_8[-1] < ema_21[-1]:
                    alignment_score -= 2
                total_checks += 2
            
            # Medium-term alignment
            if len(ema_21) > 0 and len(ema_50) > 0:
                if ema_21[-1] > ema_50[-1]:
                    alignment_score += 1
                elif ema_21[-1] < ema_50[-1]:
                    alignment_score -= 1
                total_checks += 1
            
            # Long-term alignment
            if len(ema_50) > 0 and len(ema_200) > 0:
                if ema_50[-1] > ema_200[-1]:
                    alignment_score += 1
                elif ema_50[-1] < ema_200[-1]:
                    alignment_score -= 1
                total_checks += 1
            
            # Trend strength (0.0 to 1.0)
            if total_checks > 0:
                trend_strength = abs(alignment_score) / total_checks
                trend_strength = min(trend_strength, 1.0)
            else:
                trend_strength = 0.5
            
            # Trend direction
            if alignment_score > 0:
                trend_direction = "up"
            elif alignment_score < 0:
                trend_direction = "down"
            else:
                trend_direction = "sideways"
            
            # Enhance with slope analysis
            if len(closes) >= 10:
                recent_slope = (closes[-1] - closes[-10]) / closes[-10]
                if abs(recent_slope) > 0.02:  # 2% move
                    trend_strength = min(trend_strength + 0.2, 1.0)
            
            return trend_direction, trend_strength
            
        except Exception:
            return "sideways", 0.5
    
    def _calculate_momentum(self, closes: np.ndarray, volumes: np.ndarray) -> float:
        """Calculate momentum score (-1.0 to 1.0)."""
        try:
            # Price momentum
            if len(closes) >= 14:
                price_change = (closes[-1] - closes[-14]) / closes[-14]
            else:
                price_change = (closes[-1] - closes[0]) / closes[0]
            
            # Volume-weighted momentum
            if len(volumes) >= 5:
                recent_volume = np.mean(volumes[-5:])
                avg_volume = np.mean(volumes)
                volume_factor = min(recent_volume / avg_volume, 2.0) if avg_volume > 0 else 1.0
            else:
                volume_factor = 1.0
            
            # Combined momentum
            momentum = price_change * volume_factor
            return max(-1.0, min(1.0, momentum * 5))  # Scale and clamp
            
        except Exception:
            return 0.0
    
    def _calculate_volatility(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> float:
        """Calculate volatility (0.0 to 1.0)."""
        try:
            # True Range calculation
            if len(highs) > 1:
                tr1 = highs[1:] - lows[1:]
                tr2 = np.abs(highs[1:] - closes[:-1])
                tr3 = np.abs(lows[1:] - closes[:-1])
                tr = np.maximum(tr1, np.maximum(tr2, tr3))
                atr = np.mean(tr[-14:]) if len(tr) >= 14 else np.mean(tr)
                volatility = atr / closes[-1]
                return min(volatility * 10, 1.0)  # Scale and clamp
            else:
                logger.error("❌ INSUFFICIENT DATA for volatility calculation - NO fallback")
                return None
                
        except Exception as exc:
            logger.error("❌ VOLATILITY CALCULATION FAILED - NO fallback: %s", exc)
            return None
    
    def _find_support_resistance(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> Tuple[float, float]:
        """Find support and resistance levels."""
        try:
            current_price = closes[-1]
            
            # Recent highs and lows
            recent_period = min(50, len(highs))
            recent_highs = highs[-recent_period:]
            recent_lows = lows[-recent_period:]
            
            # Find significant levels
            resistance = np.percentile(recent_highs, 90)
            support = np.percentile(recent_lows, 10)
            
            # Ensure levels make sense relative to current price
            if resistance <= current_price:
                resistance = current_price * 1.02
            if support >= current_price:
                support = current_price * 0.98
            
            return support, resistance
            
        except Exception:
            current_price = closes[-1]
            return current_price * 0.98, current_price * 1.02
    
    def _calculate_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        """Calculate RSI."""
        try:
            if len(closes) < period + 1:
                return 50.0
            
            deltas = np.diff(closes)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
            
        except Exception:
            return 50.0
    
    def _analyze_volume_trend(self, volumes: np.ndarray) -> str:
        """Analyze volume trend."""
        try:
            if len(volumes) < 10:
                return "stable"
            
            recent_volume = np.mean(volumes[-5:])
            older_volume = np.mean(volumes[-15:-5])
            
            ratio = recent_volume / older_volume if older_volume > 0 else 1.0
            
            if ratio > 1.2:
                return "increasing"
            elif ratio < 0.8:
                return "decreasing"
            else:
                return "stable"
                
        except Exception:
            return "stable"
    
    def _calculate_timeframe_confidence(self, trend_strength: float, momentum: float, 
                                      volatility: float, rsi: float, candle_count: int) -> float:
        """Calculate confidence for this timeframe analysis."""
        try:
            confidence = 0.5  # Base confidence
            
            # Trend strength contribution
            confidence += trend_strength * 0.3
            
            # Momentum contribution
            confidence += abs(momentum) * 0.2
            
            # RSI contribution (healthy ranges)
            if 30 <= rsi <= 70:
                confidence += 0.2
            elif 20 <= rsi <= 80:
                confidence += 0.1
            
            # Data quality contribution
            if candle_count >= 100:
                confidence += 0.1
            elif candle_count >= 50:
                confidence += 0.05
            
            # Volatility penalty (too high volatility reduces confidence)
            if volatility > 0.8:
                confidence -= 0.2
            elif volatility > 0.6:
                confidence -= 0.1
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as exc:
            logger.error("❌ CONFIDENCE CALCULATION FAILED - NO fallback: %s", exc)
            return None
    
    def _synthesize_signal(self, symbol: str, timeframe_results: Dict[str, TimeframeAnalysis]) -> MultiTimeframeSignal:
        """Synthesize multi-timeframe results into a single signal."""
        try:
            # Get market cap analysis
            market_cap_analyzer = get_market_cap_analyzer()
            market_cap_data = market_cap_analyzer.get_market_cap_data(symbol)
            
            rank_str = f"#{market_cap_data.market_cap_rank}" if market_cap_data.market_cap_rank else "N/A"
            logger.info("💰 MARKET CAP ANALYSIS %s: category=%s, cap=$%.0fM, rank=%s, liquidity=%.2f", 
                       symbol, market_cap_data.market_cap_category, 
                       market_cap_data.market_cap / 1_000_000, 
                       rank_str, 
                       market_cap_data.liquidity_score)
            
            # Weighted trend analysis
            bullish_weight = 0
            bearish_weight = 0
            total_weight = 0
            
            # Direction agreement tracking (for correct confluence)
            bullish_agreement = 0
            bearish_agreement = 0
            
            confidence_scores = []
            volatilities = []
            
            for tf, analysis in timeframe_results.items():
                weight = self.timeframe_weights.get(tf, 0.1)
                total_weight += weight
                
                # Trend contribution (for overall trend)
                if analysis.trend_direction == "up":
                    bullish_weight += weight * analysis.trend_strength
                    bullish_agreement += weight  # Track direction agreement
                elif analysis.trend_direction == "down":
                    bearish_weight += weight * analysis.trend_strength
                    bearish_agreement += weight  # Track direction agreement
                
                # Confidence scoring
                confidence_scores.append(analysis.confidence * weight)
                volatilities.append(analysis.volatility)
            
            # Overall trend determination
            if bullish_weight > bearish_weight * 1.2:
                overall_trend = "bullish"
            elif bearish_weight > bullish_weight * 1.2:
                overall_trend = "bearish"
            else:
                overall_trend = "neutral"
            
            # Trend confluence (0.0 to 1.0) - CORRECT: measures direction agreement, NOT trend strength
            # Confluence = % of timeframes agreeing on direction
            if total_weight > 0:
                max_agreement = max(bullish_agreement, bearish_agreement)
                trend_confluence = max_agreement / total_weight
                logger.debug("✅ CONFLUENCE CALCULATION: bullish=%.2f, bearish=%.2f, total=%.2f, confluence=%.2f", 
                           bullish_agreement, bearish_agreement, total_weight, trend_confluence)
            else:
                logger.warning("❌ NO CONFLUENCE DATA for %s - insufficient timeframe data", symbol)
                trend_confluence = None  # No fake data
            
            # Entry confidence - ONLY real calculations, NO randomization  
            if total_weight > 0:
                entry_confidence = sum(confidence_scores) / total_weight
            else:
                logger.warning("❌ NO CONFIDENCE DATA for %s - insufficient timeframe data", symbol)
                entry_confidence = None  # No fake data
            
            # Risk level assessment with market cap consideration
            avg_volatility = np.mean(volatilities) if volatilities else 0.5
            
            # Base risk from volatility
            if avg_volatility > 0.7:
                base_risk = "high"
            elif avg_volatility > 0.4:
                base_risk = "medium"
            else:
                base_risk = "low"
            
            # Adjust risk based on market cap
            market_cap_risk = market_cap_data.risk_level
            
            # Combined risk assessment (prioritize higher risk)
            risk_levels = ["low", "medium", "high", "very_high"]
            base_risk_idx = risk_levels.index(base_risk) if base_risk in risk_levels else 1
            cap_risk_idx = risk_levels.index(market_cap_risk) if market_cap_risk in risk_levels else 1
            
            final_risk_idx = max(base_risk_idx, cap_risk_idx)
            risk_level = risk_levels[min(final_risk_idx, len(risk_levels) - 1)]
            
            # Dynamic stop-loss and take-profit
            current_price = self._get_current_price(timeframe_results)
            stop_loss, take_profit = self._calculate_dynamic_levels(
                current_price, overall_trend, avg_volatility, trend_confluence
            )
            
            # Position sizing multiplier with market cap consideration
            base_sizing_multiplier = self._calculate_position_sizing_multiplier(
                trend_confluence, entry_confidence, risk_level
            )
            
            # Market cap adjustment to position sizing
            market_cap_multiplier = market_cap_analyzer.get_risk_multiplier(market_cap_data)
            sizing_multiplier = base_sizing_multiplier / market_cap_multiplier  # Inverse relationship
            
            logger.info("📊 MULTI-TF SYNTHESIS %s: trend=%s, confluence=%.2f, confidence=%.2f, risk=%s", 
                       symbol, overall_trend, trend_confluence, entry_confidence, risk_level)
            
            return MultiTimeframeSignal(
                overall_trend=overall_trend,
                trend_confluence=trend_confluence,
                entry_confidence=entry_confidence,
                risk_level=risk_level,
                timeframe_analyses=timeframe_results,
                recommended_stop_loss=stop_loss,
                recommended_take_profit=take_profit,
                position_sizing_multiplier=sizing_multiplier,
                market_cap_category=market_cap_data.market_cap_category,
                market_cap_risk_multiplier=market_cap_multiplier,
                liquidity_score=market_cap_data.liquidity_score
            )
            
        except Exception as exc:
            logger.error("❌ SIGNAL SYNTHESIS FAILED for %s: %s - NO default signal", symbol, exc)
            return None
    
    def _get_current_price(self, timeframe_results: Dict[str, TimeframeAnalysis]) -> float:
        """Get current price from timeframe results."""
        # Use the shortest timeframe for most current price
        for tf in ["1m", "5m", "15m", "1h", "4h", "1d"]:
            if tf in timeframe_results:
                # Approximate current price from support/resistance
                analysis = timeframe_results[tf]
                return (analysis.support_level + analysis.resistance_level) / 2
        logger.error("❌ NO PRICE DATA AVAILABLE - NO fallback")
        return None
    
    def _calculate_dynamic_levels(self, current_price: float, trend: str, volatility: float, confluence: float) -> Tuple[float, float]:
        """Calculate dynamic stop-loss and take-profit levels."""
        try:
            # Base multipliers
            base_stop = 0.02  # 2%
            base_target = 0.04  # 4%
            
            # Volatility adjustment
            vol_multiplier = 1 + (volatility * 2)  # 1x to 3x based on volatility
            
            # Confluence adjustment
            conf_multiplier = 0.5 + (confluence * 1.5)  # 0.5x to 2x based on confluence
            
            # Calculate levels
            stop_distance = base_stop * vol_multiplier
            target_distance = base_target * conf_multiplier
            
            if trend == "bullish":
                stop_loss = current_price * (1 - stop_distance)
                take_profit = current_price * (1 + target_distance)
            elif trend == "bearish":
                stop_loss = current_price * (1 + stop_distance)
                take_profit = current_price * (1 - target_distance)
            else:  # neutral
                stop_loss = current_price * (1 - stop_distance)
                take_profit = current_price * (1 + target_distance * 0.5)
            
            return stop_loss, take_profit
            
        except Exception:
            return current_price * 0.98, current_price * 1.04
    
    def _calculate_position_sizing_multiplier(self, confluence: float, confidence: float, risk_level: str) -> float:
        """Calculate position sizing multiplier based on signal quality."""
        try:
            base_multiplier = 1.0
            
            # Confluence bonus
            if confluence > 0.8:
                base_multiplier += 0.3
            elif confluence > 0.6:
                base_multiplier += 0.1
            
            # Confidence bonus
            if confidence > 0.8:
                base_multiplier += 0.2
            elif confidence > 0.6:
                base_multiplier += 0.1
            
            # Risk penalty
            if risk_level == "high":
                base_multiplier *= 0.7
            elif risk_level == "low":
                base_multiplier *= 1.1
            
            return max(0.5, min(1.5, base_multiplier))
            
        except Exception as exc:
            logger.error("❌ POSITION SIZING MULTIPLIER CALCULATION FAILED - NO fallback: %s", exc)
            return None
    
    # REMOVED: _default_signal - NO FAKE DEFAULT SIGNALS ALLOWED
    
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


def get_multi_timeframe_analyzer(market_data_manager) -> MultiTimeframeAnalyzer:
    """Get multi-timeframe analyzer instance."""
    return MultiTimeframeAnalyzer(market_data_manager)
