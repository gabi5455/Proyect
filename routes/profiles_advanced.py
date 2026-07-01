"""Rutas avanzadas de perfiles con mejoras."""
from flask import Blueprint, render_template_string, redirect, url_for, request, jsonify
from models_advanced import User, Post, Follow, Notification, SavedPost
from database import db
from utils import requires_login, get_current_user, is_owner, get_avatar_color
from datetime import datetime
import logging

profiles_bp = Blueprint("profiles", __name__, url_prefix="/profile")
logger = logging.getLogger(__name__)

@profiles_bp.route("/<username>")
@requires_login
def profile(username):
    """Muestra el perfil mejorado de un usuario."""
    user = User.query.filter_by(username=username).first_or_404()
    current_username, uid = get_current_user()
    
    posts = Post.query.filter_by(user_id=user.id, is_deleted=False).order_by(Post.created_at.desc()).all()
    followers = Follow.query.filter_by(following_id=user.id).count()
    following = Follow.query.filter_by(follower_id=user.id).count()
    is_following = Follow.query.filter_by(follower_id=uid, following_id=user.id).first() is not None
    is_own = username == current_username
    
    context = {
        "user": user,
        "posts": posts,
        "followers": followers,
        "following": following,
        "is_following": is_following,
        "is_own": is_own,
        "is_banned": user.is_banned,
        "avatar_color": get_avatar_color(username),
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
        logger.info(f"User {current_username} unfollowed {username}")
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
        logger.info(f"User {current_username} followed {username}")
    
    db.session.commit()
    return redirect(request.referrer or url_for("profiles.profile", username=username))

@profiles_bp.route("/me")
@requires_login
def me():
    """Redirige al perfil del usuario actual."""
    username, _ = get_current_user()
    return redirect(url_for("profiles.profile", username=username))

@profiles_bp.route("/<username>/edit", methods=["GET", "POST"])
@requires_login
def edit(username):
    """Edita el perfil del usuario."""
    current_username, uid = get_current_user()
    user = User.query.filter_by(username=username).first_or_404()
    
    if user.id != uid and not is_owner(current_username):
        return redirect(url_for("profiles.profile", username=username))
    
    if request.method == "POST":
        user.display_name = request.form.get("display_name", "")[:100]
        user.bio = request.form.get("bio", "")[:160]
        user.updated_at = datetime.utcnow()
        db.session.commit()
        logger.info(f"Profile updated for {username}")
        return redirect(url_for("profiles.profile", username=username))
    
    return render_template_string("Edit profile", user=user)

@profiles_bp.route("/api/<username>/stats")
@requires_login
def api_stats(username):
    """Obtiene estadísticas del usuario via API."""
    user = User.query.filter_by(username=username).first_or_404()
    
    followers = Follow.query.filter_by(following_id=user.id).count()
    following = Follow.query.filter_by(follower_id=user.id).count()
    posts_count = Post.query.filter_by(user_id=user.id, is_deleted=False).count()
    
    return jsonify({
        "username": user.username,
        "display_name": user.display_name,
        "followers": followers,
        "following": following,
        "posts": posts_count,
        "created_at": user.created_at.isoformat(),
        "is_verified": user.email_verified,
    })

@profiles_bp.route("/api/<username>/posts")
@requires_login
def api_posts(username):
    """Obtiene posts del usuario via API."""
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get("page", 1, type=int)
    
    posts = Post.query.filter_by(user_id=user.id, is_deleted=False).paginate(page=page, per_page=20)
    
    return jsonify({
        "posts": [{
            "id": p.id,
            "content": p.content,
            "image_url": p.image_url,
            "likes": len(p.likes),
            "comments": len(p.comments),
            "created_at": p.created_at.isoformat()
        } for p in posts.items],
        "total": posts.total,
        "pages": posts.pages
    })
