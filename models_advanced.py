"""Modelos actualizados con campos nuevos para autenticación avanzada."""
from database import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON

class User(db.Model):
    """Modelo de usuario mejorado."""
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(100), default="")
    bio = db.Column(db.Text, default="")
    avatar_url = db.Column(db.String(255), default="")
    
    # Email verification
    email_verified = db.Column(db.Boolean, default=False)
    email_verified_at = db.Column(db.DateTime, nullable=True)
    
    # Account status
    is_banned = db.Column(db.Boolean, default=False, index=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_moderator = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # 2FA
    two_fa_enabled = db.Column(db.Boolean, default=False)
    two_fa_secret = db.Column(db.String(255), nullable=True)
    
    # Relaciones
    posts = db.relationship("Post", backref="author", lazy=True, cascade="all, delete-orphan")
    likes = db.relationship("Like", backref="user", lazy=True, cascade="all, delete-orphan")
    comments = db.relationship("Comment", backref="author", lazy=True, cascade="all, delete-orphan")
    messages_sent = db.relationship("Message", foreign_keys="Message.from_user_id", backref="sender", lazy=True)
    messages_received = db.relationship("Message", foreign_keys="Message.to_user_id", backref="receiver", lazy=True)
    stories = db.relationship("Story", backref="author", lazy=True, cascade="all, delete-orphan")
    followers = db.relationship("Follow", foreign_keys="Follow.follower_id", backref="follower", lazy=True)
    following = db.relationship("Follow", foreign_keys="Follow.following_id", backref="following_user", lazy=True)
    password_resets = db.relationship("PasswordReset", backref="user", lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.username}>"

class PasswordReset(db.Model):
    """Modelo para tokens de reset de contraseña."""
    __tablename__ = "password_resets"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

class Post(db.Model):
    """Modelo de publicación mejorado."""
    __tablename__ = "posts"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), default="")
    is_pinned = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    likes = db.relationship("Like", backref="post", lazy=True, cascade="all, delete-orphan")
    comments = db.relationship("Comment", backref="post", lazy=True, cascade="all, delete-orphan")
    reactions = db.relationship("Reaction", backref="post", lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Post {self.id} by {self.author.username}>"

class Like(db.Model):
    """Modelo de like."""
    __tablename__ = "likes"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint("user_id", "post_id", name="unique_user_post_like"),)

class Reaction(db.Model):
    """Modelo de reacciones (emojis)."""
    __tablename__ = "reactions"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)  # ❤️, 😂, 😢, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint("user_id", "post_id", "emoji", name="unique_reaction"),)

class Follow(db.Model):
    """Modelo de seguimiento."""
    __tablename__ = "follows"
    
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    following_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint("follower_id", "following_id", name="unique_follow"),)

class Comment(db.Model):
    """Modelo de comentario."""
    __tablename__ = "comments"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Comment {self.id} on Post {self.post_id}>"

class Notification(db.Model):
    """Modelo de notificación."""
    __tablename__ = "notifications"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # like, comment, follow, mention
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="SET NULL"), nullable=True)
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<Notification {self.type} to user {self.user_id}>"

class Message(db.Model):
    """Modelo de mensaje privado."""
    __tablename__ = "messages"
    
    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = db.Column(db.Text, default="")
    msg_type = db.Column(db.String(20), default="text")  # text, photo, voice, video
    view_once = db.Column(db.Boolean, default=False)
    viewed = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<Message from {self.from_user_id} to {self.to_user_id}>"

class Story(db.Model):
    """Modelo de historia (24h)."""
    __tablename__ = "stories"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = db.Column(db.String(255), default="")
    caption = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<Story {self.id} by {self.author.username}>"

class Hashtag(db.Model):
    """Modelo de hashtag."""
    __tablename__ = "hashtags"
    
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(100), unique=True, nullable=False, index=True)
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SavedPost(db.Model):
    """Modelo para guardar posts."""
    __tablename__ = "saved_posts"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint("user_id", "post_id", name="unique_saved_post"),)

class Report(db.Model):
    """Modelo para reportes de contenido."""
    __tablename__ = "reports"
    
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reported_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="SET NULL"), nullable=True)
    reason = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")  # pending, reviewing, resolved, dismissed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
