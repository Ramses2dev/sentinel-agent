import os
import time
import json
import logging
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv
from web3 import Web3

# ============================================================
# LOAD ENV
# ============================================================

load_dotenv()

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    filename="sentinel.log",
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

# ============================================================
# CONFIG
# ============================================================

CONFIG = {

    # ACTIVE PAIRS
    "pairs": [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT"
    ],

    "timeframe": "5m",

    # STRATEGY
    "lookback_candles": 48,
    "risk_reward": 5.0,

    # FILTERS
    "volume_filter_multiplier": 1.8,
    "minimum_sweep_pct": 0.0003,

    # RISK
    "risk_per_trade": 0.02,
    "max_daily_drawdown_pct": 0.05,

    # EXECUTION
    "cooldown_minutes": 10,
    "loop_sleep_seconds": 20,

    # FEES
    "fee_pct": 0.0004,

    # STATE FILE
    "state_file": "sentinel_state.json"
}

# ============================================================
# BLOCKCHAIN
# ============================================================

rpc_url = "https://bsc-dataseed.binance.org/"

w3 = Web3(Web3.HTTPProvider(rpc_url))

# ============================================================
# DEFAULT STATE
# ============================================================

DEFAULT_STATE = {

    "wallet_address": os.getenv("WALLET_ADDRESS", ""),

    "initial_daily_balance": 90.0,
    "current_balance": 90.0,

    "position": "NONE",

    "active_pair": None,

    "entry_price": 0.0,
    "stop_loss": 0.0,
    "take_profit": 0.0,

    "trade_open_time": 0,
    "last_trade_time": 0,

    "wins": 0,
    "losses": 0,

    "last_drawdown_check_day": None
}

# ============================================================
# SAVE / LOAD STATE
# ============================================================

def load_state():

    if os.path.exists(CONFIG["state_file"]):

        with open(CONFIG["state_file"], "r") as f:

            loaded = json.load(f)

            for key in DEFAULT_STATE:
                if key not in loaded:
                    loaded[key] = DEFAULT_STATE[key]

            return loaded

    return DEFAULT_STATE.copy()

def save_state():

    with open(CONFIG["state_file"], "w") as f:
        json.dump(bot_state, f, indent=4)

# ============================================================
# LOAD BOT STATE
# ============================================================

bot_state = load_state()

# ============================================================
# FETCH MARKET DATA
# ============================================================

def fetch_live_candles(symbol):

    time.sleep(0.2)

    url = (
        f"https://api.binance.com/api/v3/klines"
        f"?symbol={symbol}"
        f"&interval={CONFIG['timeframe']}"
        f"&limit=100"
    )

    try:

        response = requests.get(url, timeout=10)

        response.raise_for_status()

        data = response.json()

        if isinstance(data, dict):
            print(f"⚠️ API Error {symbol}: {data}")
            return pd.DataFrame()

        df = pd.DataFrame(data).iloc[:, 0:6].copy()

        df.columns = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]

        for col in [
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]:
            df[col] = pd.to_numeric(df[col])

        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            unit="ms"
        )

        return df

    except Exception as e:

        print(f"⚠️ Data error {symbol}: {e}")

        return pd.DataFrame()

# ============================================================
# PROTECTIONS
# ============================================================

def check_protections():

    now = time.time()

    today = datetime.now(timezone.utc).date()

    if bot_state["last_drawdown_check_day"] != str(today):

        bot_state["initial_daily_balance"] = (
            bot_state["current_balance"]
        )

        bot_state["last_drawdown_check_day"] = str(today)

        save_state()

    loss_today = (
        bot_state["initial_daily_balance"]
        - bot_state["current_balance"]
    )

    max_loss_allowed = (
        bot_state["initial_daily_balance"]
        * CONFIG["max_daily_drawdown_pct"]
    )

    if loss_today >= max_loss_allowed:

        print(
            "🚨 DAILY DRAWDOWN LIMIT REACHED"
        )

        logging.info(
            "DAILY DRAWDOWN LIMIT REACHED"
        )

        return False

    elapsed_minutes = (
        (now - bot_state["last_trade_time"]) / 60
    )

    if elapsed_minutes < CONFIG["cooldown_minutes"]:
        return False

    return True

# ============================================================
# OPEN POSITION
# ============================================================

def open_position(side, pair, entry, stop, tp):

    bot_state["position"] = side

    bot_state["active_pair"] = pair

    bot_state["entry_price"] = entry

    bot_state["stop_loss"] = stop

    bot_state["take_profit"] = tp

    bot_state["trade_open_time"] = time.time()

    bot_state["last_trade_time"] = time.time()

    save_state()

    print("\n================================================")
    print(f"🚀 OPEN {side}")
    print(f"PAIR: {pair}")
    print(f"ENTRY: {entry:.4f}")
    print(f"STOP: {stop:.4f}")
    print(f"TARGET: {tp:.4f}")
    print("================================================\n")

    logging.info(
        f"{side} {pair} "
        f"ENTRY={entry:.4f} "
        f"SL={stop:.4f} "
        f"TP={tp:.4f}"
    )

# ============================================================
# CLOSE POSITION
# ============================================================

def close_position(result):

    risk_amount = (
        bot_state["current_balance"]
        * CONFIG["risk_per_trade"]
    )

    fee_cost = (
        bot_state["current_balance"]
        * CONFIG["fee_pct"]
        * 2
    )

    if result == "WIN":

        profit = (
            risk_amount
            * CONFIG["risk_reward"]
        )

        profit -= fee_cost

        bot_state["current_balance"] += profit

        bot_state["wins"] += 1

    elif result == "LOSS":

        loss = risk_amount + fee_cost

        bot_state["current_balance"] -= loss

        bot_state["losses"] += 1

    print("\n================================================")
    print(f"📊 POSITION CLOSED -> {result}")
    print(f"💰 BALANCE: {bot_state['current_balance']:.2f} USDT")
    print(
        f"🏆 WINS: {bot_state['wins']} | "
        f"❌ LOSSES: {bot_state['losses']}"
    )
    print("================================================\n")

    logging.info(
        f"CLOSED {result} "
        f"BALANCE={bot_state['current_balance']:.2f}"
    )

    bot_state["position"] = "NONE"

    bot_state["active_pair"] = None

    bot_state["entry_price"] = 0.0
    bot_state["stop_loss"] = 0.0
    bot_state["take_profit"] = 0.0

    save_state()

# ============================================================
# MANAGE POSITION
# ============================================================

def manage_position():

    if bot_state["position"] == "NONE":
        return

    pair = bot_state["active_pair"]

    df = fetch_live_candles(pair)

    if df.empty:
        return

    candle = df.iloc[-2]

    high = candle["high"]

    low = candle["low"]

    if bot_state["position"] == "LONG":

        if low <= bot_state["stop_loss"]:

            print(f"❌ LONG STOP HIT {pair}")

            close_position("LOSS")

        elif high >= bot_state["take_profit"]:

            print(f"✅ LONG TARGET HIT {pair}")

            close_position("WIN")

    elif bot_state["position"] == "SHORT":

        if high >= bot_state["stop_loss"]:

            print(f"❌ SHORT STOP HIT {pair}")

            close_position("LOSS")

        elif low <= bot_state["take_profit"]:

            print(f"✅ SHORT TARGET HIT {pair}")

            close_position("WIN")

# ============================================================
# MARKET SCANNER
# ============================================================

def scan_market():

    print(
        f"🕵️ [{datetime.now().strftime('%H:%M:%S')}] "
        "Scanning liquidity sweeps..."
    )

    if not check_protections():
        return

    if bot_state["position"] != "NONE":
        return

    for pair in CONFIG["pairs"]:

        df = fetch_live_candles(pair)

        if df.empty:
            continue

        if len(df) < CONFIG["lookback_candles"] + 2:
            continue

        current_candle = df.iloc[-2]

        window = df.iloc[
            -(CONFIG["lookback_candles"] + 2):-2
        ]

        resistance = window["high"].max()

        support = window["low"].min()

        avg_volume = window["volume"].mean()

        price_close = current_candle["close"]

        price_high = current_candle["high"]

        price_low = current_candle["low"]

        volume = current_candle["volume"]

        # ====================================================
        # SHORT
        # ====================================================

        sweep_distance = (
            (price_high - resistance)
            / resistance
        )

        if (
            price_high > resistance
            and price_close < resistance
            and sweep_distance >= CONFIG["minimum_sweep_pct"]
        ):

            if volume < (
                avg_volume
                * CONFIG["volume_filter_multiplier"]
            ):

                entry_price = price_close

                stop_loss = (
                    price_high
                    + (price_high * 0.0003)
                )

                risk_dist = (
                    stop_loss - entry_price
                )

                take_profit = (
                    entry_price
                    - (
                        risk_dist
                        * CONFIG["risk_reward"]
                    )
                )

                print(f"\n🎯 SHORT SIGNAL {pair}")

                open_position(
                    "SHORT",
                    pair,
                    entry_price,
                    stop_loss,
                    take_profit
                )

                break

        # ====================================================
        # LONG
        # ====================================================

        sweep_distance = (
            (support - price_low)
            / support
        )

        if (
            price_low < support
            and price_close > support
            and sweep_distance >= CONFIG["minimum_sweep_pct"]
        ):

            if volume < (
                avg_volume
                * CONFIG["volume_filter_multiplier"]
            ):

                entry_price = price_close

                stop_loss = (
                    price_low
                    - (price_low * 0.0003)
                )

                risk_dist = (
                    entry_price - stop_loss
                )

                take_profit = (
                    entry_price
                    + (
                        risk_dist
                        * CONFIG["risk_reward"]
                    )
                )

                print(f"\n🎯 LONG SIGNAL {pair}")

                open_position(
                    "LONG",
                    pair,
                    entry_price,
                    stop_loss,
                    take_profit
                )

                break

# ============================================================
# MAIN LOOP
# ============================================================

if __name__ == "__main__":

    print("====================================================")
    print("🤖 SENTINEL AGENT V3 - LIVE ENGINE")
    print(f"🔗 Wallet: {bot_state['wallet_address']}")
    print(f"💰 Balance: {bot_state['current_balance']} USDT")
    print("====================================================\n")

    while True:

        try:

            manage_position()

            scan_market()

            time.sleep(
                CONFIG["loop_sleep_seconds"]
            )

        except KeyboardInterrupt:

            print("\n🛑 Sentinel stopped manually.")
            break

        except Exception as e:

            print(f"⚠️ Runtime error: {e}")

            logging.error(str(e))

            time.sleep(10)