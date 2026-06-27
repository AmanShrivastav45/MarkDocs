from app.config import get_settings


def test_default_settings(monkeypatch):
    monkeypatch.delenv("MAX_UPLOAD_SIZE_MB", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    settings = get_settings()
    assert settings.max_upload_size_mb == 50
    assert settings.log_level == "INFO"


def test_settings_read_from_environment(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "10")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    settings = get_settings()
    assert settings.max_upload_size_mb == 10
    assert settings.log_level == "DEBUG"
