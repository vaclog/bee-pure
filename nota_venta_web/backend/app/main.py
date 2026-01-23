"""
Aplicación principal FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config.settings import settings
from app.config.database import init_db
from app.routes import auth

# Crear directorios necesarios
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.TEMP_DIR, exist_ok=True)

# Crear aplicación
app = FastAPI(
    title="Nota Venta Web API",
    description="API para procesamiento de archivos de notas de venta multi-cliente",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(auth.router)


@app.on_event("startup")
async def startup_event():
    """Evento al iniciar la aplicación"""
    print("🚀 Iniciando Nota Venta Web API...")

    # Inicializar base de datos
    print("📊 Inicializando base de datos...")
    try:
        init_db()
        print("✓ Base de datos inicializada")
    except Exception as e:
        print(f"⚠️  Error al inicializar base de datos: {e}")

    print(f"✓ API corriendo en http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"✓ Documentación en http://{settings.API_HOST}:{settings.API_PORT}/api/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Evento al cerrar la aplicación"""
    print("👋 Cerrando Nota Venta Web API...")


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "nombre": "Nota Venta Web API",
        "version": "1.0.0",
        "estado": "activo",
        "documentacion": "/api/docs"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "estado": "saludable",
        "servicio": "nota-venta-web"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
