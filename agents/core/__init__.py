"""
Agents Core Package

提供 Agent 开发所需的核心类型和工具。
"""

from .messages import (
    # LangChain 消息类型
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    FunctionMessage,
    # 联合类型
    Message,
    BaseMessage,
)

__all__ = [
    # 消息类型
    "SystemMessage",
    "HumanMessage",
    "AIMessage",
    "ToolMessage",
    "FunctionMessage",
    # 联合类型
    "Message",
    "BaseMessage",
]