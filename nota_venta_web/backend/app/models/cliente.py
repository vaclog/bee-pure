"""
Modelo de Cliente
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import MySQLBase


class Cliente(MySQLBase):
    """
    Tabla de clientes (microbel, amande, beepure, etc.)
    """
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False, index=True)
    codigo = Column(String(50), unique=True, nullable=False)  # microbel, amande, etc.
    email_notificacion = Column(String(255))
    activo = Column(Boolean, default=True, nullable=False)

    # Timestamps
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    usuarios = relationship("Usuario", back_populates="cliente")
    configuraciones = relationship("ConfiguracionCliente", back_populates="cliente")
    archivos = relationship("Archivo", back_populates="cliente")

    def __repr__(self):
        return f"<Cliente {self.codigo}>"
