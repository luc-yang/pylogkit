"""
审计日志模块

提供审计日志功能，支持结构化日志输出（JSON 格式），
可用于追踪用户操作、系统事件等。

审计日志与普通日志完全分离，使用独立的 logger 实例和 sink，
确保审计数据的安全性和可追溯性。

使用示例：

```python
from pylogkit.audit import info, success, warning, error

# 记录普通审计日志
info("user_login", user_id="12345", ip="192.168.1.1")

# 记录成功操作
success("file_uploaded", user_id="12345", filename="test.pdf", size=1024)

# 记录警告事件
warning("login_failed", user_id="12345", reason="invalid_password")

# 记录错误事件
error("payment_failed", order_id="ORD123", reason="insufficient_funds")
```
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


class AuditLogConfig:
    """审计日志配置类"""

    def __init__(
        self,
        log_dir: str | Path | None = None,
        level: str = "INFO",
        rotation: str = "10 MB",
        retention: str = "30 days",
        encoding: str = "utf-8",
    ):
        """
        初始化审计日志配置

        Args:
            log_dir: 审计日志文件存储目录，默认为当前目录下的 logs/audit/
            level: 日志级别，默认 "INFO"
            rotation: 日志文件轮转条件，默认 "10 MB"
            retention: 日志文件保留时间，默认 "30 days"
            encoding: 日志文件编码，默认 "utf-8"
        """
        if log_dir:
            self.log_dir = Path(os.path.normpath(log_dir))
        else:
            # 默认使用本地 logs/audit 目录
            self.log_dir = Path("logs") / "audit"

        self.level = level.upper()
        self.rotation = rotation
        self.retention = retention
        self.encoding = encoding

    def to_dict(self) -> dict[str, Any]:
        """将配置转换为字典格式"""
        return {
            "log_dir": str(self.log_dir),
            "level": self.level,
            "rotation": self.rotation,
            "retention": self.retention,
            "encoding": self.encoding,
        }


class AuditLogger:
    """审计日志记录器

    使用独立的 loguru logger 实例，确保审计日志与普通日志完全分离。
    支持 JSON 格式输出，便于后续分析和处理。
    """

    # 审计日志级别
    LEVEL_DEBUG = 10
    LEVEL_INFO = 20
    LEVEL_SUCCESS = 25
    LEVEL_WARNING = 30
    LEVEL_ERROR = 40
    LEVEL_CRITICAL = 50

    # 级别名称映射
    _LEVEL_MAP = {
        "DEBUG": LEVEL_DEBUG,
        "INFO": LEVEL_INFO,
        "SUCCESS": LEVEL_SUCCESS,
        "WARNING": LEVEL_WARNING,
        "ERROR": LEVEL_ERROR,
        "CRITICAL": LEVEL_CRITICAL,
    }

    def __init__(
        self,
        config: AuditLogConfig | None = None,
    ):
        """
        初始化审计日志记录器

        Args:
            config: 审计日志配置，如果为 None 则使用默认配置
        """
        self._config = config or AuditLogConfig()
        self._sink_id: int | None = None
        self._log_file: Path | None = None

        # 创建独立的 logger 实例，绑定 audit 标记
        self._logger = logger.bind(audit=True)

        # 初始化 sink
        self._setup_sink()

    def _setup_sink(self) -> None:
        """设置审计日志的 sink"""
        # 确保目录存在
        try:
            self._config.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # 失败则使用临时目录
            import tempfile

            self._config.log_dir = (
                Path(os.path.normpath(tempfile.gettempdir())) / "audit_logs"
            )
            self._config.log_dir.mkdir(parents=True, exist_ok=True)

        # 设置日志文件路径
        self._log_file = self._config.log_dir / "audit_{time:YYYY-MM-DD}.json"

        # 获取级别数值
        level_value = self._LEVEL_MAP.get(self._config.level, self.LEVEL_INFO)
        self._level = level_value

        # 添加 JSON 格式的文件输出
        # 使用自定义的序列化格式，确保输出纯净的 JSON
        self._sink_id = self._logger.add(
            sink=str(self._log_file),
            level=level_value,
            format="{message}",  # 只输出消息内容
            serialize=False,  # 我们手动处理 JSON 序列化
            enqueue=True,  # 使用异步写入避免阻塞
            catch=True,
            rotation=self._config.rotation,
            retention=self._config.retention,
            encoding=self._config.encoding,
        )

    def _serialize_record(
        self,
        level: int,
        level_name: str,
        action: str,
        extra_data: dict[str, Any],
    ) -> str:
        """
        序列化审计日志记录为 JSON 格式

        Args:
            level: 日志级别数值
            level_name: 级别名称
            action: 操作名称
            extra_data: 额外的数据字段

        Returns:
            JSON 格式的字符串
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "level_name": level_name,
            "action": action,
            "data": extra_data,
        }
        return json.dumps(record, ensure_ascii=False, default=str)

    def _log(self, level: int, level_name: str, action: str, **kwargs: Any) -> None:
        """
        记录审计日志的内部方法

        Args:
            level: 日志级别数值
            level_name: 级别名称
            action: 操作名称
            **kwargs: 额外的数据字段
        """
        if level < self._level:
            return

        extra_data = {"action": action}
        extra_data.update(kwargs)

        # 序列化为 JSON 并输出
        json_message = self._serialize_record(level, level_name, action, extra_data)
        self._logger.opt(depth=2).log(level, json_message)

    def debug(self, action: str, **kwargs: Any) -> None:
        """
        记录调试级别的审计日志

        Args:
            action: 操作名称
            **kwargs: 额外的数据字段
        """
        self._log(self.LEVEL_DEBUG, "DEBUG", action, **kwargs)

    def info(self, action: str, **kwargs: Any) -> None:
        """
        记录信息级别的审计日志

        Args:
            action: 操作名称
            **kwargs: 额外的数据字段
        """
        self._log(self.LEVEL_INFO, "INFO", action, **kwargs)

    def success(self, action: str, **kwargs: Any) -> None:
        """
        记录成功的审计日志

        Args:
            action: 操作名称
            **kwargs: 额外的数据字段
        """
        self._log(self.LEVEL_SUCCESS, "SUCCESS", action, **kwargs)

    def warning(self, action: str, **kwargs: Any) -> None:
        """
        记录警告级别的审计日志

        Args:
            action: 操作名称
            **kwargs: 额外的数据字段
        """
        self._log(self.LEVEL_WARNING, "WARNING", action, **kwargs)

    def error(self, action: str, **kwargs: Any) -> None:
        """
        记录错误级别的审计日志

        Args:
            action: 操作名称
            **kwargs: 额外的数据字段
        """
        self._log(self.LEVEL_ERROR, "ERROR", action, **kwargs)

    def critical(self, action: str, **kwargs: Any) -> None:
        """
        记录严重错误级别的审计日志

        Args:
            action: 操作名称
            **kwargs: 额外的数据字段
        """
        self._log(self.LEVEL_CRITICAL, "CRITICAL", action, **kwargs)

    def log_event(
        self,
        level: int,
        action: str,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        记录通用审计事件

        Args:
            level: 日志级别
            action: 操作名称
            user_id: 用户 ID
            details: 详细信息字典
        """
        kwargs: dict[str, Any] = details or {}
        if user_id:
            kwargs["user_id"] = user_id
        self._log(level, "EVENT", action, **kwargs)

    def get_log_dir(self) -> Path:
        """
        获取审计日志文件存储目录

        Returns:
            审计日志目录路径
        """
        return self._config.log_dir

    def get_log_file(self) -> Path | None:
        """
        获取当前审计日志文件路径

        Returns:
            审计日志文件路径
        """
        return self._log_file

    def parse_json_record(self, json_line: str) -> dict[str, Any]:
        """
        解析 JSON 格式的日志记录

        Args:
            json_line: JSON 格式的日志行

        Returns:
            解析后的字典
        """
        result: dict[str, Any] = json.loads(json_line)
        return result

    def close(self) -> None:
        """关闭审计日志记录器，移除 sink"""
        if self._sink_id is not None:
            self._logger.remove(self._sink_id)
            self._sink_id = None


# 全局审计日志记录器实例（延迟初始化）
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """
    获取审计日志记录器实例（延迟初始化）

    Returns:
        AuditLogger 实例
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def init_audit_logger(
    log_dir: str | Path | None = None,
    level: str = "INFO",
    rotation: str = "10 MB",
    retention: str = "30 days",
    encoding: str = "utf-8",
) -> AuditLogger:
    """
    初始化审计日志记录器

    Args:
        log_dir: 审计日志文件存储目录
        level: 日志级别，默认 "INFO"
        rotation: 日志文件轮转条件，默认 "10 MB"
        retention: 日志文件保留时间，默认 "30 days"
        encoding: 日志文件编码，默认 "utf-8"

    Returns:
        AuditLogger 实例
    """
    global _audit_logger

    # 如果已存在，先关闭旧的
    if _audit_logger is not None:
        _audit_logger.close()

    config = AuditLogConfig(
        log_dir=log_dir,
        level=level,
        rotation=rotation,
        retention=retention,
        encoding=encoding,
    )
    _audit_logger = AuditLogger(config=config)
    return _audit_logger


def reload_audit_logger() -> None:
    """
    重新加载审计日志记录器
    在审计日志配置变更时调用
    """
    global _audit_logger
    if _audit_logger is not None:
        _audit_logger.close()
        _audit_logger = None


# =============================================================================
# 导出便捷函数（使用包装函数实现延迟初始化）
# =============================================================================


def debug(action: str, **kwargs: Any) -> None:
    """
    记录调试级别的审计日志

    Args:
        action: 操作名称
        **kwargs: 额外的数据字段
    """
    return get_audit_logger().debug(action, **kwargs)


def info(action: str, **kwargs: Any) -> None:
    """
    记录信息级别的审计日志

    Args:
        action: 操作名称
        **kwargs: 额外的数据字段
    """
    return get_audit_logger().info(action, **kwargs)


def success(action: str, **kwargs: Any) -> None:
    """
    记录成功的审计日志

    Args:
        action: 操作名称
        **kwargs: 额外的数据字段
    """
    return get_audit_logger().success(action, **kwargs)


def warning(action: str, **kwargs: Any) -> None:
    """
    记录警告级别的审计日志

    Args:
        action: 操作名称
        **kwargs: 额外的数据字段
    """
    return get_audit_logger().warning(action, **kwargs)


def error(action: str, **kwargs: Any) -> None:
    """
    记录错误级别的审计日志

    Args:
        action: 操作名称
        **kwargs: 额外的数据字段
    """
    return get_audit_logger().error(action, **kwargs)


def critical(action: str, **kwargs: Any) -> None:
    """
    记录严重错误级别的审计日志

    Args:
        action: 操作名称
        **kwargs: 额外的数据字段
    """
    return get_audit_logger().critical(action, **kwargs)


def log_event(
    level: int,
    action: str,
    user_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """
    记录通用审计事件

    Args:
        level: 日志级别
        action: 操作名称
        user_id: 用户 ID
        details: 详细信息字典
    """
    return get_audit_logger().log_event(level, action, user_id=user_id, details=details)


def get_log_dir() -> Path:
    """
    获取审计日志文件存储目录

    Returns:
        审计日志目录路径
    """
    return get_audit_logger().get_log_dir()


def get_log_file() -> Path | None:
    """
    获取当前审计日志文件路径

    Returns:
        审计日志文件路径
    """
    return get_audit_logger().get_log_file()


__all__ = [
    # 配置类
    "AuditLogConfig",
    # 记录器类
    "AuditLogger",
    # 实例管理函数
    "get_audit_logger",
    "init_audit_logger",
    "reload_audit_logger",
    # 便捷函数
    "debug",
    "info",
    "success",
    "warning",
    "error",
    "critical",
    "log_event",
    "get_log_dir",
    "get_log_file",
]
