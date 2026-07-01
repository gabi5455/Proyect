"""Rutas de autenticación."""
from flask import Blueprint, request, session, redirect, url_for, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from models import User
from database import db
from templates.auth_templates import LOGIN_TEMPLATE, REGISTER_TEMPLATE
import logging

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Inicia sesión de usuario."""
    if "user" in session:
        return redirect(url_for("main.feed"))
    
    err = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            if user.is_banned:
                err = "Tu cuenta ha sido suspendida."
            else:
                session["user"] = user.username
                session["user_id"] = user.id
                logger.info(f"User {username} logged in")
                return redirect(url_for("main.feed"))
        else:
            err = "Usuario o contraseña incorrectos."
    
    return render_template_string(LOGIN_TEMPLATE, err=err)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Registra un nuevo usuario."""
    if "user" in session:
        return redirect(url_for("main.feed"))
    
    err = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        
        if len(username) < 3 or not all(c.isalnum() or c == "_" for c in username):
            err = "Usuario: mín. 3 chars, solo letras, números y _"
        elif len(password) < 6:
            err = "Contraseña de al menos 6 caracteres."
        elif password != confirm:
            err = "Las contraseñas no coinciden."
        elif User.query.filter_by(username=username).first():
            err = "Ese usuario ya existe."
        else:
            try:
                new_user = User(username=username, password=generate_password_hash(password))
                db.session.add(new_user)
                db.session.commit()
                session["user"] = username
                session["user_id"] = new_user.id
                logger.info(f"New user registered: {username}")
                return redirect(url_for("main.feed"))
            except Exception as e:
                logger.error(f"Registration error: {e}")
                err = "Error al registrar. Intenta de nuevo."
    
    return render_template_string(REGISTER_TEMPLATE, err=err)

@auth_bp.route("/logout")
def logout():
    """Cierra la sesión del usuario."""
    username = session.get("user")
    session.clear()
    logger.info(f"User {username} logged out")
    return redirect(url_for("auth.login"))
