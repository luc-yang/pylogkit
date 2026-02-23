# 📦 PyLogKit

基于 [loguru](https://github.com/Delgan/loguru) 的独立日志基础设施 🚀，专为 Python 应用程序设计，特别适用于 PyQt 等桌面应用项目。

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 📝 项目描述

PyLogKit 提供了一套完整的日志解决方案，旨在简化日志管理的同时提供企业级的功能特性。该库封装了 loguru 的强大功能，提供了更加便捷的 API 和额外的实用工具。

### ✨ 核心功能

- 🔌 **统一日志接口**：简化的 API 设计，支持多种使用方式
- 🖥️ **跨平台支持**：自动适配 Windows、macOS 和 Linux 的日志存储路径
- 📊 **审计日志**：独立的 JSON 结构化审计日志系统
- 🎨 **PyQt 集成**：可选的 PyQt5/PyQt6 集成支持
- 🛡️ **异常处理**：便捷的异常捕获装饰器
- 📝 **类型注解**：完整的类型提示支持

### 🎯 适用场景

- 💻 桌面应用程序（PyQt/PySide）
- ⌨️ 命令行工具
- 🖥️ 服务端脚本
- 📋 需要结构化审计日志的业务系统

## 📦 安装

### 基础安装

```bash
pip install pylogkit
```

或使用 uv：

```bash
uv add pylogkit
```

### 可选依赖

如果需要 PyQt 集成支持：

```bash
pip install pylogkit[pyqt]
# 或
uv add pylogkit --extra pyqt
```

### 开发依赖

```bash
pip install pylogkit[dev]
# 或
uv add pylogkit --extra dev
```

## 🚀 快速开始

### 示例一：直接使用导出的函数

最简单的方式是直接使用模块导出的日志函数：

```python
from pylogkit import info, error, debug, warning, critical

# 记录不同级别的日志
info("用户 %s 登录成功", "admin")
debug("数据库查询耗时: %.2f 秒", 0.023)
warning("磁盘空间不足: 剩余 %d%%", 15)
error("连接数据库失败: %s", "Connection refused")
critical("系统内存耗尽，即将退出")
```

### 示例二：获取 Logger 实例

需要更多控制时，可以获取 logger 实例：

```python
from pylogkit import get_logger

logger = get_logger()

# 使用 logger 实例
logger.debug("详细调试信息")
logger.info("一般信息")
logger.bind(user_id="12345").info("带上下文的日志")
```

### 示例三：自定义初始化

在应用启动时进行自定义配置：

```python
from pylogkit import init_logger, set_level

# 自定义初始化
init_logger(
    app_name="myapp",
    log_dir="/var/log/myapp",
    level="DEBUG",
    rotation="5 MB",
    retention="14 days"
)

# 动态调整日志级别
set_level("WARNING")
```

### 示例四：使用审计日志

审计日志用于记录重要的业务操作，以 JSON 格式存储：

```python
from pylogkit.audit import info, success, warning, error

# 记录用户登录
info("user_login", user_id="12345", ip="192.168.1.1", user_agent="Mozilla/5.0")

# 记录操作成功
success("file_uploaded", user_id="12345", filename="report.pdf", size=1024000)

# 记录警告事件
warning("login_failed", user_id="12345", reason="invalid_password", attempt=3)

# 记录错误事件
error("payment_failed", order_id="ORD123456", reason="insufficient_funds", amount=99.99)
```

审计日志输出格式（JSON）：

```json
{
  "timestamp": "2026-02-22T10:30:45.123456",
  "level": 20,
  "level_name": "INFO",
  "action": "user_login",
  "data": {
    "action": "user_login",
    "user_id": "12345",
    "ip": "192.168.1.1"
  }
}
```

### 示例五：异常捕获装饰器

自动捕获并记录函数异常：

```python
from pylogkit import catch_exceptions, error

# 方式一：不带括号使用（默认参数）
@catch_exceptions
def risky_function():
    raise ValueError("发生错误")

# 方式二：带括号使用（自定义参数）
@catch_exceptions(reraise=False, message="操作失败")
def safe_function():
    raise ValueError("发生错误")

# 方式三：指定自定义日志函数
@catch_exceptions(logger_func=error, reraise=False)
def custom_log_function():
    raise ValueError("发生错误")
```

### 示例六：PyQt 集成

在 PyQt 应用中显示日志：

```python
from PyQt6.QtWidgets import QApplication, QTextEdit, QVBoxLayout, QWidget
from pylogkit import get_logger, info
from pylogkit.qt_integration import LogSignalEmitter, QtLogHandler

class LogWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # 创建信号发射器和处理器
        self.log_emitter = LogSignalEmitter()
        self.log_handler = QtLogHandler(self.log_emitter)
        
        # 连接信号到 GUI 更新
        self.log_emitter.log_message.connect(self.append_log)
        
        # 添加到 loguru
        logger = get_logger()
        logger.add(self.log_handler.emit)
        
        # 创建界面
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        
        layout = QVBoxLayout()
        layout.addWidget(self.log_edit)
        self.setLayout(layout)
    
    def append_log(self, message: str):
        self.log_edit.append(message)

# 使用
app = QApplication([])
window = LogWindow()
window.show()

info("这条日志会显示在 GUI 中")

app.exec()
```

## ⚙️ 配置选项

### 🔧 核心配置参数

#### `init_logger()` 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `app_name` | `str` | `"app"` | 应用名称前缀，用于构建日志文件名和目录 |
| `log_dir` | `str \| Path \| None` | `None` | 日志文件存储目录，None 时使用跨平台默认目录 |
| `level` | `str` | `"INFO"` | 日志级别，可选值：`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `rotation` | `str` | `"10 MB"` | 日志文件轮转条件，支持大小格式（如 `"10 MB"`）或时间格式（如 `"1 day"`） |
| `retention` | `str` | `"7 days"` | 日志文件保留时间，如 `"7 days"` |
| `encoding` | `str` | `"utf-8"` | 日志文件编码 |
| `console_output` | `bool` | `True` | 是否输出到控制台 |
| `file_output` | `bool` | `True` | 是否输出到文件 |

### 🌍 环境变量配置

PyLogKit 支持通过环境变量进行配置：

| 环境变量 | 说明 | 示例值 |
|----------|------|--------|
| `LOG_LEVEL` | 日志级别 | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_DIR` | 日志目录 | `/var/log/myapp` |
| `LOG_ROTATION` | 轮转条件 | `10 MB`, `1 day` |
| `LOG_RETENTION` | 保留时间 | `7 days`, `1 month` |
| `LOG_ENCODING` | 文件编码 | `utf-8`, `gbk` |
| `LOG_APP_NAME` | 应用名称 | `myapp` |

使用示例：

```bash
# Linux/macOS
export LOG_LEVEL=DEBUG
export LOG_DIR=/var/log/myapp
export LOG_RETENTION="14 days"

# Windows PowerShell
$env:LOG_LEVEL="DEBUG"
$env:LOG_DIR="C:\Logs\MyApp"
```

### 📝 配置类使用

```python
from pylogkit.config import LogConfig, get_default_log_dir

# 从环境变量创建配置
config = LogConfig.from_env(app_name="myapp")

# 手动创建配置
config = LogConfig(
    log_dir="/var/log/myapp",
    level="DEBUG",
    rotation="5 MB",
    retention="30 days",
    encoding="utf-8",
    app_name="myapp"
)

# 确保日志目录存在
config.ensure_log_dir()

# 转换为字典
config_dict = config.to_dict()
```

### 📊 审计日志配置

```python
from pylogkit.audit import init_audit_logger

# 初始化审计日志
init_audit_logger(
    log_dir="./logs/audit",
    level="INFO",
    rotation="10 MB",
    retention="90 days",
    encoding="utf-8"
)
```

## 🌟 关键特性

### 1️⃣ 跨平台日志目录

PyLogKit 自动根据操作系统选择适当的日志存储位置：

- 🪟 **Windows**: `%APPDATA%\{app_name}\logs`
- 🍎 **macOS**: `~/Library/Application Support/{app_name}/logs`
- 🐧 **Linux**: `~/.local/share/{app_name}/logs`

### 2️⃣ 日志轮转与压缩

- 🔄 支持按文件大小或时间自动轮转
- 🗜️ 旧日志自动压缩为 zip 格式
- 🧹 自动清理过期日志文件

### 3️⃣ 彩色控制台输出

控制台输出包含颜色编码，便于快速识别日志级别：

- ⚪ **DEBUG**: 灰色
- 🟢 **INFO**: 绿色
- 🟡 **WARNING**: 黄色
- 🔴 **ERROR**: 红色
- 🟣 **CRITICAL**: 红色背景

### 4️⃣ 线程安全

- 🔒 所有日志操作都是线程安全的
- ⚡ 支持异步写入，避免阻塞主线程
- 🚀 基于 loguru 的高性能实现

### 5️⃣ 完整的类型注解

所有公共 API 都包含完整的类型注解，支持 IDE 智能提示和类型检查：

```python
from pylogkit import get_logger

logger = get_logger()
# IDE 将提供完整的自动完成和类型检查
```

### 6️⃣ 异常追踪

自动捕获并记录完整的异常堆栈信息：

```python
from pylogkit import exception

try:
    risky_operation()
except Exception:
    exception("操作执行失败")
```

## 🛠️ 故障排除指南

### ❓ 常见问题

#### 问题一：日志文件未创建

**症状**: 运行程序后没有看到日志文件生成。

**排查步骤**:

1. 检查日志目录权限
   ```python
   from pylogkit import get_log_dir
   print(get_log_dir())
   ```

2. 确认 `file_output` 参数为 `True`
   ```python
   from pylogkit import get_config
   print(get_config())
   ```

3. 检查目录是否可写
   ```python
   import os
   log_dir = get_log_dir()
   print(os.access(log_dir, os.W_OK))
   ```

**解决方案**:

- 📁 手动创建日志目录并设置正确权限
- 📝 更换日志目录到可写位置
- 🔄 使用临时目录作为备选（库会自动处理）

#### 问题二：日志级别设置不生效

**症状**: 设置了 `DEBUG` 级别但仍看不到调试日志。

**排查步骤**:

1. 确认设置时机在日志记录之前
2. 检查环境变量是否覆盖配置
   ```bash
   echo $LOG_LEVEL  # Linux/macOS
   echo %LOG_LEVEL% # Windows CMD
   ```

**解决方案**:

```python
from pylogkit import init_logger, set_level

# 在应用启动时设置
init_logger(level="DEBUG")

# 或动态调整
set_level("DEBUG")
```

#### 问题三：PyQt 集成无响应

**症状**: 日志信号未触发 GUI 更新。

**排查步骤**:

1. 确认 PyQt 已安装
   ```python
   from pylogkit.qt_integration import has_pyqt
   print(has_pyqt())  # 应返回 True
   ```

2. 检查信号连接是否正确
3. 确认在主线程中创建 LogSignalEmitter

**解决方案**:

```python
from PyQt6.QtCore import QObject
from pylogkit.qt_integration import LogSignalEmitter

# 确保传入 parent 或正确初始化
emitter = LogSignalEmitter(parent=self)
```

#### 问题四：审计日志格式错误

**症状**: 审计日志文件内容不是有效的 JSON。

**排查步骤**:

1. 检查是否混用了普通日志和审计日志
2. 确认使用正确的审计日志函数

**解决方案**:

```python
# ✅ 正确：使用审计日志模块
from pylogkit.audit import info as audit_info
audit_info("user_action", user_id="123")

# ❌ 错误：不要使用普通日志记录审计信息
from pylogkit import info
info("user_action")  # 这会记录到普通日志
```

### ⚠️ 错误消息说明

| 错误消息 | 含义 | 解决方案 |
|----------|------|----------|
| `Logger initialization failed` | 日志初始化失败 | 检查目录权限和磁盘空间 |
| `Failed to set log level` | 设置日志级别失败 | 确认传入的级别字符串正确 |
| `PyQt 未安装` | PyQt 集成模块无法使用 | 安装 PyQt6: `pip install PyQt6` |

### 🐛 调试模式

启用详细调试信息：

```python
import os
os.environ["LOGURU_DEBUG"] = "1"

from pylogkit import init_logger
init_logger(level="DEBUG")
```

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/yourusername/pylogkit.git
cd pylogkit

# 安装依赖
uv sync

# 安装 pre-commit 钩子
uv run pre-commit install
```

### 代码规范

#### 🎨 格式化

使用 Black 进行代码格式化：

```bash
# 格式化所有文件
uv run black pylogkit/ tests/

# 检查格式
uv run black --check pylogkit/ tests/
```

#### 🔍 代码检查

使用 Ruff 进行代码检查：

```bash
# 运行检查
uv run ruff check pylogkit/ tests/

# 自动修复问题
uv run ruff check --fix pylogkit/ tests/
```

#### 📋 类型检查

使用 mypy 进行静态类型检查：

```bash
uv run mypy pylogkit/
```

### 🧪 测试

运行测试：

```bash
# 运行所有测试
uv run pytest

# 运行测试并生成覆盖率报告
uv run pytest --cov=pylogkit --cov-report=html
```

### 📂 项目结构

```
pylogkit/
├── pylogkit/              # 📦 日志库主目录
│   ├── __init__.py        # 🚪 主模块入口，导出公共 API
│   ├── core.py            # ❤️ 核心日志功能（基于 loguru）
│   ├── config.py          # ⚙️ 配置类和工具函数
│   ├── utils.py           # 🛠️ 实用工具（异常捕获装饰器等）
│   ├── audit.py           # 📊 审计日志子模块（JSON 结构化）
│   └── qt_integration.py  # 🎨 PyQt 集成支持（可选依赖）
├── tests/                 # 🧪 测试目录
├── main.py                # 💡 使用示例
├── pyproject.toml         # 📋 项目配置和依赖
├── README.md              # 📖 项目文档
├── CHANGELOG.md           # 📝 变更日志
└── LICENSE                # ⚖️ 许可证
```

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

## 🏷️ 版本记录

参见 [CHANGELOG.md](CHANGELOG.md) 了解详细版本历史。

---

**注意**: 本文档适用于 PyLogKit 版本 1.0.0。如有疑问，请参考源码中的 docstring 获取最新信息。
