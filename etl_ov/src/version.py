from pathlib import Path


VERSION_FILE = Path(__file__).resolve().parents[1] / "VERSION"
UNKNOWN_VERSION = "unknown"


def get_version() -> str:
    try:
        version = VERSION_FILE.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return UNKNOWN_VERSION
    return version or UNKNOWN_VERSION
