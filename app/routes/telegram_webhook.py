from flask import Blueprint, request, current_app
from app import db
from app.models import User
import requests
from datetime import datetime

telegram_bp = Blueprint("telegram_bp", __name__)

@telegram_bp.route("/telegramWebhook", methods=["POST"])
def telegram_webhook():
    data = request.json
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # Save chat_id if user sent promo code
        promo_code = text.strip()
        user = User.query.filter_by(promo_code=promo_code).first()
        if user:
            user.chat_id = chat_id
            db.session.commit()

        # Notify owner
        owner_chat_id = current_app.config["ADMIN_CHAT_ID"]
        send_telegram(owner_chat_id, f"New chat_id received: {chat_id} for code {promo_code}")

        # Reply to user
        send_telegram(chat_id, "Torna sul sito per continuare la registrazione.")

    return "OK", 200


def send_telegram(chat_id, text):
    token = current_app.config["TELEGRAM_BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text})
