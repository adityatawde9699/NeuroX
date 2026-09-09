import os
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

CONFIG = Path(__file__).parents[1] / "app" / "config.py"


@pytest.mark.parametrize("origin", ["", "http://care.example", "https://*.example", "https://care.example/path", "https://user:secret@care.example"])
def test_deployment_requires_exact_https_origins(monkeypatch, origin):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", origin)
    with pytest.raises(RuntimeError):
        runpy.run_path(str(CONFIG))


def test_unknown_environment_is_rejected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "prodution")
    with pytest.raises(RuntimeError):
        runpy.run_path(str(CONFIG))


@pytest.mark.parametrize("module,overrides,expected", [
    ("app.auth", {"JWT_SECRET": "short"}, "JWT_SECRET"),
    ("app.auth", {"JWT_SECRET": "replace-with-a-long-random-secret"}, "JWT_SECRET"),
    ("app.database", {"DATABASE_URL": "sqlite:///unused.db"}, "PostgreSQL DATABASE_URL"),
])
def test_deployment_rejects_unsafe_credentials_and_database(module, overrides, expected):
    env = {**os.environ, "APP_ENV": "production", "CORS_ORIGINS": "https://care.example", **overrides}
    result = subprocess.run([sys.executable, "-c", f"import {module}"], env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert expected in result.stderr
