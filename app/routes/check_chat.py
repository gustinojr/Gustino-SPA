from flask import Blueprint, jsonify, session
from app import db
from app.models import User

check_bp = Blueprint("check", __name__)

@check_bp.route("/checkChatId")
def check_chat_id():
    chat_id = session.get("chat_id")
    promo = session.get("promo_code")

    if chat_id:
        return jsonify({"ok": True, "promo": promo})

    return jsonify({"ok": False})
