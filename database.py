"""Gestión de base de datos."""
from flask_sqlalchemy import SQLAlchemy
import logging

db = SQLAlchemy()
logger = logging.getLogger(__name__)

def init_db(app):
    """Inicializa la base de datos."""
    db.init_app(app)
    with app.app_context():
        from models import User, Post, Like, Follow, Comment, Notification, Message, Story
        db.create_all()
        logger.info("Database initialized")
