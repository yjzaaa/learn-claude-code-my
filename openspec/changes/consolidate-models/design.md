# Design: Model Consolidation and Refactoring

## Directory Structure

```
core/models/
├── __init__.py          # 统一导出
├── base.py              # 基类定义（Entity, Event, Response, Config）
├── mixins.py            # Mixin 类（时间戳、对话引用等）
├── entities.py          # 业务实体（Dialog, Message, ToolCall, Artifact, Skill）
├── events.py            # 所有事件类型
├── api.py               # API 请求/响应模型
├── config.py            # 所有配置类
└── types.py             # 类型别名和辅助函数
```

## Base Classes

### 1. Entity (业务实体基类)

```python
class Entity(BaseModel):
    '''业务实体基类'''
    id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def touch(self) -> None:
        '''更新时间戳'''
        self.updated_at = datetime.now()
```

### 2. Event (事件基类)

```python
class Event(BaseModel):
    '''事件基类'''
    type: str
    dialog_id: str
    timestamp: float = Field(default_factory=time.time)
    priority: EventPriority = EventPriority.NORMAL
```

### 3. Response (响应基类)

```python
class Response(BaseModel):
    '''API 响应基类'''
    success: bool
    message: str = ""
```

## Mixins

### TimestampMixin

```python
class TimestampMixin(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

### DialogRefMixin

```python
class DialogRefMixin(BaseModel):
    dialog_id: str
```

### MetadataMixin

```python
class MetadataMixin(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)
```

## Entity Refactoring

### Before

```python
# domain.py
class Artifact(BaseModel):
    id: str
    type: str
    name: str
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    dialog_id: Optional[str] = None

class Skill(BaseModel):
    id: str
    definition: SkillDefinition
    loaded_at: datetime = Field(default_factory=datetime.now)
    metadata: SkillMetadata = Field(default_factory=SkillMetadata)
```

### After

```python
# entities.py
class Artifact(Entity, DialogRefMixin):
    type: str
    name: str
    content: str
    language: Optional[str] = None

class Skill(Entity):
    definition: SkillDefinition
    metadata: dict[str, Any] = Field(default_factory=dict)
    scripts_loaded: bool = False
```

## Event Refactoring

### Before

分散在 `events.py` 和 `event_models.py` 中，重复定义 `dialog_id`, `timestamp`。

### After

```python
# events.py
class DialogCreated(Event):
    type: str = "dialog:created"
    title: str

class MessageReceived(Event):
    type: str = "message:received"
    content: str
    role: str

class StreamDelta(Event):
    type: str = "stream:delta"
    delta: str
```

## API Model Refactoring

### Before

```python
# response_models.py
class APISendMessageResponse(BaseModel):
    success: bool
    message: str
    dialog_id: str

class APIAgentStatusResponse(BaseModel):
    success: bool
    message: str
    status: str
```

### After

```python
# api.py
class SendMessageResponse(Response, DialogRefMixin):
    pass

class AgentStatusResponse(Response):
    status: str
```

## Migration Strategy

1. **Phase 1**: 创建新基类和 mixin
2. **Phase 2**: 重构 entities.py
3. **Phase 3**: 重构 events.py
4. **Phase 4**: 重构 api.py
5. **Phase 5**: 重构 config.py
6. **Phase 6**: 更新所有导入
7. **Phase 7**: 删除旧文件

## Backward Compatibility

- 保持 `__init__.py` 导出不变
- 使用 TypeAlias 向后兼容旧名称
- 废弃警告而非立即删除

## Code Reduction Estimate

| 文件 | 当前行数 | 预期行数 | 减少 |
|------|----------|----------|------|
| domain.py | 95 | 60 | 37% |
| dto.py | 327 | 220 | 33% |
| events.py | 80 | 55 | 31% |
| response_models.py | 120 | 80 | 33% |
| **总计** | **~620** | **~415** | **33%** |
