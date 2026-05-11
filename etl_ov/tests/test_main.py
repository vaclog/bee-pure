from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import main as main_module
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

    def test_automatic_mode_marks_downloaded_before_confirming(self):
        calls = []

        class FakeDepositoApiClient:
            def __init__(self, _config, dry_run=False):
                self.dry_run = dry_run

            def export_pending_customers(self, **_kwargs):
                calls.append("export")
                return {"request_id": "req-auto", "updated": 1, "rows": [_valid_row()]}

            def confirm_customer_sync(self, request_id, status, error_detail=""):
                calls.append(("confirm", request_id, status, error_detail))
                return {"updated": 1}

        class FakeVkmClient:
            def __init__(self, _config, dry_run=False):
                pass

            def connect(self):
                calls.append("connect")

            def create_or_confirm_customer(self, row):
                calls.append(("vkm", row["cliente_id"]))

            def close(self):
                calls.append("close")

        with self._patch_settings(), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient):
            exit_code = main_module.main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls[0], "export")
        self.assertIn(("confirm", "req-auto", "confirmed", ""), calls)

    def test_automatic_mode_generates_backup_csv_when_path_is_configured(self):
        settings = _settings()
        with tempfile.TemporaryDirectory() as temp_dir:
            settings.new_customer_path = temp_dir

            class FakeDepositoApiClient:
                def __init__(self, _config, dry_run=False):
                    pass

                def export_pending_customers(self, **_kwargs):
                    return {"request_id": "req-auto", "updated": 1, "rows": [_valid_row()]}

                def confirm_customer_sync(self, request_id, status, error_detail=""):
                    return {"updated": 1}

            class FakeVkmClient:
                def __init__(self, _config, dry_run=False):
                    pass

                def connect(self):
                    pass

                def create_or_confirm_customer(self, _row):
                    pass

                def close(self):
                    pass

            with patch("src.main.load_settings", return_value=settings), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient):
                exit_code = main_module.main([])

            self.assertEqual(exit_code, 0)
            generated_files = list(Path(temp_dir).glob("clientes_nuevos_*.csv"))
            self.assertEqual(len(generated_files), 1)
            content = generated_files[0].read_text(encoding="utf-8")
            self.assertIn("cliente_id;nombre;direccion;localidad;provincia;codigo_postal;observacion;tipo;numero_documento;vkm_cuenta_id", content)
            self.assertIn("C001;Cliente Uno;Calle 1;Rosario;Santa Fe;2000;;;;987", content)

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

            def confirm_customer_sync(self, request_id, status, error_detail=""):
                calls.append(("confirm", request_id, status, error_detail))
                return {"updated": 1}

        class FakeVkmClient:
            def __init__(self, _config, dry_run=False):
                pass

            def connect(self):
                pass

            def create_or_confirm_customer(self, _row):
                calls.append(("vkm_cuenta_id", _row["vkm_cuenta_id"]))

            def close(self):
                pass

        try:
            with self._patch_settings(), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient), patch("src.main.write_customers_backup_csv") as write_csv_mock:
                exit_code = main_module.main(["--csv-path", csv_path, "--request-id", "req-manual"])
        finally:
            Path(csv_path).unlink()

        self.assertEqual(exit_code, 0)
        self.assertIn(("vkm_cuenta_id", "987"), calls)
        self.assertEqual(calls[-1], ("confirm", "req-manual", "confirmed", ""))
        write_csv_mock.assert_not_called()

    def test_final_confirmation_sends_partial_when_some_rows_fail(self):
        class FakeDepositoApiClient:
            sent = []

            def __init__(self, _config, dry_run=False):
                pass

            def export_pending_customers(self, **_kwargs):
                return {"request_id": "req-partial", "updated": 2, "rows": [_valid_row("C001"), _valid_row("C002")]}

            def confirm_customer_sync(self, request_id, status, error_detail=""):
                self.sent.append((request_id, status, error_detail))
                return {"updated": 1}

        class FakeVkmClient:
            def __init__(self, _config, dry_run=False):
                pass

            def connect(self):
                pass

            def create_or_confirm_customer(self, row):
                if row["cliente_id"] == "C002":
                    raise RuntimeError("rechazado")

            def close(self):
                pass

        with self._patch_settings(), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient):
            exit_code = main_module.main([])

        self.assertEqual(exit_code, 3)
        self.assertEqual(FakeDepositoApiClient.sent[0][0], "req-partial")
        self.assertEqual(FakeDepositoApiClient.sent[0][1], "partial")
        self.assertIn("rechazado", FakeDepositoApiClient.sent[0][2])

    def test_final_confirmation_sends_error_when_all_rows_fail(self):
        class FakeDepositoApiClient:
            sent = []

            def __init__(self, _config, dry_run=False):
                pass

            def export_pending_customers(self, **_kwargs):
                return {"request_id": "req-error", "updated": 1, "rows": [_valid_row()]}

            def confirm_customer_sync(self, request_id, status, error_detail=""):
                self.sent.append((request_id, status, error_detail))
                return {"updated": 1}

        class FakeVkmClient:
            def __init__(self, _config, dry_run=False):
                pass

            def connect(self):
                pass

            def create_or_confirm_customer(self, _row):
                raise RuntimeError("caido")

            def close(self):
                pass

        with self._patch_settings(), patch("src.main.DepositoApiClient", FakeDepositoApiClient), patch("src.main.VkmClient", FakeVkmClient):
            exit_code = main_module.main([])

        self.assertEqual(exit_code, 1)
        self.assertEqual(FakeDepositoApiClient.sent[0][1], "error")
        self.assertIn("caido", FakeDepositoApiClient.sent[0][2])

    def test_dry_run_does_not_touch_backend_or_vkm(self):
        settings = _settings()
        settings.dry_run = True

        with patch("src.main.load_settings", return_value=settings), patch("src.main.DepositoApiClient") as deposito_mock, patch("src.main.VkmClient") as vkm_mock, patch("src.main.write_customers_backup_csv") as write_csv_mock:
            exit_code = main_module.main([])

        self.assertEqual(exit_code, 0)
        deposito_mock.assert_not_called()
        vkm_mock.assert_not_called()
        write_csv_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
