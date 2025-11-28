from flask import Flask
from app.routes.home import home_bp
from app.routes.register import register_bp
from app.routes.bot import bot_bp
from app.telegram_bot import start_bot
import os

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

    # Registrazione Blueprint
    app.register_blueprint(home_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(bot_bp)

    # Avvio bot Telegram all'avvio dell'app
    start_polling()

    return app
