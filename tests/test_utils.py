"""
日志工具模块测试

测试 catch_exceptions 装饰器和相关工具函数
"""

import logging
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from pylogkit.utils import (
    _default_error_logger,
    _default_logger,
    catch_exceptions,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_logger() -> MagicMock:
    """
    创建模拟日志记录器

    Returns:
        MagicMock 对象
    """
    return MagicMock()


@pytest.fixture
def capture_logs() -> list:
    """
    捕获日志消息的列表

    Returns:
        用于存储日志消息的列表
    """
    return []


# =============================================================================
# catch_exceptions 装饰器测试 - 不带括号使用
# =============================================================================


class TestCatchExceptionsWithoutParentheses:
    """不带括号使用装饰器测试"""

    def test_without_parentheses_reraises_exception(self) -> None:
        """
        测试不带括号时重新抛出异常

        验证默认情况下异常会被重新抛出
        """

        @catch_exceptions
        def failing_function() -> None:
            """会抛出异常的测试函数"""
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()

    def test_without_parentheses_logs_exception(self, capture_logs: list) -> None:
        """
        测试不带括号时记录异常

        Args:
            capture_logs: 捕获日志的列表
        """

        @catch_exceptions
        def failing_function() -> None:
            """会抛出异常的测试函数"""
            raise ValueError("Test error")

        # 捕获日志
        with patch.object(_default_logger, "error") as mock_error:
            with pytest.raises(ValueError):
                failing_function()

            # 验证日志被记录
            mock_error.assert_called_once()
            log_message = mock_error.call_args[0][0]
            assert "failing_function" in log_message
            assert "Test error" in log_message

    def test_without_parentheses_successful_function(self) -> None:
        """
        测试不带括号时正常函数执行

        验证正常函数可以正常执行并返回结果
        """

        @catch_exceptions
        def successful_function(x: int, y: int) -> int:
            """正常执行的测试函数"""
            return x + y

        result = successful_function(2, 3)
        assert result == 5

    def test_without_parentheses_preserves_function_metadata(self) -> None:
        """
        测试不带括号时保留函数元数据

        验证装饰器正确保留被装饰函数的元数据
        """

        @catch_exceptions
        def my_function() -> None:
            """这是我的文档字符串"""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "这是我的文档字符串"


# =============================================================================
# catch_exceptions 装饰器测试 - 带括号使用
# =============================================================================


class TestCatchExceptionsWithParentheses:
    """带括号使用装饰器测试"""

    def test_with_parentheses_default_reraise(self) -> None:
        """
        测试带括号时默认重新抛出异常

        验证默认情况下异常会被重新抛出
        """

        @catch_exceptions()
        def failing_function() -> None:
            """会抛出异常的测试函数"""
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()

    def test_with_parentheses_no_reraise(self) -> None:
        """
        测试带括号时不重新抛出异常

        验证设置 reraise=False 时异常不会被抛出
        """

        @catch_exceptions(reraise=False)
        def failing_function() -> None:
            """会抛出异常的测试函数"""
            raise ValueError("Test error")

        # 不应该抛出异常
        result = failing_function()
        assert result is None

    def test_with_parentheses_custom_message(self) -> None:
        """
        测试带括号时自定义错误消息

        验证可以设置自定义错误消息
        """

        @catch_exceptions(reraise=False, message="自定义错误消息")
        def failing_function() -> None:
            """会抛出异常的测试函数"""
            raise ValueError("原始错误")

        with patch.object(_default_logger, "error") as mock_error:
            failing_function()

            log_message = mock_error.call_args[0][0]
            assert "自定义错误消息" in log_message
            assert "原始错误" in log_message

    def test_with_parentheses_custom_logger(self) -> None:
        """
        测试带括号时自定义日志函数

        验证可以使用自定义日志函数
        """
        custom_logger = MagicMock()

        @catch_exceptions(reraise=False, logger_func=custom_logger)
        def failing_function() -> None:
            """会抛出异常的测试函数"""
            raise ValueError("Test error")

        failing_function()

        custom_logger.assert_called_once()
        log_message = custom_logger.call_args[0][0]
        assert "failing_function" in log_message

    def test_with_parentheses_successful_function(self) -> None:
        """
        测试带括号时正常函数执行

        验证正常函数可以正常执行并返回结果
        """

        @catch_exceptions()
        def successful_function(x: int, y: int) -> int:
            """正常执行的测试函数"""
            return x * y

        result = successful_function(3, 4)
        assert result == 12


# =============================================================================
# 参数组合测试
# =============================================================================


class TestParameterCombinations:
    """参数组合测试"""

    def test_reraise_true_with_message(self) -> None:
        """
        测试 reraise=True 且带自定义消息

        验证异常被重新抛出且使用自定义消息
        """

        @catch_exceptions(reraise=True, message="操作失败")
        def failing_function() -> None:
            """会抛出异常的测试函数"""
            raise RuntimeError("系统错误")

        with patch.object(_default_logger, "error") as mock_error:
            with pytest.raises(RuntimeError):
                failing_function()

            log_message = mock_error.call_args[0][0]
            assert "操作失败" in log_message

    def test_all_parameters_combined(self) -> None:
        """
        测试所有参数组合

        验证可以同时使用所有参数
        """
        custom_logger = MagicMock()

        @catch_exceptions(
            logger_func=custom_logger,
            reraise=False,
            message="所有参数测试",
        )
        def failing_function() -> None:
            """会抛出异常的测试函数"""
            raise Exception("综合测试错误")

        result = failing_function()

        assert result is None
        custom_logger.assert_called_once()
        log_message = custom_logger.call_args[0][0]
        assert "所有参数测试" in log_message
        assert "综合测试错误" in log_message


# =============================================================================
# 函数参数传递测试
# =============================================================================


class TestFunctionArgumentPassing:
    """函数参数传递测试"""

    def test_positional_arguments(self) -> None:
        """
        测试位置参数传递

        验证位置参数正确传递给被装饰函数
        """

        @catch_exceptions(reraise=False)
        def function_with_args(a: int, b: int, c: int) -> int:
            """带位置参数的测试函数"""
            return a + b + c

        result = function_with_args(1, 2, 3)
        assert result == 6

    def test_keyword_arguments(self) -> None:
        """
        测试关键字参数传递

        验证关键字参数正确传递给被装饰函数
        """

        @catch_exceptions(reraise=False)
        def function_with_kwargs(x: int = 0, y: int = 0) -> int:
            """带关键字参数的测试函数"""
            return x * y

        result = function_with_kwargs(x=5, y=6)
        assert result == 30

    def test_mixed_arguments(self) -> None:
        """
        测试混合参数传递

        验证位置和关键字参数混合使用
        """

        @catch_exceptions(reraise=False)
        def function_with_mixed(a: int, b: int, c: int = 0) -> int:
            """带混合参数的测试函数"""
            return a + b + c

        result = function_with_mixed(1, 2, c=3)
        assert result == 6

    def test_args_and_kwargs(self) -> None:
        """
        测试 *args 和 **kwargs

        验证可变参数正确传递
        """

        @catch_exceptions(reraise=False)
        def function_with_varargs(*args: Any, **kwargs: Any) -> tuple:
            """带可变参数的测试函数"""
            return (args, kwargs)

        result = function_with_varargs(1, 2, 3, name="test", value=42)
        assert result == ((1, 2, 3), {"name": "test", "value": 42})


# =============================================================================
# 异常类型测试
# =============================================================================


class TestExceptionTypes:
    """异常类型测试"""

    def test_value_error(self) -> None:
        """
        测试 ValueError

        验证 ValueError 被正确处理
        """

        @catch_exceptions(reraise=False)
        def raise_value_error() -> None:
            """抛出 ValueError 的测试函数"""
            raise ValueError("Invalid value")

        with patch.object(_default_logger, "error") as mock_error:
            raise_value_error()
            assert "Invalid value" in mock_error.call_args[0][0]

    def test_type_error(self) -> None:
        """
        测试 TypeError

        验证 TypeError 被正确处理
        """

        @catch_exceptions(reraise=False)
        def raise_type_error() -> None:
            """抛出 TypeError 的测试函数"""
            raise TypeError("Invalid type")

        with patch.object(_default_logger, "error") as mock_error:
            raise_type_error()
            assert "Invalid type" in mock_error.call_args[0][0]

    def test_key_error(self) -> None:
        """
        测试 KeyError

        验证 KeyError 被正确处理
        """

        @catch_exceptions(reraise=False)
        def raise_key_error() -> None:
            """抛出 KeyError 的测试函数"""
            raise KeyError("missing_key")

        with patch.object(_default_logger, "error") as mock_error:
            raise_key_error()
            assert "missing_key" in mock_error.call_args[0][0]

    def test_attribute_error(self) -> None:
        """
        测试 AttributeError

        验证 AttributeError 被正确处理
        """

        @catch_exceptions(reraise=False)
        def raise_attribute_error() -> None:
            """抛出 AttributeError 的测试函数"""
            raise AttributeError("No such attribute")

        with patch.object(_default_logger, "error") as mock_error:
            raise_attribute_error()
            assert "No such attribute" in mock_error.call_args[0][0]

    def test_custom_exception(self) -> None:
        """
        测试自定义异常

        验证自定义异常被正确处理
        """

        class CustomError(Exception):
            """自定义异常类"""

            pass

        @catch_exceptions(reraise=False)
        def raise_custom() -> None:
            """抛出自定义异常的测试函数"""
            raise CustomError("Custom error message")

        with patch.object(_default_logger, "error") as mock_error:
            raise_custom()
            assert "Custom error message" in mock_error.call_args[0][0]

    def test_nested_exception(self) -> None:
        """
        测试嵌套异常

        验证异常链被正确处理
        """

        @catch_exceptions(reraise=False)
        def raise_nested() -> None:
            """抛出嵌套异常的测试函数"""
            try:
                raise ValueError("Inner error")
            except ValueError:
                raise RuntimeError("Outer error")

        with patch.object(_default_logger, "error") as mock_error:
            raise_nested()
            assert "Outer error" in mock_error.call_args[0][0]


# =============================================================================
# 默认日志记录器测试
# =============================================================================


class TestDefaultLogger:
    """默认日志记录器测试"""

    def test_default_error_logger_fallback(self) -> None:
        """
        测试默认错误日志记录器回退

        验证当 log 模块不可用时回退到标准 logging
        """
        with patch.dict("sys.modules", {"pylogkit": None, "pylogkit.logger": None}):
            # 直接测试 _default_error_logger 函数
            with patch.object(_default_logger, "error") as mock_error:
                _default_error_logger("Test message")
                mock_error.assert_called_once_with("Test message")

    def test_default_logger_instance(self) -> None:
        """
        测试默认日志记录器实例

        验证 _default_logger 是正确的 Logger 实例
        """
        assert isinstance(_default_logger, logging.Logger)
        assert _default_logger.name == "pylogkit.utils"


# =============================================================================
# 边界条件测试
# =============================================================================


class TestEdgeCases:
    """边界条件测试"""

    def test_empty_function(self) -> None:
        """
        测试空函数

        验证空函数被正确处理
        """

        @catch_exceptions(reraise=False)
        def empty_function() -> None:
            """空函数"""
            pass

        result = empty_function()
        assert result is None

    def test_function_returning_none(self) -> None:
        """
        测试返回 None 的函数

        验证返回 None 的函数被正确处理
        """

        @catch_exceptions(reraise=False)
        def return_none() -> None:
            """返回 None 的函数"""
            return None

        result = return_none()
        assert result is None

    def test_function_returning_false(self) -> None:
        """
        测试返回 False 的函数

        验证返回 False 的函数被正确处理
        """

        @catch_exceptions(reraise=False)
        def return_false() -> bool:
            """返回 False 的函数"""
            return False

        result = return_false()
        assert result is False

    def test_function_returning_empty_string(self) -> None:
        """
        测试返回空字符串的函数

        验证返回空字符串的函数被正确处理
        """

        @catch_exceptions(reraise=False)
        def return_empty() -> str:
            """返回空字符串的函数"""
            return ""

        result = return_empty()
        assert result == ""

    def test_function_with_unicode_in_name(self) -> None:
        """
        测试函数名包含 Unicode

        验证 Unicode 函数名被正确处理
        """

        @catch_exceptions(reraise=False)
        def 中文函数() -> None:
            """中文函数名"""
            raise ValueError("错误")

        with patch.object(_default_logger, "error") as mock_error:
            中文函数()
            log_message = mock_error.call_args[0][0]
            assert "中文函数" in log_message

    def test_exception_with_unicode_message(self) -> None:
        """
        测试异常消息包含 Unicode

        验证 Unicode 异常消息被正确处理
        """

        @catch_exceptions(reraise=False)
        def raise_unicode_error() -> None:
            """抛出 Unicode 异常的函数"""
            raise ValueError("错误消息 🚨")

        with patch.object(_default_logger, "error") as mock_error:
            raise_unicode_error()
            log_message = mock_error.call_args[0][0]
            assert "错误消息 🚨" in log_message

    def test_very_long_exception_message(self) -> None:
        """
        测试超长异常消息

        验证超长异常消息被正确处理
        """
        long_message = "A" * 10000

        @catch_exceptions(reraise=False)
        def raise_long_error() -> None:
            """抛出超长异常的函数"""
            raise ValueError(long_message)

        with patch.object(_default_logger, "error") as mock_error:
            raise_long_error()
            log_message = mock_error.call_args[0][0]
            assert long_message in log_message


# =============================================================================
# 装饰器堆叠测试
# =============================================================================


class TestDecoratorStacking:
    """装饰器堆叠测试"""

    def test_multiple_decorators(self) -> None:
        """
        测试多个装饰器

        验证装饰器可以与其他装饰器一起使用
        """

        def another_decorator(func):
            """另一个装饰器"""

            def wrapper(*args, **kwargs):
                return func(*args, **kwargs) * 2

            return wrapper

        @another_decorator
        @catch_exceptions(reraise=False)
        def decorated_function() -> int:
            """多层装饰的函数"""
            raise ValueError("Error")

        # 由于异常被捕获并返回 None，another_decorator 会尝试对 None 进行乘法操作
        # 这会抛出 TypeError
        with pytest.raises(TypeError):
            decorated_function()

    def test_same_decorator_multiple_times(self) -> None:
        """
        测试同一装饰器多次使用

        验证同一装饰器可以多次使用
        """

        # 内层重新抛出，外层捕获
        @catch_exceptions(reraise=False, message="外层")
        @catch_exceptions(reraise=True, message="内层")  # 重新抛出异常
        def double_decorated() -> None:
            """双重装饰的函数"""
            raise ValueError("Error")

        with patch.object(_default_logger, "error") as mock_error:
            double_decorated()
            # 应该被记录两次（内层抛出，外层捕获）
            assert mock_error.call_count == 2


# =============================================================================
# _default_error_logger 测试
# =============================================================================


class TestDefaultErrorLogger:
    """默认错误日志记录器测试"""

    def test_default_error_logger_with_import_error(self) -> None:
        """
        测试当 pylogkit.logger 导入失败时的回退

        验证当 logger 模块不可用时回退到标准 logging
        """
        # 模拟 ImportError
        with patch(
            "builtins.__import__",
            side_effect=ImportError("No module named 'pylogkit.logger'"),
        ):
            with patch.object(_default_logger, "error") as mock_error:
                _default_error_logger("Test message with import error")
                mock_error.assert_called_once_with("Test message with import error")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
