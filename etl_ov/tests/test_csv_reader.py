import csv
import tempfile
from datetime import datetime
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.csv_reader import BACKUP_HEADERS, read_customers_csv, validate_customer_rows, write_customers_backup_csv


def _write_csv(content):
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", suffix=".csv", delete=False)
    handle.write(content)
    handle.close()
    return Path(handle.name)


class CsvReaderTests(unittest.TestCase):
    def tearDown(self):
        if hasattr(self, "path") and self.path.exists():
            self.path.unlink()
        if hasattr(self, "temp_dir"):
            for child in self.temp_dir.glob("*"):
                if child.is_file():
                    child.unlink()
            self.temp_dir.rmdir()

    def test_valid_csv(self):
        self.path = _write_csv(
            "cliente_id;nombre;direccion;localidad;provincia;codigo_postal\n"
            "C001;Cliente Uno;Calle 1;Rosario;Santa Fe;2000\n"
        )

        result = read_customers_csv(self.path)

        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0]["cliente_id"], "C001")

    def test_missing_required_headers(self):
        self.path = _write_csv("cliente_id;nombre\nC001;Cliente Uno\n")

        result = read_customers_csv(self.path)

        self.assertFalse(result.is_valid)
        self.assertIn("Faltan columnas requeridas", result.errors[0].message)

    def test_duplicate_cliente_id(self):
        self.path = _write_csv(
            "cliente_id;nombre;direccion;localidad;provincia;codigo_postal\n"
            "C001;Cliente Uno;Calle 1;Rosario;Santa Fe;2000\n"
            "C001;Cliente Dos;Calle 2;Rosario;Santa Fe;2000\n"
        )

        result = read_customers_csv(self.path)

        self.assertFalse(result.is_valid)
        self.assertTrue(any("duplicado" in error.message for error in result.errors))

    def test_validate_customer_rows_allows_same_cliente_id_for_different_client_id(self):
        result = validate_customer_rows(
            [
                {
                    "client_id": "123",
                    "cliente_id": "C001",
                    "nombre": "Cliente Uno",
                    "direccion": "Calle 1",
                    "localidad": "Rosario",
                    "provincia": "Santa Fe",
                    "codigo_postal": "2000",
                },
                {
                    "client_id": "456",
                    "cliente_id": "C001",
                    "nombre": "Cliente Dos",
                    "direccion": "Calle 2",
                    "localidad": "Cordoba",
                    "provincia": "Cordoba",
                    "codigo_postal": "5000",
                },
            ],
            headers=["client_id", "cliente_id", "nombre", "direccion", "localidad", "provincia", "codigo_postal"],
        )

        self.assertTrue(result.is_valid)

    def test_validate_customer_rows_allows_same_cliente_id_for_different_vkm_cuenta_id(self):
        result = validate_customer_rows(
            [
                {
                    "vkm_cuenta_id": "987",
                    "cliente_id": "C001",
                    "nombre": "Cliente Uno",
                    "direccion": "Calle 1",
                    "localidad": "Rosario",
                    "provincia": "Santa Fe",
                    "codigo_postal": "2000",
                },
                {
                    "vkm_cuenta_id": "654",
                    "cliente_id": "C001",
                    "nombre": "Cliente Dos",
                    "direccion": "Calle 2",
                    "localidad": "Cordoba",
                    "provincia": "Cordoba",
                    "codigo_postal": "5000",
                },
            ],
            headers=["vkm_cuenta_id", "cliente_id", "nombre", "direccion", "localidad", "provincia", "codigo_postal"],
        )

        self.assertTrue(result.is_valid)

    def test_validate_customer_rows_rejects_same_cliente_id_with_same_client_id(self):
        result = validate_customer_rows(
            [
                {
                    "client_id": "123",
                    "cliente_id": "C001",
                    "nombre": "Cliente Uno",
                    "direccion": "Calle 1",
                    "localidad": "Rosario",
                    "provincia": "Santa Fe",
                    "codigo_postal": "2000",
                },
                {
                    "client_id": "123",
                    "cliente_id": "C001",
                    "nombre": "Cliente Dos",
                    "direccion": "Calle 2",
                    "localidad": "Cordoba",
                    "provincia": "Cordoba",
                    "codigo_postal": "5000",
                },
            ],
            headers=["client_id", "cliente_id", "nombre", "direccion", "localidad", "provincia", "codigo_postal"],
        )

        self.assertFalse(result.is_valid)
        self.assertTrue(any("duplicado" in error.message for error in result.errors))

    def test_validate_customer_rows_without_account_columns_keeps_duplicate_rejection(self):
        result = validate_customer_rows(
            [
                {
                    "client_id": "123",
                    "cliente_id": "C001",
                    "nombre": "Cliente Uno",
                    "direccion": "Calle 1",
                    "localidad": "Rosario",
                    "provincia": "Santa Fe",
                    "codigo_postal": "2000",
                },
                {
                    "cliente_id": "C001",
                    "nombre": "Cliente Dos",
                    "direccion": "Calle 2",
                    "localidad": "Cordoba",
                    "provincia": "Cordoba",
                    "codigo_postal": "5000",
                },
            ],
            headers=["cliente_id", "nombre", "direccion", "localidad", "provincia", "codigo_postal"],
        )

        self.assertFalse(result.is_valid)
        self.assertTrue(any("duplicado" in error.message for error in result.errors))

    def test_required_empty_fields(self):
        self.path = _write_csv(
            "cliente_id;nombre;direccion;localidad;provincia;codigo_postal\n"
            "C001;;Calle 1;Rosario;Santa Fe;\n"
        )

        result = read_customers_csv(self.path)

        self.assertFalse(result.is_valid)
        messages = [error.message for error in result.errors]
        self.assertIn("nombre vacio.", messages)
        self.assertIn("codigo_postal vacio.", messages)

    def test_validate_customer_rows_without_file(self):
        result = validate_customer_rows(
            [
                {
                    "cliente_id": "C001",
                    "nombre": "Cliente Uno",
                    "direccion": "Calle 1",
                    "localidad": "Rosario",
                    "provincia": "Santa Fe",
                    "codigo_postal": "2000",
                }
            ],
            headers=["cliente_id", "nombre", "direccion", "localidad", "provincia", "codigo_postal"],
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.rows[0]["cliente_id"], "C001")

    def test_write_customers_backup_csv_uses_expected_headers_and_delimiter(self):
        self.temp_dir = Path(tempfile.mkdtemp())

        path = write_customers_backup_csv(
            self.temp_dir,
            [
                {
                    "client_id": "123",
                    "cliente_id": "C001",
                    "nombre": "Cliente Uno",
                    "direccion": "Calle 1",
                    "localidad": "Rosario",
                    "provincia": "Santa Fe",
                    "codigo_postal": "2000",
                    "observacion": "Obs",
                    "tipo": "80",
                    "numero_documento": "123",
                    "vkm_cuenta_id": "987",
                }
            ],
            request_id="req/1",
            timestamp=datetime(2026, 5, 8, 10, 11, 12),
        )

        self.assertTrue(path.exists())
        self.assertEqual(path.name, "clientes_nuevos_20260508_101112_req_1.csv")
        with path.open("r", encoding="utf-8", newline="") as handle:
            content = handle.read()
            self.assertIn(";".join(BACKUP_HEADERS), content)
            self.assertIn("123;C001;Cliente Uno;Calle 1;Rosario;Santa Fe;2000;Obs;80;123;987", content)

    def test_write_customers_backup_csv_fills_missing_optional_columns(self):
        self.temp_dir = Path(tempfile.mkdtemp())

        path = write_customers_backup_csv(
            self.temp_dir,
            [
                {
                    "client_id": "123",
                    "cliente_id": "C001",
                    "nombre": "Cliente Uno",
                    "direccion": "Calle 1",
                    "localidad": "Rosario",
                    "provincia": "Santa Fe",
                    "codigo_postal": "2000",
                }
            ],
            timestamp=datetime(2026, 5, 8, 10, 11, 12),
        )

        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            row = next(reader)

        self.assertEqual(row["observacion"], "")
        self.assertEqual(row["tipo"], "")
        self.assertEqual(row["numero_documento"], "")
        self.assertEqual(row["vkm_cuenta_id"], "")
        self.assertEqual(row["client_id"], "123")

    def test_write_customers_backup_csv_leaves_client_id_empty_when_missing(self):
        self.temp_dir = Path(tempfile.mkdtemp())

        path = write_customers_backup_csv(
            self.temp_dir,
            [
                {
                    "cliente_id": "C001",
                    "nombre": "Cliente Uno",
                    "direccion": "Calle 1",
                    "localidad": "Rosario",
                    "provincia": "Santa Fe",
                    "codigo_postal": "2000",
                }
            ],
            timestamp=datetime(2026, 5, 8, 10, 11, 12),
        )

        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            row = next(reader)

        self.assertEqual(row["client_id"], "")


if __name__ == "__main__":
    unittest.main()
