"""Checkpoint Manager - Checkpoint 管理

处理 LangGraph checkpoint 的获取和快照。
"""

from typing import Any

from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)


class CheckpointManager:
    """Checkpoint 管理器

    职责:
    - 获取 LangGraph checkpoint 数据
    - 构建快照
    - 保存到文件
    """

    def __init__(self, checkpointer: Any):
        self._checkpointer = checkpointer

    def get_checkpoint_snapshot(self, dialog_id: str) -> dict[str, Any]:
        """获取 checkpoint 快照

        Args:
            dialog_id: 对话 ID (thread_id)

        Returns:
            Checkpoint 数据字典
        """
        try:
            if not self._checkpointer:
                return {"dialog_id": dialog_id, "checkpoint_exists": False}

            config = {"configurable": {"thread_id": dialog_id}}
            checkpoint_tuple = self._checkpointer.get_tuple(config)

            if not checkpoint_tuple:
                return {"dialog_id": dialog_id, "checkpoint_exists": False}

            return self._build_snapshot(dialog_id, checkpoint_tuple)

        except Exception as e:
            logger.debug(f"[Checkpoint] Failed to get snapshot: {e}")
            return {"dialog_id": dialog_id, "checkpoint_exists": False, "error": str(e)}

    def _build_snapshot(self, dialog_id: str, checkpoint_tuple: Any) -> dict[str, Any]:
        """构建快照"""
        checkpoint = checkpoint_tuple.checkpoint
        metadata = checkpoint_tuple.metadata if hasattr(checkpoint_tuple, "metadata") else {}
        pending_writes = (
            checkpoint_tuple.pending_writes if hasattr(checkpoint_tuple, "pending_writes") else []
        )

        channel_values = checkpoint.get("channel_values", {})
        messages_data = self._extract_messages(channel_values.get("messages", []))

        return {
            "dialog_id": dialog_id,
            "checkpoint_exists": True,
            "checkpoint_id": checkpoint.get("id"),
            "checkpoint_ns": checkpoint.get("checkpoint_ns", ""),
            "messages_count": len(messages_data),
            "messages": messages_data[:10] if messages_data else [],
            "channel_values": {
                k: str(v)[:500] if not isinstance(v, (int, float, bool, type(None))) else v
                for k, v in channel_values.items()
                if k != "messages"
            },
            "pending_writes": [
                {
                    "task_id": pw[0] if len(pw) > 0 else None,
                    "channel": pw[1] if len(pw) > 1 else None,
                }
                for pw in (pending_writes or [])[:5]
            ],
            "metadata": {
                k: str(v)[:200] if not isinstance(v, (int, float, bool, type(None))) else v
                for k, v in (metadata or {}).items()
            },
        }

    def _extract_messages(self, messages: list) -> list:
        """提取消息数据"""
        result = []
        for msg in messages:
            if hasattr(msg, "model_dump"):
                result.append(msg.model_dump())
            elif hasattr(msg, "__dict__"):
                result.append(msg.__dict__)
            else:
                result.append({"content": str(msg)})
        return result

    def save_snapshot(self, checkpoint_data: dict[str, Any]) -> str | None:
        """保存快照到 SessionManager"""
        try:
            from backend.infrastructure.container import container

            if container.session_manager:
                return container.session_manager.save_checkpoint_snapshot(checkpoint_data)
        except Exception as e:
            logger.debug(f"[Checkpoint] Failed to save snapshot: {e}")
        return None


__all__ = ["CheckpointManager"]
