import os
import time
from datetime import datetime, date, time as dtime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, g
from flask_mail import Mail, Message
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, Time, ForeignKey, and_, select
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, scoped_session
from sqlalchemy.exc import IntegrityError

# --- Configuration ---
PROMO_START_DT = datetime(2025, 12, 20)
PROMO_END_DT = datetime(2026, 1, 6, 23, 59, 59)
OPEN_HOUR = 11
CLOSE_HOUR = 23  # last block starts at 21:00 (21-23). We'll create blocks until < CLOSE_HOUR

# Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24).hex())

# Mail (use Gmail App Password or SendGrid — set env vars accordingly)
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')  # your email
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')  # app password or sendgrid API (if using SendGrid set username "apikey")
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config.get('MAIL_USERNAME'))

mail = Mail(app)

# Database (Render provides DATABASE_URL)
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in environment. Set it to your Postgres connection (Render provides it).")

# SQLAlchemy setup
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
Base = declarative_base()

# --- Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(320), unique=True, nullable=False)
    prize_claimed = Column(Boolean, default=False)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())

    bookings = relationship("Booking", back_populates="user", cascade="all, delete-orphan")


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)           # booking day
    start = Column(Time, nullable=False)          # start time (HH:MM)
    end = Column(Time, nullable=False)            # end time
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())

    user = relationship("User", back_populates="bookings")


Base.metadata.create_all(bind=engine)

@app.route("/prize/<int:user_id>")
def prize(user_id):
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for("index"))

    return render_template(
        "prize.html",
        user=user,
        promo_start=PROMO_START,
        promo_end=PROMO_END
    )

# Utility to provide DB session per request
@app.before_request
def open_db_session():
    g.db = SessionLocal()

@app.teardown_request
def remove_db_session(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# Cache slug for assets (cache-busting)
@app.context_processor
def inject_cache_slug():
    return {'cache_slug': int(time.time())}


# Settings from env
VALID_CODE = os.environ.get("VALID_CODE", "GUSTINO2025")
PURGE_SLUG = os.environ.get("PURGE_SLUG", "superreset123")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", app.config.get('MAIL_USERNAME'))

# Helper: generate 2-hour blocks list for a given date
def generate_blocks_for_date(d: date):
    blocks = []
    hour = OPEN_HOUR
    while hour + 2 <= 24 and hour + 2 <= CLOSE_HOUR + 1:  # ensure 2-hour blocks within day and <= close hour
        start = dtime(hour, 0)
        end = dtime(hour + 2, 0)
        blocks.append((start, end))
        hour += 2
    return blocks

# Helper: check overlap in DB for a date and block
def is_block_free(db, day: date, start_time: dtime, end_time: dtime):
    # overlap if existing.start < end_time and existing.end > start_time
    q = db.query(Booking).filter(
        Booking.date == day,
        and_(Booking.start < end_time, Booking.end > start_time)
    )
    return not db.query(q.exists()).scalar()

# Determine default date logic (today if in promo, else promo start)
def default_booking_date():
    today = datetime.utcnow().date()
    promo_start = PROMO_START_DT.date()
    promo_end = PROMO_END_DT.date()
    if promo_start <= today <= promo_end:
        return today
    return promo_start

# Routes
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        code = request.form.get("redeem_code", "").strip()
        email = request.form.get("email", "").strip().lower()
        if not code or not email:
            flash("Please provide both code and email.")
            return redirect(url_for("index"))

        if code != VALID_CODE:
            flash("Invalid redeem code.")
            return redirect(url_for("index"))

        db = g.db
        user = db.query(User).filter_by(email=email).first()
        if not user:
            user = User(email=email, prize_claimed=False)
            db.add(user)
            db.commit()
            db.refresh(user)
            return redirect(url_for("prize", user_id=user.id))
        else:
            if not user.prize_claimed:
                return redirect(url_for("prize", user_id=user.id))
            else:
                return redirect(url_for("booking", user_id=user.id))
    return render_template("index.html")

@app.route("/prize/<int:user_id>", methods=["GET", "POST"])
def prize(user_id):
    db = g.db
    user = db.query(User).get(user_id)
    if not user:
        flash("User not found.")
        return redirect(url_for("index"))

    if request.method == "POST":
        # mark prize claimed and send prize email
        user.prize_claimed = True
        db.add(user)
        db.commit()

        try:
            subject = "🎉 Congratulations from Gustino's SPA!"
            body = (
                f"Dear Guest,\n\n"
                f"Congratulations! You have won a Dinner for 2 persons in selected restaurants with Gustino.\n\n"
                f"Offer valid {PROMO_START_DT.strftime('%b %d, %Y')} → {PROMO_END_DT.strftime('%b %d, %Y')}.\n\n"
                f"With love,\nGustino's SPA"
            )
            msg = Message(subject, recipients=[user.email], body=body)
            mail.send(msg)
        except Exception as e:
            app.logger.error("Error sending prize email: %s", e)
            flash("Prize claimed but email failed to send. We'll try to notify you.")

        return redirect(url_for("prize_success", user_id=user.id))

    return render_template("prize.html", user=user)

@app.route("/prize_success/<int:user_id>")
def prize_success(user_id):
    db = g.db
    user = db.query(User).get(user_id)
    if not user:
        return redirect(url_for("index"))
    return render_template("prize_success.html", user=user)

@app.route("/booking/<int:user_id>", methods=["GET", "POST"])
def booking(user_id):
    db = g.db
    user = db.query(User).get(user_id)
    if not user:
        flash("User not found.")
        return redirect(url_for("index"))

    promo_start = PROMO_START_DT.date()
    promo_end = PROMO_END_DT.date()
    today = datetime.utcnow().date()

    # build slots grouped by date (only for promo window, days >= today)
    slots_by_date = {}
    d = promo_start
    while d <= promo_end:
        if d >= today:
            blocks = generate_blocks_for_date(d)
            # filter free blocks
            available = []
            for start_t, end_t in blocks:
                if is_block_free(db, d, start_t, end_t):
                    available.append((start_t.strftime("%H:%M"), end_t.strftime("%H:%M")))
            if available:
                slots_by_date[d.isoformat()] = available
            else:
                # include empty list for completeness (so frontend can show disabled if needed)
                slots_by_date[d.isoformat()] = []
        d += timedelta(days=1)

    # default date = today if inside promo and has slots, otherwise first date with any slots, otherwise promo_start
    if today >= promo_start and today <= promo_end and slots_by_date.get(today.isoformat()):
        default_date = today.isoformat()
    else:
        # pick first date with slots, else promo_start
        default_date = next((dt for dt, s in slots_by_date.items() if s), promo_start.isoformat())

    if request.method == "POST":
        date_str = request.form.get("date")
        start_str = request.form.get("start")
        end_str = request.form.get("end")
        if not date_str or not start_str or not end_str:
            flash("Please select a date and a time slot.")
            return redirect(url_for("booking", user_id=user.id))

        # parse
        try:
            slot_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()
        except ValueError:
            flash("Invalid selection.")
            return redirect(url_for("booking", user_id=user.id))

        # ensure within promo and not past
        if slot_date < today or not (promo_start <= slot_date <= promo_end):
            flash("Selected date not in allowed booking window.")
            return redirect(url_for("booking", user_id=user.id))

        # check 6 hours in advance
        slot_dt = datetime.combine(slot_date, start_time)
        if slot_dt - datetime.utcnow() < timedelta(hours=6):
            flash("Bookings must be made at least 6 hours in advance.")
            return redirect(url_for("booking", user_id=user.id))

        # check available
        if not is_block_free(db, slot_date, start_time, end_time):
            flash("Selected time slot already booked. Choose another.")
            return redirect(url_for("booking", user_id=user.id))

        # persist booking
        new_booking = Booking(user_id=user.id, date=slot_date, start=start_time, end=end_time)
        db.add(new_booking)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            flash("Could not save booking. Try again.")
            return redirect(url_for("booking", user_id=user.id))

        # notify user + admin
        try:
            subj = "✅ Your Massage Reservation is Confirmed"
            body_user = f"Dear guest,\n\nYour massage reservation is confirmed for {date_str} from {start_str} to {end_str}.\n\nGustino's SPA"
            mail.send(Message(subj, recipients=[user.email], body=body_user))
        except Exception as e:
            app.logger.error("Failed to send customer booking email: %s", e)
            flash("Booking saved but confirmation email failed to send.")

        try:
            if ADMIN_EMAIL:
                subj_admin = "📅 New Massage Booking"
                body_admin = f"Customer: {user.email}\nDate: {date_str}\nTime: {start_str}-{end_str}"
                mail.send(Message(subj_admin, recipients=[ADMIN_EMAIL], body=body_admin))
        except Exception as e:
            app.logger.error("Failed to send admin booking email: %s", e)

        flash("Reservation confirmed!")
        return redirect(url_for("booking", user_id=user.id))

    # user bookings recap
    user_bookings = db.query(Booking).filter_by(user_id=user.id).order_by(Booking.date, Booking.start).all()

    return render_template("booking.html",
                           user=user,
                           slots_by_date=slots_by_date,
                           default_date=default_date,
                           user_bookings=user_bookings,
                           promo_start=promo_start,
                           promo_end=promo_end)

@app.route("/confirmation")
def confirmation():
    return render_template("confirmation.html")

# Purge endpoint (admin) — clears users and bookings
@app.route("/purge/<slug>", methods=["POST", "GET"])
def purge(slug):
    if slug != PURGE_SLUG:
        return "Not authorized", 403
    db = SessionLocal()
    try:
        db.query(Booking).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()
    return "Database purged", 200

# Run (for local debugging)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
