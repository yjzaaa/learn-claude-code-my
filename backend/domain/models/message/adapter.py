"""
消息适配器 - 序列化和旧格式迁移

提供消息转换工具和向后兼容支持。
"""

from typing import Any

from langchain_core.messages import (
    BaseMessage,
    message_to_dict,
    messages_from_dict,
)
from pydantic import BaseModel, Field


class LangChainMessageData(BaseModel):
    """LangChain 消息数据模型"""

    content: str
    additional_kwargs: dict[str, Any] = Field(default_factory=dict)
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class LangChainMessage(BaseModel):
    """LangChain 标准格式消息模型"""

    type: str
    data: LangChainMessageData


class MessageAdapter:
    """消息适配器 - 序列化和反序列化"""

    @staticmethod
    def to_dict(message: BaseMessage) -> dict[str, Any]:
        """
        将消息序列化为 LangChain 标准格式

        Args:
            message: BaseMessage 子类实例

        Returns:
            LangChain 标准格式字典
        """
        return message_to_dict(message)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> BaseMessage:
        """
        从 LangChain 标准格式反序列化消息

        Args:
            data: LangChain 格式字典

        Returns:
            BaseMessage 子类实例
        """
        return messages_from_dict([data])[0]

    @staticmethod
    def to_dict_list(messages: list[BaseMessage]) -> list[dict[str, Any]]:
        """批量序列化消息列表"""
        return [message_to_dict(m) for m in messages]

    @staticmethod
    def from_dict_list(data_list: list[dict[str, Any]]) -> list[BaseMessage]:
        """批量反序列化消息列表"""
        if not data_list:
            return []
        return messages_from_dict(data_list)


class LegacyMessageAdapter:
    """旧格式消息适配器 - 用于迁移"""

    # 角色映射表
    ROLE_MAP: dict[str, str] = {
        "user": "human",
        "assistant": "ai",
        "system": "system",
        "tool": "tool",
    }

    @staticmethod
    def is_legacy_format(data: dict[str, Any]) -> bool:
        """检测是否为旧格式消息

        旧格式: {"role": "user", "content": "..."}
        新格式: {"type": "human", "data": {"content": "..."}}
        """
        return "role" in data and "type" not in data

    @staticmethod
    def convert_legacy_to_langchain(data: dict[str, Any]) -> dict[str, Any]:
        """
        将旧格式消息转换为 LangChain 标准格式

        旧格式:
            {"role": "user", "content": "...", "id": "..."}

        新格式:
            {"type": "human", "data": {"content": "...", "additional_kwargs": {...}}}
        """
        role = data.get("role", "")
        content = data.get("content", "")

        # 角色映射
        msg_type = LegacyMessageAdapter.ROLE_MAP.get(role, "human")

        # 构建 additional_kwargs
        additional_kwargs: dict[str, Any] = {}

        if "id" in data:
            additional_kwargs["id"] = data["id"]
        if "created_at" in data:
            additional_kwargs["created_at"] = data["created_at"]
        if "metadata" in data:
            additional_kwargs["metadata"] = data["metadata"]
        if "agent_name" in data:
            additional_kwargs["agent_name"] = data["agent_name"]
        if "status" in data:
            additional_kwargs["status"] = data["status"]

        # 构建消息数据
        msg_data = LangChainMessageData(
            content=content, additional_kwargs=additional_kwargs if additional_kwargs else {}
        )

        # 工具调用特殊处理
        if msg_type == "tool":
            msg_data.tool_call_id = data.get("tool_call_id", "")
            if "name" in data:
                msg_data.additional_kwargs["tool_name"] = data["name"]

        # 工具调用列表
        if "tool_calls" in data and data["tool_calls"]:
            msg_data.tool_calls = data["tool_calls"]

        # 构建最终结果
        result = LangChainMessage(type=msg_type, data=msg_data)

        return result.model_dump()

    @staticmethod
    def convert_list_legacy_to_langchain(data_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """批量转换旧格式消息列表"""
        return [
            LegacyMessageAdapter.convert_legacy_to_langchain(d)
            if LegacyMessageAdapter.is_legacy_format(d)
            else d
            for d in data_list
        ]


__all__ = [
    "MessageAdapter",
    "LegacyMessageAdapter",
    "LangChainMessage",
    "LangChainMessageData",
]
