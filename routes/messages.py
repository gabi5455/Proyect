"""Rutas de mensajes privados."""
from flask import Blueprint, render_template_string, request, redirect, url_for
from models import User, Message
from database import db
from utils import requires_login, get_current_user, save_upload
import logging

messages_bp = Blueprint("messages", __name__, url_prefix="/messages")
logger = logging.getLogger(__name__)

@messages_bp.route("/")
@requires_login
def inbox():
    """Muestra el listado de conversaciones."""
    username, uid = get_current_user()
    
    # Obtener últimos mensajes de cada conversación
    conversations = db.session.query(Message).filter(
        db.or_(Message.from_user_id == uid, Message.to_user_id == uid)
    ).order_by(Message.created_at.desc()).all()
    
    return render_template_string("Messages inbox", conversations=conversations)

@messages_bp.route("/<other_username>")
@requires_login
def conversation(other_username):
    """Muestra una conversación con otro usuario."""
    username, uid = get_current_user()
    other_user = User.query.filter_by(username=other_username).first_or_404()
    
    # Obtener mensajes
    messages = Message.query.filter(
        db.or_(
            db.and_(Message.from_user_id == uid, Message.to_user_id == other_user.id),
            db.and_(Message.from_user_id == other_user.id, Message.to_user_id == uid)
        )
    ).order_by(Message.created_at.asc()).all()
    
    # Marcar como leídos
    Message.query.filter_by(from_user_id=other_user.id, to_user_id=uid).update({"is_read": True})
    db.session.commit()
    
    return render_template_string("Conversation", messages=messages, other_user=other_user)

@messages_bp.route("/<other_username>/send", methods=["POST"])
@requires_login
def send_message(other_username):
    """Envía un mensaje a otro usuario."""
    username, uid = get_current_user()
    other_user = User.query.filter_by(username=other_username).first_or_404()
    
    content = request.form.get("content", "").strip()
    photo = save_upload(request.files.get("photo_file")) if request.files.get("photo_file") else ""
    view_once = bool(request.form.get("view_once"))
    
    if photo:
        message = Message(
            from_user_id=uid,
            to_user_id=other_user.id,
            content=photo,
            msg_type="photo",
            view_once=view_once
        )
    elif content:
        message = Message(
            from_user_id=uid,
            to_user_id=other_user.id,
            content=content,
            msg_type="text"
        )
    else:
        return redirect(url_for("messages.conversation", other_username=other_username))
    
    db.session.add(message)
    db.session.commit()
    logger.info(f"Message sent from {username} to {other_username}")
    
    return redirect(url_for("messages.conversation", other_username=other_username))
