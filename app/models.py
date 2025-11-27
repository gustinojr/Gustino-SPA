from . import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    promo_code = db.Column(db.String(50))
    chat_id = db.Column(db.String(50), nullable=True)
    reservations = db.relationship("Reservation", back_populates="user")

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    service = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", back_populates="reservations")

class PromoCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True)
    redeemed = db.Column(db.Boolean, default=False)
    assigned_user_id = db.Column(db.Integer, nullable=True)
