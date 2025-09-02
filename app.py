import os
from datetime import datetime, timedelta, time
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mail import Mail, Message

# --- Flask setup ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# --- Mail setup ---
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

mail = Mail(app)

# --- Admin and redeem code ---
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
VALID_CODE = os.environ.get('VALID_CODE')

# --- Promo window (full datetime, cross-year) ---
PROMO_START = datetime(2025, 12, 20, 0, 0, 0)
PROMO_END = datetime(2026, 1, 6, 23, 59, 59)

# --- Allowed hours ---
OPEN_TIME = time(11, 0)
CLOSE_TIME = time(23, 59)

# --- In-memory state ---
booked = []
first_redeem_done = False
customer_email = None

# --- Helpers ---
def is_within_promo_window(dt: datetime):
    return PROMO_START <= dt <= PROMO_END

def is_time_allowed(t: time):
    return OPEN_TIME <= t <= CLOSE_TIME

def is_at_least_6h_in_advance(slot_dt: datetime, now: datetime):
    return slot_dt - now >= timedelta(hours=6)

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        code = request.form.get("redeem_code", "").strip()
        if code == VALID_CODE:
            return redirect(url_for("prize"))
        flash("❌ Invalid redeem code. Try again.")
    return render_template("index.html")

@app.route("/prize", methods=["GET", "POST"])
def prize():
    global first_redeem_done, customer_email, booked

    if request.method == "POST":
        # --- Redeem prize email ---
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
                flash("Prize already redeemed. You can now book sessions.")
            return redirect(url_for("prize"))

        # --- Booking form ---
        if "booking_date" in request.form and "booking_time" in request.form:
            if not customer_email:
                flash("Please enter your email first.")
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

            if not is_within_promo_window(slot_dt):
                flash("Bookings only allowed from Dec 20, 2025 to Jan 6, 2026.")
                return redirect(url_for("prize"))

            if not is_time_allowed(slot_time):
                flash("Booking time must be between 11:00 and 23:59.")
                return redirect(url_for("prize"))

            if not is_at_least_6h_in_advance(slot_dt, now):
                flash("Bookings must be made at least 6 hours in advance.")
                return redirect(url_for("prize"))

            booked.append({"date": date_str, "time": time_str})
            try:
                send_booking_emails(customer_email, date_str, time_str)
                flash(f"Reservation confirmed for {date_str} at {time_str}. Check your email!")
            except Exception as e:
                flash(f"Error sending reservation emails: {e}")
            return redirect(url_for("prize"))

    return render_template("prize.html", booked=booked, first_redeem_done=first_redeem_done)

@app.route("/confirmation")
def confirmation():
    email = request.args.get("email")
    return render_template("confirmation.html", email=email)

# --- Email functions ---
def send_prize_email(recipient: str):
    subject = "🎉 Congratulations from Gustino's SPA!"
    body = (
        "Dear Guest,\n\n"
        "Congratulations! You have won a Dinner for 2 persons in selected restaurants with Gustino.\n\n"
        "Offer valid Dec 20, 2025 → Jan 6, 2026.\n\n"
        "With love,\nGustino's SPA"
    )
    msg = Message(subject, recipients=[recipient], body=body)
    mail.send(msg)

def send_booking_emails(recipient: str, date_str: str, time_str: str):
    # Customer confirmation
    subject_customer = "✅ Your Massage Reservation is Confirmed"
    body_customer = f"Your massage is confirmed for {date_str} at {time_str}."
    mail.send(Message(subject_customer, recipients=[recipient], body=body_customer))

    # Admin notification
    if ADMIN_EMAIL:
        subject_admin = "📅 New Massage Booking"
        body_admin = f"Customer: {recipient}\nDate: {date_str}\nTime: {time_str}"
        mail.send(Message(subject_admin, recipients=[ADMIN_EMAIL], body=body_admin))

# --- Run ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
