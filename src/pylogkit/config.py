"""
日志配置模块

提供日志相关的配置类和工具函数，完全独立，无外部依赖。
"""

import os
import platform
from dataclasses import dataclass, field
from pathlib import Path

# 环境变量名常量
ENV_LOG_LEVEL = "LOG_LEVEL"
ENV_LOG_DIR = "LOG_DIR"
ENV_LOG_ROTATION = "LOG_ROTATION"
ENV_LOG_RETENTION = "LOG_RETENTION"
ENV_LOG_ENCODING = "LOG_ENCODING"
ENV_LOG_APP_NAME = "LOG_APP_NAME"

# 默认值常量
DEFAULT_LEVEL = "INFO"
DEFAULT_ROTATION = "10 MB"
DEFAULT_RETENTION = "7 days"
DEFAULT_ENCODING = "utf-8"
DEFAULT_APP_NAME = "app"


def get_default_log_dir(app_name: str = DEFAULT_APP_NAME) -> Path:
    """
    获取跨平台的默认日志目录

    根据操作系统返回合适的默认日志目录：
    - Windows: %APPDATA%\\{app_name}\\logs
    - macOS: ~/Library/Application Support/{app_name}/logs
    - Linux/Unix: ~/.local/share/{app_name}/logs

    Args:
        app_name: 应用名称，用于构建目录路径

    Returns:
        默认日志目录路径
    """
    system = platform.system()

    if system == "Windows":
        # Windows: %APPDATA%\{app_name}\logs
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / app_name / "logs"
        else:
            return Path.home() / "AppData" / "Roaming" / app_name / "logs"

    elif system == "Darwin":
        # macOS: ~/Library/Application Support/{app_name}/logs
        return Path.home() / "Library" / "Application Support" / app_name / "logs"

    else:
        # Linux/Unix: ~/.local/share/{app_name}/logs
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            return Path(xdg_data_home) / app_name / "logs"
        else:
            return Path.home() / ".local" / "share" / app_name / "logs"


@dataclass
class LogConfig:
    """
    日志配置类

    使用 dataclass 简化配置管理，支持从环境变量读取配置。

    Attributes:
        log_dir: 日志文件存储目录
        level: 日志级别
        rotation: 日志文件轮转条件
        retention: 日志文件保留时间
        encoding: 日志文件编码
        app_name: 应用名称前缀
    """

    log_dir: Path | str = field(default_factory=lambda: get_default_log_dir())
    level: str = DEFAULT_LEVEL
    rotation: str = DEFAULT_ROTATION
    retention: str = DEFAULT_RETENTION
    encoding: str = DEFAULT_ENCODING
    app_name: str = DEFAULT_APP_NAME

    def __post_init__(self) -> None:
        """初始化后处理，确保 log_dir 是 Path 对象"""
        if isinstance(self.log_dir, str):
            object.__setattr__(
                self, "log_dir", Path(os.path.normpath(self.log_dir))
            )

    def to_dict(self) -> dict:
        """
        将配置转换为字典格式

        Returns:
            配置字典
        """
        return {
            "log_dir": str(self.log_dir),
            "level": self.level,
            "rotation": self.rotation,
            "retention": self.retention,
            "encoding": self.encoding,
            "app_name": self.app_name,
        }

    def ensure_log_dir(self) -> None:
        """
        确保日志目录存在

        如果目录不存在则创建，创建失败时使用临时目录作为备选。
        """
        log_dir = Path(self.log_dir) if isinstance(self.log_dir, str) else self.log_dir
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            import tempfile

            log_dir = Path(tempfile.gettempdir()) / self.app_name / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            object.__setattr__(self, "log_dir", log_dir)

    @classmethod
    def from_env(cls, app_name: str | None = None) -> "LogConfig":
        """
        从环境变量读取配置创建 LogConfig 实例

        支持的环境变量：
        - LOG_LEVEL: 日志级别
        - LOG_DIR: 日志目录
        - LOG_ROTATION: 轮转条件
        - LOG_RETENTION: 保留时间
        - LOG_ENCODING: 文件编码
        - LOG_APP_NAME: 应用名称

        Args:
            app_name: 应用名称，如果为 None 则从环境变量读取

        Returns:
            LogConfig 实例
        """
        # 确定应用名称
        _app_name = app_name or os.environ.get(ENV_LOG_APP_NAME, DEFAULT_APP_NAME)

        # 从环境变量读取配置
        level = os.environ.get(ENV_LOG_LEVEL, DEFAULT_LEVEL)
        rotation = os.environ.get(ENV_LOG_ROTATION, DEFAULT_ROTATION)
        retention = os.environ.get(ENV_LOG_RETENTION, DEFAULT_RETENTION)
        encoding = os.environ.get(ENV_LOG_ENCODING, DEFAULT_ENCODING)

        # 日志目录
        log_dir_env = os.environ.get(ENV_LOG_DIR)
        if log_dir_env:
            log_dir = Path(os.path.normpath(log_dir_env))
        else:
            log_dir = get_default_log_dir(_app_name)

        return cls(
            log_dir=log_dir,
            level=level,
            rotation=rotation,
            retention=retention,
            encoding=encoding,
            app_name=_app_name,
        )
