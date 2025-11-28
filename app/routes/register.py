from flask import Blueprint, session, jsonify

register_bp = Blueprint("register_bp", __name__)

@register_bp.route("/register/<promo_code>")
def register(promo_code):
    # Esempio di uso session
    temp_id = session.get('temp_id', None)
    return jsonify({
        "promo_code": promo_code,
        "temp_id": temp_id
    })
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
