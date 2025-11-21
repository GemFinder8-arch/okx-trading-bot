# 🚀 Deploy to Railway (24/7 Hosting)

## What is Railway?
Railway is a free hosting platform that runs your bot 24/7 without you needing to keep your computer on.

---

## Step 1: Push Code to GitHub

### 1.1 Create GitHub Repository
1. Go to https://github.com/new
2. Name: `okx-trading-bot`
3. Description: "OKX Trading Bot with Discord Integration"
4. Make it **Public**
5. Click "Create repository"

### 1.2 Push Code to GitHub
```bash
cd c:\Users\madma\OneDrive\Desktop\OKX Trading Bot
git init
git add .
git commit -m "Initial commit: Discord trading bot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/okx-trading-bot.git
git push -u origin main
```

**Note:** Replace `YOUR_USERNAME` with your actual GitHub username.

---

## Step 2: Deploy to Railway

### 2.1 Sign Up to Railway
1. Go to https://railway.app
2. Click "Start Project"
3. Sign up with GitHub
4. Authorize Railway to access your GitHub

### 2.2 Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub"
3. Select your `okx-trading-bot` repository
4. Click "Deploy"

### 2.3 Add Environment Variables
1. Go to your Railway project
2. Click "Variables"
3. Add these environment variables from your `.env` file:

```
DISCORD_BOT_TOKEN=YOUR_TOKEN_HERE
DISCORD_SERVER_ID=YOUR_SERVER_ID
DISCORD_CHANNEL_ID=YOUR_CHANNEL_ID
OKX_API_KEY=YOUR_API_KEY
OKX_SECRET_KEY=YOUR_SECRET_KEY
OKX_PASSPHRASE=YOUR_PASSPHRASE
OKX_SANDBOX=true
TRADING_BOT_POLLING_INTERVAL=60
TRADING_BOT_MAX_CONCURRENT_POSITIONS=10
TRADING_BOT_SYMBOLS=BTC/USDT,ETH/USDT,SOL/USDT,ADA/USDT,XTZ/USDT
TRADING_BOT_TRADE_VOLUME=0.01
TRADING_BOT_MIN_QUOTE_BALANCE=50
```

**Important:** Copy the actual values from your `.env` file, not the placeholders above.

### 2.4 Configure Start Command
1. Go to "Settings"
2. Find "Start Command"
3. Set to: `python discord_trading_bot.py`
4. Save

### 2.5 Deploy
1. Click "Deploy"
2. Wait for deployment to complete
3. You should see "✅ Deployment successful"

---

## Step 3: Verify Bot is Running

1. Go to your Discord server
2. Check if bot is online (green dot)
3. Try a command: `!help`
4. Bot should respond

---

## Step 4: Monitor Logs

1. Go to Railway project
2. Click "Logs"
3. You should see:
```
✅ OKX Trading_bot#0082 has connected to Discord!
```

---

## 🎉 You're Done!

Your bot is now running 24/7 on Railway!

### What Happens Next:
- Bot automatically posts performance updates
- Users can use commands anytime
- Bot runs even when your computer is off
- No monthly cost (free tier)

---

## 📋 Troubleshooting

### Bot not showing online
- Check environment variables are correct
- Check Discord token is valid
- Check intents are enabled in Discord Developer Portal

### Bot not responding to commands
- Check bot has permissions in server
- Check bot is in the channel
- Try `!help` command

### Deployment failed
- Check GitHub repository is public
- Check all environment variables are set
- Check Procfile exists and is correct

---

## 💡 Tips

### Free Tier Limits
- 500 hours/month (enough for 24/7)
- 1 GB RAM
- No credit card needed

### Upgrade Later
- If you need more resources, Railway has paid plans
- But free tier is perfect for starting

### Auto-Deploy
- Every time you push to GitHub, Railway automatically deploys
- No manual deployment needed

---

## 🚀 Next Steps

1. Create GitHub account (if you don't have one)
2. Push code to GitHub
3. Deploy to Railway
4. Verify bot is running
5. Start inviting users!

---

**Ready to deploy? Let me know once you've pushed to GitHub!**
