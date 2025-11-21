"""Feature engineering for machine learning models."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from trading_bot.analytics.market_data import MultiTimeframeData

logger = logging.getLogger(__name__)


@dataclass
class FeatureSet:
    """Container for engineered features."""
    features: np.ndarray
    feature_names: List[str]
    target: Optional[float] = None
    timestamp: Optional[float] = None
    symbol: Optional[str] = None


class FeatureEngineer:
    """Feature engineering for trading ML models."""
    
    def __init__(self):
        """Initialize feature engineer."""
        self.feature_names = []
        self._initialize_feature_names()
    
    def _initialize_feature_names(self) -> None:
        """Initialize feature names for consistency."""
        # Price-based features
        price_features = [
            'price_change_1m', 'price_change_5m', 'price_change_15m', 'price_change_1h',
            'price_volatility_1m', 'price_volatility_5m', 'price_volatility_15m',
            'rsi_1m', 'rsi_5m', 'rsi_15m',
            'bb_position_1m', 'bb_position_5m', 'bb_position_15m',
            'macd_signal_1m', 'macd_signal_5m', 'macd_signal_15m'
        ]
        
        # Volume-based features
        volume_features = [
            'volume_change_1m', 'volume_change_5m', 'volume_change_15m',
            'volume_price_trend_1m', 'volume_price_trend_5m', 'volume_price_trend_15m',
            'vwap_deviation_1m', 'vwap_deviation_5m', 'vwap_deviation_15m'
        ]
        
        # Cross-timeframe features
        cross_tf_features = [
            'trend_alignment', 'momentum_divergence', 'volatility_regime',
            'support_resistance_proximity', 'fibonacci_level_proximity'
        ]
        
        # Market structure features
        market_features = [
            'bid_ask_spread', 'order_book_imbalance', 'market_impact_estimate',
            'liquidity_score', 'time_of_day', 'day_of_week'
        ]
        
        self.feature_names = price_features + volume_features + cross_tf_features + market_features
    
    def extract_features(
        self,
        mtf_data: MultiTimeframeData,
        current_price: float,
        order_book: Optional[Dict] = None
    ) -> FeatureSet:
        """Extract features from multi-timeframe data.
        
        Args:
            mtf_data: Multi-timeframe market data
            current_price: Current market price
            order_book: Order book data (optional)
            
        Returns:
            FeatureSet with extracted features
        """
        try:
            features = []
            
            # Extract timeframe-specific features
            for tf in ['1m', '5m', '15m', '1h']:
                candles = mtf_data.get_timeframe(tf)
                if candles and len(candles) >= 20:
                    tf_features = self._extract_timeframe_features(candles, tf)
                    features.extend(tf_features)
                else:
                    # Fill with zeros if no data
                    tf_feature_count = self._get_timeframe_feature_count(tf)
                    features.extend([0.0] * tf_feature_count)
            
            # Extract cross-timeframe features
            cross_features = self._extract_cross_timeframe_features(mtf_data, current_price)
            features.extend(cross_features)
            
            # Extract market structure features
            market_features = self._extract_market_features(order_book, current_price)
            features.extend(market_features)
            
            # Ensure we have the right number of features
            expected_count = len(self.feature_names)
            if len(features) != expected_count:
                logger.warning(
                    "Feature count mismatch: expected %d, got %d. Padding with zeros.",
                    expected_count, len(features)
                )
                # Pad or truncate to match expected count
                if len(features) < expected_count:
                    features.extend([0.0] * (expected_count - len(features)))
                else:
                    features = features[:expected_count]
            
            return FeatureSet(
                features=np.array(features, dtype=np.float32),
                feature_names=self.feature_names.copy(),
                symbol=mtf_data.symbol,
                timestamp=mtf_data.last_update
            )
            
        except Exception as exc:
            logger.error("Feature extraction failed for %s: %s", mtf_data.symbol, exc)
            # Return zero features as fallback
            return FeatureSet(
                features=np.zeros(len(self.feature_names), dtype=np.float32),
                feature_names=self.feature_names.copy(),
                symbol=mtf_data.symbol
            )
    
    def _extract_timeframe_features(self, candles: List, timeframe: str) -> List[float]:
        """Extract features for a specific timeframe."""
        try:
            # Convert to arrays
            closes = np.array([c.close for c in candles])
            highs = np.array([c.high for c in candles])
            lows = np.array([c.low for c in candles])
            volumes = np.array([c.volume for c in candles])
            
            features = []
            
            # Price change (return)
            if len(closes) > 1:
                price_change = (closes[-1] - closes[-2]) / closes[-2]
                features.append(price_change)
            else:
                features.append(0.0)
            
            # Price volatility (rolling std of returns)
            if len(closes) > 10:
                returns = np.diff(closes) / closes[:-1]
                volatility = np.std(returns[-10:])  # Last 10 periods
                features.append(volatility)
            else:
                features.append(0.0)
            
            # RSI
            rsi = self._calculate_rsi(closes)
            features.append(rsi)
            
            # Bollinger Band position
            bb_position = self._calculate_bb_position(closes)
            features.append(bb_position)
            
            # MACD signal
            macd_signal = self._calculate_macd_signal(closes)
            features.append(macd_signal)
            
            # Volume change
            if len(volumes) > 1:
                volume_change = (volumes[-1] - volumes[-2]) / max(volumes[-2], 1e-10)
                features.append(volume_change)
            else:
                features.append(0.0)
            
            # Volume-price trend
            vpt = self._calculate_volume_price_trend(closes, volumes)
            features.append(vpt)
            
            # VWAP deviation
            vwap_dev = self._calculate_vwap_deviation(closes, volumes)
            features.append(vwap_dev)
            
            return features
            
        except Exception as exc:
            logger.warning("Timeframe feature extraction failed for %s: %s", timeframe, exc)
            return [0.0] * self._get_timeframe_feature_count(timeframe)
    
    def _get_timeframe_feature_count(self, timeframe: str) -> int:
        """Get expected feature count for a timeframe."""
        return 8  # price_change, volatility, rsi, bb_position, macd, volume_change, vpt, vwap_dev
    
    def _extract_cross_timeframe_features(
        self, 
        mtf_data: MultiTimeframeData, 
        current_price: float
    ) -> List[float]:
        """Extract cross-timeframe features."""
        try:
            features = []
            
            # Trend alignment across timeframes
            trends = []
            for tf in ['1m', '5m', '15m', '1h']:
                candles = mtf_data.get_timeframe(tf)
                if candles and len(candles) >= 20:
                    closes = [c.close for c in candles]
                    trend = self._calculate_trend_direction(closes)
                    trends.append(trend)
            
            # Calculate trend alignment (-1 to 1)
            if trends:
                trend_alignment = np.mean(trends)
            else:
                trend_alignment = 0.0
            features.append(trend_alignment)
            
            # Momentum divergence (short vs long term)
            momentum_div = self._calculate_momentum_divergence(mtf_data)
            features.append(momentum_div)
            
            # Volatility regime (current vs historical)
            vol_regime = self._calculate_volatility_regime(mtf_data)
            features.append(vol_regime)
            
            # Support/resistance proximity
            sr_proximity = self._calculate_support_resistance_proximity(mtf_data, current_price)
            features.append(sr_proximity)
            
            # Fibonacci level proximity
            fib_proximity = self._calculate_fibonacci_proximity(mtf_data, current_price)
            features.append(fib_proximity)
            
            return features
            
        except Exception as exc:
            logger.warning("Cross-timeframe feature extraction failed: %s", exc)
            return [0.0] * 5
    
    def _extract_market_features(
        self, 
        order_book: Optional[Dict], 
        current_price: float
    ) -> List[float]:
        """Extract market microstructure features."""
        try:
            features = []
            
            if order_book:
                # Bid-ask spread
                bids = order_book.get('bids', [])
                asks = order_book.get('asks', [])
                
                if bids and asks:
                    best_bid = bids[0][0]
                    best_ask = asks[0][0]
                    spread = (best_ask - best_bid) / current_price
                    features.append(spread)
                    
                    # Order book imbalance
                    bid_volume = sum(bid[1] for bid in bids[:5])  # Top 5 levels
                    ask_volume = sum(ask[1] for ask in asks[:5])
                    total_volume = bid_volume + ask_volume
                    if total_volume > 0:
                        imbalance = (bid_volume - ask_volume) / total_volume
                    else:
                        imbalance = 0.0
                    features.append(imbalance)
                    
                    # Market impact estimate (simplified)
                    market_impact = spread * 0.5  # Rough estimate
                    features.append(market_impact)
                else:
                    features.extend([0.0, 0.0, 0.0])
            else:
                features.extend([0.0, 0.0, 0.0])
            
            # Liquidity score (placeholder)
            liquidity_score = 0.5  # Would need more sophisticated calculation
            features.append(liquidity_score)
            
            # Time-based features
            import time
            current_time = time.time()
            hour_of_day = (current_time % 86400) / 86400  # Normalized hour
            day_of_week = ((current_time // 86400) % 7) / 7  # Normalized day
            
            features.extend([hour_of_day, day_of_week])
            
            return features
            
        except Exception as exc:
            logger.warning("Market feature extraction failed: %s", exc)
            return [0.0] * 6
    
    # Technical indicator calculations
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate RSI indicator."""
        try:
            if len(prices) < period + 1:
                return 50.0  # Neutral RSI
            
            deltas = np.diff(prices)
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
    
    def _calculate_bb_position(self, prices: np.ndarray, period: int = 20) -> float:
        """Calculate Bollinger Band position."""
        try:
            if len(prices) < period:
                return 0.0
            
            sma = np.mean(prices[-period:])
            std = np.std(prices[-period:])
            
            if std == 0:
                return 0.0
            
            current_price = prices[-1]
            bb_position = (current_price - sma) / (2 * std)  # Normalized to [-1, 1]
            
            return float(np.clip(bb_position, -1.0, 1.0))
            
        except Exception:
            return 0.0
    
    def _calculate_macd_signal(self, prices: np.ndarray) -> float:
        """Calculate MACD signal."""
        try:
            if len(prices) < 26:
                return 0.0
            
            # Simple MACD calculation
            ema12 = self._ema(prices, 12)
            ema26 = self._ema(prices, 26)
            
            if len(ema12) < 2 or len(ema26) < 2:
                return 0.0
            
            macd_line = ema12[-1] - ema26[-1]
            macd_prev = ema12[-2] - ema26[-2]
            
            # Signal is the change in MACD
            signal = macd_line - macd_prev
            
            return float(signal / prices[-1])  # Normalize by price
            
        except Exception:
            return 0.0
    
    def _ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate exponential moving average."""
        try:
            alpha = 2.0 / (period + 1)
            ema = np.zeros_like(prices)
            ema[0] = prices[0]
            
            for i in range(1, len(prices)):
                ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
            
            return ema
            
        except Exception:
            return np.array([])
    
    def _calculate_volume_price_trend(self, prices: np.ndarray, volumes: np.ndarray) -> float:
        """Calculate volume-price trend indicator."""
        try:
            if len(prices) < 2 or len(volumes) < 2:
                return 0.0
            
            price_change = (prices[-1] - prices[-2]) / prices[-2]
            volume_change = (volumes[-1] - volumes[-2]) / max(volumes[-2], 1e-10)
            
            # VPT is correlation between price and volume changes
            vpt = price_change * volume_change
            
            return float(vpt)
            
        except Exception:
            return 0.0
    
    def _calculate_vwap_deviation(self, prices: np.ndarray, volumes: np.ndarray) -> float:
        """Calculate deviation from VWAP."""
        try:
            if len(prices) != len(volumes) or len(prices) < 10:
                return 0.0
            
            # Calculate VWAP for last 10 periods
            recent_prices = prices[-10:]
            recent_volumes = volumes[-10:]
            
            vwap = np.sum(recent_prices * recent_volumes) / np.sum(recent_volumes)
            current_price = prices[-1]
            
            deviation = (current_price - vwap) / vwap
            
            return float(deviation)
            
        except Exception:
            return 0.0
    
    def _calculate_trend_direction(self, prices: List[float]) -> float:
        """Calculate trend direction (-1 to 1)."""
        try:
            if len(prices) < 10:
                return 0.0
            
            # Simple linear regression slope
            x = np.arange(len(prices))
            y = np.array(prices)
            
            slope = np.polyfit(x, y, 1)[0]
            
            # Normalize slope by price level
            normalized_slope = slope / np.mean(y)
            
            # Clip to [-1, 1]
            return float(np.clip(normalized_slope * 100, -1.0, 1.0))
            
        except Exception:
            return 0.0
    
    def _calculate_momentum_divergence(self, mtf_data: MultiTimeframeData) -> float:
        """Calculate momentum divergence between timeframes."""
        try:
            # Compare 1m vs 1h momentum
            short_candles = mtf_data.get_timeframe('1m')
            long_candles = mtf_data.get_timeframe('1h')
            
            if not short_candles or not long_candles:
                return 0.0
            
            short_momentum = self._calculate_momentum([c.close for c in short_candles[-10:]])
            long_momentum = self._calculate_momentum([c.close for c in long_candles[-10:]])
            
            divergence = short_momentum - long_momentum
            
            return float(np.clip(divergence, -1.0, 1.0))
            
        except Exception:
            return 0.0
    
    def _calculate_momentum(self, prices: List[float]) -> float:
        """Calculate price momentum."""
        try:
            if len(prices) < 2:
                return 0.0
            
            momentum = (prices[-1] - prices[0]) / prices[0]
            return float(momentum)
            
        except Exception:
            return 0.0
    
    def _calculate_volatility_regime(self, mtf_data: MultiTimeframeData) -> float:
        """Calculate current volatility regime."""
        try:
            candles = mtf_data.get_timeframe('1h')
            if not candles or len(candles) < 50:
                return 0.0
            
            closes = [c.close for c in candles]
            returns = np.diff(closes) / closes[:-1]
            
            # Current volatility (last 10 periods)
            current_vol = np.std(returns[-10:])
            
            # Historical volatility (all periods)
            historical_vol = np.std(returns)
            
            if historical_vol == 0:
                return 0.0
            
            # Regime: current vs historical
            regime = (current_vol - historical_vol) / historical_vol
            
            return float(np.clip(regime, -1.0, 1.0))
            
        except Exception:
            return 0.0
    
    def _calculate_support_resistance_proximity(
        self, 
        mtf_data: MultiTimeframeData, 
        current_price: float
    ) -> float:
        """Calculate proximity to support/resistance levels."""
        try:
            candles = mtf_data.get_timeframe('1h')
            if not candles or len(candles) < 20:
                return 0.0
            
            highs = [c.high for c in candles]
            lows = [c.low for c in candles]
            
            # Find recent swing highs and lows
            resistance = max(highs[-20:])
            support = min(lows[-20:])
            
            # Calculate proximity (0 = at support, 1 = at resistance)
            if resistance == support:
                return 0.5
            
            proximity = (current_price - support) / (resistance - support)
            
            return float(np.clip(proximity, 0.0, 1.0))
            
        except Exception:
            return 0.5
    
    def _calculate_fibonacci_proximity(
        self, 
        mtf_data: MultiTimeframeData, 
        current_price: float
    ) -> float:
        """Calculate proximity to Fibonacci levels."""
        try:
            candles = mtf_data.get_timeframe('1h')
            if not candles or len(candles) < 50:
                return 0.0
            
            highs = [c.high for c in candles]
            lows = [c.low for c in candles]
            
            swing_high = max(highs[-50:])
            swing_low = min(lows[-50:])
            
            if swing_high == swing_low:
                return 0.0
            
            # Key Fibonacci levels
            fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
            
            # Find closest Fibonacci level
            min_distance = float('inf')
            for level in fib_levels:
                fib_price = swing_low + (swing_high - swing_low) * level
                distance = abs(current_price - fib_price) / current_price
                min_distance = min(min_distance, distance)
            
            # Convert distance to proximity (closer = higher value)
            proximity = 1.0 - min(min_distance * 10, 1.0)  # Scale and clip
            
            return float(proximity)
            
        except Exception:
            return 0.0
