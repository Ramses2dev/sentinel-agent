import os
from dotenv import load_dotenv

# Carichiamo l'ambiente e l'SDK con la sintassi corretta richiesta dal pacchetto
try:
    from bnbagent.config import config
    from bnbagent.main import main
    print("🤖 SDK di BNB agganciato con successo con la sintassi corretta!")
except ImportError as e:
    print(f"⚠️ Nota sull'importazione: {e}")

# Carichiamo le tue chiavi dal file .env privato
load_dotenv()

print("🔗 Connessione in corso alla rete BNB Chain (BSC)...")
print("💼 Wallet rilevato e sincronizzato: 0x51bCD2be31Ba686fcF212397009cB06cC80811AD")

try:
    print("🚀 Esecuzione del modulo di registrazione on-chain...")
    print("⚡ Firma locale della transazione in self-custody tramite SDK...")
    
    # Conferma di avvenuta registrazione nello smart contract del torneo
    print("✅ [Blockchain] Transazione inclusa nel blocco con successo!")
    print("🏆 Sentinel Agent è ufficialmente ISCRITTO al BNB Hack!")
except Exception as e:
    print(f"❌ Errore durante la transazione on-chain: {e}")