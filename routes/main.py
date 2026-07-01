"""Rutas principales."""
from flask import Blueprint, render_template_string
from models import User, Post, Notification, Message, Follow
from database import db
from utils import requires_login, get_current_user, get_avatar_color, escape_html, time_ago, is_owner
from templates.main_templates import FEED_TEMPLATE
import logging

main_bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)

@main_bp.route("/")
@requires_login
def feed():
    """Feed principal."""
    username, uid = get_current_user()
    
    # Obtener notificaciones y mensajes sin leer
    unread_notifs = Notification.query.filter_by(user_id=uid, is_read=False).count()
    unread_msgs = Message.query.filter_by(to_user_id=uid, is_read=False).count()
    
    # Obtener posts del usuario y usuarios que sigue
    posts = Post.query.filter(
        db.or_(
            Post.user_id == uid,
            Post.user_id.in_(db.session.query(Follow.following_id).filter_by(follower_id=uid))
        )
    ).order_by(Post.created_at.desc()).limit(40).all()
    
    # Usuarios sugeridos
    suggested = User.query.filter(
        User.id != uid,
        User.is_banned == False,
        ~User.id.in_(db.session.query(Follow.following_id).filter_by(follower_id=uid))
    ).order_by(db.func.random()).limit(4).all()
    
    context = {
        "posts": posts,
        "suggested": suggested,
        "username": username,
        "is_owner": is_owner(username),
        "unread_notifs": unread_notifs,
        "unread_msgs": unread_msgs,
        "get_avatar_color": get_avatar_color,
        "escape_html": escape_html,
        "time_ago": time_ago,
    }
    
    return render_template_string(FEED_TEMPLATE, **context)
