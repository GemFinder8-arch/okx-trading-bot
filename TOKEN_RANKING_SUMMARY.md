# 🎯 Token Ranking Workflow - Complete Summary

**Date:** 2025-11-14 23:55:00 UTC+02:00  
**Analysis:** Complete  
**Status:** ✅ ALL QUESTIONS ANSWERED

---

## ❓ Your Questions Answered

### Q1: "How does the bot select tokens?"
**A:** The bot uses a **6-factor scoring system** that evaluates:
1. Liquidity (25%)
2. Momentum (30%)
3. Macro Sentiment (15%)
4. On-Chain Strength (10%)
5. Volatility (10%)
6. Trend Strength (10%)

Each token gets a score from 0.0 to 1.0, then tokens are ranked by score.

---

### Q2: "What is the bot basing the selection on?"
**A:** The bot bases selection on **real-time market data**:

| Factor | Source | What It Measures |
|--------|--------|------------------|
| Liquidity | Order book | Can we trade without slippage? |
| Momentum | Ticker | Is price moving up with volume? |
| Sentiment | Macro events | What's the market saying? |
| On-Chain | Blockchain | What are whales doing? |
| Volatility | Price data | Is volatility in sweet spot (2-8%)? |
| Trend | Price action | Is there a clear trend? |

---

### Q3: "Does the bot select tokens only once at startup or every loop cycle?"
**A:** ✅ **EVERY LOOP CYCLE** (not just once!)

```python
# From main.py - Infinite loop
while True:
    # EVERY 30 SECONDS:
    candidate_symbols = _discover_symbols(okx, config)  # ← Every iteration
    scores = ranking_engine.rank(candidate_symbols)      # ← Every iteration
    symbols_to_analyze = [token.symbol for token in scores[:10]]  # ← Every iteration
    
    # Then analyze and trade
    for symbol in symbols_to_analyze:
        pipeline.run_cycle(symbol)
    
    sleep(30)  # Wait 30 seconds
    # Loop repeats...
```

---

## 📊 The Complete Workflow

### Every 30 Seconds:

```
┌─────────────────────────────────────────────────────┐
│ PHASE 1: SYMBOL DISCOVERY                           │
├─────────────────────────────────────────────────────┤
│ • Fetch 50 most liquid symbols from OKX             │
│ • Filter by minimum volume ($50)                    │
│ • Remove restricted symbols                         │
│ Result: 50 candidate symbols                        │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ PHASE 2: TOKEN RANKING                              │
├─────────────────────────────────────────────────────┤
│ For each symbol:                                    │
│ • Calculate liquidity score (order book analysis)   │
│ • Calculate momentum score (price + volume)         │
│ • Calculate sentiment score (macro events)          │
│ • Calculate on-chain score (whale activity)         │
│ • Calculate volatility score (price range)          │
│ • Calculate trend score (price action)              │
│ • Apply market regime weights                       │
│ • Apply risk adjustment                             │
│ Result: Ranked list of 50 symbols                   │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ PHASE 3: TOKEN SELECTION                            │
├─────────────────────────────────────────────────────┤
│ • Check available trading slots                     │
│ • Calculate: min(available_slots + 3, 10)           │
│ • Select top N symbols from ranking                 │
│ Result: 5-10 symbols to analyze                     │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ PHASE 4: MARKET DATA FETCHING                       │
├─────────────────────────────────────────────────────┤
│ • Fetch market cap data (sequential)                │
│ • Respects CoinGecko rate limit (5 calls/min)       │
│ • Filter symbols with valid data                    │
│ Result: Valid symbols with market data              │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ PHASE 5: TRADING ANALYSIS & EXECUTION               │
├─────────────────────────────────────────────────────┤
│ For each valid symbol:                              │
│ • Run trading pipeline                              │
│ • Generate trading signal (BUY/SELL/HOLD)           │
│ • Execute trade if conditions met                   │
│ Result: Trades executed or skipped                  │
└─────────────────────────────────────────────────────┘
                        ↓
                   SLEEP 30s
                        ↓
                   REPEAT LOOP
```

---

## 🎯 Real-World Example

### Iteration 1 (Time: 00:00)

```
DISCOVERY:
  Discovered 50 liquid symbols

RANKING:
  🏆 TOP 5:
    1. BTC/USDT  (0.950) ← Highest score
    2. ETH/USDT  (0.920)
    3. SOL/USDT  (0.880)
    4. ADA/USDT  (0.850)
    5. DOT/USDT  (0.820)

SELECTION:
  Available slots: 10
  Max to analyze: min(10+3, 10) = 10
  Selected: Top 10 symbols

ANALYSIS:
  BTC/USDT: HOLD (confidence 0.65 < 0.70 required)
  ETH/USDT: HOLD (confidence 0.62 < 0.70 required)
  SOL/USDT: HOLD (confidence 0.58 < 0.70 required)
  ... (all HOLD due to bearish market)

RESULT:
  Iteration summary: BTC/USDT:HOLD:SKIP, ETH/USDT:HOLD:SKIP, ...
```

### Iteration 2 (Time: 00:30)

```
DISCOVERY:
  Discovered 50 liquid symbols (might be different)

RANKING:
  🏆 TOP 5:
    1. SOL/USDT  (0.920) ← Moved up! (momentum improved)
    2. BTC/USDT  (0.910) ← Moved down
    3. ETH/USDT  (0.890)
    4. ADA/USDT  (0.870)
    5. DOT/USDT  (0.840)

SELECTION:
  Available slots: 10
  Max to analyze: min(10+3, 10) = 10
  Selected: Top 10 symbols (different order!)

ANALYSIS:
  SOL/USDT: BUY (confidence 0.75 > 0.70 required) ← EXECUTED!
  BTC/USDT: HOLD (confidence 0.68 < 0.70 required)
  ETH/USDT: HOLD (confidence 0.65 < 0.70 required)
  ... (most still HOLD)

RESULT:
  Iteration summary: SOL/USDT:BUY:EXEC, BTC/USDT:HOLD:SKIP, ...
```

**Key Observation:** Rankings changed! SOL moved from #3 to #1 because:
- Price momentum improved
- Trading volume increased
- Sentiment shifted positive
- Bot adapted to new market conditions

---

## 🔑 Key Insights

### 1. Dynamic Selection
✅ Rankings change **every 30 seconds**  
✅ Bot adapts to **real-time market conditions**  
✅ Not static - continuously evaluates all symbols  

### 2. Smart Filtering
✅ Only analyzes **top-ranked symbols**  
✅ Limits to **max 10 symbols per cycle**  
✅ Prevents **rate limiting** and **over-analysis**  

### 3. Market Regime Adaptation
✅ Weights adjust based on market conditions  
✅ Trending market → Emphasize momentum  
✅ Volatile market → Emphasize liquidity  
✅ Ranging market → Emphasize sentiment  

### 4. Risk Management
✅ High-risk tokens get **penalized** (lower scores)  
✅ Liquidity is **crucial** (prevents slippage)  
✅ Volatility must be in **sweet spot** (2-8%)  

### 5. Rate Limiting Protection
✅ Sequential market data fetching  
✅ Max 10 symbols analyzed per cycle  
✅ CoinGecko: 5 calls/minute (safe)  

---

## 📈 Scoring Formula

```
Total Score = (
    Liquidity × 0.25 +
    Momentum × 0.30 +
    Sentiment × 0.15 +
    On-Chain × 0.10 +
    Volatility × 0.10 +
    Trend × 0.10
) × Risk Adjustment × Market Regime Weights

Range: 0.0 to 1.0
```

---

## 🔄 Frequency Summary

| Event | Frequency | Details |
|-------|-----------|---------|
| Symbol Discovery | Every 30s | Fetches 50 liquid symbols |
| Token Ranking | Every 30s | Scores all 50 symbols |
| Token Selection | Every 30s | Selects top 5-10 symbols |
| Market Data Fetch | Every 30s | Sequential (respects rate limit) |
| Trading Analysis | Every 30s | Runs pipeline for selected symbols |
| Trade Execution | Every 30s | Executes if conditions met |

---

## 📊 Configuration

```python
# From config
min_quote_volume_usd = 50           # Minimum volume filter
max_concurrent_positions = 10       # Max open trades
polling_interval_seconds = 30       # Loop frequency
max_symbols_to_analyze = 10         # Max per cycle
```

---

## 🎯 Files & Locations

| Component | File | Lines |
|-----------|------|-------|
| Main Loop | `main.py` | 112-226 |
| Symbol Discovery | `main.py` | 66-73 |
| Token Ranking Engine | `token_ranking.py` | 76-143 |
| Score Calculation | `token_ranking.py` | 26-73 |
| Liquidity Scoring | `token_ranking.py` | 145-225 |
| Momentum Scoring | `token_ranking.py` | 227-243 |
| Volatility Scoring | `token_ranking.py` | 245-273 |
| Trend Scoring | `token_ranking.py` | 275-310 |
| Risk Scoring | `token_ranking.py` | 312-346 |
| On-Chain Scoring | `token_ranking.py` | 348-380 |

---

## ✅ Answers Summary

| Question | Answer |
|----------|--------|
| **How does bot select tokens?** | 6-factor scoring system (liquidity, momentum, sentiment, on-chain, volatility, trend) |
| **What is selection based on?** | Real-time market data from OKX exchange |
| **Selection frequency?** | **EVERY LOOP CYCLE** (every 30 seconds, not just once) |
| **How many tokens selected?** | Top 5-10 symbols per cycle (max 10) |
| **How often rankings change?** | Every 30 seconds (real-time adaptation) |
| **Is it adaptive?** | Yes, weights adjust to market regime |
| **Rate limiting?** | Yes, sequential processing, max 10/cycle |

---

## 📝 Documentation Created

1. **TOKEN_RANKING_WORKFLOW.md** - Complete detailed workflow
2. **TOKEN_RANKING_QUICK_REFERENCE.md** - Quick reference guide
3. **TOKEN_RANKING_CODE_FLOW.md** - Code implementation details
4. **TOKEN_RANKING_SUMMARY.md** - This summary document

---

## 🎯 Conclusion

The bot uses a **sophisticated, adaptive token ranking system** that:

✅ **Selects tokens EVERY loop cycle** (not just once)  
✅ **Adapts to real-time market conditions** (rankings change every 30s)  
✅ **Uses 6 scoring factors** (liquidity, momentum, sentiment, on-chain, volatility, trend)  
✅ **Adjusts weights by market regime** (trending, volatile, ranging)  
✅ **Protects against rate limiting** (sequential processing, max 10/cycle)  
✅ **Manages risk intelligently** (penalizes high-risk tokens)  

**Result:** The bot is **smart, adaptive, and efficient** at selecting the best trading opportunities!

---

**Status:** ✅ **COMPLETE**  
**Analysis:** ✅ **THOROUGH**  
**Documentation:** ✅ **COMPREHENSIVE**
