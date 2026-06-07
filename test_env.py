import os
import requests
from web3 import Web3
from dotenv import load_dotenv

# Caricamento del file .env
load_dotenv()

def run_diagnostic():
    print("====================================================")
    print("🔍 SENTINEL AGENT V3 - DIAGNOSTICA API E WALLET")
    print("====================================================\n")

    # 1. VERIFICA CHIAVI NEL FILE .env
    print("1️⃣ Controllo file .env...")
    wallet = os.getenv("WALLET_ADDRESS")
    pkey = os.getenv("PRIVATE_KEY")
    
    if not wallet or wallet == "0x0000000000000000000000000000000000000000":
        print("❌ ERRORE: WALLET_ADDRESS mancante o non configurato correttamente nel file .env.\n")
        return
    else:
        print(f"✅ Indirizzo Wallet rilevato: {wallet}")
        
    if not pkey:
        print("⚠️ AVVISO: PRIVATE_KEY non trovata nel file .env. (Necessaria solo se il bot firma trade on-chain reali).")
    else:
        print("✅ Chiave Privata caricata in memoria correttamente.")
    print("-" * 50)

    # 2. VERIFICA CONNESSIONE BLOCKCHAIN (BNB Chain)
    print("2️⃣ Connessione al nodo BNB Chain...")
    rpc_url = "https://bsc-dataseed.binance.org/"
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if w3.is_connected():
        print("✅ Connessione con BNB Chain stabilita con successo!")
        # Controllo del saldo reale in BNB del wallet
        try:
            balance_wei = w3.eth.get_balance(wallet)
            balance_bnb = w3.from_wei(balance_wei, 'ether')
            print(f"💰 Saldo attuale del tuo wallet: {balance_bnb:.5f} BNB")
            if balance_bnb == 0:
                print("⚠️ Attenzione: Il saldo è 0 BNB. Avrai bisogno di una frazione di BNB per pagare il gas durante la gara.")
        except Exception as e:
            print(f"⚠️ Impossibile recuperare il saldo del wallet: {e}")
    else:
        print("❌ ERRORE: Impossibile connettersi al nodo RPC di BNB Chain. Controlla la tua connessione internet.")
    print("-" * 50)

    # 3. VERIFICA API DATI (Binance / CMC Gateway)
    print("3️⃣ Test canali di ricezione dati di mercato...")
    test_url = "https://api.binance.com/api/v3/ping"
    try:
        response = requests.get(test_url, timeout=10)
        if response.status_code == 200:
            print("✅ API di ricezione prezzi online e reattiva (Ping OK).")
        else:
            print(f"❌ API di ricezione prezzi ha risposto con codice di errore: {response.status_code}")
    except Exception as e:
        print(f"❌ ERRORE: Timeout o errore di connessione con i server dei prezzi: {e}")
    print("\n====================================================")
    print("🏁 DIAGNOSTICA COMPLETATA")
    print("====================================================")

if __name__ == "__main__":
    run_diagnostic()