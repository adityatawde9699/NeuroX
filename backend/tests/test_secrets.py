import pytest

from app.secrets import setting


def test_setting_reads_mounted_secret_file(tmp_path, monkeypatch):
    secret_file = tmp_path / "jwt"
    secret_file.write_text("private-value\n")
    monkeypatch.delenv("TEST_SECRET", raising=False)
    monkeypatch.setenv("TEST_SECRET_FILE", str(secret_file))
    assert setting("TEST_SECRET") == "private-value"


def test_setting_rejects_ambiguous_or_empty_secret(tmp_path, monkeypatch):
    secret_file = tmp_path / "empty"
    secret_file.write_text("")
    monkeypatch.setenv("TEST_SECRET", "direct")
    monkeypatch.setenv("TEST_SECRET_FILE", str(secret_file))
    with pytest.raises(RuntimeError, match="only one"):
        setting("TEST_SECRET")
    monkeypatch.delenv("TEST_SECRET")
    with pytest.raises(RuntimeError, match="must not be empty"):
        setting("TEST_SECRET")
