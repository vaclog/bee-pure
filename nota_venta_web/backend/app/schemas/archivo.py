"""
Schemas para manejo de archivos
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.archivo import ArchivoEstado


class ErrorValidacion(BaseModel):
    """Error de validación"""
    fila: Optional[int]
    columna: Optional[str]
    tipo: str
    mensaje: str


class WarningValidacion(BaseModel):
    """Warning de validación"""
    fila: Optional[int]
    mensaje: str


class EstadisticasPreview(BaseModel):
    """Estadísticas del preview"""
    total_filas: int
    clientes_nuevos: int
    combos_detectados: int
    skus_unicos: int


class ArchivoUploadResponse(BaseModel):
    """Response al subir un archivo"""
    id: int
    nombre_original: str
    nombre_almacenado: str
    tamano_bytes: int
    estado: ArchivoEstado
    fecha_subida: datetime
    mensaje: str = "Archivo subido correctamente"

    class Config:
        from_attributes = True


class ValidacionResponse(BaseModel):
    """Response de validación de archivo"""
    archivo_id: int
    valido: bool
    errores: List[ErrorValidacion] = []
    warnings: List[WarningValidacion] = []
    preview: List[Dict[str, Any]] = []
    estadisticas: Optional[EstadisticasPreview]
    mensaje: str


class ProcesamientoStatus(BaseModel):
    """Estado del procesamiento"""
    task_id: str
    estado: ArchivoEstado
    progreso: int  # 0-100
    mensaje: str
    filas_procesadas: Optional[int]
    total_filas: Optional[int]


class ProcesamientoResponse(BaseModel):
    """Response final del procesamiento"""
    archivo_id: int
    estado: ArchivoEstado
    filas_procesadas: int
    clientes_nuevos: int
    combos_expandidos: int
    csv_generado: Optional[str]
    errores: List[str] = []
    warnings: List[str] = []
    fecha_finalizacion: datetime
    mensaje: str

    class Config:
        from_attributes = True


class ArchivoHistorial(BaseModel):
    """Archivo en el historial"""
    id: int
    nombre_original: str
    estado: ArchivoEstado
    total_filas: int
    filas_procesadas: int
    clientes_nuevos: int
    combos_expandidos: int
    fecha_subida: datetime
    fecha_finalizacion: Optional[datetime]
    error_mensaje: Optional[str]

    class Config:
        from_attributes = True
