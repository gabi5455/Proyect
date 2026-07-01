"""Rutas de publicaciones."""
from flask import Blueprint, request, redirect, url_for
from models import Post, Like, Comment, Notification
from database import db
from utils import requires_login, get_current_user, save_upload
import logging

posts_bp = Blueprint("posts", __name__, url_prefix="/posts")
logger = logging.getLogger(__name__)

@posts_bp.route("/create", methods=["GET", "POST"])
@requires_login
def create():
    """Crea una nueva publicación."""
    username, uid = get_current_user()
    
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        image_url = request.form.get("image_url", "").strip()
        
        if request.files.get("image_file"):
            image_url = save_upload(request.files["image_file"])
        
        if not content:
            return redirect(url_for("posts.create"))
        if len(content) > 500:
            return redirect(url_for("posts.create"))
        
        post = Post(user_id=uid, content=content, image_url=image_url)
        db.session.add(post)
        db.session.commit()
        logger.info(f"Post created by user {username}")
        return redirect(url_for("main.feed"))
    
    return "Create post page"

@posts_bp.route("/<int:post_id>/like", methods=["POST"])
@requires_login
def like(post_id):
    """Dale like a una publicación."""
    username, uid = get_current_user()
    
    post = Post.query.get_or_404(post_id)
    like = Like.query.filter_by(user_id=uid, post_id=post_id).first()
    
    if like:
        db.session.delete(like)
        db.session.commit()
    else:
        like = Like(user_id=uid, post_id=post_id)
        db.session.add(like)
        
        # Crear notificación
        notif = Notification(
            user_id=post.user_id,
            from_user_id=uid,
            type="like",
            post_id=post_id
        )
        db.session.add(notif)
        db.session.commit()
        logger.info(f"User {username} liked post {post_id}")
    
    return redirect(request.referrer or url_for("main.feed"))

@posts_bp.route("/<int:post_id>/comment", methods=["POST"])
@requires_login
def comment(post_id):
    """Agrega un comentario a una publicación."""
    username, uid = get_current_user()
    content = request.form.get("content", "").strip()
    
    if not content or len(content) > 300:
        return redirect(url_for("main.feed"))
    
    post = Post.query.get_or_404(post_id)
    
    comment = Comment(user_id=uid, post_id=post_id, content=content)
    db.session.add(comment)
    
    # Crear notificación
    notif = Notification(
        user_id=post.user_id,
        from_user_id=uid,
        type="comment",
        post_id=post_id
    )
    db.session.add(notif)
    db.session.commit()
    logger.info(f"User {username} commented on post {post_id}")
    
    return redirect(f"/posts/{post_id}")
