from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.vkm_client import INTENTIDAD_COLUMNS, VkmClient, truncate_vkm_text


def _config(**overrides):
    values = {
        "host": "sql.example",
        "port": "1433",
        "database": "VKM_Interfaz_Prod",
        "user": "user",
        "password": "secret",
        "driver": "ODBC Driver 17 for SQL Server",
        "cuenta_id": "42",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _row(**overrides):
    values = {
        "cliente_id": "C001",
        "nombre": "Cliente Uno",
        "direccion": "Calle 1",
        "localidad": "Rosario",
        "provincia": "Santa Fe",
        "codigo_postal": "2000",
        "observacion": "Obs",
    }
    values.update(overrides)
    return values


class FakeCursor:
    def __init__(self, fetchone_result=None):
        self.fetchone_result = fetchone_result
        self.execute_calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query, *params):
        self.execute_calls.append((query, params))

    def fetchone(self):
        return self.fetchone_result


class FakeConnection:
    def __init__(self, cursors):
        self.cursors = list(cursors)
        self.commit_calls = 0

    def cursor(self):
        return self.cursors.pop(0)

    def commit(self):
        self.commit_calls += 1


class VkmClientTests(unittest.TestCase):
    def test_connect_validates_required_variables(self):
        client = VkmClient(_config(host=""), dry_run=False)

        with self.assertRaisesRegex(RuntimeError, "VKM_SQLSERVER_HOST"):
            client.connect()

    def test_missing_cuenta_id_has_clear_error(self):
        client = VkmClient(_config(cuenta_id=""), dry_run=False)

        with self.assertRaisesRegex(RuntimeError, "VKM_CUENTA_ID"):
            client.connect()

    def test_customer_exists_executes_parameterized_query(self):
        cursor = FakeCursor(fetchone_result=(123,))
        client = VkmClient(_config(), dry_run=False)
        client.connection = FakeConnection([cursor])

        result = client.customer_exists("C001")

        self.assertEqual(result, 123)
        query, params = cursor.execute_calls[0]
        self.assertIn("ENT.EntEntIDC = ?", query)
        self.assertIn("ENT6.EntLogID = ?", query)
        self.assertEqual(params, ("C001", "42"))

    def test_create_or_confirm_customer_does_not_insert_existing_customer(self):
        exists_cursor = FakeCursor(fetchone_result=(123,))
        connection = FakeConnection([exists_cursor])
        client = VkmClient(_config(), dry_run=False)
        client.connection = connection

        result = client.create_or_confirm_customer(_row())

        self.assertEqual(result["status"], "exists")
        self.assertEqual(connection.commit_calls, 0)

    def test_create_or_confirm_customer_inserts_intentidad_with_expected_fields(self):
        exists_cursor = FakeCursor(fetchone_result=None)
        insert_cursor = FakeCursor()
        connection = FakeConnection([exists_cursor, insert_cursor])
        client = VkmClient(_config(cuenta_id="99"), dry_run=False)
        client.connection = connection

        result = client.create_or_confirm_customer(_row())

        self.assertEqual(result["status"], "created")
        self.assertEqual(connection.commit_calls, 1)
        query, params = insert_cursor.execute_calls[0]
        self.assertIn("[VKM_Interfaz_Prod].[dbo].[IntEntidad]", query)
        self.assertIn("[INEntId]", query)
        self.assertNotIn('"INEntId"', query)
        self.assertEqual(len(params), len(INTENTIDAD_COLUMNS))
        self.assertEqual(params[0], "C001")
        self.assertEqual(params[3], "Cliente Uno")
        self.assertEqual(params[7], "Calle 1")
        self.assertEqual(params[10], "Rosario")
        self.assertEqual(params[12], "Santa Fe")
        self.assertEqual(params[15], "2000")
        self.assertEqual(params[20], 80)
        self.assertEqual(params[21], "C001")
        self.assertEqual(params[24], "1")
        self.assertEqual(params[25], "vaclog")
        self.assertEqual(params[27], "1")
        self.assertEqual(params[33], "Obs")
        self.assertEqual(params[34], "99")

    def test_strings_are_cleaned_and_truncated(self):
        self.assertEqual(truncate_vkm_text("A'B\"C/á", 10), "ABC")
        self.assertEqual(truncate_vkm_text("123456789012345", 5), "12345")

    @patch("src.vkm_client.datetime")
    def test_insert_truncates_legacy_lengths(self, datetime_mock):
        datetime_mock.now.return_value = "NOW"
        exists_cursor = FakeCursor(fetchone_result=None)
        insert_cursor = FakeCursor()
        client = VkmClient(_config(), dry_run=False)
        client.connection = FakeConnection([exists_cursor, insert_cursor])

        client.create_or_confirm_customer(
            _row(
                cliente_id="123456789012345678901234",
                nombre="N" * 40,
                direccion="D" * 120,
                localidad="L" * 120,
                provincia="P" * 120,
                codigo_postal="1" * 12,
                observacion="O" * 1100,
            )
        )

        params = insert_cursor.execute_calls[0][1]
        self.assertEqual(len(params[0]), 20)
        self.assertEqual(len(params[3]), 35)
        self.assertEqual(len(params[7]), 100)
        self.assertEqual(len(params[10]), 100)
        self.assertEqual(len(params[12]), 100)
        self.assertEqual(len(params[15]), 10)
        self.assertEqual(len(params[21]), 11)
        self.assertEqual(len(params[33]), 1024)
        self.assertEqual(params[26], "NOW")


if __name__ == "__main__":
    unittest.main()
