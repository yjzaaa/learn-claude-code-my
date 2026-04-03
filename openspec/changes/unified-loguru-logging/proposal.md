## Why

当前项目中的日志使用存在不一致的问题：

1. **混合使用**: 部分模块使用标准库 `logging`，部分使用 `loguru`
2. **配置分散**: 每个模块独立配置 logger，缺乏统一管理
3. **输出格式不一致**: 不同模块的日志格式不同，影响可读性
4. **缺少高级特性**: 标准库 logging 不支持如日志文件轮转、结构化日志等功能

`loguru` 已存在于 requirements.txt，其优势包括：
- **简洁的 API**: 无需复杂的 logger 配置
- **自动线程安全**: 无需手动处理锁
- **内置文件轮转**: 支持按大小、时间自动轮转
- **结构化日志**: 支持 JSON 格式输出
- **更好的异常追踪**: 自动捕获和格式化异常堆栈

## What Changes

### 统一日志配置

1. **创建 `core/logging_config.py`** - 统一日志配置中心
   - 配置控制台和文件输出
   - 支持环境变量配置日志级别
   - 配置日志文件轮转

2. **更新所有模块** - 替换为 loguru
   - 移除标准库 logging 导入
   - 使用 `from loguru import logger`

3. **更新 `main.py`** - 初始化统一日志配置

### 日志规范

- **日志级别**: DEBUG, INFO, WARNING, ERROR
- **输出格式**: `[时间] [级别] [模块名] 消息`
- **文件输出**: 按天轮转，保留 7 天
- **控制台输出**: 开发环境彩色输出

## Capabilities

### New Capabilities

- 统一的日志格式和输出
- 日志文件自动轮转
- 环境变量配置日志级别 (`LOG_LEVEL`)
- 更清晰的异常堆栈追踪

### Modified Capabilities

- 所有模块的日志导入方式
- main.py 的日志初始化逻辑

## Impact

- **代码影响**: 更新所有使用 logging 的文件
- **配置影响**: 新增 `LOG_LEVEL` 环境变量支持
- **API 影响**: 无
- **测试影响**: 无

## Dependencies

- `loguru` 已在 requirements.txt
