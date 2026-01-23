"""
Rutas de autenticación
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config.database import get_mysql_db
from app.models import Usuario
from app.schemas.auth import LoginRequest, LoginResponse, UsuarioResponse
from app.utils.auth import crear_access_token, get_current_active_user

router = APIRouter(prefix="/api/auth", tags=["autenticación"])


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_mysql_db)
):
    """
    Login de usuario

    - **username**: Nombre de usuario
    - **password**: Contraseña

    Returns:
    - Token JWT y datos del usuario
    """
    # Buscar usuario
    usuario = db.query(Usuario).filter(Usuario.username == request.username).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    # Verificar password
    if not usuario.verificar_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    # Verificar que esté activo
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo. Contacte al administrador",
        )

    # Actualizar último login
    usuario.ultimo_login = datetime.utcnow()
    db.commit()

    # Crear token
    access_token = crear_access_token(data={"sub": usuario.username})

    # Preparar response
    usuario_response = UsuarioResponse(
        id=usuario.id,
        username=usuario.username,
        email=usuario.email,
        nombre_completo=usuario.nombre_completo,
        cliente_id=usuario.cliente_id,
        cliente_nombre=usuario.cliente.nombre,
        es_admin=usuario.es_admin,
        puede_procesar=usuario.puede_procesar,
        puede_validar=usuario.puede_validar,
        ultimo_login=usuario.ultimo_login
    )

    return LoginResponse(
        access_token=access_token,
        usuario=usuario_response
    )


@router.get("/me", response_model=UsuarioResponse)
def get_me(
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_mysql_db)
):
    """
    Obtiene información del usuario autenticado
    """
    # Refrescar datos del cliente
    db.refresh(current_user)

    return UsuarioResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        nombre_completo=current_user.nombre_completo,
        cliente_id=current_user.cliente_id,
        cliente_nombre=current_user.cliente.nombre,
        es_admin=current_user.es_admin,
        puede_procesar=current_user.puede_procesar,
        puede_validar=current_user.puede_validar,
        ultimo_login=current_user.ultimo_login
    )


@router.post("/logout")
def logout(
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Logout (el cliente debe eliminar el token)
    """
    return {"mensaje": "Logout exitoso"}
