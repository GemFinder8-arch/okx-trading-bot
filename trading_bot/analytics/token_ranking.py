"""Ranking engine to surface promising crypto tokens."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List

from trading_bot.analytics.macro import MacroDataProvider, OnChainDataProvider
from trading_bot.connectors.okx import OkxConnector

logger = logging.getLogger(__name__)


@dataclass
class TokenScore:
    symbol: str
    liquidity_score: float
    momentum_score: float
    macro_sentiment: float
    onchain_strength: float
    volatility_score: float = 0.0
    trend_strength: float = 0.0
    risk_score: float = 0.5  # Lower = less risky

    @property
    def total(self) -> float:
        """Calculate total score with dynamic weighting."""
        return self._calculate_weighted_score()
    
    def _calculate_weighted_score(self, market_regime: str = "neutral") -> float:
        """Calculate score with real data only - skip if CRITICAL scores are None."""
        
        # CRITICAL FIX #1: Check if CRITICAL scores are REAL (not None)
        # These are essential for trading decisions
        critical_scores = [
            self.liquidity_score,      # CRITICAL: Need real liquidity
            self.momentum_score,       # CRITICAL: Need real momentum
            self.volatility_score,     # CRITICAL: Need real volatility
        ]
        
        # Skip symbol only if critical scores are missing
        if any(score is None for score in critical_scores):
            logger.debug("⚠️ SKIPPING %s: Missing critical real data", self.symbol)
            return None  # Skip this symbol - no critical real data
        
        # Use defaults for non-critical scores if missing
        macro_sentiment = self.macro_sentiment if self.macro_sentiment is not None else 0.5
        onchain_strength = self.onchain_strength if self.onchain_strength is not None else 0.5
        trend_strength = self.trend_strength if self.trend_strength is not None else 0.5
        risk_score = self.risk_score if self.risk_score is not None else 0.5
        
        # All scores are real - proceed with calculation
        # Base weights
        weights = {
            "liquidity": 0.25,
            "momentum": 0.30,
            "sentiment": 0.15,
            "onchain": 0.10,
            "volatility": 0.10,
            "trend": 0.10
        }
        
        # Adjust weights based on market regime (from REAL market data)
        if market_regime == "trending":
            weights["momentum"] += 0.10
            weights["trend"] += 0.10
            weights["liquidity"] -= 0.10
            weights["sentiment"] -= 0.10
        elif market_regime == "volatile":
            weights["liquidity"] += 0.15
            weights["volatility"] += 0.10
            weights["momentum"] -= 0.15
            weights["trend"] -= 0.10
        elif market_regime == "ranging":
            weights["sentiment"] += 0.10
            weights["volatility"] += 0.05
            weights["momentum"] -= 0.10
            weights["trend"] -= 0.05
        
        # Risk adjustment - penalize high-risk tokens
        risk_adjustment = 1.0 - (risk_score - 0.5) * 0.3
        
        base_score = (
            self.liquidity_score * weights["liquidity"]
            + self.momentum_score * weights["momentum"]
            + macro_sentiment * weights["sentiment"]
            + onchain_strength * weights["onchain"]
            + self.volatility_score * weights["volatility"]
            + trend_strength * weights["trend"]
        )
        
        return base_score * risk_adjustment


class TokenRankingEngine:
    """Combine multiple signals to rank tradable tokens."""

    def __init__(
        self,
        okx: OkxConnector,
        macro_provider: MacroDataProvider,
        onchain_provider: OnChainDataProvider,
    ) -> None:
        self._okx = okx
        self._macro = macro_provider
        self._onchain = onchain_provider
        
        # Track previous scores for change tracking (no caching - fresh analysis every loop)
        self._previous_scores = {}

    def rank(self, symbols: Iterable[str], top_n: int = 10, min_liquidity: float = 0.3) -> List[TokenScore]:
        symbols = [s for s in symbols if s not in getattr(self._onchain, "restricted_symbols", set())]
        
        # REAL LIVE ANALYSIS: No caching - fresh token ranking every loop
        logger.info("🔄 FRESH TOKEN RANKING ANALYSIS - Analyzing all symbols in real-time")
        
        # Detect market regime from REAL data
        market_regime = self._detect_market_regime(symbols)
        logger.info("Market regime detected from real data: %s", market_regime)
        
        scores: list[TokenScore] = []
        macro_events = list(self._macro.latest_events(limit=50))
        macro_map = self._sentiment_from_macro(macro_events)

        for symbol in symbols:
            try:
                ticker = self._okx.fetch_ticker(symbol)
                book = self._okx.fetch_order_book(symbol, limit=20)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping %s due to market data error: %s", symbol, exc)
                continue

            # Enhanced scoring with new components
            liquidity_score = self._liquidity_score(book, ticker)
            momentum_score = self._momentum_score(ticker)
            volatility_score = self._calculate_volatility_score(ticker)
            trend_strength = self._calculate_trend_strength(ticker)
            risk_score = self._calculate_risk_score(ticker, book)
            
            # Enhanced macro sentiment calculation
            base_symbol = symbol.split("/")[0].lower()
            macro_score = macro_map.get(base_symbol, macro_map.get('market', 0.5))
            
            # MEDIUM FIX #8: Apply sentiment adjustments based on REAL momentum ranges
            if momentum_score is not None:
                if momentum_score > 0.6:  # Strong real positive momentum
                    macro_score = min(0.9, macro_score + 0.15)  # Boost based on real data
                elif momentum_score < 0.4:  # Weak real momentum
                    macro_score = max(0.1, macro_score - 0.15)  # Reduce based on real data

            onchain_metrics = self._onchain.latest_metrics(symbol, limit=1)
            onchain_score = self._onchain_score(onchain_metrics)

            token = TokenScore(
                symbol=symbol,
                liquidity_score=liquidity_score,
                momentum_score=momentum_score,
                macro_sentiment=macro_score,
                onchain_strength=onchain_score,
                volatility_score=volatility_score,
                trend_strength=trend_strength,
                risk_score=risk_score,
            )
            
            # ENHANCEMENT #4: Validate all scores are REAL (not None)
            if token.total is None:
                logger.debug("Skipping %s: No real data available", symbol)
                continue
            
            # ENHANCEMENT #6: Filter by minimum REAL liquidity
            if liquidity_score is None:
                logger.debug("Skipping %s: No real liquidity data", symbol)
                continue
            
            if liquidity_score < min_liquidity:
                logger.debug("Skipping %s: Real liquidity %.2f < threshold %.2f",
                           symbol, liquidity_score, min_liquidity)
                continue
            
            # ENHANCEMENT #3: Log scoring breakdown for transparency
            logger.debug("Score breakdown for %s: L:%.2f M:%.2f S:%.2f O:%.2f V:%.2f T:%.2f Risk:%.2f Total:%.3f",
                        symbol,
                        liquidity_score or 0.0,
                        momentum_score or 0.0,
                        macro_score or 0.0,
                        onchain_score or 0.0,
                        volatility_score or 0.0,
                        trend_strength or 0.0,
                        risk_score or 0.0,
                        token.total or 0.0)
            
            scores.append(token)

        # Sort by total score
        scores.sort(key=lambda token: token.total, reverse=True)
        
        # ENHANCEMENT #2: Track REAL ranking changes
        ranking_changes = []
        for score in scores[:top_n]:
            if score.symbol in self._previous_scores:
                old_score = self._previous_scores[score.symbol]
                change = score.total - old_score
                
                if abs(change) > 0.1:  # Significant REAL change
                    ranking_changes.append((score.symbol, old_score, score.total, change))
        
        if ranking_changes:
            logger.warning("⚠️ SIGNIFICANT RANKING CHANGES (based on real data):")
            for symbol, old, new, change in ranking_changes:
                direction = "↑" if change > 0 else "↓"
                logger.warning("  %s %s: %.3f → %.3f (Δ%.3f)", 
                             direction, symbol, old, new, change)
        
        # Store for next iteration (for change tracking only)
        self._previous_scores = {s.symbol: s.total for s in scores}
        
        # Log top 5 with scoring breakdown
        logger.info("🏆 TOP 5 TOKEN SCORES (based on real data):")
        for i, token in enumerate(scores[:5], 1):
            logger.info(
                "%d. %s: %.3f | L:%.2f M:%.2f S:%.2f O:%.2f V:%.2f T:%.2f Risk:%.2f",
                i, token.symbol, token.total,
                token.liquidity_score or 0.0,
                token.momentum_score or 0.0,
                token.macro_sentiment or 0.0,
                token.onchain_strength or 0.0,
                token.volatility_score or 0.0,
                token.trend_strength or 0.0,
                token.risk_score or 0.0
            )
        
        # NO CACHING - Return fresh analysis
        return scores[:top_n]

    def _liquidity_score(self, order_book: dict, ticker: dict) -> float:
        """Enhanced liquidity scoring with spread analysis and market depth quality."""
        try:
            # Validate order book structure
            if not isinstance(order_book, dict):
                logger.debug("⚠️ Order book is not a dict - SKIPPING")
                return None
            
            bids = order_book.get("bids", [])[:10]  # Look deeper into order book
            asks = order_book.get("asks", [])[:10]
            
            if not bids or not asks:
                logger.debug("⚠️ No bids or asks for liquidity calculation - SKIPPING")
                return None  # No real liquidity data
            
            # Validate bid/ask structure (each should be [price, volume])
            if not all(isinstance(b, (list, tuple)) and len(b) >= 2 for b in bids):
                logger.debug("⚠️ Malformed bid data - SKIPPING")
                return None
            
            if not all(isinstance(a, (list, tuple)) and len(a) >= 2 for a in asks):
                logger.debug("⚠️ Malformed ask data - SKIPPING")
                return None
            
            # Current price for spread calculation
            current_price = float(ticker.get("last", 0))
            if current_price <= 0:
                logger.debug("⚠️ Invalid current price for liquidity - SKIPPING")
                return None  # No valid price data
            
            # Best bid/ask for spread calculation
            try:
                best_bid = float(bids[0][0])
                best_ask = float(asks[0][0])
            except (ValueError, TypeError, IndexError):
                logger.debug("⚠️ Cannot parse best bid/ask - SKIPPING")
                return None
            
            # Validate bid/ask prices
            if best_bid <= 0 or best_ask <= 0 or best_bid >= best_ask:
                logger.debug("⚠️ Invalid bid/ask prices for liquidity - SKIPPING")
                return None  # Invalid price data
            
            # Spread analysis (lower spread = higher liquidity)
            spread = (best_ask - best_bid) / current_price
            spread_score = max(0.0, 1.0 - spread * 100)  # Penalize spreads > 1%
            
            # Market depth analysis - with safe extraction
            bid_volume = 0.0
            for level in bids:
                try:
                    bid_volume += float(level[1])
                except (ValueError, TypeError, IndexError):
                    continue
            
            ask_volume = 0.0
            for level in asks:
                try:
                    ask_volume += float(level[1])
                except (ValueError, TypeError, IndexError):
                    continue
            
            total_depth = bid_volume + ask_volume
            
            if total_depth <= 0:
                logger.debug("⚠️ Zero depth for liquidity - SKIPPING")
                return None  # No real depth data
            
            # Normalize depth (use USD value, not token count)
            # Convert to USD value for fair comparison across different price levels
            # Each bid level at its price, each ask level at its price
            bid_depth_usd = 0.0
            for level in bids:
                try:
                    bid_depth_usd += float(level[1]) * float(level[0])
                except (ValueError, TypeError, IndexError):
                    continue
            
            ask_depth_usd = 0.0
            for level in asks:
                try:
                    ask_depth_usd += float(level[1]) * float(level[0])
                except (ValueError, TypeError, IndexError):
                    continue
            
            total_depth_usd = bid_depth_usd + ask_depth_usd
            depth_score = min(total_depth_usd / 10000.0, 1.0)  # $10k depth = max score
            
            # Order book balance (closer to 1.0 = more balanced)
            if bid_volume > 0 and ask_volume > 0:
                balance = min(bid_volume, ask_volume) / max(bid_volume, ask_volume)
                balance_score = max(0.0, min(1.0, balance))  # Clamp to [0, 1]
            else:
                balance_score = 0.0
            
            # Price impact estimation (how much price moves with $1000 trade)
            impact_threshold = 1000.0  # $1000 trade size
            cumulative_volume = 0.0
            price_impact = 0.0
            
            for level in asks:
                try:
                    price_val = float(level[0])
                    volume_val = float(level[1]) * price_val
                    cumulative_volume += volume_val
                    if cumulative_volume >= impact_threshold:
                        price_impact = abs((price_val - best_ask) / best_ask)  # Use absolute value
                        break
                except (ValueError, TypeError, IndexError, ZeroDivisionError):
                    continue
            
            # If we didn't reach threshold, use last price as impact
            if cumulative_volume < impact_threshold and asks:
                try:
                    last_ask = float(asks[-1][0])
                    price_impact = abs((last_ask - best_ask) / best_ask)
                except (ValueError, TypeError, IndexError, ZeroDivisionError):
                    price_impact = 0.0
            
            impact_score = max(0.0, 1.0 - price_impact * 100)  # Penalize high impact
            
            # Combined liquidity score with weights
            liquidity_score = (
                spread_score * 0.4 +      # Spread is most important
                depth_score * 0.3 +       # Total depth
                balance_score * 0.2 +     # Order book balance
                impact_score * 0.1        # Price impact
            )
            
            logger.debug("Liquidity score for %s: %.3f (spread=%.3f, depth=%.3f, balance=%.3f, impact=%.3f)",
                        ticker.get("symbol", ""), liquidity_score, spread_score, depth_score, balance_score, impact_score)
            
            return max(0.0, min(1.0, liquidity_score))
            
        except Exception as exc:
            logger.debug("⚠️ LIQUIDITY CALCULATION FAILED - SKIPPING symbol: %s", exc)
            return None  # MEDIUM FIX #6: Skip - no real liquidity data available

    def _momentum_score(self, ticker: dict) -> float:
        """Enhanced momentum scoring with multiple timeframe consideration."""
        price_change = ticker.get("percentage", 0.0)
        volume = ticker.get("baseVolume", 0.0)
        
        # Normalize price change (more adaptive scaling)
        if abs(price_change) > 20:  # Extreme moves
            normalized = 1.0 if price_change > 0 else -1.0
        else:
            normalized = price_change / 20.0  # Scale to ±1.0 for ±20% moves
        
        # Volume momentum (relative to average)
        volume_boost = min(volume / 10000.0, 1.0)  # Adjusted threshold
        
        # MEDIUM FIX #7: Allow negative momentum for real bearish data
        momentum = normalized * 0.8 + volume_boost * 0.2
        import numpy as np
        return np.clip(momentum, -1.0, 1.0)  # Allow negative for real bearish momentum
    
    def _calculate_volatility_score(self, ticker: dict) -> float:
        """Calculate volatility score - ONLY with real data."""
        try:
            high = float(ticker.get("high", 0))
            low = float(ticker.get("low", 0))
            close = float(ticker.get("last", 0))
            
            # CRITICAL FIX #2: Check if we have REAL data (not zeros/missing)
            if close <= 0 or high <= 0 or low <= 0:
                logger.debug("⚠️ INVALID PRICE DATA for volatility - SKIPPING symbol")
                return None  # Skip - no real data
            
            # Check if high >= low (sanity check for real data)
            if high < low:
                logger.debug("⚠️ INVALID PRICE RANGE for volatility - SKIPPING symbol")
                return None  # Skip - data doesn't make sense
            
            # Calculate with REAL data
            daily_volatility = (high - low) / close
            
            # Sweet spot: 2-8% daily volatility
            if 0.02 <= daily_volatility <= 0.08:
                return 1.0
            elif 0.01 <= daily_volatility <= 0.15:
                # Linear decay outside sweet spot
                if daily_volatility < 0.02:
                    return 0.5 + (daily_volatility - 0.01) / 0.01 * 0.5
                else:
                    return 1.0 - (daily_volatility - 0.08) / 0.07 * 0.5
            else:
                return 0.1  # Too low or too high - still real data, just poor score
                
        except (ValueError, TypeError) as exc:
            logger.debug("⚠️ VOLATILITY CALCULATION FAILED - SKIPPING: %s", exc)
            return None  # Skip - can't calculate with real data
    
    def _calculate_trend_strength(self, ticker: dict) -> float:
        """Calculate trend strength - ONLY with real data."""
        try:
            open_price = float(ticker.get("open", 0))
            close_price = float(ticker.get("last", 0))
            high = float(ticker.get("high", 0))
            low = float(ticker.get("low", 0))
            
            # CRITICAL FIX #3: Check if we have REAL data (not zeros/missing)
            if not all([open_price, close_price, high, low]):
                logger.debug("⚠️ MISSING PRICE DATA for trend strength - SKIPPING symbol")
                return None  # Skip - no real data
            
            # Check if data makes sense
            if high < low or high < open_price or high < close_price:
                logger.debug("⚠️ INVALID PRICE RELATIONSHIP for trend - SKIPPING symbol")
                return None  # Skip - data doesn't make sense
            
            # Calculate with REAL data
            price_change = (close_price - open_price) / open_price
            
            # Body vs shadow ratio (strong trends have large bodies)
            body_size = abs(close_price - open_price)
            total_range = high - low
            
            if total_range > 0:
                body_ratio = body_size / total_range
            else:
                logger.debug("⚠️ ZERO PRICE RANGE for trend - SKIPPING symbol")
                return None  # Skip - no real movement
            
            # Trend strength combines direction and conviction
            if price_change > 0:  # Uptrend
                trend_strength = min(price_change * 10, 1.0) * body_ratio
            else:  # Downtrend - less favorable for long-only
                trend_strength = 0.3 * body_ratio
            
            return max(0.0, min(1.0, trend_strength))
            
        except (ValueError, TypeError) as exc:
            logger.debug("⚠️ TREND CALCULATION FAILED - SKIPPING: %s", exc)
            return None  # Skip - can't calculate with real data
    
    def _calculate_risk_score(self, ticker: dict, order_book: dict) -> float:
        """Calculate risk score - ONLY with real data."""
        try:
            # CRITICAL FIX #4: Get volatility risk from REAL data
            volatility_score = self._calculate_volatility_score(ticker)
            if volatility_score is None:
                logger.debug("⚠️ NO REAL VOLATILITY DATA for risk - SKIPPING symbol")
                return None  # Skip - can't calculate risk without real volatility
            
            volatility_risk = 1.0 - volatility_score
            
            # Get liquidity risk from REAL data
            liquidity = self._liquidity_score(order_book, ticker)
            if liquidity is None:
                logger.debug("⚠️ NO REAL LIQUIDITY DATA for risk - SKIPPING symbol")
                return None  # Skip - can't calculate risk without real liquidity
            
            liquidity_risk = 1.0 - liquidity
            
            # Asset type risk - based on REAL symbol characteristics
            symbol = ticker.get("symbol", "")
            base_symbol = symbol.split("/")[0] if "/" in symbol else symbol
            
            # ONLY use real asset categories (no fake/guessed categories)
            if base_symbol in ["BTC", "ETH", "BNB", "SOL", "ADA", "DOT"]:
                asset_risk = 0.1  # Real major assets
            elif base_symbol in ["USDT", "USDC", "BUSD", "DAI", "TUSD"]:
                asset_risk = 0.05  # Real stablecoins
            elif base_symbol in ["DOGE", "SHIB", "PEPE", "FLOKI", "TRUMP"]:
                asset_risk = 0.6  # Real meme coins
            else:
                # Unknown asset - don't guess, skip it
                logger.debug("⚠️ UNKNOWN ASSET TYPE for risk - SKIPPING symbol: %s", base_symbol)
                return None  # Skip - can't determine real risk category
            
            # Calculate risk with REAL data
            risk_score = (
                volatility_risk * 0.4 +
                liquidity_risk * 0.4 +
                asset_risk * 0.2
            )
            
            return max(0.0, min(1.0, risk_score))
            
        except (ValueError, TypeError) as exc:
            logger.debug("⚠️ RISK CALCULATION FAILED - SKIPPING: %s", exc)
            return None  # Skip - can't calculate with real data

    def _sentiment_from_macro(self, events) -> dict[str, float]:
        """Calculate sentiment scores from macro events with enhanced logic."""
        sentiment = {}
        
        # If no events, return neutral sentiment for all symbols
        if not events:
            return {}
        
        # Process macro events to extract sentiment
        for event in events:
            try:
                # Extract symbol from event description or title
                description = event.description.lower() if hasattr(event, 'description') else str(event).lower()
                
                # Look for crypto-related keywords and sentiment indicators
                bullish_keywords = ['bullish', 'pump', 'moon', 'rally', 'surge', 'breakout', 'buy', 'long', 'up', 'green', 'gain']
                bearish_keywords = ['bearish', 'dump', 'crash', 'drop', 'fall', 'sell', 'short', 'down', 'red', 'loss']
                
                # Calculate sentiment score based on keywords
                bullish_count = sum(1 for word in bullish_keywords if word in description)
                bearish_count = sum(1 for word in bearish_keywords if word in description)
                
                # Base sentiment calculation
                if bullish_count > bearish_count:
                    base_sentiment = 0.6 + min(0.3, (bullish_count - bearish_count) * 0.1)
                elif bearish_count > bullish_count:
                    base_sentiment = 0.4 - min(0.3, (bearish_count - bullish_count) * 0.1)
                else:
                    base_sentiment = 0.5
                
                # Apply importance weighting
                importance_weight = 1.0
                if hasattr(event, 'importance'):
                    if event.importance == "high":
                        importance_weight = 1.2
                    elif event.importance == "low":
                        importance_weight = 0.8
                
                # Apply impact adjustment
                if hasattr(event, 'impact'):
                    if event.impact == "negative":
                        base_sentiment = max(0.1, base_sentiment - 0.2)
                    elif event.impact == "positive":
                        base_sentiment = min(0.9, base_sentiment + 0.2)
                
                # Store sentiment for general market (affects all symbols)
                sentiment['market'] = base_sentiment * importance_weight
                
            except Exception as exc:
                logger.debug("Error processing macro event: %s", exc)
                continue
        
        return sentiment

    def _onchain_score(self, metrics: Iterable) -> float:
        """Calculate on-chain strength - ONLY with real data."""
        metric_list = list(metrics)
        
        # CRITICAL FIX #5: No metrics = no real data
        if not metric_list:
            logger.debug("⚠️ NO REAL ONCHAIN METRICS - SKIPPING symbol")
            return None  # Skip - no real data available
        
        score = 0.0
        volume_score = 0.0
        volatility_score = 0.0
        metrics_found = 0
        
        try:
            for metric in metric_list:
                # Only process metrics with REAL values
                if metric.value is None or metric.value <= 0:
                    continue  # Skip invalid metrics
                
                metrics_found += 1
                
                # Volume-based scoring with REAL data
                if metric.name == "base_volume_24h":
                    if metric.value > 1000000:
                        volume_score += 0.3
                    elif metric.value > 100000:
                        volume_score += 0.2
                    elif metric.value > 10000:
                        volume_score += 0.1
                
                elif metric.name == "quote_volume_24h":
                    if metric.value > 10000000:
                        volume_score += 0.2
                    elif metric.value > 1000000:
                        volume_score += 0.1
                
                elif metric.name == "volatility_24h":
                    if 0.02 <= metric.value <= 0.08:
                        volatility_score += 0.2
                    elif 0.01 <= metric.value <= 0.15:
                        volatility_score += 0.1
                
                elif metric.name == "market_cap" and metric.value > 1e8:
                    score += 0.1
                elif metric.name == "price" and metric.value > 1:
                    score += 0.05
            
            # If no real metrics found, skip
            if metrics_found == 0:
                logger.debug("⚠️ NO VALID ONCHAIN METRICS - SKIPPING symbol")
                return None  # Skip - no real data
            
            # Combine scores with REAL data
            final_score = score + (volume_score * 0.6) + (volatility_score * 0.4)
            
            # Normalize to 0.0-1.0 range
            final_score = max(0.0, min(1.0, final_score))
            
            logger.debug("OnChain score calculated: %.3f (base=%.3f, volume=%.3f, volatility=%.3f)", 
                        final_score, score, volume_score, volatility_score)
            
            return final_score
            
        except Exception as exc:
            logger.debug("⚠️ ONCHAIN CALCULATION FAILED - SKIPPING: %s", exc)
            return None  # Skip - can't calculate with real data
    
    def _detect_market_regime(self, symbols: Iterable[str]) -> str:
        """ENHANCEMENT #5: Detect market regime from REAL price data."""
        try:
            import numpy as np
            
            # Use REAL data from major assets
            major_symbols = [s for s in symbols 
                            if any(m in s for m in ['BTC', 'ETH', 'SOL'])]
            
            if not major_symbols:
                logger.debug("No major assets for regime detection - using neutral")
                return "neutral"
            
            # Calculate REAL momentum from actual price changes
            total_momentum = 0
            valid_count = 0
            
            for symbol in major_symbols[:3]:
                try:
                    ticker = self._okx.fetch_ticker(symbol)
                    percentage = ticker.get("percentage")
                    
                    if percentage is not None:
                        total_momentum += percentage
                        valid_count += 1
                except Exception:
                    continue
            
            if valid_count == 0:
                logger.debug("No valid price data for regime detection - using neutral")
                return "neutral"
            
            # Detect regime from REAL average momentum
            avg_momentum = total_momentum / valid_count
            
            if avg_momentum > 5:
                logger.info("Trending market detected (real momentum: +%.2f%%)", avg_momentum)
                return "trending"
            elif avg_momentum < -5:
                logger.info("Trending market detected (real momentum: %.2f%%)", avg_momentum)
                return "trending"
            elif abs(avg_momentum) > 2:
                logger.info("Volatile market detected (real momentum: %.2f%%)", avg_momentum)
                return "volatile"
            else:
                logger.info("Ranging market detected (real momentum: %.2f%%)", avg_momentum)
                return "ranging"
                
        except Exception as exc:
            logger.debug("Failed to detect market regime from real data: %s", exc)
            return "neutral"
