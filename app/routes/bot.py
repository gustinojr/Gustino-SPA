from flask import Blueprint, redirect, render_template, jsonify
import telebot
import threading
import os
import time

bot_bp = Blueprint("bot", __name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

current_chat_id = None
bot_running = False

# === HANDLER PER OTTENERE CHAT_ID ===
@bot.message_handler(func=lambda m: True)
def save_chat_id(message):
    global current_chat_id
    current_chat_id = message.chat.id
    print(f"CHAT ID RICEVUTO: {current_chat_id}")


def start_polling():
    global bot_running
    if bot_running:
        print("Bot già in esecuzione, non avvio un nuovo polling.")
        return

    bot_running = True
    try:
        bot.delete_webhook(drop_pending_updates=True)
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print("Errore nel bot:", e)
    finally:
        bot_running = False


# === ROUTE /start-bot ===
@bot_bp.route("/start-bot")
def start_bot():
    try:
        bot.delete_webhook(drop_pending_updates=True)
        threading.Thread(target=start_polling, daemon=True).start()
        print("Bot avviato correttamente.")

    except Exception as e:
        print("Errore nel bot:", e)

    # Vai alla pagina che aspetta il chat_id
    return redirect("/wait-for-chatid")


# === ROUTE /wait-for-chatid ===
@bot_bp.route("/wait-for-chatid")
def wait_for_chatid():
    return render_template("wait_for_chatid.html")


# === API POLLING ===
@bot_bp.route("/check-chatid")
def check_chatid():
    global current_chat_id
    if current_chat_id:
        return jsonify({"chat_id": current_chat_id})
    return jsonify({"chat_id": None})
