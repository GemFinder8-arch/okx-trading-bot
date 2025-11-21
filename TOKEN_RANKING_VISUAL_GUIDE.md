# 🎨 Token Ranking - Visual Guide

---

## 🔄 Complete Loop Cycle (Every 30 Seconds)

```
┌──────────────────────────────────────────────────────────────────┐
│                    MAIN LOOP STARTS                              │
│                    (Every 30 seconds)                            │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 1: SYMBOL DISCOVERY                                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  OKX Exchange                                                    │
│  ├─ Fetch liquid symbols                                        │
│  ├─ Filter by min volume ($50)                                  │
│  └─ Limit to top 50                                             │
│                                                                  │
│  Result: 50 candidate symbols                                   │
│  [BTC/USDT, ETH/USDT, SOL/USDT, ADA/USDT, DOT/USDT, ...]      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 2: TOKEN RANKING (Score each symbol)                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  For each symbol:                                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ BTC/USDT                                                   │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ Liquidity Score:   0.92 (25% weight) = 0.230              │ │
│  │ Momentum Score:    0.88 (30% weight) = 0.264              │ │
│  │ Sentiment Score:   0.85 (15% weight) = 0.128              │ │
│  │ On-Chain Score:    0.90 (10% weight) = 0.090              │ │
│  │ Volatility Score:  0.95 (10% weight) = 0.095              │ │
│  │ Trend Score:       0.91 (10% weight) = 0.091              │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ Subtotal:                                    0.898          │ │
│  │ Risk Adjustment:   × 0.95                                  │ │
│  │ TOTAL SCORE:                                 0.853          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Repeat for all 50 symbols...                                   │
│                                                                  │
│  Result: Ranked list (highest to lowest)                        │
│  1. BTC/USDT  (0.950)                                           │
│  2. ETH/USDT  (0.920)                                           │
│  3. SOL/USDT  (0.880)                                           │
│  4. ADA/USDT  (0.850)                                           │
│  5. DOT/USDT  (0.820)                                           │
│  ...                                                             │
│  50. TURBO/USDT (0.150)                                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 3: TOKEN SELECTION                                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Check available slots:                                         │
│  ├─ Max positions: 10                                           │
│  ├─ Current positions: 2                                        │
│  └─ Available slots: 8                                          │
│                                                                  │
│  Calculate max to analyze:                                      │
│  ├─ Formula: min(available_slots + 3, 10)                       │
│  ├─ Calculation: min(8 + 3, 10) = 10                            │
│  └─ Max to analyze: 10                                          │
│                                                                  │
│  Select top N symbols:                                          │
│  ├─ Take top 10 from ranking                                    │
│  └─ Result: [BTC, ETH, SOL, ADA, DOT, MATIC, AVAX, LINK, UNI, DOGE]
│                                                                  │
│  Result: 10 symbols to analyze                                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 4: MARKET DATA FETCHING (Sequential)                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  For each symbol (one at a time):                               │
│  ├─ BTC/USDT  → Fetch market cap data (wait 12.5s)             │
│  ├─ ETH/USDT  → Fetch market cap data (wait 12.5s)             │
│  ├─ SOL/USDT  → Fetch market cap data (wait 12.5s)             │
│  ├─ ADA/USDT  → Fetch market cap data (wait 12.5s)             │
│  ├─ DOT/USDT  → Fetch market cap data (wait 12.5s)             │
│  └─ ... (respects CoinGecko rate limit: 5 calls/min)           │
│                                                                  │
│  Result: Market data batch                                      │
│  {                                                               │
│    'BTC/USDT': {cap: $1.2T, rank: #1, liquidity: 0.98},        │
│    'ETH/USDT': {cap: $250B, rank: #2, liquidity: 0.97},        │
│    'SOL/USDT': {cap: $85B, rank: #5, liquidity: 0.92},         │
│    ...                                                           │
│  }                                                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 5: TRADING ANALYSIS & EXECUTION                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  For each symbol with valid data:                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ BTC/USDT                                                   │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ 1. Multi-timeframe analysis                               │ │
│  │ 2. Technical indicators                                    │ │
│  │ 3. Market regime detection                                │ │
│  │ 4. Risk assessment                                         │ │
│  │ 5. Generate signal: HOLD                                   │ │
│  │ 6. Confidence: 0.65 (< 0.70 required)                      │ │
│  │ 7. Action: SKIP (don't trade)                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ SOL/USDT                                                   │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ 1. Multi-timeframe analysis                               │ │
│  │ 2. Technical indicators                                    │ │
│  │ 3. Market regime detection                                │ │
│  │ 4. Risk assessment                                         │ │
│  │ 5. Generate signal: BUY                                    │ │
│  │ 6. Confidence: 0.78 (> 0.70 required)                      │ │
│  │ 7. Action: EXECUTE TRADE! ✅                               │ │
│  │    - Entry: $195.50                                        │ │
│  │    - Stop Loss: $185.20                                    │ │
│  │    - Take Profit: $210.80                                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Result: Trades executed or skipped                             │
│  BTC/USDT:HOLD:SKIP, ETH/USDT:HOLD:SKIP, SOL/USDT:BUY:EXEC, ...
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 6: LOGGING & REPORTING                                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🏆 TOP 5 TOKEN SCORES: BTC/USDT(0.950), ETH/USDT(0.920),      │
│     SOL/USDT(0.880), ADA/USDT(0.850), DOT/USDT(0.820)          │
│                                                                  │
│  🎯 TRADING SLOTS: 3 open positions, 7 available slots          │
│                                                                  │
│  📊 ITERATION SUMMARY: BTC/USDT:HOLD:SKIP, ETH/USDT:HOLD:SKIP, │
│     SOL/USDT:BUY:EXEC, ADA/USDT:HOLD:SKIP, ...                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 7: SLEEP & REPEAT                                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Sleep for 30 seconds (or remaining time)                       │
│                                                                  │
│  Then loop repeats...                                           │
│  (Rankings will change based on new market data!)               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📊 Score Composition Example

```
BTC/USDT Score Breakdown:

┌─────────────────────────────────────────────────────────┐
│                    TOTAL SCORE: 0.950                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Liquidity (25%)      ████████████░░░░░░░░░░░░░░░░░░  0.92
│  Momentum (30%)       ████████████░░░░░░░░░░░░░░░░░░  0.88
│  Sentiment (15%)      ████████████░░░░░░░░░░░░░░░░░░  0.85
│  On-Chain (10%)       ████████████░░░░░░░░░░░░░░░░░░  0.90
│  Volatility (10%)     ████████████░░░░░░░░░░░░░░░░░░  0.95
│  Trend (10%)          ████████████░░░░░░░░░░░░░░░░░░  0.91
│                                                         │
│  Risk Adjustment:     × 0.95                           │
│                                                         │
└─────────────────────────────────────────────────────────┘

SOL/USDT Score Breakdown:

┌─────────────────────────────────────────────────────────┐
│                    TOTAL SCORE: 0.880                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Liquidity (25%)      ██████████░░░░░░░░░░░░░░░░░░░░  0.85
│  Momentum (30%)       ████████░░░░░░░░░░░░░░░░░░░░░░  0.75
│  Sentiment (15%)      ██████████░░░░░░░░░░░░░░░░░░░░  0.80
│  On-Chain (10%)       ████████░░░░░░░░░░░░░░░░░░░░░░  0.75
│  Volatility (10%)     ██████████░░░░░░░░░░░░░░░░░░░░  0.82
│  Trend (10%)          ████████░░░░░░░░░░░░░░░░░░░░░░  0.78
│                                                         │
│  Risk Adjustment:     × 0.98                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 Ranking Changes Over Time

```
ITERATION 1 (00:00)          ITERATION 2 (00:30)          ITERATION 3 (01:00)
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│ 1. BTC (0.950)   │        │ 1. SOL (0.920)   │        │ 1. ETH (0.930)   │
│ 2. ETH (0.920)   │        │ 2. BTC (0.910)   │        │ 2. BTC (0.920)   │
│ 3. SOL (0.880)   │   →    │ 3. ETH (0.890)   │   →    │ 3. SOL (0.880)   │
│ 4. ADA (0.850)   │        │ 4. ADA (0.870)   │        │ 4. ADA (0.860)   │
│ 5. DOT (0.820)   │        │ 5. DOT (0.840)   │        │ 5. DOT (0.830)   │
└──────────────────┘        └──────────────────┘        └──────────────────┘
   (Bearish)                   (Neutral)                   (Bullish)
   All HOLD                     SOL BUY!                   ETH BUY!
```

**Why rankings change:**
- Real-time market data updates
- Price momentum shifts
- Volume changes
- Sentiment evolves
- On-chain activity varies

---

## 🎯 Selection Logic Flowchart

```
START ITERATION
    ↓
DISCOVER SYMBOLS
    ↓
RANK ALL SYMBOLS
    ↓
CHECK AVAILABLE SLOTS
    ↓
    ├─ NO SLOTS? → SKIP TO SLEEP
    │
    └─ SLOTS AVAILABLE?
        ↓
        CALCULATE MAX TO ANALYZE
        ├─ Formula: min(slots + 3, 10)
        ├─ Example: min(5 + 3, 10) = 8
        └─ Max: 8 symbols
        ↓
        SELECT TOP N SYMBOLS
        ├─ Take top 8 from ranking
        └─ [BTC, ETH, SOL, ADA, DOT, MATIC, AVAX, LINK]
        ↓
        FETCH MARKET DATA (Sequential)
        ├─ BTC → Wait 12.5s
        ├─ ETH → Wait 12.5s
        ├─ SOL → Wait 12.5s
        └─ ... (respects rate limit)
        ↓
        ANALYZE & TRADE
        ├─ BTC: HOLD:SKIP
        ├─ ETH: HOLD:SKIP
        ├─ SOL: BUY:EXEC ✅
        └─ ... (execute or skip)
        ↓
        LOG RESULTS
        ↓
SLEEP 30s
    ↓
REPEAT
```

---

## 📈 Market Regime Weight Adjustment

```
NEUTRAL MARKET (Default)
┌────────────────────────────────────────┐
│ Liquidity:  25%  ████████████░░░░░░░░  │
│ Momentum:   30%  ███████████████░░░░░  │
│ Sentiment:  15%  ███████░░░░░░░░░░░░  │
│ On-Chain:   10%  █████░░░░░░░░░░░░░░  │
│ Volatility: 10%  █████░░░░░░░░░░░░░░  │
│ Trend:      10%  █████░░░░░░░░░░░░░░  │
└────────────────────────────────────────┘

TRENDING MARKET (Up or Down)
┌────────────────────────────────────────┐
│ Liquidity:  15%  ███████░░░░░░░░░░░░  │ -10%
│ Momentum:   40%  ████████████████████  │ +10%
│ Sentiment:   5%  ██░░░░░░░░░░░░░░░░░  │ -10%
│ On-Chain:   10%  █████░░░░░░░░░░░░░░  │
│ Volatility: 10%  █████░░░░░░░░░░░░░░  │
│ Trend:      20%  ██████████░░░░░░░░░  │ +10%
└────────────────────────────────────────┘

VOLATILE MARKET
┌────────────────────────────────────────┐
│ Liquidity:  40%  ████████████████████  │ +15%
│ Momentum:   15%  ███████░░░░░░░░░░░░  │ -15%
│ Sentiment:  15%  ███████░░░░░░░░░░░░  │
│ On-Chain:   10%  █████░░░░░░░░░░░░░░  │
│ Volatility: 20%  ██████████░░░░░░░░░  │ +10%
│ Trend:       0%  ░░░░░░░░░░░░░░░░░░░  │ -10%
└────────────────────────────────────────┘

RANGING MARKET
┌────────────────────────────────────────┐
│ Liquidity:  25%  ████████████░░░░░░░░  │
│ Momentum:   20%  ██████████░░░░░░░░░░  │ -10%
│ Sentiment:  25%  ████████████░░░░░░░░  │ +10%
│ On-Chain:   10%  █████░░░░░░░░░░░░░░  │
│ Volatility: 15%  ███████░░░░░░░░░░░░  │ +5%
│ Trend:       5%  ██░░░░░░░░░░░░░░░░░  │ -5%
└────────────────────────────────────────┘
```

---

## ✅ Key Takeaways

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  ✅ SELECTION: EVERY LOOP CYCLE (every 30 seconds)     │
│  ✅ FREQUENCY: Continuous, not one-time                │
│  ✅ ADAPTATION: Real-time market data                  │
│  ✅ SCORING: 6 factors with market regime weights      │
│  ✅ PROTECTION: Rate limiting, max 10 symbols/cycle    │
│  ✅ INTELLIGENCE: Adapts to market conditions          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

**Status:** ✅ **VISUAL GUIDE COMPLETE**
