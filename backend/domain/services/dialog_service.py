"""Dialog Service - 对话领域服务

处理对话相关的业务逻辑，不依赖 HTTP 层。
"""

import uuid

from backend.domain.models.types import (
    WSDialogSnapshot,
    WSMessageItem,
    WSStreamingMessage,
)
from backend.domain.utils import SnapshotBuilder, iso_timestamp, timestamp_ms


def make_message_item(m) -> WSMessageItem:
    """将内部消息格式转换为 WSMessageItem

    Args:
        m: LangChain 消息对象或字典

    Returns:
        WSMessageItem
    """
    # 使用 SnapshotBuilder 的转换逻辑
    if hasattr(m, "type"):
        # LangChain 消息使用 type 属性 (human/ai/system/tool)
        msg_type = m.type
        role_map = {"human": "user", "ai": "assistant", "system": "system", "tool": "tool"}
        role = role_map.get(msg_type, msg_type)
        msg_id = getattr(m, "msg_id", "") or getattr(m, "id", "")
        content = getattr(m, "content", "") or ""
    else:
        # 字典格式
        role = m.get("role", "unknown")
        msg_id = m.get("id", "")
        content = m.get("content", "")

    return WSMessageItem(
        id=msg_id,
        role=role,
        content=content,
        content_type="markdown",
        status="completed",
        timestamp=iso_timestamp(),
    )


def create_streaming_placeholder(message_id: str, agent_name: str = "Agent") -> WSStreamingMessage:
    """创建流式消息占位符

    Args:
        message_id: 消息 ID
        agent_name: Agent 名称

    Returns:
        WSStreamingMessage
    """
    return WSStreamingMessage(
        id=message_id,
        role="assistant",
        content="",
        content_type="markdown",
        status="streaming",
        timestamp=iso_timestamp(),
        agent_name=agent_name,
        reasoning_content=None,
        tool_calls=[],
    )


def build_dialog_snapshot(
    dialog_id: str,
    session_manager,
    status: str = "idle",
    streaming_msg: WSStreamingMessage | None = None,
) -> WSDialogSnapshot | None:
    """构建对话快照

    Args:
        dialog_id: 对话 ID
        session_manager: SessionManager 实例
        status: 当前状态
        streaming_msg: 流式消息（如果有）

    Returns:
        WSDialogSnapshot 或 None
    """
    session_snap = session_manager.build_snapshot(dialog_id)
    if not session_snap:
        return None

    # 使用 SnapshotBuilder 转换消息列表
    messages = [
        SnapshotBuilder.transform_message_for_ws(m) for m in session_snap.get("messages", [])
    ]

    metadata = session_snap.get("metadata", {})

    # 从 session_snap 获取 selected_model_id（已由 manager.build_snapshot 提供）
    selected_model_id = session_snap.get("selected_model_id")

    return {
        "id": session_snap["id"],
        "title": session_snap.get("title", "New Dialog"),
        "status": status,
        "messages": messages,
        "streaming_message": streaming_msg,
        "metadata": {
            "model": metadata.get("model", ""),
            "agent_name": metadata.get("agent_name", "Agent"),
            "tool_calls_count": metadata.get("tool_calls_count", 0),
            "total_tokens": metadata.get("total_tokens", 0),
        },
        "created_at": session_snap["created_at"],
        "updated_at": session_snap.get("updated_at", session_snap["created_at"]),
        "selected_model_id": selected_model_id,
    }


def generate_dialog_id() -> str:
    """生成对话 ID"""
    return f"dlg_{uuid.uuid4().hex[:12]}"


def generate_message_id() -> str:
    """生成消息 ID"""
    return f"msg_{uuid.uuid4().hex[:12]}"


class DialogService:
    """对话服务

    处理对话相关的业务操作。
    """

    def __init__(self, session_manager, runtime=None):
        self.session_manager = session_manager
        self.runtime = runtime

    async def create_dialog(self, title: str, user_input: str = "") -> str:
        """创建新对话

        Args:
            title: 对话标题
            user_input: 用户初始输入

        Returns:
            新对话 ID
        """
        if self.runtime:
            dialog_id = await self.runtime.create_dialog(user_input, title)
        else:
            dialog_id = generate_dialog_id()

        return dialog_id

    async def get_dialog(self, dialog_id: str) -> WSDialogSnapshot | None:
        """获取对话信息

        Args:
            dialog_id: 对话 ID

        Returns:
            WSDialogSnapshot 或 None
        """
        from backend.infrastructure.container import container

        return build_dialog_snapshot(
            dialog_id,
            self.session_manager,
            container.get_status(dialog_id),
            container.get_streaming_message(dialog_id),
        )

    async def list_dialogs(self) -> list:
        """列出所有对话"""
        from backend.infrastructure.container import container

        dialogs = []
        for session in self.session_manager.list_sessions():
            snap = build_dialog_snapshot(
                session.dialog_id,
                self.session_manager,
                container.get_status(session.dialog_id),
                container.get_streaming_message(session.dialog_id),
            )
            if snap:
                dialogs.append(snap)
        return dialogs

    async def delete_dialog(self, dialog_id: str) -> None:
        """删除对话"""
        from backend.infrastructure.container import container

        session = self.session_manager.get_session_sync(dialog_id)
        if session is not None:
            await self.session_manager.close_session(dialog_id)

        # 清理状态
        container.clear_dialog_state(dialog_id)

    def get_messages(self, dialog_id: str) -> list:
        """获取对话消息列表"""
        snap = build_dialog_snapshot(dialog_id, self.session_manager, "idle", None)
        if snap:
            return snap.get("messages", [])
        return []


__all__ = [
    "DialogService",
    "timestamp_ms",
    "iso_timestamp",
    "make_message_item",
    "create_streaming_placeholder",
    "build_dialog_snapshot",
    "generate_dialog_id",
    "generate_message_id",
]
