"""Socket.IO event handlers initialization."""
from .chat_events import register_chat_events
from .presence_events import register_presence_events

def register_all_events(socketio):
    """Registra todos los eventos de Socket.IO."""
    register_chat_events(socketio)
    register_presence_events(socketio)
