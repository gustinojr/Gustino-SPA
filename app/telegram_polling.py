import time
import requests
import threading
from app import db
from app.models import User

def polling_loop(app):
    with app.app_context():  # <-- importantissimo
        token = app.config["TELEGRAM_BOT_TOKEN"]
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        last_update_id = None

        while True:
            try:
                params = {}
                if last_update_id:
                    params["offset"] = last_update_id + 1

                r = requests.get(url, params=params, timeout=5)
                data = r.json()

                for update in data.get("result", []):
                    last_update_id = update["update_id"]

                    if "message" in update:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"]["text"]

                        user = User.query.filter_by(chat_id=chat_id).first()
                        if not user:
                            user = User(chat_id=chat_id)
                            db.session.add(user)
                            db.session.commit()

                time.sleep(1)

            except Exception as e:
                print("Polling Error:", e)
                time.sleep(2)


def start_polling(app):
    t = threading.Thread(target=polling_loop, args=(app,), daemon=True)
    t.start()
