from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

db = SQLAlchemy()
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)

    # Register blueprints
    from app.routes.home import home_bp
    from app.routes.bot import bot_bp
    from app.routes.booking import booking_bp
    from app.routes.register import register_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(bot_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(register_bp)


    with app.app_context():
        db.create_all()

    return app
