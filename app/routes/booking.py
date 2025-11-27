from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import User, Reservation
from app import db
from app.telegram import tg_send
from datetime import datetime
import os

booking_bp = Blueprint("booking", __name__, url_prefix="/booking")

@booking_bp.route("/<int:user_id>", methods=["GET", "POST"])
def booking(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        date = datetime.strptime(request.form.get("date"), "%Y-%m-%d").date()
        start_time = datetime.strptime(request.form.get("start_time"), "%H:%M").time()
        end_time = datetime.strptime(request.form.get("end_time"), "%H:%M").time()
        service = request.form.get("service")

        reservation = Reservation(
            user_id=user.id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            service=service
        )
        db.session.add(reservation)
        db.session.commit()

        # === Send Telegram to user ===
        tg_send(
            user.chat_id,
            f"Ciao {user.name}, la tua prenotazione è confermata per il {date} dalle {start_time} alle {end_time}."
        )

        # === Send Telegram to owner ===
        owner_chat = os.environ.get("OWNER_CHAT_ID")
        if owner_chat:
            tg_send(
                owner_chat,
                f"📢 Nuova prenotazione!\nUtente: {user.name}\nData: {date}\nOrario: {start_time}-{end_time}"
            )

        flash("Prenotazione completata! Controlla Telegram 📩")
        return redirect(url_for("booking.booking", user_id=user.id))

    return render_template("booking.html", user=user)
