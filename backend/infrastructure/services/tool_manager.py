"""
Tool Manager - 工具管理器

管理工具的注册、执行和生命周期。
与 core.tools.ToolRegistry 集成。
"""

from typing import Optional, Callable, TYPE_CHECKING
import asyncio

from backend.infrastructure.tools import ToolRegistry
from backend.infrastructure.tools.workspace import WorkspaceOps
from backend.infrastructure.logging import get_logger
from backend.domain.models.agent.tool_call import ToolCall
from backend.domain.models.events.base import ToolCallStarted, ToolCallCompleted, ToolCallFailed
from backend.domain.models.shared.config import ToolManagerConfig
from backend.domain.models.agent.tool import ToolInfo
from backend.domain.models.shared.types import JSONSchema, OpenAIToolSchema, ToolSpec

if TYPE_CHECKING:
    from backend.infrastructure.event_bus import EventBus

logger = get_logger(__name__)


class ToolManager:
    """
    工具管理器
    
    职责:
    - 注册和管理工具
    - 执行工具调用
    - 通过事件总线通知调用状态
    
    依赖:
    - EventBus: 发送工具事件
    - WorkspaceOps: 内置工具 (可选)
    """
    
    def __init__(
        self,
        event_bus: 'EventBus',
        workspace_ops: Optional[WorkspaceOps] = None,
        config: Optional[ToolManagerConfig] = None
    ):
        self._event_bus = event_bus
        self._config = config or ToolManagerConfig()
        
        # 工具注册表
        self._registry = ToolRegistry()
        
        # 注册内置工具
        if workspace_ops:
            self._register_builtin_tools(workspace_ops)
    
    def _register_builtin_tools(self, workspace: WorkspaceOps):
        """注册内置工具"""
        for tool_fn in workspace.get_tools():
            spec = getattr(tool_fn, "__tool_spec__", {})
            self.register(
                name=spec.get("name", getattr(tool_fn, "__name__", "")),
                handler=tool_fn,
                description=spec.get("description", ""),
                parameters=spec.get("parameters", {})
            )
        logger.info(f"[ToolManager] Registered {len(workspace.get_tools())} built-in tools")
    
    def register(
        self,
        name: str,
        handler: Callable,
        description: str,
        parameters: Optional[JSONSchema] = None
    ):
        """
        注册工具
        
        Args:
            name: 工具名称
            handler: 处理函数
            description: 描述
            parameters: 参数定义 (JSON Schema)
        """
        self._registry.register(name, handler, description, parameters)
        logger.debug(f"[ToolManager] Registered tool: {name}")
    
    def unregister(self, name: str) -> bool:
        """
        注销工具
        
        Args:
            name: 工具名称
            
        Returns:
            是否成功注销
        """
        return self._registry.unregister(name)
    
    def get_tool(self, name: str) -> Optional[ToolSpec]:
        """
        获取工具信息
        
        Args:
            name: 工具名称
            
        Returns:
            工具信息或 None
        """
        return self._registry.get(name)
    
    def list_available(self) -> list[ToolInfo]:
        """
        列出可用工具

        Returns:
            工具信息列表
        """
        return [
            ToolInfo(
                name=info["name"],
                description=info["description"],
                parameters=info["parameters"],
            )
            for info in self._registry._tools.values()
        ]
    
    def get_schemas(self) -> list[OpenAIToolSchema]:
        """
        获取 OpenAI 格式的工具 schemas
        
        Returns:
            OpenAI tools 格式列表
        """
        return self._registry.get_schemas()
    
    async def execute(
        self,
        dialog_id: str,
        tool_call: ToolCall
    ) -> str:
        """
        执行工具调用
        
        Args:
            dialog_id: 对话 ID
            tool_call: 工具调用对象
            
        Returns:
            工具执行结果
        """
        # 发射开始事件
        self._event_bus.emit(ToolCallStarted(
            dialog_id=dialog_id,
            tool_call_id=tool_call.id,
            tool_name=tool_call.name,
            arguments=tool_call.arguments
        ))
        
        try:
            # 执行工具
            result = await self._registry.execute(
                tool_call.name,
                tool_call.arguments
            )
            
            # 完成
            tool_call.complete(result)
            
            # 发射完成事件
            self._event_bus.emit(ToolCallCompleted(
                dialog_id=dialog_id,
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                result=result,
                duration_ms=tool_call.duration_ms or 0
            ))
            
            logger.info(f"[ToolManager] Executed {tool_call.name} in {tool_call.duration_ms}ms")
            return result
            
        except Exception as e:
            error_msg = str(e)
            tool_call.fail(error_msg)
            
            # 发射失败事件
            self._event_bus.emit(ToolCallFailed(
                dialog_id=dialog_id,
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                error=error_msg
            ))
            
            logger.error(f"[ToolManager] Failed to execute {tool_call.name}: {error_msg}")
            return f"Error: {error_msg}"
    
    def has_tool(self, name: str) -> bool:
        """检查工具是否存在"""
        return self._registry.has(name)
    
    def clear(self):
        """清空所有工具 (除内置工具)"""
        # 保留内置工具，只清除自定义工具
        # 实际实现可能需要标记哪些工具是内置的
        self._registry.clear()
