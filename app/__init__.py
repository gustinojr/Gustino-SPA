from flask import Flask
from app.routes.home import home_bp
from app.routes.register import register_bp
from app.routes.booking import booking_bp
import os

def create_app():
    app = Flask(__name__)
    
    # Load config
    app.config.from_object('config.Config')
    app.secret_key = app.config.get('SECRET_KEY', 'supersecretkey')

    # Initialize database
    from app.models import db
    db.init_app(app)
    
    with app.app_context():
        db.create_all()

    # Register blueprints
    app.register_blueprint(home_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(booking_bp)

    # Determina se usare webhook o polling
    use_webhook = os.getenv("USE_WEBHOOK", "false").lower() == "true"
    
    if use_webhook:
        # Usa webhook (per Render/produzione)
        print("🌐 Modalità WEBHOOK attiva")
        try:
            from app.telegram_webhook import setup_webhook
            setup_webhook(app)
            print("✅ Webhook Telegram configurato")
        except Exception as e:
            print(f"⚠️ Errore configurazione webhook: {e}")
    else:
        # Usa polling (per sviluppo locale)
        print("🔄 Modalità POLLING attiva")
        try:
            import app.telegram_polling as telegram_polling
            telegram_polling.start_polling()
            print("✅ Bot Telegram avviato con polling")
        except Exception as e:
            print(f"⚠️ Errore avvio polling: {e}")

    return app
