import threading
import telebot
import os

bot_thread = None
bot_running = False
bot = None  # <- bot globale

def start_polling():
    global bot_running, bot, bot_thread
    if bot_running:
        print("Bot già in esecuzione")
        return False

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=["start"])
    def start(msg):
        bot.reply_to(msg, "Ciao! Invia il tuo codice.")

    bot_running = True
    print("Polling avviato")

    bot_thread = threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True))
    bot_thread.daemon = True
    bot_thread.start()
    return True
