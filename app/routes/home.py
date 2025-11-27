from flask import Blueprint, render_template
from datetime import datetime


home_bp = Blueprint("home_bp", __name__)

@home_bp.route("/")
def home():
    return render_template("home.html")
