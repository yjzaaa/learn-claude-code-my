"""
EventCoordinator - 后端事件协调器

作为 Runtime 与 WebSocket 之间的唯一桥梁：
- 接收 Runtime 产出的 AgentEvent
- 通过 SessionManager 管理对话状态
- 转换为 ServerPushEvent 并广播到所有 WebSocket 客户端
"""

from typing import Any, Awaitable, Callable, Optional
from datetime import datetime, timezone
import time

from core.models.agent_events import (
    AgentEvent,
    DialogSnapshotEvent,
    StreamDeltaEvent,
    StatusChangeEvent,
    ToolCallEvent,
    ToolResultEvent,
    ErrorEvent,
    ServerPushEvent,
)
from core.session import DialogSessionManager


def _ts() -> int:
    return int(time.time() * 1000)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventCoordinator:
    """
    事件协调器 - Runtime 与前端之间的唯一事件网关
    """

    def __init__(
        self,
        broadcast: Callable[[Any], Awaitable[None]],
        session_manager: DialogSessionManager,
    ):
        self._broadcast = broadcast
        self._session_mgr = session_manager

        # 设置 SessionManager 的事件处理器，将事件转发给前端
        self._session_mgr.set_event_handler(self._handle_session_event)

        # 兼容性：保留 _status 用于快速状态查询
        self._status: dict[str, str] = {}

        # 缓存当前流式消息 ID (dialog_id -> message_id)
        self._streaming_msg_ids: dict[str, str] = {}

    async def _handle_session_event(self, event) -> None:
        """处理 SessionManager 发出的事件并广播给前端"""
        # 将 SessionManager 的 SessionEvent 转换为前端格式
        if event.type == "delta":
            await self._send(StreamDeltaEvent(
                dialog_id=event.dialog_id,
                message_id=self._get_streaming_message_id(event.dialog_id),
                delta={"content": event.data.get("delta", "")},
                timestamp=event.timestamp
            ))
        elif event.type == "reasoning_delta":
            await self._send(StreamDeltaEvent(
                dialog_id=event.dialog_id,
                message_id=self._get_streaming_message_id(event.dialog_id),
                delta={"reasoning": event.data.get("reasoning", "")},
                timestamp=event.timestamp
            ))
        elif event.type == "status_change":
            self._status[event.dialog_id] = event.data.get("to", "idle")
            await self._send(StatusChangeEvent(
                dialog_id=event.dialog_id,
                data=event.data,
                timestamp=event.timestamp
            ))
        elif event.type == "completed":
            await self._send(StatusChangeEvent(
                dialog_id=event.dialog_id,
                data={"from": "streaming", "to": "completed"},
                timestamp=event.timestamp
            ))
            # 广播快照
            await self.broadcast_snapshot(event.dialog_id)
        elif event.type == "error":
            await self._send(ErrorEvent(
                dialog_id=event.dialog_id,
                data=event.data,
                timestamp=event.timestamp
            ))

    # ==================== 状态管理 ====================

    def ensure_dialog(self, dialog_id: str, status: str = "idle") -> None:
        """确保对话在 coordinator 中有状态记录"""
        if dialog_id not in self._status:
            self._status[dialog_id] = status

    def set_status(self, dialog_id: str, status: str) -> None:
        """设置对话状态"""
        self._status[dialog_id] = status

    def get_status(self, dialog_id: str) -> str:
        """获取对话状态"""
        return self._status.get(dialog_id, "idle")

    def remove_dialog(self, dialog_id: str) -> None:
        """移除对话状态"""
        self._status.pop(dialog_id, None)

    def clear_streaming(self, dialog_id: str) -> None:
        """清除流式状态（兼容性方法）"""
        # 流式状态现在由 SessionManager 管理，此方法仅用于兼容性
        pass

    # ==================== Snapshot 构建 ====================

    def build_snapshot(self, dialog_id: str) -> Optional[dict[str, Any]]:
        """构建当前对话快照（从 SessionManager 获取）"""
        return self._session_mgr.build_snapshot(dialog_id)

    # ==================== 广播辅助 ====================

    async def _send(self, event: ServerPushEvent) -> None:
        """内部广播方法"""
        await self._broadcast(event.model_dump())

    async def broadcast_snapshot(self, dialog_id: str) -> None:
        """广播当前对话快照"""
        snap = self.build_snapshot(dialog_id)
        if snap is None:
            return
        await self._send(
            DialogSnapshotEvent(
                dialog_id=dialog_id,
                data=snap,
                timestamp=_ts(),
            )
        )

    async def broadcast_status_change(
        self, dialog_id: str, from_status: str, to_status: str
    ) -> None:
        """广播状态变更"""
        self._status[dialog_id] = to_status
        await self._send(
            StatusChangeEvent(
                dialog_id=dialog_id,
                data={"from": from_status, "to": to_status},
                timestamp=_ts(),
            )
        )

    # ==================== 核心：ingest AgentEvent ====================

    def set_streaming_message_id(self, dialog_id: str, message_id: str) -> None:
        """设置当前流式消息 ID"""
        self._streaming_msg_ids[dialog_id] = message_id

    def _get_streaming_message_id(self, dialog_id: str) -> str:
        """获取当前流式消息 ID"""
        return self._streaming_msg_ids.get(dialog_id, "")

    async def ingest(self, dialog_id: str, event: AgentEvent) -> None:
        """
        消费 Runtime 产出的 AgentEvent，转换为 ServerPushEvent 并广播
        """
        self.ensure_dialog(dialog_id)

        etype = event.type

        if etype == "text_delta":
            chunk = event.data
            if isinstance(chunk, list):
                chunk = "".join(str(c) for c in chunk)
            elif not isinstance(chunk, str):
                chunk = str(chunk)

            await self._send(
                StreamDeltaEvent(
                    dialog_id=dialog_id,
                    message_id=self._get_streaming_message_id(dialog_id),
                    delta={"content": chunk},
                    timestamp=event.timestamp or _ts(),
                )
            )
            return

        if etype == "reasoning_delta":
            chunk = event.data
            if not isinstance(chunk, str):
                chunk = str(chunk)
            await self._send(
                StreamDeltaEvent(
                    dialog_id=dialog_id,
                    message_id=self._get_streaming_message_id(dialog_id),
                    delta={"content": None, "reasoning": chunk},
                    timestamp=event.timestamp or _ts(),
                )
            )
            return

        if etype == "snapshot":
            await self.broadcast_snapshot(dialog_id)
            return

        if etype == "tool_call":
            await self._send(
                ToolCallEvent(
                    dialog_id=dialog_id,
                    data=event.data if isinstance(event.data, dict) else {},
                    timestamp=event.timestamp or _ts(),
                )
            )
            return

        if etype == "tool_result":
            await self._send(
                ToolResultEvent(
                    dialog_id=dialog_id,
                    data=event.data if isinstance(event.data, dict) else {},
                    timestamp=event.timestamp or _ts(),
                )
            )
            return

        if etype == "status_change":
            data = event.data if isinstance(event.data, dict) else {}
            from_status = data.get("from", self._status.get(dialog_id, "idle"))
            to_status = data.get("to", "idle")
            await self.broadcast_status_change(dialog_id, from_status, to_status)
            return

        if etype == "message_complete":
            # 将 streaming_message flush 为 completed message
            await self.broadcast_status_change(
                dialog_id, self._status.get(dialog_id, "thinking"), "completed"
            )
            self.set_status(dialog_id, "idle")
            # 清除流式消息 ID 缓存
            self._streaming_msg_ids.pop(dialog_id, None)
            return

        if etype == "error":
            msg = str(event.data) if event.data is not None else "Unknown error"
            await self._send(
                ErrorEvent(
                    dialog_id=dialog_id,
                    data={"code": "agent_error", "message": msg},
                    timestamp=event.timestamp or _ts(),
                )
            )
            await self.broadcast_status_change(
                dialog_id, self._status.get(dialog_id, "idle"), "error"
            )
            return

        # 未识别的事件类型，忽略
        import logging

        logging.getLogger(__name__).warning(
            "[EventCoordinator] Unhandled event type: %s", etype
        )
