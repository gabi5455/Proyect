"""Configuración de Socket.IO."""
import os
from datetime import timedelta

class SocketIOConfig:
    """Configuración para Socket.IO."""
    
    # CORS
    CORS_ALLOWED_ORIGINS = os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5000"
    ).split(",")
    
    # Sesión
    SESSION_TIMEOUT = int(os.environ.get("SESSION_TIMEOUT", "3600"))  # 1 hora
    PING_TIMEOUT = int(os.environ.get("PING_TIMEOUT", "60"))  # 60 segundos
    PING_INTERVAL = int(os.environ.get("PING_INTERVAL", "25"))  # 25 segundos
    
    # Transporte
    TRANSPORTS = ["websocket", "polling"]
    
    # Rate limiting
    RATE_LIMIT = {
        "messages": {"limit": 100, "window": 60},  # 100 msgs/minuto
        "typing": {"limit": 10, "window": 1},      # 10 events/segundo
        "calls": {"limit": 5, "window": 60}        # 5 llamadas/minuto
    }
    
    # Almacenamiento
    MESSAGE_RETENTION = 30 * 24 * 60 * 60  # 30 días en segundos
    MAX_ROOM_SIZE = 2  # Máximo 2 usuarios por conversación
    
    # Logging
    LOGGER_ENABLED = os.environ.get("SOCKETIO_LOGGER_ENABLED", "False").lower() == "true"
    LOGGER_LEVEL = os.environ.get("SOCKETIO_LOGGER_LEVEL", "WARNING")
    ENGINEIO_LOGGER_ENABLED = os.environ.get("ENGINEIO_LOGGER_ENABLED", "False").lower() == "true"
