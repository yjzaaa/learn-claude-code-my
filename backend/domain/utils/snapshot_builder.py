"""Snapshot Builder - 对话快照构建器

统一构建对话快照的逻辑，消除 manager.py 和 dialog_service.py 中的重复代码。
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from backend.domain.utils.time_utils import iso_timestamp_now


class SnapshotBuilder:
    """对话快照构建器

    提供统一的方法构建前端所需的对话快照格式。

    Example:
        >>> from backend.domain.utils import SnapshotBuilder
        >>> builder = SnapshotBuilder()
        >>> snapshot = builder.build_from_session(session)
    """

    DEFAULT_AGENT_NAME = "hana"

    @staticmethod
    def build_from_session(session) -> Optional[Dict[str, Any]]:
        """从 DialogSession 构建前端快照

        Args:
            session: DialogSession 实例

        Returns:
            前端快照字典，如果 session 为 None 则返回 None
        """
        if session is None:
            return None

        messages = SnapshotBuilder._build_messages(session)
        streaming_message = SnapshotBuilder._build_streaming_message(session)
        current_model = SnapshotBuilder._get_current_model()

        return {
            "id": session.dialog_id,
            "title": session.metadata.title,
            "status": session.status.value,
            "messages": messages,
            "streaming_message": streaming_message,
            "metadata": {
                "model": current_model,
                "agent_name": SnapshotBuilder.DEFAULT_AGENT_NAME,
                "tool_calls_count": session.metadata.tool_calls_count,
                "total_tokens": session.metadata.token_count,
            },
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "selected_model_id": getattr(session, 'selected_model_id', None),
        }

    @staticmethod
    def _build_messages(session) -> List[Dict[str, Any]]:
        """构建消息列表

        Args:
            session: DialogSession 实例

        Returns:
            消息字典列表
        """
        messages = []
        for msg in session.history.messages:
            role = SnapshotBuilder._get_message_role(msg)
            msg_id = getattr(msg, 'msg_id', '') or str(id(msg))[:12]

            # 从 message metadata 中提取模型信息
            msg_metadata = getattr(msg, 'additional_kwargs', {}) or {}
            msg_model = msg_metadata.get('model')
            msg_provider = msg_metadata.get('provider')
            msg_reasoning = msg_metadata.get('reasoning_content')

            msg_dict = {
                "id": msg_id,
                "role": role,
                "content": msg.content,
                "content_type": "text",
                "status": "completed",
                "timestamp": session.updated_at.isoformat(),
            }

            # 添加模型信息（如果有）
            if msg_model:
                msg_dict["model"] = msg_model
            if msg_provider:
                msg_dict["provider"] = msg_provider
            if msg_reasoning:
                msg_dict["reasoning_content"] = msg_reasoning

            messages.append(msg_dict)

        return messages

    @staticmethod
    def _build_streaming_message(session) -> Optional[Dict[str, Any]]:
        """构建流式消息（如果处于流式状态）

        Args:
            session: DialogSession 实例

        Returns:
            流式消息字典或 None
        """
        if not session.streaming_context:
            return None

        return {
            "id": session.streaming_context.message_id,
            "role": "assistant",
            "content": "",  # Delta 会累积在前端
            "content_type": "text",
            "status": "streaming",
            "timestamp": session.updated_at.isoformat(),
        }

    @staticmethod
    def _get_message_role(msg) -> str:
        """获取消息角色

        Args:
            msg: LangChain 消息对象

        Returns:
            角色字符串 (user/assistant/tool)
        """
        if isinstance(msg, HumanMessage):
            return "user"
        elif isinstance(msg, AIMessage):
            return "assistant"
        elif isinstance(msg, ToolMessage):
            return "tool"
        else:
            return "unknown"

    @staticmethod
    def _get_current_model() -> str:
        """获取当前模型名称

        Returns:
            模型名称，如果获取失败则返回 "unknown"
        """
        try:
            from backend.infrastructure.services.provider_manager import ProviderManager
            pm = ProviderManager()
            model_config = pm.get_model_config()
            return model_config.model
        except Exception:
            # 回退到环境变量
            return os.getenv("MODEL_ID", "unknown")

    @staticmethod
    def transform_message_for_ws(msg_dict: Dict[str, Any]) -> Dict[str, Any]:
        """将内部消息格式转换为 WebSocket 消息格式

        Args:
            msg_dict: 内部消息字典

        Returns:
            WebSocket 消息格式字典
        """
        return {
            "id": msg_dict.get("id", ""),
            "role": msg_dict.get("role", ""),
            "content": msg_dict.get("content", ""),
            "content_type": msg_dict.get("content_type", "text"),
            "status": msg_dict.get("status", "completed"),
            "timestamp": msg_dict.get("timestamp", iso_timestamp_now()),
        }


# 向后兼容的便捷函数
def build_dialog_snapshot(session) -> Optional[Dict[str, Any]]:
    """构建对话快照（向后兼容）

    使用方式:
        from backend.domain.utils import build_dialog_snapshot
        snapshot = build_dialog_snapshot(session)

    Args:
        session: DialogSession 实例

    Returns:
        前端快照字典
    """
    return SnapshotBuilder.build_from_session(session)


__all__ = [
    "SnapshotBuilder",
    "build_dialog_snapshot",
]
