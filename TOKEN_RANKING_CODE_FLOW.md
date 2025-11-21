# 📝 Token Ranking - Code Flow & Implementation

---

## 🔄 Main Loop Flow

### File: `main.py` (lines 112-226)

```python
# INFINITE LOOP - Runs every 30 seconds
while True:
    iteration_start = time.time()
    
    # ═══════════════════════════════════════════════════════════
    # PHASE 1: SYMBOL DISCOVERY
    # ═══════════════════════════════════════════════════════════
    
    # Line 119: Discover liquid symbols
    candidate_symbols = _discover_symbols(okx, config)
    # Returns: List of 50 most liquid symbols
    # Example: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', ...]
    
    # Line 120-122: Remove restricted symbols
    restricted = pipeline.restricted_symbols
    if restricted:
        candidate_symbols = [sym for sym in candidate_symbols 
                           if sym not in restricted]
    
    # ═══════════════════════════════════════════════════════════
    # PHASE 2: TOKEN RANKING
    # ═══════════════════════════════════════════════════════════
    
    # Line 132-133: Rank all candidate symbols
    ranking_sample_size = max(len(candidate_symbols), max_positions * 3)
    scores = ranking_engine.rank(candidate_symbols, 
                                 top_n=ranking_sample_size)
    # Returns: List of TokenScore objects, sorted by total score
    # Example: [
    #   TokenScore(symbol='BTC/USDT', total=0.950),
    #   TokenScore(symbol='ETH/USDT', total=0.920),
    #   TokenScore(symbol='SOL/USDT', total=0.880),
    #   ...
    # ]
    
    # Line 134: Save report
    save_token_report(scores, report_path)
    # Saves to: reports/latest_token_rankings.json
    
    # ═══════════════════════════════════════════════════════════
    # PHASE 3: PORTFOLIO MANAGEMENT
    # ═══════════════════════════════════════════════════════════
    
    # Line 145: Manage all assets
    pipeline.manage_all_assets()
    
    # Line 148: Manage existing positions
    pipeline.manage_all_positions()
    
    # ═══════════════════════════════════════════════════════════
    # PHASE 4: TOKEN SELECTION & ANALYSIS
    # ═══════════════════════════════════════════════════════════
    
    # Line 168-169: Check available slots
    available_slots = max_positions - len(pipeline.open_positions)
    
    if available_slots > 0:
        # Line 173: Calculate max symbols to analyze
        max_symbols_to_analyze = min(available_slots + 3, 10)
        # Example: If 2 slots available → min(2+3, 10) = 5
        
        # Line 174: Select top symbols
        symbols_to_analyze = [token.symbol 
                            for token in scores[:max_symbols_to_analyze]]
        # Example: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'DOT/USDT']
        
        # Line 178: Log selection
        logger.info("Fetching market data for %d symbols SEQUENTIALLY", 
                   len(symbols_to_analyze))
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 5: MARKET DATA FETCHING (Sequential)
        # ═══════════════════════════════════════════════════════════
        
        # Line 179-180: Get market cap analyzer
        from trading_bot.analytics.market_cap_analyzer import get_market_cap_analyzer
        market_cap_analyzer = get_market_cap_analyzer()
        
        # Line 182-190: Fetch market data sequentially
        market_data_batch = {}
        for symbol in symbols_to_analyze:
            try:
                # Respects rate limiter (5 calls/min)
                cap_data = market_cap_analyzer.get_market_cap_data(symbol)
                market_data_batch[symbol] = cap_data
            except Exception as exc:
                logger.debug("Failed to fetch market data for %s: %s", 
                           symbol, exc)
                market_data_batch[symbol] = None
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 6: TRADING PIPELINE EXECUTION
        # ═══════════════════════════════════════════════════════════
        
        # Line 193: Filter symbols with valid data
        valid_symbols = [symbol for symbol, data in market_data_batch.items() 
                        if data]
        logger.info("Processing %d symbols with valid market data", 
                   len(valid_symbols))
        
        # Line 198-205: Execute trading pipeline
        for symbol in valid_symbols[:available_slots]:
            if len(pipeline.open_positions) >= max_positions:
                break
            try:
                # Run trading pipeline for this symbol
                result = pipeline.run_cycle(symbol)
                executed.append(result)
            except Exception as exc:
                logger.exception("Pipeline cycle failed for %s: %s", 
                               symbol, exc)
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 7: RESULTS & LOGGING
        # ═══════════════════════════════════════════════════════════
        
        # Line 215-219: Log iteration summary
        executions_summary = ", ".join(
            f"{res.symbol}:{res.decision}:{'EXEC' if res.executed else 'SKIP'}"
            for res in executed
        )
        logger.info("Iteration summary: %s", executions_summary or "no executions")
    
    # ═══════════════════════════════════════════════════════════
    # PHASE 8: SLEEP & REPEAT
    # ═══════════════════════════════════════════════════════════
    
    # Line 261-263: Sleep until next iteration
    elapsed = time.time() - iteration_start
    sleep_for = max(interval - elapsed, 0)
    if sleep_for:
        time.sleep(sleep_for)
    
    # Loop repeats...
```

---

## 🎯 Symbol Discovery Function

### File: `main.py` (lines 66-73)

```python
def _discover_symbols(okx, config) -> Iterable[str]:
    """Discover liquid symbols from OKX exchange."""
    
    # Get minimum volume threshold
    min_volume = config.bot.min_quote_volume_usd  # Default: 50
    
    # Fetch liquid symbols from OKX
    liquid = okx.fetch_liquid_spot_symbols(
        min_volume,                    # Minimum quote volume in USD
        quote_currency="USDT",         # Only USDT pairs
        limit=50                       # Top 50 liquid symbols
    )
    
    if liquid:
        # Extract symbol names
        symbols = [symbol for symbol, _ in liquid]
        logger.debug("Discovered %s liquid symbols", len(symbols))
        return symbols
    
    # Fallback to default symbols if API fails
    return list(config.bot.default_symbol_universe)
```

---

## 📊 Token Ranking Engine

### File: `token_ranking.py` (lines 76-143)

```python
class TokenRankingEngine:
    """Combine multiple signals to rank tradable tokens."""
    
    def __init__(self, okx, macro_provider, onchain_provider):
        self._okx = okx
        self._macro = macro_provider
        self._onchain = onchain_provider
    
    def rank(self, symbols: Iterable[str], top_n: int = 10) -> List[TokenScore]:
        """Rank symbols by composite score."""
        
        # Filter restricted symbols
        symbols = [s for s in symbols 
                  if s not in getattr(self._onchain, "restricted_symbols", set())]
        
        scores: list[TokenScore] = []
        
        # Get macro events for sentiment
        macro_events = list(self._macro.latest_events(limit=50))
        macro_map = self._sentiment_from_macro(macro_events)
        
        # Score each symbol
        for symbol in symbols:
            try:
                # Fetch market data
                ticker = self._okx.fetch_ticker(symbol)
                book = self._okx.fetch_order_book(symbol, limit=20)
            except Exception as exc:
                logger.warning("Skipping %s due to market data error: %s", 
                             symbol, exc)
                continue
            
            # ═══════════════════════════════════════════════════════════
            # CALCULATE 6 SCORING FACTORS
            # ═══════════════════════════════════════════════════════════
            
            # Factor 1: Liquidity (25% weight)
            liquidity_score = self._liquidity_score(book, ticker)
            # Returns: 0.0 - 1.0
            
            # Factor 2: Momentum (30% weight)
            momentum_score = self._momentum_score(ticker)
            # Returns: 0.0 - 1.0
            
            # Factor 3: Volatility (10% weight)
            volatility_score = self._calculate_volatility_score(ticker)
            # Returns: 0.0 - 1.0
            
            # Factor 4: Trend Strength (10% weight)
            trend_strength = self._calculate_trend_strength(ticker)
            # Returns: 0.0 - 1.0
            
            # Factor 5: Risk Score (used for adjustment)
            risk_score = self._calculate_risk_score(ticker, book)
            # Returns: 0.0 - 1.0
            
            # Factor 6: Macro Sentiment (15% weight)
            base_symbol = symbol.split("/")[0].lower()
            macro_score = macro_map.get(base_symbol, 
                                       macro_map.get('market', 0.5))
            
            # Adjust sentiment by momentum
            if momentum_score > 0.5:
                macro_score = min(0.9, macro_score + 0.1)
            elif momentum_score < 0.2:
                macro_score = max(0.1, macro_score - 0.1)
            
            # Factor 7: On-Chain Strength (10% weight)
            onchain_metrics = self._onchain.latest_metrics(symbol, limit=1)
            onchain_score = self._onchain_score(onchain_metrics)
            # Returns: 0.0 - 1.0
            
            # ═══════════════════════════════════════════════════════════
            # CREATE TOKEN SCORE OBJECT
            # ═══════════════════════════════════════════════════════════
            
            scores.append(
                TokenScore(
                    symbol=symbol,
                    liquidity_score=liquidity_score,
                    momentum_score=momentum_score,
                    macro_sentiment=macro_score,
                    onchain_strength=onchain_score,
                    volatility_score=volatility_score,
                    trend_strength=trend_strength,
                    risk_score=risk_score,
                )
            )
        
        # ═══════════════════════════════════════════════════════════
        # SORT BY TOTAL SCORE
        # ═══════════════════════════════════════════════════════════
        
        # Sort descending (highest score first)
        scores.sort(key=lambda token: token.total, reverse=True)
        
        # Log top 5
        logger.info("🏆 TOP 5 TOKEN SCORES: %s", 
                   ", ".join([f"{t.symbol}({t.total:.3f})" 
                            for t in scores[:5]]))
        
        # Return top N
        return scores[:top_n]
```

---

## 🧮 Score Calculation

### File: `token_ranking.py` (lines 26-73)

```python
@dataclass
class TokenScore:
    symbol: str
    liquidity_score: float
    momentum_score: float
    macro_sentiment: float
    onchain_strength: float
    volatility_score: float = 0.0
    trend_strength: float = 0.0
    risk_score: float = 0.5
    
    @property
    def total(self) -> float:
        """Calculate total score with dynamic weighting."""
        return self._calculate_weighted_score()
    
    def _calculate_weighted_score(self, market_regime: str = "neutral") -> float:
        """Calculate score with market regime-adaptive weights."""
        
        # ═══════════════════════════════════════════════════════════
        # BASE WEIGHTS
        # ═══════════════════════════════════════════════════════════
        
        weights = {
            "liquidity": 0.25,
            "momentum": 0.30,
            "sentiment": 0.15,
            "onchain": 0.10,
            "volatility": 0.10,
            "trend": 0.10
        }
        
        # ═══════════════════════════════════════════════════════════
        # MARKET REGIME ADJUSTMENTS
        # ═══════════════════════════════════════════════════════════
        
        if market_regime == "trending":
            weights["momentum"] += 0.10      # Boost momentum
            weights["trend"] += 0.10         # Boost trend
            weights["liquidity"] -= 0.10     # Reduce liquidity
            weights["sentiment"] -= 0.10     # Reduce sentiment
        
        elif market_regime == "volatile":
            weights["liquidity"] += 0.15     # Boost liquidity
            weights["volatility"] += 0.10    # Boost volatility
            weights["momentum"] -= 0.15      # Reduce momentum
            weights["trend"] -= 0.10         # Reduce trend
        
        elif market_regime == "ranging":
            weights["sentiment"] += 0.10     # Boost sentiment
            weights["volatility"] += 0.05    # Boost volatility
            weights["momentum"] -= 0.10      # Reduce momentum
            weights["trend"] -= 0.05         # Reduce trend
        
        # ═══════════════════════════════════════════════════════════
        # RISK ADJUSTMENT
        # ═══════════════════════════════════════════════════════════
        
        # Penalize high-risk tokens
        risk_adjustment = 1.0 - (self.risk_score - 0.5) * 0.3
        # If risk_score = 0.5 (neutral) → adjustment = 1.0
        # If risk_score = 1.0 (high risk) → adjustment = 0.85
        
        # ═══════════════════════════════════════════════════════════
        # CALCULATE BASE SCORE
        # ═══════════════════════════════════════════════════════════
        
        base_score = (
            self.liquidity_score * weights["liquidity"]
            + self.momentum_score * weights["momentum"]
            + self.macro_sentiment * weights["sentiment"]
            + self.onchain_strength * weights["onchain"]
            + self.volatility_score * weights["volatility"]
            + self.trend_strength * weights["trend"]
        )
        
        # ═══════════════════════════════════════════════════════════
        # APPLY RISK ADJUSTMENT & RETURN
        # ═══════════════════════════════════════════════════════════
        
        return base_score * risk_adjustment
        # Range: 0.0 - 1.0
```

---

## 📋 Example Execution

### Iteration 1

```python
# PHASE 1: Discover
candidate_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', ..., 'TURBO/USDT']
# 50 symbols

# PHASE 2: Rank
scores = [
    TokenScore(symbol='BTC/USDT', total=0.950),
    TokenScore(symbol='ETH/USDT', total=0.920),
    TokenScore(symbol='SOL/USDT', total=0.880),
    TokenScore(symbol='ADA/USDT', total=0.850),
    TokenScore(symbol='DOT/USDT', total=0.820),
    ...
]

# PHASE 3: Select
available_slots = 10
max_symbols_to_analyze = min(10 + 3, 10) = 10
symbols_to_analyze = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'DOT/USDT', ...]

# PHASE 4-6: Analyze & Trade
for symbol in symbols_to_analyze:
    cap_data = market_cap_analyzer.get_market_cap_data(symbol)
    result = pipeline.run_cycle(symbol)
    # Result: BTC/USDT:HOLD:SKIP, ETH/USDT:HOLD:SKIP, ...

# PHASE 7: Log
logger.info("Iteration summary: BTC/USDT:HOLD:SKIP, ETH/USDT:HOLD:SKIP, ...")

# PHASE 8: Sleep
sleep(30)
```

### Iteration 2 (30 seconds later)

```python
# PHASE 1: Discover (AGAIN)
candidate_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', ..., 'TURBO/USDT']
# 50 symbols (might be different)

# PHASE 2: Rank (AGAIN - with updated market data)
scores = [
    TokenScore(symbol='SOL/USDT', total=0.920),  # ← Moved up!
    TokenScore(symbol='BTC/USDT', total=0.910),  # ← Moved down
    TokenScore(symbol='ETH/USDT', total=0.890),
    TokenScore(symbol='ADA/USDT', total=0.870),
    TokenScore(symbol='DOT/USDT', total=0.840),
    ...
]

# PHASE 3: Select (AGAIN)
symbols_to_analyze = ['SOL/USDT', 'BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'DOT/USDT', ...]

# PHASE 4-6: Analyze & Trade (AGAIN)
for symbol in symbols_to_analyze:
    cap_data = market_cap_analyzer.get_market_cap_data(symbol)
    result = pipeline.run_cycle(symbol)
    # Result: SOL/USDT:BUY:EXEC, BTC/USDT:HOLD:SKIP, ...

# PHASE 7: Log
logger.info("Iteration summary: SOL/USDT:BUY:EXEC, BTC/USDT:HOLD:SKIP, ...")

# PHASE 8: Sleep
sleep(30)
```

---

## 🎯 Key Code Locations

| Component | File | Lines |
|-----------|------|-------|
| Main Loop | `main.py` | 112-226 |
| Symbol Discovery | `main.py` | 66-73 |
| Token Ranking | `token_ranking.py` | 76-143 |
| Score Calculation | `token_ranking.py` | 26-73 |
| Liquidity Score | `token_ranking.py` | 145-225 |
| Momentum Score | `token_ranking.py` | 227-243 |
| Volatility Score | `token_ranking.py` | 245-273 |
| Trend Strength | `token_ranking.py` | 275-310 |
| Risk Score | `token_ranking.py` | 312-346 |
| On-Chain Score | `token_ranking.py` | 348-380 |

---

## ✅ Summary

- ✅ **Selection:** EVERY LOOP CYCLE
- ✅ **Frequency:** Every 30 seconds
- ✅ **Adaptation:** Real-time market data
- ✅ **Scoring:** 6 factors with market regime weights
- ✅ **Rate Limiting:** Sequential processing, max 10/cycle
- ✅ **Code:** Well-structured and modular
