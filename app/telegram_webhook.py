import telebot
import os
from flask import request, jsonify
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Es: https://gustinospa.onrender.com

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set!")

bot = telebot.TeleBot(TOKEN)

# Cache temporanea per chat_id (invece di variabile globale)
pending_chat_ids = {}

def setup_webhook(app):
    """Configura il webhook per Telegram"""
    
    @app.route('/telegram-webhook', methods=['POST'])
    def webhook():
        if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return jsonify({"status": "ok"}), 200
        else:
            return jsonify({"error": "Invalid content type"}), 403
    
    # Handler per messaggi
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
    
    # Imposta il webhook
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/telegram-webhook"
        try:
            bot.remove_webhook()
            bot.set_webhook(url=webhook_url)
            print(f"✅ Webhook impostato: {webhook_url}")
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
