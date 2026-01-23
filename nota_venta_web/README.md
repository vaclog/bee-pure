# Nota Venta Web

Sistema web para procesamiento de archivos de notas de venta multi-cliente.

## Características

- **Multi-cliente**: Cada cliente (Microbel, Amande, BeePure, Habitare, Santia) tiene su propia configuración
- **Validación en tiempo real**: Validación instantánea antes de procesar
- **API REST**: Endpoints para integración con sistemas externos
- **WebSockets**: Actualizaciones en tiempo real del progreso de procesamiento
- **Dashboard**: Historial de archivos procesados y estadísticas

## Stack Tecnológico

### Backend
- **FastAPI** (Python 3.10+)
- **SQLAlchemy** (ORM)
- **Celery + Redis** (tareas asíncronas)
- **WebSockets** (notificaciones tiempo real)
- **JWT** (autenticación)

### Frontend
- **React 18** + TypeScript
- **Material-UI** (componentes)
- **React Query** (estado del servidor)
- **Socket.IO** (WebSockets)
- **Axios** (HTTP client)

### Base de Datos
- **MySQL** (deposito_prod) - Usuarios y configuraciones
- **SQL Server** (VKM_Prod) - Clientes Valkimia

## Estructura del Proyecto

```
nota_venta_web/
├── backend/
│   ├── app/
│   │   ├── config/
│   │   │   ├── database.py       # Configuración de BD
│   │   │   └── settings.py       # Variables de entorno
│   │   ├── models/
│   │   │   ├── cliente.py        # Modelo de cliente
│   │   │   ├── usuario.py        # Modelo de usuario
│   │   │   ├── archivo.py        # Modelo de archivo procesado
│   │   │   └── configuracion.py  # Configuración de mapeo
│   │   ├── routes/
│   │   │   ├── auth.py           # Login/logout
│   │   │   ├── files.py          # Upload/validación
│   │   │   └── dashboard.py      # Estadísticas
│   │   ├── services/
│   │   │   ├── validator.py      # Validación de archivos
│   │   │   ├── processor.py      # Procesamiento de archivos
│   │   │   └── mapper.py         # Mapeo dinámico
│   │   ├── tasks/
│   │   │   └── celery_tasks.py   # Tareas asíncronas
│   │   └── main.py               # Aplicación FastAPI
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FileUpload.tsx
│   │   │   ├── ValidationResults.tsx
│   │   │   └── ProcessingStatus.tsx
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   └── Dashboard.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   └── App.tsx
│   └── package.json
├── docker-compose.yml
└── README.md
```

## Instalación

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus credenciales
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm start
```

## Uso

### 1. Login
Accede con tu usuario de cliente (microbel, amande, etc.)

### 2. Subir Archivo
- Arrastra tu archivo .xlsx al área de carga
- El sistema valida inmediatamente el formato
- Revisa preview y posibles errores/warnings

### 3. Procesar
- Si la validación es correcta, haz clic en "Procesar"
- Verás el progreso en tiempo real
- Al finalizar, descarga el CSV generado

### 4. API REST

```bash
# Autenticación
POST /api/auth/login
{
  "username": "microbel",
  "password": "****"
}

# Upload archivo
POST /api/files/upload
Headers: Authorization: Bearer {token}
Body: multipart/form-data
  file: archivo.xlsx

# Validar archivo
POST /api/files/validate/{file_id}

# Procesar archivo
POST /api/files/process/{file_id}

# Estado de procesamiento
GET /api/files/status/{task_id}
```

## Configuración por Cliente

Cada cliente tiene su configuración en la base de datos:

```json
{
  "cliente_id": 1,
  "nombre": "microbel",
  "mapeo_excel": {
    "columnas": {
      "nombre": "A",
      "documento": "B",
      "provincia": "C",
      "cliente_id": "D",
      "direccion": "E",
      "fecha": "F",
      "numero_factura": "G",
      "sku": "H",
      "descripcion": "I",
      "cantidad": "J",
      "tipo": "K",
      "observacion": ["L", "M", "N", "O"],
      "codigo_postal": "P"
    },
    "header_row": 1,
    "data_start_row": 3
  },
  "master_file": "C:/prg/bee-pure/microbel_nota_venta/masters/Combos.xlsx",
  "rutas": {
    "import_path": "C:/prg/bee-pure/microbel_nota_venta/import_to_valkimia",
    "processed_path": "C:/prg/bee-pure/microbel_nota_venta/processed"
  }
}
```

## Licencia

Propietario - VACLOG
