import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuración base de la aplicación."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "nexus-ultra-secret-2025")
    DEBUG = os.environ.get("DEBUG", "False") == "True"
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/nexus")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "heic", "mp4", "mov", "webm"}
    OWNER_USERNAME = "gxbriel_exe"
    ITEMS_PER_PAGE = 20
    POSTS_LIMIT = 40
    STORIES_EXPIRY_HOURS = 24
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    DATABASE_URL = "sqlite:///test.db"

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
