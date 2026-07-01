"""Autenticación avanzada con Email, JWT y Rate Limiting."""
from flask import Blueprint, request, session, redirect, url_for, render_template_string, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_mail import Mail, Message
from itsdangerous import TimedSerializer
from datetime import datetime, timedelta
from models import User, PasswordReset
from database import db
from config import Config
import logging
import string
import secrets

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Serializador de tokens de email
ts = TimedSerializer(Config.SECRET_KEY)

def send_email(subject, recipient, text_body, html_body):
    """Envía un email."""
    try:
        msg = Message(
            subject=subject,
            recipients=[recipient],
            body=text_body,
            html=html_body
        )
        mail.send(msg)
        logger.info(f"Email sent to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False

def generate_verification_token(email):
    """Genera un token de verificación."""
    return ts.dumps(email, salt='email-verification')

def verify_email_token(token, expiration=3600):
    """Verifica un token de email."""
    try:
        email = ts.loads(token, salt='email-verification', max_age=expiration)
        return email
    except:
        return None

def generate_password_reset_token():
    """Genera un token seguro para reset de contraseña."""
    return secrets.token_urlsafe(32)

@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def register():
    """Registra un nuevo usuario con verificación de email."""
    if "user" in session:
        return redirect(url_for("main.feed"))
    
    err = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        
        # Validaciones
        if len(username) < 3 or not all(c.isalnum() or c == "_" for c in username):
            err = "Usuario: mín. 3 chars, solo letras, números y _"
        elif len(password) < 6:
            err = "Contraseña de al menos 6 caracteres."
        elif password != confirm:
            err = "Las contraseñas no coinciden."
        elif "@" not in email or "." not in email:
            err = "Email inválido."
        elif User.query.filter_by(username=username).first():
            err = "Ese usuario ya existe."
        elif User.query.filter_by(email=email).first():
            err = "Ese email ya está registrado."
        else:
            try:
                # Crear usuario sin verificar email aún
                new_user = User(
                    username=username,
                    email=email,
                    password=generate_password_hash(password),
                    email_verified=False
                )
                db.session.add(new_user)
                db.session.commit()
                
                # Enviar email de verificación
                token = generate_verification_token(email)
                verification_url = url_for(
                    "auth.verify_email",
                    token=token,
                    _external=True
                )
                
                html_body = f"""
                <h2>Bienvenido a Nexus!</h2>
                <p>Verifica tu email haciendo clic en el siguiente enlace:</p>
                <a href="{verification_url}">Verificar Email</a>
                <p>Este enlace expira en 1 hora.</p>
                """
                
                send_email(
                    subject="Verifica tu email en Nexus",
                    recipient=email,
                    text_body=f"Verifica tu email aquí: {verification_url}",
                    html_body=html_body
                )
                
                return render_template_string("""
                <!DOCTYPE html><html><head>{{ css|safe }}</head>
                <body>
                <div class="auth-page"><div class="auth-box">
                    <div class="auth-logo">✓ Nexus</div>
                    <p style="text-align:center;font-size:.9rem;color:#27ae60">Cuenta creada exitosamente</p>
                    <p style="text-align:center;font-size:.85rem;color:var(--muted);margin:20px 0">
                        Hemos enviado un email de verificación a <strong>{{ email }}</strong><br>
                        Revisa tu bandeja de entrada.
                    </p>
                    <div style="text-align:center;margin-top:30px">
                        <a href="/login" style="color:var(--brand);font-weight:700">Volver a login</a>
                    </div>
                </div></div>
                </body></html>
                """, email=email)
                
            except Exception as e:
                logger.error(f"Registration error: {e}")
                err = "Error al registrar. Intenta de nuevo."
    
    # Template
    from templates.auth_templates import REGISTER_TEMPLATE
    return render_template_string(REGISTER_TEMPLATE, err=err)

@auth_bp.route("/verify-email/<token>")
def verify_email(token):
    """Verifica el email del usuario."""
    email = verify_email_token(token)
    
    if not email:
        return render_template_string("""
        <!DOCTYPE html><html><head><style>
        body{display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif}
        .box{text-align:center}
        </style></head>
        <body><div class="box">
            <h2>❌ Token inválido o expirado</h2>
            <p><a href="/login">Volver a login</a></p>
        </div></body></html>
        """)
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return render_template_string("""
        <!DOCTYPE html><html><head><style>
        body{display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif}
        .box{text-align:center}
        </style></head>
        <body><div class="box">
            <h2>❌ Usuario no encontrado</h2>
            <p><a href="/login">Volver a login</a></p>
        </div></body></html>
        """)
    
    user.email_verified = True
    db.session.commit()
    logger.info(f"Email verified for user {user.username}")
    
    return render_template_string("""
    <!DOCTYPE html><html><head><style>
    body{display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif}
    .box{text-align:center}
    a{color:#6c63ff;text-decoration:none;font-weight:700}
    </style></head>
    <body><div class="box">
        <h2>✓ Email verificado correctamente</h2>
        <p>Tu cuenta está lista. <a href="/login">Inicia sesión</a></p>
    </div></body></html>
    """)

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per hour")
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
            elif not user.email_verified:
                err = "Debes verificar tu email primero."
            else:
                session["user"] = user.username
                session["user_id"] = user.id
                user.last_login = datetime.utcnow()
                db.session.commit()
                logger.info(f"User {username} logged in")
                return redirect(url_for("main.feed"))
        else:
            err = "Usuario o contraseña incorrectos."
    
    from templates.auth_templates import LOGIN_TEMPLATE
    return render_template_string(LOGIN_TEMPLATE, err=err)

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("3 per hour")
def forgot_password():
    """Inicia el proceso de recuperación de contraseña."""
    if "user" in session:
        return redirect(url_for("main.feed"))
    
    err = None
    ok = None
    
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Crear token de reset
            token = generate_password_reset_token()
            reset = PasswordReset(
                user_id=user.id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            db.session.add(reset)
            db.session.commit()
            
            # Enviar email
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            html_body = f"""
            <h2>Recuperar contraseña</h2>
            <p>Haz clic en el siguiente enlace para recuperar tu contraseña:</p>
            <a href="{reset_url}">Recuperar Contraseña</a>
            <p>Este enlace expira en 1 hora.</p>
            """
            
            send_email(
                subject="Recupera tu contraseña en Nexus",
                recipient=email,
                text_body=f"Recupera tu contraseña aquí: {reset_url}",
                html_body=html_body
            )
            ok = "Hemos enviado instrucciones a tu email."
        else:
            # No revelar si el email existe
            ok = "Hemos enviado instrucciones a tu email."
    
    return render_template_string("""
    <!DOCTYPE html><html><head>
    <style>
    body{display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;background:#f5f5f5}
    .box{background:white;padding:40px;border-radius:10px;width:100%;max-width:380px}
    h2{margin-bottom:20px}
    input{width:100%;padding:12px;margin-bottom:10px;border:1px solid #ccc;border-radius:5px;font-family:inherit}
    button{width:100%;padding:12px;background:#6c63ff;color:white;border:none;border-radius:5px;font-weight:700;cursor:pointer}
    .msg{padding:10px;border-radius:5px;margin-bottom:15px;text-align:center}
    .ok{background:#f0fff4;color:#27ae60;border:1px solid #b7eacb}
    .err{background:#fff0f0;color:#c0392b;border:1px solid #ffd5d5}
    a{color:#6c63ff;text-decoration:none}
    </style>
    </head>
    <body>
    <div class="box">
        <h2>Recuperar Contraseña</h2>
        {% if ok %}<div class="msg ok">{{ ok }}</div>{% endif %}
        {% if err %}<div class="msg err">{{ err }}</div>{% endif %}
        <form method="POST">
            <input type="email" name="email" placeholder="Tu email" required>
            <button type="submit">Enviar instrucciones</button>
        </form>
        <p style="text-align:center;margin-top:20px"><a href="/login">Volver a login</a></p>
    </div>
    </body></html>
    """, err=err, ok=ok)

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Establece una nueva contraseña."""
    reset = PasswordReset.query.filter_by(token=token, used=False).first()
    
    if not reset or reset.expires_at < datetime.utcnow():
        return render_template_string("""
        <!DOCTYPE html><html><body style="text-align:center;padding:50px">
        <h2>❌ Link inválido o expirado</h2>
        <p><a href="/login">Volver a login</a></p>
        </body></html>
        """)
    
    err = None
    ok = None
    
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        
        if len(password) < 6:
            err = "Mínimo 6 caracteres."
        elif password != confirm:
            err = "Las contraseñas no coinciden."
        else:
            user = reset.user
            user.password = generate_password_hash(password)
            reset.used = True
            db.session.commit()
            logger.info(f"Password reset for user {user.username}")
            return render_template_string("""
            <!DOCTYPE html><html><body style="text-align:center;padding:50px">
            <h2>✓ Contraseña actualizada</h2>
            <p><a href="/login">Inicia sesión</a></p>
            </body></html>
            """)
    
    return render_template_string("""
    <!DOCTYPE html><html><head>
    <style>
    body{display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;background:#f5f5f5}
    .box{background:white;padding:40px;border-radius:10px;width:100%;max-width:380px}
    h2{margin-bottom:20px}
    input{width:100%;padding:12px;margin-bottom:10px;border:1px solid #ccc;border-radius:5px;font-family:inherit}
    button{width:100%;padding:12px;background:#6c63ff;color:white;border:none;border-radius:5px;font-weight:700;cursor:pointer}
    .err{background:#fff0f0;color:#c0392b;border:1px solid #ffd5d5;padding:10px;border-radius:5px;margin-bottom:15px}
    </style>
    </head>
    <body>
    <div class="box">
        <h2>Nueva Contraseña</h2>
        {% if err %}<div class="err">{{ err }}</div>{% endif %}
        <form method="POST">
            <input type="password" name="password" placeholder="Nueva contraseña" required>
            <input type="password" name="confirm" placeholder="Confirmar contraseña" required>
            <button type="submit">Cambiar contraseña</button>
        </form>
    </div>
    </body></html>
    """, err=err)

@auth_bp.route("/logout")
def logout():
    """Cierra la sesión del usuario."""
    username = session.get("user")
    session.clear()
    logger.info(f"User {username} logged out")
    return redirect(url_for("auth.login"))

# API endpoints con JWT

@auth_bp.route("/api/login", methods=["POST"])
@limiter.limit("10 per hour")
def api_login():
    """Login via API con JWT."""
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password, password) and not user.is_banned:
        access_token = create_access_token(identity=user.id)
        return jsonify({"access_token": access_token, "user_id": user.id}), 200
    
    return jsonify({"error": "Credenciales inválidas"}), 401

@auth_bp.route("/api/me", methods=["GET"])
@jwt_required()
def api_me():
    """Obtiene datos del usuario autenticado."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name
    }), 200
