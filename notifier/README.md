# Trading Signal Notifier

Runs on GitHub Actions every 2h, checks configured tickers for candle patterns + MACD confirmation, sends Telegram message on new signal.

## Setup (one-time, ~10 min)

### 1. Create Telegram bot

1. Open Telegram, search `@BotFather`
2. Send `/newbot`, follow prompts, pick name + username
3. Copy the token — looks like `123456:ABC-DEF...`

### 2. Get your chat ID

1. Search your new bot in Telegram, send `/start`
2. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in browser
3. Find `"chat":{"id":123456789` — that number is your chat ID

### 3. Push this repo to GitHub

```bash
cd c:\Users\krist\apps\trading
git init
git add .
git commit -m "initial"
git remote add origin git@github.com:<you>/<repo>.git
git push -u origin main
```

Make repo **public** (unlimited Actions minutes) or private (2000 min/month — still plenty).

### 4. Add GitHub secrets

Repo → Settings → Secrets and variables → Actions → New repository secret:

- `TELEGRAM_BOT_TOKEN` = bot token from step 1
- `TELEGRAM_CHAT_ID` = chat ID from step 2

### 5. Enable Actions

Repo → Actions tab → allow workflows. First scheduled run within ~2h, or click "Run workflow" to trigger manually.

## Change tickers

Edit `.github/workflows/signals.yml`:

```yaml
TICKERS: 'SMH,SPMO,QQQ,SPY'
```

Commit + push. Takes effect next run.

## How it works

- `signals.py` fetches 60d of 1h data via yfinance, resamples to 4h
- Detects: Bullish/Bearish Engulfing, Hammer, Shooting Star, Morning/Evening Star
- Filters via MACD histogram (BUY only when hist < 0, SELL only when > 0)
- Dedups via `state.json` — one alert per bar per ticker

## Local test

```bash
cd notifier
pip install -r requirements.txt
$env:TELEGRAM_BOT_TOKEN="..."
$env:TELEGRAM_CHAT_ID="..."
$env:TICKERS="SMH"
python signals.py
```
