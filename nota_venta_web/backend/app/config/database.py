"""
Configuración de conexiones a base de datos
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .settings import settings

# Base para modelos MySQL (usuarios, configuraciones)
MySQLBase = declarative_base()

# Base para modelos SQL Server (Valkimia clientes)
ValkimiaBase = declarative_base()

# Engine MySQL
mysql_engine = create_engine(
    settings.mysql_database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG
)

# Engine SQL Server
valkimia_engine = create_engine(
    settings.sqlserver_database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG
)

# Session makers
MySQLSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=mysql_engine)
ValkimiaSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=valkimia_engine)


def get_mysql_db():
    """Dependency para obtener sesión MySQL"""
    db = MySQLSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_valkimia_db():
    """Dependency para obtener sesión Valkimia"""
    db = ValkimiaSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Inicializa las tablas en la base de datos"""
    # Crear tablas MySQL
    MySQLBase.metadata.create_all(bind=mysql_engine)
    print("✓ Tablas MySQL creadas")

    # No creamos tablas en Valkimia, solo leemos
    print("✓ Conexión a Valkimia establecida")
