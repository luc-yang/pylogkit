from pathlib import Path

from pylogkit import LogConfig
from pylogkit.config import (
    ENV_LOG_AUDIT_ENABLED,
    ENV_LOG_CAPTURE_STDLIB,
    ENV_LOG_DIR,
    ENV_LOG_ENCODING,
    ENV_LOG_LEVEL,
    ENV_LOG_RETENTION,
    ENV_LOG_ROTATION,
    get_default_log_dir,
)


def test_get_default_log_dir_includes_app_name():
    log_dir = get_default_log_dir("demo-app")

    assert "demo-app" in str(log_dir)
    assert "logs" in str(log_dir)


def test_log_config_from_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv(ENV_LOG_LEVEL, "DEBUG")
    monkeypatch.setenv(ENV_LOG_DIR, str(tmp_path))
    monkeypatch.setenv(ENV_LOG_ROTATION, "5 MB")
    monkeypatch.setenv(ENV_LOG_RETENTION, "14 days")
    monkeypatch.setenv(ENV_LOG_ENCODING, "utf-16")
    monkeypatch.setenv(ENV_LOG_CAPTURE_STDLIB, "false")
    monkeypatch.setenv(ENV_LOG_AUDIT_ENABLED, "0")

    config = LogConfig.from_env(app_name="demo")

    assert config.app_name == "demo"
    assert config.log_dir == tmp_path
    assert config.level == "DEBUG"
    assert config.rotation == "5 MB"
    assert config.retention == "14 days"
    assert config.encoding == "utf-16"
    assert config.capture_stdlib is False
    assert config.audit_enabled is False


def test_log_config_ensure_log_dirs_falls_back(monkeypatch, tmp_path: Path):
    invalid_dir = tmp_path / "invalid" / "logs"
    config = LogConfig(app_name="demo", log_dir=invalid_dir)

    original_mkdir = Path.mkdir

    def fake_mkdir(self, *args, **kwargs):
        if self == invalid_dir:
            raise PermissionError("denied")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    config.ensure_log_dirs()

    assert Path(config.log_dir).exists()
    assert "logs" in str(config.log_dir)
