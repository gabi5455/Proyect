"""App mejorada con Email, JWT y Rate Limiting."""
import os
import logging
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config_advanced import config
from database import init_db, db
from routes import init_routes

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Extensiones globales
jwt = JWTManager()
mail = Mail()
limiter = Limiter(key_func=get_remote_address)

def create_app(config_name=None):
    """Factory para crear la aplicación Flask con todas las extensiones."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Crear carpeta de uploads
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Inicializar extensiones
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    
    init_db(app)
    init_routes(app)
    
    # Ruta para servir archivos subidos
    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        from flask import send_from_directory
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    
    # Manejo de errores globales
    @app.errorhandler(404)
    def not_found(e):
        return {"error": "No encontrado"}, 404
    
    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Internal server error: {e}")
        return {"error": "Error interno del servidor"}, 500
    
    logger.info(f"Application created with config: {config_name}")
    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
