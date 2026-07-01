"""Rutas de perfiles."""
from flask import Blueprint, render_template_string, redirect, url_for, request
from models import User, Post, Follow, Notification
from database import db
from utils import requires_login, get_current_user
import logging

profiles_bp = Blueprint("profiles", __name__, url_prefix="/profile")
logger = logging.getLogger(__name__)

@profiles_bp.route("/<username>")
@requires_login
def profile(username):
    """Muestra el perfil de un usuario."""
    user = User.query.filter_by(username=username).first_or_404()
    current_username, uid = get_current_user()
    
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).all()
    followers = Follow.query.filter_by(following_id=user.id).count()
    following = Follow.query.filter_by(follower_id=user.id).count()
    is_following = Follow.query.filter_by(follower_id=uid, following_id=user.id).first() is not None
    
    context = {
        "user": user,
        "posts": posts,
        "followers": followers,
        "following": following,
        "is_following": is_following,
        "is_own": username == current_username,
    }
    
    return render_template_string("Profile", **context)

@profiles_bp.route("/<username>/follow", methods=["POST"])
@requires_login
def follow(username):
    """Sigue o deja de seguir a un usuario."""
    current_username, uid = get_current_user()
    user = User.query.filter_by(username=username).first_or_404()
    
    if user.id == uid:
        return redirect(request.referrer or url_for("profiles.profile", username=username))
    
    follow = Follow.query.filter_by(follower_id=uid, following_id=user.id).first()
    
    if follow:
        db.session.delete(follow)
        db.session.commit()
    else:
        follow = Follow(follower_id=uid, following_id=user.id)
        db.session.add(follow)
        
        # Crear notificación
        notif = Notification(
            user_id=user.id,
            from_user_id=uid,
            type="follow"
        )
        db.session.add(notif)
        db.session.commit()
        logger.info(f"User {current_username} followed {username}")
    
    return redirect(request.referrer or url_for("profiles.profile", username=username))

@profiles_bp.route("/me")
@requires_login
def me():
    """Redirige al perfil del usuario actual."""
    username, _ = get_current_user()
    return redirect(url_for("profiles.profile", username=username))
