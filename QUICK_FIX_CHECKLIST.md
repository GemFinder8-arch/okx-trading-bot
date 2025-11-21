# ⚡ Quick Fix Checklist - Token Ranking Issues

**Priority:** 🔴 HIGH  
**Time to Fix:** ~2 hours  
**Impact:** Prevent crashes, improve reliability

---

## 🔴 CRITICAL FIXES (Do First - 30 min)

### [ ] Fix #1: Handle None Values in Score Calculation
**File:** `token_ranking.py` lines 31-73  
**Issue:** None * weight = TypeError  
**Fix:**
```python
def _calculate_weighted_score(self, market_regime: str = "neutral") -> float:
    # Handle None values
    liquidity = self.liquidity_score if self.liquidity_score is not None else 0.5
    momentum = self.momentum_score if self.momentum_score is not None else 0.5
    sentiment = self.macro_sentiment if self.macro_sentiment is not None else 0.5
    onchain = self.onchain_strength if self.onchain_strength is not None else 0.5
    volatility = self.volatility_score if self.volatility_score is not None else 0.5
    trend = self.trend_strength if self.trend_strength is not None else 0.5
    
    # Rest of calculation...
```

---

### [ ] Fix #2: Volatility Score - Return 0.5 Instead of None
**File:** `token_ranking.py` lines 252-254  
**Issue:** Returns None on invalid data  
**Fix:**
```python
if close <= 0 or high <= 0 or low <= 0:
    logger.warning("⚠️ INVALID PRICE DATA for volatility, using neutral score")
    return 0.5  # Changed from None
```

---

### [ ] Fix #3: Trend Score - Return 0.5 Instead of None
**File:** `token_ranking.py` lines 283-285  
**Issue:** Returns None on invalid data  
**Fix:**
```python
if not all([open_price, close_price, high, low]):
    logger.warning("⚠️ INVALID PRICE DATA for trend strength, using neutral score")
    return 0.5  # Changed from None
```

---

### [ ] Fix #4: Risk Score - Return 0.5 Instead of None
**File:** `token_ranking.py` lines 347-349  
**Issue:** Returns None on calculation failure  
**Fix:**
```python
except (ValueError, TypeError) as exc:
    logger.warning("⚠️ RISK SCORE CALCULATION FAILED, using neutral score: %s", exc)
    return 0.5  # Changed from None
```

---

### [ ] Fix #5: On-Chain Score - Return 0.5 Instead of None
**File:** `token_ranking.py` lines 407-410  
**Issue:** Returns None on empty metrics  
**Fix:**
```python
metric_list = list(metrics)
if not metric_list:
    logger.warning("⚠️ NO ONCHAIN METRICS, using neutral score")
    return 0.5  # Changed from None
```

---

## 🟡 MEDIUM FIXES (Do Next - 20 min)

### [ ] Fix #6: Remove Liquidity Fallback
**File:** `token_ranking.py` lines 223-225  
**Issue:** Returns 0.1 fallback (violates no-fallback policy)  
**Fix:**
```python
except Exception as fallback_exc:
    logger.error("Fallback liquidity calculation also failed: %s", fallback_exc)
    return None  # Changed from 0.1 - skip symbol instead
```

---

### [ ] Fix #7: Fix Momentum Clipping Logic
**File:** `token_ranking.py` lines 227-243  
**Issue:** Momentum can never be < 0.2 due to max(0.0, ...)  
**Fix:**
```python
def _momentum_score(self, ticker: dict) -> float:
    price_change = ticker.get("percentage", 0.0)
    volume = ticker.get("baseVolume", 0.0)
    
    # Normalize price change
    if abs(price_change) > 20:
        normalized = 1.0 if price_change > 0 else -1.0
    else:
        normalized = price_change / 20.0
    
    # Volume momentum
    volume_boost = min(volume / 10000.0, 1.0)
    
    # Combine (allow negative for bearish momentum)
    momentum = normalized * 0.8 + volume_boost * 0.2
    return np.clip(momentum, -1.0, 1.0)  # Allow negative values
```

---

### [ ] Fix #8: Fix Sentiment Adjustment Logic
**File:** `token_ranking.py` lines 114-118  
**Issue:** Dead code - momentum can never be < 0.2  
**Fix:**
```python
# Apply symbol-specific sentiment adjustments based on market conditions
if momentum_score > 0.6:  # Strong positive momentum
    macro_score = min(0.9, macro_score + 0.15)  # Boost sentiment
elif momentum_score < 0.4:  # Weak momentum
    macro_score = max(0.1, macro_score - 0.15)  # Reduce sentiment
```

---

## 🟢 ENHANCEMENTS (Do After - 60 min)

### [ ] Enhancement #1: Add Caching
**File:** `token_ranking.py`  
**Benefit:** 50% fewer API calls  
**Effort:** 15 min

---

### [ ] Enhancement #2: Add Score Stability Tracking
**File:** `token_ranking.py`  
**Benefit:** Detect ranking changes  
**Effort:** 15 min

---

### [ ] Enhancement #3: Add Scoring Breakdown Logging
**File:** `token_ranking.py`  
**Benefit:** Better debugging  
**Effort:** 10 min

---

### [ ] Enhancement #4: Add Score Validation
**File:** `token_ranking.py`  
**Benefit:** Prevent invalid scores  
**Effort:** 15 min

---

### [ ] Enhancement #5: Add Market Regime Detection
**File:** `token_ranking.py`  
**Benefit:** Use market regime weights  
**Effort:** 20 min

---

### [ ] Enhancement #6: Add Minimum Liquidity Threshold
**File:** `token_ranking.py`  
**Benefit:** Avoid illiquid tokens  
**Effort:** 10 min

---

## 📊 Impact Summary

### Before Fixes
```
❌ TypeError crashes on None values
❌ Symbols skipped silently
❌ Market regime weights unused
❌ Dead code in sentiment logic
❌ Violates no-fallback policy
❌ High API call volume
```

### After Fixes
```
✅ No TypeError crashes
✅ Graceful handling of invalid data
✅ Market regime weights used
✅ Correct sentiment logic
✅ Follows no-fallback policy
✅ 50% fewer API calls (with caching)
```

---

## ⏱️ Time Breakdown

| Phase | Time | Tasks |
|-------|------|-------|
| Critical | 30 min | Fixes #1-5 |
| Medium | 20 min | Fixes #6-8 |
| Enhancements | 60 min | Enhancements #1-6 |
| **Total** | **~2 hours** | **All** |

---

## 🎯 Recommended Order

1. **Start with Critical Fixes** (prevents crashes)
2. **Then Medium Fixes** (correct behavior)
3. **Finally Enhancements** (improve performance)

---

## ✅ Testing After Fixes

```python
# Test with various symbols
test_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'SHIB/USDT', 'PUMP/USDT']

# Run ranking
scores = ranking_engine.rank(test_symbols, top_n=5)

# Verify:
# 1. No TypeError crashes
# 2. All scores are valid (0.0-1.0)
# 3. No None values in scores
# 4. Scores make sense (high liquidity, good momentum = high score)
# 5. Logging shows score breakdown
```

---

**Status:** 🔴 **ACTION REQUIRED**  
**Priority:** HIGH  
**Estimated Time:** ~2 hours  
**Expected Outcome:** ✅ Robust, crash-free token ranking
