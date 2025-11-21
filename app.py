import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To, Header

# Optional Sentry integration
SENTRY_DSN = os.environ.get("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.0)

# ------------------------
# Flask app setup
# ------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# ------------------------
# Logging (file + optional console)
# ------------------------
LOG_PATH = os.environ.get("LOG_PATH", "app.log")
handler = RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
app.logger.setLevel(logging.INFO)
app.logger.addHandler(handler)
# also log to stdout for container logs
console = logging.StreamHandler()
console.setFormatter(formatter)
console.setLevel(logging.INFO)
app.logger.addHandler(console)

app.logger.info("Starting Gustino's SPA app")
app.logger.debug("DEBUG MODE ACTIVE")
app.logger.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)
console.setLevel(logging.DEBUG)

# ------------------------
# Database setup
# ------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/gustino"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------------
# SendGrid settings
# ------------------------
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
TEMPLATE_BOOKING_ID = os.environ.get("TEMPLATE_BOOKING_ID")  # d-...
TEMPLATE_PRIZE_ID = os.environ.get("TEMPLATE_PRIZE_ID")      # d-...
TEMPLATE_OWNER_ID = os.environ.get("TEMPLATE_OWNER_ID")      # optional
DEFAULT_FROM_EMAIL = os.environ.get("FROM_EMAIL", "info@gustinospa.it")
DEFAULT_FROM_NAME = os.environ.get("FROM_NAME", "Gustino's SPA")
OWNER_NOTIFICATION_EMAIL = os.environ.get("OWNER_EMAIL", "gustinosspa@gmail.com")
UNSUBSCRIBE_EMAIL = os.environ.get("UNSUBSCRIBE_EMAIL", "unsubscribe@gustinospa.it")

print("SENDGRID_API_KEY:", os.environ.get("SENDGRID_API_KEY"))

app.logger.debug("Loaded environment:", extra={
    "SENDGRID_KEY": bool(SENDGRID_API_KEY),
    "TEMPLATE_BOOKING_ID": TEMPLATE_BOOKING_ID,
    "TEMPLATE_PRIZE_ID": TEMPLATE_PRIZE_ID,
    "TEMPLATE_OWNER_ID": TEMPLATE_OWNER_ID,
    "FROM_EMAIL": DEFAULT_FROM_EMAIL,
    "OWNER_EMAIL": OWNER_NOTIFICATION_EMAIL
})
# ------------------------
# Helper: send email via SendGrid (dynamic templates + fallback)
# ------------------------
def send_email(to_email, dynamic_payload: dict, email_type="booking"):
    """
    Send email using SendGrid Dynamic Templates, with extended debug logging.
    """

    app.logger.debug("send_email() called", extra={
        "to": to_email,
        "email_type": email_type,
        "payload": dynamic_payload
    })

    print("📨 EMAIL DEBUG:",
          "to:", to_email,
          "type:", email_type,
          "payload:", json.dumps(dynamic_payload, ensure_ascii=False))
    
    if not SENDGRID_API_KEY:
        app.logger.error("SENDGRID_API_KEY not configured. Email NOT sent.")
        return False

    sg = SendGridAPIClient(SENDGRID_API_KEY)

    # Choose the right template
    if email_type == "booking":
        template_id = TEMPLATE_BOOKING_ID
    elif email_type == "prize":
        template_id = TEMPLATE_PRIZE_ID
    elif email_type == "owner_notification":
        template_id = TEMPLATE_OWNER_ID
    else:
        template_id = None

    app.logger.debug("Resolved template ID", extra={
        "email_type": email_type,
        "template_id": template_id
    })

    # Build fallback subject & content
    if email_type == "booking":
        subject = "Conferma Prenotazione - Gustino's SPA"
        fallback_html = f"""
            <h3>Ciao {dynamic_payload.get('name','')},</h3>
            <p>Prenotazione confermata per il {dynamic_payload.get('date','')}.</p>
        """
        fallback_text = f"Ciao {dynamic_payload.get('name','')}, prenotazione confermata."
    elif email_type == "prize":
        subject = "Informazioni sul tuo premio - Gustino's SPA"
        fallback_html = f"""
            <h3>Ciao {dynamic_payload.get('name','')},</h3>
            <p>Hai vinto: {dynamic_payload.get('prize','Premio speciale')}</p>
        """
        fallback_text = f"Ciao {dynamic_payload.get('name','')}, hai vinto un premio."
    elif email_type == "owner_notification":
        subject = "Nuova prenotazione - Gustino's SPA"
        fallback_html = f"""
            <h3>Nuova prenotazione</h3>
            <p>Cliente: {dynamic_payload.get('name','')}</p>
        """
        fallback_text = "Nuova prenotazione"
    else:
        subject = "Notifica - Gustino's SPA"
        fallback_html = "<p>Notifica generica</p>"
        fallback_text = "Notifica generica"

    try:
        message = Mail(
            from_email=f"{DEFAULT_FROM_NAME} <{DEFAULT_FROM_EMAIL}>",
            to_emails=To(to_email),
            subject=subject
        )

        # Debug info inside headers
        message.add_header(Header("X-Debug-Email-Type", email_type))
        message.add_header(Header("X-Debug-To", to_email))
        message.add_header(Header("List-Unsubscribe", f"<mailto:{UNSUBSCRIBE_EMAIL}>"))

        message.reply_to = DEFAULT_FROM_EMAIL

        if template_id:
            message.template_id = template_id
            message.dynamic_template_data = dynamic_payload

            app.logger.debug("Sending SendGrid dynamic-template email", extra={
                "to": to_email,
                "template_id": template_id,
                "payload": dynamic_payload
            })
        else:
            message.html_content = fallback_html
            try:
                message.plain_text_content = fallback_text
            except:
                pass

            app.logger.warning("No template configured, using fallback email", extra={
                "email_type": email_type,
                "to": to_email
            })

        response = sg.send(message)

        app.logger.info("Email sent successfully", extra={
            "to": to_email,
            "status": getattr(response, "status_code", None),
            "template_id": template_id
        })

        return True

    except Exception as e:
        app.logger.exception("Failed to send email", extra={
            "to": to_email,
            "email_type": email_type,
            "payload": dynamic_payload
        })
        return False

# ------------------------
# Database Models
# ------------------------
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)

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
# Routes (unchanged features, with added dynamic fields)
# ------------------------
@app.route("/reset-db")
def reset_db():
    db.drop_all()
    db.create_all()
    for code in DEFAULT_PROMO_CODES:
        db.session.add(PromoCode(code=code))
    db.session.commit()
    app.logger.info("Database reset requested")
    return "✅ Database reset and promo codes reloaded."


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

    if promo.redeemed:
        return redirect(url_for("booking", user_id=promo.user.id))

    if promo.code == "20121997":
        return redirect(url_for("special_prize", promo_id=promo.id))
    else:
        return redirect(url_for("register", promo_id=promo.id))


@app.route("/register/<int:promo_id>", methods=["GET", "POST"])
def register(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")

        if not name or not email:
            flash("Nome ed email sono obbligatori.")
            return redirect(url_for("register", promo_id=promo.id))

        # Avoid duplicate by email
        existing = User.query.filter_by(email=email).first()
        if existing:
            user = existing
            user.name = name  # update name if changed
            db.session.commit()
        else:
            user = User(name=name, email=email)
            db.session.add(user)
            db.session.commit()

        promo.user_id = user.id
        promo.redeemed = True
        db.session.commit()

        app.logger.info("User registered", extra={"user_id": user.id, "email": user.email})
        flash("Registrazione completata! Procedi con la prenotazione.")
        return redirect(url_for("booking", user_id=user.id))

    return render_template("register.html", promo=promo)


@app.route("/special/<int:promo_id>", methods=["GET", "POST"])
def special_prize(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")

        if not name or not email:
            flash("Nome ed email sono obbligatori.")
            return redirect(url_for("special_prize", promo_id=promo.id))

        # create or reuse user
        existing = User.query.filter_by(email=email).first()
        if existing:
            user = existing
            user.name = name
            db.session.commit()
        else:
            user = User(name=name, email=email)
            db.session.add(user)
            db.session.commit()

        promo.user_id = user.id
        promo.redeemed = True
        db.session.commit()

        # Decide prize text (you can customize per promo)
        prize_text = "Premio Speciale VIP" if promo.code == "20121997" else "Premio Gustino's SPA"

        # Send template email with prize info
        payload = {
            "name": user.name,
            "prize": prize_text
        }
        sent = send_email(user.email, payload, email_type="prize")

        app.logger.info("Special prize registered", extra={"user_id": user.id, "email": user.email, "sent": sent})
        flash("Premio speciale registrato! Controlla la tua email 📩")
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
        # read optional 'service' field from form; default to generic
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

        # Prepare dynamic payload for template
        payload = {
            "name": user.name,
            "date": date.strftime("%Y-%m-%d"),
            "start_time": start_time.strftime("%H:%M"),
            "end_time": end_time.strftime("%H:%M"),
            "service": service
        }

        sent_user = send_email(user.email, payload, email_type="booking")
        sent_owner = send_email(OWNER_NOTIFICATION_EMAIL, payload, email_type="owner_notification")

        app.logger.info("Reservation created", extra={"user_id": user.id, "reservation_id": reservation.id, "sent_user": sent_user, "sent_owner": sent_owner})
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
        reservations=reservations
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0",
            port=int(os.environ.get("PORT", 5000)),
            debug=bool(os.environ.get("DEBUG", True)))
