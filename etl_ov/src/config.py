from dataclasses import dataclass
import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency optional for dry validation
    load_dotenv = None


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class DepositoApiConfig:
    base_url: str
    token: str


@dataclass(frozen=True)
class VkmConfig:
    host: str
    port: str
    database: str
    user: str
    password: str
    driver: str
    cuenta_id: str


@dataclass(frozen=True)
class Settings:
    deposito_api: DepositoApiConfig
    vkm: VkmConfig
    new_customer_path: str
    dry_run: bool
    log_level: str


def load_settings(env_path=None):
    if load_dotenv:
        load_dotenv(dotenv_path=env_path, override=False)

    return Settings(
        deposito_api=DepositoApiConfig(
            base_url=os.getenv("DEPOSITO_API_BASE_URL", "").rstrip("/"),
            token=os.getenv("DEPOSITO_API_TOKEN", ""),
        ),
        vkm=VkmConfig(
            host=os.getenv("VKM_SQLSERVER_HOST", ""),
            port=os.getenv("VKM_SQLSERVER_PORT", "1433"),
            database=os.getenv("VKM_SQLSERVER_DATABASE", ""),
            user=os.getenv("VKM_SQLSERVER_USER", ""),
            password=os.getenv("VKM_SQLSERVER_PASSWORD", ""),
            driver=os.getenv("VKM_SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server"),
            cuenta_id=os.getenv("VKM_CUENTA_ID", ""),
        ),
        new_customer_path=os.getenv("ETL_OV_NEW_CUSTOMER_PATH", "").strip(),
        dry_run=_env_bool("ETL_OV_DRY_RUN", default=True),
        log_level=os.getenv("ETL_OV_LOG_LEVEL", "INFO").upper(),
    )
