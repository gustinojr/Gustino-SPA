from flask import Blueprint, render_template, redirect, url_for, jsonify, request
import app.telegram_polling as telegram_polling  # importa il modulo intero
from app.models import User, db, Booking
import os

home_bp = Blueprint("home_bp", __name__)

# Determina modalità webhook o polling
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "false").lower() == "true"

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
    # Controlla se c'è già un promo_code nei parametri
    promo_code = request.args.get('promo_code', '').strip()
    
    # Se c'è un promo_code, verifica se l'utente esiste già
    if promo_code:
        user = User.query.filter_by(code_used=promo_code.upper()).first()
        if user and user.chat_id:
            # Se ha nome, promo e chat_id --> vai al booking
            if user.name:
                print(f"✅ Utente completo (nome+promo+chat_id): {user.name}")
                return redirect(url_for("booking_bp.booking", user_id=user.id))
            # Se ha solo promo e chat_id ma NON nome --> vai alla registrazione
            else:
                print(f"⚠️ Utente incompleto (promo+chat_id ma senza nome): {user.chat_id}")
                return redirect(url_for("register_bp.register", chat_id=user.chat_id, promo_code=promo_code.upper()))
    
    # In modalità webhook, il bot è sempre attivo
    if USE_WEBHOOK:
        print("✅ Modalità WEBHOOK - bot sempre attivo")
    else:
        # Solo in modalità polling verifica se il bot è in esecuzione
        if not telegram_polling.bot_running:
            print("⚠️ Bot non in esecuzione, avvio...")
            telegram_polling.start_polling()
        else:
            print("✅ Bot già in esecuzione")
        print(f"📊 Stato bot: bot_running={telegram_polling.bot_running}, chat_id_global={telegram_polling.chat_id_global}")
    
    # Passa il promo_code alla pagina di attesa
    redirect_url = url_for("home_bp.wait_for_chatid")
    if promo_code:
        redirect_url += f"?promo_code={promo_code}"
    return redirect(redirect_url)

# Pagina di attesa per ottenere chat_id
@home_bp.route("/wait-for-chatid")
def wait_for_chatid():
    return render_template("wait_for_chatid.html")

# Endpoint AJAX per verificare se il bot ha ricevuto un messaggio (usato dal frontend)
@home_bp.route("/check-chatid")
def check_chatid():
    if USE_WEBHOOK:
        # Modalità webhook
        from app.telegram_webhook import get_latest_chat_id
        chat_id = get_latest_chat_id()
        print(f"🔍 [WEBHOOK] check_chatid chiamato - chat_id: {chat_id}")
    else:
        # Modalità polling
        chat_id = getattr(telegram_polling, "chat_id_global", None)
        print(f"🔍 [POLLING] check_chatid chiamato - chat_id_global: {chat_id}")
        print(f"🔍 bot_running: {telegram_polling.bot_running}")
        print(f"🔍 pending_chat_ids: {getattr(telegram_polling, 'pending_chat_ids', {})}")
    
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
        # Elimina tutte le tabelle
        db.drop_all()
        db.session.commit()
        
        # Ricrea tutte le tabelle
        db.create_all()
        db.session.commit()

        # Reset chat_id in base alla modalità
        if USE_WEBHOOK:
            # Modalità webhook: pulisci pending_chat_ids
            from app.telegram_webhook import pending_chat_ids
            pending_chat_ids.clear()
            print("🧹 pending_chat_ids pulito (modalità webhook)")
        else:
            # Modalità polling: reset chat_id_global
            telegram_polling.chat_id_global = None
            print("🧹 chat_id_global resettato (modalità polling)")
        
        return jsonify({
            "success": True,
            "message": "Database resettato e ricreato con successo"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
