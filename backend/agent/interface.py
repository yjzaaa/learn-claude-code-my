"""
Agent Abstract Interface - Agent 抽象接口

定义所有 Agent 实现必须遵守的契约。

设计原则:
- 接口最小化：只定义最核心的方法
- 实现无关：不涉及任何具体 SDK 的细节
- 异步优先：所有操作都是异步的
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Callable, Any, Optional
from ..types import AgentStatus, AgentMessage, AgentEvent, HookName


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
        context: list[AgentMessage] | None = None,
        system_prompt: str | None = None
    ) -> AsyncIterator[AgentEvent]:
        """
        运行 Agent - 核心方法（流式）

        Yields:
            AgentEvent: 流式事件（文本片段、工具调用、完成等）
        """
        # yield 使此方法成为 async generator，与子类实现类型一致
        yield  # type: ignore[misc]
    
    async def run_sync(
        self,
        user_input: str,
        context: Optional[list[AgentMessage]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        同步运行（非流式）- 默认实现
        
        子类可以覆盖此方法以提供更高效的实现
        """
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
        schema: dict | None = None
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


class AgentLifecycleHooks(ABC):
    """
    Agent 生命周期钩子接口
    
    用于监控和介入 Agent 执行过程
    """
    
    @abstractmethod
    def on_hook(self, hook: HookName, **payload: Any) -> None:
        """
        钩子回调
        
        Args:
            hook: 钩子名称
            **payload: 钩子参数
        """
        pass


__all__ = ["AgentInterface", "AgentLifecycleHooks"]
