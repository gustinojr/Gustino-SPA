from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecret")

# ------------------------
# Database
# ------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:password@localhost:5432/gustino")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------------
# Mail
# ------------------------
app.config.update(
    MAIL_SERVER=os.environ.get("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_PORT=int(os.environ.get("MAIL_PORT", 587)),
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=os.environ.get("MAIL_DEFAULT_SENDER", "gustinosspa@gmail.com"),
)
mail = Mail(app)

# ------------------------
# Models
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
@app.route('/reset-db')
def reset_db():
    db.drop_all()
    db.create_all()
    for code in DEFAULT_PROMO_CODES:
        db.session.add(PromoCode(code=code))
    db.session.commit()
    return "Database reset!"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        entered_code = request.form.get("code").strip()
        promo = PromoCode.query.filter_by(code=entered_code).first()
        if not promo:
            flash("Invalid promo code")
            return redirect(url_for("index"))

        if not promo.redeemed:
            return redirect(url_for("prize", promo_id=promo.id))
        else:
            user = promo.user
            return redirect(url_for("booking", user_id=user.id))
    return render_template("index.html")


@app.route("/prize/<int:promo_id>", methods=["GET", "POST"])
def prize(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        if not name or not email:
            flash("Name and email required")
            return redirect(url_for("prize", promo_id=promo.id))

        # Create user and bind promo
        user = User(name=name, email=email)
        db.session.add(user)
        db.session.commit()

        promo.user_id = user.id
        promo.redeemed = True
        db.session.commit()

        # Send special prize email
        if promo.code == "20121997":
            msg = Message(
                subject="Congratulazioni! Hai vinto un premio Speciale!",
                recipients=[email],
                body=f"Ciao {name},\n\nHai ricevuto il tuo premio speciale: Una cena cucinata da Gustino in persona presso la Gustino's SPA!\n\nPotrai usufruire di questo premio dal 20/12/2025 fino al 06/01/2026"
            )
            mail.send(msg)

        return redirect(url_for("booking", user_id=user.id))

    return render_template("prize.html", promo=promo)


@app.route("/booking/<int:user_id>", methods=["GET", "POST"])
def booking(user_id):
    user = User.query.get_or_404(user_id)

    # Define available time slots
    slot_start = datetime.strptime("11:00", "%H:%M").time()
    slot_end = datetime.strptime("19:00", "%H:%M").time()
    slot_length = timedelta(hours=2)

    today = datetime.today().date()
    reservations = Reservation.query.filter(Reservation.date >= today).all()
    booked_dates = {r.date for r in reservations}

    # First available date logic
    first_available = today
    while first_available in booked_dates:
        first_available += timedelta(days=1)

    if request.method == "POST":
        date_str = request.form.get("date")
        start_str = request.form.get("start_time")
        end_str = request.form.get("end_time")

        # Parse date
        date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Parse time (handle potential seconds)
        start_time = datetime.strptime(start_str[:5], "%H:%M").time()
        end_time = datetime.strptime(end_str[:5], "%H:%M").time()

        # Check for overlapping reservations
        overlapping = Reservation.query.filter(
            Reservation.date == date,
            Reservation.start_time < end_time,
            Reservation.end_time > start_time
        ).first()
        if overlapping:
            flash("Selected slot is not available")
            return redirect(url_for("booking", user_id=user.id))

        reservation = Reservation(
            user_id=user.id,
            date=date,
            start_time=start_time,
            end_time=end_time
        )
        db.session.add(reservation)
        db.session.commit()

        # Email to client
        client_msg = Message(
            subject="Prenotazione Confermata",
            recipients=[user.email],
            body=f"Ciao {user.name},\n\nla tua prenotazione è confermata per il {date} dalle {start_time} alle {end_time}."
        )
        mail.send(client_msg)

        # Email to owner
        owner_msg = Message(
            subject="New Reservation",
            recipients=[os.environ.get("OWNER_EMAIL", "owner@example.com")],
            body=f"Reservation by {user.name} ({user.email}) for {date} from {start_time} to {end_time}."
        )
        mail.send(owner_msg)

        flash("Reservation successful")
        return redirect(url_for("booking", user_id=user.id))

    return render_template(
        "booking.html",
        user=user,
        slot_start=slot_start,
        slot_end=slot_end,
        slot_length=slot_length,
        first_available=first_available,
        reservations=reservations
    )

@app.template_filter('datetimeformat')
def datetimeformat(value, fmt='%H:%M'):
    return value.strftime(fmt)

@app.route("/success")
def success():
    return render_template("success.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
