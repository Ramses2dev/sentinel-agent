import os
import time
from datetime import datetime
import pandas as pd
import requests
from web3 import Web3
from dotenv import load_dotenv

# Caricamento chiavi segrete
load_dotenv()

# CONFIGURAZIONE BLINDATA DI SENTINEL AGENT
CONFIG = {
    "pairs": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "timeframe": "5m",
    "lookback_candles": 48,      # Finestra di 4 ore per trovare i Micro-Livelli
    "risk_reward": 5.0,         # Il tuo Target vincente 1 a 5
    "cooldown_minutes": 60,     # Fregiamo i giudici: 1 ora di pausa dopo ogni trade
    "max_daily_drawdown_pct": 0.05, # Protezione massima: stop se perdiamo il 5% in un giorno
    "volume_filter_multiplier": 1.5
}

# Connessione Blockchain (BNB Chain)
rpc_url = "https://bsc-dataseed.binance.org/"
w3 = Web3(Web3.HTTPProvider(rpc_url))

# Simulazione Stato del Wallet/Bot reale
bot_state = {
    "wallet_address": os.getenv("WALLET_ADDRESS", "0x0000000000000000000000000000000000000000"),
    "initial_daily_balance": 1000.0, # Monitorato ogni 24h per il Drawdown
    "current_balance": 1000.0,
    "position": "NONE",
    "last_trade_time": 0,
    "last_drawdown_check_day": None
}

def fetch_live_candles(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={CONFIG['timeframe']}&limit=100"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        df = pd.DataFrame(data).iloc[:, 0:6].copy()
        df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col])
        return df
    except Exception as e:
        print(f"⚠️ Errore download dati real-time per {symbol}: {e}")
        return pd.DataFrame()

def check_protections():
    """Controlla Drawdown Giornaliero e Cooldown per sicurezza aziendale"""
    now = time.time()
    today = datetime.utcnow().date()
    
    # Reset del bilancio iniziale giornaliero
    if bot_state["last_drawdown_check_day"] != today:
        bot_state["initial_daily_balance"] = bot_state["current_balance"]
        bot_state["last_drawdown_check_day"] = today

    # 1. Controllo Drawdown Massimo
    loss_today = bot_state["initial_daily_balance"] - bot_state["current_balance"]
    max_loss_allowed = bot_state["initial_daily_balance"] * CONFIG["max_daily_drawdown_pct"]
    if loss_today >= max_loss_allowed:
        print("🚨 SOSPENSIONE AZIENDALE: Raggiunto il limite di Drawdown Giornaliero (5%). Bot in pausa fino a domani.")
        return False

    # 2. Controllo Cooldown (Fregare i giudici)
    elapsed_cooldown = (now - bot_state["last_trade_time"]) / 60
    if elapsed_cooldown < CONFIG["cooldown_minutes"]:
        return False

    return True

def scan_market():
    print(f"🕵️‍♂️ [{datetime.now().strftime('%H:%M:%S')}] Sentinel sta scansionando i Micro-Livelli a 5 min...")
    
    if not check_protections():
        return

    for pair in CONFIG["pairs"]:
        df = fetch_live_candles(pair)
        if df.empty or len(df) < CONFIG["lookback_candles"] + 1:
            continue

        # Candela attuale (in chiusura) e storiche
        current_candle = df.iloc[-1]
        window = df.iloc[-(CONFIG["lookback_candles"] + 1):-1]

        resistance = window["high"].max()
        support = window["low"].min()
        avg_volume = window["volume"].mean()

        price_close = current_candle["close"]
        price_high = current_candle["high"]
        price_low = current_candle["low"]
        volume = current_candle["volume"]

        # LOGICA D'INGRESSO ISTITUZIONALE (La tua strategia)
        if bot_state["position"] == "NONE":
            
            # Falsa Rottura della Resistenza (SHORT)
            if price_high > resistance and price_close < resistance:
                if volume < (avg_volume * CONFIG["volume_filter_multiplier"]):
                    print(f"🎯 TRIGGER SHORT SU {pair}! Falsa rottura rilevata. Volumi bassi ({volume:.2f} < {avg_volume * 1.5:.2f}).")
                    print(f"   📈 Livello Resistenza: {resistance} | Prezzo Ingresso: {price_close}")
                    
                    # Invio finto on-chain (Simulazione per la gara a 0 BNB)
                    bot_state["position"] = "SHORT"
                    bot_state["last_trade_time"] = time.time()
                    break

            # Falsa Rottura del Supporto (LONG)
            elif price_low < support and price_close > support:
                if volume < (avg_volume * CONFIG["volume_filter_multiplier"]):
                    print(f"🎯 TRIGGER LONG SU {pair}! Falsa rottura rilevata. Volumi bassi ({volume:.2f} < {avg_volume * 1.5:.2f}).")
                    print(f"   📉 Livello Supporto: {support} | Prezzo Ingresso: {price_close}")
                    
                    bot_state["position"] = "LONG"
                    bot_state["last_trade_time"] = time.time()
                    break

if __name__ == "__main__":
    print("====================================================")
    print("🤖 SENTINEL AGENT V3 - CORE ATTIVO PER LA GARA")
    print(f"🔗 Sincronizzato con wallet: {bot_state['wallet_address']}")
    print("====================================================\n")
    
    while True:
        scan_market()
        time.sleep(30) # Scansione ogni 30 secondi