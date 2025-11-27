from flask import Blueprint, render_template, session, jsonify
from app.models import User  # supponendo che tu abbia un modello User con chat_id
bot_bp = Blueprint('bot_bp', __name__)

@bot_bp.route('/bot')
def bot_page():
    # Pagina che mostra "Apri il bot Telegram" e fa partire il polling
    return render_template('bot.html')

@bot_bp.route('/check_chatid')
def check_chatid():
    temp_id = session.get('temp_id')
    user = User.query.filter_by(temp_identifier=temp_id).first()
    if user and user.chat_id:
        return jsonify({"chat_id_found": True, "promo_code": user.promo_code})
    return jsonify({"chat_id_found": False})
