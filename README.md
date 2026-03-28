# ProTools Bundler Bot — Setup Guide

## Files
```
bot.py           ← main bot logic
config.py        ← token config
wordlist.py      ← BIP39 word list
requirements.txt ← dependencies
runtime.txt      ← Python version for Render
render.yaml      ← Render deployment config
```

---

## Step 1 — Get your Bot Token
1. Open Telegram → search **@BotFather**
2. Send `/newbot` and follow the steps
3. Copy the token it gives you (looks like `123456:ABCdef...`)

---

## Step 2 — Deploy to Render

1. Push all these files to a **GitHub repo**
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repo
4. Render will auto-detect `render.yaml` — click **Apply**
5. Go to **Environment** tab → add:
   - Key: `BOT_TOKEN`
   - Value: your token from BotFather
6. Click **Deploy** — wait for it to go live
7. Copy your Render URL (looks like `https://protools-bundler-bot.onrender.com`)

---

## Step 3 — Keep Alive with UptimeRobot

Render free tier sleeps after 15 minutes of inactivity.
UptimeRobot pings it every 5 minutes to keep it awake.

1. Go to [uptimerobot.com](https://uptimerobot.com) → Create free account
2. Click **Add New Monitor**
3. Settings:
   - Monitor Type: **HTTP(s)**
   - Friendly Name: `ProTools Bot`
   - URL: `https://your-render-url.onrender.com/`
   - Monitoring Interval: **5 minutes**
4. Click **Create Monitor** ✅

That's it — your bot will stay online 24/7.

---

## Local Testing (optional)

```bash
pip install -r requirements.txt
# Edit config.py and paste your token directly, then:
python bot.py
```
