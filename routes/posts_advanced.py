"""Rutas mejoradas de posts con reacciones, compartir y hashtags."""
from flask import Blueprint, request, redirect, url_for, jsonify
from models_advanced import Post, Like, Comment, Notification, Reaction, SavedPost, Hashtag
from database import db
from utils import requires_login, get_current_user, save_upload
from datetime import datetime
import logging
import re

posts_bp = Blueprint("posts", __name__, url_prefix="/posts")
logger = logging.getLogger(__name__)

# Emojis permitidos para reacciones
ALLOWED_REACTIONS = {"❤️": "love", "😂": "laugh", "😮": "wow", "😢": "sad", "😠": "angry", "👍": "like", "🔥": "fire"}

def extract_hashtags(text):
    """Extrae hashtags del texto."""
    return re.findall(r'#\w+', text)

def extract_mentions(text):
    """Extrae menciones del texto."""
    return re.findall(r'@\w+', text)

def process_hashtags(text):
    """Procesa y crea hashtags en la BD."""
    hashtags = extract_hashtags(text)
    for tag in hashtags:
        hashtag = Hashtag.query.filter_by(tag=tag.lower()).first()
        if hashtag:
            hashtag.usage_count += 1
        else:
            hashtag = Hashtag(tag=tag.lower())
            db.session.add(hashtag)
    db.session.commit()

def send_mention_notifications(post_id, text):
    """Envía notificaciones a usuarios mencionados."""
    from models_advanced import User
    mentions = extract_mentions(text)
    for mention in mentions:
        username = mention[1:]  # Remover @
        user = User.query.filter_by(username=username).first()
        if user:
            notif = Notification(
                user_id=user.id,
                from_user_id=get_current_user()[1],
                type="mention",
                post_id=post_id
            )
            db.session.add(notif)
    db.session.commit()

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
        db.session.flush()
        
        # Procesar hashtags
        process_hashtags(content)
        
        # Enviar notificaciones de menciones
        send_mention_notifications(post.id, content)
        
        db.session.commit()
        logger.info(f"Post created by user {username} (ID: {post.id})")
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
        logger.info(f"Like removed by user {username} on post {post_id}")
    else:
        like = Like(user_id=uid, post_id=post_id)
        db.session.add(like)
        
        # Crear notificación
        if post.user_id != uid:
            notif = Notification(
                user_id=post.user_id,
                from_user_id=uid,
                type="like",
                post_id=post_id
            )
            db.session.add(notif)
        db.session.commit()
        logger.info(f"Like added by user {username} on post {post_id}")
    
    return redirect(request.referrer or url_for("main.feed"))

@posts_bp.route("/<int:post_id>/react", methods=["POST"])
@requires_login
def react(post_id):
    """Agrega una reacción emoji a un post."""
    username, uid = get_current_user()
    data = request.get_json()
    emoji = data.get("emoji", "")
    
    if emoji not in ALLOWED_REACTIONS:
        return jsonify({"error": "Emoji no permitido"}), 400
    
    post = Post.query.get_or_404(post_id)
    reaction = Reaction.query.filter_by(user_id=uid, post_id=post_id, emoji=emoji).first()
    
    if reaction:
        db.session.delete(reaction)
    else:
        reaction = Reaction(user_id=uid, post_id=post_id, emoji=emoji)
        db.session.add(reaction)
        
        if post.user_id != uid:
            notif = Notification(
                user_id=post.user_id,
                from_user_id=uid,
                type="reaction",
                post_id=post_id
            )
            db.session.add(notif)
    
    db.session.commit()
    logger.info(f"User {username} reacted with {emoji} to post {post_id}")
    return jsonify({"success": True}), 200

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
    if post.user_id != uid:
        notif = Notification(
            user_id=post.user_id,
            from_user_id=uid,
            type="comment",
            post_id=post_id
        )
        db.session.add(notif)
    
    # Procesar menciones en comentario
    send_mention_notifications(post_id, content)
    
    db.session.commit()
    logger.info(f"User {username} commented on post {post_id}")
    
    return redirect(f"/posts/{post_id}")

@posts_bp.route("/<int:post_id>/save", methods=["POST"])
@requires_login
def save_post(post_id):
    """Guarda un post para verlo después."""
    username, uid = get_current_user()
    
    post = Post.query.get_or_404(post_id)
    saved = SavedPost.query.filter_by(user_id=uid, post_id=post_id).first()
    
    if saved:
        db.session.delete(saved)
        logger.info(f"Post {post_id} unsaved by {username}")
    else:
        saved = SavedPost(user_id=uid, post_id=post_id)
        db.session.add(saved)
        logger.info(f"Post {post_id} saved by {username}")
    
    db.session.commit()
    return redirect(request.referrer or url_for("main.feed"))

@posts_bp.route("/<int:post_id>/share", methods=["POST"])
def share_post(post_id):
    """Comparte un post (retweeting)."""
    username, uid = get_current_user()
    
    post = Post.query.get_or_404(post_id)
    
    # Crear un nuevo post que comparte el original
    share_content = f"Compartido de @{post.author.username}:\n\n{post.content}"
    shared_post = Post(user_id=uid, content=share_content, image_url=post.image_url)
    db.session.add(shared_post)
    
    # Notificar al autor original
    if post.user_id != uid:
        notif = Notification(
            user_id=post.user_id,
            from_user_id=uid,
            type="share",
            post_id=post_id
        )
        db.session.add(notif)
    
    db.session.commit()
    logger.info(f"User {username} shared post {post_id}")
    return redirect(url_for("main.feed"))

@posts_bp.route("/<int:post_id>/delete", methods=["POST"])
@requires_login
def delete(post_id):
    """Elimina un post."""
    username, uid = get_current_user()
    
    post = Post.query.get_or_404(post_id)
    
    # Solo el autor o admin puede eliminar
    if post.user_id != uid and not get_current_user()[0] == "gxbriel_exe":
        return redirect(url_for("main.feed"))
    
    db.session.delete(post)
    db.session.commit()
    logger.info(f"Post {post_id} deleted by {username}")
    return redirect(request.referrer or url_for("main.feed"))

@posts_bp.route("/search")
@requires_login
def search():
    """Busca posts por hashtag."""
    q = request.args.get("q", "").strip()
    
    if not q or len(q) < 2:
        return jsonify([])
    
    if q.startswith("#"):
        # Búsqueda de hashtag
        hashtag = Hashtag.query.filter_by(tag=q.lower()).first()
        if hashtag:
            posts = Post.query.filter(Post.content.ilike(f"%{q}%")).all()
        else:
            posts = []
    else:
        # Búsqueda general
        posts = Post.query.filter(Post.content.ilike(f"%{q}%")).all()
    
    return jsonify([{
        "id": p.id,
        "content": p.content[:100],
        "author": p.author.username,
        "created_at": p.created_at.isoformat()
    } for p in posts[:10]])

@posts_bp.route("/trending")
@requires_login
def trending():
    """Obtiene los hashtags trending."""
    trending_tags = Hashtag.query.order_by(Hashtag.usage_count.desc()).limit(10).all()
    
    return jsonify([{
        "tag": tag.tag,
        "usage_count": tag.usage_count
    } for tag in trending_tags])

@posts_bp.route("/saved")
@requires_login
def saved_posts():
    """Muestra posts guardados."""
    username, uid = get_current_user()
    
    saved = SavedPost.query.filter_by(user_id=uid).all()
    posts = [s.post for s in saved]
    
    return jsonify([{
        "id": p.id,
        "content": p.content,
        "author": p.author.username,
        "likes": len(p.likes),
        "created_at": p.created_at.isoformat()
    } for p in posts])
