from pathlib import Path
from io import StringIO
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import main as main_module
from src.deposito_api_client import DepositoApiClient
from src.main import ProcessingResult, determine_dashboard_status, exit_code_for_status


def _settings():
    return SimpleNamespace(
        deposito_api=SimpleNamespace(base_url="http://backend.test", token="token"),
        vkm=SimpleNamespace(),
        new_customer_path="",
        dry_run=False,
        log_level="CRITICAL",
    )


def _valid_row(cliente_id="C001"):
    return {
        "cliente_id": cliente_id,
        "nombre": "Cliente Uno",
        "direccion": "Calle 1",
        "localidad": "Rosario",
        "provincia": "Santa Fe",
        "codigo_postal": "2000",
        "vkm_cuenta_id": "987",
    }


class MainResultTests(unittest.TestCase):
    def test_success_status(self):
        result = ProcessingResult(ok_count=2, error_count=0, errors=[])

        status = determine_dashboard_status(result)

        self.assertEqual(status, "confirmed")
        self.assertEqual(exit_code_for_status(status), 0)

    def test_partial_status(self):
        result = ProcessingResult(ok_count=1, error_count=1, errors=["fila 2"])

        status = determine_dashboard_status(result)

        self.assertEqual(status, "partial")
        self.assertEqual(exit_code_for_status(status), 3)

    def test_error_status(self):
        result = ProcessingResult(ok_count=0, error_count=2, errors=["fila 2", "fila 3"])

        status = determine_dashboard_status(result)

        self.assertEqual(status, "error")
        self.assertEqual(exit_code_for_status(status), 1)


class MainFlowTests(unittest.TestCase):
    def _patch_settings(self):
        return patch("src.main.load_settings", return_value=_settings())

    def test_version_flag_prints_current_version_and_exits_successfully(self):
        stdout = StringIO()
        stderr = StringIO()

        with patch("sys.stdout", stdout), patch("sys.stderr", stderr), patch("src.main.get_version", return_value="9.8.7"), patch("src.main.load_settings") as load_settings_mock, patch("src.main.DepositoApiClient") as deposito_mock, patch("src.main.VkmClient") as vkm_mock:
            with self.assertRaises(SystemExit) as exc:
                main_module.main(["--version"])

        self.assertEqual(exc.exception.code, 0)
        self.assertEqual(stdout.getvalue().strip(), "ETL OV 9.8.7")
        self.assertEqual(stderr.getvalue(), "")
        load_settings_mock.assert_not_called()
        deposito_mock.assert_not_called()
        vkm_mock.assert_not_called()

    def test_manual_startup_and_completion_logs_include_version_and_exit_code(self):
        logger = unittest.mock.Mock()

        with self._patch_settings(), patch("src.main.configure_logging"), patch("src.main.logging.getLogger", return_value=logger), patch("src.main.get_version", return_value="1.0.0"), patch("src.main.run_manual_mode", return_value=main_module.EXIT_FUNCTIONAL_ERROR) as run_manual_mode_mock:
            exit_code = main_module.main(["--csv-path", "manual.csv", "--request-id", "req-1", "--dry-run"])

        self.assertEqual(exit_code, main_module.EXIT_FUNCTIONAL_ERROR)
        run_manual_mode_mock.assert_called_once()
        logger.info.assert_any_call(
            "Inicio proceso ETL OV version=%s mode=%s dry_run=%s",
            "1.0.0",
            "manual",
            True,
        )
        logger.info.assert_any_call(
            "Fin proceso ETL OV version=%s exit_code=%s",
            "1.0.0",
            main_module.EXIT_FUNCTIONAL_ERROR,
        )

    def test_automatic_startup_and_completion_logs_include_version_and_exit_code(self):
        logger = unittest.mock.Mock()

        with self._patch_settings(), patch("src.main.configure_logging"), patch("src.main.logging.getLogger", return_value=logger), patch("src.main.get_version", return_value="1.0.0"), patch("src.main.run_automatic_mode", return_value=main_module.EXIT_TECHNICAL_ERROR) as run_automatic_mode_mock:
            exit_code = main_module.main(["--dry-run"])

        self.assertEqual(exit_code, main_module.EXIT_TECHNICAL_ERROR)
        run_automatic_mode_mock.assert_called_once()
        logger.info.assert_any_call(
            "Inicio proceso ETL OV version=%s mode=%s dry_run=%s",
            "1.0.0",
            "automatic",
            True,
        )
        logger.info.assert_any_call(
            "Fin proceso ETL OV version=%s exit_code=%s",
            "1.0.0",
            main_module.EXIT_TECHNICAL_ERROR,
        )

    def test_missing_version_file_does_not_block_normal_execution(self):
        with self._patch_settings(), patch("src.main.get_version", return_value="unknown"), patch("src.main.run_automatic_mode", return_value=main_module.EXIT_SUCCESS):
            exit_code = main_module.main(["--dry-run"])

        self.assertEqual(exit_code, main_module.EXIT_SUCCESS)

    def test_automatic_mode_marks_downloaded_before_confirming(self):
        calls = []

        class FakeDepositoApiClient:
            export_calls = 0

            def __init__(self, _config, dry_run=False):
                self.dry_run = dry_run

            def export_pending_customers(self, **_kwargs):
                self.__class__.export_calls += 1
                calls.append("export")
                if self.__class__.export_calls > 1:
                    return {"request_id": "req-auto-2", "updated": 0, "rows": []}
                return {"request_id": "req-auto", "updated": 1, "rows": [{**_valid_row(), "id": 10}]}

            def list_queued_customers(self, **_kwargs):
                calls.append("queued")
                return {"rows": []}

            def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None):
                calls.append(("confirm", request_id, status, error_detail, ids))
                return {"updated": 1}

        class FakeVkmClient:
            def __init__(self, _config, dry_run=False):
                pass

            def connect(self):
                calls.append("connect")

            def create_or_confirm_customer(self, row):
                calls.append(("vkm", row["cliente_id"]))
                return {"cliente_id": row["cliente_id"], "status": "queued"}

            def verify_queued_customer(self, row):
                return {"cliente_id": row["cliente_id"], "status": "queued"}

            def close(self):
                calls.append("close")

        with self._patch_settings(), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient):
            exit_code = main_module.main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls[0], "connect")
        self.assertIn("queued", calls)
        self.assertIn("export", calls)
        self.assertIn(("confirm", "", "queued", "", ["10"]), calls)

    def test_export_validation_failure_confirms_error_by_ids(self):
        calls = []

        class FakeDepositoClient:
            def export_pending_customers(self, **_kwargs):
                return {
                    "request_id": "req-invalid",
                    "updated": 1,
                    "rows": [{**_valid_row(), "id": 10, "codigo_postal": ""}],
                }

            def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None):
                calls.append((request_id, status, error_detail, ids))
                return {"updated": 1}

        exit_code, processed_rows = main_module.export_and_process_pending_customers(
            FakeDepositoClient(),
            SimpleNamespace(client_id=None, request_id="", limit=500),
            _settings(),
            main_module.logging.getLogger("etl_ov.tests"),
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(processed_rows, 1)
        self.assertEqual(calls[0][0], "")
        self.assertEqual(calls[0][1], "error")
        self.assertIn("codigo_postal vacio", calls[0][2])
        self.assertEqual(calls[0][3], [10])

    def test_export_validation_failure_confirms_all_exported_ids_and_skips_vkm(self):
        calls = []

        class FakeDepositoClient:
            def export_pending_customers(self, **_kwargs):
                return {
                    "request_id": "req-invalid",
                    "updated": 2,
                    "rows": [
                        {**_valid_row("C001"), "id": 10},
                        {**_valid_row("C002"), "id": 11, "codigo_postal": ""},
                    ],
                }

            def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None):
                calls.append((request_id, status, error_detail, ids))
                return {"updated": 2}

        with patch("src.main.process_and_confirm") as process_and_confirm_mock:
            exit_code, processed_rows = main_module.export_and_process_pending_customers(
                FakeDepositoClient(),
                SimpleNamespace(client_id=None, request_id="", limit=500),
                _settings(),
                main_module.logging.getLogger("etl_ov.tests"),
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(processed_rows, 2)
        self.assertEqual(calls[0][0], "")
        self.assertEqual(calls[0][1], "error")
        self.assertIn("codigo_postal vacio", calls[0][2])
        self.assertEqual(calls[0][3], [10, 11])
        process_and_confirm_mock.assert_not_called()

    def test_export_validation_failure_falls_back_to_request_id_without_ids(self):
        calls = []

        class FakeDepositoClient:
            def export_pending_customers(self, **_kwargs):
                return {
                    "request_id": "req-invalid",
                    "updated": 1,
                    "rows": [{**_valid_row(), "codigo_postal": ""}],
                }

            def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None):
                calls.append((request_id, status, error_detail, ids))
                return {"updated": 1}

        exit_code, processed_rows = main_module.export_and_process_pending_customers(
            FakeDepositoClient(),
            SimpleNamespace(client_id=None, request_id="", limit=500),
            _settings(),
            main_module.logging.getLogger("etl_ov.tests"),
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(processed_rows, 1)
        self.assertEqual(calls[0][0], "req-invalid")
        self.assertEqual(calls[0][1], "error")
        self.assertIn("codigo_postal vacio", calls[0][2])
        self.assertIsNone(calls[0][3])

    def test_export_validation_failure_falls_back_to_request_id_when_some_ids_are_missing(self):
        calls = []

        class FakeDepositoClient:
            def export_pending_customers(self, **_kwargs):
                return {
                    "request_id": "req-invalid",
                    "updated": 2,
                    "rows": [
                        {**_valid_row("C001"), "id": 10},
                        {**_valid_row("C002"), "codigo_postal": ""},
                    ],
                }

            def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None):
                calls.append((request_id, status, error_detail, ids))
                return {"updated": 2}

        exit_code, processed_rows = main_module.export_and_process_pending_customers(
            FakeDepositoClient(),
            SimpleNamespace(client_id=None, request_id="", limit=500),
            _settings(),
            main_module.logging.getLogger("etl_ov.tests"),
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(processed_rows, 2)
        self.assertEqual(calls[0][0], "req-invalid")
        self.assertEqual(calls[0][1], "error")
        self.assertIn("codigo_postal vacio", calls[0][2])
        self.assertIsNone(calls[0][3])

    def test_export_validation_failure_without_request_id_uses_available_ids(self):
        calls = []

        class FakeDepositoClient:
            def export_pending_customers(self, **_kwargs):
                return {
                    "request_id": "",
                    "updated": 2,
                    "rows": [
                        {**_valid_row("C001"), "id": 10},
                        {**_valid_row("C002"), "codigo_postal": ""},
                    ],
                }

            def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None):
                calls.append((request_id, status, error_detail, ids))
                return {"updated": 1}

        exit_code, processed_rows = main_module.export_and_process_pending_customers(
            FakeDepositoClient(),
            SimpleNamespace(client_id=None, request_id="", limit=500),
            _settings(),
            main_module.logging.getLogger("etl_ov.tests"),
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(processed_rows, 2)
        self.assertEqual(calls[0][0], "")
        self.assertEqual(calls[0][1], "error")
        self.assertEqual(calls[0][3], [10])

    def test_automatic_mode_generates_backup_csv_when_path_is_configured(self):
        settings = _settings()
        with tempfile.TemporaryDirectory() as temp_dir:
            settings.new_customer_path = temp_dir

            class FakeDepositoApiClient:
                export_calls = 0

                def __init__(self, _config, dry_run=False):
                    pass

                def export_pending_customers(self, **_kwargs):
                    self.__class__.export_calls += 1
                    if self.__class__.export_calls > 1:
                        return {"request_id": "req-auto-2", "updated": 0, "rows": []}
                    return {"request_id": "req-auto", "updated": 1, "rows": [_valid_row()]}

                def list_queued_customers(self, **_kwargs):
                    return {"rows": []}

                def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None):
                    return {"updated": 1}

            class FakeVkmClient:
                def __init__(self, _config, dry_run=False):
                    pass

                def connect(self):
                    pass

                def create_or_confirm_customer(self, _row):
                    return {"cliente_id": _row["cliente_id"], "status": "queued"}

                def verify_queued_customer(self, row):
                    return {"cliente_id": row["cliente_id"], "status": "queued"}

                def close(self):
                    pass

            with patch("src.main.load_settings", return_value=settings), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient):
                exit_code = main_module.main([])

            self.assertEqual(exit_code, 0)
            generated_files = list(Path(temp_dir).glob("clientes_nuevos_*.csv"))
            self.assertEqual(len(generated_files), 1)
            content = generated_files[0].read_text(encoding="utf-8")
            self.assertIn("client_id;cliente_id;nombre;direccion;localidad;provincia;codigo_postal;observacion;tipo;numero_documento;vkm_cuenta_id", content)
            self.assertIn(";C001;Cliente Uno;Calle 1;Rosario;Santa Fe;2000;;;;987", content)

    def test_automatic_mode_without_client_id_processes_batches_until_empty(self):
        calls = []

        class FakeDepositoApiClient:
            export_calls = 0

            def __init__(self, _config, dry_run=False):
                pass

            def list_queued_customers(self, **kwargs):
                calls.append(("queued", kwargs.get("client_id")))
                return {"rows": []}

            def export_pending_customers(self, **kwargs):
                self.__class__.export_calls += 1
                calls.append(("export", kwargs.get("client_id")))
                if self.__class__.export_calls == 1:
                    return {"request_id": "req-1", "client_ids": [123], "updated": 1, "rows": [{**_valid_row("C001"), "id": 101}]}
                if self.__class__.export_calls == 2:
                    return {"request_id": "req-2", "client_ids": [456], "updated": 1, "rows": [{**_valid_row("C002"), "id": 102}]}
                return {"request_id": "req-3", "client_ids": [], "updated": 0, "rows": []}

            def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None):
                calls.append(("confirm", status, ids))
                return {"updated": 1}

        class FakeVkmClient:
            def __init__(self, _config, dry_run=False):
                pass

            def connect(self):
                calls.append("connect")

            def verify_queued_customer(self, row):
                return {"cliente_id": row["cliente_id"], "status": "queued"}

            def create_or_confirm_customer(self, row):
                calls.append(("vkm", row["cliente_id"]))
                return {"cliente_id": row["cliente_id"], "status": "queued"}

            def close(self):
                calls.append("close")

        with self._patch_settings(), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient):
            exit_code = main_module.main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls.count(("queued", None)), 1)
        self.assertEqual(calls.count(("export", None)), 3)
        self.assertIn(("vkm", "C001"), calls)
        self.assertIn(("vkm", "C002"), calls)

    def test_automatic_mode_with_client_id_runs_one_scoped_export_cycle(self):
        calls = []

        class FakeDepositoApiClient:
            def __init__(self, _config, dry_run=False):
                pass

            def list_queued_customers(self, **kwargs):
                calls.append(("queued", kwargs.get("client_id")))
                return {"rows": []}

            def export_pending_customers(self, **kwargs):
                calls.append(("export", kwargs.get("client_id")))
                return {"request_id": "req-123", "client_id": "123", "updated": 1, "rows": [{**_valid_row("C123"), "id": 123}]}

            def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None):
                calls.append(("confirm", status, ids))
                return {"updated": 1}

        class FakeVkmClient:
            def __init__(self, _config, dry_run=False):
                pass

            def connect(self):
                pass

            def verify_queued_customer(self, row):
                return {"cliente_id": row["cliente_id"], "status": "queued"}

            def create_or_confirm_customer(self, row):
                calls.append(("vkm", row["cliente_id"]))
                return {"cliente_id": row["cliente_id"], "status": "queued"}

            def close(self):
                pass

        with self._patch_settings(), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient):
            exit_code = main_module.main(["--client-id", "123"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls.count(("queued", "123")), 1)
        self.assertEqual(calls.count(("export", "123")), 1)
        self.assertIn(("vkm", "C123"), calls)

    def test_queued_customer_with_ineest_2_is_confirmed_before_export(self):
        calls = []

        class FakeDepositoApiClient:
            def __init__(self, _config, dry_run=False):
                pass

            def list_queued_customers(self, **_kwargs):
                return {"rows": [{**_valid_row("C009"), "id": 99}]}

            def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None, customer_mappings=None):
                calls.append(("confirm", status, ids, customer_mappings))
                return {"updated": 1}

            def export_pending_customers(self, **_kwargs):
                calls.append("export")
                return {"request_id": "req-auto", "updated": 0, "rows": []}

        class FakeVkmClient:
            def __init__(self, _config, dry_run=False):
                pass

            def connect(self):
                pass

            def verify_queued_customer(self, row):
                calls.append(("verify", row["cliente_id"]))
                return {
                    "cliente_id": row["cliente_id"],
                    "customer_code": row["cliente_id"],
                    "status": "confirmed",
                    "ineest": "2",
                    "codigo_valkimia": "501",
                    "vkm_id": 501,
                }

            def close(self):
                pass

        with self._patch_settings(), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient):
            exit_code = main_module.main([])

        self.assertEqual(exit_code, 0)
        self.assertIn(
            (
                "confirm",
                "confirmed",
                [99],
                [{"id": 99, "customer_code": "C009", "codigo_valkimia": "501"}],
            ),
            calls,
        )
        self.assertIn("export", calls)

    def test_queued_customer_with_ineest_1_remains_queued(self):
        calls = []

        class FakeDepositoApiClient:
            def __init__(self, _config, dry_run=False):
                pass

            def list_queued_customers(self, **_kwargs):
                return {"rows": [{**_valid_row("C009"), "id": 99}]}

            def confirm_customer_sync(self, **_kwargs):
                calls.append("confirm")
                return {"updated": 1}

            def export_pending_customers(self, **_kwargs):
                return {"request_id": "req-auto", "updated": 0, "rows": []}

        class FakeVkmClient:
            def __init__(self, _config, dry_run=False):
                pass

            def connect(self):
                pass

            def verify_queued_customer(self, row):
                calls.append(("verify", row["cliente_id"]))
                return {"cliente_id": row["cliente_id"], "status": "queued", "ineest": "1"}

            def close(self):
                pass

        with self._patch_settings(), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient):
            exit_code = main_module.main([])

        self.assertEqual(exit_code, 0)
        self.assertIn(("verify", "C009"), calls)
        self.assertNotIn("confirm", calls)

    def test_queued_customer_with_ineest_2_and_missing_entid_is_not_confirmed(self):
        calls = []

        class FakeDepositoApiClient:
            def __init__(self, _config, dry_run=False):
                pass

            def list_queued_customers(self, **_kwargs):
                return {"rows": [{**_valid_row("C009"), "id": 99}]}

            def confirm_customer_sync(self, **_kwargs):
                calls.append("confirm")
                return {"updated": 1}

            def export_pending_customers(self, **_kwargs):
                return {"request_id": "req-auto", "updated": 0, "rows": []}

        class FakeVkmClient:
            def __init__(self, _config, dry_run=False):
                pass

            def connect(self):
                pass

            def verify_queued_customer(self, row):
                calls.append(("verify", row["cliente_id"]))
                return {
                    "cliente_id": row["cliente_id"],
                    "customer_code": row["cliente_id"],
                    "status": "queued",
                    "ineest": "2",
                }

            def close(self):
                pass

        with self._patch_settings(), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient):
            exit_code = main_module.main([])

        self.assertEqual(exit_code, 0)
        self.assertIn(("verify", "C009"), calls)
        self.assertNotIn("confirm", calls)

    def test_queued_customer_confirmation_keeps_row_specific_accounts_in_mappings(self):
        calls = []

        class FakeDepositoApiClient:
            def __init__(self, _config, dry_run=False):
                pass

            def list_queued_customers(self, **_kwargs):
                return {
                    "rows": [
                        {**_valid_row("C009"), "id": 99, "vkm_cuenta_id": "88"},
                        {**_valid_row("C010"), "id": 100, "vkm_cuenta_id": "99"},
                    ]
                }

            def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None, customer_mappings=None):
                calls.append(("confirm", status, ids, customer_mappings))
                return {"updated": 2}

            def export_pending_customers(self, **_kwargs):
                return {"request_id": "req-auto", "updated": 0, "rows": []}

        class FakeVkmClient:
            def __init__(self, _config, dry_run=False):
                pass

            def connect(self):
                pass

            def verify_queued_customer(self, row):
                calls.append(("verify", row["cliente_id"], row["vkm_cuenta_id"]))
                return {
                    "cliente_id": row["cliente_id"],
                    "customer_code": row["cliente_id"],
                    "status": "confirmed",
                    "ineest": "2",
                    "codigo_valkimia": f"VKM-{row['vkm_cuenta_id']}",
                    "vkm_id": f"VKM-{row['vkm_cuenta_id']}",
                }

            def close(self):
                pass

        with self._patch_settings(), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient):
            exit_code = main_module.main([])

        self.assertEqual(exit_code, 0)
        self.assertIn(("verify", "C009", "88"), calls)
        self.assertIn(("verify", "C010", "99"), calls)
        self.assertIn(
            (
                "confirm",
                "confirmed",
                [99, 100],
                [
                    {"id": 99, "customer_code": "C009", "codigo_valkimia": "VKM-88"},
                    {"id": 100, "customer_code": "C010", "codigo_valkimia": "VKM-99"},
                ],
            ),
            calls,
        )

    def test_manual_mode_does_not_export_from_dashboard(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", suffix=".csv", delete=False) as handle:
            handle.write("cliente_id;nombre;direccion;localidad;provincia;codigo_postal;vkm_cuenta_id\n")
            handle.write("C001;Cliente Uno;Calle 1;Rosario;Santa Fe;2000;987\n")
            csv_path = handle.name

        calls = []

        class FakeDepositoApiClient:
            def __init__(self, _config, dry_run=False):
                pass

            def export_pending_customers(self, **_kwargs):
                raise AssertionError("manual mode must not export dashboard customers")

            def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None):
                calls.append(("confirm", request_id, status, error_detail))
                return {"updated": 1}

        class FakeVkmClient:
            def __init__(self, _config, dry_run=False):
                pass

            def connect(self):
                pass

            def create_or_confirm_customer(self, _row):
                calls.append(("vkm_cuenta_id", _row["vkm_cuenta_id"]))
                return {"cliente_id": _row["cliente_id"], "status": "queued"}

            def close(self):
                pass

        try:
            with self._patch_settings(), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient), patch("src.main.write_customers_backup_csv") as write_csv_mock:
                exit_code = main_module.main(["--csv-path", csv_path, "--request-id", "req-manual"])
        finally:
            Path(csv_path).unlink()

        self.assertEqual(exit_code, 0)
        self.assertIn(("vkm_cuenta_id", "987"), calls)
        self.assertEqual(calls[-1], ("confirm", "req-manual", "queued", ""))
        write_csv_mock.assert_not_called()

    def test_final_confirmation_sends_partial_when_some_rows_fail(self):
        class FakeDepositoApiClient:
            sent = []

            def __init__(self, _config, dry_run=False):
                pass

            def export_pending_customers(self, **_kwargs):
                return {"request_id": "req-partial", "updated": 2, "rows": [{**_valid_row("C001"), "id": 101}, {**_valid_row("C002"), "id": 102}]}

            def list_queued_customers(self, **_kwargs):
                return {"rows": []}

            def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None):
                self.sent.append((request_id, status, error_detail, ids))
                return {"updated": 1}

        class FakeVkmClient:
            def __init__(self, _config, dry_run=False):
                pass

            def connect(self):
                pass

            def create_or_confirm_customer(self, row):
                if row["cliente_id"] == "C002":
                    raise RuntimeError("rechazado")
                return {"cliente_id": row["cliente_id"], "status": "queued"}

            def verify_queued_customer(self, row):
                return {"cliente_id": row["cliente_id"], "status": "queued"}

            def close(self):
                pass

        with self._patch_settings(), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient):
            exit_code = main_module.main([])

        self.assertEqual(exit_code, 3)
        self.assertEqual(FakeDepositoApiClient.sent[0][1], "queued")
        self.assertEqual(FakeDepositoApiClient.sent[1][1], "error")
        self.assertIn("rechazado", FakeDepositoApiClient.sent[1][2])

    def test_final_confirmation_sends_error_when_all_rows_fail(self):
        class FakeDepositoApiClient:
            sent = []

            def __init__(self, _config, dry_run=False):
                pass

            def export_pending_customers(self, **_kwargs):
                return {"request_id": "req-error", "updated": 1, "rows": [{**_valid_row(), "id": 201}]}

            def list_queued_customers(self, **_kwargs):
                return {"rows": []}

            def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None):
                self.sent.append((request_id, status, error_detail, ids))
                return {"updated": 1}

        class FakeVkmClient:
            def __init__(self, _config, dry_run=False):
                pass

            def connect(self):
                pass

            def create_or_confirm_customer(self, _row):
                raise RuntimeError("caido")

            def verify_queued_customer(self, row):
                return {"cliente_id": row["cliente_id"], "status": "queued"}

            def close(self):
                pass

        with self._patch_settings(), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient):
            exit_code = main_module.main([])

        self.assertEqual(exit_code, 1)
        self.assertEqual(FakeDepositoApiClient.sent[0][1], "error")
        self.assertIn("caido", FakeDepositoApiClient.sent[0][2])


class CustomerSyncConfirmationTests(unittest.TestCase):
    def test_confirm_processed_rows_sends_customer_mappings_only_for_confirmed_rows(self):
        calls = []

        class FakeDepositoClient:
            def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None, customer_mappings=None):
                calls.append((request_id, status, error_detail, ids, customer_mappings))
                return {"updated": len(ids or [])}

        result = ProcessingResult(
            ok_count=2,
            error_count=1,
            errors=["fila 4"],
            row_results=[
                {
                    "row": {**_valid_row("C001"), "id": 10},
                    "cliente_id": "C001",
                    "customer_code": "C001",
                    "status": "confirmed",
                    "codigo_valkimia": "501",
                    "vkm_id": 501,
                },
                {
                    "row": {**_valid_row("C002"), "id": 11},
                    "cliente_id": "C002",
                    "status": "queued",
                },
                {
                    "row": {**_valid_row("C003"), "id": 12},
                    "cliente_id": "C003",
                    "status": "error",
                    "error": "rechazado",
                },
            ],
        )

        status = main_module.confirm_processed_rows(FakeDepositoClient(), "req-123", result, "fila 4")

        self.assertEqual(status, "partial")
        self.assertEqual(
            calls,
            [
                (
                    "",
                    "confirmed",
                    "",
                    [10],
                    [{"id": 10, "customer_code": "C001", "codigo_valkimia": "501"}],
                ),
                ("", "queued", "", [11], None),
                ("", "error", "fila 4", [12], None),
            ],
        )

    def test_confirm_processed_rows_preserves_manual_request_confirmation_without_mappings(self):
        calls = []

        class FakeDepositoClient:
            def confirm_customer_sync(self, request_id="", status="", error_detail="", ids=None, customer_mappings=None):
                calls.append((request_id, status, error_detail, ids, customer_mappings))
                return {"updated": 1}

        result = ProcessingResult(
            ok_count=1,
            error_count=0,
            errors=[],
            row_results=[
                {
                    "row": _valid_row("C001"),
                    "cliente_id": "C001",
                    "customer_code": "C001",
                    "status": "confirmed",
                    "codigo_valkimia": "501",
                }
            ],
        )

        status = main_module.confirm_processed_rows(FakeDepositoClient(), "req-manual", result, "")

        self.assertEqual(status, "confirmed")
        self.assertEqual(calls, [("req-manual", "confirmed", "", None, None)])


class DepositoApiClientTests(unittest.TestCase):
    def _patch_settings(self):
        return patch("src.main.load_settings", return_value=_settings())

    def test_confirm_customer_sync_includes_customer_mappings_only_when_present(self):
        client = DepositoApiClient(_settings().deposito_api, dry_run=True)

        with_mappings = client.confirm_customer_sync(
            status="confirmed",
            ids=[10],
            customer_mappings=[{"id": 10, "customer_code": "C001", "codigo_valkimia": "501"}],
        )
        without_mappings = client.confirm_customer_sync(status="queued", ids=[11])

        self.assertEqual(
            with_mappings["payload"],
            {
                "request_id": "",
                "status": "confirmed",
                "error_detail": "",
                "queue_type": "customers",
                "ids": [10],
                "customer_mappings": [{"id": 10, "customer_code": "C001", "codigo_valkimia": "501"}],
            },
        )
        self.assertEqual(
            without_mappings["payload"],
            {
                "request_id": "",
                "status": "queued",
                "error_detail": "",
                "queue_type": "customers",
                "ids": [11],
            },
        )

    def test_dry_run_does_not_touch_backend_or_vkm(self):
        settings = _settings()
        settings.dry_run = True

        with patch("src.main.load_settings", return_value=settings), patch("src.main.DepositoApiClient") as deposito_mock, patch("src.main.VkmClient") as vkm_mock, patch("src.main.write_customers_backup_csv") as write_csv_mock:
            exit_code = main_module.main([])

        self.assertEqual(exit_code, 0)
        deposito_mock.assert_not_called()
        vkm_mock.assert_not_called()
        write_csv_mock.assert_not_called()

    def test_automatic_mode_skips_when_lock_exists(self):
        with self._patch_settings(), patch("src.main._acquire_automatic_run_lock", return_value=None), patch("src.main.DepositoApiClient") as deposito_mock, patch("src.main.VkmClient") as vkm_mock:
            exit_code = main_module.main([])

        self.assertEqual(exit_code, 0)
        deposito_mock.assert_not_called()
        vkm_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
