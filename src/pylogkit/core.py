"""
Core logging runtime for PyLogKit.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger as _loguru_logger

from .config import (
    DEFAULT_APP_NAME,
    LogConfig,
)

if TYPE_CHECKING:
    from .qt_integration import LogSignalEmitter, QtLogHandler


DEFAULT_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
    "| <level>{level: <8}</level> "
    "| <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
    "| <level>{message}</level>"
)
DEFAULT_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} "
    "| {level: <8} "
    "| {name}:{function}:{line} "
    "| {message}"
)
DEFAULT_QT_FORMAT = "{time} | {level:<8} | {message}"

_UNSET = object()


class LoggingNotInitializedError(RuntimeError):
    """Raised when logging is used before init_logging()."""


def _is_audit_record(record: dict[str, Any]) -> bool:
    return bool(record["extra"].get("_pylogkit_audit"))


def _is_core_record(record: dict[str, Any]) -> bool:
    return not _is_audit_record(record)


class _InterceptHandler(logging.Handler):
    """Route standard logging records into Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = _loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        def patch_record(log_record: dict[str, Any]) -> None:
            log_record["name"] = record.module
            log_record["function"] = record.funcName
            log_record["line"] = record.lineno

        _loguru_logger.patch(patch_record).opt(
            depth=1, exception=record.exc_info
        ).log(level, record.getMessage())


class LogFacade:
    """User-facing facade for regular application logs."""

    def __init__(
        self,
        manager: LoggingManager,
        *,
        bound_logger: Any | None = None,
        options: dict[str, Any] | None = None,
        depth: int = 2,
    ) -> None:
        self._manager = manager
        self._bound_logger = bound_logger
        self._options = options or {}
        self._depth = depth

    def _resolve_logger(self) -> Any:
        self._manager.require_initialized()
        return self._bound_logger or self._manager.base_logger

    def _build_opt_kwargs(self) -> dict[str, Any]:
        opt_kwargs = dict(self._options)
        extra_depth = opt_kwargs.pop("depth", 0)
        if not isinstance(extra_depth, int):
            raise TypeError("log.opt(depth=...) expects an integer depth")
        opt_kwargs["depth"] = self._depth + extra_depth
        return opt_kwargs

    def _emit(self, method_name: str, message: str, *args: Any, **kwargs: Any) -> None:
        logger = self._resolve_logger()
        opt_logger = logger.opt(**self._build_opt_kwargs())
        getattr(opt_logger, method_name)(message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._emit("debug", message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._emit("info", message, *args, **kwargs)

    def success(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._emit("success", message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._emit("warning", message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._emit("error", message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._emit("critical", message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._emit("exception", message, *args, **kwargs)

    def bind(self, **kwargs: Any) -> LogFacade:
        return LogFacade(
            self._manager,
            bound_logger=self._resolve_logger().bind(**kwargs),
            options=dict(self._options),
            depth=self._depth,
        )

    def opt(self, **kwargs: Any) -> LogFacade:
        options = dict(self._options)
        if "depth" in kwargs and "depth" in options:
            existing_depth = options.get("depth", 0)
            requested_depth = kwargs["depth"]
            if not isinstance(existing_depth, int) or not isinstance(
                requested_depth, int
            ):
                raise TypeError("log.opt(depth=...) expects an integer depth")
            kwargs = dict(kwargs)
            kwargs["depth"] = existing_depth + requested_depth
            options.pop("depth", None)
        options.update(kwargs)
        return LogFacade(
            self._manager,
            bound_logger=self._bound_logger,
            options=options,
            depth=self._depth,
        )


class AuditFacade:
    """User-facing facade for structured audit logs."""

    _LEVEL_TO_VALUE = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "SUCCESS": 25,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    def __init__(self, manager: LoggingManager, *, depth: int = 2) -> None:
        self._manager = manager
        self._depth = depth

    def _resolve_logger(self) -> Any:
        config = self._manager.require_initialized()
        if not config.audit_enabled:
            raise RuntimeError("Audit logging is disabled.")
        return self._manager.audit_logger

    def _log(self, level_name: str, action: str, **kwargs: Any) -> None:
        payload = {"action": action}
        payload.update(kwargs)
        record = {
            "timestamp": datetime.now().isoformat(),
            "level": self._LEVEL_TO_VALUE[level_name],
            "level_name": level_name,
            "action": action,
            "data": payload,
        }
        message = json.dumps(record, ensure_ascii=False, default=str)
        self._resolve_logger().opt(depth=self._depth).log(level_name, message)

    def debug(self, action: str, **kwargs: Any) -> None:
        self._log("DEBUG", action, **kwargs)

    def info(self, action: str, **kwargs: Any) -> None:
        self._log("INFO", action, **kwargs)

    def success(self, action: str, **kwargs: Any) -> None:
        self._log("SUCCESS", action, **kwargs)

    def warning(self, action: str, **kwargs: Any) -> None:
        self._log("WARNING", action, **kwargs)

    def error(self, action: str, **kwargs: Any) -> None:
        self._log("ERROR", action, **kwargs)

    def critical(self, action: str, **kwargs: Any) -> None:
        self._log("CRITICAL", action, **kwargs)


class LoggingManager:
    """Owns PyLogKit runtime state."""

    def __init__(self) -> None:
        self._logger = _loguru_logger
        self._config: LogConfig | None = None
        self._initialized = False
        self._root_handler: logging.Handler | None = None
        self._previous_root_handlers: list[logging.Handler] = []
        self._previous_root_level: int = logging.NOTSET

    @property
    def base_logger(self) -> Any:
        return self._logger

    @property
    def audit_logger(self) -> Any:
        return self._logger.bind(_pylogkit_audit=True)

    def require_initialized(self) -> LogConfig:
        if self._config is None or not self._initialized:
            raise LoggingNotInitializedError(
                "PyLogKit is not initialized. Call init_logging() at program startup."
            )
        return self._config

    def _build_config(
        self,
        app_name: str,
        *,
        level: str | None,
        log_dir: str | Path | None,
        rotation: str | None,
        retention: str | None,
        encoding: str | None,
        console_output: bool,
        file_output: bool,
        capture_stdlib: bool | object,
        audit_enabled: bool | object,
    ) -> LogConfig:
        env_config = LogConfig.from_env(app_name=app_name)
        resolved_capture_stdlib = (
            env_config.capture_stdlib
            if capture_stdlib is _UNSET
            else bool(capture_stdlib)
        )
        resolved_audit_enabled = (
            env_config.audit_enabled if audit_enabled is _UNSET else bool(audit_enabled)
        )

        return LogConfig(
            app_name=app_name or DEFAULT_APP_NAME,
            log_dir=log_dir if log_dir is not None else env_config.log_dir,
            level=level if level is not None else env_config.level,
            rotation=rotation if rotation is not None else env_config.rotation,
            retention=retention if retention is not None else env_config.retention,
            encoding=encoding if encoding is not None else env_config.encoding,
            console_output=console_output,
            file_output=file_output,
            capture_stdlib=resolved_capture_stdlib,
            audit_enabled=resolved_audit_enabled,
        )

    def _install_stdlib_bridge(self) -> None:
        root_logger = logging.getLogger()
        self._previous_root_handlers = list(root_logger.handlers)
        self._previous_root_level = root_logger.level
        self._root_handler = _InterceptHandler()
        root_logger.handlers = [self._root_handler]
        root_logger.setLevel(logging.NOTSET)

    def _remove_stdlib_bridge(self) -> None:
        if self._root_handler is None:
            return

        root_logger = logging.getLogger()
        root_logger.handlers = list(self._previous_root_handlers)
        root_logger.setLevel(self._previous_root_level)
        self._root_handler = None
        self._previous_root_handlers = []
        self._previous_root_level = logging.NOTSET

    def _configure_sinks(self, config: LogConfig) -> None:
        self._logger.remove()

        if config.console_output and sys.stdout is not None:
            self._logger.add(
                sys.stdout,
                level=config.level,
                format=DEFAULT_CONSOLE_FORMAT,
                enqueue=True,
                backtrace=True,
                diagnose=True,
                filter=_is_core_record,
            )

        if config.file_output:
            log_file = Path(config.log_dir) / f"{config.app_name}_{{time:YYYY-MM-DD}}.log"
            self._logger.add(
                str(log_file),
                level=config.level,
                format=DEFAULT_FILE_FORMAT,
                rotation=config.rotation,
                retention=config.retention,
                encoding=config.encoding,
                enqueue=True,
                backtrace=True,
                diagnose=True,
                compression="zip",
                filter=_is_core_record,
            )

        if config.audit_enabled:
            audit_file = config.audit_log_dir / "audit_{time:YYYY-MM-DD}.jsonl"
            self._logger.add(
                str(audit_file),
                level=config.level,
                format="{message}",
                rotation=config.rotation,
                retention=config.retention,
                encoding=config.encoding,
                enqueue=True,
                catch=True,
                filter=_is_audit_record,
            )

    def init_logging(
        self,
        app_name: str,
        *,
        level: str | None = None,
        log_dir: str | Path | None = None,
        rotation: str | None = None,
        retention: str | None = None,
        encoding: str | None = None,
        console_output: bool = True,
        file_output: bool = True,
        capture_stdlib: bool | object = _UNSET,
        audit_enabled: bool | object = _UNSET,
    ) -> None:
        config = self._build_config(
            app_name,
            level=level,
            log_dir=log_dir,
            rotation=rotation,
            retention=retention,
            encoding=encoding,
            console_output=console_output,
            file_output=file_output,
            capture_stdlib=capture_stdlib,
            audit_enabled=audit_enabled,
        )
        config.ensure_log_dirs()

        self._remove_stdlib_bridge()
        self._configure_sinks(config)

        if config.capture_stdlib:
            self._install_stdlib_bridge()

        self._config = config
        self._initialized = True

    def attach_qt(
        self,
        emitter: LogSignalEmitter | None = None,
        *,
        level: str | None = None,
        format_string: str | None = None,
    ) -> QtLogHandler:
        config = self.require_initialized()

        from .qt_integration import QtLogHandler, has_pyqt

        if not has_pyqt():
            raise RuntimeError(
                "PyQt support is not available. Install PyQt6 or PyQt5 before "
                "calling attach_qt()."
            )

        handler = QtLogHandler(
            emitter=emitter,
            format_string=format_string or DEFAULT_QT_FORMAT,
        )
        self._logger.add(
            lambda message: handler.emit(message.record),
            level=level or config.level,
            enqueue=True,
            catch=True,
            filter=_is_core_record,
        )
        return handler

    def shutdown_logging(self) -> None:
        self._remove_stdlib_bridge()
        self._logger.remove()
        self._config = None
        self._initialized = False


_logging_manager = LoggingManager()
log = LogFacade(_logging_manager)
audit = AuditFacade(_logging_manager)


def init_logging(
    app_name: str,
    *,
    level: str | None = None,
    log_dir: str | Path | None = None,
    rotation: str | None = None,
    retention: str | None = None,
    encoding: str | None = None,
    console_output: bool = True,
    file_output: bool = True,
    capture_stdlib: bool | object = _UNSET,
    audit_enabled: bool | object = _UNSET,
) -> None:
    _logging_manager.init_logging(
        app_name,
        level=level,
        log_dir=log_dir,
        rotation=rotation,
        retention=retention,
        encoding=encoding,
        console_output=console_output,
        file_output=file_output,
        capture_stdlib=capture_stdlib,
        audit_enabled=audit_enabled,
    )


def attach_qt(
    emitter: LogSignalEmitter | None = None,
    *,
    level: str | None = None,
    format_string: str | None = None,
) -> QtLogHandler:
    return _logging_manager.attach_qt(
        emitter=emitter,
        level=level,
        format_string=format_string,
    )


def shutdown_logging() -> None:
    _logging_manager.shutdown_logging()


__all__ = [
    "LoggingNotInitializedError",
    "LogFacade",
    "AuditFacade",
    "init_logging",
    "attach_qt",
    "shutdown_logging",
    "log",
    "audit",
]
