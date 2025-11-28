from flask import Blueprint, redirect, url_for, render_template
from app.telegram_polling import start_bot_polling

home_bp = Blueprint("home_bp", __name__)

@home_bp.route("/start-bot")
def start_bot():
    from app.telegram_polling import start_bot_polling

    # Avvia polling (se non è già in esecuzione)
    start_bot_polling()

    # Poi manda l’utente nella pagina di attesa
    return redirect(url_for("home.wait_for_chatid"))

@home_bp.route("/")
def home():
    return render_template("home.html")
