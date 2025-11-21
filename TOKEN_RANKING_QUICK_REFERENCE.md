# 🎯 Token Ranking - Quick Reference

---

## ⚡ Quick Facts

✅ **Selection Happens:** EVERY LOOP CYCLE (not just once)  
✅ **Frequency:** Every 30 seconds  
✅ **Candidate Symbols:** 50 most liquid from OKX  
✅ **Symbols Analyzed:** Top 5-10 by score  
✅ **Scoring Factors:** 6 (liquidity, momentum, sentiment, on-chain, volatility, trend)  
✅ **Adaptation:** Real-time, changes every iteration  

---

## 🔍 The 6 Scoring Factors

### 1️⃣ Liquidity (25% weight)
**What:** Can we buy/sell without slippage?
- Spread analysis (40%)
- Order book depth (30%)
- Order book balance (20%)
- Price impact (10%)
**Range:** 0.0 - 1.0

### 2️⃣ Momentum (30% weight)
**What:** Is the token moving up with volume?
- 24h price change
- Trading volume
- Volume momentum
**Range:** 0.0 - 1.0

### 3️⃣ Macro Sentiment (15% weight)
**What:** What's the market saying?
- Market sentiment
- Macro events
- Adjusted by momentum
**Range:** 0.0 - 1.0

### 4️⃣ On-Chain Strength (10% weight)
**What:** What are whales doing?
- Large holder activity
- Whale movements
- Exchange flows
- Network activity
**Range:** 0.0 - 1.0

### 5️⃣ Volatility (10% weight)
**What:** Is volatility in the sweet spot?
- Daily volatility %
- Sweet spot: 2-8%
- Too low/high = penalized
**Range:** 0.0 - 1.0

### 6️⃣ Trend Strength (10% weight)
**What:** Is there a clear trend?
- Price direction
- Candle strength
- Trend persistence
**Range:** 0.0 - 1.0

---

## 📊 Score Calculation

```
Total Score = (
    Liquidity × 0.25 +
    Momentum × 0.30 +
    Sentiment × 0.15 +
    On-Chain × 0.10 +
    Volatility × 0.10 +
    Trend × 0.10
) × Risk Adjustment
```

**Risk Adjustment:** High-risk tokens get penalized

---

## 🔄 Market Regime Adaptation

### Trending Market
- ⬆️ Momentum weight: +10%
- ⬆️ Trend weight: +10%
- ⬇️ Liquidity weight: -10%
- ⬇️ Sentiment weight: -10%

### Volatile Market
- ⬆️ Liquidity weight: +15%
- ⬆️ Volatility weight: +10%
- ⬇️ Momentum weight: -15%
- ⬇️ Trend weight: -10%

### Ranging Market
- ⬆️ Sentiment weight: +10%
- ⬆️ Volatility weight: +5%
- ⬇️ Momentum weight: -10%
- ⬇️ Trend weight: -5%

---

## 🎯 Selection Process

```
Step 1: Discover
├─ Fetch 50 liquid symbols from OKX
├─ Filter by min volume ($50)
└─ Result: 50 candidates

Step 2: Rank
├─ Score each symbol (6 factors)
├─ Apply market regime weights
├─ Sort by score (highest first)
└─ Result: Ranked list

Step 3: Select
├─ Check available slots
├─ Calculate: min(slots + 3, 10)
├─ Take top N symbols
└─ Result: 5-10 symbols

Step 4: Analyze
├─ Fetch market data
├─ Generate signals
├─ Execute trades
└─ Result: Trades or HOLD
```

---

## 📈 Example Scores

```
Iteration 1:
🏆 TOP 5:
  1. BTC/USDT  (0.950)
  2. ETH/USDT  (0.920)
  3. SOL/USDT  (0.880)
  4. ADA/USDT  (0.850)
  5. DOT/USDT  (0.820)

Iteration 2 (30 seconds later):
🏆 TOP 5:
  1. SOL/USDT  (0.920) ← Moved up!
  2. BTC/USDT  (0.910) ← Moved down
  3. ETH/USDT  (0.890)
  4. ADA/USDT  (0.870)
  5. DOT/USDT  (0.840)
```

**Why changed?** Real-time market data updated!

---

## ⚙️ Configuration

```python
# From config
min_quote_volume_usd = 50      # Minimum volume filter
max_concurrent_positions = 10  # Max open trades
polling_interval_seconds = 30  # Loop frequency
max_symbols_to_analyze = 10    # Max per cycle
```

---

## 🔐 Rate Limiting Protection

✅ Max 10 symbols analyzed per cycle  
✅ Sequential market data fetching  
✅ CoinGecko: 5 calls/minute (safe)  
✅ OKX: Respects rate limits  

---

## 📊 Workflow Summary

```
MAIN LOOP (Every 30s)
    ↓
DISCOVER SYMBOLS (50 liquid)
    ↓
RANK TOKENS (6 factors)
    ↓
SELECT TOP N (max 10)
    ↓
ANALYZE & TRADE
    ↓
SLEEP 30s
    ↓
REPEAT
```

---

## 🎯 Key Insights

1. **Dynamic:** Rankings change every iteration
2. **Adaptive:** Weights adjust to market regime
3. **Smart:** Liquidity & momentum are most important
4. **Safe:** Rate limiting built-in
5. **Real-time:** Uses live market data
6. **Risk-aware:** High-risk tokens penalized

---

## ✅ Status

- ✅ Token ranking: WORKING
- ✅ Selection: EVERY CYCLE
- ✅ Adaptation: REAL-TIME
- ✅ Rate limiting: PROTECTED
- ✅ Bot: RUNNING SMOOTHLY
