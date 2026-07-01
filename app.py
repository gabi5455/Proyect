"""Punto de entrada de la aplicación."""
import os
import logging
from flask import Flask
from config import config
from database import init_db, db
from routes import init_routes

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name=None):
    """Factory para crear la aplicación Flask."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Crear carpeta de uploads
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    
    # Inicializar extensiones
    init_db(app)
    
    # Registrar blueprints
    init_routes(app)
    
    # Ruta para servir archivos subidos
    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        from flask import send_from_directory
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    
    logger.info(f"Application created with config: {config_name}")
    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
