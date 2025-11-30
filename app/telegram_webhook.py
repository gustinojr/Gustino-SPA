import telebot
import os
from flask import request, jsonify, Blueprint
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Es: https://gustinospa.dpdns.org

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set!")

bot = telebot.TeleBot(TOKEN)

# Cache temporanea per chat_id (invece di variabile globale)
pending_chat_ids = {}

# IMPORTANTE: Registra l'handler PRIMA di creare le route
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    
    print(f"🔔 Webhook: Messaggio ricevuto da chat_id: {chat_id}")
    
    # Salva in cache temporanea con timestamp
    import time
    pending_chat_ids[chat_id] = time.time()
    
    print(f"💾 pending_chat_ids: {pending_chat_ids}")
    
    # Pulisci chat_id vecchi (oltre 10 minuti)
    current_time = time.time()
    to_remove = [cid for cid, timestamp in pending_chat_ids.items() if current_time - timestamp > 600]
    for cid in to_remove:
        del pending_chat_ids[cid]
    
    if message.text and message.text.startswith('/start'):
        bot.reply_to(message, "Ciao! Torna sul sito per completare la registrazione.")
    else:
        bot.reply_to(message, "Messaggio ricevuto! Torna sul sito per continuare.")

# Crea un Blueprint per il webhook
webhook_bp = Blueprint('webhook_bp', __name__)

@webhook_bp.route('/telegram-webhook', methods=['POST'])
def webhook():
    print(f"📥 Webhook chiamato - Content-Type: {request.headers.get('content-type')}")
    
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        print(f"📦 Dati ricevuti: {json_string[:200]}...")  # Primi 200 caratteri
        
        update = telebot.types.Update.de_json(json_string)
        print(f"✅ Update decodificato: update_id={update.update_id}")
        
        # Debug: verifica contenuto update
        if update.message:
            chat_id = update.message.chat.id
            print(f"🔍 Message trovato: chat_id={chat_id}, text={update.message.text}")
            
            # Elabora direttamente il messaggio invece di usare process_new_updates
            import time
            pending_chat_ids[chat_id] = time.time()
            print(f"💾 Chat ID salvato! pending_chat_ids: {pending_chat_ids}")
            
            # Pulisci chat_id vecchi (oltre 10 minuti)
            current_time = time.time()
            to_remove = [cid for cid, timestamp in pending_chat_ids.items() if current_time - timestamp > 600]
            for cid in to_remove:
                del pending_chat_ids[cid]
            
            # Rispondi al messaggio
            try:
                if update.message.text and update.message.text.startswith('/start'):
                    bot.send_message(chat_id, "Ciao! Torna sul sito per completare la registrazione.")
                else:
                    bot.send_message(chat_id, "Messaggio ricevuto! Torna sul sito per continuare.")
                print(f"✅ Risposta inviata a {chat_id}")
            except Exception as e:
                print(f"⚠️ Errore invio risposta: {e}")
        else:
            print(f"⚠️ Nessun message nell'update")
        
        return jsonify({"status": "ok"}), 200
    else:
        print(f"⚠️ Content-Type non valido: {request.headers.get('content-type')}")
        return jsonify({"error": "Invalid content type"}), 403

def setup_webhook(app):
    """Configura il webhook per Telegram"""
    
    # Registra il Blueprint
    app.register_blueprint(webhook_bp)
    
    # Imposta il webhook su Telegram
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/telegram-webhook"
        try:
            bot.remove_webhook()
            import time
            time.sleep(1)  # Aspetta un secondo prima di impostare il nuovo webhook
            result = bot.set_webhook(url=webhook_url)
            print(f"✅ Webhook impostato: {webhook_url} - Result: {result}")
        except Exception as e:
            print(f"⚠️ Errore impostazione webhook: {e}")
    
    return bot

def get_latest_chat_id():
    """Ritorna l'ultimo chat_id ricevuto"""
    if not pending_chat_ids:
        return None
    
    # Pulisci vecchi
    import time
    current_time = time.time()
    valid_ids = {cid: ts for cid, ts in pending_chat_ids.items() if current_time - ts < 600}
    
    # Ritorna il più recente
    if valid_ids:
        return max(valid_ids.keys(), key=lambda k: valid_ids[k])
    
    return None
