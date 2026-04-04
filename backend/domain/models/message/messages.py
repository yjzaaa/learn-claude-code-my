"""
自定义消息模型 - 继承 LangChain 基础类

提供带有业务字段扩展的自定义消息类。
业务字段（id, created_at, metadata）通过 additional_kwargs 存储，
确保与 LangChain 序列化机制兼容。
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)


def _generate_id(prefix: str = "msg") -> str:
    """生成唯一ID"""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class CustomHumanMessage(HumanMessage):
    """
    自定义用户消息 - 继承 LangChain HumanMessage

    业务字段:
        - id: 消息唯一标识
        - created_at: 创建时间 ISO 格式
        - metadata: 自定义元数据字典
    """

    def __init__(
        self,
        content: str,
        msg_id: Optional[str] = None,
        created_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(content=content, **kwargs)

        # 业务字段存储在 additional_kwargs 中
        self.additional_kwargs["id"] = msg_id or _generate_id("msg")
        self.additional_kwargs["created_at"] = created_at or datetime.now().isoformat()
        if metadata:
            self.additional_kwargs["metadata"] = metadata

    @property
    def msg_id(self) -> str:
        """消息ID"""
        return self.additional_kwargs.get("id", "")

    @property
    def created_at(self) -> str:
        """创建时间"""
        return self.additional_kwargs.get("created_at", "")

    @property
    def metadata(self) -> Dict[str, Any]:
        """元数据"""
        return self.additional_kwargs.get("metadata", {})

    def __repr__(self) -> str:
        return (
            f"CustomHumanMessage("
            f"id={self.msg_id!r}, "
            f"content={self.content[:50]!r}..."
            f")"
        )


class CustomAIMessage(AIMessage):
    """
    自定义助手消息 - 继承 LangChain AIMessage

    业务字段:
        - id: 消息唯一标识
        - created_at: 创建时间 ISO 格式
        - metadata: 自定义元数据字典
        - agent_name: Agent 名称
        - status: 消息状态 (streaming, completed, error)
    """

    def __init__(
        self,
        content: str,
        msg_id: Optional[str] = None,
        created_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        agent_name: Optional[str] = None,
        status: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(content=content, tool_calls=tool_calls or [], **kwargs)

        # 业务字段存储在 additional_kwargs 中
        self.additional_kwargs["id"] = msg_id or _generate_id("msg")
        self.additional_kwargs["created_at"] = created_at or datetime.now().isoformat()
        if metadata:
            self.additional_kwargs["metadata"] = metadata
        if agent_name:
            self.additional_kwargs["agent_name"] = agent_name
        if status:
            self.additional_kwargs["status"] = status

    @property
    def msg_id(self) -> str:
        """消息ID"""
        return self.additional_kwargs.get("id", "")

    @property
    def created_at(self) -> str:
        """创建时间"""
        return self.additional_kwargs.get("created_at", "")

    @property
    def metadata(self) -> Dict[str, Any]:
        """元数据"""
        return self.additional_kwargs.get("metadata", {})

    @property
    def agent_name(self) -> str:
        """Agent 名称"""
        return self.additional_kwargs.get("agent_name", "")

    @property
    def status(self) -> str:
        """消息状态"""
        return self.additional_kwargs.get("status", "completed")

    def __repr__(self) -> str:
        tool_count = len(self.tool_calls) if self.tool_calls else 0
        return (
            f"CustomAIMessage("
            f"id={self.msg_id!r}, "
            f"content={self.content[:50]!r}..., "
            f"tool_calls={tool_count}"
            f")"
        )


class CustomSystemMessage(SystemMessage):
    """
    自定义系统消息 - 继承 LangChain SystemMessage

    业务字段:
        - id: 消息唯一标识
        - created_at: 创建时间 ISO 格式
        - metadata: 自定义元数据字典
    """

    def __init__(
        self,
        content: str,
        msg_id: Optional[str] = None,
        created_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(content=content, **kwargs)

        # 业务字段存储在 additional_kwargs 中
        self.additional_kwargs["id"] = msg_id or _generate_id("msg")
        self.additional_kwargs["created_at"] = created_at or datetime.now().isoformat()
        if metadata:
            self.additional_kwargs["metadata"] = metadata

    @property
    def msg_id(self) -> str:
        """消息ID"""
        return self.additional_kwargs.get("id", "")

    @property
    def created_at(self) -> str:
        """创建时间"""
        return self.additional_kwargs.get("created_at", "")

    @property
    def metadata(self) -> Dict[str, Any]:
        """元数据"""
        return self.additional_kwargs.get("metadata", {})

    def __repr__(self) -> str:
        return (
            f"CustomSystemMessage("
            f"id={self.msg_id!r}, "
            f"content={self.content[:50]!r}..."
            f")"
        )


class CustomToolMessage(ToolMessage):
    """
    自定义工具消息 - 继承 LangChain ToolMessage

    业务字段:
        - id: 消息唯一标识
        - created_at: 创建时间 ISO 格式
        - metadata: 自定义元数据字典
        - tool_name: 工具名称（冗余存储便于访问）
        - duration_ms: 工具执行耗时
    """

    def __init__(
        self,
        content: str,
        tool_call_id: str,
        msg_id: Optional[str] = None,
        created_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None,
        duration_ms: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            content=content,
            tool_call_id=tool_call_id,
            **kwargs
        )

        # 业务字段存储在 additional_kwargs 中
        self.additional_kwargs["id"] = msg_id or _generate_id("msg")
        self.additional_kwargs["created_at"] = created_at or datetime.now().isoformat()
        if metadata:
            self.additional_kwargs["metadata"] = metadata
        if tool_name:
            self.additional_kwargs["tool_name"] = tool_name
        if duration_ms is not None:
            self.additional_kwargs["duration_ms"] = duration_ms

    @property
    def msg_id(self) -> str:
        """消息ID"""
        return self.additional_kwargs.get("id", "")

    @property
    def created_at(self) -> str:
        """创建时间"""
        return self.additional_kwargs.get("created_at", "")

    @property
    def metadata(self) -> Dict[str, Any]:
        """元数据"""
        return self.additional_kwargs.get("metadata", {})

    @property
    def tool_name(self) -> str:
        """工具名称"""
        return self.additional_kwargs.get("tool_name", "")

    @property
    def duration_ms(self) -> Optional[int]:
        """执行耗时（毫秒）"""
        return self.additional_kwargs.get("duration_ms")

    def __repr__(self) -> str:
        return (
            f"CustomToolMessage("
            f"id={self.msg_id!r}, "
            f"tool_call_id={self.tool_call_id!r}, "
            f"tool_name={self.tool_name!r}, "
            f"content={self.content[:50]!r}..."
            f")"
        )


# ═══════════════════════════════════════════════════════════
# 工厂方法
# ═══════════════════════════════════════════════════════════

def create_human(content: str, **kwargs) -> CustomHumanMessage:
    """创建用户消息"""
    return CustomHumanMessage(content=content, **kwargs)


def create_ai(content: str, **kwargs) -> CustomAIMessage:
    """创建助手消息"""
    return CustomAIMessage(content=content, **kwargs)


def create_system(content: str, **kwargs) -> CustomSystemMessage:
    """创建系统消息"""
    return CustomSystemMessage(content=content, **kwargs)


def create_tool(
    content: str,
    tool_call_id: str,
    **kwargs
) -> CustomToolMessage:
    """创建工具消息"""
    return CustomToolMessage(
        content=content,
        tool_call_id=tool_call_id,
        **kwargs
    )


# ═══════════════════════════════════════════════════════════
# 导出
# ═══════════════════════════════════════════════════════════

__all__ = [
    # 自定义消息类
    "CustomHumanMessage",
    "CustomAIMessage",
    "CustomSystemMessage",
    "CustomToolMessage",
    # 工厂方法
    "create_human",
    "create_ai",
    "create_system",
    "create_tool",
    # 辅助函数
    "_generate_id",
]
