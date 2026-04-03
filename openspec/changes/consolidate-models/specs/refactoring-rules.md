# Spec: Model Refactoring Rules

## 继承规则

### 1. 所有业务实体必须继承 Entity

```python
# ✅ 正确
class Dialog(Entity):
    title: str

# ❌ 错误
class Dialog(BaseModel):
    id: str
    created_at: datetime
    title: str
```

### 2. 所有事件必须继承 Event

```python
# ✅ 正确
class MessageReceived(Event):
    content: str

# ❌ 错误
class MessageReceived(BaseModel):
    type: str
    dialog_id: str
    timestamp: float
    content: str
```

### 3. 所有响应必须继承 Response

```python
# ✅ 正确
class SendMessageResponse(Response):
    pass

# ❌ 错误
class SendMessageResponse(BaseModel):
    success: bool
    message: str
```

## Mixin 使用规则

### 何时使用 Mixin

| 场景 | Mixin |
|------|-------|
| 需要 created_at/updated_at | TimestampMixin |
| 需要 dialog_id | DialogRefMixin |
| 需要 metadata 字段 | MetadataMixin |

### 多继承顺序

```python
# ✅ 正确 - Mixin 在前，基类在后
class Message(Entity, DialogRefMixin, TimestampMixin):
    content: str

# ❌ 错误 - 基类应该在最右
```

## 字段命名规范

### 时间戳

- `created_at` - 创建时间
- `updated_at` - 更新时间
- `timestamp` - 事件时间戳（float，unix 时间）

### ID

- `id` - 实体 ID
- `dialog_id` - 对话引用
- `message_id` - 消息引用
- `tool_call_id` - 工具调用引用

## 向后兼容

### 类型别名

```python
# api.py
# 旧名称别名
APISendMessageResponse = SendMessageResponse
APIAgentStatusResponse = AgentStatusResponse
```

### 废弃警告

```python
import warnings

def __getattr__(name: str):
    if name == "OldModelName":
        warnings.warn("OldModelName is deprecated, use NewModelName", DeprecationWarning)
        return NewModelName
    raise AttributeError(f"module has no attribute {name}")
```

## 代码审查清单

- [ ] 新模型继承正确基类
- [ ] 使用 Mixin 而非重复字段
- [ ] 字段类型使用 Pydantic 类型
- [ ] 默认值为不可变类型（使用 Field(default_factory=...)）
- [ ] 敏感字段标记 exclude=True
- [ ] 向后兼容别名已添加
