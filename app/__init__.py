# app/__init__.py
from flask import Flask
from .bot import bp as bot_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(bot_bp)
    return app
