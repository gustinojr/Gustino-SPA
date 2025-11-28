from flask import Blueprint, jsonify
from app.telegram_polling import start_bot_polling

bot_bp = Blueprint("'bot'", __name__)

bot_running = False

@bot_bp.route('/start-bot')
def start_bot():
    start_bot_polling()
    return jsonify({"status": "ok"})
