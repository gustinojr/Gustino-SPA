import threading
import time
import telebot
import os
from flask import current_app
from dotenv import load_dotenv
import telebot

load_dotenv()  # carica le variabili da .env

token = os.getenv("TELEGRAM_BOT_TOKEN")

if not token:
    raise ValueError("TELEGRAM_BOT_TOKEN non trovato! Controlla il .env")

bot = telebot.TeleBot(token)
    
bot_thread = None
bot_running = False

from threading import Thread

def start_bot_polling():
    thread = Thread(target=bot.infinity_polling, daemon=True)
    thread.start()

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
