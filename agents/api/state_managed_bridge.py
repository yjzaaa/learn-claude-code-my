"""
StateManagedAgentBridge - 状态管理型 Agent Bridge

这是后端状态管理的唯一真实数据源实现。
任何状态变更都会立即广播快照到前端。
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Optional
from loguru import logger

try:
    from ..models.dialog_types import (
        DialogSession,
        DialogStatus,
        Message,
        MessageStatus,
        Role,
        ContentType,
        ToolCall,
        ToolCallStatus,
        DialogSummary,
    )
    from ..websocket.server import connection_manager
    from ..base.abstract.hooks import FullAgentHooks, HookName
except ImportError:
    from agents.models.dialog_types import (
        DialogSession,
        DialogStatus,
        Message,
        MessageStatus,
        Role,
        ContentType,
        ToolCall,
        ToolCallStatus,
        DialogSummary,
    )
    from agents.websocket.server import connection_manager
    from agents.base.abstract.hooks import FullAgentHooks, HookName


class StateManagedAgentBridge(FullAgentHooks):
    """
    状态管理型 Agent Bridge

    维护 DialogSession 完整状态，任何状态变更立即广播快照。
    """

    def __init__(self, dialog_id: str, agent_name: str = "TeamLeadAgent"):
        self.dialog_id = dialog_id
        self.agent_name = agent_name
        self.session = DialogSession.create_new(
            dialog_id=dialog_id,
            title="Agent 对话",
            agent_name=agent_name,
        )
        logger.info(f"[StateBridge] Created session for dialog {dialog_id}")

    # ===== 状态查询方法 =====

    def get_session(self) -> DialogSession:
        """获取当前会话状态（只读）"""
        return self.session

    def to_snapshot(self) -> dict:
        """生成状态快照"""
        return {
            "type": "dialog:snapshot",
            "dialog_id": self.dialog_id,
            "data": self.session.to_dict(),
            "timestamp": time.time(),
        }

    def to_summary(self) -> DialogSummary:
        """生成对话框摘要"""
        return DialogSummary(
            id=self.dialog_id,
            title=self.session.title,
            message_count=len(self.session.messages),
            updated_at=self.session.updated_at,
        )

    # ===== 私有广播方法 =====

    async def _broadcast(self, event: dict):
        """广播事件到所有 WebSocket 客户端"""
        try:
            await connection_manager.broadcast(event)
        except Exception as e:
            logger.error(f"[StateBridge] Broadcast error: {e}")

    def _push_snapshot(self):
        """推送完整状态快照"""
        snapshot = self.to_snapshot()
        asyncio.create_task(self._broadcast(snapshot))
        logger.debug(f"[StateBridge] Pushed snapshot for {self.dialog_id}, status={self.session.status.value}")

    def _push_delta(self, message_id: str, delta: dict):
        """推送流式增量"""
        event = {
            "type": "stream:delta",
            "dialog_id": self.dialog_id,
            "message_id": message_id,
            "delta": delta,
            "timestamp": time.time(),
        }
        asyncio.create_task(self._broadcast(event))

    def _push_tool_call_update(self, tool_call: ToolCall):
        """推送工具调用状态更新"""
        event = {
            "type": "tool_call:update",
            "dialog_id": self.dialog_id,
            "tool_call": tool_call.to_dict(),
            "timestamp": time.time(),
        }
        asyncio.create_task(self._broadcast(event))

    def _push_status_change(self, old_status: DialogStatus, new_status: DialogStatus):
        """推送状态变更"""
        event = {
            "type": "status:change",
            "dialog_id": self.dialog_id,
            "from": old_status.value,
            "to": new_status.value,
            "timestamp": time.time(),
        }
        asyncio.create_task(self._broadcast(event))

    def _gen_id(self, prefix: str = "msg") -> str:
        """生成唯一ID"""
        return f"{prefix}_{self.dialog_id}_{int(time.time() * 1000)}"

    # ===== 用户交互方法 =====

    def on_user_input(self, content: str) -> Message:
        """用户输入处理"""
        user_msg = Message(
            id=self._gen_id("user"),
            role=Role.USER,
            content=content,
            content_type=ContentType.TEXT,
            status=MessageStatus.COMPLETED,
        )

        self.session.add_message(user_msg)
        self.session.status = DialogStatus.THINKING
        self.session.update_timestamp()

        # 推送快照（包含新用户消息和状态变更）
        self._push_snapshot()
        logger.info(f"[StateBridge] User input added, dialog status: {self.session.status.value}")

        return user_msg

    # ===== Agent Hook Handlers =====

    def on_before_run(self, messages: list[dict[str, Any]]) -> None:
        """运行前重置状态"""
        # 重置流式消息
        self.session.streaming_message = None
        self.session.status = DialogStatus.THINKING
        logger.info(f"[StateBridge] Run started, status: {self.session.status.value}")

    def _ensure_streaming_message(self) -> Message:
        """确保流式消息存在"""
        if not self.session.streaming_message:
            assistant_msg = Message(
                id=self._gen_id("assistant"),
                role=Role.ASSISTANT,
                content="",
                content_type=ContentType.MARKDOWN,
                tool_calls=[],
                reasoning_content="",
                agent_name=self.agent_name,
                status=MessageStatus.STREAMING,
            )
            self.session.streaming_message = assistant_msg
            self.session.status = DialogStatus.THINKING
            self.session.update_timestamp()
            self._push_snapshot()
            logger.info(f"[StateBridge] Stream started, message_id: {assistant_msg.id}")
        return self.session.streaming_message

    def on_stream_token(self, chunk: Any) -> None:
        """处理流式 token (符合 FullAgentHooks 接口)"""
        # 确保流式消息存在
        self._ensure_streaming_message()

        # 根据 chunk 类型处理
        if hasattr(chunk, 'is_content') and chunk.is_content:
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            if self.session.streaming_message:
                self.session.streaming_message.content += content
                self.session.update_timestamp()
                self._push_delta(
                    self.session.streaming_message.id,
                    {"content": content}
                )

        elif hasattr(chunk, 'is_reasoning') and chunk.is_reasoning:
            reasoning = chunk.reasoning_content if hasattr(chunk, 'reasoning_content') else str(chunk)
            if self.session.streaming_message:
                self.session.streaming_message.reasoning_content = (
                    (self.session.streaming_message.reasoning_content or "") + reasoning
                )
                self.session.update_timestamp()
                self._push_delta(
                    self.session.streaming_message.id,
                    {"reasoning": reasoning}
                )

    def on_tool_call(self, name: str, arguments: dict[str, Any], tool_call_id: str = "") -> ToolCall:
        """工具调用"""
        # 确保流式消息存在
        if not self.session.streaming_message:
            self.on_stream_start()

        actual_id = tool_call_id or self._gen_id("call")

        tool_call = ToolCall(
            id=actual_id,
            name=name,
            arguments=arguments,
            status=ToolCallStatus.PENDING,
        )

        self.session.streaming_message.tool_calls = self.session.streaming_message.tool_calls or []
        self.session.streaming_message.tool_calls.append(tool_call)
        self.session.metadata.tool_calls_count += 1
        self.session.status = DialogStatus.TOOL_CALLING
        self.session.update_timestamp()

        self._push_snapshot()
        logger.info(f"[StateBridge] Tool call added: {name}, id: {actual_id}")

        return tool_call

    def on_tool_start(self, tool_call_id: str):
        """工具开始执行"""
        tool = self.session.get_tool_call(tool_call_id)
        if tool:
            tool.status = ToolCallStatus.RUNNING
            tool.started_at = datetime.now().isoformat()
            self.session.update_timestamp()

            self._push_tool_call_update(tool)
            logger.info(f"[StateBridge] Tool started: {tool_call_id}")

    def on_tool_result(self, name: str, result: str, assistant_message: dict[str, Any] | None = None, tool_call_id: str = ""):
        """工具执行完成"""
        actual_id = tool_call_id or self._gen_id("call")
        tool = self.session.get_tool_call(actual_id)

        if tool:
            tool.status = ToolCallStatus.COMPLETED
            tool.result = result
            tool.completed_at = datetime.now().isoformat()

            # 添加 tool 消息到消息列表
            tool_msg = Message(
                id=self._gen_id("tool"),
                role=Role.TOOL,
                content=result,
                tool_call_id=actual_id,
                tool_name=tool.name,
                status=MessageStatus.COMPLETED,
            )
            self.session.add_message(tool_msg)

            self._push_tool_call_update(tool)
            logger.info(f"[StateBridge] Tool completed: {tool.name}")
        else:
            logger.warning(f"[StateBridge] Tool not found: {actual_id}")

    def on_complete(self, content: str):
        """流式输出完成 (符合 FullAgentHooks 接口)"""
        if self.session.streaming_message:
            # 如果传入了 content，更新内容
            if content:
                self.session.streaming_message.content = content
            self.session.streaming_message.status = MessageStatus.COMPLETED
            self.session.add_message(self.session.streaming_message)
            self.session.streaming_message = None

        # 检查是否还有未完成的工具调用
        if self._has_pending_tool_calls():
            old_status = self.session.status
            self.session.status = DialogStatus.TOOL_CALLING
            self._push_status_change(old_status, self.session.status)
        else:
            old_status = self.session.status
            self.session.status = DialogStatus.COMPLETED
            self._push_status_change(old_status, self.session.status)

        self._push_snapshot()
        logger.info(f"[StateBridge] Stream completed, status: {self.session.status.value}")

    def on_after_run(self, messages: list[dict[str, Any]], rounds: int) -> None:
        """运行结束后清理"""
        # 确保流式消息被正确保存
        if self.session.streaming_message:
            self.session.streaming_message.status = MessageStatus.COMPLETED
            self.session.add_message(self.session.streaming_message)
            self.session.streaming_message = None

        # 最终状态更新
        if self.session.status not in (DialogStatus.ERROR, DialogStatus.COMPLETED):
            old_status = self.session.status
            self.session.status = DialogStatus.COMPLETED
            self._push_status_change(old_status, self.session.status)

        self._push_snapshot()
        logger.info(f"[StateBridge] Run completed, rounds: {rounds}")

    def on_error(self, error: Exception):
        """错误处理"""
        old_status = self.session.status
        self.session.status = DialogStatus.ERROR

        # 添加错误消息
        error_msg = Message(
            id=self._gen_id("error"),
            role=Role.SYSTEM,
            content=str(error),
            status=MessageStatus.ERROR,
        )
        self.session.add_message(error_msg)

        self._push_status_change(old_status, self.session.status)
        self._push_snapshot()
        logger.error(f"[StateBridge] Error: {error}")

    def on_stop(self):
        """停止处理"""
        old_status = self.session.status

        # 保存当前的流式消息
        if self.session.streaming_message:
            self.session.streaming_message.status = MessageStatus.COMPLETED
            self.session.add_message(self.session.streaming_message)
            self.session.streaming_message = None

        self.session.status = DialogStatus.IDLE
        self._push_status_change(old_status, self.session.status)
        self._push_snapshot()
        logger.info(f"[StateBridge] Stopped")

    # ===== 辅助方法 =====

    def _has_pending_tool_calls(self) -> bool:
        """检查是否有未完成的工具调用"""
        if self.session.streaming_message and self.session.streaming_message.tool_calls:
            return any(
                t.status in (ToolCallStatus.PENDING, ToolCallStatus.RUNNING)
                for t in self.session.streaming_message.tool_calls
            )
        return False


class DialogStore:
    """
    对话框存储

    管理所有活跃的对话框会话。
    """

    _instance: Optional['DialogStore'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._sessions: dict[str, DialogSession] = {}
        self._bridges: dict[str, StateManagedAgentBridge] = {}
        self._initialized = True

    def create_dialog(self, dialog_id: str, title: str = "新对话", agent_name: str = "TeamLeadAgent") -> StateManagedAgentBridge:
        """创建新对话框"""
        bridge = StateManagedAgentBridge(dialog_id, agent_name)
        self._sessions[dialog_id] = bridge.get_session()
        self._bridges[dialog_id] = bridge
        logger.info(f"[DialogStore] Created dialog: {dialog_id}")
        return bridge

    def get_bridge(self, dialog_id: str) -> Optional[StateManagedAgentBridge]:
        """获取 Bridge"""
        return self._bridges.get(dialog_id)

    def get_session(self, dialog_id: str) -> Optional[DialogSession]:
        """获取会话状态"""
        bridge = self._bridges.get(dialog_id)
        if bridge:
            return bridge.get_session()
        return None

    def get_summary(self, dialog_id: str) -> Optional[DialogSummary]:
        """获取摘要"""
        bridge = self._bridges.get(dialog_id)
        if bridge:
            return bridge.to_summary()
        return None

    def list_dialogs(self) -> list[DialogSummary]:
        """列出所有对话框"""
        return [b.to_summary() for b in self._bridges.values()]

    def delete_dialog(self, dialog_id: str) -> bool:
        """删除对话框"""
        if dialog_id in self._bridges:
            del self._bridges[dialog_id]
            if dialog_id in self._sessions:
                del self._sessions[dialog_id]
            logger.info(f"[DialogStore] Deleted dialog: {dialog_id}")
            return True
        return False


# 全局存储实例
dialog_store = DialogStore()
