"""
审计日志模块测试

测试 AuditLogConfig、AuditLogger 类以及模块级便捷函数
"""

import json
import shutil
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from pylogkit.audit import (
    AuditLogConfig,
    AuditLogger,
    critical,
    debug,
    error,
    get_audit_logger,
    get_log_dir,
    get_log_file,
    info,
    init_audit_logger,
    log_event,
    reload_audit_logger,
    success,
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
    temp_dir = Path(tempfile.mkdtemp(prefix="audit_test_"))
    yield temp_dir
    # 清理
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def cleanup_audit_logger() -> Generator[None, None, None]:
    """
    清理全局审计日志记录器

    每个测试结束后关闭并清理全局审计日志记录器
    """
    yield
    reload_audit_logger()


# =============================================================================
# AuditLogConfig 测试
# =============================================================================


class TestAuditLogConfig:
    """审计日志配置类测试"""

    def test_default_config(self) -> None:
        """
        测试默认配置

        验证默认配置参数是否正确
        """
        config = AuditLogConfig()

        assert config.log_dir == Path("logs") / "audit"
        assert config.level == "INFO"
        assert config.rotation == "10 MB"
        assert config.retention == "30 days"
        assert config.encoding == "utf-8"

    def test_custom_config(self, temp_log_dir: Path) -> None:
        """
        测试自定义配置

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(
            log_dir=str(temp_log_dir),
            level="DEBUG",
            rotation="5 MB",
            retention="7 days",
            encoding="gbk",
        )

        assert config.log_dir == temp_log_dir
        assert config.level == "DEBUG"
        assert config.rotation == "5 MB"
        assert config.retention == "7 days"
        assert config.encoding == "gbk"

    def test_config_with_path_object(self, temp_log_dir: Path) -> None:
        """
        测试使用 Path 对象作为 log_dir

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(log_dir=temp_log_dir)
        assert config.log_dir == temp_log_dir

    def test_config_to_dict(self, temp_log_dir: Path) -> None:
        """
        测试配置转换为字典

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(
            log_dir=str(temp_log_dir),
            level="WARNING",
        )
        config_dict = config.to_dict()

        assert config_dict["log_dir"] == str(temp_log_dir)
        assert config_dict["level"] == "WARNING"
        assert config_dict["rotation"] == "10 MB"
        assert config_dict["retention"] == "30 days"
        assert config_dict["encoding"] == "utf-8"

    def test_config_level_uppercase(self) -> None:
        """
        测试日志级别自动转换为大写
        """
        config = AuditLogConfig(level="debug")
        assert config.level == "DEBUG"


# =============================================================================
# AuditLogger 测试
# =============================================================================


class TestAuditLogger:
    """审计日志记录器类测试"""

    def test_logger_initialization(self, temp_log_dir: Path) -> None:
        """
        测试日志记录器初始化

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(log_dir=str(temp_log_dir))
        logger = AuditLogger(config=config)

        assert logger.get_log_dir() == temp_log_dir
        assert logger._config.level == "INFO"
        assert logger._sink_id is not None

        logger.close()

    def test_logger_creates_directory(self, temp_log_dir: Path) -> None:
        """
        测试日志记录器自动创建目录

        Args:
            temp_log_dir: 临时日志目录
        """
        nested_dir = temp_log_dir / "nested" / "audit"
        config = AuditLogConfig(log_dir=str(nested_dir))
        logger = AuditLogger(config=config)

        assert nested_dir.exists()

        logger.close()

    def test_logger_fallback_to_temp_dir(self, temp_log_dir: Path) -> None:
        """
        测试目录创建失败时回退到临时目录

        Args:
            temp_log_dir: 临时日志目录
        """
        # 创建一个无法写入的目录路径
        invalid_dir = temp_log_dir / "invalid" / "path"
        config = AuditLogConfig(log_dir=str(invalid_dir))

        # 模拟特定路径的 mkdir 失败
        original_mkdir = Path.mkdir

        def mock_mkdir(self, *args, **kwargs):
            if str(self) == str(invalid_dir):
                raise PermissionError("Access denied")
            return original_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", mock_mkdir):
            logger = AuditLogger(config=config)

            # 应该回退到临时目录
            assert "audit_logs" in str(logger.get_log_dir())

            logger.close()

    def test_logger_level_filtering(self, temp_log_dir: Path) -> None:
        """
        测试日志级别过滤

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(log_dir=str(temp_log_dir), level="WARNING")
        logger = AuditLogger(config=config)

        # INFO 级别应该被过滤
        logger.info("test_action", data="info_data")

        # WARNING 级别应该被记录
        logger.warning("test_warning", data="warning_data")

        # 给日志写入一点时间
        import time

        time.sleep(0.1)

        logger.close()

        # 读取日志文件
        log_files = list(temp_log_dir.glob("*.json"))
        if log_files:
            content = log_files[0].read_text(encoding="utf-8")
            # 应该只包含 WARNING 级别的日志
            assert "WARNING" in content
            assert "info_data" not in content

    def test_all_log_levels(self, temp_log_dir: Path) -> None:
        """
        测试所有日志级别

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(log_dir=str(temp_log_dir), level="DEBUG")
        logger = AuditLogger(config=config)

        # 记录所有级别的日志
        logger.debug("debug_action", value=1)
        logger.info("info_action", value=2)
        logger.success("success_action", value=3)
        logger.warning("warning_action", value=4)
        logger.error("error_action", value=5)
        logger.critical("critical_action", value=6)

        # 给日志写入一点时间
        import time

        time.sleep(0.1)

        logger.close()

        # 读取日志文件
        log_files = list(temp_log_dir.glob("*.json"))
        assert len(log_files) > 0

        content = log_files[0].read_text(encoding="utf-8")
        lines = [line for line in content.strip().split("\n") if line]

        # 验证所有级别都被记录
        assert len(lines) == 6

        # 解析并验证每条日志
        for line in lines:
            record = json.loads(line)
            assert "timestamp" in record
            assert "level" in record
            assert "level_name" in record
            assert "action" in record
            assert "data" in record

    def test_log_event_method(self, temp_log_dir: Path) -> None:
        """
        测试 log_event 方法

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(log_dir=str(temp_log_dir), level="INFO")
        logger = AuditLogger(config=config)

        logger.log_event(
            level=AuditLogger.LEVEL_INFO,
            action="user_login",
            user_id="12345",
            details={"ip": "192.168.1.1", "device": "mobile"},
        )

        import time

        time.sleep(0.1)

        logger.close()

        # 读取并验证日志
        log_files = list(temp_log_dir.glob("*.json"))
        content = log_files[0].read_text(encoding="utf-8")
        record = json.loads(content.strip().split("\n")[0])

        assert record["action"] == "user_login"
        assert record["data"]["user_id"] == "12345"
        assert record["data"]["ip"] == "192.168.1.1"

    def test_parse_json_record(self, temp_log_dir: Path) -> None:
        """
        测试解析 JSON 日志记录

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(log_dir=str(temp_log_dir))
        logger = AuditLogger(config=config)

        json_line = (
            '{"timestamp": "2024-01-01T00:00:00", "level": 20, "action": "test"}'
        )
        record = logger.parse_json_record(json_line)

        assert record["timestamp"] == "2024-01-01T00:00:00"
        assert record["level"] == 20
        assert record["action"] == "test"

        logger.close()

    def test_get_log_file(self, temp_log_dir: Path) -> None:
        """
        测试获取日志文件路径

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(log_dir=str(temp_log_dir))
        logger = AuditLogger(config=config)

        log_file = logger.get_log_file()
        assert log_file is not None
        assert "audit_" in str(log_file)
        assert "{time:" in str(log_file)  # 文件名包含时间格式

        logger.close()

    def test_logger_close(self, temp_log_dir: Path) -> None:
        """
        测试关闭日志记录器

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(log_dir=str(temp_log_dir))
        logger = AuditLogger(config=config)

        assert logger._sink_id is not None

        logger.close()

        assert logger._sink_id is None

    def test_logger_with_special_characters(self, temp_log_dir: Path) -> None:
        """
        测试包含特殊字符的数据

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(log_dir=str(temp_log_dir), level="INFO")
        logger = AuditLogger(config=config)

        # 包含 Unicode 字符
        logger.info("unicode_test", message="你好世界 🌍", emoji="🎉")

        # 包含引号和特殊字符
        logger.info("special_chars", data='{"key": "value with \\"quotes\\""}')

        import time

        time.sleep(0.1)

        logger.close()

        # 验证日志内容
        log_files = list(temp_log_dir.glob("*.json"))
        content = log_files[0].read_text(encoding="utf-8")

        for line in content.strip().split("\n"):
            record = json.loads(line)
            assert "timestamp" in record

    def test_logger_with_datetime_objects(self, temp_log_dir: Path) -> None:
        """
        测试包含 datetime 对象的数据

        Args:
            temp_log_dir: 临时日志目录
        """
        from datetime import datetime

        config = AuditLogConfig(log_dir=str(temp_log_dir), level="INFO")
        logger = AuditLogger(config=config)

        now = datetime.now()
        logger.info("datetime_test", created_at=now)

        import time

        time.sleep(0.1)

        logger.close()

        # 验证日志内容
        log_files = list(temp_log_dir.glob("*.json"))
        content = log_files[0].read_text(encoding="utf-8")
        record = json.loads(content.strip().split("\n")[0])

        assert "created_at" in record["data"]


# =============================================================================
# 模块级函数测试
# =============================================================================


class TestModuleLevelFunctions:
    """模块级便捷函数测试"""

    def test_get_audit_logger_singleton(self, cleanup_audit_logger) -> None:
        """
        测试获取审计日志记录器单例

        Args:
            cleanup_audit_logger: 清理 fixture
        """
        # 重新加载以获取干净的单例
        reload_audit_logger()

        logger1 = get_audit_logger()
        logger2 = get_audit_logger()

        # 应该是同一个实例
        assert logger1 is logger2

    def test_init_audit_logger(self, temp_log_dir: Path, cleanup_audit_logger) -> None:
        """
        测试初始化审计日志记录器

        Args:
            temp_log_dir: 临时日志目录
            cleanup_audit_logger: 清理 fixture
        """
        reload_audit_logger()

        logger = init_audit_logger(
            log_dir=str(temp_log_dir),
            level="DEBUG",
            rotation="5 MB",
            retention="14 days",
            encoding="utf-8",
        )

        assert logger.get_log_dir() == temp_log_dir
        assert logger._config.level == "DEBUG"

    def test_init_audit_logger_replaces_existing(
        self, temp_log_dir: Path, cleanup_audit_logger
    ) -> None:
        """
        测试重新初始化会替换现有记录器

        Args:
            temp_log_dir: 临时日志目录
            cleanup_audit_logger: 清理 fixture
        """
        reload_audit_logger()

        # 第一次初始化
        logger1 = init_audit_logger(log_dir=str(temp_log_dir / "first"))

        # 第二次初始化
        logger2 = init_audit_logger(log_dir=str(temp_log_dir / "second"))

        # 应该是不同的实例
        assert logger1 is not logger2
        assert get_audit_logger() is logger2

    def test_reload_audit_logger(self, temp_log_dir: Path) -> None:
        """
        测试重新加载审计日志记录器

        Args:
            temp_log_dir: 临时日志目录
        """
        # 先初始化
        init_audit_logger(log_dir=str(temp_log_dir))

        # 重新加载
        reload_audit_logger()

        # 下次获取应该是新实例
        logger_after = get_audit_logger()

        # 重新加载后，下次调用 get_audit_logger 会创建新实例
        # 但当前调用仍然返回旧实例直到被重新初始化
        assert logger_after is not None

    def test_convenience_functions(
        self, temp_log_dir: Path, cleanup_audit_logger
    ) -> None:
        """
        测试便捷函数

        Args:
            temp_log_dir: 临时日志目录
            cleanup_audit_logger: 清理 fixture
        """
        reload_audit_logger()
        init_audit_logger(log_dir=str(temp_log_dir), level="DEBUG")

        # 测试所有便捷函数
        debug("debug_action", value=1)
        info("info_action", value=2)
        success("success_action", value=3)
        warning("warning_action", value=4)
        error("error_action", value=5)
        critical("critical_action", value=6)

        import time

        time.sleep(0.1)

        # 验证日志目录
        assert get_log_dir() == temp_log_dir
        assert get_log_file() is not None

    def test_log_event_function(self, temp_log_dir: Path, cleanup_audit_logger) -> None:
        """
        测试 log_event 便捷函数

        Args:
            temp_log_dir: 临时日志目录
            cleanup_audit_logger: 清理 fixture
        """
        reload_audit_logger()
        init_audit_logger(log_dir=str(temp_log_dir), level="INFO")

        log_event(
            level=AuditLogger.LEVEL_INFO,
            action="test_event",
            user_id="user123",
            details={"key": "value"},
        )

        import time

        time.sleep(0.1)

        # 验证日志被记录
        log_files = list(temp_log_dir.glob("*.json"))
        assert len(log_files) > 0


# =============================================================================
# 边界条件测试
# =============================================================================


class TestEdgeCases:
    """边界条件测试"""

    def test_empty_action_name(self, temp_log_dir: Path) -> None:
        """
        测试空操作名称

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(log_dir=str(temp_log_dir), level="INFO")
        logger = AuditLogger(config=config)

        logger.info("", data="test")

        import time

        time.sleep(0.1)

        logger.close()

        log_files = list(temp_log_dir.glob("*.json"))
        content = log_files[0].read_text(encoding="utf-8")
        record = json.loads(content.strip().split("\n")[0])

        assert record["action"] == ""

    def test_none_values_in_data(self, temp_log_dir: Path) -> None:
        """
        测试数据中的 None 值

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(log_dir=str(temp_log_dir), level="INFO")
        logger = AuditLogger(config=config)

        logger.info("test_action", null_value=None, empty_string="")

        import time

        time.sleep(0.1)

        logger.close()

        log_files = list(temp_log_dir.glob("*.json"))
        content = log_files[0].read_text(encoding="utf-8")
        record = json.loads(content.strip().split("\n")[0])

        assert record["data"]["null_value"] is None
        assert record["data"]["empty_string"] == ""

    def test_nested_data(self, temp_log_dir: Path) -> None:
        """
        测试嵌套数据结构

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(log_dir=str(temp_log_dir), level="INFO")
        logger = AuditLogger(config=config)

        nested_data = {
            "user": {"id": "123", "name": "Test"},
            "permissions": ["read", "write"],
            "metadata": {"created": "2024-01-01", "version": 1.0},
        }

        logger.info("nested_test", **nested_data)

        import time

        time.sleep(0.1)

        logger.close()

        log_files = list(temp_log_dir.glob("*.json"))
        content = log_files[0].read_text(encoding="utf-8")
        record = json.loads(content.strip().split("\n")[0])

        assert record["data"]["user"]["id"] == "123"
        assert record["data"]["permissions"] == ["read", "write"]

    def test_large_data(self, temp_log_dir: Path) -> None:
        """
        测试大数据量

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(log_dir=str(temp_log_dir), level="INFO")
        logger = AuditLogger(config=config)

        # 创建较大的数据 - 注意 action 字段也会作为 data 的一部分
        large_data = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}

        logger.info("large_data_test", **large_data)

        import time

        time.sleep(0.1)

        logger.close()

        log_files = list(temp_log_dir.glob("*.json"))
        content = log_files[0].read_text(encoding="utf-8")
        record = json.loads(content.strip().split("\n")[0])

        # 验证数据包含所有键值对（包括 action 字段）
        assert len(record["data"]) >= 100


# =============================================================================
# 性能测试
# =============================================================================


class TestPerformance:
    """性能测试"""

    def test_high_frequency_logging(self, temp_log_dir: Path) -> None:
        """
        测试高频日志记录

        Args:
            temp_log_dir: 临时日志目录
        """
        config = AuditLogConfig(log_dir=str(temp_log_dir), level="INFO")
        logger = AuditLogger(config=config)

        import time

        start_time = time.time()

        # 记录 1000 条日志
        for i in range(1000):
            logger.info("high_freq", index=i)

        # 等待异步写入完成
        time.sleep(0.5)

        elapsed = time.time() - start_time

        logger.close()

        # 验证所有日志都被记录
        log_files = list(temp_log_dir.glob("*.json"))
        content = log_files[0].read_text(encoding="utf-8")
        lines = [line for line in content.strip().split("\n") if line]

        assert len(lines) == 1000
        # 性能要求：1000 条日志应在 5 秒内完成
        assert elapsed < 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
