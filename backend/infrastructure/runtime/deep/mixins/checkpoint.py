"""Deep Checkpoint Mixin - Checkpoint 快照功能

从 deep_legacy.py 提取的 checkpoint 管理逻辑。
"""

from typing import Any


class DeepCheckpointMixin:
    """Checkpoint 管理 Mixin"""

    _checkpointer: Any

    def _get_checkpoint_snapshot(self, dialog_id: str) -> dict[str, Any]:
        """获取 LangGraph checkpoint 快照数据

        从 InMemorySaver 中获取完整的运行时状态，包括：
        - 完整消息列表（含工具调用中间状态）
        - Pending writes（待写入的中间状态）
        - Channel values（各通道的当前值）

        Args:
            dialog_id: 对话 ID（对应 thread_id）

        Returns:
            包含 checkpoint 数据的字典，如果未找到则返回基础结构
        """
        try:
            if not self._checkpointer:
                return {"dialog_id": dialog_id, "checkpoint_exists": False}

            config = {"configurable": {"thread_id": dialog_id}}
            checkpoint_tuple = self._checkpointer.get_tuple(config)

            if not checkpoint_tuple:
                return {"dialog_id": dialog_id, "checkpoint_exists": False}

            checkpoint = checkpoint_tuple.checkpoint
            metadata = checkpoint_tuple.metadata if hasattr(checkpoint_tuple, 'metadata') else {}
            pending_writes = checkpoint_tuple.pending_writes if hasattr(checkpoint_tuple, 'pending_writes') else []

            # 提取消息数据（通常在 "messages" channel）
            channel_values = checkpoint.get("channel_values", {})
            messages_data = []
            if "messages" in channel_values:
                for msg in channel_values["messages"]:
                    if hasattr(msg, 'model_dump'):
                        messages_data.append(msg.model_dump())
                    elif hasattr(msg, '__dict__'):
                        messages_data.append(msg.__dict__)
                    else:
                        messages_data.append({"content": str(msg)})

            return {
                "dialog_id": dialog_id,
                "checkpoint_exists": True,
                "checkpoint_id": checkpoint.get("id"),
                "checkpoint_ns": checkpoint.get("checkpoint_ns", ""),
                "messages_count": len(messages_data),
                "messages": messages_data[:10] if messages_data else [],  # 限制数量避免过大
                "channel_values": {
                    k: str(v)[:500] if not isinstance(v, (int, float, bool, type(None))) else v
                    for k, v in channel_values.items()
                    if k != "messages"  # 消息已单独提取
                },
                "pending_writes": [
                    {"task_id": pw[0] if len(pw) > 0 else None,
                     "channel": pw[1] if len(pw) > 1 else None}
                    for pw in (pending_writes or [])[:5]  # 限制数量
                ],
                "metadata": {
                    k: str(v)[:200] if not isinstance(v, (int, float, bool, type(None))) else v
                    for k, v in (metadata or {}).items()
                },
            }
        except Exception as e:
            return {
                "dialog_id": dialog_id,
                "checkpoint_exists": False,
                "error": str(e),
            }
