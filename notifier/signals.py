"""Detect candle patterns + MACD filter, send Telegram alert on new signal."""

import json
import os
import sys
from pathlib import Path

import requests
import yfinance as yf

TICKERS = [t.strip() for t in os.environ.get("TICKERS", "SMH,SPMO").split(",") if t.strip()]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = Path(__file__).parent / "state.json"


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))


def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=15)
    r.raise_for_status()


def fetch_4h(ticker):
    # yfinance has no native 4h — pull 1h and resample.
    df = yf.Ticker(ticker).history(period="60d", interval="1h", auto_adjust=False)
    if df.empty:
        return df
    df4 = df.resample("4h").agg({
        "Open": "first", "High": "max", "Low": "min",
        "Close": "last", "Volume": "sum",
    }).dropna()
    return df4


def macd_hist(closes, fast=12, slow=26, signal=9):
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal, adjust=False).mean()
    return macd - sig


def detect(df):
    if len(df) < 30:
        return None

    r0, r1, r2 = df.iloc[-1], df.iloc[-2], df.iloc[-3]

    def body(r): return abs(r["Close"] - r["Open"])
    def upper(r): return r["High"] - max(r["Open"], r["Close"])
    def lower(r): return min(r["Open"], r["Close"]) - r["Low"]
    def rng(r): return r["High"] - r["Low"]
    def bull(r): return r["Close"] > r["Open"]
    def bear(r): return r["Close"] < r["Open"]
    def doji(r): return body(r) <= rng(r) * 0.1

    bull_engulf = bear(r1) and bull(r0) and r0["Close"] > r1["Open"] and r0["Open"] <= r1["Close"]
    bear_engulf = bull(r1) and bear(r0) and r0["Close"] < r1["Open"] and r0["Open"] >= r1["Close"]

    hammer = body(r0) <= rng(r0) * 0.3 and lower(r0) >= body(r0) * 2 and upper(r0) <= body(r0)
    star_bear = body(r0) <= rng(r0) * 0.3 and upper(r0) >= body(r0) * 2 and lower(r0) <= body(r0)

    bull_star = bear(r2) and doji(r1) and bull(r0) and r0["Close"] > (r2["Open"] + r2["Close"]) / 2
    bear_star = bull(r2) and doji(r1) and bear(r0) and r0["Close"] < (r2["Open"] + r2["Close"]) / 2

    hist = macd_hist(df["Close"]).iloc[-1]

    if (bull_engulf or bull_star or hammer) and hist < 0:
        return "BUY"
    if (bear_engulf or bear_star or star_bear) and hist > 0:
        return "SELL"
    return None


def main():
    state = load_state()
    for ticker in TICKERS:
        try:
            df = fetch_4h(ticker)
            if df.empty:
                print(f"{ticker}: no data", file=sys.stderr)
                continue

            signal = detect(df)
            last_ts = df.index[-1].isoformat()
            key = f"{signal}:{last_ts}"

            if signal and state.get(ticker) != key:
                price = df["Close"].iloc[-1]
                msg = f"{signal} {ticker} @ {price:.2f}\nBar close: {last_ts}"
                send_telegram(msg)
                state[ticker] = key
                print(f"{ticker}: sent {signal} @ {price:.2f}")
            else:
                print(f"{ticker}: no new signal (last bar {last_ts})")
        except Exception as e:
            print(f"{ticker}: ERROR {e}", file=sys.stderr)

    save_state(state)


if __name__ == "__main__":
    main()
