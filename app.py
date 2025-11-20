from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ------------------------
# Flask app setup
# ------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

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
# Gmail SMTP Email Function
# ------------------------
def send_email(to_email, user_name, email_type="booking"):
    """
    Send email using Gmail SMTP.
    Requires environment variables:
    - GMAIL_USER
    - GMAIL_PASS (App Password)
    """

    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_PASS")

    if not gmail_user or not gmail_pass:
        print("❌ Missing Gmail SMTP credentials")
        return

    # ----------------------------------------------------------------------
    # EMAIL CONTENTS BASED ON TYPE
    # ----------------------------------------------------------------------
    if email_type == "booking":
        subject = "Conferma Prenotazione - Gustino's SPA"
        text = f"""
Ciao {user_name},

La tua prenotazione presso Gustino's SPA è stata confermata.
Ti aspettiamo per un momento di relax.

A presto,
Lo staff di Gustino's SPA
"""
        html = f"""
<h3>Ciao {user_name},</h3>
<p>La tua prenotazione presso <strong>Gustino's SPA</strong> è stata confermata.</p>
<p>Ti aspettiamo per un momento di relax.</p>
<p style="font-size:12px;color:#666;">Email generata automaticamente.</p>
"""

    elif email_type == "prize":
        subject = "Informazioni sul tuo premio - Gustino's SPA"
        text = f"""
Ciao {user_name},

Hai ottenuto un premio da Gustino's SPA.
Ti contatteremo a breve con ulteriori dettagli.

Lo staff di Gustino's SPA
"""
        html = f"""
<h3>Ciao {user_name},</h3>
<p>Hai ottenuto un premio speciale da <strong>Gustino's SPA</strong>.</p>
<p>Ti ricontatteremo presto con ulteriori dettagli.</p>
"""

    elif email_type == "owner_notification":
        subject = "Nuova Prenotazione Ricevuta - Gustino's SPA"
        text = f"Nuova prenotazione effettuata da: {user_name}"
        html = f"""
<h3>Nuova prenotazione</h3>
<p><strong>Cliente:</strong> {user_name}</p>
"""

    else:
        subject = "Notifica - Gustino's SPA"
        text = f"Ciao {user_name},\nQuesta è una notifica automatica."
        html = f"<p>Ciao {user_name}, questa è una notifica automatica.</p>"

    # ----------------------------------------------------------------------
    # SMTP MESSAGE BUILDING
    # ----------------------------------------------------------------------
    msg = MIMEMultipart("alternative")
    msg["From"] = f"Gustino's SPA <{gmail_user}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    # ----------------------------------------------------------------------
    # SMTP SENDING
    # ----------------------------------------------------------------------
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, to_email, msg.as_string())
        server.quit()
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Email failed: {e}")

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

# ------------------------
# Routes
# ------------------------
@app.route("/reset-db")
def reset_db():
    db.drop_all()
    db.create_all()
    for code in DEFAULT_PROMO_CODES:
        db.session.add(PromoCode(code=code))
    db.session.commit()
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

        user = User(name=name, email=email)
        db.session.add(user)
        db.session.commit()

        promo.user_id = user.id
        promo.redeemed = True
        db.session.commit()

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

        user = User(name=name, email=email)
        db.session.add(user)
        db.session.commit()

        promo.user_id = user.id
        promo.redeemed = True
        db.session.commit()

        send_email(email, name, "prize")

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
        date_str = request.form.get("date")
        start_str = request.form.get("start_time")
        end_str = request.form.get("end_time")

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
            end_time=end_time
        )
        db.session.add(reservation)
        db.session.commit()

        send_email(user.email, user.name, "booking")
        send_email(os.environ.get("GMAIL_USER"), user.name, "owner_notification")

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

# ------------------------
# App Runner
# ------------------------
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )
