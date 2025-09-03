from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# ✅ Database connection (Render provides DATABASE_URL env var)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///local.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# ---------- MODELS ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    promo_codes = db.relationship("PromoCode", backref="user", lazy=True)


class PromoCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    redeemed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)


# ---------- ROUTES ----------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        entered_code = request.form.get("code", "").strip()
        promo = PromoCode.query.filter_by(code=entered_code).first()

        if not promo:
            return render_template("index.html", error="❌ Invalid promo code.")

        if promo.redeemed:
            # already used → redirect to booking for that user
            return redirect(url_for("booking", user_id=promo.user_id))

        # valid & unused → show registration form
        return render_template("register.html", code=promo.code)

    return render_template("index.html")


@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name")
    email = request.form.get("email")
    code = request.form.get("code")

    promo = PromoCode.query.filter_by(code=code, redeemed=False).first()
    if not promo:
        return redirect(url_for("index"))

    # Create new user
    user = User(name=name, email=email)
    db.session.add(user)
    db.session.commit()

    # Assign promo to this user
    promo.user_id = user.id
    promo.redeemed = True
    db.session.commit()

    return redirect(url_for("prize", user_id=user.id))


@app.route("/prize/<int:user_id>")
def prize(user_id):
    user = User.query.get_or_404(user_id)
    promo_start = datetime(2025, 9, 1)
    promo_end = datetime(2025, 12, 31)
    return render_template(
        "prize.html",
        user=user,
        promo_start=promo_start,
        promo_end=promo_end,
    )


@app.route("/booking/<int:user_id>")
def booking(user_id):
    user = User.query.get_or_404(user_id)
    return render_template("booking.html", user=user)


# ---------- INIT ----------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)
