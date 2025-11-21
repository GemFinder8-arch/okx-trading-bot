"""Continuous trading loop for the OKX demo environment."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

from trading_bot.analytics.token_ranking import TokenRankingEngine
from trading_bot.config import (
    build_macro_provider,
    build_okx_connector,
    build_onchain_provider,
    load_from_env,
)
from trading_bot.config.enhanced_config import load_enhanced_config
from trading_bot.execution.parallel_executor import ParallelExecutor
from trading_bot.monitoring.logging import configure_logging
from trading_bot.monitoring.performance_monitor import get_performance_monitor, PerformanceTimer
from trading_bot.orchestration.pipeline import TradingPipeline
from trading_bot.storage.reporting import save_token_report


logger = logging.getLogger(__name__)


def _build_pipeline():
    load_dotenv()
    configure_logging(level=logging.INFO)
    
    # Load both legacy and enhanced configurations
    config = load_from_env()
    enhanced_config = load_enhanced_config()
    
    # Initialize performance monitoring
    performance_monitor = get_performance_monitor()
    
    okx = build_okx_connector(config)
    macro_provider = build_macro_provider(config, okx)
    onchain_provider = build_onchain_provider(config, okx)

    pipeline = TradingPipeline(
        config=config,
        okx=okx,
        macro_provider=macro_provider,
        onchain_provider=onchain_provider,
    )
    ranking_engine = TokenRankingEngine(okx, macro_provider, onchain_provider)
    
    # Use enhanced config for parallel executor
    parallel_executor = ParallelExecutor(
        max_workers=enhanced_config.performance.parallel_workers,
        rate_limit_per_second=enhanced_config.performance.rate_limit_per_second
    )
    
    logger.info("Enhanced trading system initialized with %d workers, %d calls/sec", 
               enhanced_config.performance.parallel_workers,
               enhanced_config.performance.rate_limit_per_second)
    
    return config, enhanced_config, okx, macro_provider, onchain_provider, pipeline, ranking_engine, parallel_executor


def _discover_symbols(okx, config) -> Iterable[str]:
    min_volume = config.bot.min_quote_volume_usd
    liquid = okx.fetch_liquid_spot_symbols(min_volume, quote_currency="USDT", limit=50)
    if liquid:
        symbols = [symbol for symbol, _ in liquid]
        logger.debug("Discovered %s liquid symbols", len(symbols))
        return symbols
    return list(config.bot.default_symbol_universe)


def run_loop() -> None:
    """Continuously scan markets and execute up to N trades per iteration."""

    (
        config,
        enhanced_config,
        okx,
        macro_provider,
        onchain_provider,
        pipeline,
        ranking_engine,
        parallel_executor,
    ) = _build_pipeline()
    report_path = Path("reports/latest_token_rankings.json")
    max_positions = config.bot.max_concurrent_positions
    interval = max(config.bot.polling_interval_seconds, 1)
    
    # Get performance monitor for main loop monitoring
    performance_monitor = get_performance_monitor()

    logger.info(
        "Starting enhanced trading loop (interval=%ss, max_positions=%s, min_volume=$%.0f)",
        interval,
        max_positions,
        config.bot.min_quote_volume_usd,
    )
    
    # Log enhanced configuration
    logger.info("Enhanced features enabled: regime=%s, sentiment=%s, risk=%s, parallel=%s",
               enhanced_config.enable_regime_detection,
               enhanced_config.enable_sentiment_analysis, 
               enhanced_config.enable_enhanced_risk,
               enhanced_config.enable_parallel_processing)

    try:
        iteration_count = 0
        while True:
            iteration_start = time.time()
            try:
                # Record iteration start
                performance_monitor.record_metric("main_loop", "iteration_start", time.time())
                
                with PerformanceTimer("main_loop", "symbol_discovery"):
                    candidate_symbols = _discover_symbols(okx, config)
                    restricted = pipeline.restricted_symbols
                    if restricted:
                        candidate_symbols = [sym for sym in candidate_symbols if sym not in restricted]
                
                performance_monitor.record_metric("main_loop", "candidate_symbols", len(candidate_symbols))
                performance_monitor.record_metric("main_loop", "restricted_symbols", len(restricted) if restricted else 0)
                
                if hasattr(macro_provider, "set_symbols"):
                    # keep macro insights aligned with current scan universe
                    macro_provider.set_symbols(candidate_symbols)
                
                with PerformanceTimer("main_loop", "token_ranking"):
                    ranking_sample_size = max(len(candidate_symbols), max_positions * 3)
                    scores = ranking_engine.rank(candidate_symbols, top_n=ranking_sample_size)
                    save_token_report(scores, report_path)

                # Reset circuit breakers if they're stuck (first iteration and more frequently)
                if iteration_count == 0 or iteration_count % 5 == 0:  # Reset every 5 iterations
                    try:
                        pipeline._okx.reset_circuit_breakers()
                        logger.info("🔄 Circuit breakers reset (iteration %d)", iteration_count)
                    except Exception as exc:
                        logger.warning("Could not reset circuit breakers: %s", exc)
                
                # COMPLETE PORTFOLIO MANAGEMENT - Manage ALL assets (not just active positions)
                pipeline.manage_all_assets()
                
                # INTELLIGENT POSITION MANAGEMENT - Manage existing positions
                pipeline.manage_all_positions()
                
                # PORTFOLIO OPTIMIZATION - Periodic rebalancing (every 6 iterations)
                if iteration_count % 6 == 0 and iteration_count > 0:
                    try:
                        logger.info("🔄 PERIODIC PORTFOLIO OPTIMIZATION CHECK")
                        # Portfolio rebalancing is handled within manage_all_positions()
                        # This is just a periodic reminder/check
                    except Exception as exc:
                        logger.warning("Portfolio optimization check failed: %s", exc)
                
                # DEBUG: Check available slots for new positions
                available_slots_debug = max_positions - len(pipeline.open_positions)
                open_positions_list = list(pipeline.open_positions.keys())
                logger.info("🎯 TRADING SLOTS: %d open positions, %d available slots for new trades", 
                           len(pipeline.open_positions), available_slots_debug)
                logger.info("📊 CURRENT POSITIONS: %s", open_positions_list if open_positions_list else "None")
                
                # Optimized parallel execution
                executed = []
                available_slots = max_positions - len(pipeline.open_positions)
                
                if available_slots > 0:
                    # Select symbols to analyze (limit to prevent rate limiting)
                    # Analyze up to 15 symbols per cycle (independent of available slots)
                    # This allows more analysis even if we can only execute a few trades
                    max_symbols_to_analyze = 15  # Max 15 symbols per cycle (increased from 10)
                    symbols_to_analyze = [token.symbol for token in scores[:max_symbols_to_analyze]]
                    
                    # SEQUENTIAL market data fetching using OKX native API
                    logger.info("Fetching market data for %d symbols SEQUENTIALLY (prevents rate limiting)", len(symbols_to_analyze))
                    from trading_bot.analytics.market_cap_analyzer import get_market_cap_analyzer
                    market_cap_analyzer = get_market_cap_analyzer(okx)
                    
                    market_data_batch = {}
                    for symbol in symbols_to_analyze:
                        try:
                            # Get market cap data sequentially (respects rate limiter)
                            cap_data = market_cap_analyzer.get_market_cap_data(symbol)
                            market_data_batch[symbol] = cap_data
                        except Exception as exc:
                            logger.debug("Failed to fetch market data for %s: %s", symbol, exc)
                            market_data_batch[symbol] = None
                    
                    # Process symbols with valid market data
                    valid_symbols = [symbol for symbol, data in market_data_batch.items() if data]
                    logger.info("Processing %d symbols with valid market data", len(valid_symbols))
                    
                    # Sequential execution for trading decisions (requires stateful pipeline)
                    # NOTE: Market cap data is already cached from above, so pipeline.run_cycle() will use cache
                    for symbol in valid_symbols[:available_slots]:
                        if len(pipeline.open_positions) >= max_positions:
                            break
                        try:
                            result = pipeline.run_cycle(symbol)
                            executed.append(result)
                        except Exception as exc:  # noqa: BLE001
                            logger.exception("Pipeline cycle failed for %s: %s", symbol, exc)
                
                # Log performance stats and record metrics
                perf_stats = parallel_executor.get_performance_stats()
                performance_monitor.record_metric("parallel_executor", "calls_per_minute", perf_stats.get("calls_per_minute", 0))
                performance_monitor.record_metric("main_loop", "valid_symbols", len(valid_symbols) if 'valid_symbols' in locals() else 0)
                performance_monitor.record_metric("main_loop", "executed_trades", len(executed))
                
                logger.debug("Parallel executor stats: %s", perf_stats)

                executions_summary = ", ".join(
                    f"{res.symbol}:{res.decision}:{'EXEC' if res.executed else 'SKIP'}"
                    for res in executed
                )
                logger.info("Iteration summary: %s", executions_summary or "no executions")
            except Exception as exc:  # noqa: BLE001
                logger.exception("Trading iteration error: %s", exc)

            elapsed = time.time() - iteration_start
            performance_monitor.record_metric("main_loop", "iteration_time", elapsed, "seconds")
            performance_monitor.record_success_rate("main_loop", "iteration", True)
            iteration_count += 1
            
            # Log performance summary every 10 iterations
            if int(time.time()) % 600 == 0:  # Every 10 minutes
                summary = performance_monitor.get_performance_summary()
                logger.info("Performance summary: %s", summary)
                
                # Log daily trading performance
                from trading_bot.analytics.daily_performance import get_performance_tracker
                daily_tracker = get_performance_tracker()
                daily_stats = daily_tracker.get_daily_performance()
                profit_summary = daily_tracker.get_profit_summary(days=7)
                
                logger.info(
                    "📊 DAILY PERFORMANCE: %d trades, %.1f%% win rate, $%.2f PnL today",
                    daily_stats.total_trades, daily_stats.win_rate, daily_stats.total_pnl_usd
                )
                logger.info(
                    "📈 7-DAY SUMMARY: %.1f%% win rate, $%.2f total PnL, $%.2f avg daily",
                    profit_summary["win_rate_pct"], profit_summary["total_pnl_usd"], 
                    profit_summary["avg_daily_profit"]
                )
                
                # Generate Excel report every 4 hours
                if iteration_count % 24 == 0 and iteration_count > 0:  # Every 24 iterations (~4 hours)
                    try:
                        from trading_bot.reporting.excel_reporter import generate_trading_report
                        report_path = generate_trading_report(days_back=7)
                        if report_path:
                            logger.info("📊 EXCEL REPORT GENERATED: %s", report_path)
                        else:
                            logger.warning("Failed to generate Excel report")
                    except Exception as exc:
                        logger.error("Excel report generation failed: %s", exc)
            
            sleep_for = max(interval - elapsed, 0)
            if sleep_for:
                time.sleep(sleep_for)
    except KeyboardInterrupt:
        logger.info("Received interrupt, stopping trading loop")


if __name__ == "__main__":
    run_loop()
