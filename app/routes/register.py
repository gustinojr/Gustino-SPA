from flask import Blueprint, request, render_template, redirect, flash, current_app, url_for
from app.models import User, db
from app.telegram_utils import tg_send
from config import Config

register_bp = Blueprint("register_bp", __name__)

@register_bp.route("/register", methods=["GET", "POST"])
def register():
    promo = request.args.get('promo_code')
    chat_id = request.args.get('chat_id')

    # Se il promo è speciale, redirect alla pagina premio
    if promo == Config.SPECIAL_CODE and request.method == 'GET':
        return redirect(url_for('register_bp.special_prize', chat_id=chat_id, promo_code=promo))

    if request.method == 'GET':
        user = None
        if chat_id:
            user = User.query.filter_by(chat_id=str(chat_id)).first()
            if not user:
                # lightweight object for template when user not yet persisted
                class TempUser:
                    def __init__(self, chat_id):
                        self.chat_id = chat_id
                        self.name = None
                        self.id = None
                user = TempUser(chat_id)
        return render_template('registration.html', user=user, bot_username=current_app.config.get('TELEGRAM_BOT_USERNAME', 'GustinoSpa_bot'))

    # POST - save or update user
    name = request.form.get('name')
    email = request.form.get('email')
    chat_id = request.form.get('chat_id') or chat_id

    if not chat_id:
        flash('Chat ID mancante. Apri il bot e riprova.')
        return redirect('/')

    user = User.query.filter_by(chat_id=str(chat_id)).first()
    if not user:
        user = User(chat_id=str(chat_id), name=name, code_used=promo)
        db.session.add(user)
    else:
        user.name = name
        if promo:
            user.code_used = promo

    db.session.commit()

    # invia messaggi su Telegram: all'utente e copia all'owner
    tg_send(user.chat_id, f"Ciao {user.name}, registrazione completata! Torna sul sito per prenotare.")
    owner_chat = current_app.config.get('OWNER_CHAT_ID')
    if owner_chat:
        tg_send(owner_chat, f"{user.name} si è registrato. Promo: {promo or 'N/A'} - chat_id: {user.chat_id}")

    return redirect(f'/booking/{user.id}')


@register_bp.route("/special-prize", methods=["GET", "POST"])
def special_prize():
    promo = request.args.get('promo_code') or request.form.get('promo_code')
    chat_id = request.args.get('chat_id') or request.form.get('chat_id')

    if request.method == 'GET':
        return render_template('special_prize.html', chat_id=chat_id)

    # POST - save special user
    name = request.form.get('name')
    email = request.form.get('email', '')

    if not chat_id:
        flash('Chat ID mancante. Apri il bot e riprova.')
        return redirect('/')

    user = User.query.filter_by(chat_id=str(chat_id)).first()
    if not user:
        user = User(chat_id=str(chat_id), name=name, code_used=promo)
        db.session.add(user)
    else:
        user.name = name
        user.code_used = promo

    db.session.commit()

    # Messaggio speciale all'utente
    special_message = (
        f"🎁 Congratulazioni {user.name}!\n\n"
        f"Sei il nostro PRIMO CLIENTE! 🎉\n\n"
        f"Hai ricevuto il tuo premio speciale:\n"
        f"🍽️ CENA speciale cucinata da Gustino!\n"
        f"💆‍♀️ Sessioni di massaggio ILLIMITATE!\n\n"
        f"📅 Valido dal 20/12/2025 al 31/01/2026\n\n"
        f"Ci vediamo presto! ✨"
    )
    tg_send(user.chat_id, special_message)

    # Messaggio all'owner
    owner_chat = current_app.config.get('OWNER_CHAT_ID')
    if owner_chat:
        owner_message = (
            f"⭐ PRIMO CLIENTE REGISTRATO! 🎉\n\n"
            f"👤 Nome: {user.name}\n"
            f"🎟️ Codice: {Config.SPECIAL_CODE}\n"
            f"🎁 Premio: Massaggi ILLIMITATI\n"
            f"📅 Valido: 20/12/2025 - 31/01/2026"
        )
        tg_send(owner_chat, owner_message)

    flash("🎁 Premio Speciale confermato! Riceverai tutti i dettagli su Telegram.")
    return redirect(f'/booking/{user.id}')

