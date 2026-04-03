"""
工具管理相关功能的 Mixin
"""

from typing import Callable, Any
from pathlib import Path

from core.models.tool import ToolInfo
from core.models.types import JSONSchema
from core.tools import WorkspaceOps
from .base import EngineMixinBase


class ToolMixin(EngineMixinBase):
    """工具管理功能"""

    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str,
        parameters: JSONSchema | None = None
    ):
        """
        注册工具

        Args:
            name: 工具名称
            handler: 处理函数
            description: 描述
            parameters: 参数定义
        """
        self._tool_mgr.register(name, handler, description, parameters)

    def list_tools(self) -> list[ToolInfo]:
        """
        列出可用工具

        Returns:
            工具信息列表
        """
        return self._tool_mgr.list_available()

    def setup_workspace_tools(self, workdir: Any):
        """
        快速设置工作区工具

        Args:
            workdir: 工作目录路径
        """
        workspace = WorkspaceOps(Path(workdir))

        for tool_fn in workspace.get_tools():
            spec = getattr(tool_fn, "__tool_spec__", {})
            self.register_tool(
                name=spec.get("name", getattr(tool_fn, "__name__", "")),
                handler=tool_fn,
                description=spec.get("description", ""),
                parameters=spec.get("parameters", {})
            )

    @property
    def tool_manager(self) -> "Any":
        """工具管理器 (高级用例)"""
        return self._tool_mgr
