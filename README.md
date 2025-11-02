# 🤖 Chatbot - Sistema de Solicitudes de Permisos

Sistema completo de gestión de solicitudes de permisos con chatbot interactivo y panel de administración.

## 🚀 Características

### Chatbot Interactivo

- ✅ Crear nuevas solicitudes de permisos
- 🔍 Consultar estado de solicitudes por número
- 📋 Ver todas las solicitudes por correo electrónico
- 🔄 Menú interactivo después de cada acción
- 💬 Conversación natural y guiada

### Panel de Administración

- 📊 Estadísticas en tiempo real
- 🔎 Búsqueda y filtrado de solicitudes
- ✅ Aprobar/Rechazar solicitudes
- 🔄 Ordenar por cualquier columna
- 📈 Vista completa de la base de datos

## 🛠️ Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
python app.py
```

## 🌐 Uso

### Acceder al Chatbot

Abre tu navegador en: **http://127.0.0.1:5000**

### Acceder al Panel de Administración

Abre tu navegador en: **http://127.0.0.1:5000/admin**

O haz clic en el botón "📊 Admin" en el header del chatbot.

## 💬 Cómo usar el Chatbot

### Opción 1: Crear Nueva Solicitud

1. Escribe tu nombre o elige opción 1
2. Proporciona tu correo electrónico
3. Indica el tipo de permiso (Enfermedad, Personal, Estudio, etc.)
4. Fecha de inicio (formato: AAAA-MM-DD o DD/MM/AAAA)
5. Fecha de fin (formato: AAAA-MM-DD o DD/MM/AAAA)
6. Motivo del permiso
7. Confirma con "si" o cancela con "no"

### Opción 2: Consultar Solicitud

1. Escribe "2" o "consultar"
2. Ingresa el número de solicitud
3. Visualiza todos los detalles

### Opción 3: Ver Todas tus Solicitudes

1. Escribe "3" o "mis solicitudes"
2. Ingresa tu correo electrónico
3. Ve la lista completa de tus solicitudes

### Comandos Especiales

- **"hola"** / **"inicio"** / **"reiniciar"**: Volver al menú principal
- **"1"** / **"nueva"**: Nueva solicitud
- **"2"** / **"consultar"**: Consultar solicitud
- **"3"** / **"mis solicitudes"**: Ver todas las solicitudes
- **"4"** / **"salir"**: Terminar la conversación

## 🎨 Panel de Administración

### Estadísticas

- Total de solicitudes
- Solicitudes pendientes
- Solicitudes aprobadas
- Solicitudes rechazadas

### Funcionalidades

- **Buscar**: Por nombre, correo, tipo o motivo
- **Filtrar**: Por estado (Todas, Pendientes, Aprobadas, Rechazadas)
- **Ordenar**: Click en cualquier columna para ordenar
- **Aprobar/Rechazar**: Botones ✓ y ✗ para cada solicitud
- **Actualizar**: Botón 🔄 para recargar datos

## 📦 Estructura del Proyecto

```
Final/
├── app.py              # Backend Flask
├── index.html          # Interfaz del chatbot
├── admin.html          # Panel de administración
├── requirements.txt    # Dependencias
├── solicitudes.db      # Base de datos SQLite
└── README.md          # Documentación
```

## 🗄️ Base de Datos

La base de datos SQLite (`solicitudes.db`) contiene la tabla `solicitudes` con:

| Campo     | Tipo    | Descripción                           |
| --------- | ------- | ------------------------------------- |
| id        | INTEGER | ID único (autoincremental)            |
| nombre    | TEXT    | Nombre completo                       |
| correo    | TEXT    | Correo electrónico                    |
| tipo      | TEXT    | Tipo de permiso                       |
| inicio    | TEXT    | Fecha de inicio (ISO)                 |
| fin       | TEXT    | Fecha de fin (ISO)                    |
| motivo    | TEXT    | Motivo del permiso                    |
| estado    | TEXT    | Estado (Pendiente/Aprobado/Rechazado) |
| creado_en | TEXT    | Fecha de creación (ISO)               |

## 🔧 Tecnologías Utilizadas

- **Backend**: Flask, SQLite
- **Frontend**: HTML, CSS, JavaScript
- **Librerías**: Flask-CORS, python-dotenv

## 📝 Notas

- El servidor corre en modo debug (no usar en producción)
- Los datos se persisten en `solicitudes.db`
- CORS está habilitado para desarrollo
- Las sesiones se mantienen en memoria (se pierden al reiniciar)

## 🎯 Próximas Mejoras Posibles

- 🔐 Sistema de autenticación
- 📧 Notificaciones por correo
- 📱 Diseño responsive mejorado
- 🌍 Soporte multiidioma
- 📄 Exportar solicitudes a PDF/Excel
- 📅 Calendario de permisos
- 👥 Gestión de usuarios y roles

---

**Desarrollado con ❤️ usando Flask y JavaScript**
