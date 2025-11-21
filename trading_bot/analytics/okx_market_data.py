"""Market data provider using OKX native API (replaces CoinGecko)."""

import logging
import time
from typing import Dict, Optional
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class OKXMarketData:
    """Market data from OKX API."""
    symbol: str
    price: float
    volume_24h: float
    high_24h: float
    low_24h: float
    bid: float
    ask: float
    bid_volume: float
    ask_volume: float
    timestamp: float


class OKXMarketDataProvider:
    """Provide market data using OKX native API (no CoinGecko)."""
    
    def __init__(self, okx_connector):
        """Initialize with OKX connector.
        
        Args:
            okx_connector: OKX connector instance
        """
        self.okx = okx_connector
        self.cache = {}
        self.cache_lock = Lock()
        self.cache_ttl = 30  # 30 seconds (real-time data)
        self.last_update = {}
    
    def get_market_data(self, symbol: str) -> Optional[OKXMarketData]:
        """Get market data from OKX API.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            
        Returns:
            OKXMarketData or None if fetch fails
        """
        try:
            # Check cache
            with self.cache_lock:
                if symbol in self.cache:
                    cached_data, timestamp = self.cache[symbol]
                    if time.time() - timestamp < self.cache_ttl:
                        logger.debug(f"✅ CACHE HIT for {symbol} (age: {time.time() - timestamp:.1f}s)")
                        return cached_data
            
            # Fetch fresh data from OKX
            market_data = self._fetch_from_okx(symbol)
            if not market_data:
                logger.debug(f"⚠️ Failed to fetch market data for {symbol} from OKX")
                return None
            
            # Cache the result
            with self.cache_lock:
                self.cache[symbol] = (market_data, time.time())
            
            return market_data
            
        except Exception as exc:
            logger.debug(f"⚠️ Market data fetch failed for {symbol}: {exc}")
            return None
    
    def _fetch_from_okx(self, symbol: str) -> Optional[OKXMarketData]:
        """Fetch market data from OKX API.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            
        Returns:
            OKXMarketData or None if fetch fails
        """
        try:
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
            high_24h = float(ticker.get("high", 0))
            low_24h = float(ticker.get("low", 0))
            
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
            
            bid = float(bids[0][0])
            bid_volume = float(bids[0][1])
            ask = float(asks[0][0])
            ask_volume = float(asks[0][1])
            
            # Validate bid/ask
            if bid <= 0 or ask <= 0 or bid >= ask:
                logger.debug(f"⚠️ Invalid bid/ask for {symbol}: bid={bid}, ask={ask}")
                return None
            
            logger.debug(f"✅ OKX market data fetched for {symbol}: price={price}, volume={volume_24h}")
            
            return OKXMarketData(
                symbol=symbol,
                price=price,
                volume_24h=volume_24h,
                high_24h=high_24h,
                low_24h=low_24h,
                bid=bid,
                ask=ask,
                bid_volume=bid_volume,
                ask_volume=ask_volume,
                timestamp=time.time()
            )
            
        except Exception as exc:
            logger.debug(f"⚠️ OKX fetch failed for {symbol}: {exc}")
            return None
    
    def calculate_liquidity_score(self, market_data: OKXMarketData) -> float:
        """Calculate liquidity score from OKX market data.
        
        Args:
            market_data: OKXMarketData instance
            
        Returns:
            Liquidity score (0.0 to 1.0)
        """
        try:
            # Spread score (lower spread = higher liquidity)
            spread = (market_data.ask - market_data.bid) / market_data.price
            spread_score = max(0.0, 1.0 - spread * 100)  # Penalize spreads > 1%
            
            # Depth score (more depth = higher liquidity)
            total_depth_usd = (market_data.bid_volume * market_data.bid) + (market_data.ask_volume * market_data.ask)
            depth_score = min(total_depth_usd / 10000.0, 1.0)  # $10k depth = max score
            
            # Volume score (more volume = higher liquidity)
            if market_data.volume_24h > 0:
                volume_score = min(market_data.volume_24h / 1_000_000.0, 1.0)  # $1M volume = max score
            else:
                volume_score = 0.0
            
            # Combined score
            liquidity_score = (
                spread_score * 0.4 +      # Spread is most important
                depth_score * 0.3 +       # Depth
                volume_score * 0.3        # Volume
            )
            
            return max(0.0, min(1.0, liquidity_score))
            
        except Exception as exc:
            logger.debug(f"⚠️ Liquidity calculation failed: {exc}")
            return None
    
    def estimate_market_cap_category(self, market_data: OKXMarketData) -> str:
        """Estimate market cap category from volume.
        
        Args:
            market_data: OKXMarketData instance
            
        Returns:
            Category: "large", "mid", "small", "micro", or "nano"
        """
        try:
            volume = market_data.volume_24h
            
            # Estimate based on 24h volume (rough proxy for market cap)
            if volume > 100_000_000:  # $100M+ volume
                return "large"
            elif volume > 10_000_000:  # $10M+ volume
                return "mid"
            elif volume > 1_000_000:  # $1M+ volume
                return "small"
            elif volume > 100_000:  # $100K+ volume
                return "micro"
            else:
                return "nano"
                
        except Exception:
            return "micro"  # Default
    
    def estimate_volatility(self, market_data: OKXMarketData) -> str:
        """Estimate volatility from price range.
        
        Args:
            market_data: OKXMarketData instance
            
        Returns:
            Volatility: "low", "medium", "high", or "very_high"
        """
        try:
            if market_data.high_24h <= 0 or market_data.low_24h <= 0:
                return "medium"  # Default
            
            volatility = (market_data.high_24h - market_data.low_24h) / market_data.price
            
            if volatility < 0.02:  # < 2%
                return "low"
            elif volatility < 0.08:  # < 8%
                return "medium"
            elif volatility < 0.20:  # < 20%
                return "high"
            else:
                return "very_high"
                
        except Exception:
            return "medium"  # Default
