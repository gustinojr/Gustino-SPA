from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import resend

# ------------------------
# Flask app setup
# ------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# ------------------------
# Database setup
# ------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:password@localhost:5432/gustino"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------------
# Resend setup
# ------------------------
resend.api_key = os.environ.get("RESEND_API_KEY")

def send_email(to, subject, body, html=None):
    """Send an email using Resend with a CC to Gustino's main inbox."""
    sender = os.environ.get("MAIL_DEFAULT_SENDER", "booking@gustinospa.dpdns.org")
    gustino_copy = os.environ.get("GUSTINO_COPY_EMAIL", "gustinosspa@gmail.com")

    recipients = [to]
    if gustino_copy not in recipients:
        recipients.append(gustino_copy)

    try:
        params = {
            "from": f"Gustino's SPA <{sender}>",
            "to": recipients,
            "subject": subject,
            "html": html or f"<p>{body}</p>"
        }
        r = resend.Emails.send(params)
        print(f"✅ Email sent successfully to {recipients}: {r}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
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

# ------------------------
# Routes
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

        # Send email (Italian text)
        send_email(
            email,
            "🎁 Congratulazioni! Premio Speciale!",
            "",
            html=f"""
            <p>Ciao <strong>{name}</strong>,</p>
            <p>Hai ricevuto il tuo <b>premio speciale</b> 🎁:<br>
            Una cena cucinata da Gustino in persona presso la <b>Gustino's SPA</b>!</p>
            <p>Utilizzabile dal <b>20/12/2025</b> al <b>06/01/2026</b>.</p>
            """
        )

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

        # Send confirmation email (Italian)
        send_email(
            user.email,
            "Prenotazione Confermata",
            "",
            html=f"""
            <p>Ciao <strong>{user.name}</strong>,</p>
            <p>La tua prenotazione è confermata per il <b>{date}</b> dalle
            <b>{start_time}</b> alle <b>{end_time}</b>.</p>
            """
        )

        # Owner copy
        send_email(
            "gustinosspa@gmail.com",
            "Nuova Prenotazione Ricevuta",
            "",
            html=f"""
            <p>Nuova prenotazione da <strong>{user.name}</strong> ({user.email})</p>
            <p>Data: <b>{date}</b><br>Orario: <b>{start_time} - {end_time}</b></p>
            """
        )

        flash("Prenotazione effettuata con successo ✅")
        return redirect(url_for("booking", user_id=user.id))

    reservations = Reservation.query.all()
    return render_template("booking.html", user=user, reservations=reservations)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
