"""Advanced market structure analysis including order flow, institutional levels, and smart money detection."""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class VolumeProfile:
    """Volume profile analysis result."""
    poc: float  # Point of Control (highest volume price)
    value_area_high: float  # Value Area High (70% volume)
    value_area_low: float  # Value Area Low (70% volume)
    volume_nodes: Dict[float, float]  # Price levels and their volumes
    profile_type: str  # "balanced", "p_shape", "b_shape", "double_distribution"


@dataclass
class OrderFlowAnalysis:
    """Order flow analysis result."""
    bid_ask_imbalance: float  # -1.0 to 1.0 (negative = sell pressure)
    volume_delta: float  # Cumulative volume delta
    absorption_levels: List[float]  # Price levels showing absorption
    breakout_levels: List[float]  # Price levels likely to break
    institutional_activity: str  # "accumulation", "distribution", "neutral"


@dataclass
class MarketStructure:
    """Complete market structure analysis."""
    trend_structure: str  # "higher_highs_lows", "lower_highs_lows", "sideways"
    key_levels: List[float]  # Important support/resistance levels
    volume_profile: VolumeProfile
    order_flow: OrderFlowAnalysis
    liquidity_pools: List[Tuple[float, float]]  # (price, liquidity_size)
    smart_money_direction: str  # "bullish", "bearish", "neutral"
    structure_strength: float  # 0.0 to 1.0


class MarketStructureAnalyzer:
    """Advanced market structure analysis."""
    
    def __init__(self):
        """Initialize market structure analyzer."""
        self.price_levels = defaultdict(float)  # Track price level significance
        self.volume_history = deque(maxlen=1000)
        self.order_flow_history = deque(maxlen=500)
        
    def analyze_market_structure(self, candles: List, orderbook_data: Optional[Dict] = None) -> MarketStructure:
        """Comprehensive market structure analysis."""
        try:
            if not candles or len(candles) < 50:
                logger.error("❌ INSUFFICIENT DATA for market structure analysis - NO default")
                return None
            
            # Extract OHLCV data
            opens = np.array([c.open for c in candles])
            highs = np.array([c.high for c in candles])
            lows = np.array([c.low for c in candles])
            closes = np.array([c.close for c in candles])
            volumes = np.array([c.volume for c in candles])
            
            # 1. TREND STRUCTURE ANALYSIS
            trend_structure = self._analyze_trend_structure(highs, lows, closes)
            
            # 2. KEY LEVEL IDENTIFICATION
            key_levels = self._identify_key_levels(highs, lows, closes, volumes)
            
            # 3. VOLUME PROFILE ANALYSIS
            volume_profile = self._analyze_volume_profile(highs, lows, closes, volumes)
            
            # 4. ORDER FLOW ANALYSIS
            order_flow = self._analyze_order_flow(opens, highs, lows, closes, volumes, orderbook_data)
            
            # 5. LIQUIDITY POOL DETECTION
            liquidity_pools = self._detect_liquidity_pools(highs, lows, volumes)
            
            # 6. SMART MONEY ANALYSIS
            smart_money_direction = self._analyze_smart_money(closes, volumes, order_flow)
            
            # 7. STRUCTURE STRENGTH
            structure_strength = self._calculate_structure_strength(
                trend_structure, key_levels, volume_profile, order_flow
            )
            
            return MarketStructure(
                trend_structure=trend_structure,
                key_levels=key_levels,
                volume_profile=volume_profile,
                order_flow=order_flow,
                liquidity_pools=liquidity_pools,
                smart_money_direction=smart_money_direction,
                structure_strength=structure_strength
            )
            
        except Exception as exc:
            logger.error("❌ MARKET STRUCTURE ANALYSIS FAILED - NO default: %s", exc)
            return None
    
    def _analyze_trend_structure(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> str:
        """Analyze trend structure using swing highs and lows."""
        try:
            # Find swing highs and lows
            swing_highs = self._find_swing_points(highs, mode='high')
            swing_lows = self._find_swing_points(lows, mode='low')
            
            if len(swing_highs) < 2 or len(swing_lows) < 2:
                return "sideways"
            
            # Analyze recent swing points (last 3-4 swings)
            recent_highs = swing_highs[-3:] if len(swing_highs) >= 3 else swing_highs
            recent_lows = swing_lows[-3:] if len(swing_lows) >= 3 else swing_lows
            
            # Check for higher highs and higher lows (uptrend)
            higher_highs = all(recent_highs[i] > recent_highs[i-1] for i in range(1, len(recent_highs)))
            higher_lows = all(recent_lows[i] > recent_lows[i-1] for i in range(1, len(recent_lows)))
            
            # Check for lower highs and lower lows (downtrend)
            lower_highs = all(recent_highs[i] < recent_highs[i-1] for i in range(1, len(recent_highs)))
            lower_lows = all(recent_lows[i] < recent_lows[i-1] for i in range(1, len(recent_lows)))
            
            if higher_highs and higher_lows:
                return "higher_highs_lows"
            elif lower_highs and lower_lows:
                return "lower_highs_lows"
            else:
                return "sideways"
                
        except Exception:
            return "sideways"
    
    def _find_swing_points(self, data: np.ndarray, mode: str = 'high', window: int = 5) -> List[float]:
        """Find swing highs or lows."""
        try:
            swing_points = []
            
            for i in range(window, len(data) - window):
                if mode == 'high':
                    if all(data[i] >= data[j] for j in range(i - window, i + window + 1) if j != i):
                        swing_points.append(data[i])
                else:  # mode == 'low'
                    if all(data[i] <= data[j] for j in range(i - window, i + window + 1) if j != i):
                        swing_points.append(data[i])
            
            return swing_points
            
        except Exception:
            return []
    
    def _identify_key_levels(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray) -> List[float]:
        """Identify key support and resistance levels."""
        try:
            key_levels = []
            
            # 1. VOLUME-WEIGHTED LEVELS
            # Find price levels with high volume
            price_volume_map = defaultdict(float)
            
            for i in range(len(closes)):
                # Bin prices to nearest 0.1% level
                price_bin = round(closes[i] / closes[i] * 1000) / 1000 * closes[i]
                price_volume_map[price_bin] += volumes[i]
            
            # Sort by volume and take top levels
            volume_levels = sorted(price_volume_map.items(), key=lambda x: x[1], reverse=True)[:10]
            key_levels.extend([level[0] for level in volume_levels])
            
            # 2. PSYCHOLOGICAL LEVELS
            current_price = closes[-1]
            # Round numbers (every 5% increment)
            base = int(current_price / (current_price * 0.05)) * (current_price * 0.05)
            for i in range(-3, 4):
                level = base + (i * current_price * 0.05)
                if level > 0:
                    key_levels.append(level)
            
            # 3. FIBONACCI LEVELS
            if len(highs) >= 50 and len(lows) >= 50:
                recent_high = np.max(highs[-50:])
                recent_low = np.min(lows[-50:])
                diff = recent_high - recent_low
                
                fib_levels = [
                    recent_high,
                    recent_high - (diff * 0.236),
                    recent_high - (diff * 0.382),
                    recent_high - (diff * 0.5),
                    recent_high - (diff * 0.618),
                    recent_high - (diff * 0.786),
                    recent_low
                ]
                key_levels.extend(fib_levels)
            
            # 4. PIVOT POINTS
            if len(highs) >= 3:
                pivot = (highs[-2] + lows[-2] + closes[-2]) / 3
                r1 = 2 * pivot - lows[-2]
                s1 = 2 * pivot - highs[-2]
                r2 = pivot + (highs[-2] - lows[-2])
                s2 = pivot - (highs[-2] - lows[-2])
                
                key_levels.extend([s2, s1, pivot, r1, r2])
            
            # Remove duplicates and sort
            key_levels = sorted(list(set(key_levels)))
            
            # Filter levels close to current price (within 10%)
            current_price = closes[-1]
            filtered_levels = [
                level for level in key_levels 
                if abs(level - current_price) / current_price <= 0.10
            ]
            
            return filtered_levels[:15]  # Return top 15 levels
            
        except Exception:
            return []
    
    def _analyze_volume_profile(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray) -> VolumeProfile:
        """Analyze volume profile to find value areas."""
        try:
            # Create price bins
            price_range = np.max(highs) - np.min(lows)
            num_bins = min(50, len(closes) // 2)  # Adaptive number of bins
            bin_size = price_range / num_bins
            
            volume_at_price = defaultdict(float)
            
            # Distribute volume across price range for each candle
            for i in range(len(closes)):
                candle_range = highs[i] - lows[i]
                if candle_range > 0:
                    # Distribute volume evenly across the candle's range
                    num_price_points = max(1, int(candle_range / bin_size))
                    volume_per_point = volumes[i] / num_price_points
                    
                    for j in range(num_price_points):
                        price_point = lows[i] + (j * candle_range / num_price_points)
                        price_bin = round(price_point / bin_size) * bin_size
                        volume_at_price[price_bin] += volume_per_point
                else:
                    # Single price point
                    price_bin = round(closes[i] / bin_size) * bin_size
                    volume_at_price[price_bin] += volumes[i]
            
            if not volume_at_price:
                return VolumeProfile(closes[-1], closes[-1], closes[-1], {}, "balanced")
            
            # Find Point of Control (POC) - highest volume price
            poc = max(volume_at_price.items(), key=lambda x: x[1])[0]
            
            # Calculate Value Area (70% of total volume)
            total_volume = sum(volume_at_price.values())
            target_volume = total_volume * 0.7
            
            # Sort prices by volume
            sorted_prices = sorted(volume_at_price.items(), key=lambda x: x[1], reverse=True)
            
            value_area_volume = 0
            value_area_prices = []
            
            for price, volume in sorted_prices:
                value_area_prices.append(price)
                value_area_volume += volume
                if value_area_volume >= target_volume:
                    break
            
            value_area_high = max(value_area_prices) if value_area_prices else poc
            value_area_low = min(value_area_prices) if value_area_prices else poc
            
            # Determine profile type
            profile_type = self._classify_volume_profile(volume_at_price, poc)
            
            return VolumeProfile(
                poc=poc,
                value_area_high=value_area_high,
                value_area_low=value_area_low,
                volume_nodes=dict(volume_at_price),
                profile_type=profile_type
            )
            
        except Exception:
            return VolumeProfile(closes[-1], closes[-1], closes[-1], {}, "balanced")
    
    def _classify_volume_profile(self, volume_at_price: Dict[float, float], poc: float) -> str:
        """Classify volume profile shape."""
        try:
            if not volume_at_price:
                return "balanced"
            
            prices = sorted(volume_at_price.keys())
            volumes = [volume_at_price[p] for p in prices]
            
            # Find POC index
            poc_index = prices.index(poc) if poc in prices else len(prices) // 2
            
            # Analyze distribution
            upper_volume = sum(volumes[poc_index:])
            lower_volume = sum(volumes[:poc_index + 1])
            total_volume = sum(volumes)
            
            upper_ratio = upper_volume / total_volume
            lower_ratio = lower_volume / total_volume
            
            if upper_ratio > 0.6:
                return "p_shape"  # More volume at top
            elif lower_ratio > 0.6:
                return "b_shape"  # More volume at bottom
            else:
                # Check for double distribution
                max_volume = max(volumes)
                high_volume_count = sum(1 for v in volumes if v > max_volume * 0.8)
                
                if high_volume_count > 1:
                    return "double_distribution"
                else:
                    return "balanced"
                    
        except Exception:
            return "balanced"
    
    def _analyze_order_flow(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, 
                          closes: np.ndarray, volumes: np.ndarray, orderbook_data: Optional[Dict]) -> OrderFlowAnalysis:
        """Analyze order flow and market microstructure."""
        try:
            # 1. VOLUME DELTA ANALYSIS
            volume_delta = self._calculate_volume_delta(opens, highs, lows, closes, volumes)
            
            # 2. BID-ASK IMBALANCE (if orderbook data available)
            if orderbook_data:
                bid_ask_imbalance = self._calculate_bid_ask_imbalance(orderbook_data)
            else:
                # Estimate from price action
                bid_ask_imbalance = self._estimate_imbalance_from_price_action(opens, closes, volumes)
            
            # 3. ABSORPTION LEVELS
            absorption_levels = self._find_absorption_levels(highs, lows, closes, volumes)
            
            # 4. BREAKOUT LEVELS
            breakout_levels = self._find_breakout_levels(highs, lows, volumes)
            
            # 5. INSTITUTIONAL ACTIVITY
            institutional_activity = self._detect_institutional_activity(closes, volumes, volume_delta)
            
            return OrderFlowAnalysis(
                bid_ask_imbalance=bid_ask_imbalance,
                volume_delta=volume_delta,
                absorption_levels=absorption_levels,
                breakout_levels=breakout_levels,
                institutional_activity=institutional_activity
            )
            
        except Exception:
            return OrderFlowAnalysis(0.0, 0.0, [], [], "neutral")
    
    def _calculate_volume_delta(self, opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, 
                              closes: np.ndarray, volumes: np.ndarray) -> float:
        """Calculate cumulative volume delta."""
        try:
            delta = 0.0
            
            for i in range(len(closes)):
                # Estimate buying vs selling pressure
                if closes[i] > opens[i]:
                    # Green candle - more buying pressure
                    close_position = (closes[i] - lows[i]) / (highs[i] - lows[i]) if highs[i] != lows[i] else 0.5
                    buy_volume = volumes[i] * (0.5 + close_position * 0.5)
                    sell_volume = volumes[i] - buy_volume
                else:
                    # Red candle - more selling pressure
                    close_position = (closes[i] - lows[i]) / (highs[i] - lows[i]) if highs[i] != lows[i] else 0.5
                    sell_volume = volumes[i] * (1.5 - close_position * 0.5)
                    buy_volume = volumes[i] - sell_volume
                
                delta += (buy_volume - sell_volume)
            
            return delta
            
        except Exception:
            return 0.0
    
    def _calculate_bid_ask_imbalance(self, orderbook_data: Dict) -> float:
        """Calculate bid-ask imbalance from orderbook data."""
        try:
            bids = orderbook_data.get('bids', [])
            asks = orderbook_data.get('asks', [])
            
            if not bids or not asks:
                return 0.0
            
            # Calculate total bid and ask volume (top 10 levels)
            bid_volume = sum(float(bid[1]) for bid in bids[:10])
            ask_volume = sum(float(ask[1]) for ask in asks[:10])
            
            total_volume = bid_volume + ask_volume
            if total_volume == 0:
                return 0.0
            
            # Return imbalance (-1 to 1, negative = sell pressure)
            return (bid_volume - ask_volume) / total_volume
            
        except Exception:
            return 0.0
    
    def _estimate_imbalance_from_price_action(self, opens: np.ndarray, closes: np.ndarray, volumes: np.ndarray) -> float:
        """Estimate bid-ask imbalance from price action."""
        try:
            imbalance = 0.0
            
            for i in range(len(closes)):
                if closes[i] > opens[i]:
                    # Buying pressure
                    imbalance += volumes[i] * 0.1
                elif closes[i] < opens[i]:
                    # Selling pressure
                    imbalance -= volumes[i] * 0.1
            
            # Normalize
            total_volume = np.sum(volumes)
            return imbalance / total_volume if total_volume > 0 else 0.0
            
        except Exception:
            return 0.0
    
    def _find_absorption_levels(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray) -> List[float]:
        """Find price levels showing absorption (high volume, low price movement)."""
        try:
            absorption_levels = []
            
            for i in range(1, len(closes)):
                price_change = abs(closes[i] - closes[i-1]) / closes[i-1]
                volume_ratio = volumes[i] / np.mean(volumes[max(0, i-10):i]) if i > 10 else 1.0
                
                # High volume, low price movement = absorption
                if volume_ratio > 1.5 and price_change < 0.01:  # 1% price change threshold
                    absorption_levels.append(closes[i])
            
            return absorption_levels[-5:]  # Return last 5 absorption levels
            
        except Exception:
            return []
    
    def _find_breakout_levels(self, highs: np.ndarray, lows: np.ndarray, volumes: np.ndarray) -> List[float]:
        """Find price levels likely to break on volume."""
        try:
            breakout_levels = []
            
            # Find recent highs and lows with decreasing volume (weak levels)
            recent_highs = self._find_swing_points(highs, 'high', 3)
            recent_lows = self._find_swing_points(lows, 'low', 3)
            
            # Add recent swing levels as potential breakout points
            breakout_levels.extend(recent_highs[-3:])
            breakout_levels.extend(recent_lows[-3:])
            
            return list(set(breakout_levels))  # Remove duplicates
            
        except Exception:
            return []
    
    def _detect_institutional_activity(self, closes: np.ndarray, volumes: np.ndarray, volume_delta: float) -> str:
        """Detect institutional accumulation or distribution."""
        try:
            if len(closes) < 20:
                return "neutral"
            
            # Price trend
            price_trend = (closes[-1] - closes[-20]) / closes[-20]
            
            # Volume trend
            recent_volume = np.mean(volumes[-10:])
            older_volume = np.mean(volumes[-20:-10])
            volume_trend = (recent_volume - older_volume) / older_volume if older_volume > 0 else 0
            
            # Analysis
            if price_trend > 0.02 and volume_trend > 0.2 and volume_delta > 0:
                return "accumulation"  # Rising prices, increasing volume, positive delta
            elif price_trend < -0.02 and volume_trend > 0.2 and volume_delta < 0:
                return "distribution"  # Falling prices, increasing volume, negative delta
            else:
                return "neutral"
                
        except Exception:
            return "neutral"
    
    def _detect_liquidity_pools(self, highs: np.ndarray, lows: np.ndarray, volumes: np.ndarray) -> List[Tuple[float, float]]:
        """Detect liquidity pools (areas of high potential liquidity)."""
        try:
            liquidity_pools = []
            
            # Find areas where price has been rejected multiple times (liquidity above/below)
            swing_highs = self._find_swing_points(highs, 'high', 5)
            swing_lows = self._find_swing_points(lows, 'low', 5)
            
            # Group similar levels
            for level in swing_highs:
                similar_levels = [l for l in swing_highs if abs(l - level) / level < 0.005]  # Within 0.5%
                if len(similar_levels) >= 2:
                    avg_level = np.mean(similar_levels)
                    liquidity_size = len(similar_levels) * np.mean(volumes[-10:])
                    liquidity_pools.append((avg_level, liquidity_size))
            
            for level in swing_lows:
                similar_levels = [l for l in swing_lows if abs(l - level) / level < 0.005]
                if len(similar_levels) >= 2:
                    avg_level = np.mean(similar_levels)
                    liquidity_size = len(similar_levels) * np.mean(volumes[-10:])
                    liquidity_pools.append((avg_level, liquidity_size))
            
            # Remove duplicates and sort by liquidity size
            unique_pools = []
            for pool in liquidity_pools:
                if not any(abs(pool[0] - existing[0]) / pool[0] < 0.01 for existing in unique_pools):
                    unique_pools.append(pool)
            
            return sorted(unique_pools, key=lambda x: x[1], reverse=True)[:10]
            
        except Exception:
            return []
    
    def _analyze_smart_money(self, closes: np.ndarray, volumes: np.ndarray, order_flow: OrderFlowAnalysis) -> str:
        """Analyze smart money direction."""
        try:
            # Combine multiple factors
            factors = []
            
            # 1. Volume delta direction
            if order_flow.volume_delta > 0:
                factors.append(1)
            elif order_flow.volume_delta < 0:
                factors.append(-1)
            else:
                factors.append(0)
            
            # 2. Institutional activity
            if order_flow.institutional_activity == "accumulation":
                factors.append(1)
            elif order_flow.institutional_activity == "distribution":
                factors.append(-1)
            else:
                factors.append(0)
            
            # 3. Price vs volume divergence
            if len(closes) >= 20:
                price_change = (closes[-1] - closes[-20]) / closes[-20]
                volume_change = (np.mean(volumes[-10:]) - np.mean(volumes[-20:-10])) / np.mean(volumes[-20:-10])
                
                if price_change > 0 and volume_change > 0:
                    factors.append(1)  # Bullish confirmation
                elif price_change < 0 and volume_change > 0:
                    factors.append(-1)  # Bearish confirmation
                else:
                    factors.append(0)
            
            # 4. Bid-ask imbalance
            if order_flow.bid_ask_imbalance > 0.2:
                factors.append(1)
            elif order_flow.bid_ask_imbalance < -0.2:
                factors.append(-1)
            else:
                factors.append(0)
            
            # Calculate overall direction
            total_score = sum(factors)
            
            if total_score >= 2:
                return "bullish"
            elif total_score <= -2:
                return "bearish"
            else:
                return "neutral"
                
        except Exception:
            return "neutral"
    
    def _calculate_structure_strength(self, trend_structure: str, key_levels: List[float], 
                                    volume_profile: VolumeProfile, order_flow: OrderFlowAnalysis) -> float:
        """Calculate overall market structure strength."""
        try:
            strength = 0.5  # Base strength
            
            # Trend structure contribution
            if trend_structure in ["higher_highs_lows", "lower_highs_lows"]:
                strength += 0.2  # Clear trend structure
            
            # Key levels contribution
            if len(key_levels) >= 5:
                strength += 0.1  # Good level identification
            
            # Volume profile contribution
            if volume_profile.profile_type in ["p_shape", "b_shape"]:
                strength += 0.1  # Clear directional bias
            
            # Order flow contribution
            if abs(order_flow.volume_delta) > 0:
                strength += 0.1  # Clear order flow direction
            
            if order_flow.institutional_activity != "neutral":
                strength += 0.1  # Institutional activity present
            
            return max(0.0, min(1.0, strength))
            
        except Exception as exc:
            logger.error("❌ MARKET STRUCTURE STRENGTH CALCULATION FAILED - NO fallback: %s", exc)
            return None
    
    def _default_structure(self) -> None:
        """NO DEFAULT STRUCTURE - Return None when analysis fails."""
        logger.error("❌ MARKET STRUCTURE ANALYSIS FAILED - NO fake default structure")
        return None


# Singleton instance
_market_structure_analyzer = None

def get_market_structure_analyzer() -> MarketStructureAnalyzer:
    """Get singleton market structure analyzer."""
    global _market_structure_analyzer
    if _market_structure_analyzer is None:
        _market_structure_analyzer = MarketStructureAnalyzer()
    return _market_structure_analyzer
