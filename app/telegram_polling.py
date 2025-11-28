import threading
import telebot
import os

bot = None
bot_running = False
chat_id_global = None  # per salvare l'ID della chat dell'utente

def start_bot():
    global bot, bot_running
    if bot_running:
        print("Bot già in esecuzione")
        return

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise Exception("TELEGRAM_BOT_TOKEN non settato!")

    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=["start"])
    def handle_start(message):
        global chat_id_global
        chat_id_global = message.chat.id
        bot.reply_to(message, "Ciao! Invia il tuo codice.")

    bot_running = True
    print("Avvio bot Telegram...")

    # Avvio polling in thread separato
    thread = threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True))
    thread.daemon = True
    thread.start()
