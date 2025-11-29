import os

class Config:
    # Security & App
    SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkey")
    ADMIN_KEY = os.environ.get("ADMIN_KEY", "admin123")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")

    # Database
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///gustino.db")
    # Render uses postgres:// but SQLAlchemy needs postgresql://
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Telegram
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "gustinospa_bot")
    OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID")
    OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "owner@example.com")

    # Promo codes
    DEFAULT_PROMO_CODES = os.environ.get("INITIAL_CODES", "GUSTINO2025,20121997,VIP2025").split(",")
    VALID_CODE = os.environ.get("promo", "20121997")

    # Logging
    LOG_PATH = os.environ.get("LOG_PATH", "app.log")
