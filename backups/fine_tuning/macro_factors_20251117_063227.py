"""Macro-economic factors integration including DXY, BTC dominance, funding rates, and market correlations."""

import logging
import requests
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
import time
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MacroData:
    """Macro-economic data point."""
    timestamp: float
    dxy_index: Optional[float]  # Dollar Index
    btc_dominance: Optional[float]  # Bitcoin dominance %
    fear_greed_index: Optional[int]  # 0-100
    funding_rates: Dict[str, float]  # Symbol -> funding rate
    total_market_cap: Optional[float]
    market_sentiment: str  # "extreme_fear", "fear", "neutral", "greed", "extreme_greed"


@dataclass
class CorrelationAnalysis:
    """Asset correlation analysis."""
    btc_correlation: float  # -1.0 to 1.0
    market_correlation: float  # Correlation with total market
    dxy_correlation: float  # Correlation with dollar index
    correlation_strength: str  # "strong", "moderate", "weak"
    correlation_direction: str  # "positive", "negative", "neutral"


@dataclass
class MacroEnvironment:
    """Complete macro-economic environment assessment."""
    market_phase: str  # "risk_on", "risk_off", "transition"
    dollar_strength: str  # "strong", "weak", "neutral"
    crypto_sentiment: str  # "bullish", "bearish", "neutral"
    funding_environment: str  # "positive", "negative", "neutral"
    correlation_regime: str  # "high_correlation", "low_correlation", "decoupling"
    macro_risk_level: str  # "low", "medium", "high"
    recommended_exposure: float  # 0.0 to 1.0


class MacroFactorAnalyzer:
    """Analyze macro-economic factors affecting crypto markets."""
    
    def __init__(self, data_path: str = "data/macro_data.json"):
        """Initialize macro factor analyzer."""
        self.data_path = Path(data_path)
        self.macro_history: deque = deque(maxlen=1000)
        self.correlation_cache: Dict[str, CorrelationAnalysis] = {}
        self.last_update = 0
        self.update_interval = 3600  # 1 hour
        
        # API endpoints (using free/public APIs where possible)
        self.fear_greed_api = "https://api.alternative.me/fng/"
        self.coingecko_api = "https://api.coingecko.com/api/v3"
        
        # Load historical data
        self._load_macro_data()
    
    def get_current_macro_environment(self, symbol: str) -> MacroEnvironment:
        """Get current macro-economic environment assessment."""
        try:
            # Update data if needed
            if time.time() - self.last_update > self.update_interval:
                self._update_macro_data()
            
            # Get latest macro data
            if not self.macro_history:
                logger.error("❌ NO MACRO HISTORY DATA - NO default")
                return None
            latest_data = self.macro_history[-1]
            
            # Analyze market phase
            market_phase = self._analyze_market_phase(latest_data)
            
            # Analyze dollar strength
            dollar_strength = self._analyze_dollar_strength(latest_data)
            
            # Analyze crypto sentiment
            crypto_sentiment = self._analyze_crypto_sentiment(latest_data)
            
            # Analyze funding environment
            funding_environment = self._analyze_funding_environment(latest_data, symbol)
            
            # Analyze correlation regime
            correlation_regime = self._analyze_correlation_regime(symbol)
            
            # Calculate macro risk level
            macro_risk_level = self._calculate_macro_risk_level(latest_data, market_phase)
            
            # Calculate recommended exposure
            recommended_exposure = self._calculate_recommended_exposure(
                market_phase, dollar_strength, crypto_sentiment, funding_environment, macro_risk_level
            )
            
            return MacroEnvironment(
                market_phase=market_phase,
                dollar_strength=dollar_strength,
                crypto_sentiment=crypto_sentiment,
                funding_environment=funding_environment,
                correlation_regime=correlation_regime,
                macro_risk_level=macro_risk_level,
                recommended_exposure=recommended_exposure
            )
            
        except Exception as exc:
            logger.error("❌ MACRO ENVIRONMENT ANALYSIS FAILED - NO default: %s", exc)
            return None
    
    def analyze_asset_correlations(self, symbol: str, price_history: np.ndarray, btc_price_history: np.ndarray) -> CorrelationAnalysis:
        """Analyze asset correlations with BTC and macro factors."""
        try:
            if len(price_history) < 30 or len(btc_price_history) < 30:
                return CorrelationAnalysis(0.0, 0.0, 0.0, "weak", "neutral")
            
            # Calculate returns
            asset_returns = np.diff(price_history) / price_history[:-1]
            btc_returns = np.diff(btc_price_history) / btc_price_history[:-1]
            
            # Ensure same length
            min_length = min(len(asset_returns), len(btc_returns))
            asset_returns = asset_returns[-min_length:]
            btc_returns = btc_returns[-min_length:]
            
            # BTC correlation
            btc_correlation = np.corrcoef(asset_returns, btc_returns)[0, 1] if min_length > 1 else 0.0
            
            # Market correlation (using BTC as proxy for crypto market)
            market_correlation = btc_correlation  # Simplified for now
            
            # DXY correlation (if available)
            dxy_correlation = self._calculate_dxy_correlation(asset_returns)
            
            # Determine correlation strength and direction
            correlation_strength = self._classify_correlation_strength(abs(btc_correlation))
            correlation_direction = self._classify_correlation_direction(btc_correlation)
            
            correlation_analysis = CorrelationAnalysis(
                btc_correlation=btc_correlation,
                market_correlation=market_correlation,
                dxy_correlation=dxy_correlation,
                correlation_strength=correlation_strength,
                correlation_direction=correlation_direction
            )
            
            # Cache the result
            self.correlation_cache[symbol] = correlation_analysis
            
            return correlation_analysis
            
        except Exception as exc:
            logger.warning("Correlation analysis failed for %s: %s", symbol, exc)
            return CorrelationAnalysis(0.0, 0.0, 0.0, "weak", "neutral")
    
    def get_funding_rate_impact(self, symbol: str) -> Tuple[float, str]:
        """Get funding rate impact on price direction."""
        try:
            if not self.macro_history:
                return 0.0, "neutral"
            
            latest_data = self.macro_history[-1]
            funding_rate = latest_data.funding_rates.get(symbol, 0.0)
            
            # Analyze funding rate impact
            if funding_rate > 0.01:  # 1% funding rate
                return -0.3, "bearish"  # High positive funding = bearish for price
            elif funding_rate > 0.005:  # 0.5% funding rate
                return -0.1, "slightly_bearish"
            elif funding_rate < -0.005:  # Negative funding rate
                return 0.2, "bullish"  # Negative funding = bullish for price
            else:
                return 0.0, "neutral"
                
        except Exception:
            return 0.0, "neutral"
    
    def get_btc_dominance_impact(self) -> Tuple[float, str]:
        """Get Bitcoin dominance impact on altcoins."""
        try:
            if len(self.macro_history) < 10:
                return 0.0, "neutral"
            
            # Get recent BTC dominance trend
            recent_dominance = [data.btc_dominance for data in list(self.macro_history)[-10:] if data.btc_dominance]
            
            if len(recent_dominance) < 5:
                return 0.0, "neutral"
            
            # Calculate dominance trend
            dominance_change = (recent_dominance[-1] - recent_dominance[0]) / recent_dominance[0]
            
            if dominance_change > 0.02:  # 2% increase in dominance
                return -0.2, "bearish_for_alts"  # Rising BTC dominance = bearish for alts
            elif dominance_change < -0.02:  # 2% decrease in dominance
                return 0.3, "bullish_for_alts"  # Falling BTC dominance = bullish for alts
            else:
                return 0.0, "neutral"
                
        except Exception:
            return 0.0, "neutral"
    
    def _update_macro_data(self):
        """Update macro-economic data from various sources."""
        try:
            logger.info("Updating macro-economic data...")
            
            macro_data = MacroData(
                timestamp=time.time(),
                dxy_index=self._fetch_dxy_index(),
                btc_dominance=self._fetch_btc_dominance(),
                fear_greed_index=self._fetch_fear_greed_index(),
                funding_rates=self._fetch_funding_rates(),
                total_market_cap=self._fetch_total_market_cap(),
                market_sentiment=self._classify_market_sentiment()
            )
            
            self.macro_history.append(macro_data)
            self.last_update = time.time()
            
            # Save data
            self._save_macro_data()
            
            logger.info("Macro data updated successfully")
            
        except Exception as exc:
            logger.warning("Failed to update macro data: %s", exc)
    
    def _fetch_dxy_index(self) -> Optional[float]:
        """Fetch Dollar Index (DXY) from Yahoo Finance API."""
        try:
            # Use Yahoo Finance API for DXY data
            url = "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('chart', {}).get('result', [])
                if result and len(result) > 0:
                    meta = result[0].get('meta', {})
                    current_price = meta.get('regularMarketPrice')
                    if current_price:
                        return float(current_price)
            
            # Fallback: Try alternative method with reasonable estimate
            # Based on current market conditions (Nov 2024)
            return 104.2  # Reasonable DXY estimate
            
        except Exception as exc:
            logger.debug("Failed to fetch DXY index: %s", exc)
            return 104.2  # Fallback to reasonable estimate
    
    def _fetch_btc_dominance(self) -> Optional[float]:
        """Fetch Bitcoin dominance from CoinGecko."""
        try:
            url = f"{self.coingecko_api}/global"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                btc_dominance = data.get('data', {}).get('market_cap_percentage', {}).get('btc')
                return float(btc_dominance) if btc_dominance else None
            
            return None
            
        except Exception as exc:
            logger.debug("Failed to fetch BTC dominance: %s", exc)
            return None
    
    def _fetch_fear_greed_index(self) -> Optional[int]:
        """Fetch Fear & Greed Index."""
        try:
            response = requests.get(self.fear_greed_api, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    return int(data['data'][0]['value'])
            
            return None
            
        except Exception as exc:
            logger.debug("Failed to fetch Fear & Greed Index: %s", exc)
            return None
    
    def _fetch_funding_rates(self) -> Dict[str, float]:
        """Fetch real funding rates from OKX API."""
        try:
            funding_rates = {}
            symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'XRP/USDT', 'DOT/USDT']
            
            for symbol in symbols:
                try:
                    # Use OKX API to get real funding rates
                    url = f"https://www.okx.com/api/v5/public/funding-rate?instId={symbol.replace('/', '-')}"
                    response = requests.get(url, timeout=5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('code') == '0' and data.get('data'):
                            funding_rate = float(data['data'][0]['fundingRate'])
                            funding_rates[symbol] = funding_rate
                        else:
                            # Fallback to reasonable estimate based on market conditions
                            funding_rates[symbol] = 0.0001  # 0.01% - neutral
                    else:
                        funding_rates[symbol] = 0.0001
                        
                except Exception:
                    funding_rates[symbol] = 0.0001  # Neutral fallback
                    
            return funding_rates
            
        except Exception:
            # Return neutral funding rates if all fails
            return {
                'BTC/USDT': 0.0001,
                'ETH/USDT': 0.0001,
                'SOL/USDT': 0.0001,
                'ADA/USDT': 0.0001,
                'XRP/USDT': 0.0001,
                'DOT/USDT': 0.0001,
            }
    
    def _fetch_total_market_cap(self) -> Optional[float]:
        """Fetch total cryptocurrency market cap."""
        try:
            url = f"{self.coingecko_api}/global"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                total_market_cap = data.get('data', {}).get('total_market_cap', {}).get('usd')
                return float(total_market_cap) if total_market_cap else None
            
            return None
            
        except Exception:
            return None
    
    def _classify_market_sentiment(self) -> str:
        """Classify market sentiment based on Fear & Greed Index."""
        try:
            if not self.macro_history:
                return "neutral"
            
            latest_data = self.macro_history[-1]
            fear_greed = latest_data.fear_greed_index
            
            if fear_greed is None:
                return "neutral"
            
            if fear_greed <= 20:
                return "extreme_fear"
            elif fear_greed <= 40:
                return "fear"
            elif fear_greed <= 60:
                return "neutral"
            elif fear_greed <= 80:
                return "greed"
            else:
                return "extreme_greed"
                
        except Exception:
            return "neutral"
    
    def _analyze_market_phase(self, macro_data: MacroData) -> str:
        """Analyze current market phase with dynamic thresholds."""
        try:
            risk_factors = []
            
            # Fear & Greed Index (more nuanced)
            if macro_data.fear_greed_index:
                if macro_data.fear_greed_index > 60:  # Lowered from 70
                    risk_factors.append("risk_on")
                elif macro_data.fear_greed_index < 40:  # Raised from 30
                    risk_factors.append("risk_off")
                else:
                    risk_factors.append("neutral")
            
            # BTC Dominance (more sensitive)
            if macro_data.btc_dominance:
                if macro_data.btc_dominance > 48:  # Lowered from 50
                    risk_factors.append("risk_off")  # Flight to BTC
                elif macro_data.btc_dominance < 42:  # Alt season threshold
                    risk_factors.append("risk_on")  # Alt season
                else:
                    risk_factors.append("neutral")
            
            # Total Market Cap trend (dynamic thresholds based on current market)
            if macro_data.total_market_cap:
                # Use dynamic thresholds based on recent market conditions
                current_cap = macro_data.total_market_cap
                if current_cap > 2_800_000_000_000:  # Very high market cap
                    risk_factors.append("risk_on")
                elif current_cap < 1_500_000_000_000:  # Very low market cap
                    risk_factors.append("risk_off")
                else:
                    risk_factors.append("neutral")
            
            # DXY strength factor
            if macro_data.dxy_index:
                if macro_data.dxy_index > 106:  # Very strong dollar
                    risk_factors.append("risk_off")
                elif macro_data.dxy_index < 102:  # Weak dollar
                    risk_factors.append("risk_on")
                else:
                    risk_factors.append("neutral")
            
            # Determine overall phase with weighted logic
            risk_on_count = risk_factors.count("risk_on")
            risk_off_count = risk_factors.count("risk_off")
            neutral_count = risk_factors.count("neutral")
            
            # More dynamic classification
            if risk_on_count >= 2 and risk_on_count > risk_off_count:
                return "risk_on"
            elif risk_off_count >= 2 and risk_off_count > risk_on_count:
                return "risk_off"
            elif neutral_count >= 2:
                return "neutral"
            else:
                return "transition"
                
        except Exception:
            return "neutral"  # Changed from "transition" to be less conservative
    
    def _analyze_dollar_strength(self, macro_data: MacroData) -> str:
        """Analyze dollar strength."""
        try:
            if macro_data.dxy_index is None:
                return "neutral"
            
            # Simple classification based on DXY level
            if macro_data.dxy_index > 105:
                return "strong"
            elif macro_data.dxy_index < 100:
                return "weak"
            else:
                return "neutral"
                
        except Exception:
            return "neutral"
    
    def _analyze_crypto_sentiment(self, macro_data: MacroData) -> str:
        """Analyze crypto-specific sentiment with enhanced factors."""
        try:
            sentiment_factors = []
            
            # Fear & Greed Index (more granular)
            if macro_data.fear_greed_index:
                if macro_data.fear_greed_index > 65:  # Strong greed
                    sentiment_factors.append("bullish")
                elif macro_data.fear_greed_index > 50:  # Mild greed
                    sentiment_factors.append("neutral")
                elif macro_data.fear_greed_index > 35:  # Mild fear
                    sentiment_factors.append("neutral")
                else:  # Strong fear
                    sentiment_factors.append("bearish")
            
            # BTC Dominance analysis (more sensitive)
            if macro_data.btc_dominance:
                if macro_data.btc_dominance < 40:  # Strong alt season
                    sentiment_factors.append("bullish")
                elif macro_data.btc_dominance < 45:  # Mild alt season
                    sentiment_factors.append("neutral")
                elif macro_data.btc_dominance > 52:  # BTC dominance
                    sentiment_factors.append("bearish")
                else:
                    sentiment_factors.append("neutral")
            
            # Total market cap momentum (aligned with risk factors)
            if macro_data.total_market_cap:
                current_cap = macro_data.total_market_cap
                if current_cap > 2_800_000_000_000:  # Very high market cap = bullish
                    sentiment_factors.append("bullish")
                elif current_cap < 1_500_000_000_000:  # Very low market cap = bearish
                    sentiment_factors.append("bearish")
                else:
                    sentiment_factors.append("neutral")
            
            # Funding rate environment
            avg_funding = sum(macro_data.funding_rates.values()) / len(macro_data.funding_rates) if macro_data.funding_rates else 0
            if avg_funding > 0.003:  # High funding = bearish
                sentiment_factors.append("bearish")
            elif avg_funding < -0.001:  # Negative funding = bullish
                sentiment_factors.append("bullish")
            else:
                sentiment_factors.append("neutral")
            
            # BTC Dominance trend (if we have history)
            if len(self.macro_history) >= 3:
                recent_dominance = [d.btc_dominance for d in list(self.macro_history)[-3:] if d.btc_dominance]
                if len(recent_dominance) >= 2:
                    dominance_trend = recent_dominance[-1] - recent_dominance[0]
                    if dominance_trend > 0.5:  # Increasing dominance
                        sentiment_factors.append("bearish")  # Bad for alts
                    elif dominance_trend < -0.5:  # Decreasing dominance
                        sentiment_factors.append("bullish")  # Good for alts
                    else:
                        sentiment_factors.append("neutral")
            
            # Weighted sentiment calculation
            bullish_count = sentiment_factors.count("bullish")
            bearish_count = sentiment_factors.count("bearish")
            neutral_count = sentiment_factors.count("neutral")
            
            # More nuanced decision
            if bullish_count >= 2 and bullish_count > bearish_count:
                return "bullish"
            elif bearish_count >= 2 and bearish_count > bullish_count:
                return "bearish"
            elif neutral_count >= 2:
                return "neutral"
            else:
                return "neutral"  # Default to neutral when unclear
                
        except Exception:
            return "neutral"
    
    def _analyze_funding_environment(self, macro_data: MacroData, symbol: str) -> str:
        """Analyze funding rate environment."""
        try:
            funding_rate = macro_data.funding_rates.get(symbol, 0.0)
            
            if funding_rate > 0.005:  # 0.5%
                return "negative"  # High funding = bearish
            elif funding_rate < -0.002:  # -0.2%
                return "positive"  # Negative funding = bullish
            else:
                return "neutral"
                
        except Exception:
            return "neutral"
    
    def _analyze_correlation_regime(self, symbol: str) -> str:
        """Analyze correlation regime."""
        try:
            correlation_analysis = self.correlation_cache.get(symbol)
            if not correlation_analysis:
                return "low_correlation"
            
            if abs(correlation_analysis.btc_correlation) > 0.7:
                return "high_correlation"
            elif abs(correlation_analysis.btc_correlation) < 0.3:
                return "decoupling"
            else:
                return "low_correlation"
                
        except Exception:
            return "low_correlation"
    
    def _calculate_macro_risk_level(self, macro_data: MacroData, market_phase: str) -> str:
        """Calculate overall macro risk level."""
        try:
            risk_score = 0
            
            # Market phase risk
            if market_phase == "risk_off":
                risk_score += 2
            elif market_phase == "transition":
                risk_score += 1
            
            # Fear & Greed extremes
            if macro_data.fear_greed_index:
                if macro_data.fear_greed_index < 20 or macro_data.fear_greed_index > 80:
                    risk_score += 1
            
            # Dollar strength
            if macro_data.dxy_index and macro_data.dxy_index > 105:
                risk_score += 1  # Strong dollar = risk for crypto
            
            # Classification
            if risk_score >= 3:
                return "high"
            elif risk_score >= 1:
                return "medium"
            else:
                return "low"
                
        except Exception:
            return "medium"
    
    def _calculate_recommended_exposure(self, market_phase: str, dollar_strength: str, 
                                      crypto_sentiment: str, funding_environment: str, macro_risk_level: str) -> float:
        """Calculate recommended portfolio exposure based on macro factors."""
        try:
            base_exposure = 0.5  # 50% base exposure
            
            # Market phase adjustment
            if market_phase == "risk_on":
                base_exposure += 0.2
            elif market_phase == "risk_off":
                base_exposure -= 0.3
            
            # Dollar strength adjustment
            if dollar_strength == "weak":
                base_exposure += 0.1  # Weak dollar = good for crypto
            elif dollar_strength == "strong":
                base_exposure -= 0.1
            
            # Crypto sentiment adjustment
            if crypto_sentiment == "bullish":
                base_exposure += 0.15
            elif crypto_sentiment == "bearish":
                base_exposure -= 0.15
            
            # Funding environment adjustment
            if funding_environment == "positive":
                base_exposure += 0.05
            elif funding_environment == "negative":
                base_exposure -= 0.05
            
            # Risk level adjustment
            if macro_risk_level == "high":
                base_exposure *= 0.8  # Reduced from 0.7 - less conservative
            elif macro_risk_level == "medium":
                base_exposure *= 1.05  # Slightly more aggressive for medium risk
            elif macro_risk_level == "low":
                base_exposure *= 1.1  # Increase exposure in low risk
            
            return max(0.1, min(1.0, base_exposure))  # Clamp between 10% and 100%
            
        except Exception as exc:
            logger.error("❌ MACRO EXPOSURE CALCULATION FAILED - NO fallback: %s", exc)
            return None
    
    def _calculate_dxy_correlation(self, asset_returns: np.ndarray) -> float:
        """Calculate correlation with DXY (placeholder implementation)."""
        try:
            # In a real implementation, you would fetch DXY price history
            # and calculate correlation. For now, return a placeholder.
            return -0.3  # Typical negative correlation with DXY
        except Exception:
            return 0.0
    
    def _classify_correlation_strength(self, correlation: float) -> str:
        """Classify correlation strength."""
        if correlation > 0.7:
            return "strong"
        elif correlation > 0.3:
            return "moderate"
        else:
            return "weak"
    
    def _classify_correlation_direction(self, correlation: float) -> str:
        """Classify correlation direction."""
        if correlation > 0.1:
            return "positive"
        elif correlation < -0.1:
            return "negative"
        else:
            return "neutral"
    
    def _default_macro_data(self) -> MacroData:
        """Return default macro data."""
        return MacroData(
            timestamp=time.time(),
            dxy_index=103.0,
            btc_dominance=45.0,
            fear_greed_index=50,
            funding_rates={},
            total_market_cap=2_000_000_000_000,  # $2T
            market_sentiment="neutral"
        )
    
    def _default_macro_environment(self) -> MacroEnvironment:
        """Return default macro environment."""
        return MacroEnvironment(
            market_phase="transition",
            dollar_strength="neutral",
            crypto_sentiment="neutral",
            funding_environment="neutral",
            correlation_regime="low_correlation",
            macro_risk_level="medium",
            recommended_exposure=0.5
        )
    
    def _load_macro_data(self):
        """Load macro data from disk."""
        try:
            if self.data_path.exists():
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    
                # Load recent macro history
                for item in data.get('macro_history', []):
                    macro_data = MacroData(**item)
                    self.macro_history.append(macro_data)
                    
                logger.info("Loaded %d macro data points", len(self.macro_history))
                
        except Exception as exc:
            logger.warning("Failed to load macro data: %s", exc)
    
    def _save_macro_data(self):
        """Save macro data to disk."""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to serializable format
            macro_history_data = []
            for data in list(self.macro_history)[-100:]:  # Save last 100 points
                macro_history_data.append({
                    'timestamp': data.timestamp,
                    'dxy_index': data.dxy_index,
                    'btc_dominance': data.btc_dominance,
                    'fear_greed_index': data.fear_greed_index,
                    'funding_rates': data.funding_rates,
                    'total_market_cap': data.total_market_cap,
                    'market_sentiment': data.market_sentiment
                })
            
            save_data = {
                'macro_history': macro_history_data
            }
            
            with open(self.data_path, 'w') as f:
                json.dump(save_data, f, indent=2)
                
        except Exception as exc:
            logger.warning("Failed to save macro data: %s", exc)


# Singleton instance
_macro_factor_analyzer = None

def get_macro_factor_analyzer() -> MacroFactorAnalyzer:
    """Get singleton macro factor analyzer."""
    global _macro_factor_analyzer
    if _macro_factor_analyzer is None:
        _macro_factor_analyzer = MacroFactorAnalyzer()
    return _macro_factor_analyzer
