from flask import Blueprint, render_template, jsonify, redirect
import telebot
import threading
import os

bot_bp = Blueprint("bot", __name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Telegram Bot Token non impostato!")

bot = telebot.TeleBot(TOKEN)
current_chat_id = None
bot_running = False

# Handler per salvare chat_id
@bot.message_handler(func=lambda m: True)
def save_chat_id(message):
    global current_chat_id
    current_chat_id = message.chat.id
    print("CHAT ID RICEVUTO:", current_chat_id)

# Funzione per avviare polling
def start_polling():
    global bot_running
    if bot_running:
        return
    bot_running = True
    try:
        bot.delete_webhook(drop_pending_updates=True)
        bot.infinity_polling(timeout=60)
    except Exception as e:
        print("Errore nel bot:", e)
    finally:
        bot_running = False

# Route per avviare bot
@bot_bp.route("/start-bot")
def start_bot():
    threading.Thread(target=start_polling, daemon=True).start()
    return redirect("/wait-for-chatid")

# Route per mostrare pagina che aspetta chat_id
@bot_bp.route("/wait-for-chatid")
def wait_for_chatid():
    return render_template("wait_for_chatid.html")

# API per controllare chat_id
@bot_bp.route("/check-chatid")
def check_chatid():
    global current_chat_id
    return jsonify({"chat_id": current_chat_id})
