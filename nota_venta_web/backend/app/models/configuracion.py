"""
Modelo de Configuración por Cliente
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import MySQLBase


class ConfiguracionCliente(MySQLBase):
    """
    Configuración de mapeo y rutas por cliente
    """
    __tablename__ = "configuraciones_cliente"

    id = Column(Integer, primary_key=True, index=True)

    # Relación con cliente
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    cliente = relationship("Cliente", back_populates="configuraciones")

    # Versión de configuración (para permitir cambios históricos)
    version = Column(Integer, default=1, nullable=False)
    activa = Column(Boolean, default=True, nullable=False)

    # Mapeo de columnas Excel
    mapeo_excel = Column(JSON, nullable=False)
    """
    Ejemplo:
    {
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
        "data_start_row": 3,
        "validacion_header": "Razon Social"
    }
    """

    # Ruta al archivo master de combos
    master_file = Column(String(500), nullable=False)

    # Rutas de directorios
    rutas = Column(JSON, nullable=False)
    """
    Ejemplo:
    {
        "to_process": "C:/prg/bee-pure/microbel_nota_venta/to_process",
        "import_path": "C:/prg/bee-pure/microbel_nota_venta/import_to_valkimia",
        "processed_path": "C:/prg/bee-pure/microbel_nota_venta/processed",
        "new_customer_path": "C:/prg/bee-pure/microbel_nota_venta/new_customer",
        "combos_path": "C:/prg/bee-pure/microbel_nota_venta/combos"
    }
    """

    # Configuración de notificaciones
    notificaciones = Column(JSON)
    """
    Ejemplo:
    {
        "email_destino": "cliente@example.com",
        "notificar_validacion": true,
        "notificar_procesamiento": true,
        "notificar_errores": true
    }
    """

    # Descripción
    descripcion = Column(Text)

    # Timestamps
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())
    creado_por = Column(String(100))

    def __repr__(self):
        return f"<ConfiguracionCliente cliente={self.cliente_id} version={self.version}>"
