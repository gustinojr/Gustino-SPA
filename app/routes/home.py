from flask import Blueprint, render_template, redirect, url_for, jsonify, request
import app.telegram_polling as telegram_polling  # importa il modulo intero
from app.models import User, db, Booking

home_bp = Blueprint("home_bp", __name__)

# Pagina principale
@home_bp.route("/")
def home():
    return render_template("home.html")

# Endpoint per verificare se un codice promo esiste già
@home_bp.route("/check-promo-code")
def check_promo_code():
    code = request.args.get('code', '').strip().upper()
    if not code:
        return jsonify({"exists": False})
    
    # Cerca utente con questo codice
    user = User.query.filter_by(code_used=code).first()
    if user:
        return jsonify({
            "exists": True,
            "user_id": user.id,
            "user_name": user.name,
            "is_special": user.code_used == "20121997"
        })
    
    return jsonify({"exists": False})

# Avvia il bot e reindirizza alla pagina di attesa
@home_bp.route("/start-bot")
def start_bot():
    telegram_polling.start_polling()
    return redirect(url_for("home_bp.wait_for_chatid"))

# Pagina di attesa per ottenere chat_id
@home_bp.route("/wait-for-chatid")
def wait_for_chatid():
    return render_template("wait_for_chatid.html")

# Endpoint AJAX per verificare se il bot ha ricevuto un messaggio (usato dal frontend)
@home_bp.route("/check-chatid")
def check_chatid():
    chat_id = getattr(telegram_polling, "chat_id_global", None)
    if chat_id is None:
        return jsonify({"chat_id": None})
    
    # Controlla se l'utente esiste già (ritorno cliente)
    existing_user = User.query.filter_by(chat_id=str(chat_id)).first()
    if existing_user:
        return jsonify({
            "chat_id": chat_id,
            "existing_user": True,
            "user_id": existing_user.id,
            "user_name": existing_user.name,
            "is_special": existing_user.code_used == "20121997"
        })
    
    return jsonify({"chat_id": chat_id, "existing_user": False})

# Endpoint per resettare il database (solo per sviluppo)
@home_bp.route("/reset-db")
def reset_db():
    try:
        # Elimina tutti i dati
        Booking.query.delete()
        User.query.delete()
        db.session.commit()
        
        # Reset chat_id_global
        telegram_polling.chat_id_global = None
        
        return jsonify({
            "success": True,
            "message": "Database resettato con successo"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
