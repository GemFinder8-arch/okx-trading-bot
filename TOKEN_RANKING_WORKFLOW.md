# 🎯 Token Ranking Workflow - Complete Details

**Date:** 2025-11-14 23:50:00 UTC+02:00  
**Status:** Detailed Analysis  
**Document:** Token Selection Process & Scoring System

---

## 📊 Overview

The bot uses a **sophisticated token ranking system** that:
1. **Discovers candidate tokens** from OKX exchange
2. **Scores each token** using multiple factors
3. **Ranks tokens** by total score
4. **Selects top tokens** for trading analysis
5. **Repeats every loop cycle** (not just once at startup)

---

## 🔄 Token Selection Frequency

### ✅ EVERY LOOP CYCLE (Not Just Once!)

```python
# From main.py line 112-134
while True:  # Infinite loop
    iteration_start = time.time()
    
    # STEP 1: Discover symbols (EVERY ITERATION)
    candidate_symbols = _discover_symbols(okx, config)
    
    # STEP 2: Rank tokens (EVERY ITERATION)
    scores = ranking_engine.rank(candidate_symbols, top_n=ranking_sample_size)
    
    # STEP 3: Select top tokens (EVERY ITERATION)
    symbols_to_analyze = [token.symbol for token in scores[:max_symbols_to_analyze]]
    
    # STEP 4: Analyze and trade (EVERY ITERATION)
    for symbol in symbols_to_analyze:
        result = pipeline.run_cycle(symbol)
```

**Key Point:** Token selection happens **EVERY LOOP CYCLE**, not just at startup!

---

## 🔍 Step 1: Symbol Discovery

### Function: `_discover_symbols(okx, config)`
**Location:** `main.py` lines 66-73

```python
def _discover_symbols(okx, config) -> Iterable[str]:
    min_volume = config.bot.min_quote_volume_usd
    liquid = okx.fetch_liquid_spot_symbols(min_volume, quote_currency="USDT", limit=50)
    if liquid:
        symbols = [symbol for symbol, _ in liquid]
        logger.debug("Discovered %s liquid symbols", len(symbols))
        return symbols
    return list(config.bot.default_symbol_universe)
```

### What It Does
1. **Fetches liquid symbols** from OKX exchange
2. **Filters by minimum volume** (default: $50 minimum quote volume)
3. **Returns top 50 liquid symbols** in USDT pairs
4. **Fallback:** Uses default symbol universe if API fails

### Example Output
```
Discovered 50 liquid symbols:
BTC/USDT, ETH/USDT, SOL/USDT, ADA/USDT, DOT/USDT, ...
```

---

## 📈 Step 2: Token Ranking & Scoring

### Class: `TokenRankingEngine`
**Location:** `token_ranking.py` lines 76-143

### Scoring Factors

#### 1. **Liquidity Score** (Weight: 25%)
```python
def _liquidity_score(self, order_book, ticker) -> float:
    # Components:
    # - Spread analysis (40%): Lower spread = higher score
    # - Market depth (30%): Deeper order book = higher score
    # - Order book balance (20%): Balanced bids/asks = higher score
    # - Price impact (10%): Lower impact = higher score
    
    # Formula:
    liquidity = (spread * 0.4 + depth * 0.3 + balance * 0.2 + impact * 0.1)
    # Range: 0.0 to 1.0
```

**What It Measures:**
- Can we buy/sell without massive slippage?
- Is there enough volume at reasonable prices?
- Is the order book balanced?

---

#### 2. **Momentum Score** (Weight: 30%)
```python
def _momentum_score(self, ticker) -> float:
    price_change = ticker.get("percentage", 0.0)  # 24h % change
    volume = ticker.get("baseVolume", 0.0)        # Trading volume
    
    # Normalize price change to ±1.0 range
    normalized = price_change / 20.0  # Scale for ±20% moves
    
    # Volume boost (higher volume = stronger signal)
    volume_boost = min(volume / 10000.0, 1.0)
    
    # Combined momentum
    momentum = normalized * 0.8 + volume_boost * 0.2
    # Range: 0.0 to 1.0
```

**What It Measures:**
- Is the token moving up or down?
- Is there strong trading volume?
- Is this momentum backed by volume?

---

#### 3. **Macro Sentiment** (Weight: 15%)
```python
# From macro events and market sentiment
macro_score = macro_map.get(base_symbol, macro_map.get('market', 0.5))

# Adjusted based on momentum
if momentum_score > 0.5:  # Strong positive momentum
    macro_score = min(0.9, macro_score + 0.1)  # Boost sentiment
elif momentum_score < 0.2:  # Weak momentum
    macro_score = max(0.1, macro_score - 0.1)  # Reduce sentiment
# Range: 0.0 to 1.0
```

**What It Measures:**
- What's the overall market sentiment?
- Are there positive macro events?
- Does momentum align with sentiment?

---

#### 4. **On-Chain Strength** (Weight: 10%)
```python
def _onchain_score(self, onchain_metrics) -> float:
    # Analyzes:
    # - Large holder activity
    # - Whale movements
    # - Exchange inflows/outflows
    # - Network activity
    # Range: 0.0 to 1.0
```

**What It Measures:**
- What are whales doing?
- Is money flowing in or out?
- Is network activity increasing?

---

#### 5. **Volatility Score** (Weight: 10%)
```python
def _calculate_volatility_score(self, ticker) -> float:
    daily_volatility = (high - low) / close
    
    # Sweet spot: 2-8% daily volatility
    if 0.02 <= daily_volatility <= 0.08:
        return 1.0  # Perfect
    elif 0.01 <= daily_volatility <= 0.15:
        return 0.5 to 1.0  # Good
    else:
        return 0.1  # Too low or too high
    # Range: 0.0 to 1.0
```

**What It Measures:**
- Is volatility in the sweet spot (2-8%)?
- Too low = boring, no trading opportunity
- Too high = risky, hard to manage

---

#### 6. **Trend Strength** (Weight: 10%)
```python
def _calculate_trend_strength(self, ticker) -> float:
    # Analyzes:
    # - Price change direction
    # - Body vs shadow ratio (strong candles)
    # - Trend persistence
    # Range: 0.0 to 1.0
```

**What It Measures:**
- Is there a clear trend?
- Are candles strong (large body)?
- Is the trend persistent?

---

### Total Score Calculation

```python
@property
def total(self) -> float:
    """Calculate total score with dynamic weighting."""
    return self._calculate_weighted_score()

def _calculate_weighted_score(self, market_regime: str = "neutral") -> float:
    # Base weights
    weights = {
        "liquidity": 0.25,
        "momentum": 0.30,
        "sentiment": 0.15,
        "onchain": 0.10,
        "volatility": 0.10,
        "trend": 0.10
    }
    
    # Adjust weights based on market regime
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
    
    # Risk adjustment
    risk_adjustment = 1.0 - (risk_score - 0.5) * 0.3
    
    # Final score
    base_score = (
        liquidity * weights["liquidity"]
        + momentum * weights["momentum"]
        + sentiment * weights["sentiment"]
        + onchain * weights["onchain"]
        + volatility * weights["volatility"]
        + trend * weights["trend"]
    )
    
    return base_score * risk_adjustment
```

**Final Score Range:** 0.0 to 1.0

---

## 🎯 Step 3: Token Selection

### From main.py lines 170-174

```python
if available_slots > 0:
    # Select symbols to analyze (limit to prevent rate limiting)
    max_symbols_to_analyze = min(available_slots + 3, 10)  # Max 10 symbols per cycle
    symbols_to_analyze = [token.symbol for token in scores[:max_symbols_to_analyze]]
```

### Selection Logic

1. **Check available slots**
   - If 0 slots available → Skip this iteration
   - If slots available → Proceed

2. **Calculate max symbols to analyze**
   - `max_symbols_to_analyze = min(available_slots + 3, 10)`
   - Example: If 2 slots available → Analyze min(2+3, 10) = 5 symbols
   - Never analyze more than 10 symbols per cycle

3. **Select top-ranked symbols**
   - Take top N symbols from ranking
   - These are the highest-scoring tokens

### Example

```
Ranked tokens (by score):
1. BTC/USDT (0.95)
2. ETH/USDT (0.92)
3. SOL/USDT (0.88)
4. ADA/USDT (0.85)
5. DOT/USDT (0.82)
...

Available slots: 2
Max to analyze: min(2+3, 10) = 5

Selected for analysis:
- BTC/USDT
- ETH/USDT
- SOL/USDT
- ADA/USDT
- DOT/USDT
```

---

## 🔄 Step 4: Analysis & Trading

### From main.py lines 196-205

```python
# Sequential execution for trading decisions
for symbol in valid_symbols[:available_slots]:
    if len(pipeline.open_positions) >= max_positions:
        break
    try:
        result = pipeline.run_cycle(symbol)
        executed.append(result)
    except Exception as exc:
        logger.exception("Pipeline cycle failed for %s: %s", symbol, exc)
```

### What Happens

1. **Fetch market data** (sequentially to avoid rate limiting)
2. **Run trading pipeline** for each symbol
3. **Generate trading signals** (BUY/SELL/HOLD)
4. **Execute trades** if conditions met
5. **Record results**

---

## 📊 Example Output

### Iteration 1
```
🏆 TOP 5 TOKEN SCORES: BTC/USDT(0.950), ETH/USDT(0.920), SOL/USDT(0.880), ADA/USDT(0.850), DOT/USDT(0.820)
🎯 TRADING SLOTS: 0 open positions, 10 available slots for new trades
Fetching market data for 10 symbols SEQUENTIALLY (prevents rate limiting)
Processing 10 symbols with valid market data
Iteration summary: BTC/USDT:HOLD:SKIP, ETH/USDT:HOLD:SKIP, SOL/USDT:HOLD:SKIP, ...
```

### Iteration 2 (30 seconds later)
```
🏆 TOP 5 TOKEN SCORES: SOL/USDT(0.920), BTC/USDT(0.910), ETH/USDT(0.890), ADA/USDT(0.870), DOT/USDT(0.840)
🎯 TRADING SLOTS: 0 open positions, 10 available slots for new trades
Fetching market data for 10 symbols SEQUENTIALLY (prevents rate limiting)
Processing 10 symbols with valid market data
Iteration summary: SOL/USDT:BUY:EXEC, ETH/USDT:HOLD:SKIP, BTC/USDT:HOLD:SKIP, ...
```

**Notice:** Rankings changed! SOL moved from #3 to #1 because:
- Price momentum improved
- Volume increased
- Sentiment shifted

---

## 🔑 Key Points

### 1. **Dynamic Selection**
- ✅ Tokens are ranked EVERY iteration
- ✅ Rankings change based on real-time market data
- ✅ Bot adapts to market conditions

### 2. **Market Regime Adaptation**
- In trending markets: Emphasize momentum & trend strength
- In volatile markets: Emphasize liquidity & volatility
- In ranging markets: Emphasize sentiment & volatility

### 3. **Risk Management**
- High-risk tokens get penalized (lower scores)
- Liquidity is crucial (prevents slippage)
- Volatility must be in sweet spot (2-8%)

### 4. **Rate Limiting Protection**
- Max 10 symbols analyzed per cycle
- Sequential market data fetching
- Prevents CoinGecko API rate limiting

### 5. **Smart Slot Management**
- Only analyze if slots available
- Analyze `available_slots + 3` symbols (buffer)
- Never exceed 10 symbols per cycle

---

## 📈 Scoring Weights Summary

| Factor | Weight | Market Regime Impact |
|--------|--------|----------------------|
| Liquidity | 25% | +15% in volatile |
| Momentum | 30% | +10% in trending |
| Sentiment | 15% | +10% in ranging |
| On-Chain | 10% | Fixed |
| Volatility | 10% | +10% in volatile |
| Trend Strength | 10% | +10% in trending |

---

## 🎯 Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN LOOP (Every 30s)                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Symbol Discovery                                   │
│  - Fetch 50 most liquid symbols from OKX                    │
│  - Filter by minimum volume ($50)                           │
│  - Result: 50 candidate symbols                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Token Ranking                                      │
│  - Score each symbol (6 factors)                            │
│  - Apply market regime weights                              │
│  - Sort by total score                                      │
│  - Result: Ranked list of 50 symbols                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Token Selection                                    │
│  - Check available trading slots                            │
│  - Select top N symbols (max 10)                            │
│  - Result: 5-10 symbols to analyze                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Analysis & Trading                                 │
│  - Fetch market cap data (sequential)                       │
│  - Run trading pipeline (signals)                           │
│  - Execute trades if conditions met                         │
│  - Result: Trades executed or skipped                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    Sleep 30 seconds
                            ↓
                    REPEAT LOOP
```

---

## 🎯 Summary

| Aspect | Details |
|--------|---------|
| **Selection Frequency** | Every loop cycle (every 30 seconds) |
| **Candidate Symbols** | 50 most liquid symbols from OKX |
| **Scoring Factors** | 6 factors (liquidity, momentum, sentiment, on-chain, volatility, trend) |
| **Ranking Method** | Weighted score with market regime adaptation |
| **Selection Method** | Top N symbols (max 10) based on score |
| **Adaptation** | Real-time, changes every iteration |
| **Rate Limiting** | Sequential processing, max 10 symbols/cycle |

---

**Status:** ✅ **TOKEN RANKING FULLY DYNAMIC**  
**Selection:** ✅ **EVERY LOOP CYCLE**  
**Adaptation:** ✅ **REAL-TIME MARKET CONDITIONS**
