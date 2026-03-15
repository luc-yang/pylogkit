"""
Utility helpers for PyLogKit.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar, overload

F = TypeVar("F", bound=Callable[..., Any])


def _default_exception_logger(message: str) -> None:
    """Log an exception message through the active PyLogKit logger."""
    from .core import log

    log.opt(depth=-1).exception(message)


@overload
def catch_exceptions(func: F) -> F: ...


@overload
def catch_exceptions(
    *,
    logger_func: Callable[..., Any] | None = None,
    reraise: bool = True,
    message: str | None = None,
) -> Callable[[F], F]: ...


def catch_exceptions(
    func: F | None = None,
    *,
    logger_func: Callable[..., Any] | None = None,
    reraise: bool = True,
    message: str | None = None,
) -> F | Callable[[F], F]:
    """
    Decorate a function to log any exception raised during execution.
    """
    resolved_logger = logger_func or _default_exception_logger

    def decorator(target: F) -> F:
        @functools.wraps(target)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return target(*args, **kwargs)
            except Exception as exc:
                if message is None:
                    error_message = f"Function {target.__name__} raised an exception: {exc}"
                else:
                    error_message = f"{message}: {exc}"

                resolved_logger(error_message)
                if reraise:
                    raise
                return None

        return wrapper  # type: ignore[return-value]

    if func is None:
        return decorator
    return decorator(func)


__all__ = ["catch_exceptions"]
