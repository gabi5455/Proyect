"""Eventos de presencia y estado de usuarios."""
from flask import session
from flask_socketio import emit, join_room, leave_room
from models_advanced import User
from database import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Almacenar presencia de usuarios
user_presence = {}  # {user_id: {'status': 'online', 'last_seen': datetime, 'device': 'mobile'}}

def register_presence_events(socketio):
    """Registra eventos de presencia."""
    
    @socketio.on('set_presence')
    def handle_set_presence(data):
        """Establece la presencia del usuario."""
        username = session.get('user')
        user_id = session.get('user_id')
        
        if not username:
            return
        
        status = data.get('status', 'online')  # online, away, offline, dnd (do not disturb)
        device = data.get('device', 'web')  # web, mobile, desktop
        
        user_presence[user_id] = {
            'username': username,
            'status': status,
            'device': device,
            'last_seen': datetime.utcnow().isoformat()
        }
        
        # Notificar a seguidos
        emit('user_presence', {
            'user_id': user_id,
            'username': username,
            'status': status,
            'device': device,
            'timestamp': datetime.utcnow().isoformat()
        }, broadcast=True)
        
        logger.info(f"User {username} set presence: {status} ({device})")
    
    @socketio.on('get_presence')
    def handle_get_presence(data):
        """Obtiene la presencia de un usuario."""
        target_user_id = data.get('user_id')
        
        if target_user_id in user_presence:
            presence = user_presence[target_user_id]
            emit('presence_info', presence)
        else:
            emit('presence_info', {
                'user_id': target_user_id,
                'status': 'offline',
                'last_seen': 'unknown'
            })
    
    @socketio.on('get_all_presence')
    def handle_get_all_presence():
        """Obtiene presencia de todos los usuarios online."""
        emit('all_presence', {
            'users': list(user_presence.values()),
            'total_online': len(user_presence),
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @socketio.on('watch_user')
    def handle_watch_user(data):
        """Observa cambios de presencia de un usuario."""
        username = session.get('user')
        user_id = session.get('user_id')
        watch_user_id = data.get('user_id')
        
        # Unirse a una sala de presencia
        room = f"presence_{watch_user_id}"
        join_room(room)
        
        if watch_user_id in user_presence:
            emit('user_presence', user_presence[watch_user_id])
        
        logger.debug(f"User {username} watching presence of user {watch_user_id}")
    
    @socketio.on('unwatch_user')
    def handle_unwatch_user(data):
        """Deja de observar cambios de presencia."""
        username = session.get('user')
        watch_user_id = data.get('user_id')
        
        room = f"presence_{watch_user_id}"
        leave_room(room)
        
        logger.debug(f"User {username} stopped watching presence of user {watch_user_id}")
    
    @socketio.on('idle')
    def handle_idle(data):
        """Marca al usuario como inactivo (away)."""
        username = session.get('user')
        user_id = session.get('user_id')
        
        if user_id in user_presence:
            user_presence[user_id]['status'] = 'away'
            user_presence[user_id]['last_seen'] = datetime.utcnow().isoformat()
            
            emit('user_presence', user_presence[user_id], broadcast=True)
            logger.info(f"User {username} marked as away")
    
    @socketio.on('active')
    def handle_active(data):
        """Marca al usuario como activo."""
        username = session.get('user')
        user_id = session.get('user_id')
        
        if user_id in user_presence:
            user_presence[user_id]['status'] = 'online'
            user_presence[user_id]['last_seen'] = datetime.utcnow().isoformat()
            
            emit('user_presence', user_presence[user_id], broadcast=True)
            logger.info(f"User {username} marked as active")
