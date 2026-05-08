import argparse
from dataclasses import dataclass
import logging
import sys

from .config import load_settings
from .csv_reader import read_customers_csv, validate_customer_rows, write_customers_backup_csv
from .deposito_api_client import DepositoApiClient
from .logging_config import configure_logging
from .vkm_client import VkmClient


EXIT_SUCCESS = 0
EXIT_FUNCTIONAL_ERROR = 1
EXIT_TECHNICAL_ERROR = 2
EXIT_PARTIAL = 3


@dataclass(frozen=True)
class ProcessingResult:
    ok_count: int
    error_count: int
    errors: list


def determine_dashboard_status(result):
    if result.ok_count > 0 and result.error_count == 0:
        return "confirmed"
    if result.ok_count > 0 and result.error_count > 0:
        return "partial"
    return "error"


def exit_code_for_status(status):
    if status == "confirmed":
        return EXIT_SUCCESS
    if status == "partial":
        return EXIT_PARTIAL
    return EXIT_FUNCTIONAL_ERROR


def process_rows(rows, vkm_client):
    ok_count = 0
    errors = []
    for index, row in enumerate(rows, start=2):
        try:
            vkm_client.create_or_confirm_customer(row)
            ok_count += 1
        except Exception as exc:
            errors.append(f"Fila {index} cliente_id={row.get('cliente_id', '')}: {exc}")
    return ProcessingResult(ok_count=ok_count, error_count=len(errors), errors=errors)


def build_error_detail(errors, limit=20):
    return " | ".join(errors[:limit])


def _log_csv_errors(logger, csv_result):
    for error in csv_result.errors:
        logger.error("CSV fila=%s error=%s", error.row_number, error.message)


def _write_backup_csv_if_enabled(settings, rows, request_id, logger):
    if not settings.new_customer_path:
        logger.info("Salida CSV local de clientes nuevos deshabilitada.")
        return None

    backup_path = write_customers_backup_csv(settings.new_customer_path, rows, request_id=request_id)
    logger.info("CSV local de respaldo generado: %s", backup_path)
    return backup_path


def run_manual_mode(args, settings, dry_run, logger):
    if not args.request_id:
        logger.error("--request-id es requerido cuando se usa --csv-path.")
        return EXIT_FUNCTIONAL_ERROR

    logger.info("Inicio ETL OV manual request_id=%s dry_run=%s", args.request_id, dry_run)
    logger.info("Leyendo CSV manual: %s", args.csv_path)

    csv_result = read_customers_csv(args.csv_path)
    if not csv_result.is_valid:
        _log_csv_errors(logger, csv_result)
        return EXIT_FUNCTIONAL_ERROR

    logger.info("CSV valido filas=%s", len(csv_result.rows))
    if dry_run:
        logger.info("Dry-run activo: no se conecta a VKM ni informa API deposito.")
        return EXIT_SUCCESS

    return process_and_confirm(csv_result.rows, args.request_id, settings, logger)


def run_automatic_mode(args, settings, dry_run, logger):
    logger.info("Inicio ETL OV automatico client_id=%s request_id=%s dry_run=%s", args.client_id or "", args.request_id or "", dry_run)
    if dry_run:
        logger.info("Dry-run activo: no consulta API deposito, no conecta a VKM ni informa confirmacion.")
        return EXIT_SUCCESS

    deposito_client = DepositoApiClient(settings.deposito_api, dry_run=False)
    export_result = deposito_client.export_pending_customers(
        client_id=args.client_id,
        request_id=args.request_id,
        limit=args.limit,
    )
    request_id = export_result.get("request_id") or args.request_id
    rows = export_result.get("rows") or []
    logger.info(
        "Clientes exportados desde backend request_id=%s filas=%s updated=%s",
        request_id,
        len(rows),
        export_result.get("updated", 0),
    )
    if not rows:
        logger.info("No hay clientes pendientes para procesar.")
        return EXIT_SUCCESS

    _write_backup_csv_if_enabled(settings, rows, request_id, logger)

    csv_result = validate_customer_rows(rows, headers=rows[0].keys())
    if not csv_result.is_valid:
        _log_csv_errors(logger, csv_result)
        return EXIT_FUNCTIONAL_ERROR

    return process_and_confirm(csv_result.rows, request_id, settings, logger)


def process_and_confirm(rows, request_id, settings, logger):
    vkm_client = VkmClient(settings.vkm, dry_run=False)
    deposito_client = DepositoApiClient(settings.deposito_api, dry_run=False)
    try:
        vkm_client.connect()
        result = process_rows(rows, vkm_client)
        status = determine_dashboard_status(result)
        error_detail = build_error_detail(result.errors)
        deposito_client.confirm_customer_sync(request_id, status, error_detail)
        logger.info(
            "Resultado enviado request_id=%s status=%s ok=%s error=%s",
            request_id,
            status,
            result.ok_count,
            result.error_count,
        )
        return exit_code_for_status(status)
    except NotImplementedError as exc:
        logger.error("Alta VKM no implementada: %s", exc)
        return EXIT_TECHNICAL_ERROR
    except Exception as exc:
        logger.exception("Error tecnico ETL OV: %s", exc)
        return EXIT_TECHNICAL_ERROR
    finally:
        vkm_client.close()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="ETL OV - clientes nuevos VKM")
    parser.add_argument("--csv-path", default=None, help="Path local al CSV de respaldo manual.")
    parser.add_argument("--request-id", default="", help="request_id a usar o confirmar.")
    parser.add_argument("--client-id", default=None, help="Cuenta a procesar en modo automatico.")
    parser.add_argument("--limit", default=500, help="Cantidad maxima de clientes a tomar del backend.")
    parser.add_argument("--dry-run", action="store_true", help="Valida y simula sin tocar VKM ni backend.")
    parser.add_argument("--env-path", default=None, help="Path opcional a archivo .env.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    settings = load_settings(args.env_path)
    dry_run = args.dry_run or settings.dry_run
    configure_logging(settings.log_level)
    logger = logging.getLogger("etl_ov")

    if args.csv_path:
        return run_manual_mode(args, settings, dry_run, logger)
    return run_automatic_mode(args, settings, dry_run, logger)


if __name__ == "__main__":
    sys.exit(main())
