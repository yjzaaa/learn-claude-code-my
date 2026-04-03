## Why

当前项目中大量使用 TypedDict 定义数据类型（如 ToolSpec、ConfigDict、EventDict 等），这带来了以下问题：
1. **缺乏运行时验证**：TypedDict 仅在类型检查阶段有效，运行时不验证数据格式
2. **无自动补全和 IDE 支持**：不如 Pydantic BaseModel 提供完整的智能提示
3. **难以扩展**：添加新方法或属性需要额外的封装
4. **序列化/反序列化繁琐**：需要手动处理，容易出错

通过将所有 TypedDict 转换为 Pydantic BaseModel（或与 LangChain 集成的自定义类），可以获得运行时验证、自动序列化、更好的 IDE 支持，同时保持类型安全。

## What Changes

- **工具类型**：`ToolSpec`, `OpenAIFunctionSchema`, `OpenAIToolSchema`, `MergedToolItem`, `JSONSchema` 等转换为 Pydantic BaseModel
- **配置类型**：`ConfigDict` 转换为 `ConfigModel` Pydantic 类
- **事件类型**：`EventDict`, `SkillEditEventDict`, `TodoEventDict` 等转换为 Pydantic BaseModel
- **响应类型**：`ResultDict`, `HITLResultDict` 转换为 Pydantic BaseModel
- **统计类型**：`MemoryStatsDict`, `SkillStatsDict`, `EventBusStatsDict`, `TodoItemDict` 转换为 Pydantic BaseModel
- **WebSocket 事件类型**：`WSDialogSnapshot`, `WSSnapshotEvent`, `WSErrorEvent` 等转换为 Pydantic BaseModel
- **API 响应类型**：所有 `API*Response` TypedDict 转换为 Pydantic BaseModel
- **BREAKING**: 所有使用 TypedDict 的地方需要更新为使用 Pydantic Model 实例
- **BREAKING**: JSON 序列化方式从 `dict()` 变为 `model.model_dump()`

## Capabilities

### New Capabilities
- `pydantic-tool-models`: 工具相关的 Pydantic 模型（ToolSpec, JSONSchema 等）
- `pydantic-config-models`: 配置相关的 Pydantic 模型
- `pydantic-event-models`: 事件相关的 Pydantic 模型
- `pydantic-response-models`: API 响应相关的 Pydantic 模型
- `pydantic-websocket-models`: WebSocket 事件相关的 Pydantic 模型
- `pydantic-serialization`: 统一的 Pydantic 序列化/反序列化层

### Modified Capabilities
- 所有使用 TypedDict 的模块需要迁移到 Pydantic Model

## Impact

- **后端**: `core/models/types.py` 全面重写，所有 TypedDict 转换为 Pydantic BaseModel
- **所有使用类型的模块**: HTTP 路由、WebSocket 处理器、Manager 类等
- **API**: 外部 API 保持不变，内部数据模型全部更新
- **序列化**: 统一使用 Pydantic 的 `model_dump()` 和 `model_validate()`
