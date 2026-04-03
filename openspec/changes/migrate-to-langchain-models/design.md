## Context

### 当前状态

**后端 (`core/models/`)**:
- `types.py`: 大量使用 TypedDict 定义消息、事件、API 响应类型（约 500 行）
- `dialog.py`: 使用 dataclass + dataclass_json 定义 Message、Dialog、ToolCall
- 问题：混合使用多种类型系统，序列化格式不统一，存在裸 dict 传参

**前端 (`web/src/types/`)**:
- `sync.ts`: 自定义 WebSocket 消息类型（约 330 行）
- `dialog.ts`, `agent-event.ts`: 自定义 interface
- 问题：缺乏运行时验证，与后端模型难以对齐

### 目标架构

**继承式设计** - 自定义模型继承 LangChain 基础模型：

```
┌─────────────────────────────────────────────────────────────────────┐
│                         后端 (FastAPI)                              │
│                                                                     │
│   LangChain Base                                                    │
│   ┌──────────────┐                                                  │
│   │ BaseMessage  │◄──────────┬──────────┬──────────┐                │
│   └──────────────┘           │          │          │                │
│                              │继承       │继承      │继承             │
│                         ┌────┴───┐ ┌────┴───┐ ┌────┴───┐           │
│                         │Custom  │ │Custom  │ │Custom  │           │
│                         │Human   │ │AI      │ │Tool    │           │
│                         │Message │ │Message │ │Message │           │
│                         └───┬────┘ └────┬───┘ └───┬────┘           │
│                             │           │         │                │
│   业务字段: id,              │metadata   │tool_call_id              │
│            created_at       │agent_name │tool_name                 │
│                             │status     │duration_ms               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ WebSocket (LangChain 序列化 + 业务字段)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         前端 (Next.js)                              │
│                                                                     │
│   @langchain/core                                                   │
│   ┌──────────────┐                                                  │
│   │ BaseMessage  │◄──────────┬──────────┬──────────┐                │
│   └──────────────┘           │          │          │                │
│                         ┌────┴───┐ ┌────┴───┐ ┌────┴───┐           │
│                         │Custom  │ │Custom  │ │Custom  │           │
│                         │Human   │ │AI      │ │Tool    │           │
│                         │Message │ │Message │ │Message │           │
│                         └────────┘ └────────┘ └────────┘           │
│                                                                     │
│   业务字段通过 additional_kwargs 或自定义子类扩展                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Goals / Non-Goals

**Goals:**
- **自定义消息模型继承 LangChain BaseMessage**：`CustomHumanMessage`, `CustomAIMessage`, `CustomToolMessage` 等继承自对应的 LangChain 类
- **业务字段通过扩展机制添加**：id, created_at, metadata 等字段通过 `additional_kwargs` 或子类属性添加
- **保留 LangChain 标准序列化**：使用 `message_to_dict()` / `messages_from_dict()` 进行序列化
- **消除裸 JSON/dict**：所有消息必须是 BaseMessage 子类实例
- **前后端消息格式 100% 兼容**：基于 LangChain 标准格式 + 业务字段扩展

**Non-Goals:**
- 不替换 Pydantic 在非消息类中的使用（如配置类）
- 不改变 LLM Provider 调用方式
- 不修改业务逻辑语义，仅改变数据模型实现方式

## Decisions

### 1. 自定义模型继承 LangChain 基础类

**决策**: 创建自定义消息类继承 LangChain 的 `HumanMessage`, `AIMessage`, `ToolMessage`。

**理由**:
- 保留 LangChain 生态的全部能力（序列化、工具方法等）
- 可以通过 `additional_kwargs` 添加业务特定字段
- 支持运行时类型检查（`isinstance(msg, CustomAIMessage)`）
- 未来升级 LangChain 版本时兼容性更好

**实现方式**:
```python
from langchain_core.messages import HumanMessage

class CustomHumanMessage(HumanMessage):
    """自定义用户消息 - 继承 LangChain HumanMessage"""

    def __init__(self, content: str, msg_id: Optional[str] = None, **kwargs):
        super().__init__(content=content, **kwargs)
        # 业务字段存入 additional_kwargs
        self.additional_kwargs["id"] = msg_id or f"msg_{uuid.uuid4().hex[:12]}"
        self.additional_kwargs["created_at"] = datetime.now().isoformat()

    @property
    def msg_id(self) -> str:
        return self.additional_kwargs.get("id", "")

    @property
    def created_at(self) -> str:
        return self.additional_kwargs.get("created_at", "")
```

**替代方案考虑**:
- 直接使用 LangChain 原生类：无法满足业务字段需求（id, created_at）
- 仅使用 TypedDict：失去 LangChain 的能力和类型安全
- 组合模式（包含 BaseMessage）：增加复杂性，序列化困难

### 2. 前端同样采用继承模式

**决策**: 前端创建自定义消息类继承 `@langchain/core` 的对应类。

**理由**:
- 与后端实现对称
- 支持 `instanceof` 类型检查
- 可以扩展业务方法

**实现方式**:
```typescript
import { HumanMessage } from "@langchain/core/messages";

export class CustomHumanMessage extends HumanMessage {
  constructor(content: string, options?: { msgId?: string; createdAt?: string }) {
    super({ content });
    this.additional_kwargs = {
      id: options?.msgId || generateId(),
      created_at: options?.createdAt || new Date().toISOString(),
    };
  }

  get msgId(): string {
    return this.additional_kwargs.id;
  }

  get createdAt(): string {
    return this.additional_kwargs.created_at;
  }
}
```

### 3. 序列化策略：LangChain 标准 + 业务字段

**决策**: 使用 `message_to_dict()` 序列化，业务字段自动包含在 `data.additional_kwargs` 中。

**序列化示例**:
```json
{
  "type": "human",
  "data": {
    "content": "Hello",
    "additional_kwargs": {
      "id": "msg_abc123",
      "created_at": "2024-01-15T10:30:00",
      "metadata": { "source": "web" }
    }
  }
}
```

**理由**:
- 无需自定义序列化逻辑
- LangChain 自动处理 `additional_kwargs`
- 前端/后端格式完全一致

### 4. Dialog 类使用自定义消息类型

**决策**: `Dialog` 类存储 `BaseMessage` 列表，实际使用自定义子类。

**实现**:
```python
from langchain_core.messages import BaseMessage

class Dialog:
    def __init__(self):
        self.messages: List[BaseMessage] = []

    def add_human_message(self, content: str) -> CustomHumanMessage:
        msg = CustomHumanMessage(content=content)
        self.messages.append(msg)
        return msg
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| **LangChain 版本升级风险** | 自定义类通过继承获得向前兼容，关键方法可重写适配 |
| **additional_kwargs 命名冲突** | 业务字段统一使用 `lc_` 前缀或嵌套在 `metadata` 中 |
| **TypeScript 类继承复杂性** | 使用工厂函数创建消息，隐藏继承细节 |
| **调试难度增加** | 为自定义类添加 `__repr__` / `toString()` 方法 |

## Migration Plan

### 阶段 1: 后端自定义消息类 (优先级高)
1. 创建 `core/models/messages.py`：定义 `CustomHumanMessage`, `CustomAIMessage`, `CustomToolMessage`
2. 确保所有类继承自对应 LangChain 类
3. 业务字段通过 `additional_kwargs` 存储
4. 提供便捷的工厂方法

### 阶段 2: 更新 Dialog 和类型定义 (优先级高)
1. 更新 `core/models/dialog.py`：使用自定义消息类
2. 重写 `core/models/types.py`：移除消息相关 TypedDict
3. 更新所有导入引用

### 阶段 3: 前端自定义消息类 (优先级高)
1. 创建 `web/src/lib/langchain/messages.ts`
2. 定义 `CustomHumanMessage`, `CustomAIMessage`, `CustomToolMessage` 类
3. 确保继承 `@langchain/core` 对应类

### 阶段 4: 更新前端类型和存储 (优先级高)
1. 重写 `web/src/types/sync.ts`
2. 更新 IndexedDB 存储层
3. 更新 hooks 中的消息处理

### 阶段 5: 数据迁移 (优先级中)
1. 实现旧格式到 LangChain 格式的转换器
2. 页面加载时自动迁移

### 阶段 6: 清理 (优先级低)
1. 删除 TypedDict 消息定义
2. 删除裸 dict 处理逻辑

## Open Questions

1. **additional_kwargs vs 子类属性**: 业务字段是放在 `additional_kwargs` 中，还是定义为子类属性并重写序列化？
2. **工具调用表示**: `CustomAIMessage` 如何处理 `tool_calls`，直接继承还是需要自定义结构？
3. **流式消息构建**: 流式过程中如何逐步构建 `CustomAIMessage` 实例？
