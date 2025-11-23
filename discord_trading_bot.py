#!/usr/bin/env python3
"""Discord Trading Bot - Real-time trading signals and performance metrics."""

import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio
import logging
import json
from pathlib import Path

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

# Cache for performance data
performance_cache = {
    "last_update": None,
    "data": None
}

# Custom Views for Button Navigation
class MainMenuView(View):
    """Main menu with navigation buttons."""
    
    def __init__(self, cog):
        super().__init__(timeout=None)  # Never timeout
        self.cog = cog
    
    @discord.ui.button(label="📊 Performance", style=discord.ButtonStyle.primary, emoji="📊")
    async def performance_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_performance(interaction)
    
    @discord.ui.button(label="📅 Daily", style=discord.ButtonStyle.primary, emoji="📅")
    async def daily_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_daily(interaction)
    
    @discord.ui.button(label="📈 Trades", style=discord.ButtonStyle.primary, emoji="📈")
    async def trades_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_trades(interaction)
    
    @discord.ui.button(label="🏆 Top Symbols", style=discord.ButtonStyle.success, emoji="🏆")
    async def toptraders_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_toptraders(interaction)
    
    @discord.ui.button(label="💼 Portfolio", style=discord.ButtonStyle.success, emoji="💼")
    async def portfolio_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_portfolio(interaction)
    
    @discord.ui.button(label="📊 Analytics", style=discord.ButtonStyle.success, emoji="📊")
    async def analytics_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_analytics(interaction)
    
    @discord.ui.button(label="⚙️ Settings", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def settings_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_settings(interaction)
    
    @discord.ui.button(label="💳 Subscribe", style=discord.ButtonStyle.danger, emoji="💳")
    async def subscribe_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_subscribe(interaction)

class TradeDetailsView(View):
    """View for detailed trade information."""
    
    def __init__(self, trades, cog):
        super().__init__(timeout=300)
        self.trades = trades
        self.cog = cog
        self.current_page = 0
    
    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.secondary)
    async def previous_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_trade_display(interaction)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.trades) - 1:
            self.current_page += 1
            await self.update_trade_display(interaction)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.primary)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_trade_display(interaction)
    
    @discord.ui.button(label="📊 Back to Menu", style=discord.ButtonStyle.danger)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
    
    async def update_trade_display(self, interaction: discord.Interaction):
        trade = self.trades[self.current_page]
        embed = self.cog._create_detailed_trade_embed(trade, self.current_page + 1, len(self.trades))
        await interaction.response.edit_message(embed=embed, view=self)

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
    
    def _create_detailed_trade_embed(self, trade, page: int = 1, total_pages: int = 1):
        """Create detailed trade embed with all information."""
        pnl = trade.pnl_usd or 0
        pnl_pct = trade.pnl_percentage or 0
        status = "✅ WIN" if pnl > 0 else "❌ LOSS" if pnl < 0 else "⚪ BREAK EVEN"
        color = discord.Color.green() if pnl > 0 else discord.Color.red() if pnl < 0 else discord.Color.greyple()
        
        embed = discord.Embed(
            title=f"{status} {trade.symbol}",
            color=color,
            description=f"Trade {page}/{total_pages}"
        )
        
        # Entry Information
        embed.add_field(
            name="📍 Entry",
            value=f"Price: ${trade.entry_price:.8f}\n"
                  f"Time: {trade.entry_time.strftime('%Y-%m-%d %H:%M:%S') if trade.entry_time else 'N/A'}\n"
                  f"Amount: {trade.amount:.6f}",
            inline=False
        )
        
        # Exit Information
        if trade.exit_price:
            embed.add_field(
                name="📍 Exit",
                value=f"Price: ${trade.exit_price:.8f}\n"
                      f"Time: {trade.exit_time.strftime('%Y-%m-%d %H:%M:%S') if trade.exit_time else 'N/A'}\n"
                      f"Reason: {trade.exit_reason or 'N/A'}",
                inline=False
            )
        
        # P&L Information
        embed.add_field(
            name="💰 Profit & Loss",
            value=f"PnL: ${pnl:.2f}\n"
                  f"PnL %: {pnl_pct:.2f}%\n"
                  f"ROI: {(pnl_pct):.2f}%",
            inline=True
        )
        
        # Trade Details
        embed.add_field(
            name="📊 Trade Details",
            value=f"Confidence: {getattr(trade, 'confidence', 'N/A')}\n"
                  f"Confluence: {getattr(trade, 'confluence', 'N/A')}\n"
                  f"Risk/Reward: {getattr(trade, 'risk_reward_ratio', 'N/A')}",
            inline=True
        )
        
        # TP/SL Information
        tp_value = getattr(trade, 'take_profit', None)
        sl_value = getattr(trade, 'stop_loss', None)
        
        tp_text = f"${tp_value:.8f}" if tp_value else "Not Set"
        sl_text = f"${sl_value:.8f}" if sl_value else "Not Set"
        
        embed.add_field(
            name="🎯 Take Profit / Stop Loss",
            value=f"TP: {tp_text}\n"
                  f"SL: {sl_text}",
            inline=False
        )
        
        # Additional Metrics
        embed.add_field(
            name="📈 Metrics",
            value=f"Duration: {getattr(trade, 'duration', 'N/A')}\n"
                  f"Max Drawdown: {getattr(trade, 'max_drawdown', 'N/A')}\n"
                  f"Status: {'Closed' if trade.exit_price else 'Open'}",
            inline=True
        )
        
        embed.set_footer(text=f"Trade ID: {getattr(trade, 'id', 'N/A')} | Updated: {datetime.now().strftime('%H:%M:%S')}")
        return embed
    
    # Button callback methods
    async def show_performance(self, interaction: discord.Interaction):
        """Show performance metrics."""
        try:
            from trading_bot.analytics.daily_performance import DailyPerformanceTracker
            
            # Create fresh instance to reload data from files
            tracker = DailyPerformanceTracker()
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
                value=f"PnL: ${summary.get('total_pnl_usd', 0):.2f} | Trades: {summary.get('total_trades', 0)}",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Win Rate (7-day)",
                value=f"{summary.get('win_rate_pct', 0):.1f}%",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def show_daily(self, interaction: discord.Interaction):
        """Show today's performance."""
        try:
            from trading_bot.analytics.daily_performance import DailyPerformanceTracker
            
            tracker = DailyPerformanceTracker()
            stats = tracker.get_daily_performance()
            
            color = discord.Color.green() if stats.total_pnl_usd > 0 else discord.Color.red()
            
            embed = discord.Embed(
                title="📅 Today's Performance",
                color=color
            )
            
            embed.add_field(name="💰 PnL", value=f"${stats.total_pnl_usd:.2f}", inline=True)
            embed.add_field(name="📈 Trades", value=f"{stats.total_trades}", inline=True)
            embed.add_field(name="🎯 Win Rate", value=f"{stats.win_rate:.1f}%", inline=True)
            embed.add_field(name="✅ Wins", value=f"{stats.winning_trades}", inline=True)
            embed.add_field(name="❌ Losses", value=f"{stats.losing_trades}", inline=True)
            embed.add_field(name="💵 Best Trade", value=f"${stats.best_trade:.2f}", inline=True)
            
            embed.set_footer(text=f"Updated: {datetime.now().strftime('%H:%M:%S')}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def show_trades(self, interaction: discord.Interaction):
        """Show detailed trades with pagination."""
        try:
            from trading_bot.analytics.daily_performance import DailyPerformanceTracker
            
            tracker = DailyPerformanceTracker()
            recent_trades = tracker.trades[-10:] if tracker.trades else []
            
            if not recent_trades:
                await interaction.response.send_message("❌ No trades found", ephemeral=True)
                return
            
            # Reverse to show newest first
            recent_trades = list(reversed(recent_trades))
            
            view = TradeDetailsView(recent_trades, self)
            embed = self._create_detailed_trade_embed(recent_trades[0], 1, len(recent_trades))
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def show_toptraders(self, interaction: discord.Interaction):
        """Show top performing symbols."""
        try:
            from trading_bot.analytics.daily_performance import DailyPerformanceTracker
            
            tracker = DailyPerformanceTracker()
            
            symbol_stats = {}
            for trade in tracker.trades:
                if trade.symbol not in symbol_stats:
                    symbol_stats[trade.symbol] = {"pnl": 0, "trades": 0, "wins": 0}
                
                symbol_stats[trade.symbol]["trades"] += 1
                symbol_stats[trade.symbol]["pnl"] += trade.pnl_usd or 0
                if (trade.pnl_usd or 0) > 0:
                    symbol_stats[trade.symbol]["wins"] += 1
            
            sorted_symbols = sorted(symbol_stats.items(), key=lambda x: x[1]["pnl"], reverse=True)[:5]
            
            embed = discord.Embed(title="🏆 Top Performing Symbols", color=discord.Color.gold())
            
            for i, (symbol, stats) in enumerate(sorted_symbols, 1):
                win_rate = (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0
                embed.add_field(
                    name=f"#{i} {symbol}",
                    value=f"PnL: ${stats['pnl']:.2f} | Trades: {stats['trades']} | Win Rate: {win_rate:.1f}%",
                    inline=False
                )
            
            if not sorted_symbols:
                embed.description = "No trades yet"
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def show_portfolio(self, interaction: discord.Interaction):
        """Show portfolio overview."""
        try:
            from trading_bot.analytics.daily_performance import DailyPerformanceTracker
            
            tracker = DailyPerformanceTracker()
            summary = tracker.get_profit_summary(days=30)
            
            embed = discord.Embed(title="💼 Portfolio Overview", color=discord.Color.blue())
            
            embed.add_field(name="📊 30-Day Performance", value=f"${summary.get('total_pnl_usd', 0):.2f}", inline=True)
            embed.add_field(name="📈 Total Trades", value=f"{summary.get('total_trades', 0)}", inline=True)
            embed.add_field(name="🎯 Win Rate", value=f"{summary.get('win_rate_pct', 0):.1f}%", inline=True)
            embed.add_field(name="📊 Profit Factor", value=f"{summary.get('profit_factor', 0):.2f}x", inline=True)
            embed.add_field(name="🎲 Best Trade", value=f"${summary.get('best_trade', 0):.2f}", inline=True)
            embed.add_field(name="💸 Worst Trade", value=f"${summary.get('worst_trade', 0):.2f}", inline=True)
            
            embed.set_footer(text="Premium feature - Subscribe for more details")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def show_subscribe(self, interaction: discord.Interaction):
        """Show subscription options."""
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
        
        embed.set_footer(text="Questions? Use !menu for support")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def show_analytics(self, interaction: discord.Interaction):
        """Show advanced analytics and insights."""
        try:
            from trading_bot.analytics.daily_performance import DailyPerformanceTracker
            
            tracker = DailyPerformanceTracker()
            summary_7d = tracker.get_profit_summary(days=7)
            summary_30d = tracker.get_profit_summary(days=30)
            
            embed = discord.Embed(
                title="📊 Advanced Analytics",
                color=discord.Color.blurple(),
                description="Detailed trading insights and metrics"
            )
            
            # 7-Day Analysis
            embed.add_field(
                name="📈 7-Day Analysis",
                value=f"PnL: ${summary_7d.get('total_pnl_usd', 0):.2f}\n"
                      f"Trades: {summary_7d.get('total_trades', 0)}\n"
                      f"Win Rate: {summary_7d.get('win_rate_pct', 0):.1f}%\n"
                      f"Daily Avg: ${summary_7d.get('avg_daily_profit', 0):.2f}",
                inline=True
            )
            
            # 30-Day Analysis
            embed.add_field(
                name="📊 30-Day Analysis",
                value=f"PnL: ${summary_30d.get('total_pnl_usd', 0):.2f}\n"
                      f"Trades: {summary_30d.get('total_trades', 0)}\n"
                      f"Win Rate: {summary_30d.get('win_rate_pct', 0):.1f}%\n"
                      f"Daily Avg: ${summary_30d.get('avg_daily_profit', 0):.2f}",
                inline=True
            )
            
            # Risk Metrics
            embed.add_field(
                name="⚠️ Risk Metrics",
                value=f"Profit Factor: {summary_30d.get('profit_factor', 0):.2f}x\n"
                      f"Best Trade: ${summary_30d.get('best_trade', 0):.2f}\n"
                      f"Worst Trade: ${summary_30d.get('worst_trade', 0):.2f}",
                inline=False
            )
            
            embed.set_footer(text="Premium Analytics | Updated: " + datetime.now().strftime('%H:%M:%S'))
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def show_settings(self, interaction: discord.Interaction):
        """Show bot settings and preferences."""
        embed = discord.Embed(
            title="⚙️ Bot Settings & Preferences",
            color=discord.Color.greyple(),
            description="Configure your trading bot experience"
        )
        
        embed.add_field(
            name="🔔 Notifications",
            value="✅ Trade Alerts: ON\n"
                  "✅ Daily Reports: ON\n"
                  "✅ Risk Warnings: ON\n"
                  "✅ Performance Updates: ON",
            inline=False
        )
        
        embed.add_field(
            name="📊 Display Settings",
            value="• Trade Details: Full\n"
                  "• Chart Updates: Real-time\n"
                  "• Decimal Places: 2\n"
                  "• Currency: USD",
            inline=False
        )
        
        embed.add_field(
            name="🛡️ Risk Management",
            value="• Max Position Size: $1000\n"
                  "• Daily Loss Limit: $500\n"
                  "• Stop Loss: Enabled\n"
                  "• Take Profit: Enabled",
            inline=False
        )
        
        embed.add_field(
            name="💡 Pro Tip",
            value="Upgrade to Premium to customize these settings!",
            inline=False
        )
        
        embed.set_footer(text="Settings | Contact admin for changes")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @commands.command()
    async def menu(self, ctx):
        """Show main menu with buttons."""
        embed = discord.Embed(
            title="🤖 Trading Bot Dashboard",
            description="Click buttons below to navigate",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📊 Performance",
            value="View current performance metrics",
            inline=True
        )
        
        embed.add_field(
            name="📅 Daily",
            value="Today's performance summary",
            inline=True
        )
        
        embed.add_field(
            name="📈 Trades",
            value="Detailed trade information",
            inline=True
        )
        
        embed.add_field(
            name="🏆 Top Symbols",
            value="Best performing symbols",
            inline=True
        )
        
        embed.add_field(
            name="💼 Portfolio",
            value="30-day portfolio overview",
            inline=True
        )
        
        embed.add_field(
            name="💳 Subscribe",
            value="Premium subscription options",
            inline=True
        )
        
        view = MainMenuView(self)
        await ctx.send(embed=embed, view=view)
    
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
    async def stats(self, ctx, days: int = 30):
        """Get detailed statistics for the last N days."""
        try:
            from trading_bot.analytics.daily_performance import get_performance_tracker
            
            tracker = get_performance_tracker()
            summary = tracker.get_profit_summary(days=days)
            
            embed = discord.Embed(
                title=f"📊 Trading Statistics ({days} Days)",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="💰 Total PnL",
                value=f"${summary.get('total_pnl_usd', 0):.2f}",
                inline=True
            )
            
            embed.add_field(
                name="📈 Total Trades",
                value=f"{summary.get('total_trades', 0)}",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Win Rate",
                value=f"{summary.get('win_rate_pct', 0):.1f}%",
                inline=True
            )
            
            embed.add_field(
                name="✅ Wins",
                value=f"{summary.get('winning_trades', 0)}",
                inline=True
            )
            
            embed.add_field(
                name="❌ Losses",
                value=f"{summary.get('losing_trades', 0)}",
                inline=True
            )
            
            embed.add_field(
                name="💵 Avg Win",
                value=f"${summary.get('avg_win', 0):.2f}",
                inline=True
            )
            
            embed.add_field(
                name="💸 Avg Loss",
                value=f"${summary.get('avg_loss', 0):.2f}",
                inline=True
            )
            
            embed.add_field(
                name="📊 Profit Factor",
                value=f"{summary.get('profit_factor', 0):.2f}",
                inline=True
            )
            
            embed.add_field(
                name="🎲 Best Trade",
                value=f"${summary.get('best_trade', 0):.2f}",
                inline=True
            )
            
            embed.set_footer(text=f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command()
    async def daily(self, ctx):
        """Get today's performance summary."""
        try:
            from trading_bot.analytics.daily_performance import get_performance_tracker
            
            tracker = get_performance_tracker()
            stats = tracker.get_daily_performance()
            
            color = discord.Color.green() if stats.total_pnl_usd > 0 else discord.Color.red()
            
            embed = discord.Embed(
                title="📅 Today's Performance",
                color=color
            )
            
            embed.add_field(
                name="💰 PnL",
                value=f"${stats.total_pnl_usd:.2f}",
                inline=True
            )
            
            embed.add_field(
                name="📈 Trades",
                value=f"{stats.total_trades}",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Win Rate",
                value=f"{stats.win_rate:.1f}%",
                inline=True
            )
            
            embed.add_field(
                name="✅ Wins",
                value=f"{stats.winning_trades}",
                inline=True
            )
            
            embed.add_field(
                name="❌ Losses",
                value=f"{stats.losing_trades}",
                inline=True
            )
            
            embed.add_field(
                name="💵 Best Trade",
                value=f"${stats.best_trade:.2f}",
                inline=True
            )
            
            embed.set_footer(text=f"Updated: {datetime.now().strftime('%H:%M:%S')}")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command()
    async def toptraders(self, ctx):
        """Get top performing symbols."""
        try:
            from trading_bot.analytics.daily_performance import get_performance_tracker
            
            tracker = get_performance_tracker()
            
            # Group trades by symbol and calculate PnL
            symbol_stats = {}
            for trade in tracker.trades:
                if trade.symbol not in symbol_stats:
                    symbol_stats[trade.symbol] = {"pnl": 0, "trades": 0, "wins": 0}
                
                symbol_stats[trade.symbol]["trades"] += 1
                symbol_stats[trade.symbol]["pnl"] += trade.pnl_usd or 0
                if (trade.pnl_usd or 0) > 0:
                    symbol_stats[trade.symbol]["wins"] += 1
            
            # Sort by PnL
            sorted_symbols = sorted(symbol_stats.items(), key=lambda x: x[1]["pnl"], reverse=True)[:5]
            
            embed = discord.Embed(
                title="🏆 Top Performing Symbols",
                color=discord.Color.gold()
            )
            
            for i, (symbol, stats) in enumerate(sorted_symbols, 1):
                win_rate = (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0
                embed.add_field(
                    name=f"#{i} {symbol}",
                    value=f"PnL: ${stats['pnl']:.2f} | Trades: {stats['trades']} | Win Rate: {win_rate:.1f}%",
                    inline=False
                )
            
            if not sorted_symbols:
                embed.description = "No trades yet"
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command()
    async def alerts(self, ctx):
        """Get trading alerts and notifications."""
        embed = discord.Embed(
            title="🔔 Trading Alerts",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="📢 Alert Settings",
            value="React with ✅ to enable alerts\n"
                  "🔴 Large Loss Alert (>$100)\n"
                  "🟢 Large Win Alert (>$100)\n"
                  "📊 Daily Summary\n"
                  "⚠️ Risk Warnings",
            inline=False
        )
        
        embed.add_field(
            name="💡 Pro Tip",
            value="Enable alerts to get notified of important trading events",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def portfolio(self, ctx):
        """Get portfolio overview."""
        try:
            from trading_bot.analytics.daily_performance import get_performance_tracker
            
            tracker = get_performance_tracker()
            summary = tracker.get_profit_summary(days=30)
            
            embed = discord.Embed(
                title="💼 Portfolio Overview",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="📊 30-Day Performance",
                value=f"${summary.get('total_pnl_usd', 0):.2f}",
                inline=True
            )
            
            embed.add_field(
                name="📈 Total Trades",
                value=f"{summary.get('total_trades', 0)}",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Win Rate",
                value=f"{summary.get('win_rate_pct', 0):.1f}%",
                inline=True
            )
            
            embed.add_field(
                name="📊 Profit Factor",
                value=f"{summary.get('profit_factor', 0):.2f}x",
                inline=True
            )
            
            embed.add_field(
                name="🎲 Best Trade",
                value=f"${summary.get('best_trade', 0):.2f}",
                inline=True
            )
            
            embed.add_field(
                name="💸 Worst Trade",
                value=f"${summary.get('worst_trade', 0):.2f}",
                inline=True
            )
            
            embed.set_footer(text="Premium feature - Subscribe for more details")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command()
    async def invite(self, ctx):
        """Get bot invite link."""
        embed = discord.Embed(
            title="📨 Invite Friends",
            description="Share the bot with your trading community!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🔗 Server Link",
            value="Share this server with friends to get early access",
            inline=False
        )
        
        embed.add_field(
            name="💰 Referral Bonus",
            value="Refer 3 friends and get 1 month free premium!",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def help(self, ctx):
        """Show help message."""
        embed = discord.Embed(
            title="📖 Trading Bot Commands",
            color=discord.Color.blue(),
            description="Complete list of available commands"
        )
        
        embed.add_field(
            name="📊 Performance Commands",
            value="!performance - Get current metrics\n"
                  "!daily - Today's performance\n"
                  "!stats [days] - Statistics for N days\n"
                  "!portfolio - 30-day portfolio overview",
            inline=False
        )
        
        embed.add_field(
            name="📈 Trade Commands",
            value="!trades [limit] - Get recent trades\n"
                  "!toptraders - Top performing symbols",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Bot Commands",
            value="!status - Get bot status\n"
                  "!alerts - Trading alerts settings\n"
                  "!invite - Invite friends",
            inline=False
        )
        
        embed.add_field(
            name="💳 Premium Commands",
            value="!subscribe - Subscribe to premium\n"
                  "!help - Show this help message",
            inline=False
        )
        
        embed.add_field(
            name="💡 Tips",
            value="• Use !stats 7 for weekly stats\n"
                  "• Use !stats 30 for monthly stats\n"
                  "• Use !trades 20 for more trades\n"
                  "• Premium members get more features",
            inline=False
        )
        
        embed.set_footer(text="Questions? DM @Admin for support")
        await ctx.send(embed=embed)

@bot.event
async def on_ready():
    """Bot ready event."""
    logger.info(f"✅ {bot.user} has connected to Discord!")
    if CHANNEL_ID > 0:
        logger.info(f"📊 Monitoring channel: {CHANNEL_ID}")
    else:
        logger.warning("⚠️ DISCORD_CHANNEL_ID not set - auto-updates disabled")
    
    # Set bot status with rotating activity
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="🚀 Trading Markets | !menu for dashboard"
    )
    await bot.change_presence(activity=activity)
    
    # Post welcome message with menu to monitoring channel if set
    if CHANNEL_ID > 0:
        try:
            channel = bot.get_channel(CHANNEL_ID)
            if channel:
                # Check if welcome message already exists
                async for message in channel.history(limit=10):
                    if message.author == bot.user and "Trading Bot Dashboard" in message.content:
                        return  # Already posted
                
                # Post new welcome message
                embed = discord.Embed(
                    title="🤖 Trading Bot Dashboard",
                    description="Welcome to the OKX Trading Bot! Click buttons below to access all features.",
                    color=discord.Color.gold()
                )
                
                embed.add_field(
                    name="📊 Features",
                    value="• Real-time trading signals\n"
                          "• Performance analytics\n"
                          "• Advanced risk management\n"
                          "• Premium insights",
                    inline=False
                )
                
                embed.add_field(
                    name="🚀 Get Started",
                    value="Click any button below to explore!",
                    inline=False
                )
                
                embed.set_footer(text="OKX Trading Bot | 24/7 Automated Trading")
                
                cog = bot.get_cog("TradingSignals")
                if cog:
                    await channel.send(embed=embed, view=MainMenuView(cog))
        except Exception as e:
            logger.error(f"Could not post welcome message: {e}")

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
