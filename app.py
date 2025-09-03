import os
from datetime import datetime, time, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# PostgreSQL config for Render

DB_HOST = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_DATABASE_URI'] = f"{DB_HOST}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)

    # relationship with promo codes
    promo_codes = db.relationship("PromoCode", back_populates="user")

class PromoCode(db.Model):
    __tablename__ = "promo_codes"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    redeemed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # link back to user
    user = db.relationship("User", back_populates="promo_codes")
    
# Auto-create tables if they don't exist
with app.app_context():
    db.create_all()

# Constants for promo
PROMO_START = datetime(2025, 12, 20)
PROMO_END = datetime(2026, 1, 6)
BOOKING_START = time(11, 0)  # 11:00 am
BOOKING_END = time(23, 0)    # late night
BLOCK_HOURS = 2


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

from app import db, PromoCode

codes = ["20121997", "GUSTINO2025B", "GUSTINO2025C"]

for c in codes:
    db.session.add(PromoCode(code=c))
db.session.commit()
# Routes
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        serial = request.form.get("serial_code")
        user = User.query.filter_by(serial_code=serial).first()
        if not user:
            flash("Invalid serial code", "error")
            return redirect(url_for("index"))
        if not user.redeemed:
            user.redeemed = True
            db.session.commit()
            return redirect(url_for("prize", user_id=user.id))
        return redirect(url_for("booking", user_id=user.id))
    return render_template("index.html")

@app.route("/prize/<int:user_id>", methods=["GET"])
def prize(user_id):
    user = User.query.get(user_id)
    if not user:
        flash("User not found", "error")
        return redirect(url_for("index"))

    # Send congratulation email
    if not hasattr(user, 'prize_sent') or not getattr(user, 'prize_sent', False):
        try:
            send_email(user.email)
            user.prize_sent = True
            db.session.commit()
        except Exception as e:
            print(f"Error sending prize email: {e}")

    return render_template(
        "prize.html",
        user=user,
        promo_start=PROMO_START,
        promo_end=PROMO_END
    )

@app.route("/booking/<int:user_id>", methods=["GET", "POST"])
def booking(user_id):
    user = User.query.get(user_id)
    if not user:
        flash("User not found", "error")
        return redirect(url_for("index"))

    booked_slots = Booking.query.all()
    # Generate available time blocks per day
    available_dates = {}
    current_date = PROMO_START.date()
    while current_date <= PROMO_END.date():
        day_slots = []
        start = datetime.combine(current_date, BOOKING_START)
        end = datetime.combine(current_date, BOOKING_END) - timedelta(hours=BLOCK_HOURS)
        while start <= end:
            conflict = Booking.query.filter_by(date=current_date).filter(
                and_(Booking.start_time <= start.time(),
                     Booking.end_time > start.time())
            ).first()
            if not conflict:
                day_slots.append(start.time())
            start += timedelta(minutes=30)
        if day_slots:
            available_dates[current_date] = day_slots
        current_date += timedelta(days=1)

    if request.method == "POST":
        date_str = request.form.get("date")
        start_str = request.form.get("start_time")
        if not date_str or not start_str:
            flash("Please select date and time", "error")
            return redirect(url_for("booking", user_id=user.id))
        date_selected = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_selected = datetime.strptime(start_str, "%H:%M").time()
        end_selected = (datetime.combine(date_selected, start_selected) + timedelta(hours=BLOCK_HOURS)).time()

        # Check conflicts again
        conflict = Booking.query.filter_by(date=date_selected).filter(
            and_(Booking.start_time < end_selected,
                 Booking.end_time > start_selected)
        ).first()
        if conflict:
            flash("Selected slot is already booked", "error")
            return redirect(url_for("booking", user_id=user.id))

        booking = Booking(
            user_id=user.id,
            date=date_selected,
            start_time=start_selected,
            end_time=end_selected
        )
        db.session.add(booking)
        db.session.commit()
        flash("Booking confirmed!", "success")
        return redirect(url_for("booking", user_id=user.id))

    user_bookings = Booking.query.filter_by(user_id=user.id).all()
    return render_template("booking.html", user=user, available_dates=available_dates, user_bookings=user_bookings)

# Email function
def send_email(to_email):
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASS")  # Use App Password
    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = to_email
    msg['Subject'] = "Congratulations! You won a special prize"
    body = f"Dear customer,\n\nYou won a dinner for 2 during {PROMO_START.strftime('%b %d')} → {PROMO_END.strftime('%b %d')}.\n\nEnjoy!"
    msg.attach(MIMEText(body, 'plain'))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_pass)
        server.send_message(msg)

if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)
