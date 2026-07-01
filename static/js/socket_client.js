/**
 * Cliente Socket.IO para chat en tiempo real
 */

class ChatSocketClient {
  constructor() {
    this.socket = null;
    this.currentConversation = null;
    this.isTyping = false;
    this.typingTimeout = null;
    this.messageHandlers = {};
    this.presenceHandlers = {};
  }

  /**
   * Inicia conexión a Socket.IO
   */
  connect() {
    this.socket = io({
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: 5
    });

    this.setupConnectionHandlers();
    this.setupChatHandlers();
    this.setupPresenceHandlers();
    this.setupCallHandlers();
  }

  /**
   * Configura handlers de conexión
   */
  setupConnectionHandlers() {
    this.socket.on('connection_response', (data) => {
      console.log('✅ Conectado:', data.data);
      this.setPresence('online', 'web');
    });

    this.socket.on('connect_error', (error) => {
      console.error('❌ Error de conexión:', error);
      this.showNotification('Error de conexión', 'error');
    });

    this.socket.on('disconnect', () => {
      console.log('📴 Desconectado');
      this.showNotification('Desconectado del servidor', 'warning');
    });

    this.socket.on('reconnect', () => {
      console.log('🔄 Reconectado');
      this.showNotification('Reconectado', 'success');
    });
  }

  /**
   * Configura handlers de chat
   */
  setupChatHandlers() {
    this.socket.on('new_message', (data) => {
      this.handleNewMessage(data);
    });

    this.socket.on('user_typing', (data) => {
      this.showTypingIndicator(data.username);
    });

    this.socket.on('user_stop_typing', (data) => {
      this.hideTypingIndicator(data.username);
    });

    this.socket.on('message_read', (data) => {
      this.markMessageAsRead(data.message_id);
    });

    this.socket.on('user_online', (data) => {
      console.log(`👤 ${data.username} se conectó`);
      this.updateUserStatus(data.username, 'online');
    });

    this.socket.on('user_offline', (data) => {
      console.log(`👤 ${data.username} se desconectó`);
      this.updateUserStatus(data.username, 'offline');
    });
  }

  /**
   * Configura handlers de presencia
   */
  setupPresenceHandlers() {
    this.socket.on('user_presence', (data) => {
      this.updatePresence(data);
    });

    this.socket.on('presence_info', (data) => {
      console.log('Presencia:', data);
    });

    this.socket.on('all_presence', (data) => {
      console.log(`👥 Usuarios online: ${data.total_online}`);
    });
  }

  /**
   * Configura handlers de llamadas
   */
  setupCallHandlers() {
    this.socket.on('incoming_call', (data) => {
      this.handleIncomingCall(data);
    });

    this.socket.on('call_accepted', (data) => {
      this.handleCallAccepted(data);
    });

    this.socket.on('call_rejected', (data) => {
      this.handleCallRejected(data);
    });

    this.socket.on('call_ended', (data) => {
      this.handleCallEnded(data);
    });
  }

  /**
   * Unirse a conversación
   */
  joinConversation(otherUsername) {
    this.currentConversation = otherUsername;
    this.socket.emit('join_conversation', {
      other_username: otherUsername
    });
    console.log(`Unido a conversación con ${otherUsername}`);
  }

  /**
   * Salir de conversación
   */
  leaveConversation() {
    if (!this.currentConversation) return;
    
    this.socket.emit('leave_conversation', {
      other_username: this.currentConversation
    });
    this.currentConversation = null;
  }

  /**
   * Enviar mensaje
   */
  sendMessage(content, toUserId, type = 'text') {
    if (!content.trim()) return;

    this.socket.emit('send_message', {
      content: content.trim(),
      to_user_id: toUserId,
      type: type,
      timestamp: new Date().toISOString()
    });

    this.stopTyping();
  }

  /**
   * Indicar que está escribiendo
   */
  startTyping(toUserId) {
    if (this.isTyping) return;

    this.isTyping = true;
    this.socket.emit('typing', { to_user_id: toUserId });

    clearTimeout(this.typingTimeout);
    this.typingTimeout = setTimeout(() => {
      this.stopTyping(toUserId);
    }, 3000);
  }

  /**
   * Dejar de escribir
   */
  stopTyping(toUserId) {
    if (!this.isTyping) return;

    this.isTyping = false;
    this.socket.emit('stop_typing', { to_user_id: toUserId });
    clearTimeout(this.typingTimeout);
  }

  /**
   * Marcar mensaje como leído
   */
  markMessageRead(messageId) {
    this.socket.emit('read_message', { message_id: messageId });
  }

  /**
   * Establecer presencia
   */
  setPresence(status, device = 'web') {
    this.socket.emit('set_presence', {
      status: status,  // online, away, offline, dnd
      device: device   // web, mobile, desktop
    });
  }

  /**
   * Obtener presencia de usuario
   */
  getPresence(userId) {
    this.socket.emit('get_presence', { user_id: userId });
  }

  /**
   * Obtener presencia de todos
   */
  getAllPresence() {
    this.socket.emit('get_all_presence');
  }

  /**
   * Observar usuario
   */
  watchUser(userId) {
    this.socket.emit('watch_user', { user_id: userId });
  }

  /**
   * Dejar de observar usuario
   */
  unwatchUser(userId) {
    this.socket.emit('unwatch_user', { user_id: userId });
  }

  /**
   * Iniciar llamada
   */
  initiateCall(toUserId, type = 'voice') {
    this.socket.emit('call_initiate', {
      to_user_id: toUserId,
      type: type  // voice, video
    });
  }

  /**
   * Aceptar llamada
   */
  acceptCall(fromUserId) {
    this.socket.emit('call_accept', {
      from_user_id: fromUserId
    });
  }

  /**
   * Rechazar llamada
   */
  rejectCall(fromUserId, reason = 'rechazada') {
    this.socket.emit('call_reject', {
      from_user_id: fromUserId,
      reason: reason
    });
  }

  /**
   * Terminar llamada
   */
  endCall(otherUserId, duration = 0) {
    this.socket.emit('call_end', {
      other_user_id: otherUserId,
      duration: duration
    });
  }

  /**
   * Marcar como inactivo
   */
  setIdle() {
    this.socket.emit('idle');
  }

  /**
   * Marcar como activo
   */
  setActive() {
    this.socket.emit('active');
  }

  // ===== HANDLERS =====

  handleNewMessage(data) {
    const message = {
      id: data.id,
      from: data.from_username,
      content: data.content,
      type: data.type,
      timestamp: data.timestamp,
      isRead: data.is_read
    };

    if (this.messageHandlers['new_message']) {
      this.messageHandlers['new_message'](message);
    }

    console.log('📨 Nuevo mensaje:', message);
  }

  showTypingIndicator(username) {
    console.log(`✏️ ${username} está escribiendo...`);
    if (this.messageHandlers['typing']) {
      this.messageHandlers['typing'](username);
    }
  }

  hideTypingIndicator(username) {
    console.log(`${username} dejó de escribir`);
    if (this.messageHandlers['stop_typing']) {
      this.messageHandlers['stop_typing'](username);
    }
  }

  markMessageAsRead(messageId) {
    if (this.messageHandlers['read']) {
      this.messageHandlers['read'](messageId);
    }
  }

  updateUserStatus(username, status) {
    if (this.messageHandlers['user_status']) {
      this.messageHandlers['user_status'](username, status);
    }
  }

  updatePresence(data) {
    console.log(`👤 ${data.username}: ${data.status}`);
    if (this.presenceHandlers['update']) {
      this.presenceHandlers['update'](data);
    }
  }

  handleIncomingCall(data) {
    console.log(`📞 Llamada entrante de ${data.from_username}`);
    this.showNotification(
      `${data.from_username} te está llamando...`,
      'info',
      5000
    );
    
    if (this.messageHandlers['incoming_call']) {
      this.messageHandlers['incoming_call'](data);
    }
  }

  handleCallAccepted(data) {
    console.log(`✅ Llamada aceptada por ${data.accepted_by}`);
    if (this.messageHandlers['call_accepted']) {
      this.messageHandlers['call_accepted'](data);
    }
  }

  handleCallRejected(data) {
    console.log(`❌ Llamada rechazada: ${data.reason}`);
    this.showNotification(`Llamada rechazada`, 'warning');
    if (this.messageHandlers['call_rejected']) {
      this.messageHandlers['call_rejected'](data);
    }
  }

  handleCallEnded(data) {
    console.log(`☎️ Llamada terminada (${data.duration}s)`);
    if (this.messageHandlers['call_ended']) {
      this.messageHandlers['call_ended'](data);
    }
  }

  // ===== UTILIDADES =====

  /**
   * Registrar handler de mensajes
   */
  onMessage(event, handler) {
    this.messageHandlers[event] = handler;
  }

  /**
   * Registrar handler de presencia
   */
  onPresence(event, handler) {
    this.presenceHandlers[event] = handler;
  }

  /**
   * Mostrar notificación
   */
  showNotification(message, type = 'info', duration = 3000) {
    console.log(`[${type.toUpperCase()}] ${message}`);
    // Implementar en UI
  }

  /**
   * Desconectar
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      console.log('Desconectado de Socket.IO');
    }
  }
}

// Instancia global
const chatClient = new ChatSocketClient();
