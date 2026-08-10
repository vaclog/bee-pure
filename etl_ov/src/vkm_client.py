from datetime import datetime
import logging
import re


INTENTIDAD_TABLE = "[VKM_Interfaz_Prod].[dbo].[IntEntidad]"
INTENTIDAD_COLUMNS = (
    "INEntId",
    "INEntIdRel",
    "INEntOper",
    "INEntNombre",
    "INEntDep",
    "INEntDest",
    "INEntOrig",
    "INEntDir",
    "INEntPuerta",
    "INEntLclId",
    "INEntLclNom",
    "INEntPrvId",
    "INEntPrvNom",
    "INEntPaId",
    "INEntPaNom",
    "INEntCP",
    "INEntLaCoord",
    "INEntLoCoord",
    "INEntZona",
    "INEntSZona",
    "INEntTDI",
    "INEntNTdi",
    "INEntDvPrv",
    "INEntDPPass",
    "INEEst",
    "INEntUsuReg",
    "INEntFecReg",
    "INEntAgc",
    "INEntIVA",
    "INEBlq",
    "INEntWMSAct",
    "INEntTran",
    "INEntPrioridad",
    "INEntObs",
    "INEntLogE",
)


logger = logging.getLogger("etl_ov")


def clean_vkm_text(value):
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    text = re.sub(r"[^A-Za-z0-9\s.,;:!#&()-]", "", text)
    return text.replace("'", "").replace('"', "")


def truncate_vkm_text(value, length):
    return clean_vkm_text(value)[:length]


class VkmClient:
    def __init__(self, config, dry_run=True):
        self.config = config
        self.dry_run = dry_run
        self.connection = None

    def connect(self):
        if self.dry_run:
            return None

        missing = [
            name
            for name, value in {
                "VKM_SQLSERVER_HOST": self.config.host,
                "VKM_SQLSERVER_DATABASE": self.config.database,
                "VKM_SQLSERVER_USER": self.config.user,
                "VKM_SQLSERVER_PASSWORD": self.config.password,
                "VKM_SQLSERVER_DRIVER": self.config.driver,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError("Faltan variables VKM: " + ", ".join(missing))

        try:
            import pyodbc
        except ImportError as exc:
            raise RuntimeError("pyodbc no esta instalado.") from exc

        connection_string = (
            f"DRIVER={{{self.config.driver}}};"
            f"SERVER=tcp:{self.config.host},{self.config.port};"
            f"DATABASE={self.config.database};"
            f"UID={self.config.user};"
            f"PWD={self.config.password}"
        )
        self.connection = pyodbc.connect(connection_string)
        return self.connection

    def _ensure_connection(self):
        if self.connection is None:
            raise RuntimeError("No hay conexion VKM activa. Ejecute connect() primero.")
        return self.connection

    def _resolve_vkm_cuenta_id(self, row=None):
        row = row or {}
        vkm_cuenta_id = truncate_vkm_text(row.get("vkm_cuenta_id") or self.config.cuenta_id, 20)
        if not vkm_cuenta_id:
            raise RuntimeError("vkm_cuenta_id es requerido en la fila o VKM_CUENTA_ID debe estar configurado.")
        return vkm_cuenta_id

    def customer_exists(self, cliente_id, row=None):
        if self.dry_run:
            return False

        vkm_cuenta_id = self._resolve_vkm_cuenta_id(row)
        query = """
            SELECT TOP 1 ENT.EntID
            FROM ENT
            JOIN ENT6 ON ENT6.EntID = ENT.EntID
            WHERE ENT.EntEntIDC = ?
              AND ENT6.EntLogID = ?
        """
        with self._ensure_connection().cursor() as cursor:
            cursor.execute(
                query,
                truncate_vkm_text(cliente_id, 20),
                vkm_cuenta_id,
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return row[0]

    def intentidad_status(self, cliente_id, row=None):
        if self.dry_run:
            return None

        vkm_cuenta_id = self._resolve_vkm_cuenta_id(row)
        query = f"""
            SELECT TOP 1 INEEst
            FROM {INTENTIDAD_TABLE}
            WHERE INEntId = ?
              AND INEntLogE = ?
            ORDER BY INEntFecReg DESC
        """
        with self._ensure_connection().cursor() as cursor:
            cursor.execute(
                query,
                truncate_vkm_text(cliente_id, 20),
                vkm_cuenta_id,
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return str(row[0]).strip()

    def verify_queued_customer(self, row):
        cliente_id = truncate_vkm_text(row.get("cliente_id") or row.get("customer_code"), 20)
        status = self.intentidad_status(cliente_id, row)
        if status == "2":
            existing_id = self.customer_exists(cliente_id, row)
            codigo_valkimia = self._normalize_codigo_valkimia(existing_id)
            if codigo_valkimia:
                return {
                    "cliente_id": cliente_id,
                    "customer_code": cliente_id,
                    "status": "confirmed",
                    "ineest": status,
                    "vkm_id": existing_id,
                    "codigo_valkimia": codigo_valkimia,
                }
            logger.warning(
                "INEEst=2 sin ENT.EntID resoluble cliente_id=%s vkm_cuenta_id=%s",
                cliente_id,
                self._resolve_vkm_cuenta_id(row),
            )
        return {"cliente_id": cliente_id, "customer_code": cliente_id, "status": "queued", "ineest": status}

    def create_or_confirm_customer(self, row):
        if self.dry_run:
            return {"cliente_id": row["cliente_id"], "status": "dry_run"}

        cliente_id = truncate_vkm_text(row.get("cliente_id"), 20)
        vkm_cuenta_id = self._resolve_vkm_cuenta_id(row)
        existing_id = self.customer_exists(cliente_id, row)
        if existing_id:
            return {
                "cliente_id": cliente_id,
                "customer_code": cliente_id,
                "status": "confirmed",
                "vkm_id": existing_id,
                "codigo_valkimia": self._normalize_codigo_valkimia(existing_id),
            }

        values = self._build_intentidad_values(row, vkm_cuenta_id)
        placeholders = ", ".join("?" for _ in INTENTIDAD_COLUMNS)
        columns = ", ".join(f"[{column}]" for column in INTENTIDAD_COLUMNS)
        query = f"INSERT INTO {INTENTIDAD_TABLE} ({columns}) VALUES ({placeholders})"
        with self._ensure_connection().cursor() as cursor:
            cursor.execute(query, *values)
        self.connection.commit()
        return {"cliente_id": cliente_id, "status": "queued"}

    def _normalize_codigo_valkimia(self, value):
        if value is None:
            return ""
        return str(value).strip()

    def _build_intentidad_values(self, row, vkm_cuenta_id=None):
        cliente_id = truncate_vkm_text(row.get("cliente_id"), 20)
        vkm_cuenta_id = vkm_cuenta_id or self._resolve_vkm_cuenta_id(row)
        return (
            cliente_id,
            None,
            0,
            truncate_vkm_text(row.get("nombre"), 35),
            "N",
            "N",
            "S",
            truncate_vkm_text(row.get("direccion"), 100),
            None,
            None,
            truncate_vkm_text(row.get("localidad"), 100),
            None,
            truncate_vkm_text(row.get("provincia"), 100),
            None,
            None,
            truncate_vkm_text(row.get("codigo_postal"), 10),
            None,
            None,
            None,
            None,
            80,
            truncate_vkm_text(cliente_id, 11),
            None,
            None,
            "1",
            "vaclog",
            datetime.now(),
            None,
            "1",
            None,
            None,
            None,
            None,
            truncate_vkm_text(row.get("observacion"), 1024),
            truncate_vkm_text(vkm_cuenta_id, 20),
        )

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
