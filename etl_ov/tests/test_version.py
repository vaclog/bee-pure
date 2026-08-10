from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import version as version_module


class VersionTests(unittest.TestCase):
    def test_valid_version_file_returns_trimmed_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            version_path = Path(temp_dir) / "VERSION"
            version_path.write_text("1.2.3\n", encoding="utf-8")

            with patch("src.version.VERSION_FILE", version_path):
                self.assertEqual(version_module.get_version(), "1.2.3")

    def test_version_file_trims_surrounding_whitespace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            version_path = Path(temp_dir) / "VERSION"
            version_path.write_text("  2.0.0  \n", encoding="utf-8")

            with patch("src.version.VERSION_FILE", version_path):
                self.assertEqual(version_module.get_version(), "2.0.0")

    def test_missing_version_file_returns_unknown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            version_path = Path(temp_dir) / "VERSION"

            with patch("src.version.VERSION_FILE", version_path):
                self.assertEqual(version_module.get_version(), version_module.UNKNOWN_VERSION)

    def test_empty_version_file_returns_unknown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            version_path = Path(temp_dir) / "VERSION"
            version_path.write_text(" \n\t ", encoding="utf-8")

            with patch("src.version.VERSION_FILE", version_path):
                self.assertEqual(version_module.get_version(), version_module.UNKNOWN_VERSION)

    def test_read_error_returns_unknown(self):
        class BrokenVersionFile:
            def read_text(self, encoding="utf-8"):
                raise OSError("boom")

        with patch("src.version.VERSION_FILE", BrokenVersionFile()):
            self.assertEqual(version_module.get_version(), version_module.UNKNOWN_VERSION)

    def test_invalid_utf8_returns_unknown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            version_path = Path(temp_dir) / "VERSION"
            version_path.write_bytes(b"\xff\xfe\xfa")

            with patch("src.version.VERSION_FILE", version_path):
                self.assertEqual(version_module.get_version(), version_module.UNKNOWN_VERSION)


if __name__ == "__main__":
    unittest.main()
