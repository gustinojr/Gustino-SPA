# app/telegram_polling.py
import threading
import telebot
import os

# Token del bot
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Variabili globali per tracciare lo stato del bot
bot_thread = None
bot_running = False
chat_id_global = None

def start_polling():
    global bot_thread, bot_running

    if bot_running:
        print("Bot già in esecuzione, non avvio un nuovo polling.")
        return

    def run_bot():
        global bot_running
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print(f"Errore nel bot: {e}")
        finally:
            bot_running = False

    # Avvia il bot in un thread separato
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    bot_running = True
    print("Bot avviato correttamente.")

# Esempio di handler per il comando /start
@bot.message_handler(commands=["start"])
def send_welcome(message):
    global chat_id_global
    chat_id_global = message.chat.id  # Salva il chat_id globale
    bot.reply_to(message, f"Ciao! Bot avviato correttamente. Chat ID registrato: {chat_id_global}")

# Handler generico per tutti i messaggi
@bot.message_handler(func=lambda m: True)
def save_chat_id(message):
    global chat_id_global
    if chat_id_global is None:
        chat_id_global = message.chat.id
        print(f"Chat ID registrato: {chat_id_global}")
