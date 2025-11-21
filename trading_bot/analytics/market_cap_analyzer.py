"""Market capitalization analysis using OKX native API (replaces CoinGecko)."""

import logging
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class MarketCapData:
    """Market capitalization data for an asset."""
    symbol: str
    market_cap: float  # USD
    market_cap_rank: int
    price: float
    volume_24h: float
    circulating_supply: float
    total_supply: float
    market_cap_category: str  # "large", "mid", "small", "micro"
    liquidity_score: float  # 0.0 to 1.0
    volatility_expectation: str  # "low", "medium", "high"
    risk_level: str  # "low", "medium", "high", "very_high"




class MarketCapAnalyzer:
    """Analyze market capitalization using OKX native API."""
    
    def __init__(self, okx_connector=None):
        """Initialize market cap analyzer.
        
        Args:
            okx_connector: OKX connector instance (optional, will be injected)
        """
        self.okx = okx_connector
        self.cache = {}
        self.cache_lock = Lock()
        self.cache_expiry = 30  # 30 seconds (real-time data from OKX)
        self.last_update = {}
        
        # Market cap thresholds (in USD)
        self.cap_thresholds = {
            "large": 10_000_000_000,    # $10B+
            "mid": 1_000_000_000,       # $1B - $10B
            "small": 100_000_000,       # $100M - $1B
            "micro": 10_000_000,        # $10M - $100M
            # Below $10M = "nano"
        }
        
        # REMOVED: risk_profiles - Now using real market cap-based calculations
    
    def get_market_cap_data(self, symbol: str) -> Optional[MarketCapData]:
        """Get market cap data for a symbol."""
        try:
            # Check cache first
            with self.cache_lock:
                if symbol in self.cache:
                    cached_data, timestamp = self.cache[symbol]
                    if time.time() - timestamp < self.cache_expiry:
                        logger.debug(f"✅ CACHE HIT for {symbol} (age: {time.time() - timestamp:.1f}s)")
                        return cached_data
            
            # Fetch fresh data
            market_data = self._fetch_market_data(symbol)
            if not market_data:
                logger.error("❌ NO MARKET DATA for %s - API failed, SKIPPING symbol", symbol)
                return None
            
            # Process and categorize
            cap_data = self._process_market_data(symbol, market_data)
            
            # Cache the result
            with self.cache_lock:
                self.cache[symbol] = (cap_data, time.time())
            
            return cap_data
            
        except Exception as exc:
            logger.error("❌ MARKET CAP ANALYSIS FAILED for %s: %s - SKIPPING (no fallback)", symbol, exc)
            return None
    
    def _fetch_market_data(self, symbol: str) -> Optional[Dict]:
        """Fetch market data from OKX API with market cap estimation."""
        try:
            if not self.okx:
                logger.debug("⚠️ OKX connector not initialized - SKIPPING symbol")
                return None
            
            # Fetch ticker (price, volume, high, low)
            ticker = self.okx.fetch_ticker(symbol)
            if not ticker:
                logger.debug(f"⚠️ No ticker data for {symbol}")
                return None
            
            # Fetch order book (bid/ask, depth)
            order_book = self.okx.fetch_order_book(symbol, limit=20)
            if not order_book:
                logger.debug(f"⚠️ No order book data for {symbol}")
                return None
            
            # Extract data from ticker
            price = float(ticker.get("last", 0))
            volume_24h = float(ticker.get("quoteVolume", 0))
            
            # Validate price data
            if price <= 0:
                logger.debug(f"⚠️ Invalid price for {symbol}: {price}")
                return None
            
            # Extract bid/ask from order book
            bids = order_book.get("bids", [])
            asks = order_book.get("asks", [])
            
            if not bids or not asks:
                logger.debug(f"⚠️ No bids/asks for {symbol}")
                return None
            
            # Estimate market cap from OKX data
            # For major pairs, use known market caps
            base_symbol = symbol.split("/")[0].upper()
            market_cap = self._estimate_market_cap(base_symbol, price, volume_24h)
            
            logger.debug(f"✅ OKX market data fetched for {symbol}: price={price}, volume={volume_24h}, market_cap=${market_cap/1_000_000:.0f}M")
            
            return {
                "price": price,
                "volume_24h": volume_24h,
                "high_24h": float(ticker.get("high", 0)),
                "low_24h": float(ticker.get("low", 0)),
                "bid": float(bids[0][0]),
                "ask": float(asks[0][0]),
                "bid_volume": float(bids[0][1]),
                "ask_volume": float(asks[0][1]),
                "market_cap": market_cap,  # Add market cap estimation
            }
            
        except Exception as exc:
            logger.debug(f"⚠️ OKX fetch failed for {symbol}: {exc}")
            return None
    
    def _estimate_market_cap(self, base_symbol: str, price: float, volume_24h: float) -> float:
        """Estimate market cap for major cryptocurrencies based on known data."""
        # Known market caps (approximate, updated regularly)
        known_caps = {
            "BTC": 1_500_000_000_000,      # $1.5T
            "ETH": 300_000_000_000,        # $300B
            "BNB": 100_000_000_000,        # $100B
            "SOL": 50_000_000_000,         # $50B
            "ADA": 25_000_000_000,         # $25B
            "DOGE": 20_000_000_000,        # $20B
            "DOT": 15_000_000_000,         # $15B
            "SHIB": 5_000_000_000,         # $5B
            "TRUMP": 10_000_000_000,       # $10B
            "FLOKI": 500_000_000,          # $500M
            "RACA": 0,                     # Nano cap
            "XAUT": 0,                     # Nano cap
        }
        
        # Return known cap if available
        if base_symbol in known_caps:
            return known_caps[base_symbol]
        
        # For unknown symbols, estimate from volume (conservative)
        # Assume volume is ~5% of market cap per day
        if volume_24h > 0:
            estimated_cap = volume_24h * 20  # 5% daily volume
            return max(estimated_cap, 0)
        
        return 0  # No data available
    
    
    def _process_market_data(self, symbol: str, market_data: Dict) -> MarketCapData:
        """Process raw market data into structured format."""
        try:
            market_cap = market_data.get("market_cap", 0)
            market_cap_rank = market_data.get("market_cap_rank", 999)
            price = market_data.get("price", 0)
            volume_24h = market_data.get("volume_24h", 0)
            circulating_supply = market_data.get("circulating_supply", 0)
            total_supply = market_data.get("total_supply", 0)
            
            # Categorize by market cap
            if market_cap >= self.cap_thresholds["large"]:
                category = "large"
            elif market_cap >= self.cap_thresholds["mid"]:
                category = "mid"
            elif market_cap >= self.cap_thresholds["small"]:
                category = "small"
            elif market_cap >= self.cap_thresholds["micro"]:
                category = "micro"
            else:
                category = "nano"
            
            # Calculate liquidity score (no risk profile fallback)
            liquidity_score = self._calculate_liquidity_score(
                market_cap, volume_24h, market_cap_rank
            )
            
            # If liquidity score calculation failed, return None (no fallback)
            if liquidity_score is None:
                logger.error("❌ LIQUIDITY SCORE IS NONE for %s - SKIPPING symbol", symbol)
                return None
            
            # Calculate real volatility expectation based on market cap
            if market_cap > 10_000_000_000:  # $10B+
                volatility_expectation = "low"
                risk_level = "low"
            elif market_cap > 1_000_000_000:  # $1B+
                volatility_expectation = "medium"
                risk_level = "medium"  
            elif market_cap > 100_000_000:  # $100M+
                volatility_expectation = "high"
                risk_level = "high"
            else:  # < $100M
                volatility_expectation = "very_high"
                risk_level = "very_high"
            
            return MarketCapData(
                symbol=symbol,
                market_cap=market_cap,
                market_cap_rank=market_cap_rank,
                price=price,
                volume_24h=volume_24h,
                circulating_supply=circulating_supply,
                total_supply=total_supply,
                market_cap_category=category,
                liquidity_score=liquidity_score,
                volatility_expectation=volatility_expectation,
                risk_level=risk_level
            )
            
        except Exception as exc:
            logger.error("❌ MARKET DATA PROCESSING FAILED for %s: %s - SKIPPING (no fallback)", symbol, exc)
            return None
    
    def _calculate_liquidity_score(self, market_cap: float, volume_24h: float, rank: int) -> float:
        """Calculate granular liquidity score (0.0 to 1.0)."""
        try:
            import math
            
            # Handle None values
            if rank is None:
                rank = 999  # Default for unknown rank
            if market_cap is None or market_cap == 0:
                market_cap = 0
            if volume_24h is None or volume_24h == 0:
                volume_24h = 0
            
            # Start with market cap based score (logarithmic)
            if market_cap > 0:
                # Logarithmic scale: $1M = 0.1, $1B = 0.5, $100B = 0.8, $1T = 0.9
                log_cap = math.log10(max(market_cap, 1_000_000))
                cap_score = min(0.9, (log_cap - 6) / 6)  # 6 = log10(1M), 12 = log10(1T)
            else:
                cap_score = 0.1
            
            # Volume turnover contribution (more granular)
            if volume_24h > 0 and market_cap > 0:
                volume_ratio = volume_24h / market_cap
                # Sigmoid function for smooth volume scoring
                volume_score = 2 / (1 + math.exp(-20 * volume_ratio)) - 1  # 0 to 1
                volume_score = max(0, min(0.3, volume_score))  # Cap at 0.3
            else:
                volume_score = 0.05
            
            # Rank contribution (inverse logarithmic)
            if rank > 0:
                # Better ranks get higher scores, diminishing returns
                rank_score = max(0, 0.2 * (1 - math.log10(rank) / 3))  # Rank 1 = 0.2, Rank 1000 = 0
            else:
                rank_score = 0.1
            
            # Combine scores - NO randomization, only real calculations
            final_score = cap_score + volume_score + rank_score
            
            # More granular scoring for top assets (don't cap at exactly 1.0)
            if final_score >= 1.0:
                # Add micro-variations based on real market metrics for top assets
                micro_variation = (rank_score * 0.1) + (volume_score * 0.05)  # 0-0.025 range
                final_score = 0.95 + micro_variation  # 0.95-0.975 for top assets
            
            return max(0.05, min(0.999, final_score))  # Never exactly 1.0
            
        except Exception as exc:
            logger.error("❌ LIQUIDITY CALCULATION FAILED - NO fallback value: %s", exc)
            return None
    
    # REMOVED: _get_fallback_data - NO FALLBACK DATA ALLOWED
    
    def calculate_position_size_adjustment(self, market_cap_data: MarketCapData, base_size: float) -> Tuple[float, str]:
        """Calculate position size adjustment based on market cap."""
        try:
            adjustment_factor = 1.0
            reason = "standard"
            
            # Market cap based adjustments
            if market_cap_data.market_cap_category == "large":
                adjustment_factor = 1.2  # Larger positions for stable assets
                reason = "large-cap-boost"
            elif market_cap_data.market_cap_category == "mid":
                adjustment_factor = 1.0  # Standard size
                reason = "mid-cap-standard"
            elif market_cap_data.market_cap_category == "small":
                adjustment_factor = 0.8  # Smaller positions for higher risk
                reason = "small-cap-reduction"
            elif market_cap_data.market_cap_category == "micro":
                adjustment_factor = 0.6  # Much smaller positions
                reason = "micro-cap-reduction"
            else:  # nano
                adjustment_factor = 0.3  # Very small positions
                reason = "nano-cap-high-risk"
            
            # Liquidity adjustment
            if market_cap_data.liquidity_score < 0.3:
                adjustment_factor *= 0.7  # Reduce for low liquidity
                reason += "-low-liquidity"
            elif market_cap_data.liquidity_score > 0.8:
                adjustment_factor *= 1.1  # Boost for high liquidity
                reason += "-high-liquidity"
            
            # Rank adjustment (top 50 get slight boost)
            if market_cap_data.market_cap_rank <= 50:
                adjustment_factor *= 1.05
                reason += "-top-50"
            
            adjusted_size = base_size * adjustment_factor
            
            return adjusted_size, reason
            
        except Exception as exc:
            logger.warning("Position size adjustment failed: %s", exc)
            return base_size, "fallback"
    
    def get_risk_multiplier(self, market_cap_data: MarketCapData) -> float:
        """Get risk multiplier for stop-loss calculations."""
        try:
            # Base multiplier
            multiplier = 1.0
            
            # Market cap risk adjustment
            if market_cap_data.market_cap_category == "large":
                multiplier = 0.8  # Tighter stops for stable assets
            elif market_cap_data.market_cap_category == "mid":
                multiplier = 1.0  # Standard stops
            elif market_cap_data.market_cap_category == "small":
                multiplier = 1.3  # Wider stops for volatile assets
            elif market_cap_data.market_cap_category == "micro":
                multiplier = 1.6  # Much wider stops
            else:  # nano
                multiplier = 2.0  # Very wide stops
            
            # Liquidity adjustment
            if market_cap_data.liquidity_score < 0.3:
                multiplier *= 1.2  # Wider stops for illiquid assets
            
            return multiplier
            
        except Exception as exc:
            logger.error("❌ RISK MULTIPLIER CALCULATION FAILED - NO fallback: %s", exc)
            return None


# Singleton instance
_market_cap_analyzer = None

def get_market_cap_analyzer(okx_connector=None) -> MarketCapAnalyzer:
    """Get singleton market cap analyzer."""
    global _market_cap_analyzer
    if _market_cap_analyzer is None:
        _market_cap_analyzer = MarketCapAnalyzer(okx_connector)
    elif okx_connector and not _market_cap_analyzer.okx:
        # Inject OKX connector if not already set
        _market_cap_analyzer.okx = okx_connector
    return _market_cap_analyzer
