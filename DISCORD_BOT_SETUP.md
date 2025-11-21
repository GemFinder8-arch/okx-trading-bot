# 🤖 Discord Trading Bot - Complete Setup Guide

## Quick Start (30 minutes to launch)

### Step 1: Create Discord Bot (5 minutes)

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Name it "Trading Bot"
4. Go to "Bot" tab → Click "Add Bot"
5. Copy the TOKEN (keep it secret!)
6. Enable these Intents:
   - Message Content Intent
   - Server Members Intent
   - Presence Intent

### Step 2: Set Bot Permissions (5 minutes)

1. Go to OAuth2 → URL Generator
2. Select scopes: `bot`
3. Select permissions:
   - Send Messages
   - Embed Links
   - Read Message History
   - Manage Webhooks
4. Copy the generated URL
5. Open it in browser to add bot to your server

### Step 3: Install Dependencies (2 minutes)

```bash
pip install discord.py python-dotenv aiohttp
```

### Step 4: Create Bot File (10 minutes)

Create `discord_trading_bot.py`:

```python
import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from datetime import datetime
import asyncio

load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))  # Where to send signals

class TradingSignals(commands.Cog):
    """Trading signal cog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.signal_loop.start()
    
    @tasks.loop(minutes=1)
    async def signal_loop(self):
        """Send trading signals every minute"""
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
                    await channel.send(embed=embed)
        
        except Exception as e:
            print(f"Error in signal loop: {e}")
    
    def _create_performance_embed(self, stats):
        """Create Discord embed for performance"""
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
        """Get current performance"""
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
    
    @commands.command()
    async def trades(self, ctx, limit: int = 10):
        """Get recent trades"""
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
    
    @commands.command()
    async def status(self, ctx):
        """Get bot status"""
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
    
    @commands.command()
    async def help(self, ctx):
        """Show help message"""
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
            name="!help",
            value="Show this help message",
            inline=False
        )
        
        await ctx.send(embed=embed)

@bot.event
async def on_ready():
    """Bot ready event"""
    print(f"✅ {bot.user} has connected to Discord!")
    print(f"📊 Monitoring channel: {CHANNEL_ID}")
    
    # Set bot status
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="trading markets 📈"
    )
    await bot.change_presence(activity=activity)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found. Use !help for available commands.")
    else:
        await ctx.send(f"❌ Error: {error}")

async def main():
    """Main function"""
    async with bot:
        # Load cog
        await bot.add_cog(TradingSignals(bot))
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 5: Create .env File

Create `.env` in your project root:

```env
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here

# OKX Configuration (existing)
OKX_API_KEY=your_api_key
OKX_SECRET_KEY=your_secret_key
OKX_PASSPHRASE=your_passphrase
OKX_SANDBOX=true
```

**How to get Channel ID:**
1. Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)
2. Right-click channel → Copy Channel ID

### Step 6: Run the Bot

```bash
python discord_trading_bot.py
```

You should see:
```
✅ BotName#1234 has connected to Discord!
📊 Monitoring channel: 123456789
```

---

## 🎯 Testing Commands

In your Discord server, try:

```
!performance      # Get performance metrics
!trades 5         # Get last 5 trades
!status           # Get bot status
!help             # Show help
```

---

## 📱 Advanced Features

### Add Alerts for Big Wins/Losses

```python
@tasks.loop(minutes=1)
async def alert_loop(self):
    """Send alerts for significant trades"""
    tracker = get_performance_tracker()
    
    if tracker.trades:
        last_trade = tracker.trades[-1]
        
        if last_trade.pnl_usd:
            # Alert on big wins (>$100)
            if last_trade.pnl_usd > 100:
                channel = self.bot.get_channel(CHANNEL_ID)
                embed = discord.Embed(
                    title="🎉 BIG WIN!",
                    description=f"{last_trade.symbol}: +${last_trade.pnl_usd:.2f}",
                    color=discord.Color.gold()
                )
                await channel.send(embed=embed)
            
            # Alert on big losses (<-$100)
            elif last_trade.pnl_usd < -100:
                channel = self.bot.get_channel(CHANNEL_ID)
                embed = discord.Embed(
                    title="⚠️ SIGNIFICANT LOSS",
                    description=f"{last_trade.symbol}: ${last_trade.pnl_usd:.2f}",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)
```

### Add Real-time Signal Notifications

```python
@commands.command()
async def signal(self, ctx, symbol: str, direction: str, confidence: float):
    """Send trading signal"""
    embed = discord.Embed(
        title=f"🎯 Trading Signal: {symbol}",
        color=discord.Color.green() if direction.upper() == "BUY" else discord.Color.red()
    )
    
    embed.add_field(name="Direction", value=direction.upper(), inline=True)
    embed.add_field(name="Confidence", value=f"{confidence:.1%}", inline=True)
    embed.add_field(name="Time", value=datetime.now().strftime("%H:%M:%S"), inline=True)
    
    await ctx.send(embed=embed)
```

---

## 🚀 Deployment Options

### Option 1: Keep Running on Your PC
- Simple but requires PC to stay on
- Good for testing

### Option 2: Deploy to Cloud (Recommended)

**Using Railway (Free tier available):**

1. Create account at [railway.app](https://railway.app)
2. Create new project
3. Connect GitHub repo
4. Add environment variables (DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID)
5. Deploy!

**Using Heroku:**

```bash
# Create Procfile
echo "worker: python discord_trading_bot.py" > Procfile

# Deploy
heroku create your-bot-name
heroku config:set DISCORD_BOT_TOKEN=your_token
heroku config:set DISCORD_CHANNEL_ID=your_channel_id
git push heroku main
```

---

## 💰 Monetization

### Setup Stripe Payments

```bash
pip install stripe
```

```python
import stripe

stripe.api_key = "sk_test_YOUR_KEY"

@commands.command()
async def subscribe(self, ctx):
    """Subscribe to premium signals"""
    
    # Create Stripe checkout session
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price": "price_1234567890",  # Your Stripe price ID
                "quantity": 1,
            }
        ],
        mode="subscription",
        success_url="https://yourdomain.com/success",
        cancel_url="https://yourdomain.com/cancel",
    )
    
    embed = discord.Embed(
        title="💳 Subscribe to Premium",
        description=f"[Click here to subscribe]({session.url})",
        color=discord.Color.blue()
    )
    
    await ctx.send(embed=embed)
```

---

## 📊 Pricing Tiers

**Free:**
- Daily performance summary
- Basic commands (!performance, !trades)

**Pro ($29/month):**
- Real-time signal notifications
- Advanced analytics
- Trade alerts
- Priority support

**Enterprise ($99/month):**
- Multiple bots
- Custom alerts
- API access
- Dedicated support

---

## 🔧 Troubleshooting

### Bot not responding
- Check DISCORD_BOT_TOKEN is correct
- Verify bot has permissions in channel
- Check bot is online (green dot)

### Commands not working
- Verify command prefix (!)
- Check bot has Message Content Intent enabled
- Ensure bot has Send Messages permission

### No performance data
- Check trading bot is running
- Verify data files exist in `/data` folder
- Check daily_trades.json has data

---

## 📈 Next Steps

1. **Launch MVP** - Get bot working with basic commands
2. **Add to Discord** - Invite friends to test
3. **Gather Feedback** - See what features users want
4. **Add Premium Features** - Implement Stripe payments
5. **Scale** - Add more servers and users

---

Good luck! 🚀
