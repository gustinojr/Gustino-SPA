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

def start_bot_polling():
    global bot_thread, bot_running

    if bot_running:
        print("Bot già in esecuzione")
        return

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
