import requests
from flask import current_app

def tg_send(chat_id, text):
    if not chat_id:
        current_app.logger.warning("⚠ Cannot send Telegram message: chat_id is None")
        return

    token = current_app.config.get("TELEGRAM_BOT_TOKEN")
    if not token:
        current_app.logger.error("⚠ TELEGRAM_BOT_TOKEN not set in config")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        if not response.ok:
            current_app.logger.error(f"Telegram API error: {response.status_code} {response.text}")
        else:
            current_app.logger.info(f"Telegram message sent to {chat_id}")
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Telegram send ERROR: {e}")
