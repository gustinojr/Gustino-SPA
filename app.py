import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests

# =====================================================================
# FLASK CONFIG
# =====================================================================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# =====================================================================
# LOGGING
# =====================================================================
LOG_PATH = os.environ.get("LOG_PATH", "app.log")
handler = RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)

app.logger.setLevel(logging.INFO)
app.logger.addHandler(handler)
console = logging.StreamHandler()
console.setFormatter(formatter)
console.setLevel(logging.INFO)
app.logger.addHandler(console)

# =====================================================================
# DB CONFIG
# =====================================================================
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///gustino.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# =====================================================================
# TELEGRAM CONFIG
# =====================================================================
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID")  # your chat_id
BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "gustinospa_bot")

TG_SEND_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


# =====================================================================
# TELEGRAM — SEND MESSAGE
# =====================================================================
def tg_send(chat_id, text):
    if not chat_id:
        app.logger.warning("⚠ Cannot send message: chat_id is None")
        return

    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(TG_SEND_URL, data=payload)
        app.logger.info(f"Telegram message sent to {chat_id}")
    except Exception as e:
        app.logger.error(f"Telegram send ERROR: {e}")


# =====================================================================
# DATABASE MODELS
# =====================================================================
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


# =====================================================================
# INIT DEFAULT PROMOS
# =====================================================================
DEFAULT_PROMO_CODES = ["GUSTINO2025", "20121997", "VIP2025"]

with app.app_context():
    db.create_all()
    for code in DEFAULT_PROMO_CODES:
        if not PromoCode.query.filter_by(code=code).first():
            db.session.add(PromoCode(code=code))
    db.session.commit()


# =====================================================================
# TELEGRAM WEBHOOK ENDPOINT
# =====================================================================
@app.post("/telegramWebhook")
def telegram_webhook():
    data = request.json

    if "message" not in data:
        return jsonify({"status": "ignored"})

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")

    # user sends: /start GUSTINO2025
    if text.startswith("/start"):
        try:
            promo = text.replace("/start", "").strip()
            if not promo:
                tg_send(chat_id, "Per favore invia un codice valido.")
                return "ok"

            promo_row = PromoCode.query.filter_by(code=promo).first()
            if not promo_row:
                tg_send(chat_id, "❌ Codice inesistente.")
                return "ok"

            # Assign chat_id to user
            user = User.query.filter_by(promo_code=promo).first()
            if user:
                user.chat_id = chat_id
            else:
                user = User(name="Utente", promo_code=promo, chat_id=chat_id)
                db.session.add(user)

            promo_row.redeemed = True
            promo_row.assigned_user_id = user.id
            db.session.commit()

            tg_send(chat_id, "🎉 Benvenuto! Il tuo account è stato collegato con successo.\nOra puoi tornare sul sito e completare la prenotazione!")

            return "ok"
        except Exception as e:
            app.logger.error(f"Webhook error: {e}")
            return "error", 500

    return "ignored"


# =====================================================================
# ROUTE: HOME
# =====================================================================
@app.route("/reset-db")
def reset_db():
    db.drop_all()
    db.create_all()
    for code in DEFAULT_PROMO_CODES:
        db.session.add(PromoCode(code=code))
    db.session.commit()
    app.logger.info("Database reset requested")
    return "✅ Database reset and promo codes reloaded."


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        promo = PromoCode.query.filter_by(code=code).first()

        if not promo:
            flash("❌ Codice non valido.")
            return redirect(url_for("home"))

        # If promo already redeemed → go to user page
        if promo.redeemed and promo.assigned_user_id:
            return redirect(url_for("register", promo=promo.code))

        return redirect(url_for("register", promo=promo.code))

    return render_template("index.html", bot_username=BOT_USERNAME)


# =====================================================================
# ROUTE: REGISTRAZIONE
# =====================================================================
@app.route("/register/<promo>", methods=["GET", "POST"])
def register(promo):
    promo_row = PromoCode.query.filter_by(code=promo).first_or_404()

    user = None
    if promo_row.assigned_user_id:
        user = User.query.get(promo_row.assigned_user_id)

    # user exists but no name saved → let them add their name
    if request.method == "POST":
        name = request.form.get("name")
        if user:
            user.name = name
        else:
            user = User(name=name, promo_code=promo)
            db.session.add(user)
            promo_row.assigned_user_id = user.id

        promo_row.redeemed = True
        db.session.commit()

        return redirect(url_for("booking", user_id=user.id))

    return render_template("registration.html",
                           promo=promo,
                           user=user,
                           bot_username=BOT_USERNAME)


# =====================================================================
# ROUTE: BOOKING
# =====================================================================
@app.route("/booking/<int:user_id>", methods=["GET", "POST"])
def booking(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        date = datetime.strptime(request.form.get("date"), "%Y-%m-%d").date()
        start_time = datetime.strptime(request.form.get("start_time"), "%H:%M").time()
        end_time = datetime.strptime(request.form.get("end_time"), "%H:%M").time()
        service = request.form.get("service")

        reservation = Reservation(
            user_id=user.id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            service=service
        )
        db.session.add(reservation)
        db.session.commit()

        # === SEND USER MESSAGE ===
        tg_send(
            user.chat_id,
            f"""Ciao {user.name},

Grazie per aver prenotato presso Gustino SPA!
La tua prenotazione è confermata per il {date.strftime('%d/%m/%Y')}
dalle {start_time.strftime('%H:%M')} alle {end_time.strftime('%H:%M')}.

A presto!"""
        )

        # === SEND OWNER MESSAGE ===
        if OWNER_CHAT_ID:
            tg_send(
                OWNER_CHAT_ID,
                f"📢 Nuova prenotazione!\nUtente: {user.name}\nData: {date}\nOrario: {start_time}-{end_time}"
            )

        flash("Prenotazione completata! Controlla Telegram 📩")
        return redirect(url_for("booking", user_id=user.id))

    return render_template("booking.html", user=user)


# =====================================================================
# RUN
# =====================================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

