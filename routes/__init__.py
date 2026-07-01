"""Blueprints de rutas."""
from flask import Blueprint

def init_routes(app):
    """Registra todos los blueprints."""
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.posts import posts_bp
    from routes.profiles import profiles_bp
    from routes.messages import messages_bp
    from routes.stories import stories_bp
    from routes.notifications import notifications_bp
    from routes.reels import reels_bp
    from routes.owner import owner_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(profiles_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(stories_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(reels_bp)
    app.register_blueprint(owner_bp)
