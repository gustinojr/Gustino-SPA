from flask import Blueprint, redirect, url_for, render_template
from app.telegram_polling import start_bot_polling

home_bp = Blueprint("home_bp", __name__)

@home_bp.route("/wait-for-chatid")
def wait_for_chatid():
        # Avvia polling (se non è già in esecuzione)
    start_bot_polling()
    return render_template("wait_for_chatid.html")


@home_bp.route("/")
def home():
    return render_template("home.html")
