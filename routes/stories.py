"""Rutas de historias."""
from flask import Blueprint, render_template_string, request, redirect, url_for
from models import User, Story
from database import db
from utils import requires_login, get_current_user, save_upload, is_owner
from datetime import datetime, timedelta
import logging

stories_bp = Blueprint("stories", __name__, url_prefix="/stories")
logger = logging.getLogger(__name__)

@stories_bp.route("/create", methods=["GET", "POST"])
@requires_login
def create():
    """Crea una nueva historia."""
    username, uid = get_current_user()
    
    if request.method == "POST":
        image_url = request.form.get("image_url", "").strip()
        caption = request.form.get("caption", "").strip()[:150]
        
        if request.files.get("image_file"):
            image_url = save_upload(request.files["image_file"])
        
        if not image_url and not caption:
            return redirect(url_for("stories.create"))
        
        story = Story(user_id=uid, image_url=image_url, caption=caption)
        db.session.add(story)
        db.session.commit()
        logger.info(f"Story created by {username}")
        return redirect(url_for("stories.view", story_id=story.id))
    
    return render_template_string("Create story")

@stories_bp.route("/<int:story_id>")
@requires_login
def view(story_id):
    """Muestra una historia."""
    story = Story.query.get_or_404(story_id)
    
    # Verificar que la historia no sea muy antigua
    age = datetime.utcnow() - story.created_at
    if age > timedelta(hours=24):
        return redirect(url_for("main.feed"))
    
    return render_template_string("Story view", story=story)

@stories_bp.route("/<int:story_id>/delete", methods=["POST"])
@requires_login
def delete(story_id):
    """Elimina una historia."""
    username, uid = get_current_user()
    story = Story.query.get_or_404(story_id)
    
    if story.user_id != uid and not is_owner(username):
        return redirect(url_for("main.feed"))
    
    db.session.delete(story)
    db.session.commit()
    logger.info(f"Story {story_id} deleted by {username}")
    return redirect(url_for("main.feed"))
