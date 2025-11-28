from flask import Blueprint, render_template, redirect, url_for
from app.telegram_polling import start_bot_polling

home_bp = Blueprint("home_bp", __name__)

@home_bp.route("/")
def home():
    return render_template("home.html")

@home_bp.route("/start-bot")
def start_bot():
    start_bot_polling()
    return redirect(url_for("home_bp.wait_for_chatid"))

@home_bp.route("/wait-for-chatid")
def wait_for_chatid():
    return render_template("wait_for_chatid.html")
