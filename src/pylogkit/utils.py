"""
日志工具模块，提供异常捕获装饰器等实用工具

功能特性：
1. 提供 catch_exceptions 装饰器，自动捕获并记录函数异常
2. 支持自定义日志函数、是否重新抛出异常、自定义消息等参数
3. 装饰器支持带括号和不带括号两种使用方式
4. 完整的类型注解支持

使用示例：

```python
from log.utils import catch_exceptions
from log import error

# 方式一：不带括号使用（使用默认参数）
@catch_exceptions
def func1():
    raise ValueError("测试异常")

# 方式二：带括号使用（自定义参数）
@catch_exceptions(reraise=False, message="操作失败")
def func2():
    raise ValueError("测试异常")

# 方式三：指定自定义日志函数
@catch_exceptions(logger_func=error, reraise=False)
def func3():
    raise ValueError("测试异常")
```
"""

import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar, overload

# 定义函数类型变量
F = TypeVar("F", bound=Callable[..., Any])

# 创建默认的日志记录器
_default_logger = logging.getLogger(__name__)


def _default_error_logger(message: str, *args: Any, **kwargs: Any) -> None:
    """
    默认的错误日志记录函数

    当未指定 logger_func 时，使用此函数记录错误信息。
    使用标准 logging 记录错误。

    Args:
        message: 日志消息
        *args: 位置参数
        **kwargs: 关键字参数
    """
    _default_logger.error(message, *args, **kwargs)


# 为了类型检查器能正确处理带括号和不带括号的情况，添加重载签名
@overload
def catch_exceptions(
    func: F,
) -> F: ...


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
    异常捕获装饰器，用于自动捕获函数执行过程中的异常并记录日志

    该装饰器支持两种使用方式：
    1. 不带括号：@catch_exceptions
    2. 带括号：@catch_exceptions() 或 @catch_exceptions(reraise=False)

    Args:
        func: 被装饰的函数，当装饰器不带括号时传入
        logger_func: 日志函数，用于记录异常信息，默认为 error 函数
        reraise: 是否在记录异常后重新抛出异常，默认为 True
        message: 自定义错误消息，如果为 None 则使用异常本身的描述

    Returns:
        装饰后的函数，或者装饰器工厂函数

    Raises:
        当 reraise=True 时，会重新抛出捕获的异常

    示例：
        >>> @catch_exceptions
        ... def my_function():
        ...     raise ValueError("发生错误")
        >>>
        >>> @catch_exceptions(reraise=False, message="自定义错误消息")
        ... def my_function2():
        ...     raise ValueError("发生错误")
    """
    # 如果 logger_func 未指定，使用默认的错误日志函数
    if logger_func is None:
        logger_func = _default_error_logger

    def decorator(func: F) -> F:
        """
        实际的装饰器函数

        Args:
            func: 被装饰的目标函数

        Returns:
            包装后的函数
        """

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """
            包装函数，负责捕获和处理异常

            Args:
                *args: 位置参数
                **kwargs: 关键字参数

            Returns:
                原函数的返回值

            Raises:
                Exception: 当 reraise=True 时，重新抛出捕获的异常
            """
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 构建错误消息
                if message is not None:
                    error_msg = f"{message}: {str(e)}"
                else:
                    error_msg = f"函数 {func.__name__} 执行异常: {str(e)}"

                # 记录异常日志
                logger_func(error_msg)

                # 根据 reraise 参数决定是否重新抛出异常
                if reraise:
                    raise

        return wrapper  # type: ignore[return-value]

    # 如果 func 为 None，说明装饰器带括号使用，返回装饰器函数
    # 如果 func 不为 None，说明装饰器不带括号使用，直接应用装饰器
    if func is None:
        return decorator
    else:
        return decorator(func)
