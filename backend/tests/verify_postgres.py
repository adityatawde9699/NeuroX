"""
PostgreSQL migration smoke check.

This script is intentionally NOT a pytest test module so it never fails in the
standard CI run.  Run it manually when a PostgreSQL instance is available:

    POSTGRES_URL="postgresql+psycopg2://user:pass@localhost/neurox_test" \\
        python tests/verify_postgres.py

The script:
  1. Runs all Alembic migrations against the provided database (upgrade head).
  2. Connects via SQLAlchemy and asserts every expected table exists.
  3. Downgrades back to base to verify the down path.
  4. Prints PASSED or raises SystemExit(1) on failure.

If POSTGRES_URL is not set, the script exits 0 with an informational message.
"""

import os
import sys

POSTGRES_URL = os.environ.get("POSTGRES_URL")

if not POSTGRES_URL:
    print(
        "INFO: POSTGRES_URL is not set — skipping PostgreSQL migration verification.\n"
        "      Set POSTGRES_URL to a valid PostgreSQL connection string to run this check."
    )
    sys.exit(0)

# ── only import the heavy dependencies when actually running ──────────────────
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
import sqlalchemy as sa  # noqa: E402
from pathlib import Path  # noqa: E402

BACKEND_ROOT = Path(__file__).parent.parent
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"

EXPECTED_TABLES = {
    "users",
    "patients",
    "caregiver_patient_assignments",
    "emergency_contacts",
    "safety_settings",
    "location_updates",
    "safety_alerts",
    "sos_events",
    "refresh_sessions",
    "activity_sessions",
    "reminders",
    "sync_events",
}


def run() -> None:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", POSTGRES_URL)

    print(f"Connecting to: {POSTGRES_URL[:40]}…")

    # ── upgrade ──────────────────────────────────────────────────────────────
    print("Running: alembic upgrade head …")
    command.upgrade(cfg, "head")
    print("  upgrade OK")

    # ── inspect tables ───────────────────────────────────────────────────────
    engine = sa.create_engine(POSTGRES_URL)
    inspector = sa.inspect(engine)
    actual_tables = set(inspector.get_table_names())
    missing = EXPECTED_TABLES - actual_tables
    if missing:
        print(f"FAIL: missing tables after upgrade: {sorted(missing)}")
        sys.exit(1)
    # Verify next_difficulty column exists on patients
    patient_cols = {c["name"] for c in inspector.get_columns("patients")}
    if "next_difficulty" not in patient_cols:
        print("FAIL: patients.next_difficulty column missing after migration 002")
        sys.exit(1)
    print(f"  tables OK ({len(actual_tables)} present, including next_difficulty)")

    # ── downgrade ────────────────────────────────────────────────────────────
    print("Running: alembic downgrade base …")
    command.downgrade(cfg, "base")
    inspector2 = sa.inspect(engine)
    remaining = set(inspector2.get_table_names()) & EXPECTED_TABLES
    if remaining:
        print(f"FAIL: tables still present after downgrade: {sorted(remaining)}")
        sys.exit(1)
    print("  downgrade OK")

    engine.dispose()
    print("\nPASSED — Alembic migrations verified against PostgreSQL.")


if __name__ == "__main__":
    run()
