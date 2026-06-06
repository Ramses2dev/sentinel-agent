import numpy as np
import sys
setattr(np, "NaN", np.nan)
import requests
import pandas as pd
import time

CONFIG = {
    # Testiamo i veri re della liquidità
    "pairs": ["BTCUSDT", "ETHUSDT", "SOLUSDT"], 
    "timeframe": "5m",
    # Scarichiamo il massimo consentito dai server per il deep-test (~5000 candele intensive per asset)
    "limit": 5000, 
    "initial_equity": 1000.0,
    "targets_to_test": [3.0, 4.0, 5.0, 6.0] # La tua intuizione: testiamo tutti i target in un colpo solo
}

def fetch_deep_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={CONFIG['timeframe']}&limit={CONFIG['limit']}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data).iloc[:, 0:6].copy()
        df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception as e:
        print(f"Errore download intensivo {symbol}: {e}")
        return pd.DataFrame()

def run_stress_test(symbol, df, rr_target):
    equity = CONFIG["initial_equity"]
    position = "NONE"
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    
    trades_count = 0
    winning_trades = 0
    lookback_candles = 48 

    for i in range(lookback_candles, len(df)):
        current_row = df.iloc[i]
        price_close = current_row["close"]
        price_high = current_row["high"]
        price_low = current_row["low"]
        current_volume = current_row["volume"]

        window_candles = df.iloc[i - lookback_candles : i]
        resistance = window_candles['high'].max()
        support = window_candles['low'].min()
        avg_volume = window_candles['volume'].mean()

        if position == "LONG":
            if price_low <= stop_loss:
                equity -= (equity * 0.02)
                position = "NONE"
            elif price_high >= take_profit:
                equity += (equity * 0.02 * rr_target)
                winning_trades += 1
                position = "NONE"

        elif position == "SHORT":
            if price_high >= stop_loss:
                equity -= (equity * 0.02)
                position = "NONE"
            elif price_low <= take_profit:
                equity += (equity * 0.02 * rr_target)
                winning_trades += 1
                position = "NONE"

        if position == "NONE":
            if price_high > resistance and price_close < resistance:
                if current_volume < (avg_volume * 1.5):
                    position = "SHORT"
                    entry_price = price_close
                    stop_loss = price_high + (price_high * 0.0003)
                    risk_dist = stop_loss - entry_price
                    take_profit = entry_price - (risk_dist * rr_target)
                    trades_count += 1

            elif price_low < support and price_close > support:
                if current_volume < (avg_volume * 1.5):
                    position = "LONG"
                    entry_price = price_close
                    stop_loss = price_low - (price_low * 0.0003)
                    risk_dist = entry_price - stop_loss
                    take_profit = entry_price + (risk_dist * rr_target)
                    trades_count += 1

    win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0
    return {
        "Profitto %": round(((equity - CONFIG["initial_equity"]) / CONFIG["initial_equity"]) * 100, 2),
        "Trade": trades_count,
        "Win Rate %": round(win_rate, 2)
    }

if __name__ == "__main__":
    print("====================================================")
    print("🔬 MATRICE DI OTTIMIZZAZIONE PROFESSIONALE")
    print("🔥 TESTING MULTI-TARGET & ASSET AD ALTA LIQUIDITÀ")
    print("====================================================\n")
    
    for pair in CONFIG["pairs"]:
        print(f"📥 Scaricando storico profondo per {pair}...")
        df_hist = fetch_deep_data(pair)
        
        if df_hist.empty:
            print(f"❌ Impossibile recuperare dati per {pair}")
            continue
            
        print(f"📊 Elaborazione simulazioni per {pair}:")
        for target in CONFIG["targets_to_test"]:
            res = run_stress_test(pair, df_hist, target)
            print(f"   🎯 Target 1:{int(target)} -> Profitto: {res['Profitto %']}% | Trade: {res['Trade']} | WR: {res['Win Rate %']}%")
        print("-" * 52)