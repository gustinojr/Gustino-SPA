from flask import Blueprint, jsonify
from app.telegram_bot import start_bot

bot_bp = Blueprint("bot_bp", __name__)

@bot_bp.route('/start-bot')
def start_bot_route():
    start_bot()
    return jsonify({"status": "ok", "message": "Bot avviato o già in esecuzione"})
