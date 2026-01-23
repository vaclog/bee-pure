"""
Modelo de Usuario
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from passlib.context import CryptContext
from app.config.database import MySQLBase

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Usuario(MySQLBase):
    """
    Tabla de usuarios del sistema
    """
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    nombre_completo = Column(String(255))
    activo = Column(Boolean, default=True, nullable=False)

    # Relación con cliente
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    cliente = relationship("Cliente", back_populates="usuarios")

    # Permisos
    es_admin = Column(Boolean, default=False)
    puede_procesar = Column(Boolean, default=True)
    puede_validar = Column(Boolean, default=True)

    # Timestamps
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())
    ultimo_login = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<Usuario {self.username}>"

    def verificar_password(self, password: str) -> bool:
        """Verifica si el password es correcto"""
        return pwd_context.verify(password, self.hashed_password)

    @staticmethod
    def hash_password(password: str) -> str:
        """Genera hash del password"""
        return pwd_context.hash(password)

    def set_password(self, password: str):
        """Establece el password del usuario"""
        self.hashed_password = self.hash_password(password)
