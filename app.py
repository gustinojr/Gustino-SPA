import os
from datetime import datetime, timedelta, time
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# --- Mail / Prize / Admin configuration from environment ---
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')  # your Gmail
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')  # app password
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')  # where reservations are CC'd to you
VALID_CODE = os.environ.get('VALID_CODE', 'GUSTINO2025')

mail = Mail(app)

# --- In-memory state (resets on dyno restart; OK for "static" demo) ---
booked = []  # list of {"date": "YYYY-MM-DD", "time": "HH:MM"}
first_redeem_done = False
customer_email = None

# --- Promo window: Dec 20 → Jan 6 (inclusive), any year ---
PROMO_START = (12, 20)  # (month, day)
PROMO_END = (1, 6)      # (month, day)
OPEN_TIME = time(11, 0) # 11:00
CLOSE_TIME = time(23, 59)


def is_within_promo_window(dt: datetime) -> bool:
    """
    Accept any date with month/day between Dec 20 and Jan 6 inclusive,
    spanning new year.
    """
    m, d = dt.month, dt.day
    # In Dec: allowed if day >= 20
    if m == 12 and d >= PROMO_START[1]:
        return True
    # In Jan: allowed if day <= 6
    if m == 1 and d <= PROMO_END[1]:
        return True
    return False


def is_time_allowed(t: time) -> bool:
    return OPEN_TIME <= t <= CLOSE_TIME


def is_at_least_6h_in_advance(slot_dt: datetime, now: datetime) -> bool:
    return slot_dt - now >= timedelta(hours=6)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        code = request.form.get("redeem_code", "").strip()
        if code == VALID_CODE:
            return redirect(url_for("prize"))
        flash("Invalid redeem code. Try again.")
    return render_template("index.html")


@app.route("/prize", methods=["GET", "POST"])
def prize():
    global first_redeem_done, customer_email, booked

    if request.method == "POST":
        # Redeem email form (one-time prize email)
        if "email" in request.form:
            customer_email = request.form.get("email", "").strip()
            if not customer_email:
                flash("Please enter a valid email address.")
                return redirect(url_for("prize"))

            if not first_redeem_done:
                try:
                    send_prize_email(customer_email)
                    first_redeem_done = True
                    return redirect(url_for("confirmation", email=customer_email))
                except Exception as e:
                    flash(f"Error sending prize email: {e}")
            else:
                flash("Prize already redeemed. You can now make reservations.")
            return redirect(url_for("prize"))

        # Booking form (requires customer_email set)
        if "booking_date" in request.form and "booking_time" in request.form:
            if not customer_email:
                flash("Please enter your email first to proceed.")
                return redirect(url_for("prize"))

            date_str = request.form.get("booking_date")
            time_str = request.form.get("booking_time")

            try:
                slot_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                slot_time = datetime.strptime(time_str, "%H:%M").time()
                slot_dt = datetime.combine(slot_date, slot_time)
                now = datetime.now()
            except ValueError:
                flash("Invalid date/time format.")
                return redirect(url_for("prize"))

            # Validate window (Dec 20 → Jan 6), time, and 6h rule
            if not is_within_promo_window(slot_dt):
                flash("Bookings are only available from December 20 to January 6.")
                return redirect(url_for("prize"))

            if not is_time_allowed(slot_time):
                flash("Bookings available from 11:00 to late night (23:59).")
                return redirect(url_for("prize"))

            if not is_at_least_6h_in_advance(slot_dt, now):
                flash("Reservations must be made at least 6 hours in advance.")
                return redirect(url_for("prize"))

            # "Static calendar": just append (no availability checks)
            booked.append({"date": date_str, "time": time_str})

            try:
                msg = Message("🎉 Congratulations from Gustino’s SPA",
                              recipients=[email])
                msg.body = "You have won a dinner for 2 persons in selected restaurants!"
                mail.send(msg)
            except Exception as e:
                print(f"Email sending failed: {e}")

