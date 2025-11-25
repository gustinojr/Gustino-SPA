import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests

# ------------------------
# Config Flask
# ------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# ------------------------
# Logging
# ------------------------
LOG_PATH = os.environ.get("LOG_PATH", "app.log")
handler = RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
app.logger.setLevel(logging.INFO)
app.logger.addHandler(handler)
console = logging.StreamHandler()
console.setFormatter(formatter)
console.setLevel(logging.INFO)
app.logger.addHandler(console)

# ------------------------
# DB setup
# ------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL",
    "sqlite:///gustino.db"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------------
# Telegram Bot
# ------------------------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID")  # Telegram chat_id del proprietario

def send_telegram_message(chat_id, tipo, nome, data=None, ora_inizio=None, ora_fine=None):
    if tipo == "prenotazione":
        text = f"""Ciao {nome},

Grazie per aver prenotato presso Gustino SPA!
La tua prenotazione è confermata per il {data} dalle {ora_inizio} alle {ora_fine}.

Per qualsiasi domanda, contatta Gustino.

Un saluto,
Il team di Gustino's SPA"""
    elif tipo == "premio":
        text = f"""Ciao {nome},

Congratulazioni! Hai ricevuto il tuo premio speciale presso Gustino SPA 🎁
Goditi una cena personalizzata cucinata da Gustino in persona!
Valido dal 20/12/2025 al 06/01/2026.

Per maggiori informazioni contatta Gustino.

Un saluto,
Il team di Gustino's SPA"""
    else:
        text = "Messaggio generico"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        r = requests.post(url, data=payload)
        app.logger.info(f"Telegram message sent to {chat_id} ({tipo})")
    except Exception as e:
        app.logger.error(f"Failed to send telegram message: {e}")

# ------------------------
# DB Models
# ------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    chat_id = db.Column(db.String(50), unique=True, nullable=True)
    reservations = db.relationship("Reservation", back_populates="user")
    promo_codes = db.relationship("PromoCode", back_populates="user")

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    details = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", back_populates="reservations")

class PromoCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True)
    redeemed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", back_populates="promo_codes")

# ------------------------
# DB Init
# ------------------------
DEFAULT_PROMO_CODES = ["GUSTINO2025", "20121997", "VIP2025"]
with app.app_context():
    db.create_all()
    for code in DEFAULT_PROMO_CODES:
        if not PromoCode.query.filter_by(code=code).first():
            db.session.add(PromoCode(code=code))
    db.session.commit()

# ------------------------
# Routes
# ------------------------
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        promo = PromoCode.query.filter_by(code=code).first()
        if not promo:
            flash("Codice non valido")
            return redirect(url_for("home"))
        if promo.redeemed and promo.user:
            return redirect(url_for("booking", user_id=promo.user.id))
        if promo.code == "20121997":  # special prize
            return redirect(url_for("special_prize", promo_id=promo.id))
        return redirect(url_for("register", promo_id=promo.id))
    return render_template("index.html")

@app.route("/register/<int:promo_id>", methods=["GET", "POST"])
def register(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)
    if request.method == "POST":
        name = request.form.get("name")
        chat_id = request.form.get("chat_id")  # viene ricevuto tramite bot
        user = User(name=name, chat_id=chat_id)
        db.session.add(user)
        db.session.commit()
        promo.user_id = user.id
        promo.redeemed = True
        db.session.commit()
        flash("Registrazione completata! Procedi con la prenotazione.")
        return redirect(url_for("booking", user_id=user.id))
    return render_template("registration.html", promo=promo)

@app.route("/special/<int:promo_id>", methods=["GET", "POST"])
def special_prize(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)
    if request.method == "POST":
        name = request.form.get("name")
        chat_id = request.form.get("chat_id")
        user = User(name=name, chat_id=chat_id)
        db.session.add(user)
        db.session.commit()
        promo.user_id = user.id
        promo.redeemed = True
        db.session.commit()
        send_telegram_message(chat_id, "premio", nome=name)
        flash("Premio speciale registrato! Controlla il tuo Telegram 📩")
        return redirect(url_for("booking", user_id=user.id))
    return render_template("special_prize.html", promo=promo)

@app.route("/booking/<int:user_id>", methods=["GET", "POST"])
def booking(user_id):
    user = User.query.get_or_404(user_id)
    start_date = datetime.strptime("2025-12-20", "%Y-%m-%d").date()
    end_date = datetime.strptime("2026-01-06", "%Y-%m-%d").date()
    slot_start = datetime.strptime("11:00", "%H:%M").time()
    slot_end = datetime.strptime("23:59", "%H:%M").time()

    if request.method == "POST":
        date = datetime.strptime(request.form.get("date"), "%Y-%m-%d").date()
        start_time = datetime.strptime(request.form.get("start_time"), "%H:%M").time()
        end_time = datetime.strptime(request.form.get("end_time"), "%H:%M").time()
        service = request.form.get("service", "Servizio Gustino's SPA")

        reservation = Reservation(
            user_id=user.id, date=date, start_time=start_time, end_time=end_time, details=service
        )
        db.session.add(reservation)
        db.session.commit()

        # invia messaggi Telegram a user e owner
        if user.chat_id:
            send_telegram_message(user.chat_id, "prenotazione", user.name,
                                  data=date.strftime("%d/%m/%Y"),
                                  ora_inizio=start_time.strftime("%H:%M"),
                                  ora_fine=end_time.strftime("%H:%M"))
        if OWNER_CHAT_ID:
            send_telegram_message(OWNER_CHAT_ID, "prenotazione", user.name,
                                  data=date.strftime("%d/%m/%Y"),
                                  ora_inizio=start_time.strftime("%H:%M"),
                                  ora_fine=end_time.strftime("%H:%M"))

        flash("Prenotazione effettuata con successo ✅")
        return redirect(url_for("booking", user_id=user.id))

    return render_template("booking.html", user=user, start_date=start_date,
                           end_date=end_date, slot_start=slot_start, slot_end=slot_end)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
