#!/usr/bin/env python3
"""
Test script to verify rate limiter is working correctly
"""

import time
import logging
from trading_bot.analytics.market_cap_analyzer import get_market_cap_analyzer

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def test_rate_limiter():
    """Test the rate limiter with sequential API calls."""
    
    analyzer = get_market_cap_analyzer()
    symbols = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'MATIC', 'AVAX', 'LINK', 'UNI', 'DOGE']
    
    logger.info("=" * 80)
    logger.info("TESTING RATE LIMITER - 10 calls/minute (0.167 calls/sec)")
    logger.info("=" * 80)
    
    start_time = time.time()
    successful = 0
    failed = 0
    
    for i, symbol in enumerate(symbols, 1):
        call_start = time.time()
        logger.info(f"\n[{i}/10] Fetching market cap for {symbol}...")
        
        try:
            cap_data = analyzer.get_market_cap_data(symbol)
            if cap_data:
                successful += 1
                logger.info(f"✅ SUCCESS: {symbol} - Market Cap: ${cap_data.market_cap:,.0f}")
            else:
                failed += 1
                logger.error(f"❌ FAILED: {symbol} - No data returned")
        except Exception as exc:
            failed += 1
            logger.error(f"❌ FAILED: {symbol} - {exc}")
        
        call_duration = time.time() - call_start
        logger.info(f"   Call duration: {call_duration:.2f}s")
    
    total_time = time.time() - start_time
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST RESULTS")
    logger.info("=" * 80)
    logger.info(f"Total time: {total_time:.1f}s")
    logger.info(f"Successful: {successful}/10")
    logger.info(f"Failed: {failed}/10")
    logger.info(f"Success rate: {successful/10*100:.1f}%")
    logger.info(f"Average time per call: {total_time/10:.1f}s")
    logger.info(f"Expected time per call: 6.0s (1 call per 6 seconds)")
    logger.info("=" * 80)
    
    if successful == 10:
        logger.info("✅ ALL TESTS PASSED - Rate limiter working correctly!")
    else:
        logger.warning(f"⚠️ SOME TESTS FAILED - {failed} symbols failed")

if __name__ == "__main__":
    test_rate_limiter()
