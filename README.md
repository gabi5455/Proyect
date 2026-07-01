# Nexus - Red Social Moderna

## 📱 Descripción

Nexus es una red social moderna construida con Flask, SQLAlchemy y PostgreSQL. Ofrece características como feed, mensajes privados, historias, reels, notificaciones y un panel de administración.

## 🚀 Características Actuales

- ✅ Autenticación de usuarios
- ✅ Feed personalizado
- ✅ Posts con imágenes
- ✅ Sistema de likes y comentarios
- ✅ Seguimiento de usuarios
- ✅ Mensajes privados (texto y fotos)
- ✅ Historias (24 horas)
- ✅ Reels (videos cortos)
- ✅ Notificaciones en tiempo real
- ✅ Panel de administración

## 📋 Requisitos

- Python 3.9+
- PostgreSQL 12+
- pip

## 🔧 Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/gabi5455/Proyect.git
cd Proyect
```

2. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\\Scripts\\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

5. Ejecutar la aplicación:
```bash
python app.py
```

La aplicación estará disponible en `http://localhost:3000`

## 📁 Estructura del Proyecto

```
.
├── app.py                 # Punto de entrada
├── config.py             # Configuración
├── database.py           # Gestión de BD
├── models.py             # Modelos SQLAlchemy
├── utils.py              # Funciones auxiliares
├── routes/               # Blueprints de rutas
│   ├── auth.py
│   ├── main.py
│   ├── posts.py
│   ├── profiles.py
│   ├── messages.py
│   ├── stories.py
│   ├── notifications.py
│   ├── reels.py
│   └── owner.py
├── templates/            # Plantillas HTML
├── uploads/              # Archivos subidos
├── requirements.txt
├── .env.example
└── README.md
```

## 🔐 Seguridad

- Contraseñas hasheadas con Werkzeug
- Sesiones seguras con HTTPS en producción
- Validación de tipos de archivo
- Límite de tamaño de upload (50MB)
- Protección contra inyección SQL con SQLAlchemy

## 📝 Plan de Desarrollo

### Fase 1 ✅ - Refactorización (actual)
- Modularización de código
- Estructura profesional
- SQLAlchemy ORM

### Fase 2 - Autenticación Avanzada
- Verificación por correo
- Recuperación de contraseña
- OAuth (Google)
- JWT para API
- Rate limiting

### Fase 3 - Red Social
- Reacciones (emojis)
- Compartir publicaciones
- Hashtags y búsqueda
- Menciones
- Guardar publicaciones

### Fase 4 - Chat en Tiempo Real
- WebSockets
- Indicador "escribiendo"
- Confirmación de lectura

### Fase 5 - Administración
- Moderadores
- Sistema de reportes
- Estadísticas avanzadas

### Fase 6 - Producción
- Docker & Docker Compose
- Nginx
- HTTPS
- Deployment

## 📄 Licencia

MIT License

## 👤 Autor

Gabriel (gxbriel_exe)
