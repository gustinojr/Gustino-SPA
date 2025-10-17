from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import resend

# ------------------------
# App setup
# ------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecret")

# ------------------------
# Database
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

# ------------------------
# Funzione per invio email
# ------------------------
def invia_email(to, nome, data=None, ora_inizio=None, ora_fine=None, tipo="prenotazione"):
    sender = os.environ.get("MAIL_DEFAULT_SENDER", "booking@gustinospa.dpdns.org")  # dominio verificato
    copia_gustino = os.environ.get("GUSTINO_COPY_EMAIL", "gustinosspa@gmail.com")
    destinatari = [to]
    if copia_gustino not in destinatari:
        destinatari.append(copia_gustino)

    if tipo == "prenotazione":
        subject = f"Conferma prenotazione Gustino SPA - {data}"
        html_body = f"""
        <html><body>
        <p>Ciao {nome},</p>
        <p>Grazie per aver prenotato presso <strong>Gustino SPA</strong>!</p>
        <p>La tua prenotazione è confermata per il <strong>{data}</strong> dalle <strong>{ora_inizio}</strong> alle <strong>{ora_fine}</strong>.</p>
        <p>Per qualsiasi domanda, rispondi a questa email o visita il nostro sito: <a href="https://gustinospa.dpdns.org">gustinospa.dpdns.org</a>.</p>
        <p>Un saluto,<br>Il team di Gustino SPA</p>
        </body></html>
        """
        text_body = f"""
        Ciao {nome},

        Grazie per aver prenotato presso Gustino SPA!
        La tua prenotazione è confermata per il {data} dalle {ora_inizio} alle {ora_fine}.

        Per qualsiasi domanda, rispondi a questa email o visita https://gustinospa.dpdns.org.

        Un saluto,
        Il team di Gustino SPA
        """
    elif tipo == "premio":
        subject = "🎁 Congratulazioni! Premio speciale Gustino SPA"
        html_body = f"""
        <html><body>
        <p>Ciao {nome},</p>
        <p>Congratulazioni! Hai ricevuto il tuo premio speciale presso <strong>Gustino SPA</strong> 🎁</p>
        <p>Goditi una cena personalizzata cucinata da Gustino in persona!</p>
        <p>Valido dal <strong>20/12/2025</strong> al <strong>06/01/2026</strong>.</p>
        <p>Per maggiori informazioni visita <a href="https://gustinospa.dpdns.org">gustinospa.dpdns.org</a>.</p>
        <p>Un saluto,<br>Il team di Gustino SPA</p>
        </body></html>
        """
        text_body = f"""
        Ciao {nome},

        Congratulazioni! Hai ricevuto il tuo premio speciale presso Gustino SPA 🎁
        Goditi una cena personalizzata cucinata da Gustino in persona!
        Valido dal 20/12/2025 al 06/01/2026.

        Per maggiori informazioni visita https://gustinospa.dpdns.org.

        Un saluto,
        Il team di Gustino SPA
        """
    else:
        raise ValueError("Tipo email non valido")

    try:
        resend.Emails.send({
            "from": sender,
            "to": destinatari,
            "subject": subject,
            "html": html_body,
            "text": text_body
        })
        print(f"✅ Email inviata a {to} con copia a {copia_gustino}")
        return True
    except Exception as e:
        print(f"❌ Email fallita: {e}")
        return False

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
@app.route("/reset-db")
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
        entered_code = request.form.get("code", "").strip()
        promo = PromoCode.query.filter_by(code=entered_code).first()
        if not promo:
            flash("Codice non valido")
            return redirect(url_for("index"))
        if promo.redeemed:
            return redirect(url_for("booking", user_id=promo.user.id))
        return redirect(url_for("special_prize" if promo.code=="20121997" else "register", promo_id=promo.id))
    return render_template("index.html")

@app.route("/register/<int:promo_id>", methods=["GET","POST"])
def register(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)
    if request.method=="POST":
        name = request.form.get("name")
        email = request.form.get("email")
        if not name or not email:
            flash("Nome ed email obbligatori")
            return redirect(url_for("register", promo_id=promo.id))
        user = User(name=name,email=email)
        db.session.add(user)
        db.session.commit()
        promo.user_id = user.id
        promo.redeemed = True
        db.session.commit()
        flash("Registrazione completata! Procedi con la prenotazione.")
        return redirect(url_for("booking", user_id=user.id))
    return render_template("register.html", promo=promo)

@app.route("/special/<int:promo_id>", methods=["GET","POST"])
def special_prize(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)
    if request.method=="POST":
        name = request.form.get("name")
        email = request.form.get("email")
        if not name or not email:
            flash("Nome ed email obbligatori")
            return redirect(url_for("special_prize", promo_id=promo.id))
        user = User(name=name,email=email)
        db.session.add(user)
        db.session.commit()
        promo.user_id = user.id
        promo.redeemed = True
        db.session.commit()
        invia_email(email, nome, tipo="premio")
        flash("Premio speciale registrato! Controlla la tua email 📩")
        return redirect(url_for("booking", user_id=user.id))
    return render_template("special_prize.html", promo=promo)

@app.route("/booking/<int:user_id>", methods=["GET","POST"])
def booking(user_id):
    user = User.query.get_or_404(user_id)
    slot_start = datetime.strptime("11:00","%H:%M").time()
    slot_end = datetime.strptime("23:59","%H:%M").time()
    start_date = datetime.strptime("2025-12-20","%Y-%m-%d").date()
    end_date = datetime.strptime("2026-01-06","%Y-%m-%d").date()
    if request.method=="POST":
        date_str = request.form.get("date")
        start_str = request.form.get("start_time")
        end_str = request.form.get("end_time")
        date = datetime.strptime(date_str,"%Y-%m-%d").date()
        start_time = datetime.strptime(start_str,"%H:%M").time()
        end_time = datetime.strptime(end_str,"%H:%M").time()
        if date<start_date or date>end_date:
            flash(f"La data deve essere tra {start_date} e {end_date}")
            return redirect(url_for("booking", user_id=user.id))
        if start_time<slot_start or end_time>slot_end:
            flash("Orario deve essere tra 11:00 e 23:59")
            return redirect(url_for("booking", user_id=user.id))
        existing = Reservation.query.filter(
            Reservation.date==date,
            Reservation.start_time<end_time,
            Reservation.end_time>start_time
        ).first()
        if existing:
            flash("L'orario selezionato non è disponibile")
            return redirect(url_for("booking", user_id=user.id))
        resv = Reservation(user_id=user.id,date=date,start_time=start_time,end_time=end_time)
        db.session.add(resv)
        db.session.commit()
        invia_email(user.email,user.name,data=date,ora_inizio=start_time,ora_fine=end_time,tipo="prenotazione")
        flash("Prenotazione effettuata con successo")
        return redirect(url_for("booking", user_id=user.id))

    reservations = Reservation.query.filter(
        Reservation.date>=start_date,
        Reservation.date<=end_date
    ).all()
    booked_dates = {r.date for r in reservations}
    first_available = start_date
    while first_available in booked_dates and first_available<=end_date:
        first_available += timedelta(days=1)
    if first_available>end_date:
        first_available=None

    return render_template(
        "booking.html",
        user=user,
        slot_start=slot_start.strftime("%H:%M"),
        slot_end=slot_end.strftime("%H:%M"),
        first_available=first_available,
        start_date=start_date,
        end_date=end_date,
        reservations=reservations
    )

@app.template_filter('datetimeformat')
def datetimeformat(value, fmt='%H:%M'):
    return value.strftime(fmt)

@app.route("/success")
def success():
    return render_template("success.html")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=True)
