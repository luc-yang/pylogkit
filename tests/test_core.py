"""
日志核心模块测试

测试 LoggerManager 类和模块级日志函数
"""

import os
import platform
import shutil
import sys
import tempfile
from collections.abc import Generator
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from pylogkit.core import (
    LOG_LEVELS,
    LoggerManager,
    critical,
    debug,
    error,
    exception,
    get_config,
    get_log_dir,
    get_logger,
    info,
    init_logger,
    shutdown,
    warning,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_log_dir() -> Generator[Path, None, None]:
    """
    创建临时日志目录

    Yields:
        临时目录路径
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="core_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def reset_logger_manager() -> Generator[None, None, None]:
    """
    重置日志管理器 fixture

    每个测试结束后重置日志管理器状态
    """
    yield
    # 清理日志管理器
    shutdown()
    # 重置单例
    LoggerManager._instance = None
    LoggerManager._initialized = False


@pytest.fixture
def capture_stdout() -> Generator[StringIO, None, None]:
    """
    捕获标准输出

    Yields:
        StringIO 对象
    """
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    yield sys.stdout
    sys.stdout = old_stdout


# =============================================================================
# LoggerManager 单例测试
# =============================================================================


class TestLoggerManagerSingleton:
    """日志管理器单例模式测试"""

    def test_singleton_instance(self, reset_logger_manager) -> None:
        """
        测试单例实例

        验证多次获取的是同一个实例

        Args:
            reset_logger_manager: 重置 fixture
        """
        manager1 = LoggerManager()
        manager2 = LoggerManager()

        assert manager1 is manager2

    def test_singleton_initialized_once(self, reset_logger_manager) -> None:
        """
        测试初始化只执行一次

        验证 __init__ 只被调用一次

        Args:
            reset_logger_manager: 重置 fixture
        """
        # 先重置单例状态
        LoggerManager._instance = None
        LoggerManager._initialized = False

        # 创建第一个实例
        manager1 = LoggerManager()

        # 第一次初始化后 _initialized 应该为 True
        assert LoggerManager._initialized is True

        # 再次创建实例不应该重新初始化（__init__ 会直接返回）
        manager2 = LoggerManager()

        # 应该是同一个实例
        assert manager1 is manager2


# =============================================================================
# LoggerManager 初始化测试
# =============================================================================


class TestLoggerManagerInit:
    """日志管理器初始化测试"""

    def test_default_initialization(
        self, temp_log_dir: Path, reset_logger_manager
    ) -> None:
        """
        测试默认初始化

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        manager = LoggerManager()
        manager.init_logger(log_dir=str(temp_log_dir))

        assert manager._is_initialized is True
        assert manager._app_name == "app"
        assert manager._log_dir == temp_log_dir

    def test_custom_initialization(
        self, temp_log_dir: Path, reset_logger_manager
    ) -> None:
        """
        测试自定义初始化

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        manager = LoggerManager()
        manager.init_logger(
            app_name="myapp",
            log_dir=str(temp_log_dir),
            level="DEBUG",
            rotation="5 MB",
            retention="14 days",
            encoding="utf-16",
            console_output=True,
            file_output=True,
        )

        assert manager._app_name == "myapp"
        assert manager._log_dir == temp_log_dir
        config = manager.get_config()
        assert config["level"] == "DEBUG"
        assert config["rotation"] == "5 MB"
        assert config["retention"] == "14 days"
        assert config["encoding"] == "utf-16"

    def test_init_creates_directory(
        self, temp_log_dir: Path, reset_logger_manager
    ) -> None:
        """
        测试初始化创建目录

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        nested_dir = temp_log_dir / "nested" / "logs"
        manager = LoggerManager()

        assert not nested_dir.exists()

        manager.init_logger(log_dir=str(nested_dir))

        assert nested_dir.exists()

    def test_init_fallback_to_temp_dir(
        self, temp_log_dir: Path, reset_logger_manager
    ) -> None:
        """
        测试初始化失败时回退到临时目录

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        manager = LoggerManager()

        # 创建一个无法写入的目录路径
        invalid_dir = temp_log_dir / "invalid" / "path"

        # 模拟特定路径的 mkdir 失败
        original_mkdir = Path.mkdir

        def mock_mkdir(self, *args, **kwargs):
            if str(self) == str(invalid_dir):
                raise PermissionError("Access denied")
            return original_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", mock_mkdir):
            manager.init_logger(log_dir=str(invalid_dir))

            # 应该回退到临时目录
            assert "logs" in str(manager._log_dir)

    def test_init_without_console_output(
        self, temp_log_dir: Path, reset_logger_manager
    ) -> None:
        """
        测试禁用控制台输出

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        manager = LoggerManager()
        manager.init_logger(
            log_dir=str(temp_log_dir),
            console_output=False,
            file_output=True,
        )

        assert manager._console_sink_id is None
        assert manager._file_sink_id is not None

    def test_init_without_file_output(
        self, temp_log_dir: Path, reset_logger_manager
    ) -> None:
        """
        测试禁用文件输出

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        manager = LoggerManager()
        manager.init_logger(
            log_dir=str(temp_log_dir),
            console_output=True,
            file_output=False,
        )

        assert manager._console_sink_id is not None
        assert manager._file_sink_id is None

    def test_init_clears_previous_sinks(
        self, temp_log_dir: Path, reset_logger_manager
    ) -> None:
        """
        测试初始化清除之前的 sinks

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        manager = LoggerManager()

        # 第一次初始化
        manager.init_logger(log_dir=str(temp_log_dir))
        first_console_id = manager._console_sink_id
        first_file_id = manager._file_sink_id

        # 第二次初始化
        manager.init_logger(log_dir=str(temp_log_dir / "second"))

        # sink ID 应该改变
        assert manager._console_sink_id != first_console_id
        assert manager._file_sink_id != first_file_id


# =============================================================================
# 日志级别测试
# =============================================================================


class TestLogLevels:
    """日志级别测试"""

    def test_all_log_levels(self, temp_log_dir: Path, reset_logger_manager) -> None:
        """
        测试所有日志级别

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        manager = LoggerManager()
        manager.init_logger(log_dir=str(temp_log_dir), level="DEBUG")

        logger = manager.get_logger()

        # 记录所有级别的日志
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")

        # 日志应该被记录（通过文件验证）
        import time

        time.sleep(0.1)

        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0

    def test_level_filtering(self, temp_log_dir: Path, reset_logger_manager) -> None:
        """
        测试日志级别过滤

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        manager = LoggerManager()
        manager.init_logger(log_dir=str(temp_log_dir), level="WARNING")

        logger = manager.get_logger()

        # DEBUG 和 INFO 应该被过滤
        logger.debug("debug message")
        logger.info("info message")

        # WARNING 及以上应该被记录
        logger.warning("warning message")
        logger.error("error message")

        import time

        time.sleep(0.1)

        log_files = list(temp_log_dir.glob("*.log"))
        if log_files:
            content = log_files[0].read_text(encoding="utf-8")
            assert "WARNING" in content
            assert "ERROR" in content
            assert "debug message" not in content
            assert "info message" not in content

    def test_set_level(self, temp_log_dir: Path, reset_logger_manager) -> None:
        """
        测试动态设置日志级别

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        manager = LoggerManager()
        manager.init_logger(log_dir=str(temp_log_dir), level="INFO")

        # 初始级别为 INFO
        logger = manager.get_logger()
        logger.debug("debug before")  # 应该被过滤

        # 设置级别为 DEBUG
        manager.set_level("DEBUG")

        logger.debug("debug after")  # 应该被记录

        import time

        time.sleep(0.1)

        config = manager.get_config()
        assert config["level"] == "DEBUG"


# =============================================================================
# 模块级函数测试
# =============================================================================


class TestModuleLevelFunctions:
    """模块级函数测试"""

    def test_get_logger_auto_init(
        self, temp_log_dir: Path, reset_logger_manager
    ) -> None:
        """
        测试 get_logger 自动初始化

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        # 使用模块级函数
        logger = get_logger()

        # 应该自动初始化
        assert logger is not None

    def test_init_logger(self, temp_log_dir: Path, reset_logger_manager) -> None:
        """
        测试 init_logger 函数

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        init_logger(
            app_name="testapp",
            log_dir=str(temp_log_dir),
            level="DEBUG",
        )

        config = get_config()
        assert config["app_name"] == "testapp"
        assert config["level"] == "DEBUG"

    def test_get_log_dir(self, temp_log_dir: Path, reset_logger_manager) -> None:
        """
        测试 get_log_dir 函数

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        init_logger(log_dir=str(temp_log_dir))

        log_dir = get_log_dir()
        assert log_dir == temp_log_dir

    def test_get_config(self, temp_log_dir: Path, reset_logger_manager) -> None:
        """
        测试 get_config 函数

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        init_logger(
            app_name="config_test",
            log_dir=str(temp_log_dir),
            level="WARNING",
        )

        config = get_config()
        assert config["app_name"] == "config_test"
        assert config["level"] == "WARNING"
        assert "log_dir" in config
        assert "rotation" in config
        assert "retention" in config
        assert "encoding" in config
        assert "console_output" in config
        assert "file_output" in config

    def test_shutdown(self, temp_log_dir: Path, reset_logger_manager) -> None:
        """
        测试 shutdown 函数

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        init_logger(log_dir=str(temp_log_dir))

        # 确认已初始化
        assert get_log_dir() == temp_log_dir

        # 关闭
        shutdown()

        # 单例应该被重置
        assert LoggerManager._instance is None

    def test_debug_function(self, temp_log_dir: Path, reset_logger_manager) -> None:
        """
        测试 debug 函数

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        init_logger(log_dir=str(temp_log_dir), level="DEBUG")

        debug("test debug message: %s", "arg1")

        # 验证日志被记录
        import time

        time.sleep(0.1)

        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0

    def test_info_function(self, temp_log_dir: Path, reset_logger_manager) -> None:
        """
        测试 info 函数

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        init_logger(log_dir=str(temp_log_dir), level="INFO")

        info("test info message")

        import time

        time.sleep(0.1)

        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0

    def test_warning_function(self, temp_log_dir: Path, reset_logger_manager) -> None:
        """
        测试 warning 函数

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        init_logger(log_dir=str(temp_log_dir), level="WARNING")

        warning("test warning message")

        import time

        time.sleep(0.1)

        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0

    def test_error_function(self, temp_log_dir: Path, reset_logger_manager) -> None:
        """
        测试 error 函数

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        init_logger(log_dir=str(temp_log_dir), level="ERROR")

        error("test error message")

        import time

        time.sleep(0.1)

        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0

    def test_critical_function(self, temp_log_dir: Path, reset_logger_manager) -> None:
        """
        测试 critical 函数

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        init_logger(log_dir=str(temp_log_dir), level="CRITICAL")

        critical("test critical message")

        import time

        time.sleep(0.1)

        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0

    def test_exception_function(self, temp_log_dir: Path, reset_logger_manager) -> None:
        """
        测试 exception 函数

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        init_logger(log_dir=str(temp_log_dir), level="DEBUG")

        try:
            raise ValueError("Test exception")
        except Exception:
            exception("Exception occurred")

        import time

        time.sleep(0.1)

        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0


# =============================================================================
# 跨平台测试
# =============================================================================


class TestCrossPlatform:
    """跨平台功能测试"""

    def test_default_log_dir_windows(self, reset_logger_manager) -> None:
        """
        测试 Windows 默认日志目录

        Args:
            reset_logger_manager: 重置 fixture
        """
        if platform.system() != "Windows":
            pytest.skip("仅 Windows 环境测试")

        with patch.dict(os.environ, {"APPDATA": r"C:\Users\Test\AppData\Roaming"}):
            # 重置单例以使用新的环境变量
            LoggerManager._instance = None
            LoggerManager._initialized = False

            manager = LoggerManager()
            # 不传递 log_dir，使用默认目录
            manager.init_logger(app_name="testapp", log_dir=None)

            log_dir = manager.get_log_dir()
            # 验证路径包含预期的组件
            assert "testapp" in str(log_dir)
            assert "logs" in str(log_dir)
            # 验证使用了 APPDATA
            assert "AppData" in str(log_dir) or "APPDATA" in str(log_dir).upper()

    def test_default_log_dir_macos(self, reset_logger_manager) -> None:
        """
        测试 macOS 默认日志目录

        Args:
            reset_logger_manager: 重置 fixture
        """
        if platform.system() != "Darwin":
            pytest.skip("仅 macOS 环境测试")

        manager = LoggerManager()
        manager.init_logger(app_name="testapp")

        log_dir = manager.get_log_dir()
        assert "Library" in str(log_dir)
        assert "Application Support" in str(log_dir)

    def test_default_log_dir_linux(self, reset_logger_manager) -> None:
        """
        测试 Linux 默认日志目录

        Args:
            reset_logger_manager: 重置 fixture
        """
        if platform.system() == "Windows" or platform.system() == "Darwin":
            pytest.skip("仅 Linux 环境测试")

        manager = LoggerManager()
        manager.init_logger(app_name="testapp")

        log_dir = manager.get_log_dir()
        assert ".local" in str(log_dir) or "share" in str(log_dir)

    def test_init_logger_exception_handling(
        self, temp_log_dir: Path, reset_logger_manager
    ) -> None:
        """
        测试初始化日志器时的异常处理

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        manager = LoggerManager()

        # 模拟 logger.add 抛出异常
        with patch.object(
            manager._logger, "add", side_effect=RuntimeError("Test error")
        ):
            with pytest.raises(RuntimeError, match="Test error"):
                manager.init_logger(log_dir=str(temp_log_dir))

    def test_set_level_without_config(
        self, temp_log_dir: Path, reset_logger_manager
    ) -> None:
        """
        测试在没有配置的情况下设置日志级别

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        manager = LoggerManager()
        manager.init_logger(log_dir=str(temp_log_dir), level="INFO")

        # 清除配置
        manager._config = {}

        # 应该能正常工作，使用默认值
        manager.set_level("DEBUG")

        config = manager.get_config()
        assert config["level"] == "DEBUG"

    def test_set_level_exception_handling(
        self, temp_log_dir: Path, reset_logger_manager
    ) -> None:
        """
        测试设置日志级别时的异常处理

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        manager = LoggerManager()
        manager.init_logger(log_dir=str(temp_log_dir))

        # 模拟 logger.info 抛出异常
        with patch.object(
            manager._logger, "info", side_effect=RuntimeError("Test error")
        ):
            with pytest.raises(RuntimeError, match="Test error"):
                manager.set_level("DEBUG")


# =============================================================================
# 边界条件测试
# =============================================================================


class TestEdgeCases:
    """边界条件测试"""

    def test_empty_app_name(self, temp_log_dir: Path, reset_logger_manager) -> None:
        """
        测试空应用名称

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        manager = LoggerManager()
        manager.init_logger(app_name="", log_dir=str(temp_log_dir))

        assert manager._app_name == ""

    def test_special_characters_in_messages(
        self, temp_log_dir: Path, reset_logger_manager
    ) -> None:
        """
        测试消息中的特殊字符

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        init_logger(log_dir=str(temp_log_dir), level="DEBUG")

        # 测试 Unicode 字符
        info("Unicode test: 你好世界 🌍")

        # 测试特殊字符
        info("Special chars: \"quotes\" 'apostrophes' \n newlines \t tabs")

        import time

        time.sleep(0.1)

        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0

    def test_very_long_message(self, temp_log_dir: Path, reset_logger_manager) -> None:
        """
        测试超长消息

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        init_logger(log_dir=str(temp_log_dir), level="DEBUG")

        long_message = "A" * 10000
        info(long_message)

        import time

        time.sleep(0.1)

        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0

    def test_multiple_init_calls(
        self, temp_log_dir: Path, reset_logger_manager
    ) -> None:
        """
        测试多次初始化调用

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        init_logger(
            app_name="first",
            log_dir=str(temp_log_dir / "first"),
            level="DEBUG",
        )

        # 第二次初始化
        init_logger(
            app_name="second",
            log_dir=str(temp_log_dir / "second"),
            level="WARNING",
        )

        config = get_config()
        assert config["app_name"] == "second"
        assert config["level"] == "WARNING"


# =============================================================================
# 性能测试
# =============================================================================


class TestPerformance:
    """性能测试"""

    def test_high_frequency_logging(
        self, temp_log_dir: Path, reset_logger_manager
    ) -> None:
        """
        测试高频日志记录

        Args:
            temp_log_dir: 临时日志目录
            reset_logger_manager: 重置 fixture
        """
        init_logger(log_dir=str(temp_log_dir), level="DEBUG")

        import time

        start_time = time.time()

        # 记录 1000 条日志
        for i in range(1000):
            info("High frequency log entry: %d", i)

        # 等待异步写入
        time.sleep(0.5)

        elapsed = time.time() - start_time

        # 性能要求：1000 条日志应在 5 秒内完成
        assert elapsed < 5.0

        # 验证日志文件存在
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0


# =============================================================================
# 日志级别常量测试
# =============================================================================


class TestLogLevelConstants:
    """日志级别常量测试"""

    def test_log_levels_dict(self) -> None:
        """
        测试日志级别字典

        验证 LOG_LEVELS 字典包含所有标准级别
        """
        assert "DEBUG" in LOG_LEVELS
        assert "INFO" in LOG_LEVELS
        assert "WARNING" in LOG_LEVELS
        assert "ERROR" in LOG_LEVELS
        assert "CRITICAL" in LOG_LEVELS

        assert LOG_LEVELS["DEBUG"] == "DEBUG"
        assert LOG_LEVELS["INFO"] == "INFO"
        assert LOG_LEVELS["WARNING"] == "WARNING"
        assert LOG_LEVELS["ERROR"] == "ERROR"
        assert LOG_LEVELS["CRITICAL"] == "CRITICAL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
