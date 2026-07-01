"""Configuración mejorada con soporte para Email y JWT."""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuración base de la aplicación."""
    
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "nexus-ultra-secret-2025")
    DEBUG = os.environ.get("DEBUG", "False") == "True"
    TESTING = False
    
    # Database
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/nexus")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = DEBUG
    
    # Security
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False") == "True"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    
    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    
    # Email
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", True)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@nexus.app")
    
    # Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "heic", "mp4", "mov", "webm"}
    
    # App settings
    OWNER_USERNAME = "gxbriel_exe"
    ITEMS_PER_PAGE = 20
    POSTS_LIMIT = 40
    STORIES_EXPIRY_HOURS = 24
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get("REDIS_URL", "memory://")
    
    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = "logs/app.log"


class DevelopmentConfig(Config):
    """Configuración para desarrollo."""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Configuración para testing."""
    DEBUG = True
    TESTING = True
    DATABASE_URL = "sqlite:///test.db"
    SQLALCHEMY_DATABASE_URI = "sqlite:///test.db"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Configuración para producción."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
