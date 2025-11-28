from flask import Blueprint, jsonify, session
from app import db
from app.models import User

check_bp = Blueprint("check", __name__)

@home_bp.route("/wait-for-chatid")
def wait_for_chatid():
    return render_template("wait_for_chatid.html")

    if chat_id:
        return jsonify({"ok": True, "promo": promo})

    return jsonify({"ok": False})
