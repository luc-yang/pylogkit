"""
PyLogKit public package interface.
"""

from .config import LogConfig
from .core import (
    LoggingNotInitializedError,
    attach_qt,
    audit,
    init_logging,
    log,
    shutdown_logging,
)
from .utils import catch_exceptions

__version__ = "1.0.0"

__all__ = [
    "__version__",
    "LogConfig",
    "LoggingNotInitializedError",
    "attach_qt",
    "audit",
    "catch_exceptions",
    "init_logging",
    "log",
    "shutdown_logging",
]
