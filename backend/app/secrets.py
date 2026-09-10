"""Read configuration from environment variables or mounted secret files."""

import os
from pathlib import Path


def setting(name: str, default: str | None = None) -> str | None:
    direct = os.getenv(name)
    secret_file = os.getenv(f"{name}_FILE")
    if direct is not None and secret_file:
        raise RuntimeError(f"Configure only one of {name} or {name}_FILE.")
    if not secret_file:
        return direct if direct is not None else default
    try:
        value = Path(secret_file).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Unable to read {name}_FILE.") from exc
    if not value:
        raise RuntimeError(f"{name}_FILE must not be empty.")
    return value
