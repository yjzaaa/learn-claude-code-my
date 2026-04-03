# Runtime Base Class Technical Specification

## 接口规范

### AbstractAgentRuntime[ConfigT]

```python
class AbstractAgentRuntime(AgentRuntime, Generic[ConfigT], ABC):
    """
    抽象基类提供 Runtime 的通用实现。

    Type Parameters:
        ConfigT: 配置类型，必须是 BaseModel 子类
                 (EngineConfig, DeepAgentConfig, etc.)
    """

    def __init__(self, agent_id: str) -> None
        """初始化基类属性"""

    @property
    def runtime_id(self) -> str
        """运行时唯一标识"""

    @property
    @abstractmethod
    def agent_type(self) -> str
        """Agent 类型标识 (simple/deep)"""

    @final
    async def initialize(self, config: ConfigT | dict[str, Any]) -> None
        """
        模板方法: 初始化 Runtime

        流程:
        1. 调用 _validate_config() 验证配置
        2. 调用 _do_initialize() 子类特定初始化
        3. 记录初始化日志
        """

    @abstractmethod
    async def _do_initialize(self) -> None
        """子类实现: 特定初始化逻辑"""

    @final
    async def shutdown(self) -> None
        """
        模板方法: 关闭 Runtime

        流程:
        1. 调用 _do_shutdown() 子类特定清理
        2. 记录关闭日志
        """

    @abstractmethod
    async def _do_shutdown(self) -> None
        """子类实现: 特定清理逻辑"""

    @abstractmethod
    async def send_message(
        self,
        dialog_id: str,
        message: str,
        stream: bool = True
    ) -> AsyncIterator[AgentEvent]
        """子类实现: 发送消息并返回流式事件"""

    @final
    async def create_dialog(self, user_input: str, title: Optional[str] = None) -> str
        """通用实现: 创建新对话"""

    @final
    def get_dialog(self, dialog_id: str) -> Optional[Dialog]
        """通用实现: 获取对话"""

    @final
    def list_dialogs(self) -> list[Dialog]
        """通用实现: 列出所有对话"""

    @final
    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str,
        parameters_schema: Optional[dict[str, Any]] = None
    ) -> None
        """通用实现: 注册工具"""

    @final
    def unregister_tool(self, name: str) -> None
        """通用实现: 注销工具"""

    @abstractmethod
    async def stop(self, dialog_id: Optional[str] = None) -> None
        """子类实现: 停止 Agent"""

    def _validate_config(self, config: ConfigT | dict[str, Any]) -> ConfigT
        """配置验证钩子 (可覆盖)"""
```

### ToolCache

```python
class ToolCache(BaseModel):
    """
    工具缓存模型 - 统一 SimpleRuntime 和 DeepRuntime 的工具存储

    Attributes:
        handler: 工具处理函数
        description: 工具描述
        parameters_schema: JSON Schema 参数定义
    """
    handler: Any = None
    description: str = ""
    parameters_schema: dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True
```

## 实现规范

### base.py 文件结构

```python
"""
AbstractAgentRuntime - Runtime 抽象基类

提供 AgentRuntime 的通用实现，使用模板方法模式。
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any, Optional, Callable, AsyncIterator
from pydantic import BaseModel, Field

from core.agent.runtime import AgentRuntime
from core.models.dialog import Dialog
from core.types import AgentEvent

# 类型变量定义
ConfigT = TypeVar("ConfigT", bound=BaseModel)


class ToolCache(BaseModel):
    """工具缓存模型"""
    ...


class AbstractAgentRuntime(AgentRuntime, Generic[ConfigT], ABC):
    """抽象基类"""
    ...
```

### SimpleRuntime 修改

```python
class SimpleRuntime(AbstractAgentRuntime[EngineConfig]):
    """
    Simple Runtime 实现 - 继承抽象基类

    只需实现特定行为:
    - agent_type 属性
    - _do_initialize() - 初始化 6 Managers
    - _do_shutdown() - 保存状态
    - send_message() - LLM 循环
    - stop() - 停止 Agent
    """

    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        # 特定初始化
        self._event_bus = EventBus()
        self._state_mgr = StateManager()
        ...
```

### DeepAgentRuntime 修改

```python
class DeepAgentRuntime(AbstractAgentRuntime[DeepAgentConfig]):
    """
    Deep Agent Runtime 实现 - 继承抽象基类

    只需实现特定行为:
    - agent_type 属性
    - _do_initialize() - 创建 deep agent
    - _do_shutdown() - 清理资源
    - send_message() - astream 流式处理
    - stop() - 停止 Agent
    """

    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        # 特定初始化
        self._msg_logger = get_deep_msg_logger()
        ...
```

## 类型安全

### 泛型约束

```python
# 配置类型必须是 BaseModel 子类
ConfigT = TypeVar("ConfigT", bound=BaseModel)

class AbstractAgentRuntime(AgentRuntime, Generic[ConfigT], ABC):
    def __init__(self, agent_id: str):
        self._config: Optional[ConfigT] = None
```

### 子类类型提示

```python
# SimpleRuntime 使用 EngineConfig
class SimpleRuntime(AbstractAgentRuntime[EngineConfig]):
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self._config: Optional[EngineConfig] = None  # 类型收窄

# DeepAgentRuntime 使用 DeepAgentConfig
class DeepAgentRuntime(AbstractAgentRuntime[DeepAgentConfig]):
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self._config: Optional[DeepAgentConfig] = None  # 类型收窄
```

## 测试要求

1. **类型检查**: `mypy core/agent/runtimes/` 无错误
2. **功能测试**: 现有测试全部通过
3. **新基类测试**:
   - ToolCache 序列化/反序列化
   - AbstractAgentRuntime 子类化验证
   - 模板方法调用顺序验证

## 依赖关系

```
base.py
├── core.agent.runtime.AgentRuntime
├── core.models.dialog.Dialog
├── core.types.AgentEvent
└── pydantic.BaseModel

simple_runtime.py
├── AbstractAgentRuntime[EngineConfig]
├── ToolCache
└── 各 Manager 类

deep_runtime.py
├── AbstractAgentRuntime[DeepAgentConfig]
├── ToolCache
└── deepagents 库
```
