# Runtime 基类提取设计

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        AgentRuntime (ABC)                       │
│                    - 接口定义 (保持现状)                         │
└─────────────────────────────────────────────────────────────────┘
                                △
                                │ 继承
┌─────────────────────────────────────────────────────────────────┐
│              AbstractAgentRuntime[ConfigT] (ABC)                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 通用实现                                                  │   │
│  │ - _agent_id, _config, _tools, _dialogs                   │   │
│  │ - runtime_id, agent_type 属性                            │   │
│  │ - register_tool / unregister_tool                        │   │
│  │ - create_dialog / get_dialog / list_dialogs              │   │
│  │ - initialize (模板方法) / shutdown                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 抽象方法 (子类实现)                                       │   │
│  │ - _do_initialize()     # 初始化特定逻辑                  │   │
│  │ - _do_shutdown()       # 清理特定逻辑                    │   │
│  │ - send_message()       # 核心消息处理                    │   │
│  │ - stop()               # 停止处理                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                △                                       △
                │                                       │
    ┌───────────┴───────────┐               ┌───────────┴───────────┐
    │    SimpleRuntime      │               │   DeepAgentRuntime    │
    │  - 6 Managers         │               │  - deep-agents 框架   │
    │  - 手动 LLM Loop      │               │  - astream() 流式     │
    │  - EventBus           │               │  - 3 个专用 Logger    │
    └───────────────────────┘               └───────────────────────┘
```

## 核心设计模式

### 1. 泛型类型参数

```python
ConfigT = TypeVar("ConfigT", bound=BaseModel)

class AbstractAgentRuntime(AgentRuntime, Generic[ConfigT], ABC):
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._config: Optional[ConfigT] = None
        self._tools: dict[str, ToolCache] = {}
        self._dialogs: dict[str, Dialog] = {}
```

### 2. 模板方法模式

```python
async def initialize(self, config: ConfigT | dict[str, Any]) -> None:
    # 1. 配置验证和存储 (通用)
    self._config = self._validate_config(config)

    # 2. 子类特定初始化 (抽象)
    await self._do_initialize()

    # 3. 日志记录 (通用)
    logger.info(f"[{self.__class__.__name__}] Initialized: {self._agent_id}")
```

### 3. 共享模型

```python
class ToolCache(BaseModel):
    """工具缓存 - 供所有 Runtime 使用"""
    handler: Any = None
    description: str = ""
    parameters_schema: dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True
```

## 类结构

### AbstractAgentRuntime[ConfigT]

| 成员 | 类型 | 说明 |
|------|------|------|
| `_agent_id` | `str` | 运行时唯一标识 |
| `_config` | `Optional[ConfigT]` | 泛型配置对象 |
| `_tools` | `dict[str, ToolCache]` | 工具缓存 |
| `_dialogs` | `dict[str, Dialog]` | 对话缓存 |
| `runtime_id` | `property` | 返回 `_agent_id` |
| `agent_type` | `abstract property` | 子类实现 |
| `initialize()` | `async` | 模板方法 |
| `_do_initialize()` | `abstract async` | 子类实现 |
| `shutdown()` | `async` | 模板方法 |
| `_do_shutdown()` | `abstract async` | 子类实现 |
| `send_message()` | `abstract async` | 子类实现 |
| `create_dialog()` | `async` | 通用实现 |
| `get_dialog()` | 方法 | 通用实现 |
| `list_dialogs()` | 方法 | 通用实现 |
| `register_tool()` | 方法 | 通用实现 |
| `unregister_tool()` | 方法 | 通用实现 |
| `stop()` | `abstract async` | 子类实现 |
| `_validate_config()` | 方法 | 配置验证钩子 |

## 类型转换策略

### SimpleRuntime

```python
class SimpleRuntime(AbstractAgentRuntime[EngineConfig]):
    """使用 EngineConfig 作为配置类型"""

    @property
    def agent_type(self) -> str:
        return "simple"

    async def _do_initialize(self) -> None:
        # 初始化 6 个 Managers
        self._state_mgr = StateManager(...)
        ...
```

### DeepAgentRuntime

```python
class DeepAgentRuntime(AbstractAgentRuntime[DeepAgentConfig]):
    """使用 DeepAgentConfig 作为配置类型"""

    @property
    def agent_type(self) -> str:
        return "deep"

    async def _do_initialize(self) -> None:
        # 创建 deep agent
        self._agent = create_deep_agent(...)
```

## 文件布局

```
core/agent/runtimes/
├── __init__.py          # 导出所有 Runtime
├── base.py              # AbstractAgentRuntime[ConfigT] + ToolCache
├── simple_runtime.py    # SimpleRuntime (简化后 ~400 行)
└── deep_runtime.py      # DeepAgentRuntime (简化后 ~350 行)
```

## 迁移策略

1. **第一阶段**: 创建 `base.py` 并实现 `AbstractAgentRuntime`
2. **第二阶段**: 修改 `SimpleRuntime` 继承基类
3. **第三阶段**: 修改 `DeepAgentRuntime` 继承基类
4. **第四阶段**: 运行测试验证功能完整

## 向后兼容性

- `AgentRuntime` 接口保持不变
- `AgentFactory` 创建逻辑无需修改
- 所有外部调用方不受影响
