# run.py o app/view.py
from flask import Flask, jsonify, render_template
import json, os

CHAT_STORE = os.environ.get("CHAT_STORE", "/tmp/chat_ids.json")

def load_chat_ids():
    try:
        with open(CHAT_STORE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

app = Flask(__name__)

@app.route("/check-chat")
def check_chat():
    store = load_chat_ids()
    # se vuoi mostrare HTML
    return render_template("check_chat.html", chat_items=store.values())

@app.route("/api/chat-ids")
def api_chat_ids():
    return jsonify(load_chat_ids())
