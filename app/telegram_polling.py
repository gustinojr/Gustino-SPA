import threading
import telebot
import os

token = os.getenv("TELEGRAM_BOT_TOKEN")

bot_running = False     # <--- QUI! Variabile globale

def run_bot():
    global bot_running
    bot_running = True

    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['start'])
    def start(msg):
        bot.reply_to(msg, "Bot attivo!")

    bot.infinity_polling()


def start_bot_polling():
    global bot_running

    if bot_running:   # <--- ORA ESISTE
        print("Bot già in esecuzione")
        return

    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
    print("Bot avviato in polling")
