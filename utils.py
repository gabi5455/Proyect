"""Funciones auxiliares y utilitarios."""
import html
import uuid
import os
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, render_template_string
from config import Config

# Colores para avatares
COLORS = ["#6c63ff", "#ff6b9d", "#48c6ef", "#f7b731", "#26de81", "#fc5c65", "#45aaf2", "#fd9644", "#a29bfe", "#fd79a8"]

def get_avatar_color(username):
    """Obtiene un color consistente para el avatar de un usuario."""
    return COLORS[sum(ord(c) for c in username) % len(COLORS)]

def get_current_user():
    """Obtiene el usuario actual de la sesión."""
    return session.get("user"), session.get("user_id")

def is_owner(username):
    """Verifica si el usuario es el propietario."""
    return username and username.lower() == Config.OWNER_USERNAME.lower()

def escape_html(text):
    """Escapa caracteres HTML."""
    return html.escape(str(text))

def time_ago(timestamp):
    """Calcula el tiempo relativo desde un timestamp."""
    try:
        if isinstance(timestamp, datetime):
            dt = timestamp.replace(tzinfo=None)
        else:
            dt = datetime.strptime(str(timestamp)[:19], "%Y-%m-%d %H:%M:%S")
        diff = (datetime.utcnow() - dt).total_seconds()
        if diff < 60:
            return f"{int(diff)}s"
        if diff < 3600:
            return f"{int(diff//60)}m"
        if diff < 86400:
            return f"{int(diff//3600)}h"
        return f"{int(diff//86400)}d"
    except:
        return ""

def allowed_file(filename):
    """Verifica si la extensión del archivo está permitida."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def save_upload(file_obj):
    """Guarda un archivo subido y retorna su URL."""
    if file_obj and file_obj.filename and allowed_file(file_obj.filename):
        ext = file_obj.filename.rsplit(".", 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        file_obj.save(os.path.join(Config.UPLOAD_FOLDER, filename))
        return f"/uploads/{filename}"
    return ""

def requires_login(f):
    """Decorador para rutas que requieren login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username, uid = get_current_user()
        if not username:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def requires_owner(f):
    """Decorador para rutas que requieren permisos de owner."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username, _ = get_current_user()
        if not is_owner(username):
            return redirect(url_for("main.feed"))
        return f(*args, **kwargs)
    return decorated_function
