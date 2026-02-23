"""
PyLogKit - 基于 loguru 的独立日志基础设施

本模块提供了一套通用的日志基础设施，基于 loguru 实现，
可轻松复用于 PyQt 等中小型项目。

模块架构：
- core.py: 核心日志功能（基于 loguru）
- config.py: 配置类和工具函数
- utils.py: 实用工具（异常捕获装饰器等）
- audit.py: 审计日志子模块（JSON 结构化）
- qt_integration.py: PyQt 集成支持（可选依赖）

使用示例：

```python
# 方式一：直接使用导出的函数
from pylogkit import info, error, debug, warning

info("用户登录: %s", user_id)
error("数据库连接失败: %s", e)

# 方式二：获取 logger 实例
from pylogkit import get_logger

logger = get_logger()
logger.debug("详细调试信息")

# 方式三：初始化并配置
from pylogkit import init_logger, set_level

# 自定义初始化
init_logger(log_dir="/custom/logs", level="DEBUG")

# 动态调整日志级别
set_level("WARNING")

# 方式四：使用审计日志
from pylogkit.audit import info as audit_info
audit_info("user_login", user_id="12345", ip="192.168.1.1")

# 方式五：异常捕获装饰器
from pylogkit import catch_exceptions

@catch_exceptions(reraise=False)
def my_function():
    raise ValueError("测试异常")
```

功能特性：
- 支持 DEBUG, INFO, WARNING, ERROR, CRITICAL 日志级别
- 控制台彩色输出 + 文件输出
- 自动日志轮转、压缩和清理
- 线程安全的异步写入
- 跨平台默认日志目录
- 完整的类型注解
"""

__version__ = "0.1.0"

# =============================================================================
# 从 core.py 导入主要功能
# =============================================================================
# =============================================================================
# 从 audit.py 导入审计日志子模块（保持向后兼容）
# 可以通过 from log import audit 或 from log.audit import info 使用
# =============================================================================
from . import audit

# =============================================================================
# 从 config.py 导入配置相关
# =============================================================================
from .config import (
    LogConfig,
    get_default_log_dir,
)
from .core import (
    critical,
    debug,
    error,
    exception,
    get_config,
    get_log_dir,
    get_logger,
    info,
    init_logger,
    set_level,
    shutdown,
    warning,
)

# =============================================================================
# 从 utils.py 导入工具函数
# =============================================================================
from .utils import catch_exceptions

# =============================================================================
# 从 qt_integration.py 导入 PyQt 集成（可选依赖）
# =============================================================================
try:
    from .qt_integration import (
        LogSignalEmitter,
        QtLogHandler,
        has_pyqt,
    )

    _qt_available = True
except ImportError:
    _qt_available = False
    # 定义占位符，确保导入不会失败
    LogSignalEmitter = None  # type: ignore
    QtLogHandler = None  # type: ignore

    def has_pyqt() -> bool:
        return False

# =============================================================================
# 向后兼容的 API 导出（与原来相同的导出列表）
# =============================================================================
__all__ = [
    # 版本信息
    "__version__",
    # 核心日志函数
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    "exception",
    # 日志管理函数
    "get_logger",
    "init_logger",
    "set_level",
    "get_log_dir",
    "get_config",
    "shutdown",
    # 配置类
    "LogConfig",
    "get_default_log_dir",
    # 工具函数
    "catch_exceptions",
    # 审计日志子模块
    "audit",
    # PyQt 集成（可能为 None）
    "LogSignalEmitter",
    "QtLogHandler",
    "has_pyqt",
]
