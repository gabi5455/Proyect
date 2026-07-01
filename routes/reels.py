"""Rutas de reels (videos cortos)."""
from flask import Blueprint, render_template_string
from models import Post
from database import db
from utils import requires_login, get_current_user

reels_bp = Blueprint("reels", __name__, url_prefix="/reels")

@reels_bp.route("/")
@requires_login
def reels():
    """Muestra reels (videos)."""
    username, uid = get_current_user()
    
    # Obtener posts con video
    videos = Post.query.filter(
        db.or_(
            Post.image_url.ilike("%.mp4"),
            Post.image_url.ilike("%.mov"),
            Post.image_url.ilike("%.webm")
        )
    ).order_by(Post.created_at.desc()).limit(50).all()
    
    return render_template_string("Reels", videos=videos)
