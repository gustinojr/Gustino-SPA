from flask import Blueprint, redirect, url_for
from app.telegram_polling import start_bot_polling

home_bp = Blueprint("home_bp", __name__)

@home_bp.route("/start-bot")
def start_bot():
    start_bot_polling()  # avvia il bot in background
    return redirect(url_for("home_bp.home"))  # torna alla home

@home_bp.route("/")
def home():
    return render_template("home.html")
