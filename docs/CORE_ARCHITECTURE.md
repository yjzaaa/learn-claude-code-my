# Core 架构文档

## 概述

`core/` 模块是 Agent 系统的重构版本，采用**四层架构**和**面向接口编程**原则，为未来集成 LangGraph、CrewAI 等框架预留了清晰的扩展点。

---

## 架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Application Layer                              │
│  (examples/, API routes, CLI tools...)                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Agent Interface Layer                          │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                     AgentInterface (ABC)                         │   │
│   │  - run() / run_sync() / stop()                                   │   │
│   │  - register_tool() / unregister_tool()                           │   │
│   │  - get_conversation_state() / restore_conversation_state()       │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                    ▲                                    │
│                    ┌───────────────┼───────────────┐                    │
│                    │               │               │                    │
│                    ▼               ▼               ▼                    │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│   │   SimpleAgent   │  │  LangGraphAgent │  │   CrewAIAgent   │        │
│   │   (当前实现)     │  │    (预留接口)    │  │    (预留接口)    │        │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘        │
│                                                                          │
│   AgentFactory.create("simple", id)   AgentFactory.create("langgraph", id)│
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌─────────────────────────────┐         ┌─────────────────────────────┐
│        Tools Layer          │         │       Provider Layer        │
│                             │         │                             │
│  - ToolRegistry             │         │  - BaseProvider (ABC)       │
│  - @tool decorator          │         │  - LiteLLMProvider          │
│  - WorkspaceOps             │         │    (OpenAI, Anthropic, ...) │
│                             │         │                             │
└─────────────────────────────┘         └─────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            Types Layer                                   │
│                                                                          │
│  - AgentStatus, AgentMessage, AgentEvent, ToolResult                    │
│  - StreamChunk, HookName                                                │
│  (所有模块共享的基础类型)                                                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 模块说明

### 1. `core/types/` - 类型层

所有模块共享的基础类型定义。避免循环导入，确保类型一致性。

```python
from core.types import (
    AgentStatus,      # IDLE, RUNNING, THINKING, TOOL_CALLING, ...
    AgentMessage,     # role, content, tool_calls, tool_call_id
    AgentEvent,       # type, data, metadata
    ToolResult,       # tool_name, tool_call_id, output, error
    StreamChunk,      # is_content, is_tool_call, is_done, ...
    HookName,         # ON_BEFORE_RUN, ON_STREAM_TOKEN, ...
)
```

---

### 2. `core/agent/` - Agent 层

#### 2.1 抽象接口 (`interface.py`)

```python
class AgentInterface(ABC):
    @abstractmethod
    async def run(self, user_input, context, system_prompt) -> AsyncIterator[AgentEvent]: ...
    
    @abstractmethod
    async def stop(self) -> None: ...
    
    @abstractmethod
    def register_tool(self, name, handler, description, schema) -> None: ...
```

#### 2.2 当前实现 (`simple/agent.py`)

```python
class SimpleAgent(AgentInterface):
    """不依赖任何框架，直接调用 LLM provider"""
    
    async def run(self, ...):
        # 手动实现 Agent Loop
        # 1. 调用 LLM (流式)
        # 2. 如果有 tool_calls, 执行工具
        # 3. 将结果回填给 LLM
        # 4. 重复直到没有 tool_calls
```

#### 2.3 工厂模式 (`factory.py`)

```python
# 创建 Agent
agent = AgentFactory.create("simple", agent_id="my_agent")

# 未来切换到 LangGraph（只改一行）
agent = AgentFactory.create("langgraph", agent_id="my_agent")
```

#### 2.4 适配器基类 (`adapters/base.py`)

为未来集成 LangGraph、CrewAI 等框架预留的接口：

```python
class SDKAdapterBase(AgentInterface):
    @abstractmethod
    async def _create_agent(self, config: dict) -> Any: ...
    
    @abstractmethod
    def _adapt_tools(self, tools: dict) -> list: ...
    
    @abstractmethod
    def _convert_event(self, sdk_event: Any) -> AgentEvent: ...
```

---

### 3. `core/tools/` - 工具层

#### 3.1 工具定义 (`toolkit.py`)

```python
from core.tools import tool

@tool(name="search", description="Search the web")
def search(query: str, limit: int = 10) -> str:
    ...
```

#### 3.2 工具注册表 (`registry.py`)

```python
registry = ToolRegistry()
registry.register("search", search_handler, "Search the web", schema)

# 执行工具
result = await registry.execute("search", {"query": "python"})
```

#### 3.3 工作区操作 (`workspace.py`)

```python
workspace = WorkspaceOps(Path.cwd())

# 内置工具
workspace.run_bash("ls -la")
workspace.run_read("file.txt")
workspace.run_write("file.txt", "content")
workspace.run_edit("file.txt", "old", "new")
```

---

### 4. `core/providers/` - Provider 层

```python
from core.providers import LiteLLMProvider

provider = LiteLLMProvider(
    model="deepseek-chat",
    api_key="...",
)

# 流式调用
async for chunk in provider.chat_stream(messages, tools):
    if chunk.is_content:
        print(chunk.content)
    elif chunk.is_tool_call:
        print(chunk.tool_call)
```

---

## 事件流

```
用户输入
    │
    ▼
┌────────────────┐
│ ON_BEFORE_RUN  │
└────────────────┘
    │
    ▼
调用 LLM (流式)
    │
    ├──► ON_STREAM_TOKEN (text_delta)
    │
    ├──► ON_STREAM_TOKEN (reasoning_delta) [可选]
    │
    └──► 发现 tool_calls
            │
            ▼
    ┌────────────────┐
    │ ON_TOOL_CALL   │
    └────────────────┘
            │
            ▼
    执行工具函数
            │
            ▼
    ┌────────────────┐
    │ ON_TOOL_RESULT │
    └────────────────┘
            │
            ▼
    将结果回填给 LLM
            │
            ▼
    循环继续 (如果有更多工具调用)
            │
            ▼
    ┌────────────────┐
    │ ON_COMPLETE    │
    └────────────────┘
            │
            ▼
    ┌────────────────┐
    │ ON_AFTER_RUN   │
    └────────────────┘
```

---

## 使用示例

### 基础用法

```python
import asyncio
from core import AgentFactory, AgentMessage
from core.tools import WorkspaceOps

async def main():
    # 1. 创建 Agent
    workspace = WorkspaceOps(Path.cwd())
    agent = AgentFactory.create("simple", "my_agent")
    
    # 2. 准备工具
    tools_info = []
    for tool_fn in workspace.get_tools():
        spec = getattr(tool_fn, "__tool_spec__", {})
        tools_info.append({
            "name": spec["name"],
            "handler": tool_fn,
            "description": spec["description"],
            "parameters": spec["parameters"],
        })
    
    # 3. 初始化
    await agent.initialize({
        "model": "deepseek-chat",
        "system": "You are helpful",
        "tools": tools_info,
    })
    
    # 4. 运行
    async for event in agent.run("Hello"):
        if event.type == "text_delta":
            print(event.data, end="")
        elif event.type == "tool_start":
            print(f"\n[Tool: {event.data['name']}]")
        elif event.type == "complete":
            print("\n[Done]")

asyncio.run(main())
```

### 使用配置

```python
# agent_config.yaml
agent:
  type: "simple"
  id: "my_agent"
  model: "deepseek-chat"
  system: "You are a helpful assistant"
  max_iterations: 10
  max_tokens: 8000
```

```python
from core import bootstrap_agent

agent = await bootstrap_agent("agent_config.yaml")
```

---

## 扩展：添加新的 Agent 类型

### 1. 实现适配器

```python
# core/agent/adapters/langgraph_adapter.py

from .base import SDKAdapterBase
from ...types import AgentEvent

try:
    from langgraph.graph import StateGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

class LangGraphAdapter(SDKAdapterBase):
    async def _create_agent(self, config: dict):
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("pip install langgraph")
        
        workflow = StateGraph(dict)
        # ... 构建工作流
        return workflow.compile()
    
    async def run(self, user_input, context, system_prompt):
        # 调用 LangGraph 并转换事件
        async for sdk_event in self._sdk_agent.astream(...):
            agent_event = self._convert_event(sdk_event)
            if agent_event:
                yield agent_event
    
    def _adapt_tools(self, tools: dict):
        # 转换为 LangChain Tool 格式
        from langchain.tools import Tool
        return [Tool(name=n, func=t["handler"], description=t["description"]) 
                for n, t in tools.items()]
```

### 2. 注册到工厂

```python
# core/agent/factory.py

from .adapters.langgraph_adapter import LangGraphAdapter

class AgentFactory:
    _registry = {
        "simple": SimpleAgent,
        "langgraph": LangGraphAdapter,  # 添加这一行
    }
```

### 3. 使用

```python
agent = AgentFactory.create("langgraph", agent_id="my_agent")
```

---

## 设计原则

1. **面向接口编程**: 上层代码依赖 `AgentInterface`，不依赖具体实现
2. **依赖倒置**: 通过工厂模式创建实例，运行时决定使用哪个实现
3. **单一职责**: 每个模块只做一件事（types/agent/tools/providers）
4. **开闭原则**: 添加新 Agent 类型不需要修改现有代码，只需要注册到工厂
5. **异步优先**: 所有 I/O 操作都是异步的，支持流式输出

---

## 文件清单

```
core/
├── __init__.py
├── types/
│   ├── __init__.py          # AgentStatus, AgentMessage, AgentEvent, ...
├── agent/
│   ├── __init__.py          # AgentFactory, AgentInterface, SimpleAgent
│   ├── interface.py         # AgentInterface, AgentLifecycleHooks
│   ├── factory.py           # AgentFactory, bootstrap_agent
│   ├── simple/
│   │   ├── __init__.py      # SimpleAgent
│   │   └── agent.py         # SimpleAgent 实现
│   └── adapters/
│       ├── __init__.py      # SDKAdapterBase
│       └── base.py          # SDKAdapterBase
├── tools/
│   ├── __init__.py          # tool, ToolRegistry, WorkspaceOps
│   ├── toolkit.py           # @tool 装饰器
│   ├── registry.py          # ToolRegistry
│   └── workspace.py         # WorkspaceOps
└── providers/
    ├── __init__.py          # BaseProvider, LiteLLMProvider
    ├── base.py              # BaseProvider
    └── litellm_provider.py  # LiteLLMProvider
```
