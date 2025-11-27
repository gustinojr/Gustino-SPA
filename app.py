import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests

# =====================================================================
# FLASK CONFIG
# =====================================================================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")
app.config["SESSION_TYPE"] = "filesystem"

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
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID")  # your chat_id (string)
BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "gustinospa_bot")

TG_SEND_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage" if BOT_TOKEN else None

# =====================================================================
# TELEGRAM — SEND MESSAGE
# =====================================================================
def tg_send(chat_id, text):
    if not chat_id:
        app.logger.warning("⚠ Cannot send message: chat_id is None")
        return False
    if not TG_SEND_URL:
        app.logger.error("⚠ BOT_TOKEN not configured, cannot send Telegram messages.")
        return False
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(TG_SEND_URL, data=payload, timeout=10)
        app.logger.info(f"Telegram message sent to {chat_id} (status {r.status_code})")
        return r.ok
    except Exception as e:
        app.logger.error(f"Telegram send ERROR: {e}")
        return False
TG_GET_UPDATES_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates" if BOT_TOKEN else None

def tg_poll_for_chat_id(promo_code):
    """
    Poll Telegram getUpdates looking for a /start <promo> message.
    Returns chat_id if found, else None.
    """
    if not TG_GET_UPDATES_URL:
        app.logger.error("Polling skipped: BOT_TOKEN missing.")
        return None

    try:
        r = requests.get(TG_GET_UPDATES_URL, timeout=10)
        data = r.json()

        if "result" not in data:
            return None

        for update in data["result"]:
            msg = update.get("message")
            if not msg:
                continue

            chat_id = str(msg["chat"]["id"])
            text = msg.get("text", "")

            # match: /start GUSTINO2025
            if text.startswith("/start"):
                received_promo = text.replace("/start", "").strip()

                if received_promo == promo_code:
                    app.logger.info(f"Polling: found chat_id {chat_id} for promo {promo_code}")
                    return chat_id

        return None

    except Exception as e:
        app.logger.error(f"Telegram polling ERROR: {e}")
        return None

# =====================================================================
# DATABASE MODELS (explicit __tablename__ to avoid mismatch)
# =====================================================================
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    promo_code = db.Column(db.String(50))
    chat_id = db.Column(db.String(50), nullable=True)
    reservations = db.relationship("Reservation", back_populates="user")
    promo_codes = db.relationship("PromoCode", back_populates="user")


class Reservation(db.Model):
    __tablename__ = "reservations"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    service = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = db.relationship("User", back_populates="reservations")


class PromoCode(db.Model):
    __tablename__ = "promo_codes"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True)
    redeemed = db.Column(db.Boolean, default=False)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user = db.relationship("User", back_populates="promo_codes", foreign_keys=[assigned_user_id])

# =====================================================================
# INIT DEFAULT PROMOS + ONE-TIME SAFE RESET
# =====================================================================
DEFAULT_PROMO_CODES = ["GUSTINO2025", "20121997", "VIP2025"]
INIT_LOCK = "/tmp/gustino_init.lock"  # file on container filesystem

with app.app_context():
    # If lock file not present, perform safe reset (drop_all -> create_all), then create lock.
    # This ensures DB schema always matches models on first run.
    try:
        if not os.path.exists(INIT_LOCK):
            app.logger.info("### FIRST EXECUTION: resetting/initializing database ###")
            # Drop and recreate tables according to current models
            db.drop_all()
            db.create_all()
            # Add default promo codes
            for code in DEFAULT_PROMO_CODES:
                if not PromoCode.query.filter_by(code=code).first():
                    db.session.add(PromoCode(code=code))
            db.session.commit()
            # Create lock file
            try:
                with open(INIT_LOCK, "w") as f:
                    f.write("initialized")
            except Exception as e:
                app.logger.warning(f"Could not create init lock file: {e}")
            app.logger.info("Database initialized and promo codes inserted.")
        else:
            # Lock exists: ensure that tables are created (no destructive action)
            db.create_all()
            app.logger.info("Database already initialized (init lock present).")
            # Ensure default promo codes exist (idempotent)
            for code in DEFAULT_PROMO_CODES:
                if not PromoCode.query.filter_by(code=code).first():
                    db.session.add(PromoCode(code=code))
            db.session.commit()
            app.logger.info("Promo codes ensured.")
    except Exception as e:
        app.logger.exception("Error during DB initialization: %s", e)
        # do not crash import — surface error and continue; app may still fail on DB ops

# =====================================================================
# TELEGRAM WEBHOOK ENDPOINT
# =====================================================================
@app.post("/telegramWebhook")
def telegram_webhook():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"ok": False, "error": "no json"}), 400

    if "message" not in data:
        return jsonify({"ok": True, "status": "ignored"})

    msg = data["message"]
    chat_id = str(msg["chat"]["id"])
    text = msg.get("text", "")

    # /start <PROMO>
    if text.startswith("/start"):
        try:
            promo = text.replace("/start", "").strip()
            if not promo:
                tg_send(chat_id, "Per favore invia un codice valido: /start <CODICE_PROMO>")
                return jsonify({"ok": True})

            # find promo row
            promo_row = PromoCode.query.filter_by(code=promo).first()
            if not promo_row:
                tg_send(chat_id, "❌ Codice inesistente.")
                return jsonify({"ok": True})

            # If a user already assigned to this promo, update its chat_id; else create user
            user = None
            if promo_row.assigned_user_id:
                user = User.query.get(promo_row.assigned_user_id)
                if user:
                    user.chat_id = chat_id
            else:
                # create a placeholder user (name will be requested on site)
                user = User(name="Utente", promo_code=promo, chat_id=chat_id)
                db.session.add(user)
                db.session.flush()  # get user.id

                promo_row.assigned_user_id = user.id

            promo_row.redeemed = True
            db.session.commit()

            tg_send(chat_id, "🎉 Benvenuto! Il tuo account è stato collegato con successo.\nTorna al sito e completa la registrazione/prenotazione.")
            return jsonify({"ok": True})
        except Exception as e:
            app.logger.exception("Webhook handling failed: %s", e)
            return jsonify({"ok": False, "error": str(e)}), 500

    # other messages can be handled here
    return jsonify({"ok": True, "status": "ignored"})

# =====================================================================
# ROUTES
# =====================================================================

@app.route("/reset-db")
def reset_db():
    # manual reset (admin). Use with caution.
    try:
        db.drop_all()
        db.create_all()
        for code in DEFAULT_PROMO_CODES:
            db.session.add(PromoCode(code=code))
        db.session.commit()
        # remove init lock so next start will treat as first-run if necessary
        try:
            if os.path.exists(INIT_LOCK):
                os.remove(INIT_LOCK)
        except Exception:
            pass
        app.logger.info("Database reset requested and completed.")
        return "✅ Database reset and promo codes reloaded."
    except Exception as e:
        app.logger.exception("Reset DB failed: %s", e)
        return f"Error: {e}", 500


@app.route("/", methods=["GET", "POST"])
def home():
    # The index page will show the Telegram "open bot" button when user has no chat_id
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        promo = PromoCode.query.filter_by(code=code).first()
        if not promo:
            flash("❌ Codice non valido.")
            return redirect(url_for("home"))

        # If promo already redeemed and has assigned user -> redirect to register (where name can be set)
        if promo.redeemed and promo.assigned_user_id:
            return redirect(url_for("register", promo=promo.code))
        return redirect(url_for("register", promo=promo.code))

    return render_template("index.html", bot_username=BOT_USERNAME)


@app.route("/register/<promo>", methods=["GET", "POST"])
def register(promo):
    promo_row = PromoCode.query.filter_by(code=promo).first_or_404()
    user = None
    if promo_row.assigned_user_id:
        user = User.query.get(promo_row.assigned_user_id)

    if request.method == "POST":
        name = request.form.get("name")
        if not name:
            flash("Nome obbligatorio.")
            return redirect(url_for("register", promo=promo))

        if user:
            user.name = name
        else:
            user = User(name=name, promo_code=promo)
            db.session.add(user)
            db.session.flush()
            promo_row.assigned_user_id = user.id

        promo_row.redeemed = True
        db.session.commit()
        return redirect(url_for("booking", user_id=user.id))
# AUTO-POLLING TO RETRIEVE CHAT_ID IF MISSING
if user and not user.chat_id:
    app.logger.warning(f"⚠ User {user.id} has no chat_id — polling Telegram...")

    polled_chat = tg_poll_for_chat_id(user.promo_code)

    if polled_chat:
        user.chat_id = polled_chat
        db.session.commit()
        flash("✅ Account Telegram collegato correttamente!")
    else:
        flash("⚠ Per completare la registrazione, apri il bot Telegram e premi START.")

    # On GET: show registration page. Template should check if user and user.chat_id exist to hide/show bot button.
    return render_template("registration.html", promo=promo, user=user, bot_username=BOT_USERNAME)


@app.route("/booking/<int:user_id>", methods=["GET", "POST"])
def booking(user_id):
    user = User.query.get_or_404(user_id)
# ensure chat_id exists
if not user.chat_id:
    app.logger.warning(f"⚠ User {user.id} entered booking but has NO chat_id")

    polled = tg_poll_for_chat_id(user.promo_code)
    if polled:
        user.chat_id = polled
        db.session.commit()
        flash("✅ Collegamento Telegram recuperato automaticamente!")
    else:
        flash("⚠ Devi prima collegare il tuo account tramite Telegram.")
        return redirect(url_for("register", promo=user.promo_code))

    if request.method == "POST":
        date = datetime.strptime(request.form.get("date"), "%Y-%m-%d").date()
        start_time = datetime.strptime(request.form.get("start_time"), "%H:%M").time()
        end_time = datetime.strptime(request.form.get("end_time"), "%H:%M").time()
        service = request.form.get("service") or "Servizio Gustino's SPA"

        reservation = Reservation(
            user_id=user.id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            service=service
        )
        db.session.add(reservation)
        db.session.commit()

        # send Telegram messages (user + owner)
        # User message
        if user.chat_id:
            tg_send(
                user.chat_id,
                f"""Ciao {user.name},

Grazie per aver prenotato presso <b>Gustino SPA</b>!
La tua prenotazione è confermata per il <b>{date.strftime('%d/%m/%Y')}</b>
dalle <b>{start_time.strftime('%H:%M')}</b> alle <b>{end_time.strftime('%H:%M')}</b>.

Un saluto,
Il team di Gustino SPA"""
            )
        else:
            app.logger.warning(f"User {user.id} has no chat_id; cannot send telegram message.")

        # Owner message
        if OWNER_CHAT_ID:
            tg_send(
                OWNER_CHAT_ID,
                f"📢 <b>Nuova prenotazione</b>\nUtente: {user.name}\nData: {date.strftime('%d/%m/%Y')}\nOrario: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}\nServizio: {service}"
            )

        flash("Prenotazione completata! Controlla Telegram 📩")
        return redirect(url_for("booking", user_id=user.id))

    return render_template("booking.html", user=user)

# =====================================================================
# RUN
# =====================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
