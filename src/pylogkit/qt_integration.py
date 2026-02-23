"""
PyQt 日志集成模块

功能特性：
1. 支持 PyQt6/PyQt5 的自动检测和适配
2. 提供线程安全的日志信号发射器
3. 实现 QtLogHandler 用于将日志输出到 GUI
4. 无 PyQt 环境下可正常导入（功能受限）

使用示例：

```python
# 在 PyQt 应用中使用日志集成
from PyQt6.QtWidgets import QApplication, QTextEdit, QVBoxLayout, QWidget
from log.qt_integration import LogSignalEmitter, QtLogHandler
from log import info, get_logger

class LogWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.log_emitter = LogSignalEmitter()
        self.log_handler = QtLogHandler(self.log_emitter)

        # 连接信号到 GUI 更新槽
        self.log_emitter.log_record.connect(self.append_log)

        # 添加到 loguru
        logger = get_logger()
        logger.add(self.log_handler.emit)

        self.log_edit = QTextEdit()
        layout = QVBoxLayout()
        layout.addWidget(self.log_edit)
        self.setLayout(layout)

    def append_log(self, record: dict):
        self.log_edit.append(record.get("message", ""))

# 使用
info("这条日志会显示在 GUI 中")
```
"""

import threading
import warnings
from collections.abc import Callable
from logging import Handler, LogRecord
from typing import Any

# 尝试导入 PyQt 模块
QObject: type
QThread: type
QApplication: type
pyqtSignal: type

PYQT_VERSION: int = 0
HAS_PYQT: bool = False

try:
    # 优先尝试 PyQt6
    from PyQt6.QtCore import QObject, QThread, pyqtSignal  # type: ignore
    from PyQt6.QtWidgets import QApplication  # type: ignore

    PYQT_VERSION = 6
    HAS_PYQT = True
except ImportError:
    try:
        # 回退到 PyQt5
        from PyQt5.QtCore import QObject, QThread, pyqtSignal  # type: ignore
        from PyQt5.QtWidgets import QApplication  # type: ignore

        PYQT_VERSION = 5
        HAS_PYQT = True
    except ImportError:
        # 创建占位符类，确保模块可导入
        class _QObject:
            """PyQt QObject 的占位符类"""

            pass

        class _PyQtSignal:
            """PyQt pyqtSignal 的占位符类"""

            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def connect(self, slot: Any) -> None:
                pass

            def emit(self, *args: Any) -> None:
                pass

        class _QThread:
            """PyQt QThread 的占位符类"""

            pass

        class _QApplication:
            """PyQt QApplication 的占位符类"""

            pass

        QObject = _QObject
        QThread = _QThread
        QApplication = _QApplication
        pyqtSignal = _PyQtSignal  # noqa: N816


class LogSignalEmitter(QObject):
    """
    日志信号发射器

    用于在不同线程间安全地传递日志记录。
    继承自 QObject，提供 pyqtSignal 信号机制。

    Attributes:
        log_record: 日志记录信号，发射包含日志信息的字典
        log_message: 简化日志消息信号，发射格式化的日志字符串
    """

    # 定义信号：发射完整的日志记录字典
    log_record = pyqtSignal(dict)

    # 定义信号：发射格式化的日志字符串
    log_message = pyqtSignal(str)

    def __init__(self, parent: Any = None) -> None:
        """
        初始化日志信号发射器

        Args:
            parent: 父 QObject 对象，默认为 None
        """
        if not HAS_PYQT:
            # 无 PyQt 环境下发出警告
            warnings.warn(
                "PyQt 未安装，LogSignalEmitter 功能受限。"
                "请安装 PyQt6 或 PyQt5 以获得完整功能。",
                RuntimeWarning,
                stacklevel=2,
            )
            # 存储回调函数列表（无 PyQt 时的备选方案）
            self._callbacks: list[Callable[[dict], None]] = []
            self._message_callbacks: list[Callable[[str], None]] = []
            return

        super().__init__(parent)

    def emit_record(self, record: dict[str, Any]) -> None:
        """
        发射日志记录信号

        将日志记录字典发射到连接的槽函数。
        如果当前线程不是主线程，信号会自动排队到主线程执行。

        Args:
            record: 包含日志信息的字典，应包含以下键：
                   - message: 日志消息
                   - level: 日志级别
                   - time: 时间戳
                   - name: 记录器名称
                   - function: 函数名
                   - line: 行号
        """
        if not HAS_PYQT:
            # 无 PyQt 环境下直接调用回调
            for callback in self._callbacks:
                try:
                    callback(record)
                except Exception:
                    pass
            return

        self.log_record.emit(record)

    def emit_message(self, message: str) -> None:
        """
        发射日志消息信号

        将格式化的日志字符串发射到连接的槽函数。

        Args:
            message: 格式化的日志消息字符串
        """
        if not HAS_PYQT:
            # 无 PyQt 环境下直接调用回调
            for callback in self._message_callbacks:
                try:
                    callback(message)
                except Exception:
                    pass
            return

        self.log_message.emit(message)

    def connect_record(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """
        连接日志记录回调

        Args:
            callback: 接收日志记录字典的回调函数
        """
        if not HAS_PYQT:
            self._callbacks.append(callback)
            return

        self.log_record.connect(callback)

    def connect_message(self, callback: Callable[[str], None]) -> None:
        """
        连接日志消息回调

        Args:
            callback: 接收日志字符串的回调函数
        """
        if not HAS_PYQT:
            self._message_callbacks.append(callback)
            return

        self.log_message.connect(callback)


class QtLogHandler:
    """
    Qt 日志处理器

    用于将日志输出捕获并转发到 PyQt GUI。
    兼容 loguru 的 sink 接口和 Python 标准 logging 的 Handler 接口。

    特性：
    - 线程安全的日志记录
    - 支持 loguru 的异步写入模式
    - 自动检测当前线程，确保 GUI 更新在主线程执行

    Attributes:
        emitter: LogSignalEmitter 实例，用于发射日志信号
        format_string: 日志格式字符串
    """

    def __init__(
        self,
        emitter: LogSignalEmitter | None = None,
        format_string: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
    ) -> None:
        """
        初始化 Qt 日志处理器

        Args:
            emitter: LogSignalEmitter 实例，如果为 None 则自动创建
            format_string: 日志格式字符串，用于格式化日志消息
        """
        self.emitter = emitter or LogSignalEmitter()
        self.format_string = format_string
        self._lock = threading.Lock()
        self._message_buffer: list[str] = []
        self._buffer_size = 100

        if not HAS_PYQT:
            warnings.warn(
                "PyQt 未安装，QtLogHandler 将以受限模式运行。"
                "日志将通过回调函数传递，而非 Qt 信号。",
                RuntimeWarning,
                stacklevel=2,
            )

    def emit(self, record: dict[str, Any] | str | LogRecord) -> None:
        """
        处理并发射日志记录

        此方法可作为 loguru 的 sink 函数使用，
        也可作为标准 logging Handler 的 emit 方法。

        Args:
            record: 日志记录，可以是：
                   - loguru 的记录字典
                   - 字符串消息
                   - logging.LogRecord 对象
        """
        try:
            # 解析记录为统一格式
            parsed_record = self._parse_record(record)

            # 格式化消息
            formatted_message = self._format_message(parsed_record)

            # 线程安全地发射信号
            with self._lock:
                # 发射完整记录
                self.emitter.emit_record(parsed_record)

                # 发射格式化消息
                self.emitter.emit_message(formatted_message)

                # 添加到缓冲区
                self._message_buffer.append(formatted_message)
                if len(self._message_buffer) > self._buffer_size:
                    self._message_buffer.pop(0)

        except Exception as e:
            # 发射失败时不应抛出异常，避免日志循环
            warnings.warn(f"日志发射失败: {e}", RuntimeWarning, stacklevel=2)

    def _parse_record(
        self, record: dict[str, Any] | str | LogRecord
    ) -> dict[str, Any]:
        """
        解析日志记录为统一格式

        Args:
            record: 原始日志记录

        Returns:
            标准化的日志记录字典
        """
        if isinstance(record, dict):
            # loguru 格式
            return {
                "message": record.get("message", ""),
                "level": (
                    record.get("level", {}).get("name", "INFO")
                    if isinstance(record.get("level"), dict)
                    else str(record.get("level", "INFO"))
                ),
                "time": record.get("time", ""),
                "name": record.get("name", ""),
                "function": record.get("function", ""),
                "line": record.get("line", 0),
                "exception": record.get("exception", None),
                "extra": record.get("extra", {}),
            }

        elif isinstance(record, LogRecord):
            # Python 标准 logging 格式
            return {
                "message": record.getMessage(),
                "level": record.levelname,
                "time": record.created,
                "name": record.name,
                "function": record.funcName,
                "line": record.lineno,
                "exception": None,
                "extra": {},
            }

        # 字符串或其他格式，转换为字符串
        return {
            "message": str(record),
            "level": "INFO",
            "time": "",
            "name": "",
            "function": "",
            "line": 0,
            "exception": None,
            "extra": {},
        }

    def _format_message(self, record: dict[str, Any]) -> str:
        """
        格式化日志消息

        Args:
            record: 日志记录字典

        Returns:
            格式化后的日志字符串
        """
        try:
            # 简单的格式化实现
            time_str = record.get("time", "")
            if hasattr(time_str, "strftime"):
                time_str = time_str.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            level_str = str(record.get("level", "INFO")).upper().ljust(8)
            message_str = record.get("message", "")

            return f"{time_str} | {level_str} | {message_str}"
        except Exception:
            # 格式化失败时返回原始消息
            return str(record.get("message", ""))

    def get_buffer(self) -> list[str]:
        """
        获取日志缓冲区内容

        Returns:
            最近的日志消息列表
        """
        with self._lock:
            return self._message_buffer.copy()

    def clear_buffer(self) -> None:
        """清空日志缓冲区"""
        with self._lock:
            self._message_buffer.clear()

    def write(self, message: str) -> None:
        """
        写入日志消息（兼容文件接口）

        Args:
            message: 日志消息字符串
        """
        self.emit(message)

    def flush(self) -> None:
        """刷新缓冲区（兼容文件接口）"""
        pass


class QtLoggingHandler(Handler):
    """
    Python 标准 logging 的 Qt 处理器

    继承自 logging.Handler，可直接添加到标准 logging 的 Logger 中。
    将日志记录转发到 Qt 信号系统，实现 GUI 集成。

    使用示例：

    ```python
    import logging
    from log.qt_integration import QtLoggingHandler, LogSignalEmitter

    # 创建发射器和处理器
    emitter = LogSignalEmitter()
    handler = QtLoggingHandler(emitter)

    # 配置标准 logging
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    # 连接信号到 GUI
    emitter.log_message.connect(my_text_edit.append)
    ```
    """

    def __init__(
        self,
        emitter: LogSignalEmitter | None = None,
        level: int = 0,
    ) -> None:
        """
        初始化 Qt Logging 处理器

        Args:
            emitter: LogSignalEmitter 实例，如果为 None 则自动创建
            level: 日志级别阈值
        """
        super().__init__(level)
        self.qt_handler = QtLogHandler(emitter)

    def emit(self, record: LogRecord) -> None:
        """
        发射日志记录

        Args:
            record: logging.LogRecord 对象
        """
        self.qt_handler.emit(record)


def is_main_thread() -> bool:
    """
    检查当前是否为主线程

    Returns:
        如果当前线程是主线程返回 True，否则返回 False
    """
    return threading.current_thread() is threading.main_thread()


def get_pyqt_version() -> int:
    """
    获取检测到的 PyQt 版本

    Returns:
            0: 未安装 PyQt
            5: PyQt5
            6: PyQt6
    """
    return PYQT_VERSION


def has_pyqt() -> bool:
    """
    检查是否安装了 PyQt

    Returns:
        如果安装了 PyQt 返回 True，否则返回 False
    """
    return HAS_PYQT


# 导出公共接口
__all__ = [
    "LogSignalEmitter",
    "QtLogHandler",
    "QtLoggingHandler",
    "is_main_thread",
    "get_pyqt_version",
    "has_pyqt",
    "PYQT_VERSION",
    "HAS_PYQT",
]
