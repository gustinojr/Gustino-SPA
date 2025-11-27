from flask import Blueprint, render_template, request, redirect, url_for
from app.models import User, PromoCode, db


register_bp = Blueprint("register", __name__, url_prefix="/register")


@home_bp.route('/register/<promo_code>', methods=['GET', 'POST'])
def register(promo_code):
    temp_id = session.get('temp_id')
    user = User.query.filter_by(temp_identifier=temp_id).first()
    
    if request.method == 'POST':
        name = request.form.get('name')
        user.name = name
        db.session.commit()

        # invia messaggio Telegram
        tg_send(user.chat_id, f"Ciao {name}, registrazione completata!")
        tg_send(current_app.config['OWNER_CHAT_ID'], f"{name} si è registrato con promo {promo_code}")

        return redirect(f'/booking/{user.id}')

    return render_template('register.html', promo_code=promo_code)
