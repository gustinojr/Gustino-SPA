from flask import current_app
from .models import PromoCode
from . import db

def initialize_database():
    db.create_all()

    codes = current_app.config["DEFAULT_PROMO_CODES"]
    for code in codes:
        if not PromoCode.query.filter_by(code=code).first():
            db.session.add(PromoCode(code=code))

    db.session.commit()
