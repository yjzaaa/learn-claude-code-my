"""
Tool Registry - 工具注册表

管理工具的注册、注销和执行。
"""

from collections.abc import Callable

from backend.domain.models.shared.types import (
    JSONSchema,
    OpenAIFunctionSchema,
    OpenAIToolSchema,
    ToolSpec,
)


class ToolRegistry:
    """
    工具注册表

    管理工具的生命周期：注册、获取、注销、执行
    """

    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}  # name -> tool_info
        self._handlers: dict[str, Callable] = {}  # name -> handler

    def register(
        self, name: str, handler: Callable, description: str, schema: JSONSchema | None = None
    ) -> None:
        """
        注册工具

        Args:
            name: 工具名称
            handler: 处理函数
            description: 工具描述
            schema: JSON Schema 参数定义
        """
        self._tools[name] = ToolSpec(
            name=name,
            description=description,
            parameters=schema or JSONSchema(type="object", properties={}, required=[]),
        )
        self._handlers[name] = handler

    def unregister(self, name: str) -> bool:
        """注销工具，返回是否成功"""
        if name in self._tools:
            del self._tools[name]
            del self._handlers[name]
            return True
        return False

    def get(self, name: str) -> ToolSpec | None:
        """获取工具信息"""
        return self._tools.get(name)

    def get_handler(self, name: str) -> Callable | None:
        """获取工具处理函数"""
        return self._handlers.get(name)

    def has(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools

    def list_tools(self) -> list[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())

    def get_schemas(self) -> list[OpenAIToolSchema]:
        """
        获取所有工具的 OpenAI 格式 Schema

        Returns:
            list[OpenAIToolSchema]: OpenAI tools 格式列表
        """
        return [
            OpenAIToolSchema(
                type="function",
                function=OpenAIFunctionSchema(
                    name=info["name"],
                    description=info["description"],
                    parameters=info["parameters"],
                ),
            )
            for info in self._tools.values()
        ]

    async def execute(self, name: str, arguments: dict) -> str:
        """
        执行工具

        Args:
            name: 工具名称
            arguments: 参数

        Returns:
            工具执行结果字符串
        """
        handler = self._handlers.get(name)
        if not handler:
            return f"Error: Unknown tool: {name}"

        try:
            import asyncio

            result = handler(**arguments)

            # 如果结果是协程，等待它
            if asyncio.iscoroutine(result):
                result = await result

            return str(result)
        except Exception as e:
            return f"Error executing {name}: {str(e)}"

    def clear(self) -> None:
        """清空所有工具"""
        self._tools.clear()
        self._handlers.clear()

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
