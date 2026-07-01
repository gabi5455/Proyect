# Fase 3 - Red Social Avanzada

## Características Implementadas

### ✅ Reacciones con Emojis
- Emojis permitidos: ❤️ 😂 😮 😢 😠 👍 🔥
- Endpoint: `POST /posts/<id>/react`
- JSON: `{"emoji": "❤️"}`
- Notificaciones automáticas

### ✅ Hashtags y Trending
- Extracción automática de #hashtags
- Contador de uso
- Endpoint: `GET /posts/trending`
- Búsqueda: `GET /posts/search?q=#python`

### ✅ Menciones (@usuario)
- Extracción automática de @menciones
- Notificaciones a usuarios mencionados
- Compatible en posts y comentarios

### ✅ Guardar Posts
- Endpoint: `POST /posts/<id>/save`
- Ver guardados: `GET /posts/saved`
- Relación many-to-many

### ✅ Compartir Posts (Retweet)
- Endpoint: `POST /posts/<id>/share`
- Crea nuevo post con referencia
- Notificación al autor original

### ✅ API REST Completa
- `GET /api/users/<username>`
- `GET /api/users/<username>/posts`
- `GET /api/posts/<id>`
- `GET /api/posts/<id>/comments`
- `GET /api/search/users?q=...`
- `GET /api/search/posts?q=...`
- `GET /api/me` (JWT)
- `POST /api/posts` (JWT)

## Base de Datos Mejorada

```sql
Reaction (user, post, emoji)        -- Reacciones
Hashtag (tag, usage_count)          -- Trending
SavedPost (user, post)              -- Guardados
Post (updated_at, is_deleted)       -- Soft delete
Comment (is_deleted)                -- Soft delete
Notification (types: mention, share, reaction)
```

## Ejemplos de Uso

### Crear Post con Hashtags y Menciones
```
POST /posts/create
- content: "Hola @gxbriel_exe, este es un #python post!"
- image_file: (optional)

Resultado:
- Hashtag #python creado y contador +1
- Notificación enviada a @gxbriel_exe
```

### Reaccionar a Post
```
POST /api/posts/123/react
Content-Type: application/json
{"emoji": "❤️"}

Resultado:
- Reacción creada/eliminada
- Notificación al autor (si no existe)
```

### Búsqueda de Trending
```
GET /api/posts/trending

Resultado:
[
  {"tag": "#python", "usage_count": 150},
  {"tag": "#web", "usage_count": 98}
]
```

### API - Obtener Posts de Usuario
```
GET /api/users/gxbriel_exe/posts?page=1

Resultado:
{
  "posts": [
    {
      "id": 1,
      "content": "...",
      "likes": 5,
      "comments": 2,
      "reactions": {"❤️": 3, "😂": 1},
      "created_at": "2024-01-15T10:30:00"
    }
  ],
  "total": 45,
  "pages": 3
}
```

## Próximas Fases

### Fase 4 - Chat en Tiempo Real
- WebSockets para mensajes en vivo
- Indicador "escribiendo..."
- Confirmación de lectura
- Tipeos múltiples

### Fase 5 - Administración Avanzada
- Moderadores
- Sistema de reportes
- Estadísticas detalladas
- Acciones en masa

### Fase 6 - Producción
- Docker & Docker Compose
- Nginx reverse proxy
- HTTPS/SSL
- Deployment en Render/Railway
