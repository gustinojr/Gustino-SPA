from flask import Blueprint, jsonify
from app.telegram_polling import start_polling

bot_bp = Blueprint("bot_bp", __name__)

@bot_bp.route("/start-bot")
def start_bot():
    ok = start_polling()
    if not ok:
        return jsonify({"status": "already running"})
    return jsonify({"status": "ok"})
