"""Keep revision history reproducible without importing today's model metadata."""

from pathlib import Path

from alembic import command
from alembic.config import Config
import sqlalchemy as sa


def test_revision_roundtrip_preserves_patient_data(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.attributes["database_url"] = url
    # An unrelated application URL must not redirect migration verification.
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'wrong.db'}")
    engine = sa.create_engine(url)
    try:
        command.upgrade(config, "20260907_001")
        assert "next_difficulty" not in {
            c["name"] for c in sa.inspect(engine).get_columns("patients")
        }
        with engine.begin() as db:
            db.execute(
                sa.text(
                    "INSERT INTO users (id,name,email,role,created_at) VALUES ('p','Patient','p@example.test','PATIENT',CURRENT_TIMESTAMP)"
                )
            )
            db.execute(
                sa.text(
                    "INSERT INTO patients (user_id,age,preferred_language) VALUES ('p',68,'English')"
                )
            )
            db.execute(
                sa.text(
                    "INSERT INTO refresh_sessions (id,user_id,expires_at,revoked) VALUES ('existing-session','p',CURRENT_TIMESTAMP,0)"
                )
            )
        command.upgrade(config, "head")
        with engine.connect() as db:
            assert (
                db.execute(
                    sa.text("SELECT next_difficulty FROM patients WHERE user_id='p'")
                ).scalar_one()
                == 2
            )
            assert (
                db.execute(
                    sa.text(
                        "SELECT family_id FROM refresh_sessions WHERE id='existing-session'"
                    )
                ).scalar_one()
                == "existing-session"
            )
            assert (
                db.execute(
                    sa.text("SELECT failed_login_attempts FROM users WHERE id='p'")
                ).scalar_one()
                == 0
            )
            assert db.execute(
                sa.text("SELECT email_verified FROM users WHERE id='p'")
            ).scalar_one()
            assert "account_tokens" in sa.inspect(engine).get_table_names()
        command.downgrade(config, "20260907_001")
        with engine.connect() as db:
            assert (
                db.execute(
                    sa.text("SELECT age FROM patients WHERE user_id='p'")
                ).scalar_one()
                == 68
            )
        command.upgrade(config, "head")
        command.downgrade(config, "base")
        assert set(sa.inspect(engine).get_table_names()) <= {"alembic_version"}
        assert not (tmp_path / "wrong.db").exists()
    finally:
        engine.dispose()


def test_initial_revision_is_frozen():
    revision = (
        Path(__file__).resolve().parents[1] / "alembic/versions/20260907_001_initial.py"
    )
    source = revision.read_text()
    assert "from app" not in source
    assert "create_all" not in source
    assert "drop_all" not in source
