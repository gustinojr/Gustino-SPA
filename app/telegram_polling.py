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

def start_polling():
    """Avvia il bot in un thread separato."""
    global bot_thread, bot_running

    if bot_running:
        print("Bot già in esecuzione, non avvio un nuovo polling.")
        return False  # ritorna False se già in esecuzione

    def run_bot():
        global bot_running
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print(f"Errore nel bot: {e}")
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
    chat_id_global = message.chat.id  # salva il chat_id globale
    
    if message.text and message.text.startswith('/start'):
        bot.reply_to(message, "Ciao! Torna sul sito per completare la registrazione.")
    else:
        bot.reply_to(message, "Messaggio ricevuto! Torna sul sito per continuare.")
