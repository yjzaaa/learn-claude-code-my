"""
Agents Models Package - OpenAI 原生风格

所有类型与 OpenAI API 完全兼容。
参考: https://platform.openai.com/docs/api-reference/chat
"""

from .openai_types import (
    # 基础类型
    ChatRole,
    ChatMessage,
    ChatCompletionMessageToolCall,
    # 工具
    ChatCompletionTool,
    # 流式响应
    ChatCompletionChunk,
    # 会话
    ChatSession,
    # 事件
    ChatEvent,
)

__all__ = [
    # 基础类型
    "ChatRole",
    "ChatMessage",
    "ChatCompletionMessageToolCall",
    # 工具
    "ChatCompletionTool",
    # 流式响应
    "ChatCompletionChunk",
    # 会话
    "ChatSession",
    # 事件
    "ChatEvent",
]
