import threading
import time
import telebot
import os
from flask import current_app
from dotenv import load_dotenv

load_dotenv()  # carica il .env
token = os.getenv("TELEGRAM_BOT_TOKEN")

if token is None:
    raise ValueError("TELEGRAM_BOT_TOKEN non trovato! Controlla il .env")
    
bot_thread = None
bot_running = False


def start_bot_polling():
    global bot_thread, bot_running

    # Evita di avviare il bot più volte
    if bot_running:
        return

    bot_running = True

    def run_bot():
        from app import create_app
        app = create_app()
        with app.app_context():
            token = current_app.config["TELEGRAM_BOT_TOKEN"]
            bot = telebot.TeleBot(token)

            print("BOT POLLING STARTED")

            bot.infinity_polling(timeout=10, long_polling_timeout=5)

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
