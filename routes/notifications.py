"""Rutas de notificaciones."""
from flask import Blueprint, render_template_string
from models import Notification
from database import db
from utils import requires_login, get_current_user

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")

@notifications_bp.route("/")
@requires_login
def notifications():
    """Muestra todas las notificaciones."""
    username, uid = get_current_user()
    
    notifs = Notification.query.filter_by(user_id=uid).order_by(Notification.created_at.desc()).limit(50).all()
    
    # Marcar como leídas
    Notification.query.filter_by(user_id=uid, is_read=False).update({"is_read": True})
    db.session.commit()
    
    return render_template_string("Notifications", notifications=notifs)
