# app/bot.py
import os
import requests
import json
from flask import current_app as app, request, Blueprint

bp = Blueprint("bot", __name__)

TOKEN = os.environ.get("TELEGRAM_TOKEN")  # metti il token nel .env / secrets
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

CHAT_STORE = os.environ.get("CHAT_STORE", "/tmp/chat_ids.json")
# CHAT_STORE può essere un file oppure un percorso DB. /tmp è ok per test, su produzione usa DB/persistent volume.

def load_chat_ids():
    try:
        with open(CHAT_STORE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_chat_ids(data):
    with open(CHAT_STORE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

@bp.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True, silent=True)
    app.logger.info("Webhook update: %s", update)

    # Gestione standard di diversi tipi di update (message, callback_query, etc.)
    chat_id = None
    if not update:
        return "no update", 400

    if "message" in update:
        msg = update["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        # salva user info se vuoi
    elif "callback_query" in update:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
    # aggiungi altri tipi se ti servono

    if chat_id:
        # salva chat_id (mappa chat_id -> metadata)
        store = load_chat_ids()
        store[str(chat_id)] = {
            "chat_id": chat_id,
            "last_update": update.get("update_id"),
        }
        save_chat_ids(store)
        app.logger.info("Saved chat_id %s", chat_id)

        # risposta di test (opzionale)
        # send_message(chat_id, "Ricevuto! Chat ID salvato.")

    return "OK"

# route helper per debug / check
@bp.route("/_chat-ids", methods=["GET"])
def list_chat_ids():
    store = load_chat_ids()
    return {"count": len(store), "items": list(store.values())}
