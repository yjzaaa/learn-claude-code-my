## Context

### 当前状态

**`core/models/types.py`**:
- 大量使用 TypedDict 定义类型（约 500 行）
- 包括：ToolSpec, ConfigDict, EventDict, ResultDict, WebSocket 事件类型等
- 运行时无验证，仅类型提示

**问题**:
- 数据验证依赖调用方，容易出错
- 序列化/反序列化需要手动处理
- 缺乏 IDE 的智能提示和补全
- 难以添加业务方法

### 目标架构

**Pydantic BaseModel 统一模型层**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Pydantic BaseModel 层                        │
├─────────────────────────────────────────────────────────────────┤
│  Tool Models         │  ToolSpec, JSONSchema, OpenAIToolSchema   │
│  Config Models       │  ConfigModel, StateConfig, etc.           │
│  Event Models        │  EventModel, SkillEditEvent, etc.         │
│  Response Models     │  ResultModel, APIResponse, etc.           │
│  WebSocket Models    │  WSSnapshotEvent, WSErrorEvent, etc.      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Pydantic 序列化/反序列化
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     使用层 (HTTP/WebSocket)                      │
│  - FastAPI 自动集成 Pydantic                                      │
│  - WebSocket 使用 model.model_dump()                             │
│  - 运行时自动验证                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Goals / Non-Goals

**Goals:**
- 所有 TypedDict 转换为 Pydantic BaseModel
- 运行时数据验证和类型检查
- 统一的序列化/反序列化接口
- 更好的 IDE 支持和开发者体验
- 与 FastAPI 原生集成

**Non-Goals:**
- 不改变外部 API 接口格式
- 不改变数据库存储格式
- 消息模型保持继承 LangChain（已在另一个变更中处理）

## Decisions

### 1. 所有非消息类型使用 Pydantic BaseModel

**决策**: Tool、Config、Event、Response 等非消息类型全部使用 Pydantic BaseModel。

**理由**:
- FastAPI 原生支持 Pydantic，自动文档生成
- 运行时验证，减少数据错误
- `model_dump()` / `model_validate()` 统一序列化
- 可添加业务方法到模型类

**实现方式**:
```python
from pydantic import BaseModel, Field
from typing import Optional

class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: JSONSchema

class JSONSchema(BaseModel):
    type: str = "object"
    properties: dict[str, JSONSchemaProperty]
    required: list[str] = Field(default_factory=list)
```

### 2. 保留 TypedDict 用于特定场景

**决策**: 仅在以下场景保留 TypedDict:
- 与外部库强制要求 TypedDict 的接口
- 性能敏感的内部数据结构（大量数据处理）
- 临时性的、无需验证的数据传递

**理由**:
- Pydantic 有轻微性能开销
- 某些底层库可能要求特定类型

### 3. 字段默认值和可选字段

**决策**: 使用 Pydantic 的 `Field(default=...)` 和 `Optional` 定义可选字段。

**实现**:
```python
class ResultModel(BaseModel):
    success: bool
    message: str
    data: Optional[dict[str, Any]] = Field(default=None)
```

### 4. 序列化策略

**决策**: 统一使用 Pydantic 的序列化方法。

| 场景 | 方法 |
|------|------|
| 转字典 | `model.model_dump()` |
| 转 JSON 字符串 | `model.model_dump_json()` |
| 从字典创建 | `Model.model_validate(data)` |
| 从 JSON 创建 | `Model.model_validate_json(json_str)` |

### 5. 与 LangChain 消息模型的集成

**决策**: Pydantic 模型与 LangChain 消息模型共存，通过适配器转换。

**理由**:
- LangChain 消息已在单独变更中处理
- WebSocket 事件可能需要同时包含 Pydantic 事件数据和 LangChain 消息数据

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| **性能开销** | Pydantic 验证有轻微性能影响；关键路径可使用 `__init__` 绕过验证 |
| **迁移复杂性** | 分阶段迁移，先核心类型后边缘类型；保留测试验证行为一致 |
| **循环导入** |  careful 设计模块结构，必要时使用 `TYPE_CHECKING` 或前向引用 |
| **向后兼容** | 保持 JSON 输出格式不变；添加兼容性测试 |

## Migration Plan

### 阶段 1: 核心工具类型 (优先级高)
1. 创建 `core/models/tool_models.py`: ToolSpec, JSONSchema 等
2. 更新 `core/models/__init__.py` 导出
3. 更新使用这些类型的模块

### 阶段 2: 配置类型 (优先级高)
1. 将 `core/models/config.py` 从 dataclass 转为 Pydantic
2. 更新配置管理器

### 阶段 3: 事件和响应类型 (优先级高)
1. 创建 `core/models/event_models.py`
2. 创建 `core/models/response_models.py`
3. 更新 HTTP 路由和 WebSocket 处理器

### 阶段 4: WebSocket 事件类型 (优先级中)
1. 创建 `core/models/websocket_models.py`
2. 更新 WebSocket 广播器

### 阶段 5: 统计和辅助类型 (优先级中)
1. 迁移 MemoryStats, SkillStats 等
2. 更新统计收集代码

### 阶段 6: 清理和测试 (优先级中)
1. 删除所有未使用的 TypedDict
2. 编写 Pydantic 模型单元测试
3. 验证序列化/反序列化一致性

## Open Questions

1. **Pydantic V1 vs V2**: 项目当前使用哪个版本？是否需要升级？
2. **嵌套模型深度**: JSONSchema 的嵌套结构如何处理？
3. **额外字段策略**: 是否允许额外字段（`extra='allow'`）？
4. **别名策略**: 是否需要字段别名（如 snake_case 转 camelCase）？
