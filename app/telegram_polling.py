import threading
import telebot
import os

# Stato globale del bot
bot_thread = None
bot_running = False
chat_id_global = None  # Salva il chat_id del primo utente che scrive /start

# Funzione che gira nel thread separato
def run_bot():
    global bot_running, chat_id_global

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Variabile d'ambiente TELEGRAM_BOT_TOKEN non trovata!")

    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=["start"])
    def start(msg):
        global chat_id_global
        chat_id_global = msg.chat.id
        bot.reply_to(msg, "Ciao! Invia il tuo codice.")

    bot_running = True
    print("Polling avviato")
    bot.infinity_polling()

# Funzione per avviare il polling in background
def start_polling():
    global bot_running, bot_thread

    if bot_running:
        print("Bot già in esecuzione")
        return False

    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    return True
