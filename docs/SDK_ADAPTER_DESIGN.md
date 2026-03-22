# Agent SDK 适配器架构设计

**设计目标**: 保持当前简单实现，预留切换到 LangGraph/CrewAI/AutoGen 等框架的接口

---

## 1. 核心思想

```
┌─────────────────────────────────────────────────────────────────┐
│                    依赖倒置原则 (DIP)                             │
│                                                                 │
│   上层模块 (Core) ──────► 抽象接口 (AgentInterface)               │
│                               ▲                                 │
│                               │ 实现                             │
│   ┌───────────────────────────┼───────────────────────────┐     │
│   │                           │                           │     │
│   ▼                           ▼                           ▼     │
│ SimpleAgent               LangGraphAgent            CrewAIAgent │
│ (当前实现)                 (未来适配)                (未来适配)  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 目录结构设计

```
core/
├── agent/
│   ├── __init__.py
│   ├── interface.py              # Agent 抽象接口 (核心)
│   ├── simple/                   # 当前简单实现
│   │   ├── __init__.py
│   │   ├── agent.py              # SimpleAgent 实现
│   │   ├── loop.py               # 基础 Agent Loop
│   │   └── tools.py              # 工具执行
│   ├── adapters/                 # SDK 适配器 (预留)
│   │   ├── __init__.py
│   │   ├── base.py               # 适配器基类
│   │   ├── langgraph_adapter.py  # LangGraph 适配器 (预留)
│   │   ├── crewai_adapter.py     # CrewAI 适配器 (预留)
│   │   ├── autogen_adapter.py    # AutoGen 适配器 (预留)
│   │   └── claude_sdk_adapter.py # Claude Agent SDK 适配器 (预留)
│   └── factory.py                # Agent 工厂 (创建具体实现)
└── ...
```

---

## 3. 核心接口定义

### 3.1 Agent 抽象接口

```python
# core/agent/interface.py
"""
Agent 抽象接口 - 定义所有 Agent 实现必须遵守的契约

设计原则:
- 接口最小化：只定义最核心的方法
- 实现无关：不涉及任何具体 SDK 的细节
- 异步优先：所有操作都是异步的
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Callable, Optional, Any
from dataclasses import dataclass
from enum import Enum


class AgentStatus(Enum):
    """Agent 状态"""
    IDLE = "idle"
    RUNNING = "running"
    THINKING = "thinking"      # 正在推理
    TOOL_CALLING = "tool_calling"  # 正在调用工具
    STREAMING = "streaming"    # 正在流式输出
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class AgentMessage:
    """标准化消息格式"""
    role: str                    # "user", "assistant", "system", "tool"
    content: str
    tool_calls: Optional[list] = None
    tool_call_id: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    tool_call_id: str
    output: str
    error: Optional[str] = None
    execution_time_ms: int = 0


@dataclass
class AgentEvent:
    """Agent 事件 - 用于通知上层"""
    type: str                    # "text_delta", "tool_start", "tool_end", "complete", "error"
    data: Any
    metadata: Optional[dict] = None


class AgentInterface(ABC):
    """
    Agent 抽象接口
    
    所有 Agent 实现（Simple/LangGraph/CrewAI）都必须实现此接口
    这样上层代码不需要关心底层使用什么 SDK
    """
    
    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Agent 唯一标识"""
        pass
    
    @property
    @abstractmethod
    def status(self) -> AgentStatus:
        """当前状态"""
        pass
    
    @abstractmethod
    async def initialize(self, config: dict) -> None:
        """
        初始化 Agent
        
        Args:
            config: 配置字典，不同实现可以有不同的配置项
                   但必须有 "model" 和 "tools" 两个基础配置
        """
        pass
    
    @abstractmethod
    async def run(
        self, 
        user_input: str,
        context: Optional[list[AgentMessage]] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[AgentEvent]:
        """
        运行 Agent - 核心方法
        
        Args:
            user_input: 用户输入
            context: 历史消息上下文
            system_prompt: 系统提示词
            
        Yields:
            AgentEvent: 流式事件（文本片段、工具调用、完成等）
        """
        pass
    
    @abstractmethod
    async def run_sync(
        self,
        user_input: str,
        context: Optional[list[AgentMessage]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        同步运行（非流式）
        
        默认实现可以通过 run() 收集所有输出后返回
        但具体实现可以优化此方法
        """
        # 默认实现
        result = []
        async for event in self.run(user_input, context, system_prompt):
            if event.type == "text_delta":
                result.append(event.data)
            elif event.type == "complete":
                break
        return "".join(result)
    
    @abstractmethod
    async def stop(self) -> None:
        """停止当前运行"""
        pass
    
    @abstractmethod
    def register_tool(
        self, 
        name: str, 
        handler: Callable,
        description: str,
        schema: Optional[dict] = None
    ) -> None:
        """
        注册工具
        
        Args:
            name: 工具名称
            handler: 工具处理函数
            description: 工具描述
            schema: 参数 JSON Schema
        """
        pass
    
    @abstractmethod
    def unregister_tool(self, name: str) -> None:
        """注销工具"""
        pass
    
    @abstractmethod
    async def get_conversation_state(self) -> dict:
        """获取对话状态（用于持久化）"""
        pass
    
    @abstractmethod
    async def restore_conversation_state(self, state: dict) -> None:
        """恢复对话状态"""
        pass
```

### 3.2 当前简单实现

```python
# core/agent/simple/agent.py
"""
SimpleAgent - 当前简单实现，不依赖任何框架
基于原始的 base_agent_loop.py 重构
"""
import asyncio
from typing import AsyncIterator, Callable, Optional, Any
from core.agent.interface import (
    AgentInterface, AgentStatus, AgentMessage, 
    AgentEvent, ToolResult
)
from core.providers.base import BaseProvider
from core.tools.registry import ToolRegistry


class SimpleAgent(AgentInterface):
    """
    简单 Agent 实现
    
    特点:
    - 无外部依赖
    - 直接调用 LLM provider
    - 手动处理工具调用循环
    - 适合理解原理和快速原型
    """
    
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._status = AgentStatus.IDLE
        self._provider: Optional[BaseProvider] = None
        self._tools = ToolRegistry()
        self._stop_event = asyncio.Event()
        self._messages: list[AgentMessage] = []
        self._config: dict = {}
    
    @property
    def agent_id(self) -> str:
        return self._agent_id
    
    @property
    def status(self) -> AgentStatus:
        return self._status
    
    async def initialize(self, config: dict) -> None:
        """初始化 - 配置 provider 和工具"""
        self._config = config
        
        # 初始化 provider (内部使用 LiteLLM)
        from core.providers.litellm_provider import LiteLLMProvider
        self._provider = LiteLLMProvider(
            model=config.get("model", "claude-sonnet-4-6"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url")
        )
        
        # 注册内置工具
        for tool_config in config.get("tools", []):
            self._tools.register(
                name=tool_config["name"],
                handler=tool_config["handler"],
                description=tool_config["description"],
                schema=tool_config.get("schema")
            )
    
    async def run(
        self,
        user_input: str,
        context: Optional[list[AgentMessage]] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[AgentEvent]:
        """
        运行 Agent - 简单循环实现
        
        流程: user input → LLM → (tool call → execute → repeat) → final answer
        """
        self._status = AgentStatus.RUNNING
        self._stop_event.clear()
        
        # 构建消息列表
        messages = list(context) if context else []
        messages.append(AgentMessage(role="user", content=user_input))
        
        try:
            max_iterations = self._config.get("max_iterations", 10)
            
            for iteration in range(max_iterations):
                if self._stop_event.is_set():
                    yield AgentEvent(type="stopped", data="User stopped")
                    break
                
                # 1. 调用 LLM
                self._status = AgentStatus.THINKING
                response = await self._provider.chat(
                    messages=self._convert_messages(messages),
                    system_prompt=system_prompt,
                    tools=self._tools.get_schemas(),
                    stream=True
                )
                
                # 2. 处理流式响应
                assistant_content = ""
                tool_calls = []
                
                async for chunk in response:
                    if self._stop_event.is_set():
                        break
                    
                    delta = chunk.get("delta", {})
                    
                    # 文本增量
                    if "content" in delta:
                        text = delta["content"]
                        assistant_content += text
                        yield AgentEvent(
                            type="text_delta",
                            data=text,
                            metadata={"iteration": iteration}
                        )
                    
                    # 工具调用收集
                    if "tool_calls" in delta:
                        tool_calls.extend(delta["tool_calls"])
                
                # 3. 如果没有工具调用，直接返回
                if not tool_calls:
                    messages.append(AgentMessage(
                        role="assistant",
                        content=assistant_content
                    ))
                    yield AgentEvent(
                        type="complete",
                        data=assistant_content,
                        metadata={"messages": messages}
                    )
                    break
                
                # 4. 执行工具调用
                messages.append(AgentMessage(
                    role="assistant",
                    content=assistant_content,
                    tool_calls=tool_calls
                ))
                
                for tool_call in tool_calls:
                    if self._stop_event.is_set():
                        break
                    
                    self._status = AgentStatus.TOOL_CALLING
                    tool_name = tool_call["function"]["name"]
                    tool_args = tool_call["function"]["arguments"]
                    tool_call_id = tool_call["id"]
                    
                    # 通知工具开始
                    yield AgentEvent(
                        type="tool_start",
                        data={"name": tool_name, "args": tool_args},
                        metadata={"tool_call_id": tool_call_id}
                    )
                    
                    # 执行工具
                    try:
                        result = await self._tools.execute(tool_name, tool_args)
                        tool_result = ToolResult(
                            tool_name=tool_name,
                            tool_call_id=tool_call_id,
                            output=str(result)
                        )
                    except Exception as e:
                        tool_result = ToolResult(
                            tool_name=tool_name,
                            tool_call_id=tool_call_id,
                            output="",
                            error=str(e)
                        )
                    
                    # 添加工具结果到消息
                    messages.append(AgentMessage(
                        role="tool",
                        content=tool_result.output or tool_result.error,
                        tool_call_id=tool_call_id
                    ))
                    
                    # 通知工具完成
                    yield AgentEvent(
                        type="tool_end",
                        data=tool_result,
                        metadata={"tool_call_id": tool_call_id}
                    )
                
                # 继续循环，让 LLM 基于工具结果继续思考
                
            else:
                # 达到最大迭代次数
                yield AgentEvent(
                    type="error",
                    data="Max iterations reached",
                    metadata={"max_iterations": max_iterations}
                )
        
        except Exception as e:
            self._status = AgentStatus.ERROR
            yield AgentEvent(type="error", data=str(e))
        
        finally:
            if self._status != AgentStatus.ERROR:
                self._status = AgentStatus.IDLE
    
    async def stop(self) -> None:
        """停止运行"""
        self._stop_event.set()
        self._status = AgentStatus.STOPPED
    
    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str,
        schema: Optional[dict] = None
    ) -> None:
        """注册工具"""
        self._tools.register(name, handler, description, schema)
    
    def unregister_tool(self, name: str) -> None:
        """注销工具"""
        self._tools.unregister(name)
    
    async def get_conversation_state(self) -> dict:
        """获取对话状态"""
        return {
            "agent_id": self._agent_id,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "tool_calls": m.tool_calls,
                    "tool_call_id": m.tool_call_id
                }
                for m in self._messages
            ],
            "config": self._config
        }
    
    async def restore_conversation_state(self, state: dict) -> None:
        """恢复对话状态"""
        self._messages = [
            AgentMessage(**m) for m in state.get("messages", [])
        ]
        self._config = state.get("config", {})
    
    def _convert_messages(self, messages: list[AgentMessage]) -> list[dict]:
        """转换为 provider 需要的格式"""
        return [
            {
                "role": m.role,
                "content": m.content,
                **({"tool_calls": m.tool_calls} if m.tool_calls else {}),
                **({"tool_call_id": m.tool_call_id} if m.tool_call_id else {})
            }
            for m in messages
        ]
```

### 3.3 适配器基类 (预留)

```python
# core/agent/adapters/base.py
"""
SDK 适配器基类

为 LangGraph、CrewAI 等框架适配提供公共基础
"""
from abc import abstractmethod
from typing import Optional
from core.agent.interface import AgentInterface, AgentMessage


class SDKAdapterBase(AgentInterface):
    """
    SDK 适配器基类
    
    子类需要实现:
    - _create_agent(): 创建具体的 SDK Agent 实例
    - _adapt_tools(): 将我们的工具格式转换为 SDK 格式
    - _convert_events(): 将 SDK 事件转换为我们的事件格式
    """
    
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._sdk_agent = None
        self._tools = {}
        self._config = {}
    
    @property
    def agent_id(self) -> str:
        return self._agent_id
    
    async def initialize(self, config: dict) -> None:
        """初始化 - 创建 SDK Agent"""
        self._config = config
        self._sdk_agent = await self._create_agent(config)
    
    @abstractmethod
    async def _create_agent(self, config: dict) -> Any:
        """
        创建具体的 SDK Agent 实例
        
        子类必须实现此方法
        """
        pass
    
    @abstractmethod
    def _adapt_tools(self, tools: dict) -> list:
        """
        将我们的工具格式转换为 SDK 特定格式
        
        例如 LangGraph 需要转换为 LangChain Tool 对象
        CrewAI 需要转换为 CrewAI Tool 对象
        """
        pass
    
    @abstractmethod
    def _convert_event(self, sdk_event: Any) -> Optional[AgentEvent]:
        """
        将 SDK 事件转换为我们的 AgentEvent 格式
        
        返回 None 表示忽略此事件
        """
        pass
```

### 3.4 工厂模式 - 创建 Agent

```python
# core/agent/factory.py
"""
Agent 工厂

根据配置创建不同的 Agent 实现
实现运行时切换 SDK
"""
from typing import Optional
from core.agent.interface import AgentInterface
from core.agent.simple.agent import SimpleAgent

# 可选：延迟导入适配器
# from core.agent.adapters.langgraph_adapter import LangGraphAgent
# from core.agent.adapters.crewai_adapter import CrewAIAgent


class AgentFactory:
    """
    Agent 工厂
    
    使用:
        agent = AgentFactory.create("simple", agent_id="agent_001")
        agent = AgentFactory.create("langgraph", agent_id="agent_002")
    """
    
    _registry = {
        "simple": SimpleAgent,
        # "langgraph": LangGraphAgent,  # 未来启用
        # "crewai": CrewAIAgent,        # 未来启用
        # "autogen": AutoGenAgent,      # 未来启用
        # "claude_sdk": ClaudeSDKAgent, # 未来启用
    }
    
    @classmethod
    def create(
        cls,
        agent_type: str,
        agent_id: str,
        config: Optional[dict] = None
    ) -> AgentInterface:
        """
        创建 Agent 实例
        
        Args:
            agent_type: Agent 类型 (simple/langgraph/crewai/...)
            agent_id: 唯一标识
            config: 配置字典
            
        Returns:
            AgentInterface: Agent 实例
        """
        if agent_type not in cls._registry:
            raise ValueError(
                f"Unknown agent type: {agent_type}. "
                f"Available: {list(cls._registry.keys())}"
            )
        
        agent_class = cls._registry[agent_type]
        agent = agent_class(agent_id)
        
        if config:
            # 注意：异步初始化需要在异步环境中调用
            # 这里只是创建实例，initialize 需要单独调用
            pass
        
        return agent
    
    @classmethod
    def register(cls, agent_type: str, agent_class: type) -> None:
        """
        注册新的 Agent 类型
        
        用于插件系统或测试
        """
        if not issubclass(agent_class, AgentInterface):
            raise TypeError(f"Agent class must implement AgentInterface")
        cls._registry[agent_type] = agent_class
    
    @classmethod
    def available_types(cls) -> list[str]:
        """获取所有可用的 Agent 类型"""
        return list(cls._registry.keys())
    
    @classmethod
    def is_available(cls, agent_type: str) -> bool:
        """检查某个 Agent 类型是否可用"""
        return agent_type in cls._registry
```

### 3.5 配置驱动的 Agent 创建

```python
# core/agent/bootstrap.py
"""
Agent 启动引导

根据配置文件创建和初始化 Agent
"""
import yaml
from core.agent.factory import AgentFactory
from core.agent.interface import AgentInterface


async def bootstrap_agent(config_path: str) -> AgentInterface:
    """
    从配置文件启动 Agent
    
    配置文件示例 (config.yaml):
    
    agent:
      type: "simple"  # 或 "langgraph", "crewai"
      id: "my_agent"
      model: "claude-sonnet-4-6"
      max_iterations: 10
      
    tools:
      - name: "search"
        enabled: true
      - name: "code_executor"
        enabled: true
    """
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    agent_config = config.get("agent", {})
    agent_type = agent_config.get("type", "simple")
    agent_id = agent_config.get("id", "default_agent")
    
    # 创建 Agent
    agent = AgentFactory.create(agent_type, agent_id)
    
    # 初始化
    await agent.initialize(agent_config)
    
    # 注册工具
    tools_config = config.get("tools", [])
    for tool in tools_config:
        if tool.get("enabled", True):
            handler = _load_tool_handler(tool["name"])
            agent.register_tool(
                name=tool["name"],
                handler=handler,
                description=tool.get("description", ""),
                schema=tool.get("schema")
            )
    
    return agent


def _load_tool_handler(tool_name: str):
    """加载工具处理函数"""
    # 动态导入工具
    from core.tools import TOOL_REGISTRY
    return TOOL_REGISTRY.get(tool_name)
```

---

## 4. 使用示例

### 4.1 当前使用方式 (SimpleAgent)

```python
import asyncio
from core.agent.factory import AgentFactory

async def main():
    # 创建 Agent（当前使用 simple 实现）
    agent = AgentFactory.create(
        agent_type="simple",
        agent_id="my_agent"
    )
    
    # 初始化
    await agent.initialize({
        "model": "claude-sonnet-4-6",
        "api_key": "...",
        "max_iterations": 10
    })
    
    # 注册工具
    agent.register_tool(
        name="search",
        handler=search_tool,
        description="搜索信息"
    )
    
    # 运行
    async for event in agent.run("你好，请帮我搜索 Python 教程"):
        if event.type == "text_delta":
            print(event.data, end="")
        elif event.type == "tool_start":
            print(f"\n[调用工具: {event.data['name']}]")
        elif event.type == "complete":
            print("\n[完成]")

asyncio.run(main())
```

### 4.2 未来切换到 LangGraph (只需要改一行)

```python
# 现在
agent = AgentFactory.create(agent_type="simple", agent_id="my_agent")

# 未来切换到 LangGraph（只需要改这里）
agent = AgentFactory.create(agent_type="langgraph", agent_id="my_agent")

# 其余代码完全一致！
await agent.initialize(config)
async for event in agent.run("你好"):
    ...
```

### 4.3 运行时动态切换

```python
# 根据配置动态选择实现
AGENT_TYPE = os.getenv("AGENT_TYPE", "simple")  # 通过环境变量切换

agent = AgentFactory.create(agent_type=AGENT_TYPE, agent_id="my_agent")
```

---

## 5. 预留的适配器实现 (待完成)

### 5.1 LangGraph 适配器大纲

```python
# core/agent/adapters/langgraph_adapter.py
"""
LangGraph 适配器 - 预留实现

完成后可以实现:
- 状态图可视化
- 复杂流程控制
- 时间旅行调试
"""

try:
    from langgraph.graph import StateGraph, END
    from langchain_anthropic import ChatAnthropic
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

from core.agent.adapters.base import SDKAdapterBase


class LangGraphAgent(SDKAdapterBase):
    """
    LangGraph 适配器
    
    依赖: pip install langgraph langchain-anthropic
    """
    
    async def _create_agent(self, config: dict):
        if not LANGGRAPH_AVAILABLE:
            raise ImportError(
                "LangGraph not installed. "
                "Run: pip install langgraph langchain-anthropic"
            )
        
        # 创建 LangGraph 工作流
        workflow = StateGraph(dict)
        
        # 添加节点
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tool_node)
        
        # 添加边
        workflow.add_edge("start", "agent")
        workflow.add_conditional_edges(
            "agent",
            self._should_call_tools,
            {"tools": "tools", "end": END}
        )
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    async def run(self, user_input, context=None, system_prompt=None):
        # 调用 LangGraph 并转换事件
        ...
```

### 5.2 CrewAI 适配器大纲

```python
# core/agent/adapters/crewai_adapter.py
"""
CrewAI 适配器 - 预留实现

完成后可以实现:
- 多 Agent 协作
- 角色驱动的工作流
- 简单的 crew 定义
"""

try:
    from crewai import Agent as CrewAIAgent, Crew, Task
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False


class CrewAIAdapter(SDKAdapterBase):
    """
    CrewAI 适配器
    
    依赖: pip install crewai
    """
    
    async def _create_agent(self, config: dict):
        # 创建 CrewAI Agent
        agent = CrewAIAgent(
            role=config.get("role", "助手"),
            goal=config.get("goal", "帮助用户"),
            backstory=config.get("backstory", "你是一个有用的助手"),
            llm=config.get("model", "claude-sonnet-4-6"),
            tools=self._adapt_tools(self._tools)
        )
        return agent
```

---

## 6. 迁移路径

### 阶段 1: 立即实施
1. 创建 `core/agent/interface.py` - 定义抽象接口
2. 重构当前代码为 `core/agent/simple/agent.py`
3. 创建 `core/agent/factory.py` - 工厂模式
4. 修改现有代码使用新接口

### 阶段 2: 稳定期
- 测试 SimpleAgent 实现
- 完善工具注册机制
- 确保事件系统稳定

### 阶段 3: 按需添加适配器
- 需要 LangGraph 功能时 → 实现 LangGraphAdapter
- 需要多 Agent 协作时 → 实现 CrewAIAdapter
- 需要 AutoGen 功能时 → 实现 AutoGenAdapter

---

## 7. 收益总结

| 方面 | 当前 | 重构后 | 收益 |
|------|------|--------|------|
| **代码耦合** | Agent 逻辑分散在各处 | 统一接口 | 易于维护 |
| **测试** | 难以单元测试 | 可 mock 接口 | 100% 可测试 |
| **切换 SDK** | 需要重写大量代码 | 改一行配置 | 零成本切换 |
| **理解成本** | 需要理解所有实现细节 | 只需要理解接口 | 降低门槛 |
| **扩展性** | 难以添加新实现 | 注册新适配器即可 | 插件化 |

---

**核心原则**: 面向接口编程，而不是面向实现编程。
