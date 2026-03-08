"""
OpenAI 原生风格数据模型

与 OpenAI API 完全兼容的消息格式，用于前后端通信。
参考: https://platform.openai.com/docs/api-reference/chat
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional
from datetime import datetime
import uuid
import json


# ============================================================================
# 基础类型
# ============================================================================

ChatRole = Literal["system", "user", "assistant", "tool"]


@dataclass
class ChatCompletionMessageToolCall:
    """工具调用定义 - OpenAI 标准格式"""
    id: str
    type: Literal["function"] = "function"
    function: dict[str, str] = field(default_factory=dict)  # {"name": str, "arguments": str}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "function": self.function
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatCompletionMessageToolCall":
        return cls(
            id=data.get("id", ""),
            type=data.get("type", "function"),
            function=data.get("function", {})
        )


@dataclass
class ChatMessage:
    """
    聊天消息 - OpenAI 原生格式

    字段:
        id: 消息唯一标识符
        role: 消息角色 (system/user/assistant/tool)
        content: 消息内容 (文本或多模态内容)
        tool_calls: 工具调用列表 (仅 assistant 角色)
        tool_call_id: 工具调用ID (仅 tool 角色)
        name: 工具名称 (仅 tool 角色)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: ChatRole = "user"
    content: Optional[str] = None
    tool_calls: Optional[list[ChatCompletionMessageToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """转换为 OpenAI API 格式"""
        result: dict[str, Any] = {
            "id": self.id,
            "role": self.role,
        }

        if self.content is not None:
            result["content"] = self.content

        if self.tool_calls is not None:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]

        if self.tool_call_id is not None:
            result["tool_call_id"] = self.tool_call_id

        if self.name is not None:
            result["name"] = self.name

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatMessage":
        """从 OpenAI API 格式创建"""
        tool_calls = None
        if "tool_calls" in data:
            tool_calls = [
                ChatCompletionMessageToolCall.from_dict(tc)
                for tc in data["tool_calls"]
            ]

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            role=data.get("role", "user"),
            content=data.get("content"),
            tool_calls=tool_calls,
            tool_call_id=data.get("tool_call_id"),
            name=data.get("name")
        )

    @classmethod
    def user(cls, content: str) -> "ChatMessage":
        """工厂方法：创建用户消息"""
        return cls(role="user", content=content)

    @classmethod
    def assistant(cls, content: str) -> "ChatMessage":
        """工厂方法：创建助手消息"""
        return cls(role="assistant", content=content)

    @classmethod
    def system(cls, content: str) -> "ChatMessage":
        """工厂方法：创建系统消息"""
        return cls(role="system", content=content)

    @classmethod
    def tool(cls, content: str, tool_call_id: str, name: str = "") -> "ChatMessage":
        """工厂方法：创建工具结果消息"""
        return cls(
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
            name=name
        )

    @classmethod
    def tool_call(cls, tool_calls: list[ChatCompletionMessageToolCall]) -> "ChatMessage":
        """工厂方法：创建工具调用消息"""
        return cls(role="assistant", tool_calls=tool_calls)


# ============================================================================
# 工具定义
# ============================================================================

@dataclass
class ChatCompletionTool:
    """工具定义 - OpenAI 函数调用格式"""
    type: Literal["function"] = "function"
    function: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "function": self.function
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatCompletionTool":
        return cls(
            type=data.get("type", "function"),
            function=data.get("function", {})
        )


# ============================================================================
# 流式响应
# ============================================================================

@dataclass
class ChatCompletionChunk:
    """流式响应块 - OpenAI 流式格式"""
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str = ""
    choices: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "choices": self.choices
        }

    @classmethod
    def delta_content(cls, content: str, model: str = "", index: int = 0) -> "ChatCompletionChunk":
        """创建内容增量块"""
        return cls(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            model=model,
            choices=[{
                "index": index,
                "delta": {"content": content},
                "finish_reason": None
            }]
        )

    @classmethod
    def delta_tool_call(
        cls,
        tool_call: ChatCompletionMessageToolCall,
        model: str = "",
        index: int = 0
    ) -> "ChatCompletionChunk":
        """创建工具调用增量块"""
        return cls(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            model=model,
            choices=[{
                "index": index,
                "delta": {"tool_calls": [tool_call.to_dict()]},
                "finish_reason": None
            }]
        )

    @classmethod
    def done(cls, model: str = "") -> "ChatCompletionChunk":
        """创建完成信号块"""
        return cls(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            model=model,
            choices=[{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        )


# ============================================================================
# 对话会话
# ============================================================================

@dataclass
class ChatSession:
    """
    对话会话 - OpenAI 风格

    包含消息历史和其他元数据
    """
    id: str
    messages: list[ChatMessage] = field(default_factory=list)
    model: str = "gpt-4o"
    created_at: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    updated_at: int = field(default_factory=lambda: int(datetime.now().timestamp()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "messages": [m.to_dict() for m in self.messages],
            "model": self.model,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def add_message(self, message: ChatMessage) -> None:
        """添加消息并更新时间戳"""
        self.messages.append(message)
        self.updated_at = int(datetime.now().timestamp())

    def get_messages_for_api(self) -> list[dict[str, Any]]:
        """获取用于 API 调用的消息列表"""
        return [m.to_dict() for m in self.messages]


# ============================================================================
# WebSocket 事件 (基于 OpenAI 格式)
# ============================================================================

@dataclass
class ChatEvent:
    """
    WebSocket 事件 - 基于 OpenAI 格式的通信协议

    所有事件都包含一个 OpenAI 标准消息格式
    """
    type: Literal[
        "message",           # 新消息
        "delta",             # 流式增量
        "tool_call",         # 工具调用
        "tool_result",       # 工具结果
        "error",             # 错误
        "system"             # 系统事件
    ]
    dialog_id: str
    message: ChatMessage
    timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "dialog_id": self.dialog_id,
            "message": self.message.to_dict(),
            "timestamp": self.timestamp
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatEvent":
        """从字典创建"""
        return cls(
            type=data.get("type", "message"),
            dialog_id=data.get("dialog_id", ""),
            message=ChatMessage.from_dict(data.get("message", {})),
            timestamp=data.get("timestamp", int(datetime.now().timestamp()))
        )


# ============================================================================
# 导出列表
# ============================================================================

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
