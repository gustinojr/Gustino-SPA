import threading
import telebot
import os

bot_thread = None
bot_running = False

def run_bot():
    global bot_running
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=["start"])
    def start(msg):
        bot.reply_to(msg, "Ciao! Invia il tuo codice.")

    bot_running = True
    print("Polling avviato")
    bot.infinity_polling()

def start_polling():
    global bot_running

    if bot_running:
        print("Bot già in esecuzione")
        return False

    bot_running = True
    print("Polling avviato")

    thread = threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True))
    thread.daemon = True
    thread.start()
    return True
