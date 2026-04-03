"""
Tool Adapter - 工具格式适配器

将内部工具格式转换为 LangChain Tool 格式。
"""
from langchain.tools import tool as langchain_tool
from core.agent.runtimes.base import ToolCache


class ToolAdapter:
    """工具格式适配器"""

    @staticmethod
    def adapt(tools: dict[str, ToolCache]) -> list:
        """
        将内部工具格式转换为 LangChain Tool 格式

        Args:
            tools: 工具字典 {name: ToolCache}

        Returns:
            LangChain Tool 列表
        """
        adapted = []

        for name, tool_info in tools.items():
            handler = tool_info.handler
            description = tool_info.description

            @langchain_tool(name=name, description=description)  # type: ignore[call-overload]
            def adapted_tool(**kwargs):
                return handler(**kwargs)

            adapted.append(adapted_tool)

        return adapted
