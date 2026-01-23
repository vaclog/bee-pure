# Guía de Instalación - Nota Venta Web

## Requisitos Previos

- Python 3.10 o superior
- Node.js 18 o superior
- MySQL 5.7 o superior (para deposito_prod)
- SQL Server (para VKM_Prod)
- Redis (para Celery)

## Instalación Backend

### 1. Crear entorno virtual

```bash
cd nota_venta_web/backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
# Copiar archivo de ejemplo
copy .env.example .env

# Editar .env con tus credenciales
notepad .env
```

### 4. Inicializar base de datos

```bash
python init_db.py
```

Esto creará:
- Tablas necesarias en MySQL (deposito_prod)
- Clientes: Microbel, Amande
- Usuarios de prueba:
  - `admin / admin123` (administrador)
  - `microbel / microbel123`
  - `amande / amande123`

### 5. Iniciar servidor

```bash
# Modo desarrollo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Modo producción
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

La API estará disponible en:
- http://localhost:8000
- Documentación: http://localhost:8000/api/docs

## Instalación Frontend (Próximo paso)

```bash
cd nota_venta_web/frontend
npm install
npm start
```

## Instalación Redis (para Celery)

### Windows
```bash
# Descargar Redis para Windows
# https://github.com/microsoftarchive/redis/releases

# O usar Docker
docker run -d -p 6379:6379 redis:latest
```

### Linux/Mac
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis
```

## Iniciar Worker de Celery

```bash
cd nota_venta_web/backend

# Windows
celery -A app.tasks.celery_tasks worker --loglevel=info --pool=solo

# Linux/Mac
celery -A app.tasks.celery_tasks worker --loglevel=info
```

## Verificar Instalación

### 1. Health Check

```bash
curl http://localhost:8000/api/health
```

Respuesta esperada:
```json
{
  "estado": "saludable",
  "servicio": "nota-venta-web"
}
```

### 2. Login de prueba

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "microbel", "password": "microbel123"}'
```

Respuesta esperada:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "usuario": {
    "id": 1,
    "username": "microbel",
    "cliente_nombre": "Microbel",
    ...
  }
}
```

## Estructura de Directorios

La aplicación creará automáticamente:
- `uploads/` - Archivos subidos
- `temp/` - Archivos temporales durante procesamiento

## Solución de Problemas

### Error: No se puede conectar a MySQL

Verificar:
1. Que MySQL esté corriendo
2. Credenciales en `.env`
3. Puerto 3308 disponible
4. Firewall no bloquea conexión

### Error: No se puede conectar a Redis

```bash
# Verificar que Redis esté corriendo
redis-cli ping
# Debe responder: PONG
```

### Error: Módulo no encontrado

```bash
# Reinstalar dependencias
pip install -r requirements.txt --force-reinstall
```

## Configuración de Producción

### 1. Cambiar contraseñas

Editar `init_db.py` y cambiar contraseñas antes de ejecutar en producción.

### 2. Configurar HTTPS

Usar nginx como reverse proxy:

```nginx
server {
    listen 443 ssl;
    server_name api.notaventa.vaclog.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Usar variables de entorno del sistema

En producción, usar variables de entorno del sistema en lugar de `.env`:

```bash
export JWT_SECRET_KEY="clave-super-secreta-produccion"
export SECRET_KEY="otra-clave-secreta"
# etc...
```

## Próximos Pasos

1. ✅ Backend API funcionando
2. ⏳ Crear frontend React
3. ⏳ Implementar endpoints de upload
4. ⏳ Implementar procesamiento asíncrono
5. ⏳ Agregar WebSockets para tiempo real

## Soporte

Para problemas o preguntas:
- Email: asagula@vaclog.com
- Documentación API: http://localhost:8000/api/docs
