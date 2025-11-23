#!/usr/bin/env python3
"""Start both trading bot and Discord bot together."""

import asyncio
import logging
import threading
from trading_bot.main import run_loop
from discord_trading_bot import main as discord_main, DISCORD_TOKEN

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_trading_bot():
    """Run the trading bot in a separate thread."""
    try:
        logger.info("🤖 Starting Trading Bot...")
        run_loop()
    except Exception as e:
        logger.error(f"❌ Trading Bot Error: {e}", exc_info=True)

async def run_discord_bot():
    """Run the Discord bot."""
    try:
        logger.info("💬 Starting Discord Bot...")
        await discord_main()
    except Exception as e:
        logger.error(f"❌ Discord Bot Error: {e}", exc_info=True)

def main():
    """Start both bots."""
    if not DISCORD_TOKEN:
        logger.error("❌ DISCORD_BOT_TOKEN not set!")
        return
    
    # Start trading bot in a separate thread
    trading_thread = threading.Thread(target=run_trading_bot, daemon=True)
    trading_thread.start()
    logger.info("✅ Trading Bot thread started")
    
    # Run Discord bot in main thread
    try:
        asyncio.run(run_discord_bot())
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down...")

if __name__ == "__main__":
    main()
