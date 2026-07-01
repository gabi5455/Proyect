"""Eventos de chat en tiempo real con Socket.IO."""
from flask import request, session
from flask_socketio import emit, join_room, leave_room, rooms
from models_advanced import Message, User, Notification
from database import db
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

# Almacenar usuarios conectados por sala
connected_users = {}

def register_chat_events(socketio):
    """Registra todos los eventos de chat."""
    
    @socketio.on('connect')
    def handle_connect():
        """Maneja conexión de usuario."""
        username = session.get('user')
        user_id = session.get('user_id')
        
        if not username:
            return False
        
        logger.info(f"User {username} connected via WebSocket")
        emit('connection_response', {
            'data': f'Conectado como {username}',
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return True
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Maneja desconexión de usuario."""
        username = session.get('user')
        user_id = session.get('user_id')
        
        if not username:
            return
        
        # Remover de todas las salas
        for room in list(rooms()):
            leave_room(room)
            # Notificar que se fue
            emit('user_offline', {
                'username': username,
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room)
        
        logger.info(f"User {username} disconnected")
    
    @socketio.on('join_conversation')
    def on_join_conversation(data):
        """Se une a una sala de conversación."""
        username = session.get('user')
        user_id = session.get('user_id')
        
        if not username:
            emit('error', {'message': 'No autenticado'})
            return
        
        other_username = data.get('other_username')
        
        if not other_username:
            emit('error', {'message': 'Username requerido'})
            return
        
        # Crear ID de sala único
        room = f"chat_{min(user_id, other_username)}_{max(user_id, other_username)}"
        
        join_room(room)
        
        if room not in connected_users:
            connected_users[room] = []
        
        connected_users[room].append({
            'username': username,
            'user_id': user_id,
            'connected_at': datetime.utcnow().isoformat()
        })
        
        # Notificar que se unió
        emit('user_online', {
            'username': username,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room)
        
        logger.info(f"User {username} joined conversation: {room}")
    
    @socketio.on('leave_conversation')
    def on_leave_conversation(data):
        """Se va de una sala de conversación."""
        username = session.get('user')
        user_id = session.get('user_id')
        
        other_username = data.get('other_username')
        room = f"chat_{min(user_id, other_username)}_{max(user_id, other_username)}"
        
        leave_room(room)
        
        if room in connected_users:
            connected_users[room] = [
                u for u in connected_users[room] if u['user_id'] != user_id
            ]
        
        emit('user_offline', {
            'username': username,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room)
        
        logger.info(f"User {username} left conversation: {room}")
    
    @socketio.on('send_message')
    def handle_send_message(data):
        """Maneja envío de mensaje en tiempo real."""
        username = session.get('user')
        user_id = session.get('user_id')
        
        if not username:
            emit('error', {'message': 'No autenticado'})
            return
        
        content = data.get('content', '').strip()
        other_user_id = data.get('to_user_id')
        msg_type = data.get('type', 'text')  # text, image, video
        
        if not content and msg_type == 'text':
            emit('error', {'message': 'Mensaje vacío'})
            return
        
        if len(content) > 500:
            emit('error', {'message': 'Mensaje muy largo'})
            return
        
        # Crear mensaje en BD
        message = Message(
            from_user_id=user_id,
            to_user_id=other_user_id,
            content=content,
            msg_type=msg_type,
            created_at=datetime.utcnow()
        )
        db.session.add(message)
        db.session.commit()
        
        room = f"chat_{min(user_id, other_user_id)}_{max(user_id, other_user_id)}"
        
        # Emitir a ambos usuarios
        emit('new_message', {
            'id': message.id,
            'from_user_id': user_id,
            'from_username': username,
            'content': content,
            'type': msg_type,
            'timestamp': message.created_at.isoformat(),
            'is_read': False
        }, room=room)
        
        # Crear notificación
        notif = Notification(
            user_id=other_user_id,
            from_user_id=user_id,
            type='message'
        )
        db.session.add(notif)
        db.session.commit()
        
        logger.info(f"Message sent from {username} to user {other_user_id}")
    
    @socketio.on('typing')
    def handle_typing(data):
        """Notifica que alguien está escribiendo."""
        username = session.get('user')
        user_id = session.get('user_id')
        other_user_id = data.get('to_user_id')
        
        if not username:
            return
        
        room = f"chat_{min(user_id, other_user_id)}_{max(user_id, other_user_id)}"
        
        emit('user_typing', {
            'username': username,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room, skip_sid=request.sid)  # No enviar al remitente
        
        logger.debug(f"User {username} is typing in {room}")
    
    @socketio.on('stop_typing')
    def handle_stop_typing(data):
        """Notifica que alguien dejó de escribir."""
        username = session.get('user')
        user_id = session.get('user_id')
        other_user_id = data.get('to_user_id')
        
        if not username:
            return
        
        room = f"chat_{min(user_id, other_user_id)}_{max(user_id, other_user_id)}"
        
        emit('user_stop_typing', {
            'username': username,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room, skip_sid=request.sid)
        
        logger.debug(f"User {username} stopped typing in {room}")
    
    @socketio.on('read_message')
    def handle_read_message(data):
        """Marca un mensaje como leído."""
        username = session.get('user')
        user_id = session.get('user_id')
        message_id = data.get('message_id')
        
        if not username or not message_id:
            return
        
        message = Message.query.get(message_id)
        if message and message.to_user_id == user_id:
            message.is_read = True
            db.session.commit()
            
            other_user_id = message.from_user_id
            room = f"chat_{min(user_id, other_user_id)}_{max(user_id, other_user_id)}"
            
            emit('message_read', {
                'message_id': message_id,
                'read_by': username,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room)
            
            logger.debug(f"Message {message_id} marked as read by {username}")
    
    @socketio.on('user_status')
    def handle_user_status(data):
        """Actualiza el estado del usuario (online/away/offline)."""
        username = session.get('user')
        user_id = session.get('user_id')
        status = data.get('status', 'online')  # online, away, offline
        
        if not username:
            return
        
        # Emitir a todas las salas donde está
        for room in list(rooms()):
            emit('user_status_change', {
                'username': username,
                'user_id': user_id,
                'status': status,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room)
        
        logger.info(f"User {username} status changed to {status}")
    
    @socketio.on('call_initiate')
    def handle_call_initiate(data):
        """Inicia una llamada de voz/video."""
        username = session.get('user')
        user_id = session.get('user_id')
        to_user_id = data.get('to_user_id')
        call_type = data.get('type', 'voice')  # voice, video
        
        if not username or not to_user_id:
            emit('error', {'message': 'Datos de llamada inválidos'})
            return
        
        room = f"chat_{min(user_id, to_user_id)}_{max(user_id, to_user_id)}"
        
        emit('incoming_call', {
            'from_user_id': user_id,
            'from_username': username,
            'type': call_type,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room, skip_sid=request.sid)
        
        logger.info(f"Call initiated by {username} to user {to_user_id} (type: {call_type})")
    
    @socketio.on('call_accept')
    def handle_call_accept(data):
        """Acepta una llamada."""
        username = session.get('user')
        user_id = session.get('user_id')
        from_user_id = data.get('from_user_id')
        
        room = f"chat_{min(user_id, from_user_id)}_{max(user_id, from_user_id)}"
        
        emit('call_accepted', {
            'accepted_by': username,
            'accepted_by_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room)
        
        logger.info(f"Call accepted by {username}")
    
    @socketio.on('call_reject')
    def handle_call_reject(data):
        """Rechaza una llamada."""
        username = session.get('user')
        user_id = session.get('user_id')
        from_user_id = data.get('from_user_id')
        
        room = f"chat_{min(user_id, from_user_id)}_{max(user_id, from_user_id)}"
        
        emit('call_rejected', {
            'rejected_by': username,
            'reason': data.get('reason', 'rechazada'),
            'timestamp': datetime.utcnow().isoformat()
        }, room=room)
        
        logger.info(f"Call rejected by {username}")
    
    @socketio.on('call_end')
    def handle_call_end(data):
        """Termina una llamada."""
        username = session.get('user')
        user_id = session.get('user_id')
        other_user_id = data.get('other_user_id')
        duration = data.get('duration', 0)  # en segundos
        
        room = f"chat_{min(user_id, other_user_id)}_{max(user_id, other_user_id)}"
        
        emit('call_ended', {
            'ended_by': username,
            'duration': duration,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room)
        
        logger.info(f"Call ended by {username} (duration: {duration}s)")
