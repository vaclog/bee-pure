import os
import sys
import csv
import io
import traceback

from common import config as cnf
from common.mysql_db import get_mysql_conn

VALKIMIA_FILENAME_FMT = "import_{documento}.csv"
NEW_CUSTOMER_FILENAME_FMT = "new_customer_{documento}.csv"


def get_path(attr_name: str, env_name: str) -> str:
    """
    Usa cnf.<attr_name> si existe; si no, usa env <env_name>.
    """
    if hasattr(cnf, attr_name):
        p = getattr(cnf, attr_name)
        if p:
            return p
    p = os.getenv(env_name)
    if not p:
        raise RuntimeError(f"Falta configurar path: cnf.{attr_name} o env {env_name}")
    return p


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def write_text_file(path: str, content: str, encoding: str):
    with open(path, "w", encoding=encoding, newline="") as f:
        f.write(content or "")


def parse_semicolon_csv(text: str):
    if not text:
        return []
    text = text.strip()
    if not text:
        return []
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    return list(reader)


def process_queue_row(mysql_cur, row: dict, write_files: bool, mark_processed: bool):
    queue_id = row["id"]
    documento = row["documento"]  # ej: BATCH-7

    csv_valkimia = row["csv_valkimia"] or ""
    csv_new_clients = row.get("csv_new_clients") or ""

    import_path = get_path("import_path", "IMPORT_PATH")
    new_customer_root = get_path("new_customer_path", "NEW_CUSTOMER_PATH")

    # 1) CSV Valkimia (UTF-8)
    ensure_dir(import_path)
    valkimia_path = os.path.join(import_path, VALKIMIA_FILENAME_FMT.format(documento=documento))
    if write_files:
        write_text_file(valkimia_path, csv_valkimia, encoding="utf-8")

    # 2) CSV Nuevos Clientes (ANSI/latin-1) si hay
    new_customer_path = None
    new_clients_count = 0
    if csv_new_clients and csv_new_clients.strip():
        ensure_dir(new_customer_root)
        new_customer_path = os.path.join(
            new_customer_root,
            NEW_CUSTOMER_FILENAME_FMT.format(documento=documento),
        )
        if write_files:
            write_text_file(new_customer_path, csv_new_clients, encoding="latin-1")

        new_clients_count = len(parse_semicolon_csv(csv_new_clients))

    # 3) Marcar procesado en MySQL
    if mark_processed:
        mysql_cur.execute(
            """
            UPDATE ov_order_queue
               SET processed_at = NOW(),
                   status = 'processed',
                   last_error = NULL
             WHERE id = %s
            """,
            (queue_id,),
        )

    return {
        "id": queue_id,
        "documento": documento,
        "valkimia_path": valkimia_path,
        "new_customer_path": new_customer_path,
        "new_clients_count": new_clients_count,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Exporta ov_order_queue -> CSVs (sin SQL Server)")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--export-only", action="store_true", help="Escribe CSV y marca processed_at. No usa SQL Server.")
    parser.add_argument("--dry-run", action="store_true", help="No escribe CSV ni marca processed_at.")
    args = parser.parse_args()

    # Resolución de modo
    if args.dry_run:
        write_files = False
        mark_processed = False
    else:
        # por defecto: export-only (es lo que querés ahora)
        write_files = True
        mark_processed = True

    mysql_conn = get_mysql_conn()
    processed = 0

    try:
        with mysql_conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                  FROM ov_order_queue
                 WHERE processed_at IS NULL
                   AND status IN ('pending', 'ready')
                 ORDER BY id ASC
                 LIMIT %s
                """,
                (args.limit,),
            )
            rows = cur.fetchall()

            if not rows:
                print("No hay registros pendientes.")
                return 0

            for row in rows:
                qid = row["id"]
                try:
                    if mark_processed:
                        cur.execute(
                            "UPDATE ov_order_queue SET attempt_count = attempt_count + 1 WHERE id = %s",
                            (qid,),
                        )

                    result = process_queue_row(cur, row, write_files=write_files, mark_processed=mark_processed)

                    if mark_processed:
                        mysql_conn.commit()

                    processed += 1
                    print(
                        f"[OK] id={result['id']} documento={result['documento']} "
                        f"valkimia={result['valkimia_path']} "
                        f"new_customer={result['new_customer_path'] or '-'} "
                        f"new_clients={result['new_clients_count']}"
                    )

                except Exception as e:
                    err = f"{e}\n{traceback.format_exc()}"
                    if mark_processed:
                        mysql_conn.rollback()
                        with mysql_conn.cursor() as cur2:
                            cur2.execute(
                                """
                                UPDATE ov_order_queue
                                   SET status = 'error',
                                       last_error = %s,
                                       updated_at = NOW()
                                 WHERE id = %s
                                """,
                                (err[:65000], qid),
                            )
                        mysql_conn.commit()
                    print(f"[ERROR] id={qid}: {e}", file=sys.stderr)

        print(f"Procesados: {processed}")
        return 0

    finally:
        try:
            mysql_conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())