# PyLogKit

基于 [loguru](https://github.com/Delgan/loguru) 的开箱即用日志封装。

目标很直接：

- 程序入口只初始化一次
- 业务代码里统一用 `log` 和 `audit`
- 自带默认文件日志、控制台日志、日志轮转
- 默认接管标准库 `logging`
- 需要 GUI 时再显式 `attach_qt()`

## 安装

```bash
pip install pylogkit
```

如果需要 PyQt 集成：

```bash
pip install pylogkit[pyqt]
```

## 快速开始

```python
from pylogkit import init_logging, log, audit

init_logging("myapp")

log.info("Application started")
log.bind(user_id="42").warning("User quota is low")

audit.info("user_login", user_id="42", ip="127.0.0.1")
```

默认行为：

- 普通日志输出到控制台和 `<默认日志目录>/myapp_YYYY-MM-DD.log`
- 审计日志输出到 `<默认日志目录>/audit/audit_YYYY-MM-DD.jsonl`
- 标准库 `logging` 默认自动接入同一套日志 sink
- 未调用 `init_logging()` 前直接使用会抛 `LoggingNotInitializedError`

## 主 API

```python
from pylogkit import (
    LogConfig,
    LoggingNotInitializedError,
    attach_qt,
    audit,
    catch_exceptions,
    init_logging,
    log,
    shutdown_logging,
)
```

### `init_logging()`

```python
init_logging(
    "myapp",
    level="DEBUG",
    log_dir="./logs",
    rotation="20 MB",
    retention="14 days",
    encoding="utf-8",
    console_output=True,
    file_output=True,
    capture_stdlib=True,
    audit_enabled=True,
)
```

### `log`

```python
from pylogkit import log

log.debug("debug message")
log.info("hello {}", "world")
log.success("done")
log.warning("warning")
log.error("error")
log.critical("critical")

log.bind(request_id="req-1").info("with context")
log.opt(exception=True).error("captured exception")
```

### `audit`

```python
from pylogkit import audit

audit.info("user_login", user_id="42", ip="127.0.0.1")
audit.success("file_uploaded", filename="report.pdf", size=1024)
audit.warning("login_failed", user_id="42", reason="bad_password")
audit.error("payment_failed", order_id="ORD-1", reason="declined")
```

审计日志每行都是一个 JSON 对象：

```json
{
  "timestamp": "2026-03-15T10:00:00.000000",
  "level": 20,
  "level_name": "INFO",
  "action": "user_login",
  "data": {
    "action": "user_login",
    "user_id": "42",
    "ip": "127.0.0.1"
  }
}
```

### `catch_exceptions()`

```python
from pylogkit import catch_exceptions

@catch_exceptions(reraise=False)
def do_work():
    raise ValueError("boom")
```

默认会通过当前 `log` 记录异常和 traceback。

### `attach_qt()`

```python
from pylogkit import attach_qt, init_logging, log

init_logging("myapp")
handler = attach_qt()

log.info("This message will also be forwarded to Qt")
```

`attach_qt()` 只在已经初始化并且安装了 PyQt 时可用；否则会抛出明确异常。

## 标准库 `logging` 接管

初始化后，标准库 `logging` 默认会进入同一套主日志：

```python
import logging

from pylogkit import init_logging

init_logging("myapp")

logging.getLogger(__name__).warning("stdlib warning")
```

如果不想接管，初始化时关闭：

```python
init_logging("myapp", capture_stdlib=False)
```

## 环境变量

`init_logging()` 会读取环境变量，显式传入的参数优先。

| 环境变量 | 说明 | 默认值 |
| --- | --- | --- |
| `LOG_LEVEL` | 普通日志和审计日志级别 | `INFO` |
| `LOG_DIR` | 日志根目录 | 平台默认目录 |
| `LOG_ROTATION` | 轮转策略 | `10 MB` |
| `LOG_RETENTION` | 保留策略 | `7 days` |
| `LOG_ENCODING` | 文件编码 | `utf-8` |
| `LOG_APP_NAME` | 应用名 | `app` |
| `LOG_CAPTURE_STDLIB` | 是否接管标准库 `logging` | `true` |
| `LOG_AUDIT_ENABLED` | 是否启用审计日志 | `true` |

示例：

```bash
export LOG_LEVEL=DEBUG
export LOG_DIR=./logs
export LOG_CAPTURE_STDLIB=false
```

Windows PowerShell：

```powershell
$env:LOG_LEVEL = "DEBUG"
$env:LOG_DIR = "C:\Logs\MyApp"
$env:LOG_AUDIT_ENABLED = "false"
```

## 高级用法

`LogConfig` 适合在需要先解析配置、再延后初始化时使用：

```python
from pylogkit import LogConfig

config = LogConfig.from_env(app_name="myapp")
print(config.to_dict())
```

如果程序退出或测试结束需要清理运行时状态：

```python
from pylogkit import shutdown_logging

shutdown_logging()
```

## 说明

- 这是显式初始化模型，不会自动懒初始化。
- 日志消息格式使用 `loguru` 风格占位符：`{}`，不要使用 `%s`。
- 普通日志和审计日志是隔离的，不会互相混入。
