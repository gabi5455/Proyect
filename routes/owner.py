"""Rutas del panel de administrador."""
from flask import Blueprint, render_template_string, request, redirect, url_for
from models import User, Post, Message, Comment, Like
from database import db
from utils import requires_login, requires_owner, get_current_user
import logging

owner_bp = Blueprint("owner", __name__, url_prefix="/owner")
logger = logging.getLogger(__name__)

@owner_bp.route("/")
@requires_login
@requires_owner
def panel():
    """Panel de administrador."""
    username, uid = get_current_user()
    
    users = User.query.all()
    total_posts = Post.query.count()
    total_likes = Like.query.count()
    total_comments = Comment.query.count()
    total_messages = Message.query.count()
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()
    
    context = {
        "users": users,
        "total_posts": total_posts,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_messages": total_messages,
        "recent_posts": recent_posts,
    }
    
    return render_template_string("Owner Panel", **context)

@owner_bp.route("/ban/<username>", methods=["POST"])
@requires_login
@requires_owner
def ban_user(username):
    """Banea o desbanea un usuario."""
    user = User.query.filter_by(username=username).first_or_404()
    user.is_banned = not user.is_banned
    db.session.commit()
    logger.info(f"User {username} ban status changed to {user.is_banned}")
    return redirect(request.referrer or url_for("owner.panel"))

@owner_bp.route("/delete-post/<int:post_id>", methods=["POST"])
@requires_login
@requires_owner
def delete_post(post_id):
    """Elimina un post."""
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    logger.info(f"Post {post_id} deleted")
    return redirect(request.referrer or url_for("owner.panel"))

@owner_bp.route("/delete-comment/<int:comment_id>", methods=["POST"])
@requires_login
@requires_owner
def delete_comment(comment_id):
    """Elimina un comentario."""
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    logger.info(f"Comment {comment_id} deleted")
    return redirect(request.referrer or url_for("main.feed"))
