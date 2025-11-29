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

    return app
