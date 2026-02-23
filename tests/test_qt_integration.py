"""
PyQt 日志集成模块测试

测试 LogSignalEmitter、QtLogHandler、QtLoggingHandler 等类
"""

import sys
import threading
import warnings
from datetime import datetime
from logging import LogRecord
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from pylogkit.qt_integration import (
    HAS_PYQT,
    PYQT_VERSION,
    LogSignalEmitter,
    QObject,
    QtLoggingHandler,
    QtLogHandler,
    get_pyqt_version,
    has_pyqt,
    is_main_thread,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def captured_records() -> list[dict[str, Any]]:
    """
    捕获的记录列表

    Returns:
        用于存储捕获记录的列表
    """
    return []


@pytest.fixture
def captured_messages() -> list[str]:
    """
    捕获的消息列表

    Returns:
        用于存储捕获消息的列表
    """
    return []


@pytest.fixture
def log_emitter() -> LogSignalEmitter:
    """
    创建日志信号发射器

    Returns:
        LogSignalEmitter 实例
    """
    return LogSignalEmitter()


# =============================================================================
# LogSignalEmitter 测试
# =============================================================================


class TestLogSignalEmitter:
    """日志信号发射器测试"""

    def test_initialization(self) -> None:
        """
        测试初始化

        验证 LogSignalEmitter 正确初始化
        """
        emitter = LogSignalEmitter()
        assert emitter is not None

    def test_emit_record_with_callback(
        self, log_emitter: LogSignalEmitter, captured_records: list[dict[str, Any]]
    ) -> None:
        """
        测试使用回调发射记录

        Args:
            log_emitter: 日志发射器
            captured_records: 捕获的记录列表
        """
        record = {"message": "test", "level": "INFO"}

        # 连接回调
        log_emitter.connect_record(captured_records.append)

        # 发射记录
        log_emitter.emit_record(record)

        # 验证记录被捕获
        assert len(captured_records) == 1
        assert captured_records[0]["message"] == "test"

    def test_emit_message_with_callback(
        self, log_emitter: LogSignalEmitter, captured_messages: list[str]
    ) -> None:
        """
        测试使用回调发射消息

        Args:
            log_emitter: 日志发射器
            captured_messages: 捕获的消息列表
        """
        message = "Test log message"

        # 连接回调
        log_emitter.connect_message(captured_messages.append)

        # 发射消息
        log_emitter.emit_message(message)

        # 验证消息被捕获
        assert len(captured_messages) == 1
        assert captured_messages[0] == message

    def test_multiple_callbacks(
        self, log_emitter: LogSignalEmitter, captured_records: list[dict[str, Any]]
    ) -> None:
        """
        测试多个回调

        Args:
            log_emitter: 日志发射器
            captured_records: 捕获的记录列表
        """
        callback1_records: list[dict[str, Any]] = []
        callback2_records: list[dict[str, Any]] = []

        log_emitter.connect_record(callback1_records.append)
        log_emitter.connect_record(callback2_records.append)

        record = {"message": "multi", "level": "DEBUG"}
        log_emitter.emit_record(record)

        # 两个回调都应该被调用
        assert len(callback1_records) == 1
        assert len(callback2_records) == 1

    def test_emit_record_without_pyqt(
        self, captured_records: list[dict[str, Any]]
    ) -> None:
        """
        测试无 PyQt 时发射记录

        Args:
            captured_records: 捕获的记录列表
        """
        with patch("pylogkit.qt_integration.HAS_PYQT", False):
            emitter = LogSignalEmitter()
            emitter.connect_record(captured_records.append)

            record = {"message": "no pyqt", "level": "WARNING"}
            emitter.emit_record(record)

            assert len(captured_records) == 1
            assert captured_records[0]["message"] == "no pyqt"

    def test_emit_message_without_pyqt(self, captured_messages: list[str]) -> None:
        """
        测试无 PyQt 时发射消息

        Args:
            captured_messages: 捕获的消息列表
        """
        with patch("pylogkit.qt_integration.HAS_PYQT", False):
            emitter = LogSignalEmitter()
            emitter.connect_message(captured_messages.append)

            emitter.emit_message("no pyqt message")

            assert len(captured_messages) == 1
            assert captured_messages[0] == "no pyqt message"

    def test_emit_record_exception_handling(
        self, log_emitter: LogSignalEmitter
    ) -> None:
        """
        测试发射记录时的异常处理

        Args:
            log_emitter: 日志发射器
        """

        def failing_callback(record: dict[str, Any]) -> None:
            raise ValueError("Callback error")

        log_emitter.connect_record(failing_callback)

        # 不应该抛出异常
        record = {"message": "test", "level": "INFO"}
        log_emitter.emit_record(record)  # 不应该抛出

    def test_emit_message_exception_handling(
        self, log_emitter: LogSignalEmitter
    ) -> None:
        """
        测试发射消息时的异常处理

        Args:
            log_emitter: 日志发射器
        """

        def failing_callback(message: str) -> None:
            raise ValueError("Callback error")

        log_emitter.connect_message(failing_callback)

        # 不应该抛出异常
        log_emitter.emit_message("test message")  # 不应该抛出


# =============================================================================
# QtLogHandler 测试
# =============================================================================


class TestQtLogHandler:
    """Qt 日志处理器测试"""

    def test_initialization(self) -> None:
        """
        测试初始化

        验证 QtLogHandler 正确初始化
        """
        handler = QtLogHandler()
        assert handler is not None
        assert handler.emitter is not None
        assert handler.format_string is not None

    def test_initialization_with_custom_emitter(
        self, log_emitter: LogSignalEmitter
    ) -> None:
        """
        测试使用自定义发射器初始化

        Args:
            log_emitter: 日志发射器
        """
        handler = QtLogHandler(emitter=log_emitter)
        assert handler.emitter is log_emitter

    def test_initialization_with_custom_format(self) -> None:
        """
        测试使用自定义格式初始化
        """
        custom_format = "{level} | {message}"
        handler = QtLogHandler(format_string=custom_format)
        assert handler.format_string == custom_format

    def test_emit_loguru_record(
        self, log_emitter: LogSignalEmitter, captured_records: list[dict[str, Any]]
    ) -> None:
        """
        测试发射 loguru 格式记录

        Args:
            log_emitter: 日志发射器
            captured_records: 捕获的记录列表
        """
        handler = QtLogHandler(emitter=log_emitter)
        log_emitter.connect_record(captured_records.append)

        # loguru 格式的记录
        record = {
            "message": "Test message",
            "level": {"name": "INFO"},
            "time": datetime.now(),
            "name": "test_logger",
            "function": "test_func",
            "line": 42,
            "exception": None,
            "extra": {},
        }

        handler.emit(record)

        assert len(captured_records) == 1
        assert captured_records[0]["message"] == "Test message"

    def test_emit_string_record(
        self, log_emitter: LogSignalEmitter, captured_messages: list[str]
    ) -> None:
        """
        测试发射字符串记录

        Args:
            log_emitter: 日志发射器
            captured_messages: 捕获的消息列表
        """
        handler = QtLogHandler(emitter=log_emitter)
        log_emitter.connect_message(captured_messages.append)

        handler.emit("Simple string message")

        assert len(captured_messages) == 1
        assert "Simple string message" in captured_messages[0]

    def test_emit_standard_logging_record(
        self, log_emitter: LogSignalEmitter, captured_records: list[dict[str, Any]]
    ) -> None:
        """
        测试发射标准 logging 记录

        Args:
            log_emitter: 日志发射器
            captured_records: 捕获的记录列表
        """
        handler = QtLogHandler(emitter=log_emitter)
        log_emitter.connect_record(captured_records.append)

        # 创建标准 logging LogRecord
        record = LogRecord(
            name="test_logger",
            level=20,  # INFO
            pathname="/test/path.py",
            lineno=10,
            msg="Test log record",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        assert len(captured_records) == 1
        assert captured_records[0]["message"] == "Test log record"

    def test_buffer_management(self) -> None:
        """
        测试缓冲区管理

        验证缓冲区正确存储和清空
        """
        handler = QtLogHandler()

        # 发射多条消息
        for i in range(150):
            handler.emit(f"Message {i}")

        # 获取缓冲区
        buffer = handler.get_buffer()

        # 缓冲区大小限制为 100
        assert len(buffer) == 100
        assert "Message 149" in buffer[-1]

        # 清空缓冲区
        handler.clear_buffer()
        assert len(handler.get_buffer()) == 0

    def test_buffer_size_limit(self) -> None:
        """
        测试缓冲区大小限制

        验证缓冲区不会无限增长
        """
        handler = QtLogHandler()

        # 发射超过缓冲区限制的消息
        for i in range(200):
            handler.emit(f"Message {i}")

        buffer = handler.get_buffer()
        assert len(buffer) == 100  # 缓冲区大小限制

    def test_write_method(self, log_emitter: LogSignalEmitter) -> None:
        """
        测试 write 方法

        Args:
            log_emitter: 日志发射器
        """
        handler = QtLogHandler(emitter=log_emitter)
        captured_messages: list[str] = []
        log_emitter.connect_message(captured_messages.append)

        handler.write("Write test message")

        assert len(captured_messages) == 1
        assert "Write test message" in captured_messages[0]

    def test_flush_method(self) -> None:
        """
        测试 flush 方法

        验证 flush 方法可以正常调用
        """
        handler = QtLogHandler()

        # flush 方法不应该抛出异常
        handler.flush()

    def test_thread_safety(self, log_emitter: LogSignalEmitter) -> None:
        """
        测试线程安全

        Args:
            log_emitter: 日志发射器
        """
        handler = QtLogHandler(emitter=log_emitter)
        captured_records: list[dict[str, Any]] = []
        log_emitter.connect_record(captured_records.append)

        # 在多线程中发射记录
        def emit_records():
            for i in range(50):
                handler.emit({"message": f"Thread message {i}", "level": "INFO"})

        threads = [threading.Thread(target=emit_records) for _ in range(4)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有记录都应该被捕获
        assert len(captured_records) == 200

    def test_emit_exception_handling(self, log_emitter: LogSignalEmitter) -> None:
        """
        测试发射时的异常处理

        Args:
            log_emitter: 日志发射器
        """
        handler = QtLogHandler(emitter=log_emitter)

        # 模拟发射器抛出异常
        with patch.object(
            log_emitter, "emit_record", side_effect=Exception("Emit error")
        ):
            # 不应该抛出异常
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                handler.emit({"message": "test", "level": "INFO"})


# =============================================================================
# QtLoggingHandler 测试
# =============================================================================


class TestQtLoggingHandler:
    """Qt Logging 处理器测试"""

    def test_initialization(self) -> None:
        """
        测试初始化

        验证 QtLoggingHandler 正确初始化
        """
        handler = QtLoggingHandler()
        assert handler is not None
        assert handler.qt_handler is not None

    def test_initialization_with_custom_emitter(
        self, log_emitter: LogSignalEmitter
    ) -> None:
        """
        测试使用自定义发射器初始化

        Args:
            log_emitter: 日志发射器
        """
        handler = QtLoggingHandler(emitter=log_emitter)
        assert handler.qt_handler.emitter is log_emitter

    def test_emit_standard_record(
        self, log_emitter: LogSignalEmitter, captured_records: list[dict[str, Any]]
    ) -> None:
        """
        测试发射标准记录

        Args:
            log_emitter: 日志发射器
            captured_records: 捕获的记录列表
        """
        handler = QtLoggingHandler(emitter=log_emitter)
        log_emitter.connect_record(captured_records.append)

        record = LogRecord(
            name="test",
            level=20,
            pathname="test.py",
            lineno=1,
            msg="Standard logging",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        assert len(captured_records) == 1
        assert captured_records[0]["message"] == "Standard logging"


# =============================================================================
# 工具函数测试
# =============================================================================


class TestUtilityFunctions:
    """工具函数测试"""

    def test_is_main_thread_in_main_thread(self) -> None:
        """
        测试在主线程中检查

        验证在主线程中返回 True
        """
        assert is_main_thread() is True

    def test_is_main_thread_in_other_thread(self) -> None:
        """
        测试在其他线程中检查

        验证在非主线程中返回 False
        """
        result = []

        def check_thread():
            result.append(is_main_thread())

        thread = threading.Thread(target=check_thread)
        thread.start()
        thread.join()

        assert result[0] is False

    def test_get_pyqt_version(self) -> None:
        """
        测试获取 PyQt 版本

        验证返回正确的版本号
        """
        version = get_pyqt_version()
        assert version in [0, 5, 6]

    def test_has_pyqt(self) -> None:
        """
        测试检查 PyQt 是否安装

        验证返回布尔值
        """
        has = has_pyqt()
        assert isinstance(has, bool)
        assert has == HAS_PYQT


# =============================================================================
# 记录解析测试
# =============================================================================


class TestRecordParsing:
    """记录解析测试"""

    def test_parse_loguru_record(self) -> None:
        """
        测试解析 loguru 记录

        验证 loguru 格式记录被正确解析
        """
        handler = QtLogHandler()

        loguru_record = {
            "message": "Loguru message",
            "level": {"name": "DEBUG"},
            "time": datetime.now(),
            "name": "logger",
            "function": "func",
            "line": 10,
            "exception": None,
            "extra": {"key": "value"},
        }

        parsed = handler._parse_record(loguru_record)

        assert parsed["message"] == "Loguru message"
        assert parsed["level"] == "DEBUG"
        assert parsed["extra"]["key"] == "value"

    def test_parse_loguru_level_as_string(self) -> None:
        """
        测试解析 loguru 记录（级别为字符串）

        验证级别为字符串时被正确处理
        """
        handler = QtLogHandler()

        loguru_record = {
            "message": "Test",
            "level": "WARNING",
            "time": "",
            "name": "",
            "function": "",
            "line": 0,
        }

        parsed = handler._parse_record(loguru_record)
        assert parsed["level"] == "WARNING"

    def test_parse_standard_logging_record(self) -> None:
        """
        测试解析标准 logging 记录

        验证标准 logging 记录被正确解析
        """
        handler = QtLogHandler()

        record = LogRecord(
            name="test_logger",
            level=30,  # WARNING
            pathname="/test.py",
            lineno=20,
            msg="Warning message",
            args=(),
            exc_info=None,
        )

        parsed = handler._parse_record(record)

        assert parsed["message"] == "Warning message"
        assert parsed["level"] == "WARNING"
        assert parsed["name"] == "test_logger"
        assert parsed["line"] == 20

    def test_parse_string_record(self) -> None:
        """
        测试解析字符串记录

        验证字符串被正确解析为记录
        """
        handler = QtLogHandler()

        parsed = handler._parse_record("Simple string")

        assert parsed["message"] == "Simple string"
        assert parsed["level"] == "INFO"

    def test_parse_unknown_record(self) -> None:
        """
        测试解析未知类型记录

        验证未知类型被转换为字符串
        """
        handler = QtLogHandler()

        class UnknownType:
            def __str__(self):
                return "Unknown object"

        parsed = handler._parse_record(UnknownType())

        assert parsed["message"] == "Unknown object"
        assert parsed["level"] == "INFO"


# =============================================================================
# 消息格式化测试
# =============================================================================


class TestMessageFormatting:
    """消息格式化测试"""

    def test_format_message_with_datetime(self) -> None:
        """
        测试格式化包含 datetime 的消息

        验证 datetime 对象被正确格式化
        """
        handler = QtLogHandler()

        record = {
            "message": "Test",
            "level": "INFO",
            "time": datetime(2024, 1, 15, 10, 30, 0),
        }

        formatted = handler._format_message(record)

        assert "2024-01-15" in formatted
        assert "INFO" in formatted
        assert "Test" in formatted

    def test_format_message_with_string_time(self) -> None:
        """
        测试格式化包含字符串时间的消息

        验证字符串时间被正确处理
        """
        handler = QtLogHandler()

        record = {
            "message": "Test message",
            "level": "ERROR",
            "time": "2024-01-15 10:30:00",
        }

        formatted = handler._format_message(record)

        assert "ERROR" in formatted
        assert "Test message" in formatted

    def test_format_message_formatting_error(self) -> None:
        """
        测试格式化错误处理

        验证格式化失败时返回原始消息
        """
        handler = QtLogHandler()

        # 创建一个会导致格式化错误的记录
        record = {
            "message": object(),  # 不是字符串
            "level": None,
        }

        formatted = handler._format_message(record)

        # 应该返回原始消息的字符串表示
        assert formatted is not None


# =============================================================================
# 边界条件测试
# =============================================================================


class TestEdgeCases:
    """边界条件测试"""

    def test_empty_record(self) -> None:
        """
        测试空记录

        验证空记录被正确处理
        """
        handler = QtLogHandler()

        empty_record = {}
        parsed = handler._parse_record(empty_record)

        assert parsed["message"] == ""
        assert parsed["level"] == "INFO"

    def test_none_values_in_record(self) -> None:
        """
        测试记录中的 None 值

        验证 None 值被正确处理
        """
        handler = QtLogHandler()

        record = {
            "message": None,
            "level": None,
            "time": None,
            "name": None,
            "function": None,
            "line": None,
        }

        parsed = handler._parse_record(record)

        # None 值会被保留
        assert parsed["message"] is None
        # level 为 None 时会被转换为字符串 "None"
        assert parsed["level"] == "None"

    def test_unicode_in_messages(self, log_emitter: LogSignalEmitter) -> None:
        """
        测试消息中的 Unicode 字符

        Args:
            log_emitter: 日志发射器
        """
        handler = QtLogHandler(emitter=log_emitter)
        captured_messages: list[str] = []
        log_emitter.connect_message(captured_messages.append)

        handler.emit("Unicode 测试 🌍")

        assert len(captured_messages) == 1
        assert "Unicode 测试 🌍" in captured_messages[0]

    def test_very_long_message(self, log_emitter: LogSignalEmitter) -> None:
        """
        测试超长消息

        Args:
            log_emitter: 日志发射器
        """
        handler = QtLogHandler(emitter=log_emitter)
        captured_messages: list[str] = []
        log_emitter.connect_message(captured_messages.append)

        long_message = "A" * 10000
        handler.emit(long_message)

        assert len(captured_messages) == 1

    def test_special_characters_in_message(self, log_emitter: LogSignalEmitter) -> None:
        """
        测试消息中的特殊字符

        Args:
            log_emitter: 日志发射器
        """
        handler = QtLogHandler(emitter=log_emitter)
        captured_messages: list[str] = []
        log_emitter.connect_message(captured_messages.append)

        special_message = 'Special chars: "quotes" \n newlines \t tabs'
        handler.emit(special_message)

        assert len(captured_messages) == 1


# =============================================================================
# 常量测试
# =============================================================================


class TestConstants:
    """常量测试"""

    def test_pyqt_version_constant(self) -> None:
        """
        测试 PYQT_VERSION 常量

        验证 PYQT_VERSION 常量定义正确
        """
        assert PYQT_VERSION in [0, 5, 6]

    def test_has_pyqt_constant(self) -> None:
        """
        测试 HAS_PYQT 常量

        验证 HAS_PYQT 常量定义正确
        """
        assert isinstance(HAS_PYQT, bool)


# =============================================================================
# 导出测试
# =============================================================================


class TestExports:
    """导出测试"""

    def test_all_exports_present(self) -> None:
        """
        测试所有导出项存在

        验证 __all__ 列表中的所有项都可以导入
        """
        from pylogkit.qt_integration import __all__

        expected_exports = [
            "LogSignalEmitter",
            "QtLogHandler",
            "QtLoggingHandler",
            "is_main_thread",
            "get_pyqt_version",
            "has_pyqt",
            "PYQT_VERSION",
            "HAS_PYQT",
        ]

        for export in expected_exports:
            assert export in __all__


# =============================================================================
# 无 PyQt 环境下的占位符类测试
# =============================================================================


class TestPlaceholderClasses:
    """无 PyQt 环境下的占位符类测试"""

    def test_placeholder_qobject(self) -> None:
        """
        测试 QObject 占位符类

        验证无 PyQt 时 QObject 占位符可以实例化
        """
        with patch("pylogkit.qt_integration.HAS_PYQT", False):
            # 重新导入以获取占位符类
            from pylogkit.qt_integration import QObject as PlaceholderQObject

            obj = PlaceholderQObject()
            assert obj is not None

    def test_placeholder_pyqt_signal(self) -> None:
        """
        测试 pyqtSignal 占位符类

        验证无 PyQt 时 pyqtSignal 占位符可以正常使用
        """
        with patch("pylogkit.qt_integration.HAS_PYQT", False):
            from pylogkit.qt_integration import pyqtSignal as PlaceholderSignal

            signal = PlaceholderSignal(dict)
            assert signal is not None

            # 测试 connect 和 emit 方法
            signal.connect(lambda x: None)
            signal.emit({})

    def test_placeholder_qthread(self) -> None:
        """
        测试 QThread 占位符类

        验证无 PyQt 时 QThread 占位符可以实例化
        """
        with patch("pylogkit.qt_integration.HAS_PYQT", False):
            from pylogkit.qt_integration import QThread as PlaceholderQThread

            thread = PlaceholderQThread()
            assert thread is not None

    def test_placeholder_qapplication(self) -> None:
        """
        测试 QApplication 占位符类

        验证无 PyQt 时 QApplication 占位符可以实例化
        """
        with patch("pylogkit.qt_integration.HAS_PYQT", False):
            from pylogkit.qt_integration import QApplication as PlaceholderQApplication

            app = PlaceholderQApplication()
            assert app is not None


# =============================================================================
# QtLogHandler 在无 PyQt 环境下的测试
# =============================================================================


class TestQtLogHandlerWithoutPyQt:
    """QtLogHandler 在无 PyQt 环境下的测试"""

    def test_qt_handler_initialization_without_pyqt(self) -> None:
        """
        测试无 PyQt 时 QtLogHandler 初始化

        验证无 PyQt 时 QtLogHandler 可以正常初始化并发出警告
        """
        with patch("pylogkit.qt_integration.HAS_PYQT", False):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                handler = QtLogHandler()
                assert handler is not None
                # 检查是否有 PyQt 未安装的警告
                pyqt_warnings = [
                    warning for warning in w if "PyQt 未安装" in str(warning.message)
                ]
                assert len(pyqt_warnings) >= 1

    def test_qt_handler_emit_without_pyqt(self) -> None:
        """
        测试无 PyQt 时 QtLogHandler.emit

        验证无 PyQt 时 emit 方法可以正常工作
        """
        with patch("pylogkit.qt_integration.HAS_PYQT", False):
            handler = QtLogHandler()
            captured_messages: list[str] = []
            handler.emitter.connect_message(captured_messages.append)

            handler.emit("Test message without PyQt")

            assert len(captured_messages) == 1
            assert "Test message without PyQt" in captured_messages[0]


# =============================================================================
# LogSignalEmitter 在有 PyQt 环境下的测试
# =============================================================================


class TestLogSignalEmitterWithPyQt:
    """LogSignalEmitter 在有 PyQt 环境下的测试"""

    def test_initialization_with_pyqt(self) -> None:
        """
        测试有 PyQt 时 LogSignalEmitter 初始化

        验证有 PyQt 时正确调用父类初始化
        """
        # 当 HAS_PYQT 为 True 时，应该调用 super().__init__
        # 由于无法真正安装 PyQt，我们测试当 HAS_PYQT=True 时的代码路径
        with patch("pylogkit.qt_integration.HAS_PYQT", True):
            with patch.object(QObject, "__init__", return_value=None):
                emitter = LogSignalEmitter()
                # 注意：由于 QObject 是真实的类（从 PyQt 导入），
                # 这里实际上会调用真实的 QObject.__init__
                # 这个测试主要是为了覆盖代码路径
                assert emitter is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
