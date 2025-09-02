import os
from datetime import datetime, timedelta, time, date
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mail import Mail, Message

# --- Flask setup ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# --- Gmail Mail setup ---
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')  # Gmail App Password
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

mail = Mail(app)

# --- Admin and redeem code ---
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
VALID_CODE = os.environ.get('VALID_CODE', 'GUSTINO2025')

# --- Promo window ---
PROMO_START = datetime(2025, 12, 20, 0, 0)
PROMO_END = datetime(2026, 1, 6, 23, 59, 59)

# --- In-memory storage ---
booked = []  # {"date": "YYYY-MM-DD", "start": "HH:MM", "end": "HH:MM", "email": "user@email.com"}
first_redeem_done = False
customer_email = None

# --- Helpers ---
def generate_time_blocks():
    blocks = []
    start_hour = 11
    end_hour = 23
    while start_hour < end_hour:
        block_start = time(start_hour, 0)
        block_end = time(start_hour + 2, 0)
        blocks.append({
            "start": block_start.strftime("%H:%M"),
            "end": block_end.strftime("%H:%M")
        })
        start_hour += 2
    return blocks

def is_block_available(date_str, block):
    for b in booked:
        if b["date"] == date_str:
            booked_start = datetime.strptime(b["start"], "%H:%M").time()
            booked_end = datetime.strptime(b["end"], "%H:%M").time()
            block_start = datetime.strptime(block["start"], "%H:%M").time()
            block_end = datetime.strptime(block["end"], "%H:%M").time()
            # overlap check
            if (block_start < booked_end) and (block_end > booked_start):
                return False
    return True

def is_at_least_6h_in_advance(slot_dt: datetime, now: datetime):
    return slot_dt - now >= timedelta(hours=6)

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    global first_redeem_done
    if request.method == "POST":
        code = request.form.get("redeem_code", "").strip()
        if code != VALID_CODE:
            flash("❌ Invalid redeem code. Try again.")
            return redirect(url_for("index"))

        if not first_redeem_done:
            return redirect(url_for("prize"))
        else:
            return redirect(url_for("booking"))
    return render_template("index.html")


@app.route("/prize", methods=["GET", "POST"])
def prize():
    global first_redeem_done, customer_email
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            flash("Please enter a valid email.")
            return redirect(url_for("prize"))
        customer_email = email
        try:
            send_prize_email(customer_email)
            first_redeem_done = True
            return redirect(url_for("prize_success"))
        except Exception as e:
            flash(f"Error sending prize email: {e}")
            return redirect(url_for("prize"))
    return render_template("prize.html")


@app.route("/prize_success")
def prize_success():
    return render_template("prize_success.html")


@app.route("/booking", methods=["GET", "POST"])
def booking():
    global booked, customer_email
    if not customer_email:
        flash("Please redeem first to enter your email.")
        return redirect(url_for("index"))

    # Determine default date
    today = datetime.now().date()

    # Default to today if it's within the promo window, otherwise first promo day
    if PROMO_START.date() <= today <= PROMO_END.date():
        default_date = today
    else:
        default_date = PROMO_START.date()

    # Selected date from form or default
    date_selected_str = request.form.get("booking_date")
    if date_selected_str:
        date_selected = datetime.strptime(date_selected_str, "%Y-%m-%d").date()
    else:
        date_selected = default_date

    first_available_date = PROMO_START.date()
    last_available_date = PROMO_END.date()

    # Generate blocks and mark availability
    blocks = generate_time_blocks()
    for block in blocks:
        block["available"] = is_block_available(date_selected.strftime("%Y-%m-%d"), block)

    # Handle booking submission
    if request.method == "POST" and "block_start" in request.form:
        block_start = request.form.get("block_start")
        block_end = request.form.get("block_end")
        block = {"start": block_start, "end": block_end}

        if not is_block_available(date_selected.strftime("%Y-%m-%d"), block):
            flash("Selected time slot is already booked.")
            return redirect(url_for("booking"))

        slot_dt = datetime.strptime(f"{date_selected} {block_start}", "%Y-%m-%d %H:%M")
        if not is_at_least_6h_in_advance(slot_dt, datetime.now()):
            flash("Bookings must be at least 6 hours in advance.")
            return redirect(url_for("booking"))

        booked.append({
            "date": date_selected.strftime("%Y-%m-%d"),
            "start": block_start,
            "end": block_end,
            "email": customer_email
        })

        try:
            send_booking_emails(customer_email, date_selected.strftime("%Y-%m-%d"), block_start, block_end)
            flash(f"Reservation confirmed for {date_selected} {block_start}-{block_end}. Check your email!")
        except Exception as e:
            flash(f"Error sending booking emails: {e}")
        return redirect(url_for("booking"))

    # User booking recap
    user_bookings = [b for b in booked if b["email"] == customer_email]

    return render_template("booking.html",
                           date_selected=date_selected,
                           first_available_date=first_available_date,
                           last_available_date=last_available_date,
                           blocks=blocks,
                           user_bookings=user_bookings)


# --- Email functions ---
def send_prize_email(recipient):
    subject = "🎉 Congratulations from Gustino's SPA!"
    body = (
        f"Dear Guest,\n\n"
        f"Congratulations! You have won a Dinner for 2 persons in selected restaurants with Gustino.\n"
        f"Offer valid Dec 20, 2025 → Jan 6, 2026.\n\n"
        f"With love,\nGustino's SPA"
    )
    msg = Message(subject, recipients=[recipient], body=body)
    mail.send(msg)


def send_booking_emails(recipient, date_str, start, end):
    # Customer confirmation
    subject_customer = "✅ Your Massage Reservation is Confirmed"
    body_customer = f"Your massage is confirmed for {date_str} from {start} to {end}."
    mail.send(Message(subject_customer, recipients=[recipient], body=body_customer))

    # Admin notification
    if ADMIN_EMAIL:
        subject_admin = "📅 New Massage Booking"
        body_admin = f"Customer: {recipient}\nDate: {date_str}\nTime: {start}-{end}"
        mail.send(Message(subject_admin, recipients=[ADMIN_EMAIL], body=body_admin))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
