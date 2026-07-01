# Fase 4 - Chat en Tiempo Real con WebSockets

## 🚀 Características Implementadas

### ✅ Comunicación en Tiempo Real
- **WebSockets con Socket.IO**
  - Fallback a polling si WebSocket no está disponible
  - Auto-reconexión con exponential backoff
  - Manejo robusto de desconexiones

### ✅ Eventos de Chat
```
🟢 JOIN_CONVERSATION     - Unirse a conversación
🔴 LEAVE_CONVERSATION    - Salir de conversación
📨 SEND_MESSAGE         - Enviar mensaje
✏️  TYPING              - Usuario escribiendo
⏹️  STOP_TYPING         - Usuario dejó de escribir
✅ READ_MESSAGE         - Marcar como leído
```

### ✅ Indicador de Escritura
- Muestra "Usuario está escribiendo..."
- Desaparece automáticamente después de 3 segundos
- No se envía al remitente (skip_sid)
- Cancelación al presionar Enter

### ✅ Confirmación de Lectura
- `read_message` marca mensaje como leído en BD
- Notificación al remitente
- Tick ✔️✔️ en interfaz
- Timestamp de lectura

### ✅ Presencia y Estado
```
🟢 ONLINE              - Usuario activo
🟡 AWAY               - Usuario inactivo >5 min
🔴 OFFLINE            - Usuario desconectado
🚫 DND                - No molestar
```

#### Eventos de Presencia
```
SET_PRESENCE           - Establecer estado
GET_PRESENCE          - Obtener estado de usuario
GET_ALL_PRESENCE      - Obtener todos online
WATCH_USER            - Observar cambios de presencia
UNWATCH_USER          - Dejar de observar
IDLE                  - Marcar como inactivo
ACTIVE                - Marcar como activo
```

### ✅ Llamadas de Voz/Video
```
📞 CALL_INITIATE      - Iniciar llamada
✅ CALL_ACCEPT        - Aceptar llamada
❌ CALL_REJECT        - Rechazar llamada
☎️  CALL_END          - Terminar llamada
```

Propiedades:
- Type: voice, video
- Duration tracking
- Caller/Receiver info
- Rejection reasons

## 📁 Estructura de Archivos

```
socket_events/
├── __init__.py              # Inicialización
├── chat_events.py           # Chat en tiempo real
└── presence_events.py       # Presencia y estado

config/
└── socketio_config.py       # Configuración

static/js/
└── socket_client.js         # Cliente JavaScript
```

## 🔧 Configuración

### Variables de Entorno
```bash
# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://nexus.app

# Timeouts
SESSION_TIMEOUT=3600         # 1 hora
PING_TIMEOUT=60              # 60 segundos
PING_INTERVAL=25             # 25 segundos

# Logging
SOCKETIO_LOGGER_ENABLED=False
SOCKETIO_LOGGER_LEVEL=WARNING
ENGINEIO_LOGGER_ENABLED=False
```

### Rate Limiting
```python
RATE_LIMIT = {
    "messages": {"limit": 100, "window": 60},   # 100 msgs/min
    "typing": {"limit": 10, "window": 1},      # 10 events/seg
    "calls": {"limit": 5, "window": 60}        # 5 calls/min
}
```

## 💻 Uso en Frontend

### Inicializar
```javascript
// Conectar
chatClient.connect();

// Unirse a conversación
chatClient.joinConversation('gxbriel_exe');

// Configurar handlers
chatClient.onMessage('new_message', (msg) => {
  console.log('Nuevo mensaje:', msg);
  displayMessage(msg);
});
```

### Enviar Mensaje
```javascript
chatClient.sendMessage('Hola! ¿Cómo estás?', toUserId);
```

### Indicador de Escritura
```javascript
// En el input del mensaje
input.addEventListener('input', () => {
  chatClient.startTyping(toUserId);
});

// Handler para mostrar
chatClient.onMessage('typing', (username) => {
  showTypingDots(username);
});
```

### Marcar como Leído
```javascript
chatClient.markMessageRead(messageId);
```

### Presencia
```javascript
// Establecer estado
chatClient.setPresence('online', 'mobile');

// Obtener estado de usuario
chatClient.getPresence(userId);

// Observar cambios
chatClient.watchUser(userId);
chatClient.onPresence('update', (data) => {
  updateUserBadge(data.username, data.status);
});
```

### Llamadas
```javascript
// Iniciar llamada
chatClient.initiateCall(toUserId, 'video');

// Aceptar
chatClient.acceptCall(fromUserId);

// Rechazar
chatClient.rejectCall(fromUserId, 'ocupado');

// Terminar
chatClient.endCall(otherUserId, durationSeconds);
```

## 🗄️ Base de Datos

Colecciones utilizadas:
```python
Message(
    id, from_user_id, to_user_id, content,
    msg_type, is_read, created_at
)

Notification(
    id, user_id, from_user_id, type,
    is_read, created_at
)
```

## 🔐 Seguridad

### Autenticación
- Validación de sesión en cada evento
- Verificación de permisos
- No autenticar = evento rechazado

### Validación
- Límite de caracteres por mensaje (500)
- Rate limiting por usuario
- Sanitización de contenido

### Privacidad
- Solo 2 usuarios por sala
- Mensajes privados
- No broadcast de datos sensibles

## 📊 Eventos y Rooms

### Rooms
```
chat_user1_user2     # Conversación 1-a-1
presence_userId      # Presencia del usuario
```

### Broadcast vs Room
```javascript
// A todos
emit('event', data, broadcast=True)

// Solo a la sala
emit('event', data, room=room)

// Excepto al remitente
emit('event', data, skip_sid=request.sid)
```

## 📈 Métricas y Monitoreo

### Logs
```
✅ User connected via WebSocket
📨 Message sent from X to Y
✏️  User X is typing
👤 User X set presence: online (mobile)
📞 Call initiated by X to Y (type: video)
```

### Debugging
```javascript
// Socket.IO logger
chatClient.socket.on('*', (event, ...args) => {
  console.log('Event:', event, 'Args:', args);
});
```

## 🚀 Próximas Mejoras

### Fase 5 - Optimizaciones
- [ ] Compresión de mensajes
- [ ] Caché de últimos mensajes
- [ ] Histórico infinito (lazy loading)
- [ ] Búsqueda en conversaciones

### Fase 6 - Multimedia
- [ ] Upload de archivos en tiempo real
- [ ] Compartir pantalla
- [ ] Filtros de video
- [ ] Grabación de llamadas

## 🔗 Ejemplo de Integración

```html
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
  <script src="/static/js/socket_client.js"></script>
</head>
<body>
  <div id="chat-container">
    <div id="messages"></div>
    <input id="message-input" type="text" placeholder="Escribe un mensaje...">
    <button id="send-btn">Enviar</button>
  </div>

  <script>
    // Inicializar
    chatClient.connect();
    chatClient.joinConversation('gxbriel_exe');

    // Handlers
    chatClient.onMessage('new_message', (msg) => {
      const div = document.createElement('div');
      div.textContent = `${msg.from}: ${msg.content}`;
      document.getElementById('messages').appendChild(div);
    });

    // Enviar
    document.getElementById('send-btn').onclick = () => {
      const input = document.getElementById('message-input');
      chatClient.sendMessage(input.value, toUserId);
      input.value = '';
    };

    // Indicador de escritura
    document.getElementById('message-input').addEventListener('input', () => {
      chatClient.startTyping(toUserId);
    });

    chatClient.onMessage('typing', (username) => {
      console.log(`${username} está escribiendo...`);
    });
  </script>
</body>
</html>
```
