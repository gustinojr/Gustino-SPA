# app/telegram_polling.py
import threading
import telebot
import os

# Token del bot
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Variabili globali
bot_thread = None
bot_running = False
chat_id_global = None

def start_polling():
    """
    Avvia il bot in un thread separato. Se già in esecuzione,
    non fa nulla ma restituisce True per il redirect.
    """
    global bot_thread, bot_running

    if bot_running:
        print("Bot già in esecuzione.")
        return True  # indica che il bot è già attivo

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
    return True


# Handler per salvare il chat_id alla prima interazione
@bot.message_handler(func=lambda m: True)
def save_chat_id(message):
    global chat_id_global
    if chat_id_global is None:
        chat_id_global = message.chat.id
        print(f"Chat ID registrato: {chat_id_global}")
        bot.reply_to(message, "Ciao! Chat ID registrato correttamente.")


# Handler specifico per /start (opzionale)
@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "Ciao! Bot avviato correttamente.")
