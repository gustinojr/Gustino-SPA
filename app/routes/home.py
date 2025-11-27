from flask import Blueprint, render_template
from datetime import datetime


home_bp = Blueprint("home_bp", __name__)

@home_bp.route("/")
def home():
    return render_template("home.html")

@home_bp.route("/startBot")
def start_bot():
    return render_template("start_bot.html")
