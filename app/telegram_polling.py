import time
import requests
import threading
from flask import current_app
from app import db
from app.models import User

last_update_id = None

def polling_loop(app):
    global last_update_id

    token = app.config["TELEGRAM_BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/getUpdates"

    with app.app_context():
        while True:
            try:
                params = {}
                if last_update_id:
                    params["offset"] = last_update_id + 1

                r = requests.get(url, params=params, timeout=5)
                data = r.json()

                if "result" not in data:
                    time.sleep(1)
                    continue

                for update in data["result"]:
                    last_update_id = update["update_id"]

                    if "message" in update:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"]["text"]

                        current_app.logger.info(f"New Telegram message from {chat_id}: {text}")

                        # 👇 QUI SALVI IL CHAT_ID NEL DATABASE
                        user = User.query.filter_by(chat_id=chat_id).first()
                        if not user:
                            user = User(chat_id=chat_id)
                            db.session.add(user)
                            db.session.commit()

                time.sleep(1)

            except Exception as e:
                current_app.logger.error(f"Polling error: {e}")
                time.sleep(2)


def start_polling(app):
    thread = threading.Thread(target=polling_loop, args=(app,), daemon=True)
    thread.start()
