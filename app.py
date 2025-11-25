import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import requests

# ------------------------
# Flask app setup
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
app.logger.addHandler(handler)
console = logging.StreamHandler()
console.setFormatter(formatter)
app.logger.addHandler(console)
app.logger.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)
console.setLevel(logging.DEBUG)

# ------------------------
# Database setup
# ------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL",
    "sqlite:///gustino.db"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------------
# Telegram settings
# ------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8266193314:AAG-DzC00KGJvtXo25PkdvuJu2TpIBAaBhQ")
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ------------------------
# Database models
# ------------------------
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=True)
    chat_id = db.Column(db.String(50), unique=True, nullable=True)

    reservations = db.relationship("Reservation", back_populates="user")
    promo_codes = db.relationship("PromoCode", back_populates="user")


class Reservation(db.Model):
    __tablename__ = "reservations"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    details = db.Column(db.String(255))

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = db.relationship("User", back_populates="reservations")


class PromoCode(db.Model):
    __tablename__ = "promo_codes"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True)
    redeemed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = db.relationship("User", back_populates="promo_codes")


# ------------------------
# Initialize DB & Promo Codes
# ------------------------
DEFAULT_PROMO_CODES = ["GUSTINO2025", "20121997", "VIP2025"]

with app.app_context():
    db.create_all()
    for code in DEFAULT_PROMO_CODES:
        if not PromoCode.query.filter_by(code=code).first():
            db.session.add(PromoCode(code=code))
    db.session.commit()
    app.logger.info("Database initialized and promo codes ensured.")


# ------------------------
# Helper: send message via Telegram
# ------------------------
def send_telegram(chat_id, text):
    try:
        resp = requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        )
        if resp.status_code == 200:
            app.logger.info(f"Messaggio Telegram inviato a {chat_id}")
            return True
        else:
            app.logger.warning(f"Errore invio Telegram a {chat_id}: {resp.text}")
            return False
    except Exception as e:
        app.logger.exception("Exception durante invio Telegram")
        return False


# ------------------------
# Telegram webhook
# ------------------------
@app.route("/telegram_webhook", methods=["POST"])
def telegram_webhook():
    """Registra utenti al primo messaggio e invia istruzioni."""
    data = request.json
    if "message" in data:
        chat_id = str(data["message"]["chat"]["id"])
        first_name = data["message"]["from"].get("first_name", "Sconosciuto")

        user = User.query.filter_by(chat_id=chat_id).first()
        if not user:
            user = User(name=first_name, chat_id=chat_id)
            db.session.add(user)
            db.session.commit()
            send_telegram(chat_id, f"Ciao {first_name}! Benvenuto a Gustino SPA 🎁\n"
                                    "Inserisci il tuo codice promo nella pagina web per iniziare.")
        else:
            send_telegram(chat_id, f"Ciao {first_name}, bentornato! Inserisci il codice promo per procedere.")

    return jsonify({"ok": True})


# ------------------------
# Routes principali
# ------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/", methods=["POST"])
def handle_code():
    entered_code = request.form.get("code", "").strip()
    promo = PromoCode.query.filter_by(code=entered_code).first()

    if not promo:
        flash("Codice non valido.")
        return redirect(url_for("home"))

    # Se già riscattato, vai a booking
    if promo.redeemed and promo.user:
        return redirect(url_for("booking", user_id=promo.user.id))

    # Se speciale, vai a registrazione speciale (solo nome)
    if promo.code == "20121997":
        return redirect(url_for("special_prize", promo_id=promo.id))
    else:
        return redirect(url_for("register", promo_id=promo.id))


@app.route("/register/<int:promo_id>", methods=["GET", "POST"])
def register(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")  # rimane opzionale per codice normale

        if not name:
            flash("Il nome è obbligatorio.")
            return redirect(url_for("register", promo_id=promo.id))

        # Cerca utente via email o crea nuovo
        user = None
        if email:
            user = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email)
            db.session.add(user)
            db.session.commit()

        promo.user_id = user.id
        promo.redeemed = True
        db.session.commit()

        # Invia notifica Telegram all'owner
        if OWNER_CHAT_ID:
            send_telegram(OWNER_CHAT_ID, f"Nuovo utente registrato: {name}")

        flash("Registrazione completata! Procedi con la prenotazione.")
        return redirect(url_for("booking", user_id=user.id))

    return render_template("registration.html", promo=promo)


@app.route("/special/<int:promo_id>", methods=["GET", "POST"])
def special_prize(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)

    if request.method == "POST":
        name = request.form.get("name")
        if not name:
            flash("Il nome è obbligatorio.")
            return redirect(url_for("special_prize", promo_id=promo.id))

        user = User(name=name)
        db.session.add(user)
        db.session.commit()

        promo.user_id = user.id
        promo.redeemed = True
        db.session.commit()

        # Messaggio solo per premio speciale
        if user.chat_id:
            send_telegram(user.chat_id, f"Congratulazioni {name}! Hai vinto un premio speciale 🎉")

        if OWNER_CHAT_ID:
            send_telegram(OWNER_CHAT_ID, f"Premio speciale riscattato da {name}")

        flash("Premio speciale registrato! Ora puoi prenotare.")
        return redirect(url_for("booking", user_id=user.id))

    return render_template("special_prize.html", promo=promo)


@app.route("/booking/<int:user_id>", methods=["GET", "POST"])
def booking(user_id):
    user = User.query.get_or_404(user_id)

    slot_start = datetime.strptime("11:00", "%H:%M").time()
    slot_end = datetime.strptime("23:59", "%H:%M").time()
    start_date = datetime.strptime("2025-12-20", "%Y-%m-%d").date()
    end_date = datetime.strptime("2026-01-06", "%Y-%m-%d").date()

    if request.method == "POST":
        date_str = request.form.get("date")
        start_str = request.form.get("start_time")
        end_str = request.form.get("end_time")
        service = request.form.get("service", "Servizio Gustino's SPA")

        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()

        if date < start_date or date > end_date:
            flash(f"La data deve essere tra {start_date} e {end_date}.")
            return redirect(url_for("booking", user_id=user.id))

        existing = Reservation.query.filter(
            Reservation.date == date,
            Reservation.start_time < end_time,
            Reservation.end_time > start_time
        ).first()
        if existing:
            flash("L'orario selezionato non è disponibile.")
            return redirect(url_for("booking", user_id=user.id))

        reservation = Reservation(
            user_id=user.id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            details=service
        )
        db.session.add(reservation)
        db.session.commit()

        # Messaggi Telegram
        if user.chat_id:
            send_telegram(user.chat_id, f"Prenotazione confermata per {date} dalle {start_time} alle {end_time}")
        if OWNER_CHAT_ID:
            send_telegram(OWNER_CHAT_ID, f"Nuova prenotazione da {user.name} il {date} dalle {start_time} alle {end_time}")

        flash("Prenotazione effettuata con successo ✅")
        return redirect(url_for("booking", user_id=user.id))

    reservations = Reservation.query.filter(
        Reservation.date >= start_date,
        Reservation.date <= end_date
    ).all()
    booked_dates = {r.date for r in reservations}

    first_available = start_date
    while first_available in booked_dates and first_available <= end_date:
        first_available += timedelta(days=1)

    if first_available > end_date:
        first_available = None

    return render_template(
        "booking.html",
        user=user,
        start_date=start_date,
        end_date=end_date,
        first_available=first_available,
        reservations=user.reservations,
        slot_start=slot_start,
        slot_end=slot_end
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
