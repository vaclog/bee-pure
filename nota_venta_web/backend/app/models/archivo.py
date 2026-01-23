"""
Modelo de Archivo procesado
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from app.config.database import MySQLBase


class ArchivoEstado(PyEnum):
    """Estados del archivo"""
    SUBIDO = "subido"
    VALIDANDO = "validando"
    VALIDACION_OK = "validacion_ok"
    VALIDACION_ERROR = "validacion_error"
    PROCESANDO = "procesando"
    PROCESADO_OK = "procesado_ok"
    PROCESADO_ERROR = "procesado_error"


class Archivo(MySQLBase):
    """
    Tabla de archivos procesados
    """
    __tablename__ = "archivos"

    id = Column(Integer, primary_key=True, index=True)

    # Información del archivo
    nombre_original = Column(String(255), nullable=False)
    nombre_almacenado = Column(String(255), nullable=False)
    ruta_archivo = Column(String(500), nullable=False)
    tamano_bytes = Column(Integer)

    # Estado
    estado = Column(Enum(ArchivoEstado), default=ArchivoEstado.SUBIDO, nullable=False, index=True)
    task_id = Column(String(255), index=True)  # ID de tarea Celery

    # Relaciones
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    cliente = relationship("Cliente", back_populates="archivos")

    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    usuario = relationship("Usuario")

    # Resultados de validación
    validacion_resultado = Column(JSON)  # {"valido": true, "errores": [], "warnings": []}

    # Resultados de procesamiento
    procesamiento_resultado = Column(JSON)  # {"filas_procesadas": 100, "clientes_nuevos": 5, ...}
    csv_generado = Column(String(500))  # Ruta al CSV generado

    # Errores
    error_mensaje = Column(Text)
    error_detalle = Column(Text)

    # Estadísticas
    total_filas = Column(Integer, default=0)
    filas_procesadas = Column(Integer, default=0)
    clientes_nuevos = Column(Integer, default=0)
    combos_expandidos = Column(Integer, default=0)

    # Timestamps
    fecha_subida = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    fecha_validacion = Column(DateTime(timezone=True))
    fecha_procesamiento = Column(DateTime(timezone=True))
    fecha_finalizacion = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<Archivo {self.nombre_original} ({self.estado.value})>"
