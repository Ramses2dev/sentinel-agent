import pandas as pd
import requests
import time

# ============================================================
# CONFIGURAZIONE ALLINEATA AL BOT REAL
# ============================================================
CONFIG = {
    "pairs": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "timeframe": "5m",
    "lookback_candles": 48,
    "risk_reward": 5.0,
    "volume_filter_multiplier": 1.8, # Allineato al bot Real
    "minimum_sweep_pct": 0.0003,
    "initial_balance": 90.0,
    "risk_per_trade": 0.02,
    "fee_pct": 0.0004,
    "limit": 5000
}

# ============================================================
# FETCH DATA
# ============================================================
def fetch_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={CONFIG['timeframe']}&limit={CONFIG['limit']}"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        df = pd.DataFrame(data).iloc[:, 0:6].copy()
        df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col])
        return df
    except Exception as e:
        print(f"❌ Errore download {symbol}: {e}")
        return pd.DataFrame()

# ============================================================
# MOTORE BACKTEST
# ============================================================
def run_backtest(symbol, df):
    balance = CONFIG["initial_balance"]
    wins, losses, trades = 0, 0, 0
    position = "NONE"
    
    # Parametri temporanei per il trade
    stop_loss, take_profit = 0.0, 0.0
    
    for i in range(CONFIG["lookback_candles"] + 2, len(df)):
        current_candle = df.iloc[i-1]
        window = df.iloc[i-CONFIG["lookback_candles"]-1 : i-1]
        
        # Dati del momento
        price_close, price_high, price_low, volume = current_candle["close"], current_candle["high"], current_candle["low"], current_candle["volume"]
        resistance = window["high"].max()
        support = window["low"].min()
        avg_volume = window["volume"].mean()

        # 1. GESTIONE POSIZIONE APERTA
        if position == "LONG":
            if price_low <= stop_loss:
                balance -= (balance * CONFIG["risk_per_trade"]) + (balance * CONFIG["fee_pct"] * 2)
                losses += 1
                position = "NONE"
            elif price_high >= take_profit:
                balance += (balance * CONFIG["risk_per_trade"] * CONFIG["risk_reward"]) - (balance * CONFIG["fee_pct"] * 2)
                wins += 1
                position = "NONE"
        
        elif position == "SHORT":
            if price_high >= stop_loss:
                balance -= (balance * CONFIG["risk_per_trade"]) + (balance * CONFIG["fee_pct"] * 2)
                losses += 1
                position = "NONE"
            elif price_low <= take_profit:
                balance += (balance * CONFIG["risk_per_trade"] * CONFIG["risk_reward"]) - (balance * CONFIG["fee_pct"] * 2)
                wins += 1
                position = "NONE"

        # 2. LOGICA DI INGRESSO (ALLINEATA AL REAL)
        if position == "NONE":
            # SHORT
            sweep_dist_short = (price_high - resistance) / resistance
            if price_high > resistance and price_close < resistance and sweep_dist_short >= CONFIG["minimum_sweep_pct"]:
                if volume < (avg_volume * CONFIG["volume_filter_multiplier"]):
                    entry = price_close
                    stop_loss = price_high + (price_high * 0.0003)
                    take_profit = entry - ((stop_loss - entry) * CONFIG["risk_reward"])
                    position = "SHORT"
                    trades += 1
            
            # LONG
            elif price_low < support and price_close > support and ((support - price_low) / support) >= CONFIG["minimum_sweep_pct"]:
                if volume < (avg_volume * CONFIG["volume_filter_multiplier"]):
                    entry = price_close
                    stop_loss = price_low - (price_low * 0.0003)
                    take_profit = entry + ((entry - stop_loss) * CONFIG["risk_reward"])
                    position = "LONG"
                    trades += 1

    return {"Pair": symbol, "Final": round(balance, 2), "Trades": trades, "Wins": wins, "Losses": losses}

# ============================================================
# ESECUZIONE
# ============================================================
if __name__ == "__main__":
    for pair in CONFIG["pairs"]:
        df = fetch_data(pair)
        if not df.empty:
            res = run_backtest(pair, df)
            print(f"✅ {res['Pair']} | Saldo Finale: {res['Final']} USDT | Trades: {res['Trades']} (W:{res['Wins']}/L:{res['Losses']})")