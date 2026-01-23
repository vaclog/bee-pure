"""
Schemas para autenticación
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    """Request para login"""
    username: str
    password: str


class Token(BaseModel):
    """Response con token JWT"""
    access_token: str
    token_type: str = "bearer"


class UsuarioResponse(BaseModel):
    """Response con información del usuario"""
    id: int
    username: str
    email: str
    nombre_completo: Optional[str]
    cliente_id: int
    cliente_nombre: str
    es_admin: bool
    puede_procesar: bool
    puede_validar: bool
    ultimo_login: Optional[datetime]

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Response completo de login"""
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse
