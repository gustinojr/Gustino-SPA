import threading
import telebot
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Token del bot
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment variables!")

bot = telebot.TeleBot(TOKEN)

# Stato globale del bot
bot_thread = None
bot_running = False
chat_id_global = None

# Cache temporanea per chat_id pendenti (per gestire la registrazione)
pending_chat_ids = {}

def start_polling():
    """Avvia il bot in un thread separato."""
    global bot_thread, bot_running

    if bot_running:
        print("Bot già in esecuzione, non avvio un nuovo polling.")
        return False  # ritorna False se già in esecuzione

    def run_bot():
        global bot_running
        try:
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Errore nel bot: {e}")
            bot_running = False
            # Riavvia automaticamente il bot in caso di errore
            import time
            time.sleep(5)
            if not bot_running:
                start_polling()
        finally:
            bot_running = False

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    bot_running = True
    print("Bot avviato correttamente.")
    return True  # ritorna True se il bot è stato avviato

# Handler per tutti i messaggi
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global chat_id_global
    chat_id = message.chat.id
    chat_id_global = chat_id  # salva il chat_id globale
    
    # Salva in cache temporanea con timestamp
    import time
    pending_chat_ids[chat_id] = time.time()
    
    # Pulisci chat_id vecchi (oltre 10 minuti)
    current_time = time.time()
    to_remove = [cid for cid, timestamp in pending_chat_ids.items() if current_time - timestamp > 600]
    for cid in to_remove:
        del pending_chat_ids[cid]
    
    if message.text and message.text.startswith('/start'):
        bot.reply_to(message, "Ciao! Torna sul sito per completare la registrazione.")
    else:
        bot.reply_to(message, "Messaggio ricevuto! Torna sul sito per continuare.")
