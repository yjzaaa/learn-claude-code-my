# 设计文档：统一 Loguru 日志系统

## Context

当前项目使用两种日志方式：
1. 标准库 `logging` - 约 30+ 处使用
2. `loguru` - 已在 requirements.txt 中声明，但使用较少

问题：
- 配置分散，每个模块独立创建 logger
- 输出格式不一致
- 缺少日志文件轮转等高级功能

## Goals

1. **完全统一**: 所有模块使用 loguru
2. **集中配置**: 单一配置文件管理日志行为
3. **生产就绪**: 支持文件轮转、级别控制、结构化输出
4. **向后兼容**: 不改变日志调用方式

## Non-Goals

- 不修改日志的业务逻辑
- 不添加新的日志点（只替换现有日志）
- 不改变日志文件位置（除非配置指定）

## Design Decisions

### 1. 配置中心设计

```python
# runtime/logging_config.py
"""统一日志配置 - 运行时基础设施"""

import sys
import os
from pathlib import Path
from loguru import logger

# 移除默认的 stderr 处理器
logger.remove()

# 日志格式
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"

# 日志级别映射
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
LOG_ROTATION = os.getenv("LOG_ROTATION", "10 MB")  # 或 "1 day"
LOG_RETENTION = os.getenv("LOG_RETENTION", "7 days")


def setup_logging():
    """配置统一日志系统"""

    # 控制台输出 (开发环境彩色)
    logger.add(
        sys.stderr,
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        colorize=True,
        enqueue=True,  # 线程安全
    )

    # 文件输出 (生产环境)
    log_path = Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(log_path),
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        encoding="utf-8",
        enqueue=True,
        backtrace=True,   # 异常追踪
        diagnose=True,    # 诊断信息
    )

    # 可选: JSON 格式输出 (用于日志收集)
    if os.getenv("LOG_JSON", "false").lower() == "true":
        logger.add(
            str(log_path).replace(".log", ".json.log"),
            level=LOG_LEVEL,
            serialize=True,  # JSON 格式
            rotation=LOG_ROTATION,
            retention=LOG_RETENTION,
            encoding="utf-8",
        )

    logger.info(f"Logging configured: level={LOG_LEVEL}, file={LOG_FILE}")


# 导出配置好的 logger
__all__ = ["logger", "setup_logging"]
```

### 2. 模块迁移策略

#### 迁移前 (标准库 logging)

```python
import logging

logger = logging.getLogger(__name__)

class MyClass:
    def do_something(self):
        logger.info("Doing something")
        logger.debug("Debug info: %s", data)
        try:
            risky_operation()
        except Exception as e:
            logger.exception("Operation failed")
```

#### 迁移后 (loguru)

```python
from loguru import logger

class MyClass:
    def do_something(self):
        logger.info("Doing something")
        logger.debug("Debug info: {}", data)  # 使用 {} 占位符
        try:
            risky_operation()
        except Exception:
            logger.exception("Operation failed")  # 自动包含堆栈
```

### 3. 文件分类

根据 grep 结果，需要更新的文件：

**核心文件 (必须更新)**:
- `main.py`
- `core/agent/runtimes/simple_runtime.py`
- `core/agent/runtimes/deep_runtime.py`
- `core/agent/factory.py`
- `core/managers/*.py`
- `interfaces/agent_runtime_bridge.py`
- `interfaces/websocket/manager.py`
- `runtime/event_bus.py`

**可选文件 (参考文件，低优先级)**:
- `study/*.py` - 学习笔记
- `skills/*/references/*.py` - 参考代码

### 4. 环境变量配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LOG_LEVEL` | INFO | 日志级别 (DEBUG/INFO/WARNING/ERROR) |
| `LOG_FILE` | logs/app.log | 日志文件路径 |
| `LOG_ROTATION` | 10 MB | 轮转条件 (10 MB / 1 day / 1 week) |
| `LOG_RETENTION` | 7 days | 保留时间 |
| `LOG_JSON` | false | 是否输出 JSON 格式 |

### 5. 特殊处理

#### 第三方库日志

某些第三方库使用标准库 logging，需要桥接到 loguru：

```python
# runtime/logging_config.py

def intercept_standard_logging():
    """拦截标准库日志到 loguru"""
    import logging

    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # 获取对应的 loguru 级别
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # 找到调用者
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    # 配置根 logger 使用拦截处理器
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
```

#### FastAPI/Uvicorn 日志

```python
# main.py

@app.on_event("startup")
async def setup_logging():
    from runtime.logging_config import setup_logging as _setup
    _setup()

    # 配置 uvicorn 使用 loguru
    import logging
    for _log in ["uvicorn", "uvicorn.access", "fastapi"]:
        _logger = logging.getLogger(_log)
        _logger.handlers = [InterceptHandler()]
```

## Migration Plan

### Phase 1: 创建日志配置模块
1. 创建 `runtime/logging_config.py`
2. 实现 `setup_logging()` 函数
3. 实现标准库日志拦截

### Phase 2: 更新入口点
1. 更新 `main.py` 初始化日志配置
2. 验证日志输出正常

### Phase 3: 更新核心模块
按优先级更新：
1. `core/agent/runtimes/*.py`
2. `core/managers/*.py`
3. `interfaces/*.py`
4. `runtime/*.py`

### Phase 4: 验证和测试
1. 运行测试套件
2. 验证日志输出格式
3. 验证日志文件轮转

## File Changes Summary

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `runtime/logging_config.py` | 新增 | 统一日志配置（运行时基础设施） |
| `main.py` | 修改 | 初始化日志配置 |
| `core/agent/runtimes/*.py` | 修改 | 替换 logger |
| `core/managers/*.py` | 修改 | 替换 logger |
| `core/agent/factory.py` | 修改 | 替换 logger |
| `interfaces/*.py` | 修改 | 替换 logger |
| `runtime/event_bus.py` | 修改 | 替换 logger |

## Risks

| Risk | Mitigation |
|------|------------|
| 日志格式变更影响日志解析 | 保留旧格式选项，逐步过渡 |
| 性能下降 | loguru 性能优于标准库，且支持异步 |
| 第三方库日志丢失 | 使用 InterceptHandler 桥接 |
| 配置错误导致无日志 | 添加配置验证和默认值 |
