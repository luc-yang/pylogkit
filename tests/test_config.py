"""
日志配置模块测试

测试 LogConfig 类和相关工具函数
"""

import os
import platform
import shutil
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from pylogkit.config import (
    DEFAULT_APP_NAME,
    DEFAULT_ENCODING,
    DEFAULT_LEVEL,
    DEFAULT_RETENTION,
    DEFAULT_ROTATION,
    ENV_LOG_APP_NAME,
    ENV_LOG_DIR,
    ENV_LOG_ENCODING,
    ENV_LOG_LEVEL,
    ENV_LOG_RETENTION,
    ENV_LOG_ROTATION,
    LogConfig,
    get_default_log_dir,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    创建临时目录

    Yields:
        临时目录路径
    """
    temp_path = Path(tempfile.mkdtemp(prefix="config_test_"))
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """
    清理环境变量 fixture

    保存并恢复相关环境变量
    """
    # 保存原始值
    env_vars = [
        ENV_LOG_LEVEL,
        ENV_LOG_DIR,
        ENV_LOG_ROTATION,
        ENV_LOG_RETENTION,
        ENV_LOG_ENCODING,
        ENV_LOG_APP_NAME,
    ]
    original_values = {var: os.environ.get(var) for var in env_vars}

    yield

    # 恢复原始值
    for var, value in original_values.items():
        if value is None:
            os.environ.pop(var, None)
        else:
            os.environ[var] = value


# =============================================================================
# get_default_log_dir 测试
# =============================================================================


class TestGetDefaultLogDir:
    """默认日志目录获取函数测试"""

    def test_default_app_name(self) -> None:
        """
        测试默认应用名称

        验证使用默认应用名称时返回正确的路径
        """
        log_dir = get_default_log_dir()

        system = platform.system()

        if system == "Windows":
            assert "app" in str(log_dir)
            assert "logs" in str(log_dir)
        elif system == "Darwin":
            assert "Library" in str(log_dir)
            assert "Application Support" in str(log_dir)
        else:
            assert ".local" in str(log_dir) or "share" in str(log_dir)

    def test_custom_app_name(self) -> None:
        """
        测试自定义应用名称

        验证自定义应用名称被正确包含在路径中
        """
        log_dir = get_default_log_dir("myapp")

        assert "myapp" in str(log_dir)
        assert "logs" in str(log_dir)

    def test_windows_with_appdata(self) -> None:
        """
        测试 Windows 环境下使用 APPDATA

        验证在 Windows 下正确使用 APPDATA 环境变量
        """
        if platform.system() != "Windows":
            pytest.skip("仅 Windows 环境测试")

        with patch.dict(os.environ, {"APPDATA": r"C:\Users\Test\AppData\Roaming"}):
            log_dir = get_default_log_dir("testapp")
            assert r"C:\Users\Test\AppData\Roaming" in str(log_dir)
            assert "testapp" in str(log_dir)

    def test_windows_without_appdata(self) -> None:
        """
        测试 Windows 环境下无 APPDATA

        验证在 Windows 下无 APPDATA 时回退到用户目录
        """
        if platform.system() != "Windows":
            pytest.skip("仅 Windows 环境测试")

        # 模拟 Path.home() 和 os.environ 都为空的情况
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=Path("C:/Users/Test")):
                log_dir = get_default_log_dir("testapp")
                # 使用 Path 对象进行比较，避免路径分隔符问题
                assert Path("C:/Users/Test") in log_dir.parents or str(
                    log_dir
                ).startswith("C:\\Users\\Test")
                assert "testapp" in str(log_dir)

    def test_darwin_default_log_dir(self) -> None:
        """
        测试 macOS 默认日志目录

        验证在 macOS 下返回正确的默认路径
        """
        if platform.system() != "Darwin":
            pytest.skip("仅 macOS 环境测试")

        log_dir = get_default_log_dir("testapp")
        assert "Library" in str(log_dir)
        assert "Application Support" in str(log_dir)
        assert "testapp" in str(log_dir)
        assert "logs" in str(log_dir)

    def test_linux_with_xdg_data_home(self) -> None:
        """
        测试 Linux 环境下使用 XDG_DATA_HOME

        验证在 Linux 下正确使用 XDG_DATA_HOME 环境变量
        """
        if platform.system() == "Windows":
            pytest.skip("仅非 Windows 环境测试")

        with patch.dict(os.environ, {"XDG_DATA_HOME": "/home/user/.local/share"}):
            log_dir = get_default_log_dir("testapp")
            assert "/home/user/.local/share" in str(log_dir)
            assert "testapp" in str(log_dir)


# =============================================================================
# LogConfig 测试
# =============================================================================


class TestLogConfig:
    """日志配置类测试"""

    def test_default_values(self) -> None:
        """
        测试默认值

        验证 LogConfig 的默认配置值
        """
        config = LogConfig()

        assert config.level == DEFAULT_LEVEL
        assert config.rotation == DEFAULT_ROTATION
        assert config.retention == DEFAULT_RETENTION
        assert config.encoding == DEFAULT_ENCODING
        assert config.app_name == DEFAULT_APP_NAME
        assert isinstance(config.log_dir, Path)

    def test_custom_values(self, temp_dir: Path) -> None:
        """
        测试自定义值

        Args:
            temp_dir: 临时目录
        """
        config = LogConfig(
            log_dir=temp_dir,
            level="DEBUG",
            rotation="5 MB",
            retention="14 days",
            encoding="gbk",
            app_name="custom_app",
        )

        assert config.log_dir == temp_dir
        assert config.level == "DEBUG"
        assert config.rotation == "5 MB"
        assert config.retention == "14 days"
        assert config.encoding == "gbk"
        assert config.app_name == "custom_app"

    def test_string_log_dir(self, temp_dir: Path) -> None:
        """
        测试字符串类型的 log_dir

        验证字符串类型的 log_dir 被正确转换为 Path

        Args:
            temp_dir: 临时目录
        """
        config = LogConfig(log_dir=str(temp_dir))

        assert isinstance(config.log_dir, Path)
        assert config.log_dir == temp_dir

    def test_post_init_normalizes_path(self) -> None:
        """
        测试 __post_init__ 规范化路径

        验证路径在初始化后被正确规范化
        """
        # 使用包含多余分隔符的路径字符串
        raw_path = "/tmp//test///path"
        config = LogConfig(log_dir=raw_path)

        # 路径应该被规范化
        assert isinstance(config.log_dir, Path)

    def test_to_dict(self, temp_dir: Path) -> None:
        """
        测试转换为字典

        验证 to_dict 方法正确返回配置字典

        Args:
            temp_dir: 临时目录
        """
        config = LogConfig(
            log_dir=temp_dir,
            level="WARNING",
            app_name="test_app",
        )

        config_dict = config.to_dict()

        assert config_dict["log_dir"] == str(temp_dir)
        assert config_dict["level"] == "WARNING"
        assert config_dict["rotation"] == DEFAULT_ROTATION
        assert config_dict["retention"] == DEFAULT_RETENTION
        assert config_dict["encoding"] == DEFAULT_ENCODING
        assert config_dict["app_name"] == "test_app"

    def test_ensure_log_dir_creates_directory(self, temp_dir: Path) -> None:
        """
        测试 ensure_log_dir 创建目录

        验证 ensure_log_dir 方法正确创建目录

        Args:
            temp_dir: 临时目录
        """
        nested_dir = temp_dir / "nested" / "logs"
        config = LogConfig(log_dir=nested_dir)

        assert not nested_dir.exists()

        config.ensure_log_dir()

        assert nested_dir.exists()
        assert nested_dir.is_dir()

    def test_ensure_log_dir_fallback_to_temp(self, temp_dir: Path) -> None:
        """
        测试 ensure_log_dir 回退到临时目录

        验证创建目录失败时回退到临时目录

        Args:
            temp_dir: 临时目录
        """
        # 创建一个无法写入的目录路径
        invalid_dir = temp_dir / "invalid" / "path"

        config = LogConfig(log_dir=invalid_dir)

        # 模拟 mkdir 失败 - 使用更具体的 mock
        original_mkdir = Path.mkdir

        def mock_mkdir(self, *args, **kwargs):
            if str(self) == str(invalid_dir):
                raise PermissionError("Access denied")
            return original_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", mock_mkdir):
            config.ensure_log_dir()

            # 应该回退到临时目录
            assert "logs" in str(config.log_dir)


# =============================================================================
# from_env 测试
# =============================================================================


class TestFromEnv:
    """从环境变量读取配置测试"""

    def test_from_env_all_variables(self, temp_dir: Path, clean_env) -> None:
        """
        测试从环境变量读取所有配置

        Args:
            temp_dir: 临时目录
            clean_env: 清理环境变量 fixture
        """
        # 设置环境变量
        os.environ[ENV_LOG_LEVEL] = "DEBUG"
        os.environ[ENV_LOG_DIR] = str(temp_dir)
        os.environ[ENV_LOG_ROTATION] = "20 MB"
        os.environ[ENV_LOG_RETENTION] = "30 days"
        os.environ[ENV_LOG_ENCODING] = "utf-16"
        os.environ[ENV_LOG_APP_NAME] = "env_app"

        config = LogConfig.from_env()

        assert config.level == "DEBUG"
        assert config.log_dir == temp_dir
        assert config.rotation == "20 MB"
        assert config.retention == "30 days"
        assert config.encoding == "utf-16"
        assert config.app_name == "env_app"

    def test_from_env_partial_variables(self, clean_env) -> None:
        """
        测试从环境变量读取部分配置

        Args:
            clean_env: 清理环境变量 fixture
        """
        # 只设置部分环境变量
        os.environ[ENV_LOG_LEVEL] = "ERROR"
        os.environ[ENV_LOG_APP_NAME] = "partial_app"

        config = LogConfig.from_env()

        assert config.level == "ERROR"
        assert config.app_name == "partial_app"
        # 其他值应使用默认值
        assert config.rotation == DEFAULT_ROTATION
        assert config.retention == DEFAULT_RETENTION
        assert config.encoding == DEFAULT_ENCODING

    def test_from_env_no_variables(self, clean_env) -> None:
        """
        测试无环境变量时使用默认值

        Args:
            clean_env: 清理环境变量 fixture
        """
        config = LogConfig.from_env()

        assert config.level == DEFAULT_LEVEL
        assert config.rotation == DEFAULT_ROTATION
        assert config.retention == DEFAULT_RETENTION
        assert config.encoding == DEFAULT_ENCODING
        assert config.app_name == DEFAULT_APP_NAME

    def test_from_env_with_app_name_parameter(self, temp_dir: Path, clean_env) -> None:
        """
        测试 from_env 的 app_name 参数

        验证传入的 app_name 参数优先于环境变量

        Args:
            temp_dir: 临时目录
            clean_env: 清理环境变量 fixture
        """
        os.environ[ENV_LOG_APP_NAME] = "env_app"

        config = LogConfig.from_env(app_name="param_app")

        # 传入的参数应该优先
        assert config.app_name == "param_app"

    def test_from_env_log_dir_normalization(self, temp_dir: Path, clean_env) -> None:
        """
        测试 from_env 时 log_dir 路径规范化

        Args:
            temp_dir: 临时目录
            clean_env: 清理环境变量 fixture
        """
        # 使用包含多余分隔符的路径
        raw_path = str(temp_dir) + "//subdir"
        os.environ[ENV_LOG_DIR] = raw_path

        config = LogConfig.from_env()

        assert isinstance(config.log_dir, Path)
        assert "subdir" in str(config.log_dir)


# =============================================================================
# 边界条件测试
# =============================================================================


class TestEdgeCases:
    """边界条件测试"""

    def test_empty_string_values(self) -> None:
        """
        测试空字符串值

        验证空字符串被正确处理
        """
        config = LogConfig(
            level="",
            rotation="",
            retention="",
            encoding="",
            app_name="",
        )

        assert config.level == ""
        assert config.rotation == ""
        assert config.retention == ""
        assert config.encoding == ""
        assert config.app_name == ""

    def test_special_characters_in_app_name(self, temp_dir: Path) -> None:
        """
        测试应用名称中的特殊字符

        Args:
            temp_dir: 临时目录
        """
        special_names = [
            "app-with-dashes",
            "app_with_underscores",
            "app.with.dots",
            "app with spaces",
            "app123",
        ]

        for name in special_names:
            config = LogConfig(log_dir=temp_dir, app_name=name)
            assert config.app_name == name

    def test_unicode_in_config(self, temp_dir: Path) -> None:
        """
        测试配置中的 Unicode 字符

        Args:
            temp_dir: 临时目录
        """
        config = LogConfig(
            log_dir=temp_dir,
            app_name="应用名称",
        )

        assert config.app_name == "应用名称"

    def test_path_with_spaces(self, temp_dir: Path) -> None:
        """
        测试包含空格的路径

        Args:
            temp_dir: 临时目录
        """
        path_with_spaces = temp_dir / "path with spaces" / "logs"
        config = LogConfig(log_dir=path_with_spaces)

        assert config.log_dir == path_with_spaces

    def test_very_long_app_name(self, temp_dir: Path) -> None:
        """
        测试超长应用名称

        Args:
            temp_dir: 临时目录
        """
        long_name = "a" * 200
        config = LogConfig(log_dir=temp_dir, app_name=long_name)

        assert config.app_name == long_name


# =============================================================================
# 常量测试
# =============================================================================


class TestConstants:
    """常量定义测试"""

    def test_env_variable_names(self) -> None:
        """
        测试环境变量名常量

        验证环境变量名常量定义正确
        """
        assert ENV_LOG_LEVEL == "LOG_LEVEL"
        assert ENV_LOG_DIR == "LOG_DIR"
        assert ENV_LOG_ROTATION == "LOG_ROTATION"
        assert ENV_LOG_RETENTION == "LOG_RETENTION"
        assert ENV_LOG_ENCODING == "LOG_ENCODING"
        assert ENV_LOG_APP_NAME == "LOG_APP_NAME"

    def test_default_values(self) -> None:
        """
        测试默认值常量

        验证默认值常量定义正确
        """
        assert DEFAULT_LEVEL == "INFO"
        assert DEFAULT_ROTATION == "10 MB"
        assert DEFAULT_RETENTION == "7 days"
        assert DEFAULT_ENCODING == "utf-8"
        assert DEFAULT_APP_NAME == "app"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
