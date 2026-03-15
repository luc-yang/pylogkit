"""
Logging configuration helpers for PyLogKit.
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Environment variable names
ENV_LOG_LEVEL = "LOG_LEVEL"
ENV_LOG_DIR = "LOG_DIR"
ENV_LOG_ROTATION = "LOG_ROTATION"
ENV_LOG_RETENTION = "LOG_RETENTION"
ENV_LOG_ENCODING = "LOG_ENCODING"
ENV_LOG_APP_NAME = "LOG_APP_NAME"
ENV_LOG_CAPTURE_STDLIB = "LOG_CAPTURE_STDLIB"
ENV_LOG_AUDIT_ENABLED = "LOG_AUDIT_ENABLED"

# Default values
DEFAULT_LEVEL = "INFO"
DEFAULT_ROTATION = "10 MB"
DEFAULT_RETENTION = "7 days"
DEFAULT_ENCODING = "utf-8"
DEFAULT_APP_NAME = "app"

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def parse_env_bool(value: str | None, default: bool) -> bool:
    """Parse a boolean environment variable."""
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return default


def get_default_log_dir(app_name: str = DEFAULT_APP_NAME) -> Path:
    """
    Return the default log directory for the current platform.

    Paths:
    - Windows: %APPDATA%\\{app_name}\\logs
    - macOS: ~/Library/Application Support/{app_name}/logs
    - Linux/Unix: ~/.local/share/{app_name}/logs
    """
    system = platform.system()

    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / app_name / "logs"
        return Path.home() / "AppData" / "Roaming" / app_name / "logs"

    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / app_name / "logs"

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / app_name / "logs"
    return Path.home() / ".local" / "share" / app_name / "logs"


@dataclass(slots=True)
class LogConfig:
    """Resolved logging configuration used by the runtime."""

    app_name: str = DEFAULT_APP_NAME
    log_dir: Path | str | None = None
    level: str = DEFAULT_LEVEL
    rotation: str = DEFAULT_ROTATION
    retention: str = DEFAULT_RETENTION
    encoding: str = DEFAULT_ENCODING
    console_output: bool = True
    file_output: bool = True
    capture_stdlib: bool = True
    audit_enabled: bool = True

    def __post_init__(self) -> None:
        if self.log_dir is None:
            self.log_dir = get_default_log_dir(self.app_name)
        else:
            self.log_dir = Path(os.path.normpath(os.fspath(self.log_dir)))

        self.level = self.level.upper()

    @property
    def audit_log_dir(self) -> Path:
        return Path(self.log_dir) / "audit"

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_name": self.app_name,
            "log_dir": str(self.log_dir),
            "level": self.level,
            "rotation": self.rotation,
            "retention": self.retention,
            "encoding": self.encoding,
            "console_output": self.console_output,
            "file_output": self.file_output,
            "capture_stdlib": self.capture_stdlib,
            "audit_enabled": self.audit_enabled,
        }

    def ensure_log_dirs(self) -> None:
        """
        Ensure the configured log directory exists.

        If directory creation fails, fall back to the system temporary directory.
        """
        log_dir = Path(self.log_dir)
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            if self.audit_enabled:
                self.audit_log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            import tempfile

            fallback = Path(tempfile.gettempdir()) / self.app_name / "logs"
            fallback.mkdir(parents=True, exist_ok=True)
            object.__setattr__(self, "log_dir", fallback)
            if self.audit_enabled:
                self.audit_log_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls, app_name: str | None = None) -> LogConfig:
        """Build a configuration object from environment variables."""
        resolved_app_name = app_name or os.environ.get(
            ENV_LOG_APP_NAME, DEFAULT_APP_NAME
        )

        log_dir_env = os.environ.get(ENV_LOG_DIR)
        log_dir: Path | str | None
        if log_dir_env:
            log_dir = Path(os.path.normpath(log_dir_env))
        else:
            log_dir = get_default_log_dir(resolved_app_name)

        return cls(
            app_name=resolved_app_name,
            log_dir=log_dir,
            level=os.environ.get(ENV_LOG_LEVEL, DEFAULT_LEVEL),
            rotation=os.environ.get(ENV_LOG_ROTATION, DEFAULT_ROTATION),
            retention=os.environ.get(ENV_LOG_RETENTION, DEFAULT_RETENTION),
            encoding=os.environ.get(ENV_LOG_ENCODING, DEFAULT_ENCODING),
            capture_stdlib=parse_env_bool(
                os.environ.get(ENV_LOG_CAPTURE_STDLIB), True
            ),
            audit_enabled=parse_env_bool(
                os.environ.get(ENV_LOG_AUDIT_ENABLED), True
            ),
        )
