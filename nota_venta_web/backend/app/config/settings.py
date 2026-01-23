"""
Configuración de la aplicación cargada desde variables de entorno
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    SECRET_KEY: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # MySQL Database (Usuarios)
    REMITO_DB_HOST: str
    REMITO_DB_DATABASE: str
    REMITO_DB_USER: str
    REMITO_DB_PASSWORD: str
    REMITO_DB_PORT: int = 3308

    # SQL Server Database (Valkimia)
    VKM_DB_HOST: str
    VKM_DB_NAME: str
    VKM_DB_USER: str
    VKM_DB_PASSWORD: str

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # SMTP
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    SENDER_MAIL: str
    EMAIL_ADMIN: str

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    TEMP_DIR: str = "./temp"
    MAX_FILE_SIZE_MB: int = 50

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Convierte CORS_ORIGINS a lista"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def mysql_database_url(self) -> str:
        """URL de conexión MySQL"""
        return f"mysql+pymysql://{self.REMITO_DB_USER}:{self.REMITO_DB_PASSWORD}@{self.REMITO_DB_HOST}:{self.REMITO_DB_PORT}/{self.REMITO_DB_DATABASE}"

    @property
    def sqlserver_database_url(self) -> str:
        """URL de conexión SQL Server"""
        driver = "ODBC Driver 17 for SQL Server"
        return f"mssql+pyodbc://{self.VKM_DB_USER}:{self.VKM_DB_PASSWORD}@{self.VKM_DB_HOST}/{self.VKM_DB_NAME}?driver={driver}"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Instancia global de configuración
settings = Settings()
