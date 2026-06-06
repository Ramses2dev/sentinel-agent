import numpy as np
import sys
setattr(np, "NaN", np.nan)
import requests
import pandas as pd

CONFIG = {
    "pairs": ["BNBUSDT", "ETHUSDT", "SOLUSDT"], # Solo crypto liquide
    "timeframe": "5m",       # Scendiamo a 5 minuti per entrate chirurgiche
    "limit": 3000,          # Analizziamo le ultime 3000 candele a 5 minuti
    "initial_equity": 1000.0,
    "risk_reward": 4.0      # Alziamo il Target a 1 a 4
}

def fetch_5m_data(symbol):
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

def run_advanced_backtest(symbol, df):
    if df.empty or len(df) < 50:
        return None

    equity = CONFIG["initial_equity"]
    position = "NONE"
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    
    trades_count = 0
    winning_trades = 0
    
    # Finestra temporale per trovare i livelli (ultime 4 ore = 48 candele da 5 min)
    lookback_candles = 48 

    for i in range(lookback_candles, len(df)):
        current_row = df.iloc[i]
        price_close = current_row["close"]
        price_high = current_row["high"]
        price_low = current_row["low"]
        current_volume = current_row["volume"]

        # Livelli e media dei volumi per capire la forza
        window_candles = df.iloc[i - lookback_candles : i]
        resistance = window_candles['high'].max()
        support = window_candles['low'].min()
        avg_volume = window_candles['volume'].mean()

        # 1. GESTIONE OPERAZIONI APERTE
        if position == "LONG":
            if price_low <= stop_loss:
                equity -= (equity * 0.02) # Rischio 2%
                position = "NONE"
            elif price_high >= take_profit:
                equity += (equity * 0.02 * CONFIG["risk_reward"])
                winning_trades += 1
                position = "NONE"

        elif position == "SHORT":
            if price_high >= stop_loss:
                equity -= (equity * 0.02)
                position = "NONE"
            elif price_low <= take_profit:
                equity += (equity * 0.02 * CONFIG["risk_reward"])
                winning_trades += 1
                position = "NONE"

        # 2. LOGICA DI INGRESSO CON FILTRO VOLUMI (Il bot capisce la finta)
        if position == "NONE":
            
            # Falsa Rottura della Resistenza: il volume deve essere BASSO (finta spinta)
            if price_high > resistance and price_close < resistance:
                if current_volume < (avg_volume * 1.5): # Se i volumi sono troppo alti, è un breakout vero ed evitiamo lo Short
                    position = "SHORT"
                    entry_price = price_close
                    # SL millimetrico: appena sopra il massimo della candela corrente
                    stop_loss = price_high + (price_high * 0.0003) 
                    risk_dist = stop_loss - entry_price
                    take_profit = entry_price - (risk_dist * CONFIG["risk_reward"])
                    trades_count += 1

            # Falsa Rottura del Supporto: volumi bassi sul break
            elif price_low < support and price_close > support:
                if current_volume < (avg_volume * 1.5):
                    position = "LONG"
                    entry_price = price_close
                    # SL millimetrico: appena sotto il minimo della candela corrente
                    stop_loss = price_low - (price_low * 0.0003)
                    risk_dist = entry_price - stop_loss
                    take_profit = entry_price + (risk_dist * CONFIG["risk_reward"])
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
    print("🔥 SENTINEL LIVELLI EVOLUTO - TRADING ISTITUZIONALE")
    print("⚡ TIMEFRAME 5 MINUTI | TARGET 1:4 | FILTRO VOLUMI")
    print("====================================================\n")
    
    for pair in CONFIG["pairs"]:
        print(f"📥 Scaricando flussi a 5 min per {pair}...")
        df_hist = fetch_5m_data(pair)
        results = run_advanced_backtest(pair, df_hist)
        
        if results:
            print(f"📊 RISULTATI FINALI PER {pair.replace('USDT', '')}:")
            for key, value in results.items():
                print(f"   🔹 {key}: {value}")
            print("-" * 52)