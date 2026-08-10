import argparse
from dataclasses import dataclass
import logging
import os
from pathlib import Path
import sys

from .config import load_settings
from .csv_reader import read_customers_csv, validate_customer_rows, write_customers_backup_csv
from .deposito_api_client import DepositoApiClient
from .logging_config import configure_logging
from .version import get_version
from .vkm_client import VkmClient


EXIT_SUCCESS = 0
EXIT_FUNCTIONAL_ERROR = 1
EXIT_TECHNICAL_ERROR = 2
EXIT_PARTIAL = 3
MAX_AUTOMATIC_EXPORT_CYCLES = 100
AUTOMATIC_LOCK_FILENAME = ".etl_ov.automatic.lock"


@dataclass(frozen=True)
class ProcessingResult:
    ok_count: int
    error_count: int
    errors: list
    row_results: list = None


def determine_dashboard_status(result):
    statuses = {item.get("status") for item in (result.row_results or []) if item.get("status")}
    if "queued" in statuses and result.error_count == 0:
        return "queued"
    if result.ok_count > 0 and result.error_count == 0:
        return "confirmed"
    if result.ok_count > 0 and result.error_count > 0:
        return "partial"
    return "error"


def exit_code_for_status(status):
    if status in ("confirmed", "queued"):
        return EXIT_SUCCESS
    if status == "partial":
        return EXIT_PARTIAL
    return EXIT_FUNCTIONAL_ERROR


def process_rows(rows, vkm_client):
    ok_count = 0
    errors = []
    row_results = []
    for index, row in enumerate(rows, start=2):
        try:
            result = vkm_client.create_or_confirm_customer(row)
            row_results.append({"row": row, **(result or {})})
            ok_count += 1
        except Exception as exc:
            row_results.append({"row": row, "status": "error", "error": str(exc)})
            errors.append(f"Fila {index} cliente_id={row.get('cliente_id', '')}: {exc}")
    return ProcessingResult(ok_count=ok_count, error_count=len(errors), errors=errors, row_results=row_results)


def _confirmed_customer_mappings(row_results):
    mappings = []
    for item in row_results or []:
        if item.get("status") != "confirmed":
            continue
        row = item.get("row") or {}
        queue_id = row.get("id")
        if not queue_id:
            continue

        customer_code = (item.get("customer_code") or item.get("cliente_id") or row.get("customer_code") or row.get("cliente_id") or "").strip()
        codigo_valkimia = str(item.get("codigo_valkimia") or "").strip()
        if not customer_code or not codigo_valkimia:
            raise RuntimeError(
                f"Cliente confirmado sin mapping completo id={queue_id} customer_code={customer_code or ''}"
            )

        mappings.append(
            {
                "id": queue_id,
                "customer_code": customer_code,
                "codigo_valkimia": codigo_valkimia,
            }
        )
    return mappings


def confirm_processed_rows(deposito_client, request_id, result, error_detail):
    rows_have_ids = any((item.get("row") or {}).get("id") for item in (result.row_results or []))
    if not rows_have_ids:
        status = determine_dashboard_status(result)
        deposito_client.confirm_customer_sync(request_id=request_id, status=status, error_detail=error_detail)
        return status

    sent_status = "confirmed"
    for status in ("confirmed", "queued"):
        ids = [
            (item.get("row") or {}).get("id")
            for item in (result.row_results or [])
            if item.get("status") == status and (item.get("row") or {}).get("id")
        ]
        if ids:
            confirm_kwargs = {"status": status, "ids": ids}
            if status == "confirmed":
                confirm_kwargs["customer_mappings"] = _confirmed_customer_mappings(result.row_results)
            deposito_client.confirm_customer_sync(**confirm_kwargs)
            if status == "queued":
                sent_status = "queued"

    error_ids = [
        (item.get("row") or {}).get("id")
        for item in (result.row_results or [])
        if item.get("status") == "error" and (item.get("row") or {}).get("id")
    ]
    if error_ids:
        deposito_client.confirm_customer_sync(status="error", ids=error_ids, error_detail=error_detail)
        sent_status = "partial" if result.ok_count else "error"
    return sent_status


def verify_queued_customers(deposito_client, vkm_client, client_id, limit, logger):
    queued_result = deposito_client.list_queued_customers(client_id=client_id, limit=limit)
    queued_rows = queued_result.get("rows") or []
    verified_rows = []
    for row in queued_rows:
        result = vkm_client.verify_queued_customer(row)
        verified_rows.append({"row": row, **(result or {})})

    confirmed_ids = [
        (item.get("row") or {}).get("id")
        for item in verified_rows
        if item.get("status") == "confirmed" and (item.get("row") or {}).get("id")
    ]

    if confirmed_ids:
        deposito_client.confirm_customer_sync(
            status="confirmed",
            ids=confirmed_ids,
            customer_mappings=_confirmed_customer_mappings(verified_rows),
        )
    logger.info("Clientes en cola verificados=%s confirmados=%s", len(queued_rows), len(confirmed_ids))
    return {"checked": len(queued_rows), "confirmed": len(confirmed_ids)}


def build_error_detail(errors, limit=20):
    return " | ".join(errors[:limit])


def _log_csv_errors(logger, csv_result):
    for error in csv_result.errors:
        logger.error("CSV fila=%s error=%s", error.row_number, error.message)


def _validation_error_messages(csv_result):
    return [
        f"Fila {error.row_number}: {error.message}"
        for error in csv_result.errors
    ]


def _exported_row_ids(rows):
    return [
        row.get("id")
        for row in rows
        if row.get("id")
    ]


def confirm_customer_validation_failure(deposito_client, rows, request_id, csv_result):
    error_detail = build_error_detail(_validation_error_messages(csv_result))
    ids = _exported_row_ids(rows)
    if ids and len(ids) == len(rows):
        deposito_client.confirm_customer_sync(status="error", ids=ids, error_detail=error_detail)
    elif request_id:
        deposito_client.confirm_customer_sync(
            request_id=request_id,
            status="error",
            error_detail=error_detail,
        )
    elif ids:
        deposito_client.confirm_customer_sync(status="error", ids=ids, error_detail=error_detail)
    return error_detail


def _write_backup_csv_if_enabled(settings, rows, request_id, logger):
    if not settings.new_customer_path:
        logger.info("Salida CSV local de clientes nuevos deshabilitada.")
        return None

    backup_path = write_customers_backup_csv(settings.new_customer_path, rows, request_id=request_id)
    logger.info("CSV local de respaldo generado: %s", backup_path)
    return backup_path


def _automatic_lock_path():
    return Path(__file__).resolve().parents[1] / AUTOMATIC_LOCK_FILENAME


def _acquire_automatic_run_lock(logger):
    lock_path = _automatic_lock_path()
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        logger.warning("Ya existe una ejecucion automatica en curso. Se omite esta corrida: %s", lock_path)
        return None

    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    return lock_path


def _release_automatic_run_lock(lock_path):
    if not lock_path:
        return
    try:
        Path(lock_path).unlink(missing_ok=True)
    except OSError:
        pass


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

    lock_path = _acquire_automatic_run_lock(logger)
    if lock_path is None:
        return EXIT_SUCCESS

    try:
        deposito_client = DepositoApiClient(settings.deposito_api, dry_run=False)
        vkm_client = VkmClient(settings.vkm, dry_run=False)
        try:
            vkm_client.connect()
            verify_queued_customers(deposito_client, vkm_client, args.client_id, args.limit, logger)
        except Exception as exc:
            logger.exception("Error verificando clientes en cola VKM: %s", exc)
            return EXIT_TECHNICAL_ERROR
        finally:
            vkm_client.close()

        if args.client_id:
            exit_code, _processed_rows = export_and_process_pending_customers(
                deposito_client,
                args,
                settings,
                logger,
            )
            return exit_code

        total_rows = 0
        for cycle in range(1, MAX_AUTOMATIC_EXPORT_CYCLES + 1):
            exit_code, processed_rows = export_and_process_pending_customers(
                deposito_client,
                args,
                settings,
                logger,
                cycle=cycle,
            )
            total_rows += processed_rows
            if processed_rows == 0:
                logger.info("No hay mas clientes pendientes para procesar. total_procesados=%s", total_rows)
                return EXIT_SUCCESS
            if exit_code != EXIT_SUCCESS:
                logger.info("Corte de ciclo automatico por resultado funcional exit_code=%s total_procesados=%s", exit_code, total_rows)
                return exit_code

        logger.error("Corte preventivo: se alcanzo el maximo de ciclos automaticos (%s).", MAX_AUTOMATIC_EXPORT_CYCLES)
        return EXIT_TECHNICAL_ERROR
    finally:
        _release_automatic_run_lock(lock_path)


def export_and_process_pending_customers(deposito_client, args, settings, logger, cycle=None):
    export_result = deposito_client.export_pending_customers(
        client_id=args.client_id,
        request_id=args.request_id,
        limit=args.limit,
    )
    request_id = export_result.get("request_id") or args.request_id
    rows = export_result.get("rows") or []
    logger.info(
        "Clientes exportados desde backend ciclo=%s request_id=%s client_id=%s client_ids=%s filas=%s updated=%s",
        cycle or 1,
        request_id,
        export_result.get("client_id") or "",
        export_result.get("client_ids") or [],
        len(rows),
        export_result.get("updated", 0),
    )
    if not rows:
        logger.info("No hay clientes pendientes para procesar.")
        return EXIT_SUCCESS, 0

    _write_backup_csv_if_enabled(settings, rows, request_id, logger)

    csv_result = validate_customer_rows(rows, headers=rows[0].keys())
    if not csv_result.is_valid:
        _log_csv_errors(logger, csv_result)
        confirm_customer_validation_failure(deposito_client, rows, request_id, csv_result)
        return EXIT_FUNCTIONAL_ERROR, len(rows)

    return process_and_confirm(csv_result.rows, request_id, settings, logger), len(rows)


def process_and_confirm(rows, request_id, settings, logger):
    vkm_client = VkmClient(settings.vkm, dry_run=False)
    deposito_client = DepositoApiClient(settings.deposito_api, dry_run=False)
    try:
        vkm_client.connect()
        result = process_rows(rows, vkm_client)
        error_detail = build_error_detail(result.errors)
        status = confirm_processed_rows(deposito_client, request_id, result, error_detail)
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
    parser.add_argument("--version", action="version", version=f"ETL OV {get_version()}")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    settings = load_settings(args.env_path)
    dry_run = args.dry_run or settings.dry_run
    configure_logging(settings.log_level)
    logger = logging.getLogger("etl_ov")
    version = get_version()
    mode = "manual" if args.csv_path else "automatic"

    logger.info(
        "Inicio proceso ETL OV version=%s mode=%s dry_run=%s",
        version,
        mode,
        dry_run,
    )

    if args.csv_path:
        exit_code = run_manual_mode(args, settings, dry_run, logger)
    else:
        exit_code = run_automatic_mode(args, settings, dry_run, logger)

    logger.info(
        "Fin proceso ETL OV version=%s exit_code=%s",
        version,
        exit_code,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
