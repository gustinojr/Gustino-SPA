from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

db = SQLAlchemy()
load_dotenv()

    def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # registra i blueprint
    from app.routes.home import home_bp
    from app.routes.register import register_bp
    from app.routes.bot import bot_bp
    app.register_blueprint(home_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(bot_bp)

    # ⚠️ AVVIA IL POLLING SOLO ORA
    with app.app_context():
        from app.telegram_polling import start_polling
        start_polling(app)

    return app

