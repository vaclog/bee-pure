from dataclasses import dataclass
import csv
from datetime import datetime
from pathlib import Path


REQUIRED_HEADERS = (
    "cliente_id",
    "nombre",
    "direccion",
    "localidad",
    "provincia",
    "codigo_postal",
)

BACKUP_HEADERS = (
    "client_id",
    "cliente_id",
    "nombre",
    "direccion",
    "localidad",
    "provincia",
    "codigo_postal",
    "observacion",
    "tipo",
    "numero_documento",
    "vkm_cuenta_id",
)


@dataclass(frozen=True)
class RowError:
    row_number: int
    message: str


@dataclass(frozen=True)
class CsvReadResult:
    rows: list
    errors: list
    headers: list

    @property
    def is_valid(self):
        return not self.errors


def _clean(value):
    if value is None:
        return ""
    return str(value).strip()


def _duplicate_customer_key(row):
    cliente_id = row.get("cliente_id", "")
    client_id = row.get("client_id", "")
    if client_id:
        return ("client_id", client_id, cliente_id)

    vkm_cuenta_id = row.get("vkm_cuenta_id", "")
    if vkm_cuenta_id:
        return ("vkm_cuenta_id", vkm_cuenta_id, cliente_id)

    return ("cliente_id", cliente_id)


def validate_customer_rows(raw_rows, headers=None):
    headers = list(headers or REQUIRED_HEADERS)
    missing_headers = [header for header in REQUIRED_HEADERS if header not in headers]
    if missing_headers:
        return CsvReadResult(
            rows=[],
            errors=[RowError(1, "Faltan columnas requeridas: " + ", ".join(missing_headers))],
            headers=headers,
        )

    rows = []
    errors = []
    seen_customer_keys = set()

    for row_number, raw_row in enumerate(raw_rows, start=2):
        row = {header: _clean(raw_row.get(header)) for header in headers}
        cliente_id = row.get("cliente_id", "")
        if not cliente_id:
            errors.append(RowError(row_number, "cliente_id vacio."))
        else:
            duplicate_key = _duplicate_customer_key(row)
            if duplicate_key in seen_customer_keys:
                errors.append(RowError(row_number, f"cliente_id duplicado: {cliente_id}."))
            else:
                seen_customer_keys.add(duplicate_key)

        for header in REQUIRED_HEADERS:
            if not row.get(header):
                errors.append(RowError(row_number, f"{header} vacio."))

        rows.append(row)

    if not rows:
        errors.append(RowError(1, "El archivo no contiene filas de datos."))

    return CsvReadResult(rows=rows, errors=errors, headers=headers)


def read_customers_csv(csv_path):
    path = Path(csv_path)
    if not path.exists():
        return CsvReadResult(rows=[], errors=[RowError(0, f"Archivo no encontrado: {path}")], headers=[])
    if not path.is_file():
        return CsvReadResult(rows=[], errors=[RowError(0, f"La ruta no es un archivo: {path}")], headers=[])
    if path.stat().st_size == 0:
        return CsvReadResult(rows=[], errors=[RowError(0, "El archivo esta vacio.")], headers=[])

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=";,") if sample else csv.excel
        reader = csv.DictReader(handle, dialect=dialect)
        headers = [h.strip() for h in (reader.fieldnames or []) if h]

        missing_headers = [header for header in REQUIRED_HEADERS if header not in headers]
        if missing_headers:
            return CsvReadResult(
                rows=[],
                errors=[RowError(1, "Faltan columnas requeridas: " + ", ".join(missing_headers))],
                headers=headers,
            )

        return validate_customer_rows(reader, headers=headers)


def _safe_filename_fragment(value):
    cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in _clean(value))
    return cleaned.strip("_")


def write_customers_backup_csv(output_dir, rows, request_id="", timestamp=None):
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    export_time = timestamp or datetime.now()
    safe_request_id = _safe_filename_fragment(request_id)
    filename = f"clientes_nuevos_{export_time.strftime('%Y%m%d_%H%M%S')}"
    if safe_request_id:
        filename = f"{filename}_{safe_request_id}"
    path = directory / f"{filename}.csv"

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BACKUP_HEADERS, delimiter=";")
        writer.writeheader()
        for raw_row in rows:
            writer.writerow({header: _clean(raw_row.get(header)) for header in BACKUP_HEADERS})

    return path
