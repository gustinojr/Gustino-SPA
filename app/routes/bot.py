import os
import json
import requests
from flask import Blueprint, request, current_app as app

bot_bp = Blueprint("bot", __name__)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"
CHAT_STORE = "/tmp/chat_ids.json"


def load_chat_ids():
    try:
        with open(CHAT_STORE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_chat_ids(data):
    with open(CHAT_STORE, "w", encoding="utf-8") as f:
        json.dump(data, f)


@bot_bp.route("/webhook", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True, force=True)
    app.logger.info("TELEGRAM UPDATE: %s", update)

    if not update:
        return "no update", 400

    chat_id = None

    # messaggio normale
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]

    # callback dei bottoni
    elif "callback_query" in update:
        chat_id = update["callback_query"]["message"]["chat"]["id"]

    if chat_id:
        store = load_chat_ids()
        store[str(chat_id)] = {"chat_id": chat_id}
        save_chat_ids(store)
        app.logger.info("Saved chat_id %s", chat_id)

    return "OK"
