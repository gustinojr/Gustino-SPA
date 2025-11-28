from flask import Blueprint, jsonify
from app.telegram_polling import start_bot_polling

bp = Blueprint("main", __name__)

@bp.route("/start-bot")
def start_bot():
    start_bot_polling()
    return jsonify({"status": "ok"})
