from flask import Blueprint, render_template, request, redirect, flash, current_app
from datetime import datetime
from app.models import Booking, User, db
from app.telegram_utils import tg_send

booking_bp = Blueprint('booking_bp', __name__)

@booking_bp.route('/booking/<int:user_id>', methods=['GET', 'POST'])
def booking(user_id):
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        date = request.form.get('date')
        time = request.form.get('time')

        booking = Booking(user_id=user.id, date=date, time=time)
        db.session.add(booking)
        db.session.commit()

        tg_send(user.chat_id, f"Prenotazione confermata: {date} {time}")
        tg_send(current_app.config['OWNER_CHAT_ID'], f"{user.name} ha prenotato: {date} {time}")

        flash("Prenotazione completata!")
        return redirect(f'/booking/{user.id}')
    
    return render_template('booking.html', user=user)
