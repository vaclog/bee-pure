from pathlib import Path
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_settings


class ConfigTests(unittest.TestCase):
    def test_load_settings_reads_deposito_api_variables(self):
        with patch.dict(
            os.environ,
            {
                "DEPOSITO_API_BASE_URL": "http://deposito.test",
                "DEPOSITO_API_TOKEN": "deposito-token",
                "ETL_OV_NEW_CUSTOMER_PATH": "C:/tmp/clientes",
            },
            clear=False,
        ):
            settings = load_settings()

        self.assertEqual(settings.deposito_api.base_url, "http://deposito.test")
        self.assertEqual(settings.deposito_api.token, "deposito-token")
        self.assertEqual(settings.new_customer_path, "C:/tmp/clientes")


if __name__ == "__main__":
    unittest.main()
