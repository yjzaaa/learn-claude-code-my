"""
OpenAI 原生风格数据模型 (Pydantic 版本)

与 OpenAI API 完全兼容的消息格式，用于前后端通信。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# 基础类型
# ============================================================================

ChatRole = Literal["system", "user", "assistant", "tool"]


class FunctionCall(BaseModel):
    """函数调用定义"""
    name: str
    arguments: str  # JSON 字符串


class ChatCompletionMessageToolCall(BaseModel):
    """工具调用定义 - OpenAI 标准格式"""
    id: str
    type: Literal["function"] = "function"
    function: FunctionCall

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatCompletionMessageToolCall":
        """从字典创建"""
        func_data = data.get("function", {})
        return cls(
            id=data.get("id", ""),
            type=data.get("type", "function"),
            function=FunctionCall(
                name=func_data.get("name", ""),
                arguments=func_data.get("arguments", "")
            )
        )


class ChatMessage(BaseModel):
    """
    聊天消息 - OpenAI 原生格式
    """
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    role: ChatRole = "user"
    content: Optional[str] = None
    reasoning_content: Optional[str] = None
    tool_calls: Optional[list[ChatCompletionMessageToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

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

class ChatCompletionToolFunction(BaseModel):
    """工具函数定义"""
    name: str
    description: str
    parameters: dict[str, Any]


class ChatCompletionTool(BaseModel):
    """工具定义 - OpenAI 函数调用格式"""
    type: Literal["function"] = "function"
    function: ChatCompletionToolFunction


# ============================================================================
# 流式响应
# ============================================================================

class DeltaContent(BaseModel):
    """增量内容"""
    content: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None


class ChatCompletionChunkChoice(BaseModel):
    """流式响应选择"""
    index: int
    delta: DeltaContent
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    """流式响应块 - OpenAI 流式格式"""
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str = ""
    choices: list[ChatCompletionChunkChoice] = Field(default_factory=list)

    @classmethod
    def delta_content(cls, content: str, model: str = "", index: int = 0) -> "ChatCompletionChunk":
        """创建内容增量块"""
        return cls(
            id=f"chatcmpl-{uuid4().hex[:8]}",
            model=model,
            choices=[ChatCompletionChunkChoice(
                index=index,
                delta=DeltaContent(content=content),
                finish_reason=None
            )]
        )

    @classmethod
    def done(cls, model: str = "") -> "ChatCompletionChunk":
        """创建完成信号块"""
        return cls(
            id=f"chatcmpl-{uuid4().hex[:8]}",
            model=model,
            choices=[ChatCompletionChunkChoice(
                index=0,
                delta=DeltaContent(),
                finish_reason="stop"
            )]
        )


# ============================================================================
# 对话会话
# ============================================================================

class ChatSession(BaseModel):
    """
    对话会话 - OpenAI 风格
    """
    id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    model: str = "gpt-4o"
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    updated_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))

    def add_message(self, message: ChatMessage) -> "ChatSession":
        """添加消息并更新时间戳"""
        self.messages.append(message)
        self.updated_at = int(datetime.now().timestamp())
        return self

    def get_messages_for_api(self) -> list[dict[str, Any]]:
        """获取用于 API 调用的消息列表"""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                **({"tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in msg.tool_calls
                ]} if msg.tool_calls else {}),
                **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {}),
                **({"name": msg.name} if msg.name else {}),
            }
            for msg in self.messages
        ]


# ============================================================================
# WebSocket 事件 (基于 OpenAI 格式)
# ============================================================================

class ChatEvent(BaseModel):
    """
    WebSocket 事件 - 基于 OpenAI 格式的通信协议
    """
    model_config = ConfigDict(use_enum_values=True)

    type: Literal[
        "message",
        "delta",
        "tool_call",
        "tool_result",
        "error",
        "system",
        "dialog:snapshot",
        "status:change",
    ]
    dialog_id: str
    message: Optional[ChatMessage] = None
    data: Optional[dict[str, Any]] = None
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp()))

    @classmethod
    def snapshot(cls, dialog_id: str, data: dict[str, Any]) -> "ChatEvent":
        """创建对话框快照事件"""
        return cls(
            type="dialog:snapshot",
            dialog_id=dialog_id,
            data=data
        )

    @classmethod
    def status_change(cls, dialog_id: str, status: str) -> "ChatEvent":
        """创建状态变更事件"""
        return cls(
            type="status:change",
            dialog_id=dialog_id,
            data={"status": status}
        )


# ============================================================================
# API 请求/响应模型
# ============================================================================

class ChatCompletionRequest(BaseModel):
    """聊天完成请求"""
    model: str
    messages: list[dict[str, Any]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    tools: Optional[list[ChatCompletionTool]] = None
    stream: bool = False


class ChatCompletionResponseChoice(BaseModel):
    """聊天完成响应选择"""
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    """聊天完成响应"""
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str
    choices: list[ChatCompletionResponseChoice]
    usage: Optional[dict[str, int]] = None


# ============================================================================
# 导出列表
# ============================================================================

__all__ = [
    # 基础类型
    "ChatRole",
    "ChatMessage",
    "FunctionCall",
    "ChatCompletionMessageToolCall",
    # 工具
    "ChatCompletionTool",
    "ChatCompletionToolFunction",
    # 流式响应
    "ChatCompletionChunk",
    "ChatCompletionChunkChoice",
    "DeltaContent",
    # 会话
    "ChatSession",
    # 事件
    "ChatEvent",
    # API 模型
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatCompletionResponseChoice",
]
