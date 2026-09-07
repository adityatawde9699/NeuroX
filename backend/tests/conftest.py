"""
conftest.py — shared test configuration.

Establishes a unique SQLite DATABASE_URL *before* any test module imports
app.main, so that running the full test suite (all modules together) does not
cause cross-module DATABASE_URL collision.

Each test module that needs a fresh database still manages its own TestClient
fixture and tmp file cleanup.  This conftest simply guarantees that the env var
is always set to a valid path before the first import happens.
"""
import os
from pathlib import Path
from uuid import uuid4

# Set a session-level default only if no URL has been provided already.
# Individual test modules that need isolation may override this inside
# their own module-level setup block.
if "DATABASE_URL" not in os.environ:
    _session_db = Path("/tmp") / f"neurox-session-{uuid4().hex}.sqlite3"
    os.environ["DATABASE_URL"] = f"sqlite:///{_session_db}"
