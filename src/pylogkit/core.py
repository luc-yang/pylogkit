"""
日志核心模块 - 基于 loguru 实现

功能特性：
1. 单例模式管理日志实例
2. 跨平台默认日志目录
3. 支持自定义应用名称前缀
4. 日志格式包含文件名、函数名、行号
5. 延迟初始化机制
6. 控制台彩色输出 + 文件输出
7. 日志轮转、压缩、清理
8. 完整的类型注解

使用示例：

```python
from log.core import debug, info, error, get_logger, init_logger

# 方式一：直接使用导出的日志方法
info("这是一条信息日志")
error("这是一条错误日志")

# 方式二：获取 logger 实例
logger = get_logger()
logger.debug("这是一条调试日志")

# 方式三：自定义初始化
init_logger(
    app_name="myapp",
    log_dir="/path/to/logs",
    level="DEBUG",
    rotation="5 MB",
    retention="14 days"
)
```
"""

import os
import platform
import sys
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from loguru._logger import Logger

from .config import get_default_log_dir

# 类型别名
LoguruLogger = logger.__class__

# 日志级别映射
LOG_LEVELS = {
    "DEBUG": "DEBUG",
    "INFO": "INFO",
    "WARNING": "WARNING",
    "ERROR": "ERROR",
    "CRITICAL": "CRITICAL",
}


class LoggerManager:
    """
    日志管理器（单例模式）

    基于 loguru 提供统一的日志管理接口，支持跨平台、彩色输出、日志轮转等功能。
    """

    _instance: Optional["LoggerManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "LoggerManager":
        """
        创建单例实例

        Returns:
            LoggerManager 单例实例
        """
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """初始化日志管理器（仅执行一次）"""
        if self._initialized:
            return

        self._logger = logger
        self._is_initialized: bool = False
        self._log_dir: Path | None = None
        self._app_name: str = "app"
        self._config: dict[str, Any] = {}
        self._console_sink_id: int | None = None
        self._file_sink_id: int | None = None

        LoggerManager._initialized = True

    def _get_default_log_dir(self) -> Path:
        """
        获取跨平台的默认日志目录

        Returns:
            默认日志目录路径
        """
        system = platform.system()

        if system == "Windows":
            # Windows: %APPDATA%\{app_name}\logs
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / self._app_name / "logs"
            else:
                return Path.home() / "AppData" / "Roaming" / self._app_name / "logs"

        elif system == "Darwin":
            # macOS: ~/Library/Application Support/{app_name}/logs
            return (
                Path.home()
                / "Library"
                / "Application Support"
                / self._app_name
                / "logs"
            )

        else:
            # Linux/Unix: ~/.local/share/{app_name}/logs
            xdg_data_home = os.environ.get("XDG_DATA_HOME")
            if xdg_data_home:
                return Path(xdg_data_home) / self._app_name / "logs"
            else:
                return Path.home() / ".local" / "share" / self._app_name / "logs"

    def init_logger(
        self,
        app_name: str = "app",
        log_dir: str | Path | None = None,
        level: str = "INFO",
        rotation: str = "10 MB",
        retention: str = "7 days",
        encoding: str = "utf-8",
        console_output: bool = True,
        file_output: bool = True,
    ) -> None:
        """
        初始化日志配置

        Args:
            app_name: 应用名称前缀，用于构建默认日志目录和文件名
            log_dir: 日志文件存储目录，None 时使用跨平台默认目录
            level: 日志级别，可选值：DEBUG, INFO, WARNING, ERROR, CRITICAL
            rotation: 日志文件轮转条件，支持大小格式（如 "10 MB"）或时间格式（如 "1 day"）
            retention: 日志文件保留时间，如 "7 days"
            encoding: 日志文件编码
            console_output: 是否输出到控制台
            file_output: 是否输出到文件
        """
        try:
            # 清除默认配置
            self._logger.remove()
            self._console_sink_id = None
            self._file_sink_id = None

            # 设置应用名称
            self._app_name = app_name

            # 设置日志目录
            if log_dir is None:
                self._log_dir = self._get_default_log_dir()
            else:
                self._log_dir = Path(os.path.normpath(log_dir))

            # 创建日志目录
            self._ensure_log_dir()

            # 控制台日志格式 - 彩色显示
            console_format = (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
                "| <level>{level: <8}</level> "
                "| <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
                "| <level>{message}</level>"
            )

            # 文件日志格式 - 简洁清晰，包含文件名和行号
            file_format = (
                "{time:YYYY-MM-DD HH:mm:ss.SSS} "
                "| {level: <8} "
                "| {name}:{function}:{line} "
                "| {message}"
            )

            # 添加控制台输出
            if console_output and sys.stdout is not None:
                self._console_sink_id = self._logger.add(
                    sink=sys.stdout,
                    level=level,
                    format=console_format,
                    enqueue=True,
                    backtrace=True,
                    diagnose=True,
                )

            # 添加文件输出
            if file_output:
                log_file = self._log_dir / f"{app_name}_{{time:YYYY-MM-DD}}.log"
                self._file_sink_id = self._logger.add(
                    sink=str(log_file),
                    level=level,
                    format=file_format,
                    rotation=rotation,
                    retention=retention,
                    encoding=encoding,
                    enqueue=True,
                    backtrace=True,
                    diagnose=True,
                    compression="zip",
                )

            self._is_initialized = True
            self._config = {
                "app_name": app_name,
                "log_dir": str(self._log_dir),
                "level": level,
                "rotation": rotation,
                "retention": retention,
                "encoding": encoding,
                "console_output": console_output,
                "file_output": file_output,
            }

            # 记录初始化信息
            self._logger.info("Logger initialized successfully")
            self._logger.info(f"Log directory: {self._log_dir.absolute()}")
            self._logger.info(f"Log level: {level}")

        except Exception as e:
            print(f"Logger initialization failed: {e}")
            raise

    def _ensure_log_dir(self) -> None:
        """
        确保日志目录存在

        如果创建失败，尝试使用备用目录。
        """
        if self._log_dir is None:
            self._log_dir = get_default_log_dir(self._app_name)

        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # 如果创建目录失败，使用临时目录作为备选
            import tempfile

            self._log_dir = (
                Path(os.path.normpath(tempfile.gettempdir())) / self._app_name / "logs"
            )
            self._log_dir.mkdir(parents=True, exist_ok=True)

    def get_logger(self) -> Any:
        """
        获取 logger 实例

        如果尚未初始化，使用默认配置自动初始化。

        Returns:
            loguru.logger 实例
        """
        if not self._is_initialized:
            self.init_logger()
        return self._logger

    def set_level(self, level: str) -> None:
        """
        设置日志级别

        Args:
            level: 日志级别，可选值：DEBUG, INFO, WARNING, ERROR, CRITICAL
        """
        try:
            # 移除所有 sink
            self._logger.remove()
            self._console_sink_id = None
            self._file_sink_id = None

            # 重新初始化，使用新的日志级别
            if self._config:
                self.init_logger(
                    app_name=self._config.get("app_name", "app"),
                    log_dir=self._config.get("log_dir"),
                    level=level,
                    rotation=self._config.get("rotation", "10 MB"),
                    retention=self._config.get("retention", "7 days"),
                    encoding=self._config.get("encoding", "utf-8"),
                    console_output=self._config.get("console_output", True),
                    file_output=self._config.get("file_output", True),
                )
            else:
                self.init_logger(level=level)

            self._logger.info(f"Log level changed to: {level}")

        except Exception as e:
            self._logger.error(f"Failed to set log level: {e}")
            raise

    def get_log_dir(self) -> Path | None:
        """
        获取日志文件存储目录

        Returns:
            日志文件存储目录路径
        """
        return self._log_dir

    def get_config(self) -> dict[str, Any]:
        """
        获取当前日志配置

        Returns:
            配置字典
        """
        return self._config.copy()

    def shutdown(self) -> None:
        """
        关闭日志管理器

        清理所有 sink 并释放资源。
        """
        self._logger.remove()
        self._console_sink_id = None
        self._file_sink_id = None
        self._is_initialized = False
        self._initialized = False
        LoggerManager._instance = None


# 创建全局日志管理器实例
_logger_manager = LoggerManager()


def debug(message: str, *args: Any, **kwargs: Any) -> None:
    """
    记录调试级别日志

    Args:
        message: 日志消息
        *args: 格式化参数
        **kwargs: 额外参数
    """
    _logger_manager.get_logger().debug(message, *args, **kwargs)


def info(message: str, *args: Any, **kwargs: Any) -> None:
    """
    记录信息级别日志

    Args:
        message: 日志消息
        *args: 格式化参数
        **kwargs: 额外参数
    """
    _logger_manager.get_logger().info(message, *args, **kwargs)


def warning(message: str, *args: Any, **kwargs: Any) -> None:
    """
    记录警告级别日志

    Args:
        message: 日志消息
        *args: 格式化参数
        **kwargs: 额外参数
    """
    _logger_manager.get_logger().warning(message, *args, **kwargs)


def error(message: str, *args: Any, **kwargs: Any) -> None:
    """
    记录错误级别日志

    Args:
        message: 日志消息
        *args: 格式化参数
        **kwargs: 额外参数
    """
    _logger_manager.get_logger().error(message, *args, **kwargs)


def critical(message: str, *args: Any, **kwargs: Any) -> None:
    """
    记录严重错误级别日志

    Args:
        message: 日志消息
        *args: 格式化参数
        **kwargs: 额外参数
    """
    _logger_manager.get_logger().critical(message, *args, **kwargs)


def exception(message: str, *args: Any, **kwargs: Any) -> None:
    """
    记录异常级别日志（包含堆栈跟踪）

    Args:
        message: 日志消息
        *args: 格式化参数
        **kwargs: 额外参数
    """
    _logger_manager.get_logger().exception(message, *args, **kwargs)


# 导出日志管理器实例的方法
get_logger = _logger_manager.get_logger
init_logger = _logger_manager.init_logger
set_level = _logger_manager.set_level
get_log_dir = _logger_manager.get_log_dir
get_config = _logger_manager.get_config
shutdown = _logger_manager.shutdown
