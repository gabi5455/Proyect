"""Sistema de notificaciones avanzado."""
from flask import Blueprint, render_template_string, jsonify, request
from models_advanced import Notification, User, Post
from database import db
from utils import requires_login, get_current_user
from datetime import datetime
import logging

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")
logger = logging.getLogger(__name__)

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

@notifications_bp.route("/api/unread")
@requires_login
def api_unread():
    """Obtiene el número de notificaciones sin leer via API."""
    username, uid = get_current_user()
    
    unread_count = Notification.query.filter_by(user_id=uid, is_read=False).count()
    
    return jsonify({"unread_count": unread_count})

@notifications_bp.route("/api")
@requires_login
def api_notifications():
    """Obtiene notificaciones via API."""
    username, uid = get_current_user()
    page = request.args.get("page", 1, type=int)
    
    notifs = Notification.query.filter_by(user_id=uid).order_by(
        Notification.created_at.desc()
    ).paginate(page=page, per_page=20)
    
    return jsonify({
        "notifications": [{
            "id": n.id,
            "type": n.type,
            "from_user": {
                "username": n.from_user.username,
                "display_name": n.from_user.display_name
            },
            "post_id": n.post_id,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat()
        } for n in notifs.items],
        "total": notifs.total,
        "pages": notifs.pages
    })

@notifications_bp.route("/<int:notif_id>/read", methods=["POST"])
@requires_login
def mark_as_read(notif_id):
    """Marca una notificación como leída."""
    username, uid = get_current_user()
    
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id != uid:
        return {"error": "No autorizado"}, 403
    
    notif.is_read = True
    db.session.commit()
    logger.info(f"Notification {notif_id} marked as read by {username}")
    
    return {"success": True}

@notifications_bp.route("/clear", methods=["POST"])
@requires_login
def clear_all():
    """Limpia todas las notificaciones."""
    username, uid = get_current_user()
    
    Notification.query.filter_by(user_id=uid).delete()
    db.session.commit()
    logger.info(f"All notifications cleared for {username}")
    
    return {"success": True}
