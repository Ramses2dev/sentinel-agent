import numpy as np
import sys
setattr(np, "NaN", np.nan)
import requests
import pandas as pd
from datetime import datetime, time

CONFIG = {
    "pairs": ["BNBUSDT", "ETHUSDT", "CAKEUSDT"],
    "timeframe": "15m",
    "limit": 1500,          # Analizziamo le ultime 1500 candele a 15 minuti
    "initial_equity": 1000.0,
    "risk_reward": 3.0      # Target 1 a 3 (Rapporto Rischio/Rendimento)
}

def fetch_15m_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={CONFIG['timeframe']}&limit={CONFIG['limit']}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data).iloc[:, 0:6].copy()
        df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception as e:
        print(f"Errore download {symbol}: {e}")
        return pd.DataFrame()

def run_levels_backtest(symbol, df):
    if df.empty or len(df) < 100:
        return None

    equity = CONFIG["initial_equity"]
    position = "NONE"
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    
    trades_count = 0
    winning_trades = 0

    # Raggruppiamo i dati per calcolare i livelli del giorno precedente
    df['date'] = df['timestamp'].dt.date
    
    # Ciclo storico delle candele a 15 minuti
    for i in range(48, len(df)): # Partiamo dopo un po' di candele per avere i dati storici stabili
        current_row = df.iloc[i]
        current_time = current_row["timestamp"].time()
        current_date = current_row["timestamp"].date()
        price_close = current_row["close"]
        price_high = current_row["high"]
        price_low = current_row["low"]

        # 1. Calcolo livelli del giorno precedente (Daily High / Low)
        past_days = df[df['date'] < current_date]
        if past_days.empty:
            continue
        last_day_date = past_days['date'].max()
        last_day_candles = past_days[past_days['date'] == last_day_date]
        
        daily_high = last_day_candles['high'].max()
        daily_low = last_day_candles['low'].min()

        # 2. Calcolo Sessione Asiatica (00:00 - 08:00 UTC / Ora Italiana indicativa)
        # Prendiamo le candele di oggi tra la mezzanotte e le 08:00
        asian_candles = df[(df['date'] == current_date) & (df['timestamp'].dt.time >= time(0, 0)) & (df['timestamp'].dt.time <= time(8, 0))]
        
        if not asian_candles.empty:
            asian_high = asian_candles['high'].max()
            asian_low = asian_candles['low'].min()
        else:
            asian_high = daily_high
            asian_low = daily_low

        # Uniamo i livelli per trovare i massimi e minimi assoluti di riferimento
        resistance = max(daily_high, asian_high)
        support = min(daily_low, asian_low)

        # 3. GESTIONE POSIZIONE APERTA (Controllo se tocca SL o TP)
        if position == "LONG":
            if price_low <= stop_loss: # Prende lo Stop Loss
                risk_taken = entry_price - stop_loss
                equity -= (equity * 0.02) # Rischiamo l'2% del capitale a trade
                position = "NONE"
            elif price_high >= take_profit: # Prende il Target 1:3
                equity += (equity * 0.02 * CONFIG["risk_reward"])
                winning_trades += 1
                position = "NONE"

        elif position == "SHORT":
            if price_high >= stop_loss: # Prende lo Stop Loss
                risk_taken = stop_loss - entry_price
                equity -= (equity * 0.02)
                position = "NONE"
            elif price_low <= take_profit: # Prende il Target 1:3
                equity += (equity * 0.02 * CONFIG["risk_reward"])
                winning_trades += 1
                position = "NONE"

        # 4. LOGICA DI INGRESSO (Solo se siamo flat)
        if position == "NONE":
            # SCENARIO SHORT: Rottura resistenza e rientro sotto
            if price_high > resistance and price_close < resistance:
                position = "SHORT"
                entry_price = price_close
                stop_loss = price_high + (price_high * 0.001) # SL appena sopra il massimo della finta
                risk_dist = stop_loss - entry_price
                take_profit = entry_price - (risk_dist * CONFIG["risk_reward"]) # Target 1 a 3
                trades_count += 1

            # SCENARIO LONG: Rottura supporto e rientro sopra
            elif price_low < support and price_close > support:
                position = "LONG"
                entry_price = price_close
                stop_loss = price_low - (price_low * 0.001) # SL appena sotto il minimo della finta
                risk_dist = entry_price - stop_loss
                take_profit = entry_price + (risk_dist * CONFIG["risk_reward"]) # Target 1 a 3
                trades_count += 1

    win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0
    return {
        "Capitale Finale": round(equity, 2),
        "Profitto Totale %": round(((equity - CONFIG["initial_equity"]) / CONFIG["initial_equity"]) * 100, 2),
        "Trade Totali": trades_count,
        "Win Rate %": round(win_rate, 2)
    }

if __name__ == "__main__":
    print("====================================================")
    print("🎯 STRATEGIA 'DA LIVELLO A LIVELLO' (LIQUIDITY SWEEP)")
    print("📊 TARGET RIGIDO 1:3 & STOP LOSS SUL MASSIMO/MINIMO")
    print("====================================================\n")
    
    for pair in CONFIG["pairs"]:
        print(f"📥 Analizzando i flussi a 15 minuti per {pair}...")
        df_hist = fetch_15m_data(pair)
        results = run_levels_backtest(pair, df_hist)
        
        if results:
            print(f"📊 RISULTATI STRATEGIA DI {pair.replace('USDT', '')}:")
            for key, value in results.items():
                print(f"   🔹 {key}: {value}")
            print("-" * 52)
        else:
            print(f"❌ Errore nel caricamento dei dati per {pair}.\n")