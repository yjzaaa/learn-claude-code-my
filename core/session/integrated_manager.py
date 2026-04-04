"""
Integrated Session Manager - 集成 WebSocket 的会话管理器

将 DialogSessionManager 与 WebSocket 广播器集成，实现完整的前后端事件同步。
"""

from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
import logging

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.messages import message_to_dict

from .manager import DialogSessionManager, EventHandler
from .models import SessionEvent, SessionStatus
from interfaces.websocket.manager import WebSocketBroadcaster, WSDialogMetadata

logger = logging.getLogger(__name__)


class IntegratedSessionManager(DialogSessionManager):
    """
    集成 WebSocket 广播的会话管理器

    职责:
    1. 继承 DialogSessionManager 的所有功能
    2. 自动将内部事件转换为 WebSocket 事件并广播
    3. 向前端发送 dialog:snapshot 等关键事件
    """

    def __init__(
        self,
        broadcaster: WebSocketBroadcaster,
        max_sessions: int = 100,
        session_ttl_seconds: int = 1800,
    ):
        super().__init__(
            max_sessions=max_sessions,
            session_ttl_seconds=session_ttl_seconds,
            event_handler=self._on_session_event
        )
        self._broadcaster = broadcaster

    def _on_session_event(self, event: SessionEvent) -> None:
        """处理会话内部事件并广播到 WebSocket"""
        # 使用 asyncio.create_task 异步广播，避免阻塞
        try:
            asyncio.create_task(self._broadcast_event(event))
        except Exception as e:
            logger.error(f"[IntegratedSessionManager] Failed to broadcast event: {e}")

    async def _broadcast_event(self, event: SessionEvent) -> None:
        """将会话事件转换为 WebSocket 事件并广播"""
        try:
            if event.type == "delta":
                # 流式增量
                delta = event.data.get("delta", "")
                message_id = event.data.get("message_id", "")
                if delta:
                    await self._broadcaster.broadcast_delta(
                        dialog_id=event.dialog_id,
                        message_id=message_id,
                        delta=delta,
                        is_reasoning=False
                    )

            elif event.type == "reasoning_delta":
                # 推理增量
                reasoning = event.data.get("reasoning", "")
                message_id = event.data.get("message_id", "")
                if reasoning:
                    await self._broadcaster.broadcast_delta(
                        dialog_id=event.dialog_id,
                        message_id=message_id,
                        delta=reasoning,
                        is_reasoning=True
                    )

            elif event.type == "status_change":
                # 状态变更
                from_status = event.data.get("from", "")
                to_status = event.data.get("to", "")
                await self._broadcaster.broadcast_status_change(
                    dialog_id=event.dialog_id,
                    from_status=from_status,
                    to_status=to_status
                )

                # 状态变更后发送最新快照
                if to_status in ("completed", "active"):
                    await self.broadcast_snapshot(event.dialog_id)

            elif event.type == "tool_call":
                # 工具调用事件
                tool_name = event.data.get("name", "")
                tool_input = event.data.get("input", {})
                tool_call_id = event.data.get("tool_call_id", "")
                # 转换为前端格式
                event_dict = {
                    "type": "agent:tool_call",
                    "dialog_id": event.dialog_id,
                    "data": {
                        "message_id": tool_call_id or f"tool_{int(datetime.now().timestamp() * 1000)}",
                        "tool_call": {
                            "id": tool_call_id or f"call_{int(datetime.now().timestamp() * 1000)}",
                            "name": tool_name,
                            "arguments": tool_input,
                            "status": "running"
                        }
                    },
                    "timestamp": int(datetime.now().timestamp() * 1000)
                }
                await self._broadcaster.broadcast(event_dict, event.dialog_id)

            elif event.type == "tool_result":
                # 工具结果事件
                tool_call_id = event.data.get("tool_call_id", "")
                result = event.data.get("result", "")
                duration_ms = event.data.get("duration_ms")
                event_dict = {
                    "type": "agent:tool_result",
                    "dialog_id": event.dialog_id,
                    "data": {
                        "tool_call_id": tool_call_id,
                        "tool_name": "unknown",  # 可以从上下文中获取
                        "result": result,
                    },
                    "timestamp": int(datetime.now().timestamp() * 1000)
                }
                await self._broadcaster.broadcast(event_dict, event.dialog_id)

            elif event.type == "snapshot":
                # 显式请求的快照
                await self.broadcast_snapshot(event.dialog_id)

        except Exception as e:
            logger.error(f"[IntegratedSessionManager] Broadcast error: {e}")

    async def broadcast_snapshot(self, dialog_id: str) -> None:
        """广播对话快照到 WebSocket"""
        try:
            snapshot = self.build_snapshot(dialog_id)
            if not snapshot:
                return

            # 转换为 WSDialogSnapshot 格式
            from core.models.websocket_models import WSDialogSnapshot, WSStreamingMessage

            # 构建消息列表（LangChain 格式）
            messages = []
            for msg in snapshot.get("messages", []):
                msg_dict = {
                    "type": msg.get("role", "unknown"),
                    "content": msg.get("content", ""),
                    "additional_kwargs": {}
                }
                messages.append(msg_dict)

            # 构建 streaming_message（如果存在）
            streaming_msg = snapshot.get("streaming_message")
            ws_streaming = None
            if streaming_msg:
                ws_streaming = WSStreamingMessage(
                    id=streaming_msg.get("id", ""),
                    message={
                        "type": "assistant",
                        "content": streaming_msg.get("content", ""),
                        "additional_kwargs": {}
                    },
                    status="streaming",
                    timestamp=streaming_msg.get("timestamp", ""),
                    agent_name=snapshot.get("metadata", {}).get("agent_name", "Agent"),
                    reasoning_content=streaming_msg.get("reasoning_content")
                )

            # 构建元数据
            metadata = WSDialogMetadata(
                model=snapshot.get("metadata", {}).get("model", ""),
                agent_name=snapshot.get("metadata", {}).get("agent_name", "Agent"),
                tool_calls_count=snapshot.get("metadata", {}).get("tool_calls_count", 0),
                total_tokens=snapshot.get("metadata", {}).get("total_tokens", 0)
            )

            # 构建快照
            ws_snapshot = WSDialogSnapshot(
                id=dialog_id,
                title=snapshot.get("title", "Dialog"),
                status=snapshot.get("status", "active"),
                messages=messages,
                streaming_message=ws_streaming,
                metadata=metadata,
                created_at=snapshot.get("created_at", ""),
                updated_at=snapshot.get("updated_at", "")
            )

            # 构建事件
            from core.models.websocket_models import WSSnapshotEvent
            event = WSSnapshotEvent(
                type="dialog:snapshot",
                dialog_id=dialog_id,
                data=ws_snapshot,
                timestamp=int(datetime.now().timestamp() * 1000)
            )

            await self._broadcaster.broadcast(event, dialog_id)
            logger.debug(f"[IntegratedSessionManager] Broadcasted snapshot for {dialog_id}")

        except Exception as e:
            logger.error(f"[IntegratedSessionManager] Failed to broadcast snapshot: {e}")

    # ==================== 重写方法以添加广播 ====================

    async def add_user_message(
        self,
        dialog_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HumanMessage:
        """添加用户消息并广播 message:added 事件"""
        msg = await super().add_user_message(dialog_id, content, metadata)

        # 广播 message:added 事件
        try:
            await self._broadcaster.broadcast_message_added(dialog_id, msg)
            # 同时发送快照更新
            await self.broadcast_snapshot(dialog_id)
        except Exception as e:
            logger.error(f"[IntegratedSessionManager] Failed to broadcast user message: {e}")

        return msg

    async def complete_ai_response(
        self,
        dialog_id: str,
        message_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AIMessage:
        """完成 AI 响应并广播更新"""
        msg = await super().complete_ai_response(dialog_id, message_id, content, metadata)

        # 广播 message:added 事件
        try:
            await self._broadcaster.broadcast_message_added(dialog_id, msg)
            await self.broadcast_snapshot(dialog_id)
        except Exception as e:
            logger.error(f"[IntegratedSessionManager] Failed to broadcast AI message: {e}")

        return msg

    async def start_ai_response(
        self,
        dialog_id: str,
        message_id: str,
    ) -> None:
        """标记 AI 响应开始并广播 stream:start"""
        await super().start_ai_response(dialog_id, message_id)

        # 广播 stream:start 事件
        try:
            await self._broadcaster.broadcast_stream_start(
                dialog_id=dialog_id,
                message_id=message_id,
                message=None  # 还没有内容
            )
        except Exception as e:
            logger.error(f"[IntegratedSessionManager] Failed to broadcast stream start: {e}")

    async def add_tool_result(
        self,
        dialog_id: str,
        tool_call_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolMessage:
        """添加工具结果并广播"""
        msg = await super().add_tool_result(dialog_id, tool_call_id, content, metadata)

        # 广播 tool_result 事件并更新快照
        try:
            await self._broadcast_event(SessionEvent(
                type="tool_result",
                dialog_id=dialog_id,
                data={
                    "tool_call_id": tool_call_id,
                    "result": content,
                }
            ))
            await self.broadcast_snapshot(dialog_id)
        except Exception as e:
            logger.error(f"[IntegratedSessionManager] Failed to broadcast tool result: {e}")

        return msg

    # ==================== 便捷方法 ====================

    async def emit_delta_with_broadcast(
        self,
        dialog_id: str,
        delta: str,
        message_id: Optional[str] = None,
    ) -> None:
        """发送 delta 并广播到 WebSocket"""
        await self.emit_delta(dialog_id, delta, message_id)

    async def emit_reasoning_with_broadcast(
        self,
        dialog_id: str,
        reasoning: str,
        message_id: Optional[str] = None,
    ) -> None:
        """发送 reasoning delta 并广播到 WebSocket"""
        await self.emit_reasoning_delta(dialog_id, reasoning, message_id)


# 全局实例（在应用启动时初始化）
_integrated_manager: Optional[IntegratedSessionManager] = None


def get_integrated_manager() -> Optional[IntegratedSessionManager]:
    """获取全局集成的会话管理器实例"""
    return _integrated_manager


def set_integrated_manager(manager: IntegratedSessionManager) -> None:
    """设置全局集成的会话管理器实例"""
    global _integrated_manager
    _integrated_manager = manager
