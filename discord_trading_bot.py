#!/usr/bin/env python3
"""Discord Trading Bot - Real-time trading signals and performance metrics."""

import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from datetime import datetime
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Configuration
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

class TradingSignals(commands.Cog):
    """Trading signal cog for real-time updates."""
    
    def __init__(self, bot):
        self.bot = bot
        self.signal_loop.start()
        logger.info("✅ TradingSignals cog initialized")
    
    @tasks.loop(minutes=1)
    async def signal_loop(self):
        """Send trading signals every minute."""
        try:
            # Import here to avoid circular imports
            from trading_bot.analytics.daily_performance import get_performance_tracker
            
            tracker = get_performance_tracker()
            daily_stats = tracker.get_daily_performance()
            
            # Only send if there's activity
            if daily_stats.total_trades > 0:
                channel = self.bot.get_channel(CHANNEL_ID)
                if channel:
                    embed = self._create_performance_embed(daily_stats)
                    try:
                        await channel.send(embed=embed)
                    except Exception as e:
                        logger.error(f"Failed to send message: {e}")
        
        except Exception as e:
            logger.debug(f"Error in signal loop: {e}")
    
    def _create_performance_embed(self, stats):
        """Create Discord embed for performance."""
        color = discord.Color.green() if stats.total_pnl_usd > 0 else discord.Color.red()
        
        embed = discord.Embed(
            title="📊 Trading Bot Performance",
            description=f"Updated: {datetime.now().strftime('%H:%M:%S')}",
            color=color
        )
        
        embed.add_field(
            name="💰 Today's PnL",
            value=f"${stats.total_pnl_usd:.2f}",
            inline=True
        )
        
        embed.add_field(
            name="📈 Win Rate",
            value=f"{stats.win_rate:.1f}%",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Total Trades",
            value=f"{stats.total_trades}",
            inline=True
        )
        
        embed.add_field(
            name="✅ Winning Trades",
            value=f"{stats.winning_trades}",
            inline=True
        )
        
        embed.add_field(
            name="❌ Losing Trades",
            value=f"{stats.losing_trades}",
            inline=True
        )
        
        embed.add_field(
            name="📊 Avg Win",
            value=f"${stats.avg_win:.2f}",
            inline=True
        )
        
        return embed
    
    @commands.command()
    async def performance(self, ctx):
        """Get current performance metrics."""
        try:
            from trading_bot.analytics.daily_performance import get_performance_tracker
            
            tracker = get_performance_tracker()
            stats = tracker.get_daily_performance()
            summary = tracker.get_profit_summary(days=7)
            
            embed = discord.Embed(
                title="📊 Trading Performance Summary",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="📅 Today",
                value=f"PnL: ${stats.total_pnl_usd:.2f} | Win Rate: {stats.win_rate:.1f}%",
                inline=False
            )
            
            embed.add_field(
                name="📈 7-Day Summary",
                value=f"PnL: ${summary['total_pnl_usd']:.2f} | Trades: {summary['total_trades']}",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Win Rate (7-day)",
                value=f"{summary['win_rate_pct']:.1f}%",
                inline=False
            )
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
    
    @commands.command()
    async def trades(self, ctx, limit: int = 10):
        """Get recent trades."""
        try:
            from trading_bot.analytics.daily_performance import get_performance_tracker
            
            tracker = get_performance_tracker()
            recent_trades = tracker.trades[-limit:]
            
            if not recent_trades:
                await ctx.send("❌ No trades found")
                return
            
            embed = discord.Embed(
                title=f"📋 Last {len(recent_trades)} Trades",
                color=discord.Color.blue()
            )
            
            for trade in recent_trades:
                if trade.exit_price:
                    pnl = trade.pnl_usd or 0
                    pnl_pct = trade.pnl_percentage or 0
                    status = "✅" if pnl > 0 else "❌"
                    
                    embed.add_field(
                        name=f"{status} {trade.symbol}",
                        value=f"Entry: ${trade.entry_price:.6f}\nExit: ${trade.exit_price:.6f}\nPnL: ${pnl:.2f} ({pnl_pct:.2f}%)",
                        inline=False
                    )
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
    
    @commands.command()
    async def status(self, ctx):
        """Get bot status."""
        try:
            from trading_bot.monitoring.performance_monitor import get_performance_monitor
            
            monitor = get_performance_monitor()
            summary = monitor.get_performance_summary()
            
            embed = discord.Embed(
                title="🤖 Bot Status",
                color=discord.Color.green(),
                description="Bot is running and monitoring markets"
            )
            
            embed.add_field(
                name="⚙️ Status",
                value="✅ Online",
                inline=False
            )
            
            embed.add_field(
                name="📊 Performance",
                value=str(summary),
                inline=False
            )
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
    
    @commands.command()
    async def subscribe(self, ctx):
        """Subscribe to premium tier."""
        embed = discord.Embed(
            title="💳 Subscribe to Trading Bot Premium",
            description="Get real-time signals and advanced analytics",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="📊 Pro Tier - $29/month",
            value="✅ Real-time signals\n✅ Advanced analytics\n✅ Email alerts\n✅ Priority support",
            inline=False
        )
        
        embed.add_field(
            name="🏢 Enterprise Tier - $99/month",
            value="✅ Everything in Pro\n✅ Multiple bots\n✅ API access\n✅ Custom features",
            inline=False
        )
        
        embed.add_field(
            name="💰 Payment Instructions",
            value="**Bank Transfer to:**\n\n"
                  "Account Holder: Ahmed Sharf\n"
                  "Bank: Abu Dhabi Islamic Bank Egypt\n"
                  "Account Number: 200000550790\n"
                  "IBAN: EG7400305524000000200000550790\n"
                  "SWIFT: ABDIEGCADKI\n\n"
                  "**After payment:**\n"
                  "DM @Admin with proof of payment\n"
                  "You'll be added to premium role",
            inline=False
        )
        
        embed.set_footer(text="Questions? Use !help for support")
        await ctx.send(embed=embed)
    
    @commands.command()
    async def help(self, ctx):
        """Show help message."""
        embed = discord.Embed(
            title="📖 Trading Bot Commands",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="!performance",
            value="Get current performance metrics",
            inline=False
        )
        
        embed.add_field(
            name="!trades [limit]",
            value="Get recent trades (default: 10)",
            inline=False
        )
        
        embed.add_field(
            name="!status",
            value="Get bot status",
            inline=False
        )
        
        embed.add_field(
            name="!subscribe",
            value="Subscribe to premium tier",
            inline=False
        )
        
        embed.add_field(
            name="!help",
            value="Show this help message",
            inline=False
        )
        
        await ctx.send(embed=embed)

@bot.event
async def on_ready():
    """Bot ready event."""
    logger.info(f"✅ {bot.user} has connected to Discord!")
    if CHANNEL_ID > 0:
        logger.info(f"📊 Monitoring channel: {CHANNEL_ID}")
    else:
        logger.warning("⚠️ DISCORD_CHANNEL_ID not set - auto-updates disabled")
    
    # Set bot status
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="trading markets 📈"
    )
    await bot.change_presence(activity=activity)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found. Use !help for available commands.")
    else:
        logger.error(f"Command error: {error}")
        await ctx.send(f"❌ Error: {error}")

async def main():
    """Main function."""
    async with bot:
        # Load cog
        await bot.add_cog(TradingSignals(bot))
        logger.info("🤖 Starting Discord bot...")
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.error("❌ DISCORD_BOT_TOKEN not set in .env file!")
        exit(1)
    
    asyncio.run(main())
