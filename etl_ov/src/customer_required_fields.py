CUSTOMER_REQUIRED_CANONICAL_FIELDS = (
    "codigo",
    "nombre",
    "direccion",
    "localidad",
    "provincia",
    "codigo_postal",
)

CUSTOMER_REQUIRED_FIELD_ALIASES = {
    "codigo": {"backend": "codigo", "excel": "codigo", "etl": "cliente_id"},
    "nombre": {"backend": "nombre", "excel": "nombre", "etl": "nombre"},
    "direccion": {"backend": "direccion", "excel": "direccion", "etl": "direccion"},
    "localidad": {"backend": "localidad", "excel": "localidad", "etl": "localidad"},
    "provincia": {"backend": "provincia", "excel": "provincia", "etl": "provincia"},
    "codigo_postal": {"backend": "cp", "excel": "cp", "etl": "codigo_postal"},
}

CUSTOMER_REQUIRED_BACKEND_FIELDS = tuple(
    CUSTOMER_REQUIRED_FIELD_ALIASES[field]["backend"]
    for field in CUSTOMER_REQUIRED_CANONICAL_FIELDS
)

CUSTOMER_REQUIRED_EXCEL_FIELDS = tuple(
    CUSTOMER_REQUIRED_FIELD_ALIASES[field]["excel"]
    for field in CUSTOMER_REQUIRED_CANONICAL_FIELDS
)

CUSTOMER_REQUIRED_ETL_FIELDS = tuple(
    CUSTOMER_REQUIRED_FIELD_ALIASES[field]["etl"]
    for field in CUSTOMER_REQUIRED_CANONICAL_FIELDS
)


def clean_required_customer_value(value):
    if value is None:
        return ""
    return str(value).strip()


def missing_required_customer_fields(data, field_names):
    return [
        field_name
        for field_name in field_names
        if not clean_required_customer_value((data or {}).get(field_name))
    ]
