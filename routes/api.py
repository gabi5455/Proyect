"""API REST para consumir desde frontend o apps externas."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models_advanced import User, Post, Follow, Comment
from database import db
from datetime import datetime
import logging

api_bp = Blueprint("api", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)

# Users API

@api_bp.route("/users/<username>")
def get_user(username):
    """GET user profile info."""
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "bio": user.bio,
        "email_verified": user.email_verified,
        "created_at": user.created_at.isoformat(),
        "is_admin": user.is_admin,
        "followers": len(user.followers),
        "following": len(user.following),
    })

@api_bp.route("/users/<username>/posts")
def get_user_posts(username):
    """GET all posts from a user."""
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get("page", 1, type=int)
    
    posts = Post.query.filter_by(user_id=user.id, is_deleted=False).order_by(
        Post.created_at.desc()
    ).paginate(page=page, per_page=20)
    
    return jsonify({
        "posts": [{
            "id": p.id,
            "content": p.content,
            "image_url": p.image_url,
            "likes": len(p.likes),
            "comments": len(p.comments),
            "reactions": {r.emoji: len([x for x in p.reactions if x.emoji == r.emoji]) for r in p.reactions},
            "created_at": p.created_at.isoformat()
        } for p in posts.items],
        "total": posts.total,
        "pages": posts.pages,
        "current_page": page
    })

# Posts API

@api_bp.route("/posts/<int:post_id>")
def get_post(post_id):
    """GET post details."""
    post = Post.query.get_or_404(post_id)
    
    return jsonify({
        "id": post.id,
        "content": post.content,
        "image_url": post.image_url,
        "author": {
            "username": post.author.username,
            "display_name": post.author.display_name
        },
        "likes": len(post.likes),
        "comments": len(post.comments),
        "reactions": {r.emoji: sum(1 for x in post.reactions if x.emoji == r.emoji) for r in set((r.emoji for r in post.reactions))},
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat()
    })

@api_bp.route("/posts/<int:post_id>/comments")
def get_post_comments(post_id):
    """GET comments for a post."""
    post = Post.query.get_or_404(post_id)
    page = request.args.get("page", 1, type=int)
    
    comments = Comment.query.filter_by(post_id=post_id, is_deleted=False).order_by(
        Comment.created_at.asc()
    ).paginate(page=page, per_page=20)
    
    return jsonify({
        "comments": [{
            "id": c.id,
            "content": c.content,
            "author": {
                "username": c.author.username,
                "display_name": c.author.display_name
            },
            "created_at": c.created_at.isoformat()
        } for c in comments.items],
        "total": comments.total,
        "pages": comments.pages,
        "current_page": page
    })

# Search API

@api_bp.route("/search/users")
def search_users():
    """Search for users."""
    q = request.args.get("q", "").strip()
    
    if not q or len(q) < 2:
        return jsonify([])
    
    users = User.query.filter(
        db.or_(
            User.username.ilike(f"%{q}%"),
            User.display_name.ilike(f"%{q}%")
        )
    ).limit(10).all()
    
    return jsonify([{
        "username": u.username,
        "display_name": u.display_name,
        "followers": len(u.followers)
    } for u in users])

@api_bp.route("/search/posts")
def search_posts():
    """Search for posts."""
    q = request.args.get("q", "").strip()
    
    if not q or len(q) < 2:
        return jsonify([])
    
    posts = Post.query.filter(
        Post.content.ilike(f"%{q}%"),
        Post.is_deleted == False
    ).limit(10).all()
    
    return jsonify([{
        "id": p.id,
        "content": p.content[:100],
        "author": p.author.username,
        "created_at": p.created_at.isoformat()
    } for p in posts])

# Protected routes with JWT

@api_bp.route("/me", methods=["GET"])
@jwt_required()
def api_me():
    """GET current user data (requires JWT)."""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "bio": user.bio,
        "followers": len(user.followers),
        "following": len(user.following),
    })

@api_bp.route("/posts", methods=["POST"])
@jwt_required()
def create_post():
    """CREATE a new post (requires JWT)."""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    content = data.get("content", "").strip()
    if not content or len(content) > 500:
        return jsonify({"error": "Invalid content"}), 400
    
    post = Post(user_id=user_id, content=content)
    db.session.add(post)
    db.session.commit()
    
    logger.info(f"Post created via API by user {user_id}")
    return jsonify({"id": post.id, "created_at": post.created_at.isoformat()}), 201
