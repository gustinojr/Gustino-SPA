from flask import Blueprint, render_template, redirect, url_for, jsonify
from app.telegram_polling import start_polling, bot_running

home_bp = Blueprint("home_bp", __name__)

# Pagina principale
@home_bp.route("/")
def home():
    return render_template("home.html")


# Avvia il bot (chiamata dalla UI)
@home_bp.route("/start-bot")
def start_bot():
    ok = start_polling()
    if not ok:
        return "Bot già in esecuzione", 200

    return redirect(url_for("home_bp.wait_for_chatid"))


# Pagina di attesa per ottenere chat_id
@home_bp.route("/wait-for-chatid")
def wait_for_chatid():
    return render_template("wait_for_chatid.html")


# Endpoint AJAX per verificare se il bot ha ricevuto un messaggio
@home_bp.route("/check-chat")
def check_chat():
    try:
        from app.telegram_polling import chat_id_global
    except ImportError:
        chat_id_global = None

    if chat_id_global is None:
        return jsonify({"waiting": True})
    return jsonify({"waiting": False, "chat_id": chat_id_global})
