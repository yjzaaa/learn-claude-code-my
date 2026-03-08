"""
核心消息类型 - 基于 LangChain

本模块重新导出 LangChain 的消息类型，确保 Agent 层使用标准消息格式。
LangChain 消息是 Agent 层的通用语言，与具体 LLM 提供商无关。

使用示例:
    from agents.core import HumanMessage, AIMessage, ToolMessage

    # 用户消息
    human_msg = HumanMessage(content="Hello")

    # AI 消息
    ai_msg = AIMessage(content="Hi there!")

    # 工具结果
    tool_msg = ToolMessage(content="result", tool_call_id="tc-123")
"""

from __future__ import annotations

from typing import Union

# 从 LangChain 重新导出标准消息类型
from langchain_core.messages import (
    AIMessage as LangChainAIMessage,
    BaseMessage,
    FunctionMessage as LangChainFunctionMessage,
    HumanMessage as LangChainHumanMessage,
    SystemMessage as LangChainSystemMessage,
    ToolMessage as LangChainToolMessage,
)


class SystemMessage(LangChainSystemMessage):
    """系统消息 - 用于设置 AI 的行为和上下文

    示例:
        system_msg = SystemMessage(content="你是一个 helpful assistant")
    """
    pass


class HumanMessage(LangChainHumanMessage):
    """人类/用户消息

    示例:
        human_msg = HumanMessage(content="你好，请帮我查询数据")
    """
    pass


class AIMessage(LangChainAIMessage):
    """AI/助手消息

    可以包含文本回复或工具调用请求。

    示例:
        # 纯文本回复
        ai_msg = AIMessage(content="好的，我来帮您查询")

        # 带工具调用
        ai_msg = AIMessage(
            content="",
            tool_calls=[{
                "id": "tc-123",
                "name": "sql_query",
                "args": {"sql": "SELECT * FROM users"}
            }]
        )
    """
    pass


class ToolMessage(LangChainToolMessage):
    """工具执行结果消息

    用于向 AI 返回工具调用的执行结果。

    示例:
        tool_msg = ToolMessage(
            content='{"count": 42}',
            tool_call_id="tc-123",
            name="sql_query"
        )
    """
    pass


class FunctionMessage(LangChainFunctionMessage):
    """函数调用结果消息 (Legacy, 建议使用 ToolMessage)"""
    pass


class ThinkingMessage(AIMessage):
    """AI 思考过程消息

    用于展示 AI 的推理过程，通常作为子消息附加到父消息。
    继承自 AIMessage，但类型标识为 thinking。

    示例:
        thinking = ThinkingMessage(
            content="让我分析一下这个问题...",
            parent_message_id="msg-parent-123"
        )
    """

    def __init__(self, content: str, parent_message_id: str | None = None, **kwargs):
        super().__init__(content=content, **kwargs)
        self.parent_message_id = parent_message_id


# 联合类型 - 所有消息类型的并集
Message = Union[
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    FunctionMessage,
    ThinkingMessage,
]


__all__ = [
    # 基础类
    "BaseMessage",
    # 具体消息类型
    "SystemMessage",
    "HumanMessage",
    "AIMessage",
    "ToolMessage",
    "FunctionMessage",
    "ThinkingMessage",
    # 联合类型
    "Message",
]