# 实施任务：统一 Loguru 日志系统

## 功能要求

### FR1: 统一日志配置中心

- 必须创建 `runtime/logging_config.py` 作为统一配置入口（运行时基础设施）
- 必须支持控制台和文件双输出
- 必须支持环境变量配置日志级别
- 必须实现日志文件自动轮转

### FR2: 标准库日志桥接

- 必须拦截第三方库的 logging 输出到 loguru
- 必须保留原有的日志级别映射
- 必须正确传递异常堆栈信息

### FR3: 核心模块迁移

- 必须更新所有核心模块使用 loguru
- 必须保持日志调用方式向后兼容
- 必须验证日志输出功能正常

### FR4: FastAPI/Uvicorn 集成

- 必须将 FastAPI/Uvicorn 日志集成到统一系统
- 必须保持 HTTP 访问日志正常输出

## 验收标准

- [x] `runtime/logging_config.py` 存在且功能完整
- [x] 运行应用时日志格式统一
- [x] 日志文件按配置轮转
- [x] `LOG_LEVEL` 环境变量生效
- [x] 所有测试通过

## 任务清单

### Phase 1: 创建日志配置模块

- [x] 1.1 创建 `runtime/logging_config.py` 基础结构
  - 导入 loguru
  - 移除默认处理器
  - 定义日志格式常量

- [x] 1.2 实现 `setup_logging()` 函数
  - 控制台输出配置
  - 文件输出配置
  - 环境变量读取

- [x] 1.3 实现标准库日志拦截器
  - 创建 `InterceptHandler` 类
  - 配置根 logger 使用拦截器

- [x] 1.4 更新 `.env.example` 添加日志配置变量

### Phase 2: 更新入口点

- [x] 2.1 更新 `main.py` 导入日志配置
  - 在 lifespan 中初始化日志
  - 配置 uvicorn 日志拦截

- [x] 2.2 验证日志初始化正常
  - 启动应用测试
  - 检查日志输出

### Phase 3: 更新核心模块

- [x] 3.1 更新 `core/agent/runtimes/simple_runtime.py`
  - 替换 `import logging` 为 `from loguru import logger`
  - 移除 `logger = logging.getLogger(...)`
  - 更新日志调用格式

- [x] 3.2 更新 `core/agent/runtimes/deep_runtime.py`
  - 同上

- [x] 3.3 更新 `core/agent/factory.py`
  - 同上

- [x] 3.4 更新 `core/managers/dialog_manager.py`
  - 同上

- [x] 3.5 更新 `core/managers/skill_manager.py`
  - 同上

- [x] 3.6 更新 `core/managers/tool_manager.py`
  - 同上

- [x] 3.7 更新 `core/managers/memory_manager.py`
  - 同上

- [x] 3.8 更新 `core/managers/provider_manager.py`
  - 同上

- [x] 3.9 更新 `core/managers/state_manager.py`
  - 同上

- [x] 3.10 更新 `interfaces/agent_runtime_bridge.py`
  - 同上

- [x] 3.11 更新 `interfaces/websocket/manager.py`
  - 同上

- [x] 3.12 更新 `runtime/event_bus.py`
  - 同上

### Phase 4: 验证和测试

- [x] 4.1 运行测试套件
  - `python -m pytest tests/test_agent_runtime.py -v`

- [x] 4.2 手动验证日志输出
  - 启动应用
  - 检查控制台输出格式
  - 检查日志文件生成

- [x] 4.3 测试日志轮转
  - 配置小文件大小轮转
  - 验证轮转功能

- [x] 4.4 测试环境变量配置
  - 设置 `LOG_LEVEL=DEBUG`
  - 验证 DEBUG 日志输出

### Phase 5: 更新文档

- [x] 5.1 更新 `CLAUDE.md` 日志配置说明
- [x] 5.2 更新 `.env.example` 日志配置示例

## 实施顺序

```
1.1 → 1.2 → 1.3 → 1.4 → 2.1 → 2.2 → 3.1~3.12 → 4.1~4.4 → 5.1~5.2
```

## 注意事项

1. **日志格式**: 使用 `{}` 占位符而非 `%s`
   - 旧: `logger.debug("Value: %s", value)`
   - 新: `logger.debug("Value: {}", value)`

2. **异常日志**: `logger.exception()` 自动包含堆栈
   - 无需手动传递 `exc_info`

3. **延迟计算**: 使用 `logger.opt(lazy=True)` 避免昂贵计算
   - `logger.opt(lazy=True).debug("Data: {}", lambda: expensive())`

4. **上下文**: 可使用 `logger.bind()` 添加上下文
   - `logger.bind(request_id="123").info("Request processed")`
