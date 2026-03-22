# Agent 架构重构设计文档

## 总体架构

```
agents/
├── __init__.py
├── main.py                    # 统一入口
│
├── interfaces/                # 【接口层】
│   ├── __init__.py
│   ├── http/                  # HTTP REST API
│   │   ├── __init__.py
│   │   ├── server.py          # FastAPI 应用
│   │   └── routes/            # API 路由
│   └── websocket/             # WebSocket 接口
│       ├── __init__.py
│       ├── server.py          # WebSocket 服务器
│       └── connection.py      # 连接管理
│
├── runtime/                   # 【运行时层】
│   ├── __init__.py
│   ├── builder.py             # AgentBuilder
│   ├── state.py               # StateManager（集中状态）
│   ├── events.py              # EventSystem（统一事件）
│   └── context.py             # 运行时上下文
│
├── kernel/                    # 【核心层】最小 Agent
│   ├── __init__.py
│   ├── agent.py               # KernelAgent
│   ├── loop.py                # 执行循环
│   └── registry.py            # 插件注册表
│
├── plugins/                   # 【插件层】
│   ├── __init__.py
│   ├── base.py                # Plugin 基类
│   │
│   └── builtin/               # 内置插件
│       ├── todo/
│       │   ├── __init__.py
│       │   ├── plugin.py      # TodoPlugin
│       │   ├── tools.py       # 工具实现
│       │   └── state.py       # 状态定义
│       ├── task/
│       ├── background/
│       ├── subagent/
│       ├── team/
│       └── plan/
│
└── infrastructure/            # 【基础设施层】
    ├── __init__.py
    ├── llm/                   # LLM 相关
    │   ├── __init__.py
    │   ├── base.py            # Provider 基类
    │   └── litellm.py         # LiteLLM 实现
    ├── persistence/           # 持久化
    │   ├── __init__.py
    │   └── storage.py         # 存储抽象
    └── tools/                 # 基础工具
        ├── __init__.py
        ├── base.py            # 工具基类
        ├── bash.py
        └── filesystem.py
```

## 核心组件设计

### 1. KernelAgent（最小核心）

```python
# kernel/agent.py
class KernelAgent:
    """
    最小 Agent 核心，只包含：
    - 执行循环
    - 工具调用机制
    - 插件注册接口
    """

    def __init__(
        self,
        provider: LLMProvider,
        state_manager: StateManager,
        event_system: EventSystem,
        tools: list[Callable] = None,
    ):
        self.provider = provider
        self.state = state_manager
        self.events = event_system
        self.plugins = PluginRegistry()
        self.tools = tools or []
        self._stopped = False

    def run(self, messages: list[dict]) -> str:
        """最小执行循环"""
        self.events.emit("agent_started", {"messages": messages})

        while not self._stopped:
            # 1. 调用 LLM
            response = self.provider.chat(messages, self.tools)

            # 2. 检查是否完成
            if not response.tool_calls:
                self.events.emit("agent_completed", {"content": response.content})
                return response.content

            # 3. 执行工具
            for tool_call in response.tool_calls:
                self.events.emit("tool_call", tool_call)
                result = self._execute_tool(tool_call)
                self.events.emit("tool_result", {"call": tool_call, "result": result})

            # 4. 更新消息
            messages.extend(self._build_tool_messages(response.tool_calls))

    def use_plugin(self, plugin: Plugin) -> "KernelAgent":
        """注册插件（链式调用）"""
        plugin.on_load(self)
        self.plugins.register(plugin)
        self.tools.extend(plugin.get_tools())
        return self
```

### 2. StateManager（集中状态）

```python
# runtime/state.py
class StateManager:
    """
    所有状态的单一真实数据源
    """

    def __init__(self, dialog_id: str):
        self.dialog_id = dialog_id
        self.session = DialogSession()
        self._plugin_states: dict[str, PluginState] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str, default=None):
        """获取全局状态"""
        async with self._lock:
            return getattr(self.session, key, default)

    async def set(self, key: str, value):
        """设置全局状态"""
        async with self._lock:
            setattr(self.session, key, value)
            await self._notify_change()

    def plugin(self, plugin_name: str) -> PluginState:
        """获取插件专属状态"""
        if plugin_name not in self._plugin_states:
            self._plugin_states[plugin_name] = PluginState()
        return self._plugin_states[plugin_name]

    def snapshot(self) -> dict:
        """生成完整状态快照"""
        return {
            "dialog_id": self.dialog_id,
            "session": self.session.model_dump(),
            "plugins": {
                name: state.model_dump()
                for name, state in self._plugin_states.items()
            },
        }

    async def _notify_change(self):
        """状态变更通知（广播到 WebSocket）"""
        # 由 EventSystem 处理
        pass
```

### 3. EventSystem（统一事件）

```python
# runtime/events.py
class EventSystem:
    """
    统一事件系统：
    - 内部钩子调用（同步）
    - 外部监控广播（异步）
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._external_adapters: list[ExternalAdapter] = []

    def on(self, event_type: str, handler: Callable) -> "EventSystem":
        """注册事件处理器"""
        self._handlers[event_type].append(handler)
        return self

    def emit(self, event_type: str, payload: dict) -> None:
        """
        触发事件：
        1. 同步调用内部处理器
        2. 异步广播给外部适配器
        """
        event = Event(type=event_type, payload=payload, timestamp=time.time())

        # 1. 同步调用内部处理器（原 hooks）
        for handler in self._handlers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler error for {event_type}: {e}")

        # 2. 异步广播给外部（原 monitoring -> WebSocket）
        asyncio.create_task(self._broadcast_external(event))

    async def _broadcast_external(self, event: Event):
        """广播给外部适配器"""
        for adapter in self._external_adapters:
            try:
                await adapter.send(event)
            except Exception as e:
                logger.error(f"Adapter error: {e}")

    def add_external_adapter(self, adapter: ExternalAdapter):
        """添加外部适配器（如 WebSocket）"""
        self._external_adapters.append(adapter)
```

### 4. Plugin 基类

```python
# plugins/base.py
class Plugin(ABC):
    """
    插件基类，所有功能扩展通过此接口实现
    """

    name: str = ""  # 插件唯一标识

    @abstractmethod
    def on_load(self, agent: KernelAgent) -> None:
        """
        插件加载时调用

        在此方法中：
        - 注册工具
        - 订阅事件
        - 初始化状态
        """
        pass

    @abstractmethod
    def get_tools(self) -> list[Callable]:
        """返回插件提供的工具列表"""
        pass

    def on_unload(self) -> None:
        """插件卸载时调用，清理资源"""
        pass

    def get_state(self, agent: KernelAgent) -> Any:
        """便捷方法：获取插件专属状态"""
        return agent.state.plugin(self.name)
```

## 插件实现示例

```python
# plugins/builtin/todo/plugin.py
class TodoPlugin(Plugin):
    """Todo 管理插件"""

    name = "todo"

    def on_load(self, agent: KernelAgent) -> None:
        # 获取插件专属状态
        self.state = self.get_state(agent)
        if not hasattr(self.state, 'items'):
            self.state.items = []

        # 订阅事件
        agent.events.on("tool_call", self._on_tool_call)

    def get_tools(self) -> list[Callable]:
        from .tools import todo_tool
        return [todo_tool]

    def _on_tool_call(self, event):
        """监听工具调用，更新状态"""
        if event.payload.get("name") == "todo":
            # 更新 todo 状态
            pass

    def _default_system_prompt(self) -> str:
        return "Use todo tool to track progress..."
```

## 运行时组装

```python
# runtime/builder.py
class AgentBuilder:
    """流式 API 构建 Agent"""

    def __init__(self):
        self._plugins: list[Plugin] = []
        self._tools: list[Callable] = []
        self._provider: LLMProvider = None

    def with_provider(self, provider: LLMProvider) -> "AgentBuilder":
        self._provider = provider
        return self

    def with_base_tools(self) -> "AgentBuilder":
        """添加基础工具（bash, read_file, write_file, edit_file）"""
        from infrastructure.tools import bash, filesystem
        self._tools.extend([bash.run_bash, filesystem.read_file,
                           filesystem.write_file, filesystem.edit_file])
        return self

    def with_plugin(self, plugin: Plugin) -> "AgentBuilder":
        """添加插件"""
        self._plugins.append(plugin)
        return self

    def build(self, dialog_id: str) -> KernelAgent:
        """构建 Agent"""
        # 创建运行时组件
        state = StateManager(dialog_id)
        events = EventSystem()

        # 创建 Agent
        agent = KernelAgent(
            provider=self._provider or create_provider_from_env(),
            state_manager=state,
            event_system=events,
            tools=self._tools.copy(),
        )

        # 加载插件
        for plugin in self._plugins:
            agent.use_plugin(plugin)

        return agent
```

## 依赖关系图

```
interfaces/          →  runtime/          →  kernel/           →  plugins/          →  infrastructure/
     │                      │                   │                   │                    │
     │                      │                   │                   │                    │
     ▼                      ▼                   ▼                   ▼                    ▼
  HTTP/WS              Builder         KernelAgent          PluginBase            LLM/Tools
  Server               StateMgr        Loop                 Todo/Task/etc         Storage
                       EventSys        Registry
```

**关键约束**：
- 上层可以依赖下层
- 下层不能依赖上层
- 同层组件可以互相依赖（但尽量避免）
- plugins/ 只依赖 kernel/ 和 infrastructure/
