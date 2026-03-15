# Pydantic 数据模型迁移说明

## 概述

已将项目中的所有数据模型从 `dataclasses` 迁移到 `Pydantic BaseModel`，提供自动验证、序列化和类型安全。

## 主要变更

### 1. 依赖更新

```txt
# requirements.txt
pydantic>=2.0.0
pydantic-settings>=2.0.0
```

### 2. 数据模型迁移

#### `agents/models/dialog_types.py`

**转换为 Pydantic BaseModel:**
- `ToolCall` - 工具调用模型
- `Message` - 消息模型
- `DialogMetadata` - 对话框元数据
- `DialogSession` - 对话框会话模型
- `DialogSummary` - 对话框摘要

**新增 API 请求/响应模型:**
- `CreateDialogRequest` - 创建对话框请求
- `CreateDialogResponse` - 创建对话框响应
- `SendMessageRequest` - 发送消息请求
- `SendMessageResponse` - 发送消息响应
- `DialogListResponse` - 对话框列表响应
- `DialogDetailResponse` - 对话框详情响应
- `ErrorResponse` - 错误响应

#### `agents/models/openai_types.py`

**转换为 Pydantic BaseModel:**
- `ChatMessage` - 聊天消息
- `ChatCompletionMessageToolCall` - 工具调用
- `ChatCompletionTool` - 工具定义
- `ChatCompletionChunk` - 流式响应块
- `ChatSession` - 聊天会话
- `ChatEvent` - WebSocket 事件

**新增 API 模型:**
- `ChatCompletionRequest` - 聊天完成请求
- `ChatCompletionResponse` - 聊天完成响应

### 3. API 端点更新

`agents/api/main_new.py` 中的端点已更新使用 Pydantic 模型:

| 端点 | 请求模型 | 响应模型 |
|------|----------|----------|
| `GET /api/dialogs` | - | `DialogListResponse` |
| `POST /api/dialogs` | `CreateDialogRequest` | `CreateDialogResponse` |
| `GET /api/dialogs/{id}` | - | `DialogDetailResponse` |
| `POST /api/dialogs/{id}/messages` | `SendMessageRequest` | `SendMessageResponse` |
| `POST /api/dialogs/{id}/stop` | - | `DialogDetailResponse` |
| `POST /api/dialogs/{id}/resume` | - | `SendMessageResponse` |
| `DELETE /api/dialogs/{id}` | - | `ErrorResponse` |

## Pydantic 特性使用

### 1. 自动验证

```python
from agents.models.dialog_types import Message, Role

# 自动验证 role 必须是 Role 枚举值
msg = Message(
    id="123",
    role=Role.USER,  # 类型安全
    content="Hello"
)

# 错误的类型会在创建时抛出 ValidationError
# msg = Message(id="123", role="invalid", content="Hello")  # 报错
```

### 2. 自动序列化

```python
# 类 → 字典
session_dict = session.model_dump()

# 类 → JSON
session_json = session.model_dump_json()

# 字典 → 类
session = DialogSession(**data)
```

### 3. 字段默认值

```python
from pydantic import Field

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: MessageStatus = MessageStatus.COMPLETED
```

### 4. 配置选项

```python
class ToolCall(BaseModel):
    model_config = ConfigDict(use_enum_values=True)  # 枚举使用值而不是名称
```

### 5. 方法链式调用

```python
session = DialogSession.create_new("123", "测试")
    .add_message(Message.create_user("Hello"))
    .set_status(DialogStatus.THINKING)
```

## 工厂方法

### Message 工厂方法

```python
# 创建用户消息
msg = Message.create_user("Hello")

# 创建助手消息
msg = Message.create_assistant("Hi there")

# 创建工具消息
msg = Message.create_tool(
    content="结果",
    tool_call_id="call_123",
    tool_name="bash"
)

# 创建系统消息
msg = Message.create_system("You are a helpful assistant")
```

### DialogSession 工厂方法

```python
session = DialogSession.create_new(
    dialog_id="uuid",
    title="新对话",
    agent_name="SFullAgent"
)
```

## 与 FastAPI 集成

Pydantic 模型与 FastAPI 原生集成:

```python
from fastapi import FastAPI
from agents.models.dialog_types import CreateDialogRequest, CreateDialogResponse

app = FastAPI()

@app.post("/api/dialogs", response_model=CreateDialogResponse)
async def create_dialog(request: CreateDialogRequest):
    # 自动验证请求数据
    # 自动序列化响应数据
    return CreateDialogResponse(
        success=True,
        data=session
    )
```

## 迁移好处

1. **类型安全** - 编译时类型检查，运行时自动验证
2. **自动文档** - FastAPI 自动生成 OpenAPI 文档
3. **IDE 支持** - 更好的代码补全和类型提示
4. **序列化简化** - `model_dump()` 替代手动 `to_dict()`
5. **配置管理** - 可使用 `pydantic-settings` 管理环境变量

## 向后兼容性

- 原有 `to_dict()` 方法已被 `model_dump()` 替代
- 原有 `from_dict()` 类方法仍可用 `**data` 解包替代
- 枚举类型保持不变，继续使用 `.value` 访问

## 后续建议

1. **配置管理** - 使用 `pydantic-settings` 管理应用配置
2. **环境变量** - 使用 `BaseSettings` 管理环境变量
3. **复杂验证** - 使用 `field_validator` 进行复杂字段验证
4. **嵌套模型** - 利用 Pydantic 的嵌套模型功能

## 示例

### 完整使用示例

```python
from agents.models.dialog_types import (
    DialogSession,
    Message,
    ToolCall,
    DialogStatus,
    Role
)

# 创建会话
session = DialogSession.create_new("123", "测试对话")

# 添加用户消息
session.add_message(Message.create_user("查询数据"))

# 添加助手消息（带工具调用）
tool_call = ToolCall(
    id="call_1",
    name="query_database",
    arguments={"sql": "SELECT * FROM users"}
)
session.add_message(
    Message.create_assistant("", tool_calls=[tool_call])
)

# 序列化
data = session.model_dump()
print(data)

# 反序列化
restored = DialogSession(**data)
```
