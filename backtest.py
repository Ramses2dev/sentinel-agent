import pandas as pd
import requests
from datetime import datetime

# CONFIGURAZIONE DI BASE
CONFIG = {
    "pairs": ["BTC", "ETH", "SOL"],
    "timeframe": "5m",
    "lookback_candles": 48,
    "volume_filter_multiplier": 1.5
}

# I TRE SCENARI DA CONFRONTARE
TARGETS_TO_TEST = [3.0, 4.0, 5.0]

def fetch_historical_data(symbol, limit=1000):
    """Scarica lo storico dei prezzi da Binance"""
    binance_symbol = f"{symbol}USDT"
    url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval={CONFIG['timeframe']}&limit={limit}"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        df = pd.DataFrame(data).iloc[:, 0:6].copy()
        df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col])
        return df
    except Exception as e:
        print(f"⚠️ Errore nel caricamento dello storico per {symbol}: {e}")
        return pd.DataFrame()

def run_mega_backtest():
    print("====================================================")
    print("📊 SENTINEL AGENT V3 - COMPARATORE DI RISK/REWARD")
    print("====================================================\n")
    
    summary_results = []

    for symbol in CONFIG["pairs"]:
        print(f"📥 Scaricamento dati storici per {symbol}...")
        df = fetch_historical_data(symbol, limit=1000)
        
        if df.empty or len(df) < CONFIG["lookback_candles"] + 1:
            print(f"❌ Dati insufficienti per {symbol}.\n")
            continue
            
        # Per ogni moneta, facciamo girare i 3 diversi target
        for rr in TARGETS_TO_TEST:
            total_trades = 0
            win_trades = 0
            loss_trades = 0
            
            for i in range(CONFIG["lookback_candles"] + 1, len(df)):
                window = df.iloc[i - (CONFIG["lookback_candles"] + 1) : i - 1]
                current_candle = df.iloc[i]
                
                resistance = window["high"].max()
                support = window["low"].min()
                avg_volume = window["volume"].mean()
                
                price_close = current_candle["close"]
                price_high = current_candle["high"]
                price_low = current_candle["low"]
                volume = current_candle["volume"]
                
                # Semplice simulazione statistica basata sull'andamento delle candele successive
                # Se il prezzo si muove a favore del trade nei blocchi successivi, lo conta come Gain
                if price_high > resistance and price_close < resistance:
                    if volume < (avg_volume * CONFIG["volume_filter_multiplier"]):
                        total_trades += 1
                        if price_close > df.iloc[min(i+5, len(df)-1)]["close"]: 
                            win_trades += 1
                        else:
                            loss_trades += 1

                elif price_low < support and price_close > support:
                    if volume < (avg_volume * CONFIG["volume_filter_multiplier"]):
                        total_trades += 1
                        if price_close < df.iloc[min(i+5, len(df)-1)]["close"]:
                            win_trades += 1
                        else:
                            loss_trades += 1

            win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
            profit_loss_units = (win_trades * rr) - loss_trades if total_trades > 0 else 0
            
            summary_results.append({
                "Asset": symbol,
                "R:R": f"1:{int(rr)}",
                "Trades": total_trades,
                "Win Rate": f"{win_rate:.2f}%",
                "Rendimento Finale": f"{'+' if profit_loss_units >= 0 else ''}{profit_loss_units:.2f}R"
            })

    # STAMPA FINALE DEL TABELLONE COMPARATIVO
    print("\n🏁 ====================================================")
    print("🏆 CLASSIFICA FINALE CONFIGURAZIONI")
    print("====================================================")
    print(f"{'ASSET':<8} | {'TARGET':<8} | {'TRADES':<6} | {'WIN RATE':<10} | {'RENDIMENTO':<10}")
    print("-" * 55)
    for res in summary_results:
        print(f"{res['Asset']:<8} | {res['R:R']:<8} | {res['Trades']:<6} | {res['Win Rate']:<10} | {res['Rendimento Finale']:<10}")
    print("====================================================\n")

if __name__ == "__main__":
    run_mega_backtest()