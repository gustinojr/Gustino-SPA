from flask import Blueprint, render_template, request, redirect, flash, current_app
from datetime import datetime
from app.models import Booking, User, db
from app.telegram_utils import tg_send

booking_bp = Blueprint('booking_bp', __name__)

@booking_bp.route('/booking/<int:user_id>', methods=['GET', 'POST'])
def booking(user_id):
    user = User.query.get(user_id)
    
    if not user:
        flash("Utente non trovato.")
        return redirect('/')
    
    if request.method == 'POST':
        date = request.form.get('date')
        time = request.form.get('time')

        booking = Booking(user_id=user.id, date=date, time=time)
        db.session.add(booking)
        db.session.commit()

        # Invia messaggio all'utente (senza chat_id nel messaggio)
        user_message = (
            f"✅ Prenotazione confermata!\n\n"
            f"👤 {user.name}\n"
            f"📅 Data: {date}\n"
            f"🕐 Ora: {time}\n\n"
            f"Ci vediamo presto! ✨"
        )
        tg_send(user.chat_id, user_message)
        
        # Invia copia all'owner (con tutti i dettagli)
        owner_chat = current_app.config.get('OWNER_CHAT_ID')
        if owner_chat:
            owner_message = (
                f"🔔 Nuova prenotazione!\n\n"
                f"👤 Cliente: {user.name}\n"
                f"📅 {date} alle {time}\n"
                f"📞 Chat: {user.chat_id}"
            )
            tg_send(owner_chat, owner_message)

        flash("✅ Prenotazione completata! Riceverai una conferma su Telegram.")
        return redirect(f'/booking/{user.id}')
    
    return render_template('booking.html', user=user)
