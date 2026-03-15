"""Agents Core Package

Provides core types and tools for agent development.

Key Components:
- AgentBuilder: Fluent API for assembling agents with plugins
- Message types: SystemMessage, HumanMessage, AIMessage, ToolMessage

AgentBuilder Example:
    from agents.core import AgentBuilder
    from agents.plugins import TodoPlugin, TaskPlugin

    # Build agent with selected plugins
    agent = (
        AgentBuilder()
        .with_base_tools()
        .with_plugin(TodoPlugin())
        .with_plugin(TaskPlugin())
        .with_system("Custom system prompt")
        .with_monitoring(dialog_id="dlg-123")
        .build()
    )

    # Use predefined configurations
    simple_agent = AgentBuilder.simple_agent().build()
    todo_agent = AgentBuilder.todo_agent().build()
    full_agent = AgentBuilder.full_agent().build()
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

# AgentBuilder for modular agent construction
from .builder import AgentBuilder

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
    # Builder
    "AgentBuilder",
]