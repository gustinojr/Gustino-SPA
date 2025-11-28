# app/telegram_polling.py
import threading
import telebot
import os

# Token del bot
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Variabile globale per tracciare lo stato del bot
bot_thread = None
bot_running = False

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

# Esempio di handler
@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "Ciao! Bot avviato correttamente.")
