"""Enhanced decision engine with market regime and sentiment integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from trading_bot.analytics.market_data import MultiTimeframeData
from trading_bot.analytics.market_regime import MarketRegime, MarketRegimeDetector, RegimeAnalysis, SentimentAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """Enhanced trading signal with regime and sentiment context."""
    decision: str  # "BUY", "SELL", "HOLD"
    confidence: float  # 0.0 to 1.0
    regime_context: RegimeAnalysis
    sentiment_scores: Dict[str, float]
    technical_score: float
    risk_adjusted_score: float
    reasoning: List[str]  # Human-readable reasoning
    
    def get_position_size_multiplier(self) -> float:
        """Get position size multiplier based on confidence and regime."""
        base_multiplier = self.confidence
        
        # Adjust based on regime
        if self.regime_context.is_trending() and self.regime_context.confidence > 0.7:
            base_multiplier *= 1.2  # Increase size in strong trends
        elif self.regime_context.is_ranging():
            base_multiplier *= 0.8  # Reduce size in ranging markets
        elif self.regime_context.is_high_volatility():
            base_multiplier *= 0.6  # Reduce size in high volatility
        
        # Adjust based on sentiment
        if self.decision == "BUY" and self.sentiment_scores.get('greed', 0) > 0.7:
            base_multiplier *= 0.8  # Reduce size when greed is high
        elif self.decision == "SELL" and self.sentiment_scores.get('fear', 0) > 0.7:
            base_multiplier *= 0.8  # Reduce size when fear is high
        
        return np.clip(base_multiplier, 0.1, 2.0)


class EnhancedDecisionEngine:
    """Enhanced decision engine with market regime and sentiment integration."""
    
    def __init__(self):
        """Initialize enhanced decision engine."""
        self.regime_detector = MarketRegimeDetector()
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Decision thresholds
        self.min_confidence_threshold = 0.30  # Lowered to allow more trading opportunities (was 0.45)
        
        # Profit-focused parameters for daily trading
        self.profit_target_multiplier = 1.5  # Take profit at 1.5x risk (better risk/reward)
        self.trailing_stop_activation = 0.8  # Activate trailing stop at 80% of profit target
        self.min_profit_margin = 0.02  # Minimum 2% profit margin required
        self.strong_signal_threshold = 0.8
        self.ultra_high_confidence_threshold = 0.9  # New threshold for aggressive trades
        
        # Regime-specific parameters
        self.regime_strategies = {
            MarketRegime.TRENDING_UP: {
                'buy_bias': 0.3,
                'sell_bias': -0.2,
                'momentum_weight': 0.4,
                'mean_reversion_weight': 0.1
            },
            MarketRegime.TRENDING_DOWN: {
                'buy_bias': -0.2,
                'sell_bias': 0.3,
                'momentum_weight': 0.4,
                'mean_reversion_weight': 0.1
            },
            MarketRegime.RANGING: {
                'buy_bias': 0.1,  # Increased for aggressive ranging trades
                'sell_bias': 0.0,
                'momentum_weight': 0.2,  # Increased momentum weight
                'mean_reversion_weight': 0.4
            },
            MarketRegime.HIGH_VOLATILITY: {
                'buy_bias': 0.15,  # Increased for aggressive volatile trades
                'sell_bias': 0.0,
                'momentum_weight': 0.35,  # Increased momentum weight
                'mean_reversion_weight': 0.15
            },
            MarketRegime.BREAKOUT: {
                'buy_bias': 0.2,
                'sell_bias': 0.2,
                'momentum_weight': 0.5,
                'mean_reversion_weight': 0.0
            },
            MarketRegime.REVERSAL: {
                'buy_bias': 0.0,
                'sell_bias': 0.0,
                'momentum_weight': 0.0,
                'mean_reversion_weight': 0.5
            }
        }
    
    def make_trading_decision(
        self,
        symbol: str,
        mtf_data: MultiTimeframeData,
        current_price: float,
        technical_features: Optional[Dict[str, float]] = None,
        order_book: Optional[Dict] = None
    ) -> TradingSignal:
        """Make enhanced trading decision with regime and sentiment analysis.
        
        Args:
            symbol: Trading symbol
            mtf_data: Multi-timeframe market data
            current_price: Current market price
            technical_features: Pre-calculated technical features
            order_book: Order book data
            
        Returns:
            TradingSignal with decision and context
        """
        try:
            # Analyze market regime
            regime_analysis = self.regime_detector.detect_regime(mtf_data)
            
            # Analyze sentiment
            sentiment_scores = self.sentiment_analyzer.analyze_sentiment(mtf_data)
            
            # Calculate technical score
            technical_score = self._calculate_technical_score(mtf_data, technical_features)
            
            # Get regime-specific strategy
            strategy = self.regime_strategies.get(
                regime_analysis.primary_regime,
                self.regime_strategies[MarketRegime.RANGING]
            )
            
            # Calculate regime-adjusted signals
            buy_signal = self._calculate_buy_signal(
                regime_analysis, sentiment_scores, technical_score, strategy
            )
            sell_signal = self._calculate_sell_signal(
                regime_analysis, sentiment_scores, technical_score, strategy
            )
            
            # Make decision
            decision, confidence, reasoning = self._make_final_decision(
                buy_signal, sell_signal, regime_analysis, sentiment_scores
            )
            
            # Calculate risk-adjusted score
            risk_adjusted_score = self._calculate_risk_adjusted_score(
                confidence, regime_analysis, sentiment_scores
            )
            
            return TradingSignal(
                decision=decision,
                confidence=confidence,
                regime_context=regime_analysis,
                sentiment_scores=sentiment_scores,
                technical_score=technical_score,
                risk_adjusted_score=risk_adjusted_score,
                reasoning=reasoning
            )
            
        except Exception as exc:
            logger.error("❌ DECISION MAKING FAILED for %s: %s - NO default signal", symbol, exc)
            return None
    
    def _calculate_technical_score(
        self,
        mtf_data: MultiTimeframeData,
        technical_features: Optional[Dict[str, float]]
    ) -> float:
        """Calculate technical analysis score."""
        try:
            if technical_features:
                # Use pre-calculated features if available
                return self._score_from_features(technical_features)
            
            # Calculate basic technical score from price data
            candles = mtf_data.get_timeframe('1h')
            if not candles or len(candles) < 20:
                candles = mtf_data.get_timeframe('15m')
                if not candles or len(candles) < 20:
                    return 0.0
            
            closes = np.array([c.close for c in candles])
            
            # Simple technical indicators
            rsi = self._calculate_simple_rsi(closes)
            ma_signal = self._calculate_ma_signal(closes)
            momentum = self._calculate_simple_momentum(closes)
            
            # Combine indicators
            technical_score = (
                (rsi - 50) / 50 * 0.3 +  # RSI signal
                ma_signal * 0.4 +         # MA signal
                momentum * 0.3            # Momentum signal
            )
            
            return float(np.clip(technical_score, -1.0, 1.0))
            
        except Exception as exc:
            logger.warning("Technical score calculation failed: %s", exc)
            return 0.0
    
    def _score_from_features(self, features: Dict[str, float]) -> float:
        """Calculate score from technical features."""
        try:
            # Weight different feature categories
            score = 0.0
            
            # RSI signals
            rsi_1h = features.get('rsi_1h', 50)
            score += (rsi_1h - 50) / 50 * 0.2
            
            # MACD signals
            macd_signal = features.get('macd_signal_1h', 0)
            score += macd_signal * 0.3
            
            # Bollinger Band position
            bb_position = features.get('bb_position_1h', 0)
            score += bb_position * 0.2
            
            # Price momentum
            price_change = features.get('price_change_1h', 0)
            score += price_change * 0.3
            
            return float(np.clip(score, -1.0, 1.0))
            
        except Exception:
            return 0.0
    
    def _calculate_buy_signal(
        self,
        regime_analysis: RegimeAnalysis,
        sentiment_scores: Dict[str, float],
        technical_score: float,
        strategy: Dict[str, float]
    ) -> float:
        """Calculate buy signal strength."""
        try:
            buy_signal = 0.0
            
            # Base technical signal
            if technical_score > 0:
                buy_signal += technical_score * 0.4
            
            # Regime bias
            buy_signal += strategy['buy_bias']
            
            # Momentum component
            if regime_analysis.momentum_score > 0:
                buy_signal += regime_analysis.momentum_score * strategy['momentum_weight']
            
            # Mean reversion component (contrarian)
            if regime_analysis.mean_reversion_score > 0.7 and technical_score < -0.3:
                buy_signal += 0.2 * strategy['mean_reversion_weight']
            
            # Sentiment adjustments
            bullish_sentiment = sentiment_scores.get('bullish', 0)
            greed_sentiment = sentiment_scores.get('greed', 0)
            
            buy_signal += bullish_sentiment * 0.3  # Increased bullish weight
            buy_signal += greed_sentiment * 0.2   # Changed: embrace greed for aggressive trades
            
            # Enhanced regime-specific adjustments for aggressive trading
            if regime_analysis.primary_regime == MarketRegime.TRENDING_UP:
                buy_signal += 0.2 * regime_analysis.confidence
            elif regime_analysis.primary_regime == MarketRegime.BREAKOUT:
                if regime_analysis.trend_strength > 0:
                    buy_signal += 0.3 * regime_analysis.confidence
            elif regime_analysis.primary_regime == MarketRegime.RANGING:
                # Aggressive ranging strategy: capitalize on positive sentiment
                positive_sentiment = bullish_sentiment + greed_sentiment
                if positive_sentiment > 0.5:
                    buy_signal += 0.25 * positive_sentiment * regime_analysis.confidence
            elif regime_analysis.primary_regime == MarketRegime.HIGH_VOLATILITY:
                # Aggressive volatility strategy: ride the momentum with positive sentiment
                positive_sentiment = bullish_sentiment + greed_sentiment
                if positive_sentiment > 0.5 and regime_analysis.momentum_score > 0.3:
                    buy_signal += 0.35 * positive_sentiment * regime_analysis.confidence
            
            return float(np.clip(buy_signal, 0.0, 1.0))
            
        except Exception:
            return 0.0
    
    def _calculate_sell_signal(
        self,
        regime_analysis: RegimeAnalysis,
        sentiment_scores: Dict[str, float],
        technical_score: float,
        strategy: Dict[str, float]
    ) -> float:
        """Calculate sell signal strength."""
        try:
            sell_signal = 0.0
            
            # Base technical signal
            if technical_score < 0:
                sell_signal += abs(technical_score) * 0.4
            
            # Regime bias
            sell_signal += strategy['sell_bias']
            
            # Momentum component
            if regime_analysis.momentum_score < 0:
                sell_signal += abs(regime_analysis.momentum_score) * strategy['momentum_weight']
            
            # Mean reversion component (contrarian)
            if regime_analysis.mean_reversion_score > 0.7 and technical_score > 0.3:
                sell_signal += 0.2 * strategy['mean_reversion_weight']
            
            # Sentiment adjustments
            bearish_sentiment = sentiment_scores.get('bearish', 0)
            fear_sentiment = sentiment_scores.get('fear', 0)
            
            sell_signal += bearish_sentiment * 0.2
            sell_signal -= fear_sentiment * 0.1  # Contrarian: reduce when fearful
            
            # Regime-specific adjustments
            if regime_analysis.primary_regime == MarketRegime.TRENDING_DOWN:
                sell_signal += 0.2 * regime_analysis.confidence
            elif regime_analysis.primary_regime == MarketRegime.BREAKOUT:
                if regime_analysis.trend_strength < 0:
                    sell_signal += 0.3 * regime_analysis.confidence
            
            return float(np.clip(sell_signal, 0.0, 1.0))
            
        except Exception:
            return 0.0
    
    def _make_final_decision(
        self,
        buy_signal: float,
        sell_signal: float,
        regime_analysis: RegimeAnalysis,
        sentiment_scores: Dict[str, float]
    ) -> Tuple[str, float, List[str]]:
        """Make final trading decision."""
        try:
            reasoning = []
            
            # Determine signal strength difference
            signal_diff = buy_signal - sell_signal
            max_signal = max(buy_signal, sell_signal)
            
            # Decision logic
            if abs(signal_diff) < 0.1 or max_signal < self.min_confidence_threshold:
                decision = "HOLD"
                confidence = 1.0 - max_signal  # Higher confidence in HOLD when signals are weak
                reasoning.append(f"Weak signals: buy={buy_signal:.2f}, sell={sell_signal:.2f}")
            elif buy_signal > sell_signal:
                decision = "BUY"
                confidence = buy_signal
                reasoning.append(f"Buy signal strength: {buy_signal:.2f}")
            else:
                decision = "SELL"
                confidence = sell_signal
                reasoning.append(f"Sell signal strength: {sell_signal:.2f}")
            
            # Add regime context to reasoning
            regime = regime_analysis.primary_regime.value
            reasoning.append(f"Market regime: {regime} (confidence: {regime_analysis.confidence:.2f})")
            
            # Add sentiment context
            dominant_sentiment = max(sentiment_scores.keys(), key=lambda k: sentiment_scores[k])
            reasoning.append(f"Dominant sentiment: {dominant_sentiment} ({sentiment_scores[dominant_sentiment]:.2f})")
            
            # Enhanced regime-specific decision adjustments for aggressive trading
            bullish_sentiment = sentiment_scores.get('bullish', 0) + sentiment_scores.get('greed', 0)
            is_positive_sentiment = bullish_sentiment > 0.5
            is_high_confidence = confidence > 0.9
            
            if regime_analysis.primary_regime == MarketRegime.HIGH_VOLATILITY:
                if is_high_confidence and is_positive_sentiment and decision == "BUY":
                    # Allow aggressive trading in high volatility with very high confidence + positive sentiment
                    confidence *= 1.1  # Boost confidence for high-conviction trades
                    reasoning.append("HIGH VOLATILITY OPPORTUNITY: Very high confidence + positive sentiment")
                else:
                    confidence *= 0.9  # Reduced penalty for high volatility (was 0.7)
                    reasoning.append("Reduced confidence due to high volatility")
            elif regime_analysis.is_ranging() and decision != "HOLD":
                if is_high_confidence and is_positive_sentiment and decision == "BUY":
                    # Allow aggressive trading in ranging markets with very high confidence + positive sentiment
                    confidence *= 1.05  # Slight boost for high-conviction ranging trades
                    reasoning.append("RANGING OPPORTUNITY: Very high confidence + positive sentiment")
                else:
                    confidence *= 0.8  # Reduce confidence for directional trades in ranging market
                    reasoning.append("Reduced confidence for directional trade in ranging market")
            
            # Sentiment-based adjustments
            uncertainty = sentiment_scores.get('uncertainty', 0)
            if uncertainty > 0.6:
                confidence *= 0.9  # Reduced penalty (was 0.8)
                reasoning.append("Reduced confidence due to market uncertainty")
            
            return decision, float(np.clip(confidence, 0.0, 1.0)), reasoning
            
        except Exception as exc:
            logger.error("Final decision making failed: %s", exc)
            return "HOLD", 0.5, ["Decision making error"]
    
    def _calculate_risk_adjusted_score(
        self,
        confidence: float,
        regime_analysis: RegimeAnalysis,
        sentiment_scores: Dict[str, float]
    ) -> float:
        """Calculate risk-adjusted score for position sizing."""
        try:
            risk_score = confidence
            
            # Adjust for regime risk
            if regime_analysis.primary_regime == MarketRegime.HIGH_VOLATILITY:
                risk_score *= 0.6
            elif regime_analysis.is_trending() and regime_analysis.confidence > 0.8:
                risk_score *= 1.2  # Increase in strong trends
            
            # Adjust for sentiment extremes
            fear = sentiment_scores.get('fear', 0)
            greed = sentiment_scores.get('greed', 0)
            
            if fear > 0.8 or greed > 0.8:
                risk_score *= 0.7  # Reduce in extreme sentiment
            
            return float(np.clip(risk_score, 0.0, 1.0))
            
        except Exception:
            return confidence * 0.5
    
    # Simple technical indicator calculations
    def _calculate_simple_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        """Calculate simple RSI."""
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
            
            return float(rsi)
            
        except Exception:
            return 50.0
    
    def _calculate_ma_signal(self, closes: np.ndarray) -> float:
        """Calculate moving average signal."""
        try:
            if len(closes) < 20:
                return 0.0
            
            short_ma = np.mean(closes[-5:])
            long_ma = np.mean(closes[-20:])
            
            signal = (short_ma - long_ma) / long_ma
            
            return float(np.clip(signal, -1.0, 1.0))
            
        except Exception:
            return 0.0
    
    def _calculate_simple_momentum(self, closes: np.ndarray) -> float:
        """Calculate simple momentum."""
        try:
            if len(closes) < 10:
                return 0.0
            
            momentum = (closes[-1] - closes[-10]) / closes[-10]
            
            return float(np.clip(momentum, -1.0, 1.0))
            
        except Exception:
            return 0.0
    
    # REMOVED: _default_trading_signal - NO FAKE DEFAULT SIGNALS ALLOWED
