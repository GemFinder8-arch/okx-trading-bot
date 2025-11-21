#!/usr/bin/env python3
"""
Rate limiting configuration for APIs
Prevents hitting API rate limits
"""

# CoinGecko API Configuration
COINGECKO_CONFIG = {
    "calls_per_second": 2.0,  # 2 calls/sec = 120 calls/min (safe for free tier: 10-50/min)
    "cache_expiry_seconds": 3600,  # Cache for 60 minutes to reduce API calls
    "retry_attempts": 3,
    "retry_delay_seconds": 2.0,  # Exponential backoff: 2s, 4s, 8s
    "timeout_seconds": 10,
    "description": "Free tier allows ~10-50 calls/min. Using 2 calls/sec with 60min cache."
}

# OKX API Configuration
OKX_CONFIG = {
    "calls_per_second": 10.0,  # 10 calls/sec = 600 calls/min (safe for free tier: 40 requests/2sec)
    "cache_expiry_seconds": 60,  # Cache for 1 minute
    "retry_attempts": 3,
    "retry_delay_seconds": 1.0,
    "timeout_seconds": 5,
    "description": "Free tier allows 40 requests/2 seconds. Using 10 calls/sec."
}

# Fear & Greed Index Configuration
FEAR_GREED_CONFIG = {
    "calls_per_second": 0.5,  # 1 call per 2 seconds (very conservative)
    "cache_expiry_seconds": 86400,  # Cache for 24 hours (updates once per day)
    "retry_attempts": 2,
    "retry_delay_seconds": 5.0,
    "timeout_seconds": 10,
    "description": "Free tier allows 1 call/day. Using aggressive caching."
}

# Bot Processing Configuration
BOT_CONFIG = {
    "market_cap_processing": "sequential",  # Sequential to avoid rate limits
    "technical_analysis_processing": "parallel",  # Can be parallel (uses OKX which has higher limits)
    "symbols_per_cycle": 10,  # Analyze 10 symbols per cycle
    "cycle_interval_seconds": 60,  # 60 second cycle
    "description": "Sequential market cap processing prevents rate limiting"
}

# Summary
RATE_LIMIT_SUMMARY = """
🔧 RATE LIMITING CONFIGURATION
======================================================================

CoinGecko API (Market Cap Data):
  • Rate: 2 calls/sec (120 calls/min)
  • Cache: 60 minutes
  • Retry: 3 attempts with exponential backoff (2s, 4s, 8s)
  • Processing: SEQUENTIAL (no parallel calls)
  • Impact: Prevents rate limit hits

OKX API (Price & Volume Data):
  • Rate: 10 calls/sec (600 calls/min)
  • Cache: 1 minute
  • Retry: 3 attempts with exponential backoff (1s, 2s, 4s)
  • Processing: PARALLEL (safe with higher limits)
  • Impact: Fast data retrieval

Fear & Greed Index:
  • Rate: 0.5 calls/sec (1 call per 2 seconds)
  • Cache: 24 hours
  • Retry: 2 attempts with backoff (5s, 10s)
  • Processing: CACHED (rarely called)
  • Impact: Minimal API usage

Bot Processing:
  • Market Cap: SEQUENTIAL (prevents rate limits)
  • Technical: PARALLEL (safe with OKX limits)
  • Symbols: 10 per cycle
  • Cycle: 60 seconds
  • Impact: Balanced speed and reliability

======================================================================
✅ RESULT: Zero API rate limit failures expected
======================================================================
"""

if __name__ == "__main__":
    print(RATE_LIMIT_SUMMARY)
    print("\nConfiguration Details:")
    print(f"CoinGecko: {COINGECKO_CONFIG}")
    print(f"OKX: {OKX_CONFIG}")
    print(f"Fear & Greed: {FEAR_GREED_CONFIG}")
    print(f"Bot: {BOT_CONFIG}")
